"""Attributed, append-only revisions and a pure projection of their journal.

An accepted text edit creates a new version and a proposed mechanical analysis.
Old units and semantic links stay on their old version. Reattachment candidates
are observations about strings, not claims of semantic equivalence.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .records import parse_json, sync_directory, word_spans, record_key, record_id, normalize_lines, publish_exclusive


FORMAT = "humboldt.revision_event"
SCHEMA_VERSION = 2
LEGACY_SUPPORTED = {
    'text_version': frozenset({'body'}),
    'term_sense': frozenset({'rule','definition','caution'}),
    'decision': frozenset({'resolution'}),
}
SUPPORTED = {
    "text_version": frozenset({"body", "title", "locator", "transcription_status", "provenance"}),
    "term_sense": frozenset({"label", "rule", "definition", "caution"}),
    "decision": frozenset({"question", "resolution", "authority", "status"}),
    "evidence": frozenset({"excerpt", "statement", "locator", "quote_status", "claim_status"}),
    "lexeme": frozenset({"headword", "kind", "scope"}),
    "sense_rendering": frozenset({"rendering"}),
    "lexeme_form": frozenset({"form", "form_role"}),
    "alignment": frozenset({"relation", "note", "status"}),
    "alignment_member": frozenset({"unit_id"}),
    "analysis": frozenset({"method", "scope", "status"}),
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_MAX_CANDIDATES = 32


class RevisionError(ValueError):
    """An unsupported or malformed revision/journal."""


class RevisionConflict(RevisionError):
    """The original target precondition is no longer true."""


class ProjectLocked(RevisionError):
    """Another writer owns the project lock; no stale lock is removed."""


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RevisionError("revision data must be finite JSON values") from exc


def _bytes(value):
    try:
        return (_json(value) + "\n").encode("utf-8")
    except UnicodeError as exc:
        raise RevisionError("revision data must be valid UTF-8 text") from exc


def fingerprint(row):
    """SHA-256 of a complete target row, with canonical JSON keys and values.

    A UI may include this as expected_sha256 in a downloaded proposal. Do not
    hash a query wrapper, selected columns, or history instead of the actual row.
    """
    if not isinstance(row, dict):
        row = dict(row)
    return hashlib.sha256(_bytes(row)).hexdigest()


def _text(value, name, *, empty=False):
    if not isinstance(value, str) or "\x00" in value:
        raise RevisionError(f"{name} must be a string without NUL")
    if not empty and not value.strip():
        raise RevisionError(f"{name} must not be empty")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise RevisionError(f"{name} must be valid UTF-8") from exc
    return value


def _uuid(value, name="event id"):
    _text(value, name)
    try:
        valid = str(uuid.UUID(value)) == value
    except ValueError:
        valid = False
    if not valid:
        raise RevisionError(f"{name} must be a canonical UUID")


def _time(value):
    _text(value, "recorded_at")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RevisionError("recorded_at must be an ISO timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise RevisionError("recorded_at must include a timezone")
    return result.astimezone(timezone.utc)


def _project(project):
    path = Path(project).resolve()
    if not path.is_dir():
        raise RevisionError("project must be an existing directory")
    return path


def _confined(project, relative):
    result = (project / relative).resolve()
    if not result.is_relative_to(project):
        raise RevisionError("journal path escapes the project")
    return result


@contextmanager
def project_lock(project):
    """Fail-fast exclusive lock shared by all project writers.

    The owner removes only its own unchanged lock file. There is deliberately
    no timeout, PID-based recovery, or automatic deletion of an existing lock.
    """
    project = _project(project)
    path = project / ".humboldt.lock"
    token = {"id": str(uuid.uuid4()), "pid": os.getpid(),
             "recorded_at": datetime.now(timezone.utc).isoformat()}
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ProjectLocked(f"project is locked: {path}. Inspect its PID and any running authoring command; remove only a confirmed abandoned lock. Never remove a live writer's lock.") from exc
    inode = None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_bytes(token))
            stream.flush()
            os.fsync(stream.fileno())
            inode = os.fstat(stream.fileno()).st_ino
        yield
    finally:
        try:
            current = path.stat()
            same = current.st_ino == inode and path.read_bytes() == _bytes(token)
        except FileNotFoundError:
            same = False
        if same:
            path.unlink()


def _publish(project, directory, event):
    parent = _confined(project, directory)
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / (event["id"] + ".json")
    fd, temporary = tempfile.mkstemp(prefix=".revision-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_bytes(event))
            stream.flush()
            os.fsync(stream.fileno())
        # A no-replace atomic publication: neither a UUID collision nor another
        # writer can cause an existing journal record to be overwritten.
        try:
            publish_exclusive(temporary, target)
        except FileExistsError as exc:
            raise RevisionConflict("journal event already exists") from exc
        sync_directory(parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _read_events(project):
    project = _project(project)
    events = []
    for relative, event_type in (("edition/proposals", "proposal"),
                                 ("edition/changes", "decision")):
        directory = _confined(project, relative)
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            if path.is_symlink() or not path.resolve().is_relative_to(project):
                raise RevisionError("journal files must be local regular files")
            try:
                raw = path.read_bytes()
                event = parse_json(raw)
            except (OSError, ValueError) as exc:
                raise RevisionError(f"cannot read journal event: {path.name}") from exc
            _validate_event(event)
            if event["event_type"] != event_type or path.stem != event["id"]:
                raise RevisionError("journal filename/directory does not match event")
            if raw != _bytes(event):
                raise RevisionError("journal event is not canonical JSON")
            events.append(event)
    return _ordered(events)


def _validate_event(event):
    if not isinstance(event, dict):
        raise RevisionError("journal events must be JSON objects")
    base = {"format", "schema_version", "event_type", "id", "sequence",
            "recorded_at", "by", "reason", "evidence"}
    if event.get("event_type") == "proposal":
        extra = {"kind", "target_id", "field", "value", "old_value", "target_sha256"}
        if event.get('schema_version') == 2:extra.add('target_snapshot')
    elif event.get("event_type") == "decision":
        extra = {"proposal_id", "accept"}
    else:
        raise RevisionError("unsupported event_type")
    if set(event) != base | extra:
        raise RevisionError("missing or unsupported journal fields")
    if event["format"] != FORMAT or type(event["schema_version"]) is not int or event["schema_version"] not in (1, 2):
        raise RevisionError("unsupported revision event format/schema")
    _uuid(event["id"])
    if type(event["sequence"]) is not int or event["sequence"] < 1:
        raise RevisionError("sequence must be a positive integer")
    _time(event["recorded_at"])
    _text(event["by"], "by")
    _text(event["reason"], "reason")
    if not isinstance(event["evidence"], list):
        raise RevisionError("evidence must be a list of known evidence IDs")
    if any(not isinstance(e, str) or not e.strip() for e in event["evidence"]):
        raise RevisionError("evidence references must be nonempty strings")
    if len(event["evidence"]) != len(set(event["evidence"])):
        raise RevisionError("duplicate evidence reference")
    if event["event_type"] == "decision":
        _uuid(event["proposal_id"], "proposal_id")
        if type(event["accept"]) is not bool:
            raise RevisionError("accept must explicitly be true or false")
    else:
        _operation(event["kind"], event["field"])
        if event['schema_version']==1 and event['field'] not in LEGACY_SUPPORTED.get(event['kind'],()):
            raise RevisionError('format 1 does not support this amendment; use format 2')
        _text(event["target_id"], "target_id")
        _value(event["kind"], event["field"], event["value"])
        _text(event["old_value"], "old_value", empty=True)
        if not isinstance(event["target_sha256"], str) or not _HEX.fullmatch(event["target_sha256"]):
            raise RevisionError("target_sha256 must be a lowercase SHA-256")
        if event['schema_version'] == 2:
            snapshot=event['target_snapshot']
            if not isinstance(snapshot,dict) or fingerprint(snapshot)!=event['target_sha256']:
                raise RevisionError('proposal target snapshot does not match its fingerprint')
            key=record_key(event['kind'],event['target_id'])
            if any(snapshot.get(k)!=v for k,v in key.items()) or snapshot.get(event['field'])!=event['old_value']:
                raise RevisionError('proposal target snapshot does not match its key/original value')
            if normalize_lines(event['value'])!=event['value']:
                raise RevisionError('format 2 proposed values must use LF line endings')
    _bytes(event)


def _ordered(events):
    try:
        result = list(events)
    except TypeError as exc:
        raise RevisionError("events must be an iterable of event objects") from exc
    for event in result:
        _validate_event(event)
    if len({e["id"] for e in result}) != len(result):
        raise RevisionError("duplicate event UUID")
    result.sort(key=lambda e: e["sequence"])
    if [e["sequence"] for e in result] != list(range(1, len(result) + 1)):
        raise RevisionError("journal sequence is duplicated or incomplete; one authoritative writer must append events. Exchange proposal drafts between clones, not journal files.")
    if any(_time(a["recorded_at"]) > _time(b["recorded_at"])
           for a, b in zip(result, result[1:])):
        raise RevisionError("journal time goes backwards")
    return result


def _operation(kind, field):
    _text(kind, "kind")
    _text(field, "field")
    if kind not in SUPPORTED or field not in SUPPORTED[kind]:
        raise RevisionError(f"unsupported revision operation: {kind!r}/{field!r}")


def _value(kind, field, value):
    _operation(kind, field)
    _text(value, "value", empty=field in {'caution','note','locator','provenance'})


def _target(tables, kind, target_id):
    key=record_key(kind,target_id)
    rows = [r for r in tables.get(kind, []) if all(r.get(k)==v for k,v in key.items())]
    if len(rows) != 1:
        raise RevisionError(f"target must identify exactly one {kind} row: {target_id}")
    return rows[0]


def _evidence(tables, references):
    known = {r.get("id") for r in tables.get("evidence", [])}
    if any(ref not in known for ref in references):
        raise RevisionError("unknown evidence reference; only existing evidence IDs are supported")


def _text_version(row):
    for name in ("id", "title", "language", "body", "body_sha256", "source_path",
                 "source_sha256", "locator", "transcription_status", "provenance"):
        _text(row.get(name), "text_version." + name,
              empty=name in {"locator", "transcription_status", "provenance"})
    if not _HEX.fullmatch(row["source_sha256"]):
        raise RevisionError("invalid original source_sha256")
    if row["body_sha256"] != hashlib.sha256(row["body"].encode("utf-8")).hexdigest():
        raise RevisionError("original text body hash does not match body")


def _check(tables, proposal, superseded, *, replay=False):
    row = _target(tables, proposal["kind"], proposal["target_id"])
    if proposal["field"] not in row:
        raise RevisionError("target field is absent")
    if proposal["kind"] == "text_version":
        _text_version(row)
        if proposal['field']=='body' and row["id"] in superseded:
            raise RevisionConflict("text version has an accepted successor; target that version explicitly")
    context_changed=fingerprint(row) != proposal['target_sha256']
    if row[proposal["field"]] != proposal["old_value"] or context_changed and not (replay and proposal['schema_version']==2):
        raise RevisionConflict(f"proposal {proposal['id']}: target no longer matches the proposal's original precondition; inspect its recorded context and create a fresh proposal rather than editing history")
    return row


def _next(events, by, reason, evidence):
    now = datetime.now(timezone.utc)
    if events:
        now = max(now, _time(events[-1]["recorded_at"]) + timedelta(microseconds=1))
    event_id = str(uuid.uuid4())
    if any(e["id"] == event_id for e in events):
        raise RevisionConflict("generated event UUID already exists")
    return {"format": FORMAT, "schema_version": SCHEMA_VERSION,
            "id": event_id, "sequence": len(events) + 1,
            "recorded_at": now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "by": _text(by, "by"), "reason": normalize_lines(_text(reason, "reason")),
            "evidence": list(evidence)}


def _superseded(events):
    proposals = {e["id"]: e for e in events if e["event_type"] == "proposal"}
    return {proposals[e["proposal_id"]]["target_id"] for e in events
            if e["event_type"] == "decision" and e["accept"]
            and e["proposal_id"] in proposals
            and proposals[e["proposal_id"]]["kind"] == "text_version"
            and proposals[e["proposal_id"]]['field'] == 'body'}


def propose(project, *, kind, target_id, field, value, by, reason, evidence=(),
            expected_sha256=None):
    """Persist a proposal for the current target, checking a supplied UI hash.

    An omitted expected_sha256 creates a proposal against the current snapshot;
    a supplied stale hash is never silently replaced by a new one.
    """
    _operation(kind, field)
    _text(target_id, "target_id")
    _value(kind, field, value)
    value=normalize_lines(value);reason=normalize_lines(_text(reason,'reason'))
    if not isinstance(evidence, (list, tuple)):
        raise RevisionError("evidence must be a list of existing evidence IDs")
    project = _project(project)
    with project_lock(project):
        from . import ingest  # local import: ingest invokes the pure apply()
        tables, _metadata = ingest.load(project, changes=True)
        events = _read_events(project)
        row = _target(tables, kind, target_id)
        target_id=record_id(kind,row)
        if field not in row:
            raise RevisionError("target field is absent")
        if kind == "text_version":
            _text_version(row)
            if field=='body' and target_id in _superseded(events):
                raise RevisionConflict("text version already has an accepted successor")
        digest = fingerprint(row)
        if expected_sha256 is not None and expected_sha256 != digest:
            raise RevisionConflict("supplied target hash is stale or invalid")
        if row[field] == value:
            raise RevisionError("proposal would make no change")
        event = _next(events, by, reason, evidence)
        event.update(event_type="proposal", kind=kind, target_id=target_id,
                     field=field, value=value, old_value=row[field], target_sha256=digest,
                     target_snapshot=deepcopy(row))
        _validate_event(event)
        _evidence(tables, event["evidence"])
        _publish(project, "edition/proposals", event)
    return event


def decide(project, proposal_id, *, accept, by, reason):
    """Record explicit acceptance or rejection; stale acceptance is refused."""
    _uuid(proposal_id, "proposal_id")
    if type(accept) is not bool:
        raise RevisionError("accept must explicitly be true or false")
    project = _project(project)
    with project_lock(project):
        from . import ingest
        tables, _metadata = ingest.load(project, changes=True)
        events = _read_events(project)
        proposals = {e["id"]: e for e in events if e["event_type"] == "proposal"}
        if proposal_id not in proposals:
            raise RevisionError("unknown proposal UUID")
        if any(e["event_type"] == "decision" and e["proposal_id"] == proposal_id for e in events):
            raise RevisionConflict("proposal already has a decision")
        proposal = proposals[proposal_id]
        event = _next(events, by, reason, proposal["evidence"])
        event.update(event_type="decision", proposal_id=proposal_id, accept=accept)
        _validate_event(event)
        if accept:
            row = _check(tables, proposal, _superseded(events))
            # Reuse the one-operation pure transformation for preflight. Do not
            # recursively call apply(), ingest.load(), propose(), or decide().
            candidate=deepcopy(tables)
            candidate_row=_target(candidate,proposal['kind'],proposal['target_id'])
            _project_one(candidate, proposal, event, candidate_row)
            # An accepted event must never strand the edition with invalid FKs,
            # statuses or alignment sides. Validate before publishing history.
            from . import database
            check=database.connect()
            try:
                database.migrate(check);database.insert_records(check,candidate)
            finally:check.close()
        _publish(project, "edition/changes", event)
    return event


def _derived(proposal_id, kind, detail=""):
    return "revision-" + kind + "-" + str(uuid.uuid5(uuid.UUID(proposal_id), kind + ":" + detail))


def _append(tables, table, row):
    if any(r.get("id") == row["id"] for r in tables.get(table, [])):
        raise RevisionConflict(f"new {table} identity already exists")
    tables.setdefault(table, []).append(row)


def _paragraphs(body):
    start = 0
    for end, next_start in [(m.start(), m.end()) for m in re.finditer(r"\r?\n[ \t]*\r?\n", body)] + [(len(body), len(body))]:
        a, b = start, end
        while a < b and body[a].isspace():
            a += 1
        while b > a and body[b - 1].isspace():
            b -= 1
        if a < b:
            yield a, b
        start = next_start


def _positions(body, excerpt):
    found, at = [], 0
    while True:
        at = body.find(excerpt, at)
        if at < 0:
            return found, False
        if len(found) == _MAX_CANDIDATES:
            return found, True
        found.append({"start": at, "end": at + len(excerpt)})
        at += 1


def _impact(decision, kind, entity_id, impact, metadata):
    return {"revision_id": decision["id"], "entity_kind": kind,
            "entity_id": entity_id, "impact": impact, "metadata_json": _json(metadata)}


def _key(row):
    return row["id"] if isinstance(row.get("id"), str) else _json(row)


def _references(tables, identifiers, decision, impact):
    result = []
    for table, rows in sorted(tables.items()):
        for row in rows:
            fields = {key: value for key, value in row.items()
                      if key != "id" and isinstance(value, str) and value in identifiers}
            if fields:
                result.append(_impact(decision, table, _key(row), impact,
                                      {"matched_identifier_fields": fields,
                                       "links_retained_on_original_records": True,
                                       "semantic_equivalence_asserted": False}))
    return result


def _new_text(tables, proposal, decision, old):
    _text_version(old)
    body = proposal["value"]
    version_id = _derived(proposal["id"], "text")
    analysis_id = _derived(proposal["id"], "analysis")
    document_id = _derived(proposal["id"], "unit", "document")
    original_analyses = [a["id"] for a in tables.get("analysis", []) if a.get("version_id") == old["id"]]
    old_units = [u for u in tables.get("unit", []) if u.get("version_id") == old["id"]]
    identifiers = {old["id"], *original_analyses, *(u["id"] for u in old_units)}
    impacts = _references(tables, identifiers, decision, "reanchoring_review_required")
    cache = {}
    for unit in old_units:
        a, b = unit.get("start"), unit.get("end")
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(old["body"]):
            raise RevisionError("original unit has invalid source bounds")
        excerpt = old["body"][a:b]
        if excerpt not in cache:
            cache[excerpt] = _positions(body, excerpt)
        candidates, truncated = cache[excerpt]
        state = "missing" if not candidates else "ambiguous" if len(candidates) > 1 or truncated else "unique"
        impacts.append(_impact(decision, "unit", unit["id"], "reanchor_" + state + "_candidate",
                               {"new_version_id": version_id, "candidates": candidates,
                                "candidates_truncated": truncated,
                                "automatic_reattachment": False,
                                "semantic_equivalence_asserted": False}))
    new = dict(old)
    new.update(id=version_id, body=body,
               body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
               source_path="edition/proposals/" + proposal["id"] + ".json",
               source_sha256=hashlib.sha256(_bytes(proposal)).hexdigest(),
               locator="body revision of " + old["id"],
               transcription_status="revision accepted; original source verification not inherited",
               provenance=_json({"proposal_id": proposal["id"], "decision_id": decision["id"],
                                 "previous_version_id": old["id"],
                                 "source_verification_inherited": False}))
    _text_version(new)
    _append(tables, "text_version", new)
    _append(tables, "analysis", {"id": analysis_id, "version_id": version_id,
                                "method": "mechanical paragraphs and written tokens; semantic links require review",
                                "scope": "entire revised body", "status": "proposed", "supersedes": None})
    units = [{"id": document_id, "analysis_id": analysis_id, "version_id": version_id,
              "kind": "document", "label": "revised text", "start": 0, "end": len(body),
              "parent_id": None, "note": "New version; no semantic equivalence or retained alignment asserted."}]
    for number, (a, b) in enumerate(_paragraphs(body), 1):
        paragraph_id = _derived(proposal["id"], "unit", f"paragraph:{a}:{b}")
        units.append({"id": paragraph_id, "analysis_id": analysis_id, "version_id": version_id,
                      "kind": "paragraph", "label": f"paragraph {number}", "start": a, "end": b,
                      "parent_id": document_id, "note": "Mechanical paragraph division; proposed analysis."})
        for word_number, (word_start, word_end) in enumerate(word_spans(body[a:b]), 1):
            x, y = a + word_start, a + word_end
            units.append({"id": _derived(proposal["id"], "unit", f"word:{x}:{y}"),
                          "analysis_id": analysis_id, "version_id": version_id, "kind": "word",
                          "label": f"p{number} word {word_number}", "start": x, "end": y,
                          "parent_id": paragraph_id, "note": "Mechanical written token; no linguistic segmentation review claimed."})
    for unit in units:
        _append(tables, "unit", unit)
    metadata = {"previous_version_id": old["id"], "new_version_id": version_id,
                "new_analysis_id": analysis_id, "previous_analysis_ids": original_analyses,
                "new_unit_count": len(units), "old_units_and_links_preserved": True,
                "automatic_reattachment": False, "semantic_equivalence_asserted": False,
                "source_verification_inherited": False}
    impacts.append(_impact(decision, "text_version", old["id"], "new_version_created", metadata))
    impacts.append(_impact(decision, "text_version", version_id, "revision_version", metadata))
    impacts.append(_impact(decision, "analysis", analysis_id, "new_proposed_analysis", metadata))
    return metadata, impacts


def _project_one(tables, proposal, decision, row):
    _value(proposal["kind"], proposal["field"], proposal["value"])
    if proposal["value"] == row[proposal["field"]]:
        raise RevisionError("proposal would make no change")
    if proposal["kind"] == "text_version" and proposal['field']=='body':
        return _new_text(tables, proposal, decision, row)
    impacts = _references(tables, {proposal["target_id"]}, decision, "interpretation_review_required")
    # Outgoing relationships also need attention: e.g. a changed rule does not
    # silently rewrite its associated recorded decision or renderings.
    outgoing = {v for k, v in row.items() if k.endswith("_id") and isinstance(v, str)}
    for table, rows in sorted(tables.items()):
        for related in rows:
            if related.get("id") in outgoing:
                impacts.append(_impact(decision, table, related["id"], "associated_record_review_required",
                                       {"changed_kind": proposal["kind"], "changed_id": proposal["target_id"],
                                        "not_automatically_rewritten": True}))
    row[proposal["field"]] = proposal["value"]
    if (proposal['kind'],proposal['field']) in {('lexeme','headword'),('lexeme_form','form')}:
        row['query_key']=proposal['value'].casefold()
    after=record_id(proposal['kind'],row)
    impacts.append(_impact(decision,proposal['kind'],after,'explicit_record_amendment',{'previous_target_id':proposal['target_id']}))
    return {"projection_only": True, "original_preserved_in_base_and_history": True, 'target_after_id':after}, impacts


def read_events(project):
    """Read and validate the immutable event journal without projecting data."""
    return _read_events(_project(project))


def apply(tables, events, *, materialize=None):
    """Purely project the complete journal, checking original preconditions.

    Input tables and events are not mutated. Pass the immutable base tables and
    ALL proposal/decision events exactly once, not an already projected copy.
    """
    if not isinstance(tables, dict) or any(not isinstance(rows, list) for rows in tables.values()):
        raise RevisionError("tables must map table names to row lists")
    if any(not isinstance(row, dict) for rows in tables.values() for row in rows):
        raise RevisionError("table rows must be dictionaries")
    projected = deepcopy(tables)
    if materialize:materialize(projected)
    proposals, decided, superseded = {}, set(), set()
    registered_context={}
    history, impacts = [], []
    for event in _ordered(events):
        _evidence(projected, event["evidence"])
        if event["event_type"] == "proposal":
            observed=_check(projected, event, superseded, replay=True)
            registered_context[event['id']]=fingerprint(observed)
            proposals[event["id"]] = event
            continue
        proposal_id = event["proposal_id"]
        if proposal_id not in proposals:
            raise RevisionError("decision precedes or lacks its proposal")
        if proposal_id in decided:
            raise RevisionError("proposal has more than one decision")
        decided.add(proposal_id)
        proposal = proposals[proposal_id]
        stale = False
        try:
            row = _check(projected, proposal, superseded, replay=True)
            if fingerprint(row)!=registered_context[proposal_id]:
                raise RevisionConflict(f"proposal {proposal_id}: target context changed after this proposal; create a fresh proposal")
        except RevisionConflict:
            if event["accept"]:
                raise
            stale = True
            row = None
        metadata = {"proposal_by": proposal["by"], "proposal_recorded_at": proposal["recorded_at"],
                    "proposal_reason": proposal["reason"], "target_sha256": proposal["target_sha256"],
                    "stale_at_decision": stale}
        context_changed=row is not None and fingerprint(row)!=proposal['target_sha256']
        metadata['context_changed_since_proposal']=context_changed
        if context_changed:
            metadata['original_target_snapshot']=proposal.get('target_snapshot')
            impacts.append(_impact(event,proposal['kind'],proposal['target_id'],'proposal_context_review_required',{'original_target_snapshot':proposal.get('target_snapshot'),'current_context':deepcopy(row)}))
        if event["accept"]:
            extra, affected = _project_one(projected, proposal, event, row)
            metadata.update(extra)
            impacts.extend(affected)
            if proposal["kind"] == "text_version" and proposal['field']=='body':
                superseded.add(proposal["target_id"])
            if materialize:materialize(projected)
        references = list(dict.fromkeys(proposal["evidence"] + event["evidence"]))
        history.append({"id": event["id"], "proposal_id": proposal_id,
                        "kind": proposal["kind"], "target_id": proposal["target_id"],
                        "field": proposal["field"], "old_value_json": _json(proposal["old_value"]),
                        "new_value_json": _json(proposal["value"]), "by_name": event["by"],
                        "reason": event["reason"], "evidence_json": _json(references),
                        "recorded_at": event["recorded_at"],
                        "status": "accepted" if event["accept"] else "rejected",
                        "metadata_json": _json(metadata)})
    # Composite keys in change_impact must remain unique even if an entity is
    # encountered through more than one exact identifier relationship.
    unique = {(r["revision_id"], r["entity_kind"], r["entity_id"], r["impact"]): r for r in impacts}
    return projected, {"revision_history": history, "change_impact": list(unique.values())}
