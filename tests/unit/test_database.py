"""Storage contract tests using only small, self-contained synthetic records."""

import copy
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from humboldt import database


def fixture():
    """One connected example across every scholarly/infrastructure data table."""
    sha = "a" * 64
    versions = [dict(id=key, title=key, language=language, body="alpha beta",
                     body_sha256=hashlib.sha256(b"alpha beta").hexdigest(),
                     source_path="fixture.txt", source_sha256=sha, locator="fixture",
                     transcription_status="synthetic", provenance="unit test")
                for key, language in (("g", "de"), ("e", "en"))]
    return {
        # Intentionally not dependency ordered. The child also precedes its
        # parent lexically and in the list; alignment starts already proposed.
        "change_impact": [dict(revision_id="h", entity_kind="term_sense", entity_id="s",
                               impact="review", metadata_json="{}")],
        "alignment_member": [dict(alignment_id="a", side="left", unit_id="a-child"),
                             dict(alignment_id="a", side="right", unit_id="e-parent")],
        "alignment": [dict(id="a", left_version="g", right_version="e", relation="test",
                           note="synthetic", status="proposed")],
        "unit": [dict(id="a-child", analysis_id="g1", version_id="g", kind="word", label="beta",
                      start=6, end=10, parent_id="z-parent", note=""),
                 dict(id="e-parent", analysis_id="e1", version_id="e", kind="paragraph", label="English",
                      start=0, end=10, parent_id=None, note=""),
                 dict(id="z-parent", analysis_id="g1", version_id="g", kind="paragraph", label="German",
                      start=0, end=10, parent_id=None, note="")],
        "analysis": [dict(id="g1", version_id="g", method="test", scope="test", status="proposed", supersedes="g0"),
                     dict(id="e1", version_id="e", method="test", scope="test", status="proposed", supersedes=None),
                     dict(id="g0", version_id="g", method="test", scope="test", status="proposed", supersedes=None)],
        "text_version": versions,
        "decision": [dict(id="d", question="test", resolution="beta", authority="synthetic", status="provisional")],
        "evidence": [dict(id="ev", source_path="fixture.txt", source_sha256=sha, locator="fixture",
                          excerpt="alpha beta", statement="synthetic", quote_status="synthetic", claim_status="unverified")],
        "evidence_detail": [dict(evidence_id="ev", metadata_json="{}")],
        "decision_evidence": [dict(decision_id="d", evidence_id="ev")],
        "unit_evidence": [dict(unit_id="a-child", evidence_id="ev")],
        "unit_decision": [dict(unit_id="a-child", decision_id="d")],
        "word_index": [dict(unit_id="a-child", query_form="beta", printed_page=1, pdf_page=2,
                            scan_leaf=3, zone="body", extraction="synthetic")],
        "term_family": [dict(id="f", label="synthetic", pattern="beta")],
        "term_occurrence": [dict(family_id="f", unit_id="a-child", query_form="beta", zone="body")],
        "term_entry": [dict(id="t", decision_id="d", forms_json='["beta"]', candidates_json='["beta"]',
                            rule="test", exceptions="", confidence="synthetic", limitation="synthetic")],
        "term_entry_evidence": [dict(entry_id="t", evidence_id="ev")],
        "term_entry_family": [dict(entry_id="t", family_id="f")],
        "preparation_input": [dict(path="fixture.json", sha256=sha)],
        "lexeme": [dict(id="l", headword="Beta", query_key="beta", kind="contextual", scope="synthetic",
                        domains_json="[]", roles_json="[]")],
        "lexeme_form": [dict(lexeme_id="l", form="beta", query_key="beta", form_role="synthetic")],
        "term_sense": [dict(id="s", lexeme_id="l", label="synthetic", definition="test", rule="beta",
                            caution="", decision_id="d")],
        "term_use": [dict(id="u", sense_id="s", origin="fixture-use", label="synthetic",
                          definition="test", rule="beta", caution="")],
        "sense_rendering": [dict(sense_id="s", rank=1, rendering="beta")],
        "sense_attestation": [dict(id="att", sense_id="s", use_id="u", evidence_id="ev",
                                   checked_context_unit="z-parent", checked_expression_unit="a-child",
                                   ocr_context_unit=None, source_page_unit="z-parent", printed_page=1,
                                   pdf_page=2, scan_leaf=3, term_form="beta", evidence_role="direct_occurrence",
                                   composite_group=None, text_layer="synthetic", issue="")],
        "term_expression_part": [dict(attestation_id="att", rank=1, unit_id="a-child", part_role="expression")],
        "composite_attestation": [dict(id="ca", lexeme_id="l", sense_id="s", joined_form="beta", method="synthetic")],
        "composite_member": [dict(group_id="ca", attestation_id="att", part_order=1)],
        "term_relation": [dict(lexeme_id="l", relation="synthetic", target_id="l", target_label="Beta", reason="test")],
        "terminology_control": [dict(id="c", metadata_json="{}")],
        "lexeme_control": [dict(lexeme_id="l", control_id="c", relation="synthetic", comment="test")],
        "terminology_candidate": [dict(id="tc", form="beta", occurrences=1, pages_json="[1]", header_only=0,
                                       reader="synthetic", disposition="included", target_id="l", reason="test")],
        "terminology_page_review": [dict(printed_page=1, reader="synthetic", metadata_json="{}")],
        "register_carry_forward": [dict(old_entry="t", old_label="beta", disposition="included", target_id="l", reason="test")],
        "revision_history": [dict(id="h", proposal_id="p", kind="term_sense", target_id="s", field="rule",
                                  old_value_json='"beta"', new_value_json='"gamma"', by_name="synthetic",
                                  reason="test", evidence_json="[]", recorded_at="2000-01-01T00:00:00Z",
                                  status="accepted", metadata_json="{}")],
        "build_metadata": [dict(key="fixture", value_json="true")],
    }


