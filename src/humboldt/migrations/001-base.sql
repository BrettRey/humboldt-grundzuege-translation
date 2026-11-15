-- Version 1: exact scholarly schema from the read-only cumulative pilot.
-- Existing identifiers, columns, constraints, triggers and view are preserved.

CREATE TABLE alignment (
    id TEXT PRIMARY KEY NOT NULL,
    left_version TEXT NOT NULL REFERENCES text_version(id),
    right_version TEXT NOT NULL REFERENCES text_version(id),
    relation TEXT NOT NULL,
    note TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed'))
);

CREATE TABLE alignment_member (
    alignment_id TEXT NOT NULL REFERENCES alignment(id),
    side TEXT NOT NULL CHECK (side IN ('left', 'right')),
    unit_id TEXT NOT NULL REFERENCES unit(id),
    PRIMARY KEY (alignment_id, side, unit_id)
);

CREATE TABLE analysis (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES text_version(id),
    method TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed', 'reviewed')),
    supersedes TEXT,
    UNIQUE (id, version_id),
    FOREIGN KEY (supersedes, version_id) REFERENCES analysis(id, version_id)
);

CREATE TABLE composite_attestation (
          id TEXT PRIMARY KEY NOT NULL, lexeme_id TEXT NOT NULL REFERENCES lexeme(id),
          sense_id TEXT NOT NULL REFERENCES term_sense(id), joined_form TEXT NOT NULL, method TEXT NOT NULL);

CREATE TABLE composite_member (
          group_id TEXT NOT NULL REFERENCES composite_attestation(id),
          attestation_id TEXT NOT NULL REFERENCES sense_attestation(id), part_order INTEGER NOT NULL,
          PRIMARY KEY(group_id,part_order));

CREATE TABLE decision (
    id TEXT PRIMARY KEY NOT NULL,
    question TEXT NOT NULL,
    resolution TEXT NOT NULL,
    authority TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('provisional', 'adopted'))
);

CREATE TABLE decision_evidence (
    decision_id TEXT NOT NULL REFERENCES decision(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    PRIMARY KEY (decision_id, evidence_id)
);

CREATE TABLE evidence (
    id TEXT PRIMARY KEY NOT NULL,
    source_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL CHECK (length(source_sha256) = 64),
    locator TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    statement TEXT NOT NULL,
    quote_status TEXT NOT NULL,
    claim_status TEXT NOT NULL
);

CREATE TABLE evidence_detail (
                evidence_id TEXT PRIMARY KEY NOT NULL REFERENCES evidence(id),
                metadata_json TEXT NOT NULL);

CREATE TABLE lexeme (
          id TEXT PRIMARY KEY NOT NULL, headword TEXT NOT NULL, query_key TEXT UNIQUE NOT NULL,
          kind TEXT NOT NULL, scope TEXT NOT NULL, domains_json TEXT NOT NULL, roles_json TEXT NOT NULL);

CREATE TABLE lexeme_control (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), control_id TEXT NOT NULL REFERENCES terminology_control(id),
          relation TEXT NOT NULL, comment TEXT NOT NULL, PRIMARY KEY(lexeme_id,control_id));

CREATE TABLE lexeme_form (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), form TEXT NOT NULL, query_key TEXT NOT NULL, form_role TEXT NOT NULL,
          PRIMARY KEY(lexeme_id,form));

CREATE TABLE preparation_input (
                path TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL);

CREATE TABLE register_carry_forward (
          old_entry TEXT NOT NULL, old_label TEXT PRIMARY KEY NOT NULL,
          disposition TEXT NOT NULL, target_id TEXT REFERENCES lexeme(id), reason TEXT NOT NULL);

CREATE TABLE sense_attestation (
          id TEXT PRIMARY KEY NOT NULL, sense_id TEXT NOT NULL REFERENCES term_sense(id),
          use_id TEXT NOT NULL REFERENCES term_use(id),
          evidence_id TEXT NOT NULL REFERENCES evidence(id),
          checked_context_unit TEXT NOT NULL REFERENCES unit(id),
          checked_expression_unit TEXT REFERENCES unit(id),
          ocr_context_unit TEXT REFERENCES unit(id), source_page_unit TEXT REFERENCES unit(id),
          printed_page INTEGER NOT NULL, pdf_page INTEGER NOT NULL, scan_leaf INTEGER,
          term_form TEXT, evidence_role TEXT NOT NULL, composite_group TEXT,
          text_layer TEXT NOT NULL, issue TEXT NOT NULL);

CREATE TABLE sense_rendering (
          sense_id TEXT NOT NULL REFERENCES term_sense(id), rank INTEGER NOT NULL, rendering TEXT NOT NULL,
          PRIMARY KEY(sense_id,rank));

