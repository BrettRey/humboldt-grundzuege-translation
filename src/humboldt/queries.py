"""Read-only, JSON-safe interrogation of an edition database.

Span overlap is evidence of context, not proof that an annotation or translation
is an exact semantic equivalent. Public results keep that distinction explicit.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict


class NotFound(LookupError):
    """The requested durable identifier is absent from this database."""


KINDS = {
    "lexeme": "lexeme", "term": "lexeme", "sense": "term_sense",
    "term_sense": "term_sense", "term_use": "term_use",
    "attestation": "sense_attestation", "sense_attestation": "sense_attestation",
    "evidence": "evidence", "decision": "decision", "unit": "unit",
    "text_version": "text_version", "version": "text_version",
    "analysis": "analysis", "alignment": "alignment", "term_entry": "term_entry",
    "composite_attestation": "composite_attestation",
    "revision": "revision_history", "revision_history": "revision_history",
    "sense_rendering": "sense_rendering", "lexeme_form": "lexeme_form",
    "alignment_member": "alignment_member",
}


def _rows(db, sql, parameters=()):
    cursor = db.execute(sql, parameters)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _one(db, sql, parameters=()):
    rows = _rows(db, sql, parameters)
    return rows[0] if rows else None


def _has(db, table):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type IN ('table','view')", (table,)).fetchone())


def _json(value, default=None):
    if value is None:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default


def _by_ids(db, table, column, values):
    # Only internal, fixed table/column names reach this helper.
    values = list(dict.fromkeys(values))
    if not values or not _has(db, table):
        return []
    result = []
    for offset in range(0, len(values), 200):
        group = values[offset:offset + 200]
        result.extend(_rows(db, f'SELECT * FROM "{table}" WHERE "{column}" IN ({",".join("?" for _ in group)})', group))
    return result


def _unit(db, unit_id):
    return _one(db, "SELECT u.*, substr(v.body,u.start+1,u.end-u.start) AS text, v.language, v.title AS version_title FROM unit u JOIN text_version v ON v.id=u.version_id WHERE u.id=?", (unit_id,))


def _spatial(selected, annotation):
    if selected["version_id"] != annotation["version_id"]:
        return "linked_context"
    a, b = selected["start"], selected["end"]
    c, d = annotation["start"], annotation["end"]
    if a == c and b == d:
        return "exact_span"
    if c <= a and d >= b:
        return "containing_context"
    if a <= c and b >= d:
        return "contained_annotation"
    return "overlapping_context"


def _annotations(db, unit):
    links = []
    for table, column in (("unit_decision", "unit_id"), ("unit_evidence", "unit_id"), ("alignment_member", "unit_id"), ("term_occurrence", "unit_id"), ("term_expression_part", "unit_id")):
        if _has(db, table):
            links.append(f'EXISTS (SELECT 1 FROM {table} z WHERE z.{column}=u.id)')
    if _has(db, "sense_attestation"):
        links.append("EXISTS (SELECT 1 FROM sense_attestation z WHERE u.id IN (z.checked_context_unit,z.checked_expression_unit,z.ocr_context_unit,z.source_page_unit))")
    keep = "u.kind NOT IN ('word','written_word_candidate')"
    if links:
        keep += " OR " + " OR ".join(links)
    return _rows(db, f"SELECT u.*, substr(v.body,u.start+1,u.end-u.start) AS text, v.language, v.title AS version_title FROM unit u JOIN text_version v ON v.id=u.version_id WHERE u.version_id=? AND u.start<? AND u.end>? AND u.id<>? AND ({keep}) ORDER BY u.start,u.end,u.id", (unit["version_id"], unit["end"], unit["start"], unit["id"]))


def _evidence(db, evidence_id):
    row = _one(db, "SELECT * FROM evidence WHERE id=?", (evidence_id,)) if _has(db, "evidence") else None
    if row and _has(db, "evidence_detail"):
        detail = _one(db, "SELECT metadata_json FROM evidence_detail WHERE evidence_id=?", (evidence_id,))
        row["detail"] = _json(detail["metadata_json"], {}) if detail else {}
    return row


def _history(db, targets, kind=None):
    if not _has(db, "revision_history"):
        return {"available": False, "revisions": [], "impacts": [], "note": "This snapshot has no revision-history tables; this does not establish that no earlier revision occurred."}
    revisions = _by_ids(db, "revision_history", "target_id", targets)
    impacts = _by_ids(db, "change_impact", "entity_id", targets)
    if kind:
        revisions = [r for r in revisions if r.get("kind") == kind]
        impacts = [r for r in impacts if r.get("entity_kind") == kind]
    revisions += _by_ids(db, "revision_history", "id", [r["revision_id"] for r in impacts])
    unique = {r["id"]: r for r in revisions}
    result = []
    for row in sorted(unique.values(), key=lambda r: (r.get("recorded_at", ""), r["id"])):
        row = dict(row)
        for key in ("old_value", "new_value", "evidence", "metadata"):
            row[key] = _json(row.get(key + "_json"), None)
        result.append(row)
    return {"available": True, "revisions": result, "impacts": impacts}


def _sense(db, row):
    result = dict(row)
    result["renderings"] = _rows(db, "SELECT sense_id,rank,rendering FROM sense_rendering WHERE sense_id=? ORDER BY rank", (row["id"],)) if _has(db, "sense_rendering") else []
    result["uses"] = _by_ids(db, "term_use", "sense_id", [row["id"]])
    result["attestations"] = _by_ids(db, "sense_attestation", "sense_id", [row["id"]])
    for attestation in result["attestations"]:
        attestation["evidence"] = _evidence(db, attestation["evidence_id"])
        attestation["expression_parts"] = _by_ids(db, "term_expression_part", "attestation_id", [attestation["id"]])
        attestation["composite_memberships"] = _by_ids(db, "composite_member", "attestation_id", [attestation["id"]])
    result["composites"] = _by_ids(db, "composite_attestation", "sense_id", [row["id"]])
    for composite in result["composites"]:
        composite["members"] = _by_ids(db, "composite_member", "group_id", [composite["id"]])
    return result


def entity(db, kind, id):
    """Retrieve an allowlisted entity. ``record`` is the unmodified SQL row.

    Keeping the raw row separate permits conservative revision fingerprints;
    decoded display metadata and history must never enter that fingerprint.
    """
    table = KINDS.get(kind)
    if not table:
        raise ValueError("Unknown entity kind: " + str(kind))
    if not _has(db, table):
        raise NotFound(f"Entity kind {table} is unavailable in this snapshot")
    from .records import record_key,record_id
    key=record_key(table,str(id))
    where=' AND '.join('"'+k+'"=?' for k in key)
    row = _one(db, f'SELECT * FROM "{table}" WHERE '+where, tuple(key.values()))
    if not row:
        raise NotFound(f"No {table} with identifier {id}")
    out = {"kind": table, "record": row, 'identifier':record_id(table,row)}
    targets = [record_id(table,row)]
    if table == "unit":
        out["trace"] = trace(db, id)
    elif table == "lexeme":
        out["forms"] = _by_ids(db, "lexeme_form", "lexeme_id", [id])
        out["senses"] = [_sense(db, s) for s in _by_ids(db, "term_sense", "lexeme_id", [id])]
        out["relations"] = _by_ids(db, "term_relation", "lexeme_id", [id])
        out["controls"] = []
        for link in _by_ids(db, "lexeme_control", "lexeme_id", [id]):
            control = _one(db, "SELECT * FROM terminology_control WHERE id=?", (link["control_id"],))
            out["controls"].append({**link, "control": _json(control["metadata_json"], {}) if control else None})
        out["domains"] = _json(row.get("domains_json"), [])
        out["roles"] = _json(row.get("roles_json"), [])
        targets += [s["id"] for s in out["senses"]]
    elif table == "term_sense":
        out["sense"] = _sense(db, row)
    elif table == "decision":
        out["evidence"] = [_evidence(db, r["evidence_id"]) for r in _by_ids(db, "decision_evidence", "decision_id", [id])]
        out["units"] = _by_ids(db, "unit_decision", "decision_id", [id])
    elif table == "evidence":
        out["evidence"] = _evidence(db, id)
    elif table == "text_version":
        out["analyses"] = _by_ids(db, "analysis", "version_id", [id])
        out["blocks"] = _blocks(db, id)
        out['successors']=[]
        if _has(db,'revision_history'):
            for revision in _rows(db,"SELECT * FROM revision_history WHERE kind='text_version' AND field='body' AND target_id=? AND status='accepted'",(id,)):
                successor=_json(revision['metadata_json'],{}).get('new_version_id')
                if successor:out['successors']+=_by_ids(db,'text_version','id',[successor])
        out['predecessor_id']=_json(row.get('provenance'),{}).get('previous_version_id') if row.get('provenance','').startswith('{') else None
    elif table == "alignment":
        out["members"] = _alignment_members(db, id)
    elif table == "composite_attestation":
        out["members"] = _by_ids(db, "composite_member", "group_id", [id])
    elif table == "term_entry":
        out["forms"] = _json(row.get("forms_json"), [])
        out["candidates"] = _json(row.get("candidates_json"), [])
        out["evidence"] = [_evidence(db, r["evidence_id"]) for r in _by_ids(db, "term_entry_evidence", "entry_id", [id])]
        out["families"] = _by_ids(db, "term_entry_family", "entry_id", [id])
    out["history"] = _history(db, targets, None if table == "lexeme" else table)
    return out


def _alignment_members(db, alignment_id):
    rows = _by_ids(db, "alignment_member", "alignment_id", [alignment_id])
    return [{**r, "unit": _unit(db, r["unit_id"])} for r in rows]


def _alignments(db, unit_ids):
    links = _by_ids(db, "alignment_member", "unit_id", unit_ids)
    records = _by_ids(db, "alignment", "id", [r["alignment_id"] for r in links])
    return [{**r, "members": _alignment_members(db, r["id"])} for r in sorted(records, key=lambda r: r["id"])]


def trace(db, unit_id):
    """Trace a span through ancestry, overlapping annotations and alignments.

    Sibling annotations are deliberately searched by interval. In particular,
    a written word need not be the child of a term annotation to expose that
    annotation's decision. Alignment-derived links always remain contextual.
    """
    selected = _unit(db, str(unit_id))
    if selected is None:
        raise NotFound("No unit with identifier " + str(unit_id))
    ancestors, seen, parent = [], {selected["id"]}, selected.get("parent_id")
    while parent:
        if parent in seen:
            raise ValueError("Cyclic unit ancestry at " + parent)
        seen.add(parent)
        row = _unit(db, parent)
        if row is None:
            raise ValueError("Missing parent unit " + parent)
        ancestors.append(row)
        parent = row.get("parent_id")
    annotations = _annotations(db, selected)
    roles = {selected["id"]: {"unit_id": selected["id"], "scope": "exact", "relation": "selected", "via": "selected"}}
    for row in ancestors + annotations:
        relation = _spatial(selected, row)
        roles.setdefault(row["id"], {"unit_id": row["id"], "scope": "exact" if relation == "exact_span" else "context", "relation": relation, "via": "overlap_or_ancestry"})
    first_alignments = _alignments(db, roles)
    counterpart_rows = {}
    for alignment in first_alignments:
        for member in alignment["members"]:
            row = member["unit"]
            if row and row["version_id"] != selected["version_id"]:
                counterpart_rows[row["id"]] = row
                for context in [row] + _annotations(db, row):
                    roles.setdefault(context["id"], {"unit_id": context["id"], "scope": "context", "relation": "aligned_context", "via": alignment["id"]})
    alignments = _alignments(db, roles)
    decision_links = _by_ids(db, "unit_decision", "unit_id", roles)
    evidence_links = _by_ids(db, "unit_evidence", "unit_id", roles)
    terms = []
    attestations = {}
    for column in ("checked_context_unit", "checked_expression_unit", "ocr_context_unit", "source_page_unit"):
        for row in _by_ids(db, "sense_attestation", column, roles):
            attestations[row["id"]] = row
    for part in _by_ids(db, "term_expression_part", "unit_id", roles):
        for row in _by_ids(db, "sense_attestation", "id", [part["attestation_id"]]):
            attestations[row["id"]] = row
    for attestation in attestations.values():
        parts = _by_ids(db, "term_expression_part", "attestation_id", [attestation["id"]])
        expression_ids = [attestation.get("checked_expression_unit")] + [p["unit_id"] for p in parts]
        direct = []
        for expression_id in filter(None, expression_ids):
            row = _unit(db, expression_id)
            if row and row["version_id"] == selected["version_id"] and row["start"] < selected["end"] and row["end"] > selected["start"]:
                direct.append({"unit_id": expression_id, "relation": _spatial(selected, row)})
        scope = "exact" if any(link["relation"] == "exact_span" for link in direct) else "context"
        sense = _one(db, "SELECT * FROM term_sense WHERE id=?", (attestation["sense_id"],))
        lexeme = _one(db, "SELECT * FROM lexeme WHERE id=?", (sense["lexeme_id"],)) if sense else None
        terms.append({"scope": scope, "match": "exact_attested_expression" if scope == "exact" else "attested_expression_overlap" if direct else "attestation_context", "expression_links": direct, "attestation": attestation, "sense": sense, "lexeme": lexeme})
        evidence_links.append({"evidence_id": attestation["evidence_id"], "unit_id": attestation.get("checked_expression_unit") or attestation["checked_context_unit"], "scope": scope, "via": "sense_attestation"})
        if sense and sense.get("decision_id"):
            decision_links.append({"decision_id": sense["decision_id"], "unit_id": selected["id"], "scope": scope, "via": "sense_attestation"})
    families = []
    entry_ids = []
    occurrences = _by_ids(db, "term_occurrence", "unit_id", roles)
    for occurrence in occurrences:
        families.append({**occurrence, **roles[occurrence["unit_id"]], "family": _one(db, "SELECT * FROM term_family WHERE id=?", (occurrence["family_id"],))})
        entry_ids += [r["entry_id"] for r in _by_ids(db, "term_entry_family", "family_id", [occurrence["family_id"]])]
    entries = [entity(db, "term_entry", i) for i in sorted(set(entry_ids))]
    for entry in entries:
        decision_links.append({"decision_id": entry["record"]["decision_id"], "unit_id": selected["id"], "scope": "context", "via": "term_family"})
    decisions = []
    for decision in _by_ids(db, "decision", "id", [r["decision_id"] for r in decision_links]):
        links = []
        for link in decision_links:
            if link["decision_id"] == decision["id"]:
                links.append({**roles.get(link["unit_id"], {}), **link})
        decisions.append({**decision, "links": links})
        for link in _by_ids(db, "decision_evidence", "decision_id", [decision["id"]]):
            evidence_links.append({"evidence_id": link["evidence_id"], "scope": "context", "via": "decision", "decision_id": decision["id"]})
    evidence = []
    for evidence_id in sorted({r["evidence_id"] for r in evidence_links}):
        record = _evidence(db, evidence_id)
        if record:
            links = [{**roles.get(r.get("unit_id"), {}), **r} for r in evidence_links if r["evidence_id"] == evidence_id]
            evidence.append({**record, "links": links})
    # Form lookup is discovery, never a sense assignment. This also exposes the
    # curated lexeme behind an older family annotation in an aligned passage.
    discoveries = []
    forms = {r["query_form"].casefold() for r in occurrences}
    if selected["kind"] in ("word", "term_expression", "term_occurrence"):
        forms.add(selected["text"].casefold())
    if forms and _has(db, "lexeme_form"):
        discovered = {r["lexeme_id"] for r in _rows(db, "SELECT lexeme_id,query_key,form FROM lexeme_form") if r["query_key"].casefold() in forms or r["form"].casefold() in forms}
        bound = {r["lexeme"]["id"] for r in terms if r["lexeme"]}
        discoveries = [{"lexeme_id": i, "scope": "context", "match": "form_discovery_not_sense_assignment"} for i in sorted(discovered - bound)]
    lexeme_ids = {r["lexeme"]["id"] for r in terms if r["lexeme"]} | {r["lexeme_id"] for r in discoveries}
    versions = {m["unit"]["version_id"] for a in alignments for m in a["members"] if m["unit"] and m["unit"]["version_id"] != selected["version_id"]}
    targets = list(roles) + [selected["version_id"]] + list(versions) + [r["id"] for r in decisions] + list(lexeme_ids) + [r["sense"]["id"] for r in terms if r["sense"]]
    return {"unit": selected, "analyses": _by_ids(db, "analysis", "version_id", [selected["version_id"]] + list(versions)), "ancestors": ancestors, "annotations": [{**row, **roles[row["id"]]} for row in annotations], "context_links": list(roles.values()), "aligned_context": list(counterpart_rows.values()), "decisions": decisions, "evidence": evidence, "terms": terms, "term_families": families, "term_entries": entries, "term_discoveries": discoveries, "term_objects": [entity(db, "lexeme", i) for i in sorted(lexeme_ids)], "alignments": alignments, "alternatives": _by_ids(db, "text_version", "id", versions), "history": _history(db, targets), "note": "Exact labels describe linked spans, not certified semantic equivalence. Containing, overlapping, aligned and form-discovery links remain contextual."}


def _match_span(body, needle, start=0):
    folded = body.casefold()
    index = folded.find(needle.casefold(), start)
    if index < 0:
        return None
    end = index + len(needle.casefold())
    position, first, last = 0, None, None
    for i, char in enumerate(body):
        next_position = position + len(char.casefold())
        if first is None and next_position > index:
            first = i
        if next_position >= end:
            last = i + 1
            break
        position = next_position
    return first, last, end


def _snippet(body, start, end, width=110):
    a, b = max(0, start - width), min(len(body), end + width)
    return ("…" if a else "") + body[a:b] + ("…" if b < len(body) else "")


def search(db, text, limit=30):
    """Literal Unicode-casefolded German/English search, without FTS writes."""
    if not isinstance(text, str) or not text.strip():
        return []
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("Search limit must be an integer from 1 to 200")
    needle = text.strip()
    if len(needle) > 500:
        raise ValueError("Search text must be 500 characters or fewer")
    folded = needle.casefold()
    term_results, sense_results, text_results = [], [], []
    if _has(db, "lexeme"):
        all_forms = defaultdict(list)
        for row in _rows(db, "SELECT * FROM lexeme_form") if _has(db, "lexeme_form") else []:
            all_forms[row["lexeme_id"]].append(row["form"])
        for row in _rows(db, "SELECT * FROM lexeme ORDER BY headword,id"):
            values = [row["headword"]] + all_forms[row["id"]]
            matches = [v for v in values if folded in v.casefold()]
            if matches:
                term_results.append({"kind": "lexeme", "id": row["id"], "label": row["headword"], "language": "de", "match_field": "headword/form", "matches": list(dict.fromkeys(matches)), "snippet": row["headword"], "exact_form": any(v.casefold() == folded for v in matches)})
        term_results.sort(key=lambda r: (not r["exact_form"], r["label"], r["id"]))
    if _has(db, "term_sense"):
        renderings = defaultdict(list)
        for row in _rows(db, "SELECT * FROM sense_rendering ORDER BY rank") if _has(db, "sense_rendering") else []:
            renderings[row["sense_id"]].append(row["rendering"])
        for row in _rows(db, "SELECT s.*,l.headword FROM term_sense s JOIN lexeme l ON l.id=s.lexeme_id ORDER BY l.headword,s.id"):
            fields = {"English rendering": " / ".join(renderings[row["id"]]), "definition": row["definition"], "rule": row["rule"], "caution": row["caution"]}
            for field, value in fields.items():
                match = _match_span(value, needle)
                if match:
                    sense_results.append({"kind": "term_sense", "id": row["id"], "lexeme_id": row["lexeme_id"], "label": row["headword"] + " — " + row["label"], "language": "en", "match_field": field, "snippet": _snippet(value, *match[:2]), "renderings": renderings[row["id"]], "exact_form": field == "English rendering" and any(v.casefold() == folded for v in renderings[row["id"]]), "rendering_rank": next((i for i,v in enumerate(renderings[row["id"]],1) if v.casefold()==folded), 999)})
                    break
    if _has(db, "text_version"):
        by_version = []
        for version in _rows(db, "SELECT * FROM text_version ORDER BY CASE WHEN transcription_status LIKE '%uncorrected%' THEN 1 ELSE 0 END,language,id"):
            matches, offset = [], 0
            for _ in range(min(limit, 5)):
                match = _match_span(version["body"], needle, offset)
                if not match:
                    break
                a, b, offset = match
                unit = _one(db, "SELECT id,kind FROM unit WHERE version_id=? AND start<=? AND end>=? ORDER BY (end-start), CASE kind WHEN 'word' THEN 0 WHEN 'term_expression' THEN 1 WHEN 'phrase' THEN 2 WHEN 'sentence' THEN 3 WHEN 'rendering' THEN 3 WHEN 'paragraph' THEN 4 ELSE 5 END,id LIMIT 1", (version["id"], a, b))
                matches.append({"kind": "text_version", "id": version["id"], "label": version["title"], "language": version["language"], "match_field": "embedded text", "snippet": _snippet(version["body"], a, b), "match_start": a, "match_end": b, "unit_id": unit["id"] if unit else None, "locator": version["locator"], "transcription_status": version["transcription_status"]})
            by_version.append(matches)
        while any(by_version):
            for matches in by_version:
                if matches:
                    text_results.append(matches.pop(0))
    # Exact lexical/rendering matches precede incidental prose. Other channels
    # retain bounded visibility; an English text hit is never a sense assignment.
    exact = [r for r in term_results + sense_results if r.get("exact_form")]
    exact.sort(key=lambda r: (r["kind"] != "lexeme", r.get("rendering_rank", 0), r["label"], r["id"]))
    curated = [r for r in term_results + sense_results if not r.get("exact_form")]
    curated.sort(key=lambda r: (r["match_field"] not in ("headword/form", "English rendering"), r["label"], r["id"]))
    return (exact + curated + text_results)[:limit]



def _section_numbers(db):
    versions = _rows(db, "SELECT id,title,language,locator,transcription_status FROM text_version ORDER BY id")
    by_id = {v["id"]: set(re.findall(r"§\s*(\d+)\b", v["title"])) for v in versions}
    for row in _rows(db, "SELECT DISTINCT version_id,label FROM unit WHERE kind='paragraph'"):
        number = re.fullmatch(r"\s*§\s*(\d+)\s*", row["label"])
        if number and not by_id.get(row['version_id']):
            by_id.setdefault(row["version_id"], set()).add(number[1])
    declared = metadata(db).get("passages", [])
    for passage_info in declared if isinstance(declared, list) else []:
        if not isinstance(passage_info, dict):
            continue
        section = str(passage_info.get("section", "")).strip().removeprefix("§").strip()
        version_ids = passage_info.get("version_ids", [])
        if re.fullmatch(r"\d{1,6}", section) and isinstance(version_ids, list):
            for version_id in version_ids:
                if isinstance(version_id, str) and version_id in by_id:
                    by_id[version_id].add(section)
    return versions, by_id


def sections(db):
    """Discover explicit passage metadata plus legacy title/paragraph labels."""
    versions, numbers = _section_numbers(db)
    groups = defaultdict(list)
    for version in versions:
        for number in numbers[version["id"]]:
            groups[number].append(version)
    return [{"section": number, "label": "§" + number, "versions": groups[number]} for number in sorted(groups, key=int)]


def _blocks(db, version_id):
    units = _rows(db, "SELECT u.*, substr(v.body,u.start+1,u.end-u.start) AS text FROM unit u JOIN text_version v ON v.id=u.version_id WHERE u.version_id=? AND u.kind IN ('rendering','sentence','paragraph','excerpt') ORDER BY u.start,u.end,u.id", (version_id,))
    for kind in ("rendering", "sentence", "paragraph", "excerpt"):
        chosen = [u for u in units if u["kind"] == kind]
        if chosen:
            break
    else:
        version = _one(db, "SELECT body FROM text_version WHERE id=?", (version_id,))
        return [{"id": None, "version_id": version_id, "kind": "unsegmented text", "label": "Embedded text; no recorded segmentation", "start": 0, "end": len(version["body"]), "text": version["body"], "words": []}]
    words = _rows(db, "SELECT u.*,substr(v.body,u.start+1,u.end-u.start) AS text FROM unit u JOIN text_version v ON v.id=u.version_id WHERE u.version_id=? AND u.kind IN ('word','written_word_candidate') ORDER BY u.start,u.end,u.id", (version_id,))
    result, spans = [], set()
    for block in chosen:
        span = block["start"], block["end"]
        if span in spans:
            continue
        spans.add(span)
        block["words"] = [w for w in words if block["start"] <= w["start"] and w["end"] <= block["end"]]
        result.append(block)
    return result


def passage(db, section):
    value = str(section).strip().removeprefix("§").strip()
    if not re.fullmatch(r"\d{1,6}", value):
        raise ValueError("Section must be a number, for example 147 or §147")
    versions, numbers = _section_numbers(db)
    selected = [v for v in versions if value in numbers[v["id"]]]
    if not selected:
        raise NotFound("No recorded passage for §" + value)
    output = []
    for version_metadata in selected:
        row = _one(db, "SELECT * FROM text_version WHERE id=?", (version_metadata["id"],))
        output.append({**row, "analyses": _by_ids(db, "analysis", "version_id", [row["id"]]), "blocks": _blocks(db, row["id"]), "history": _history(db, [row["id"]], "text_version")})
    ids = {v["id"] for v in output}
    alignments = []
    if _has(db, "alignment"):
        for row in _rows(db, "SELECT * FROM alignment ORDER BY id"):
            if row["left_version"] in ids and row["right_version"] in ids:
                alignments.append({**row, "members": _alignment_members(db, row["id"])})
    defaults = next((r for r in metadata(db).get('reading_defaults', []) if r.get('section') == value), {})
    return {"section": value, "label": "§" + value, "versions": output, "alignments": alignments, "reading_defaults": defaults, "note": "Version selection is a reading choice, not acceptance or certification. Alignments retain their recorded relation and status."}


def metadata(db):
    return {r["key"]: _json(r["value_json"], r["value_json"]) for r in _rows(db, "SELECT * FROM build_metadata")} if _has(db, "build_metadata") else {}


def resources(db):
    """Return source references; filesystem authorization belongs to the reader."""
    records = []
    for table, sha in (("text_version", "source_sha256"), ("evidence", "source_sha256")):
        if _has(db, table):
            records.extend({"path": r["source_path"], "sha256": r[sha], "origin": table} for r in _rows(db, f'SELECT DISTINCT source_path,{sha} FROM {table}'))
    declared = metadata(db).get("resources", [])
    if isinstance(declared, list):
        records.extend({**r, "origin": "manifest"} for r in declared if isinstance(r, dict) and isinstance(r.get("path"), str))
    return records
