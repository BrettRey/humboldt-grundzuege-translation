"""Revision contract tests. All text and evidence below are synthetic."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from humboldt import revisions as rev


def fixture():
    def version(key, body):
        digest = hashlib.sha256(body.encode()).hexdigest()
        return dict(id=key, title="Synthetic text", language="en", body=body,
                    body_sha256=digest, source_path="source.txt", source_sha256=digest,
                    locator="synthetic", transcription_status="synthetic checked fixture",
                    provenance="unit test; no corpus material")
    return {
        "text_version": [version("fixed:old/version", "alpha beta alpha"), version("other", "omega")],
        "analysis": [dict(id="fixed-analysis", version_id="fixed:old/version", method="synthetic",
                          scope="whole", status="reviewed", supersedes=None),
                     dict(id="other-analysis", version_id="other", method="synthetic",
                          scope="whole", status="proposed", supersedes=None)],
        "unit": [dict(id="fixed-root", analysis_id="fixed-analysis", version_id="fixed:old/version",
                      kind="paragraph", label="old", start=0, end=16, parent_id=None, note=""),
                 dict(id="fixed-alpha", analysis_id="fixed-analysis", version_id="fixed:old/version",
                      kind="word", label="alpha", start=0, end=5, parent_id="fixed-root", note=""),
                 dict(id="fixed-beta", analysis_id="fixed-analysis", version_id="fixed:old/version",
                      kind="word", label="beta", start=6, end=10, parent_id="fixed-root", note=""),
                 dict(id="other-root", analysis_id="other-analysis", version_id="other",
                      kind="paragraph", label="other", start=0, end=5, parent_id=None, note="")],
        "evidence": [dict(id="ev-opaque", source_path="source.txt", source_sha256="a" * 64,
                          locator="synthetic", excerpt="alpha", statement="synthetic evidence",
                          quote_status="synthetic", claim_status="unverified")],
        "decision": [dict(id="fixed-decision", question="synthetic question", resolution="old resolution",
                          authority="synthetic author", status="provisional")],
        "lexeme": [dict(id="fixed-lexeme", headword="synthetic", query_key="synthetic", kind="term",
                        scope="test", domains_json="[]", roles_json="[]")],
        "term_sense": [dict(id="fixed-sense", lexeme_id="fixed-lexeme", label="synthetic",
                            definition="old definition", rule="old rule", caution="old caution",
                            decision_id="fixed-decision")],
        "term_use": [dict(id="fixed-use", sense_id="fixed-sense", origin="fixture", label="test",
                          definition="use definition", rule="use rule", caution="")],
        "sense_rendering": [dict(sense_id="fixed-sense", rank=1, rendering="synthetic")],
        "alignment": [dict(id="fixed-alignment", left_version="fixed:old/version", right_version="other",
                           relation="synthetic comparison", note="test", status="proposed")],
        "alignment_member": [dict(alignment_id="fixed-alignment", side="left", unit_id="fixed-beta"),
                             dict(alignment_id="fixed-alignment", side="right", unit_id="other-root")],
        "unit_evidence": [dict(unit_id="fixed-beta", evidence_id="ev-opaque")],
        "unit_decision": [dict(unit_id="fixed-beta", decision_id="fixed-decision")],
    }


def proposal(tables, sequence=1, *, kind="term_sense", target="fixed-sense", field="rule", value="new rule"):
    row = next(r for r in tables[kind] if r["id"] == target)
    return dict(format=rev.FORMAT, schema_version=1, event_type="proposal", id=str(uuid.uuid4()),
                sequence=sequence, recorded_at=f"2026-01-01T00:00:00.{sequence:06d}Z",
                by="synthetic proposer", reason="synthetic reason", evidence=["ev-opaque"],
                kind=kind, target_id=target, field=field, value=value,
                old_value=row[field], target_sha256=rev.fingerprint(row))


def decision(p, sequence=2, *, accept=True):
    return dict(format=rev.FORMAT, schema_version=1, event_type="decision", id=str(uuid.uuid4()),
                sequence=sequence, recorded_at=f"2026-01-01T00:00:00.{sequence:06d}Z",
                by="synthetic decider", reason="explicit synthetic decision", evidence=list(p["evidence"]),
                proposal_id=p["id"], accept=accept)


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture()

    def test_acceptance_is_pure_attributed_and_deterministic(self):
        p = proposal(self.base)
        d = decision(p)
        before_tables, before_events = copy.deepcopy(self.base), copy.deepcopy([p, d])
        projected, meta = rev.apply(self.base, [d, p])  # file order is not chronology
        self.assertEqual(self.base, before_tables)
        self.assertEqual([p, d], before_events)
        self.assertEqual(projected["term_sense"][0]["rule"], "new rule")
        self.assertEqual(projected["decision"][0]["resolution"], "old resolution")
        self.assertEqual(meta["revision_history"][0]["by_name"], "synthetic decider")
        self.assertEqual(meta["revision_history"][0]["old_value_json"], '"old rule"')
        self.assertEqual(meta["revision_history"][0]["status"], "accepted")
        self.assertEqual((projected, meta), rev.apply(self.base, [p, d]))
        self.assertTrue(any(i["entity_kind"] == "decision" and i["entity_id"] == "fixed-decision"
                            and i["impact"] == "associated_record_review_required"
                            for i in meta["change_impact"]))

    def test_rejection_keeps_current_and_records_requested_change(self):
        p = proposal(self.base)
        projected, meta = rev.apply(self.base, [p, decision(p, accept=False)])
        self.assertEqual(projected, self.base)
        self.assertEqual(meta["change_impact"], [])
        self.assertEqual(meta["revision_history"][0]["status"], "rejected")
        self.assertEqual(meta["revision_history"][0]["new_value_json"], '"new rule"')

    def test_conflicting_original_preconditions_and_stale_rejection(self):
        a, b = proposal(self.base), proposal(self.base, 2, value="competing rule")
        accepted = decision(a, 3)
        with self.assertRaises(rev.RevisionConflict):
            rev.apply(self.base, [a, b, accepted, decision(b, 4)])
        projected, meta = rev.apply(self.base, [a, b, accepted, decision(b, 4, accept=False)])
        self.assertEqual(projected["term_sense"][0]["rule"], "new rule")
        self.assertTrue(json.loads(meta["revision_history"][-1]["metadata_json"])["stale_at_decision"])

    def test_rebased_or_tampered_proposal_is_not_trusted(self):
        p = proposal(self.base)
        p["old_value"] = "invented previous rule"
        with self.assertRaises(rev.RevisionConflict):
            rev.apply(self.base, [p, decision(p)])

    def test_chronology_gaps_duplicates_and_unknown_fields_fail(self):
        p = proposal(self.base)
        d = decision(p)
        bad_cases = []
        backwards = copy.deepcopy(d)
        backwards["recorded_at"] = "2025-01-01T00:00:00Z"
        bad_cases.append([p, backwards])
        prior = copy.deepcopy(d)
        prior["sequence"] = 1
        later = copy.deepcopy(p)
        later["sequence"] = 2
        later["recorded_at"] = d["recorded_at"]
        prior["recorded_at"] = p["recorded_at"]
        bad_cases.append([prior, later])
        bad_cases.append([p, decision(p, 3)])
        bad_cases.append([p, d, decision(p, 3)])
        bad_cases.append([p, p])
        extra = copy.deepcopy(p)
        extra["human_approved"] = True
        bad_cases.append([extra])
        for events in bad_cases:
            with self.subTest(events=events), self.assertRaises(rev.RevisionError):
                rev.apply(self.base, events)

    def test_unsupported_invalid_values_and_unknown_evidence(self):
        p = proposal(self.base)
        for replacement in ({"field": "authority"}, {"kind": ["decision"]},
                            {"value": ""}, {"evidence": ["missing"]}, {"by": ""}):
            bad = dict(p, **replacement)
            with self.subTest(replacement=replacement), self.assertRaises(rev.RevisionError):
                rev.apply(self.base, [bad])
        d = decision(p)
        d["accept"] = "true"
        with self.assertRaises(rev.RevisionError):
            rev.apply(self.base, [p, d])

    def test_all_supported_rule_definition_caution_and_resolution_fields(self):
        for kind, target, field, value in [
            ("term_sense", "fixed-sense", "definition", "new definition"),
            ("term_sense", "fixed-sense", "caution", ""),
            ("decision", "fixed-decision", "resolution", "new resolution"),
        ]:
            with self.subTest(field=field):
                p = proposal(self.base, kind=kind, target=target, field=field, value=value)
                projected, _ = rev.apply(self.base, [p, decision(p)])
                self.assertEqual(next(r for r in projected[kind] if r["id"] == target)[field], value)
                self.assertEqual(self.base[kind][0][field], p["old_value"])

    def test_body_edit_preserves_sources_old_versions_and_all_links(self):
        p = proposal(self.base, kind="text_version", target="fixed:old/version", field="body",
                     value="alpha beta alpha gamma\n\nδelta 🙂 e\u0301lan, l’esprit mother-in-law 42!")
        projected, meta = rev.apply(self.base, [p, decision(p)])
        old = next(v for v in projected["text_version"] if v["id"] == "fixed:old/version")
        self.assertEqual(old, self.base["text_version"][0])
        self.assertEqual(projected["alignment"], self.base["alignment"])
        self.assertEqual(projected["alignment_member"], self.base["alignment_member"])
        self.assertEqual(projected["unit_evidence"], self.base["unit_evidence"])
        self.assertEqual(projected["unit"][:4], self.base["unit"])
        new = projected["text_version"][-1]
        self.assertEqual(new["body_sha256"], hashlib.sha256(p["value"].encode()).hexdigest())
        self.assertEqual(new["source_sha256"], hashlib.sha256(rev._bytes(p)).hexdigest())
        self.assertIn(p["id"], new["source_path"])
        self.assertIn("not inherited", new["transcription_status"])
        self.assertEqual(projected["analysis"][-1]["status"], "proposed")
        self.assertIsNone(projected["analysis"][-1]["supersedes"])
        new_units = [u for u in projected["unit"] if u["version_id"] == new["id"]]
        words = [new["body"][u["start"]:u["end"]] for u in new_units if u["kind"] == "word"]
        self.assertEqual(words, ["alpha", "beta", "alpha", "gamma", "δelta", "e\u0301lan",
                                 "l’esprit", "mother-in-law", "42"])
        self.assertTrue(any(i["entity_id"] == new["id"] for i in meta["change_impact"]))

    def test_ambiguous_unique_missing_candidates_do_not_reattach(self):
        p = proposal(self.base, kind="text_version", target="fixed:old/version", field="body", value="alpha alpha gamma")
        projected, meta = rev.apply(self.base, [p, decision(p)])
        impacts = {(i["entity_id"], i["impact"]): json.loads(i["metadata_json"]) for i in meta["change_impact"]}
        alpha = impacts[("fixed-alpha", "reanchor_ambiguous_candidate")]
        self.assertEqual(len(alpha["candidates"]), 2)
        self.assertFalse(alpha["automatic_reattachment"])
        self.assertFalse(alpha["semantic_equivalence_asserted"])
        self.assertEqual(impacts[("fixed-beta", "reanchor_missing_candidate")]["candidates"], [])
        self.assertEqual(projected["alignment_member"], self.base["alignment_member"])
        p = proposal(self.base, kind="text_version", target="fixed:old/version", field="body", value="alpha beta alpha new")
        _, meta = rev.apply(self.base, [p, decision(p)])
        self.assertTrue(any(i["entity_id"] == "fixed-beta" and i["impact"] == "reanchor_unique_candidate" for i in meta["change_impact"]))

    def test_immutable_old_hash_does_not_allow_two_silent_text_successors(self):
        a = proposal(self.base, kind="text_version", target="fixed:old/version", field="body", value="alpha changed")
        b = proposal(self.base, 2, kind="text_version", target="fixed:old/version", field="body", value="other changed")
        with self.assertRaises(rev.RevisionConflict):
            rev.apply(self.base, [a, b, decision(a, 3), decision(b, 4)])

    def test_bad_original_hash_and_bounds_cannot_create_a_revision(self):
        for edit in (lambda b: b["text_version"][0].update(body_sha256="0" * 64),
                     lambda b: b["unit"][0].update(end=999)):
            base = copy.deepcopy(self.base)
            edit(base)
            p = proposal(base, kind="text_version", target="fixed:old/version", field="body", value="new body")
            with self.assertRaises(rev.RevisionError):
                rev.apply(base, [p, decision(p)])

    def test_projected_rows_fit_database_and_old_reading_remains_queryable(self):
        from humboldt import database
        p = proposal(self.base, kind="text_version", target="fixed:old/version", field="body", value="alpha beta alpha gamma")
        projected, meta = rev.apply(self.base, [p, decision(p)])
        projected.update(meta)
        db = database.connect()
        try:
            database.migrate(db)
            database.insert_records(db, projected)
            self.assertEqual(db.execute("SELECT body FROM text_version WHERE id=?", ("fixed:old/version",)).fetchone()[0], "alpha beta alpha")
            self.assertEqual(db.execute("SELECT count(*) FROM text_version").fetchone()[0], 3)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            db.close()


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.base = fixture()
        (self.project / "source.txt").write_text("immutable synthetic source")
        self.source_before = (self.project / "source.txt").read_bytes()
        def load(project, *, changes=True):
            self.assertTrue((Path(project) / ".humboldt.lock").exists())
            events = rev._read_events(Path(project)) if changes else []
            return rev.apply(self.base, events)
        patcher = mock.patch("humboldt.ingest.load", side_effect=load)
        patcher.start()
        self.addCleanup(patcher.stop)

    def propose(self, **overrides):
        args = dict(kind="term_sense", target_id="fixed-sense", field="rule", value="new rule",
                    by="synthetic author", reason="synthetic reason", evidence=["ev-opaque"])
        args.update(overrides)
        return rev.propose(self.project, **args)

    def decide(self, p, accept=True):
        return rev.decide(self.project, p["id"], accept=accept, by="explicit synthetic decider", reason="explicit reason")

    def test_append_only_files_uuid_sequence_and_explicit_attribution(self):
        p = self.propose()
        path = self.project / "edition/proposals" / (p["id"] + ".json")
        before = path.read_bytes()
        self.assertEqual(str(uuid.UUID(p["id"])), p["id"])
        self.assertEqual(before, rev._bytes(p))
        d = self.decide(p)
        self.assertEqual(d["sequence"], 2)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(rev.RevisionConflict):
            self.decide(p, accept=False)
        self.assertEqual((self.project / "source.txt").read_bytes(), self.source_before)
        self.assertFalse((self.project / ".humboldt.lock").exists())

    def test_stale_ui_hash_and_invalid_content_write_no_events(self):
        cases = [dict(expected_sha256="0" * 64), dict(value=""), dict(evidence=["missing"]),
                 dict(by=""), dict(reason=""), dict(kind="evidence"), dict(value="bad\x00text")]
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(rev.RevisionError):
                self.propose(**overrides)
        self.assertEqual(list(self.project.glob("edition/**/*.json")), [])

    def test_stale_acceptance_fails_but_explicit_rejection_is_saved(self):
        a, b = self.propose(), self.propose(value="other rule")
        self.decide(a)
        with self.assertRaises(rev.RevisionConflict):
            self.decide(b)
        self.assertEqual(len(list(self.project.glob("edition/changes/*.json"))), 1)
        self.decide(b, accept=False)
        _, meta = rev.apply(self.base, rev._read_events(self.project))
        self.assertTrue(json.loads(meta["revision_history"][-1]["metadata_json"])["stale_at_decision"])

    def test_current_hash_can_propose_again_without_rewriting_originals(self):
        a = self.propose()
        self.decide(a)
        current, _ = rev.apply(self.base, rev._read_events(self.project))
        p = self.propose(value="newer rule", expected_sha256=rev.fingerprint(current["term_sense"][0]))
        self.assertEqual(p["old_value"], "new rule")
        self.assertEqual(self.base["term_sense"][0]["rule"], "old rule")

    def test_superseded_text_requires_explicit_new_version_target(self):
        a = self.propose(kind="text_version", target_id="fixed:old/version", field="body", value="new body")
        self.decide(a)
        with self.assertRaises(rev.RevisionConflict):
            self.propose(kind="text_version", target_id="fixed:old/version", field="body", value="another body")
        projected, _ = rev.apply(self.base, rev._read_events(self.project))
        new_id = projected["text_version"][-1]["id"]
        p = self.propose(kind="text_version", target_id=new_id, field="body", value="another body")
        self.decide(p)
        current, _ = rev.apply(self.base, rev._read_events(self.project))
        self.assertEqual(len(current["text_version"]), 4)

    def test_project_lock_never_deletes_an_existing_or_replaced_lock(self):
        lock = self.project / ".humboldt.lock"
        lock.write_text("another writer, possibly stale")
        with self.assertRaises(rev.ProjectLocked):
            self.propose()
        self.assertEqual(lock.read_text(), "another writer, possibly stale")
        lock.unlink()
        with rev.project_lock(self.project):
            with self.assertRaises(rev.ProjectLocked):
                with rev.project_lock(self.project):
                    self.fail("nested writer acquired lock")
            lock.write_text("replaced by external owner")
        self.assertEqual(lock.read_text(), "replaced by external owner")

    def test_uuid_collision_and_atomic_publication_failure_do_not_overwrite(self):
        p = self.propose()
        original = (self.project / "edition/proposals" / (p["id"] + ".json")).read_bytes()
        with mock.patch.object(rev.uuid, "uuid4", return_value=uuid.UUID(p["id"])):
            with self.assertRaises(rev.RevisionConflict):
                self.decide(p)
        self.assertEqual((self.project / "edition/proposals" / (p["id"] + ".json")).read_bytes(), original)
        with mock.patch.object(rev.os, "link", side_effect=OSError("synthetic atomic publish failure")):
            with self.assertRaises(OSError):
                self.propose(value="different")
        self.assertEqual(len(list(self.project.glob("edition/**/*.json"))), 1)
        self.assertEqual(list(self.project.glob("edition/**/.revision-*.tmp")), [])
        self.assertFalse((self.project / ".humboldt.lock").exists())


if __name__ == "__main__":
    unittest.main()