CREATE TABLE term_entry (
                id TEXT PRIMARY KEY NOT NULL, decision_id TEXT NOT NULL REFERENCES decision(id),
                forms_json TEXT NOT NULL, candidates_json TEXT NOT NULL,
                rule TEXT NOT NULL, exceptions TEXT NOT NULL, confidence TEXT NOT NULL,
                limitation TEXT NOT NULL);

CREATE TABLE term_entry_evidence (
                entry_id TEXT NOT NULL REFERENCES term_entry(id),
                evidence_id TEXT NOT NULL REFERENCES evidence(id),
                PRIMARY KEY(entry_id, evidence_id));

CREATE TABLE term_entry_family (
                entry_id TEXT NOT NULL REFERENCES term_entry(id),
                family_id TEXT NOT NULL REFERENCES term_family(id),
                PRIMARY KEY(entry_id, family_id));

CREATE TABLE term_expression_part (
          attestation_id TEXT NOT NULL REFERENCES sense_attestation(id), rank INTEGER NOT NULL,
          unit_id TEXT NOT NULL REFERENCES unit(id), part_role TEXT NOT NULL,
          PRIMARY KEY(attestation_id,rank));

CREATE TABLE term_family (id TEXT PRIMARY KEY NOT NULL, label TEXT NOT NULL, pattern TEXT NOT NULL);

CREATE TABLE term_occurrence (family_id TEXT NOT NULL REFERENCES term_family(id),
                unit_id TEXT NOT NULL REFERENCES unit(id), query_form TEXT NOT NULL, zone TEXT NOT NULL,
                PRIMARY KEY(family_id,unit_id));

CREATE TABLE term_relation (
          lexeme_id TEXT NOT NULL REFERENCES lexeme(id), relation TEXT NOT NULL,
          target_id TEXT REFERENCES lexeme(id), target_label TEXT NOT NULL, reason TEXT NOT NULL);

CREATE TABLE term_sense (
          id TEXT PRIMARY KEY NOT NULL, lexeme_id TEXT NOT NULL REFERENCES lexeme(id),
          label TEXT NOT NULL, definition TEXT NOT NULL, rule TEXT NOT NULL, caution TEXT NOT NULL,
          decision_id TEXT NOT NULL REFERENCES decision(id));

CREATE TABLE term_use (
          id TEXT PRIMARY KEY NOT NULL, sense_id TEXT NOT NULL REFERENCES term_sense(id),
          origin TEXT UNIQUE NOT NULL, label TEXT NOT NULL, definition TEXT NOT NULL,
          rule TEXT NOT NULL, caution TEXT NOT NULL);

CREATE TABLE terminology_candidate (
          id TEXT PRIMARY KEY NOT NULL, form TEXT NOT NULL, occurrences INTEGER NOT NULL,
          pages_json TEXT NOT NULL, header_only INTEGER NOT NULL, reader TEXT NOT NULL,
          disposition TEXT NOT NULL, target_id TEXT REFERENCES lexeme(id), reason TEXT NOT NULL);

CREATE TABLE terminology_control (
          id TEXT PRIMARY KEY NOT NULL, metadata_json TEXT NOT NULL);

CREATE TABLE terminology_page_review (
          printed_page INTEGER PRIMARY KEY NOT NULL, reader TEXT NOT NULL, metadata_json TEXT NOT NULL);

CREATE TABLE text_version (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    body TEXT NOT NULL CHECK (length(body) > 0 AND instr(body, char(0)) = 0),
    body_sha256 TEXT NOT NULL CHECK (length(body_sha256) = 64),
    source_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL CHECK (length(source_sha256) = 64),
    locator TEXT NOT NULL,
    transcription_status TEXT NOT NULL,
    provenance TEXT NOT NULL
);

CREATE TABLE unit (
    id TEXT PRIMARY KEY NOT NULL,
    analysis_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    start INTEGER NOT NULL CHECK (typeof(start) = 'integer' AND start >= 0),
    end INTEGER NOT NULL CHECK (typeof(end) = 'integer' AND end > start),
    parent_id TEXT,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE (id, analysis_id, version_id),
    FOREIGN KEY (analysis_id, version_id) REFERENCES analysis(id, version_id),
    FOREIGN KEY (parent_id, analysis_id, version_id)
        REFERENCES unit(id, analysis_id, version_id)
);

CREATE TABLE unit_decision (
    unit_id TEXT NOT NULL REFERENCES unit(id),
    decision_id TEXT NOT NULL REFERENCES decision(id),
    PRIMARY KEY (unit_id, decision_id)
);