class DatabaseTests(unittest.TestCase):
    def fresh(self, version=None):
        db = database.connect()
        self.addCleanup(db.close)
        database.migrate(db, target=version)
        return db

    def populated(self):
        db = self.fresh()
        database.insert_records(db, fixture())
        return db

    def test_connection_and_packaged_v1_upgrade_preserve_schema_and_rows(self):
        db = self.fresh(1)
        self.assertIsInstance(db.execute("SELECT 1").fetchone(), sqlite3.Row)
        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        before = dict(db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name != 'schema_migration'"))
        base_tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} - {"schema_migration"}
        self.assertEqual(len(base_tables), 33)
        self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0], 12)
        database.insert_records(db, {"decision": [dict(id="old", question="q", resolution="r", authority="test", status="provisional")]})
        self.assertEqual(database.migrate(db), 2)
        for name, sql in before.items():
            self.assertEqual(db.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0], sql)
        self.assertEqual(db.execute("SELECT resolution FROM decision WHERE id='old'").fetchone()[0], "r")
        self.assertEqual(database.migrate(db), 2)
        history = list(db.execute("SELECT version, name, sha256 FROM schema_migration ORDER BY version"))
        for row in history:
            path = Path(database.__file__).with_name("migrations") / row[1]
            self.assertEqual(row[2], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_future_version_checksum_and_schema_drift_fail_before_mutation(self):
        with self.subTest("future version"):
            db = self.fresh(1)
            db.execute("PRAGMA user_version=999")
            with self.assertRaisesRegex(database.SchemaError, "future"):
                database.migrate(db)
        with self.subTest("future target"):
            with self.assertRaisesRegex(database.SchemaError, "unknown target"):
                database.migrate(self.fresh(), target=999)
        with self.subTest("checksum"):
            db = self.fresh(1)
            db.execute("UPDATE schema_migration SET sha256=?", ("0" * 64,))
            with self.assertRaisesRegex(database.SchemaError, "checksum"):
                database.migrate(db)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        for sql in ("CREATE TABLE unexpected(id TEXT)", "ALTER TABLE decision ADD COLUMN unexpected TEXT",
                    "DROP TRIGGER unit_bounds", "DROP VIEW unit_text"):
            with self.subTest(sql):
                db = self.fresh(1)
                db.execute(sql)
                with self.assertRaises(database.SchemaError):
                    database.migrate(db)
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_unversioned_nonempty_database_and_downgrade_are_rejected(self):
        db = database.connect()
        self.addCleanup(db.close)
        db.execute("CREATE TABLE unknown(id TEXT)")
        with self.assertRaisesRegex(database.SchemaError, "unversioned"):
            database.migrate(db)
        with self.assertRaisesRegex(database.SchemaError, "downgrade"):
            database.migrate(self.fresh(), target=1)

    def test_failed_upgrade_rolls_back_ddl_history_and_user_version(self):
        db = self.fresh(1)
        migrations = database._migrations()
        broken = "CREATE TABLE partial(id TEXT);\nINVALID SQL;\n"
        altered = (migrations[0], (2, migrations[1][1], broken, hashlib.sha256(broken.encode()).hexdigest()))
        with mock.patch.object(database, "_migrations", return_value=altered):
            with self.assertRaises(sqlite3.OperationalError):
                database.migrate(db)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT count(*) FROM schema_migration").fetchone()[0], 1)
        self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='partial'").fetchone())
        self.assertEqual(database.migrate(db), 2)

    def test_import_orders_parents_deferred_analysis_and_alignment_freeze(self):
        records = fixture()
        original = copy.deepcopy(records)
        db = self.fresh()
        database.insert_records(db, records)
        self.assertEqual(records, original)
        self.assertEqual(db.execute("SELECT text FROM unit_text WHERE id='a-child'").fetchone()[0], "beta")
        self.assertEqual(db.execute("SELECT status FROM alignment WHERE id='a'").fetchone()[0], "proposed")
        self.assertEqual(db.execute("SELECT supersedes FROM analysis WHERE id='g1'").fetchone()[0], "g0")
        self.assertEqual(database.report(db)["foreign_key_errors"], [])
        with self.assertRaisesRegex(sqlite3.IntegrityError, "frozen"):
            db.execute("DELETE FROM alignment_member WHERE alignment_id='a'")
        self.assertEqual(db.execute("PRAGMA defer_foreign_keys").fetchone()[0], 0)

    def test_import_rejects_incomplete_fk_bad_spans_and_incomplete_alignment_atomically(self):
        for mutate in (lambda x: x["unit"][0].update(parent_id="missing"),
                       lambda x: x["unit"][0].update(end=99),
                       lambda x: x["alignment_member"].pop(),
                       lambda x: x["change_impact"][0].update(revision_id="missing")):
            with self.subTest(mutate=mutate):
                db = self.fresh()
                records = fixture()
                mutate(records)
                with self.assertRaises(sqlite3.IntegrityError):
                    database.insert_records(db, records)
                self.assertEqual(db.execute("SELECT count(*) FROM text_version").fetchone()[0], 0)
                self.assertEqual(db.execute("PRAGMA defer_foreign_keys").fetchone()[0], 0)

    def test_import_rejects_cycles_duplicate_ids_and_untrusted_identifiers(self):
        records = fixture()
        records["unit"][2]["parent_id"] = "a-child"
        with self.assertRaisesRegex(ValueError, "cycle"):
            database.insert_records(self.fresh(), records)
        records = fixture()
        records["unit"].append(dict(records["unit"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            database.insert_records(self.fresh(), records)
        db = self.fresh()
        for bad in ({'decision; DROP TABLE decision; --': []},
                    {"decision": [{"id); DROP TABLE decision; --": "bad"}]},
                    {"schema_migration": [dict(version=3)]},
                    {"build_metadata": [dict(key="sealed", value_json="true")]}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    database.insert_records(db, bad)
        self.assertEqual(db.execute("SELECT count(*) FROM decision").fetchone()[0], 0)

    def test_seal_blocks_insert_update_delete_on_every_table_and_migration(self):
        db = self.populated()
        digest = database.logical_digest(db)
        database.seal(db)
        database.seal(db)
        summary = database.report(db)
        self.assertTrue(summary["sealed"])
        self.assertEqual(summary["integrity"], "ok")
        self.assertEqual(summary["foreign_key_errors"], [])
        self.assertEqual(digest, database.logical_digest(db))
        for table in summary["counts"]:
            self.assertGreater(summary["counts"][table], 0, table)
            column = db.execute(f'PRAGMA table_info("{table}")').fetchone()[1]
            for sql in (f'INSERT INTO "{table}" DEFAULT VALUES',
                        f'UPDATE "{table}" SET "{column}"="{column}"', f'DELETE FROM "{table}"'):
                with self.subTest(sql=sql):
                    with self.assertRaisesRegex(sqlite3.IntegrityError, "database is sealed"):
                        db.execute(sql)
        with self.assertRaisesRegex(database.SealedError, "sealed"):
            database.migrate(db)
        with self.assertRaises(database.SealedError):
            database.insert_records(db, {})

    def test_digest_is_order_path_build_metadata_and_migration_time_independent(self):
        first = self.populated()
        second = self.fresh()
        records = fixture()
        records = {table: list(reversed(rows)) for table, rows in reversed(list(records.items()))}
        database.insert_records(second, records)
        second.execute("UPDATE schema_migration SET applied_at='another construction time'")
        second.execute("INSERT INTO build_metadata VALUES ('logical_digest','\"not included\"')")
        second.execute("INSERT INTO build_metadata VALUES ('local_path','\"/other/machine\"')")
        self.assertEqual(database.logical_digest(first), database.logical_digest(second))
        second.execute("UPDATE revision_history SET recorded_at='2001-01-01T00:00:00Z'")
        self.assertNotEqual(database.logical_digest(first), database.logical_digest(second))

    def test_readonly_uses_uri_and_cannot_write_or_create_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "edition ?# space.sqlite"
            db = database.connect(path)
            database.migrate(db)
            database.insert_records(db, fixture())
            db.close()
            reader = database.connect(path, readonly=True)
            try:
                self.assertEqual(reader.execute("SELECT count(*) FROM text_version").fetchone()[0], 2)
                with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                    reader.execute("INSERT INTO build_metadata VALUES ('bad', 'true')")
            finally:
                reader.close()
            missing = Path(directory) / "missing.sqlite"
            with self.assertRaises(sqlite3.OperationalError):
                database.connect(missing, readonly=True)
            self.assertFalse(missing.exists())

    def test_existing_immutability_and_span_triggers_remain_active_before_sealing(self):
        db = self.populated()
        for sql in ("UPDATE text_version SET body='different' WHERE id='g'",
                    "DELETE FROM text_version WHERE id='g'",
                    "UPDATE unit SET start=1 WHERE id='z-parent'",
                    "DELETE FROM analysis WHERE id='g1'"):
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                    db.execute(sql)


if __name__ == "__main__":
    unittest.main()