CREATE TABLE unit_evidence (
    unit_id TEXT NOT NULL REFERENCES unit(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    PRIMARY KEY (unit_id, evidence_id)
);

CREATE TABLE word_index (unit_id TEXT PRIMARY KEY NOT NULL REFERENCES unit(id),
                query_form TEXT NOT NULL, printed_page INTEGER NOT NULL, pdf_page INTEGER NOT NULL,
                scan_leaf INTEGER NOT NULL, zone TEXT NOT NULL, extraction TEXT NOT NULL);

CREATE INDEX family_lookup ON term_occurrence(family_id);

CREATE INDEX lexeme_form_lookup ON lexeme_form(query_key);

CREATE INDEX word_form_lookup ON word_index(query_form);

CREATE TRIGGER alignment_insert_draft BEFORE INSERT ON alignment
WHEN NEW.status != 'draft' BEGIN
    SELECT RAISE(ABORT, 'create alignment in draft status');
END;

CREATE TRIGGER alignment_update BEFORE UPDATE ON alignment BEGIN
    SELECT CASE WHEN OLD.status != 'draft' OR NEW.id != OLD.id
        OR NEW.left_version != OLD.left_version OR NEW.right_version != OLD.right_version
        OR NEW.relation != OLD.relation OR NEW.note != OLD.note
        THEN RAISE(ABORT, 'alignment identity is immutable') END;
    SELECT CASE WHEN NEW.status = 'proposed' AND (
        NOT EXISTS (SELECT 1 FROM alignment_member WHERE alignment_id = OLD.id AND side = 'left')
        OR NOT EXISTS (SELECT 1 FROM alignment_member WHERE alignment_id = OLD.id AND side = 'right')
    ) THEN RAISE(ABORT, 'proposed alignment requires both sides') END;
END;

CREATE TRIGGER analysis_delete BEFORE DELETE ON analysis BEGIN
    SELECT RAISE(ABORT, 'analyses are immutable; add another analysis');
END;

CREATE TRIGGER analysis_update BEFORE UPDATE ON analysis BEGIN
    SELECT RAISE(ABORT, 'analyses are immutable; add another analysis');
END;

CREATE TRIGGER member_delete BEFORE DELETE ON alignment_member
WHEN (SELECT status FROM alignment WHERE id = OLD.alignment_id) != 'draft' BEGIN
    SELECT RAISE(ABORT, 'alignment membership is frozen');
END;

CREATE TRIGGER member_insert BEFORE INSERT ON alignment_member BEGIN
    SELECT CASE WHEN (SELECT status FROM alignment WHERE id = NEW.alignment_id) != 'draft'
        THEN RAISE(ABORT, 'alignment membership is frozen') END;
    SELECT CASE WHEN (SELECT version_id FROM unit WHERE id = NEW.unit_id) != (
        SELECT CASE NEW.side WHEN 'left' THEN left_version ELSE right_version END
        FROM alignment WHERE id = NEW.alignment_id
    ) THEN RAISE(ABORT, 'alignment member belongs to wrong text version') END;
END;

CREATE TRIGGER member_update BEFORE UPDATE ON alignment_member BEGIN
    SELECT RAISE(ABORT, 'replace a draft member with delete/insert');
END;

CREATE TRIGGER unit_bounds BEFORE INSERT ON unit BEGIN
    SELECT CASE WHEN NEW.end > (SELECT length(body) FROM text_version WHERE id = NEW.version_id)
        THEN RAISE(ABORT, 'span exceeds text version') END;
    SELECT CASE WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM unit p WHERE p.id = NEW.parent_id
          AND p.analysis_id = NEW.analysis_id AND p.version_id = NEW.version_id
          AND p.start <= NEW.start AND p.end >= NEW.end
    ) THEN RAISE(ABORT, 'parent must already exist, contain child and share analysis/version') END;
END;

CREATE TRIGGER unit_delete BEFORE DELETE ON unit BEGIN
    SELECT RAISE(ABORT, 'units are immutable; add another analysis');
END;

CREATE TRIGGER unit_update BEFORE UPDATE ON unit BEGIN
    SELECT RAISE(ABORT, 'units are immutable; add another analysis');
END;

CREATE TRIGGER version_delete BEFORE DELETE ON text_version BEGIN
    SELECT RAISE(ABORT, 'text versions are immutable');
END;

CREATE TRIGGER version_update BEFORE UPDATE ON text_version BEGIN
    SELECT RAISE(ABORT, 'text versions are immutable');
END;

CREATE VIEW unit_text AS
    SELECT u.*, substr(v.body, u.start + 1, u.end - u.start) AS text
    FROM unit u JOIN text_version v ON v.id = u.version_id;
