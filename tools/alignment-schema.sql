PRAGMA foreign_keys = ON;

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
CREATE TRIGGER unit_bounds BEFORE INSERT ON unit BEGIN
    SELECT CASE WHEN NEW.end > (SELECT length(body) FROM text_version WHERE id = NEW.version_id)
        THEN RAISE(ABORT, 'span exceeds text version') END;
    SELECT CASE WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM unit p WHERE p.id = NEW.parent_id
          AND p.analysis_id = NEW.analysis_id AND p.version_id = NEW.version_id
          AND p.start <= NEW.start AND p.end >= NEW.end
    ) THEN RAISE(ABORT, 'parent must already exist, contain child and share analysis/version') END;
END;
CREATE VIEW unit_text AS
    SELECT u.*, substr(v.body, u.start + 1, u.end - u.start) AS text
    FROM unit u JOIN text_version v ON v.id = u.version_id;

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
CREATE TABLE decision (
    id TEXT PRIMARY KEY NOT NULL,
    question TEXT NOT NULL,
    resolution TEXT NOT NULL,
    authority TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('provisional', 'adopted'))
);
CREATE TABLE unit_evidence (
    unit_id TEXT NOT NULL REFERENCES unit(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    PRIMARY KEY (unit_id, evidence_id)
);
CREATE TABLE unit_decision (
    unit_id TEXT NOT NULL REFERENCES unit(id),
    decision_id TEXT NOT NULL REFERENCES decision(id),
    PRIMARY KEY (unit_id, decision_id)
);
CREATE TABLE decision_evidence (
    decision_id TEXT NOT NULL REFERENCES decision(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    PRIMARY KEY (decision_id, evidence_id)
);
CREATE TABLE alignment (
    id TEXT PRIMARY KEY NOT NULL,
    left_version TEXT NOT NULL REFERENCES text_version(id),
    right_version TEXT NOT NULL REFERENCES text_version(id),
    relation TEXT NOT NULL,
    note TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed'))
);
CREATE TRIGGER alignment_insert_draft BEFORE INSERT ON alignment
WHEN NEW.status != 'draft' BEGIN
    SELECT RAISE(ABORT, 'create alignment in draft status');
END;
CREATE TABLE alignment_member (
    alignment_id TEXT NOT NULL REFERENCES alignment(id),
    side TEXT NOT NULL CHECK (side IN ('left', 'right')),
    unit_id TEXT NOT NULL REFERENCES unit(id),
    PRIMARY KEY (alignment_id, side, unit_id)
);
CREATE TRIGGER member_insert BEFORE INSERT ON alignment_member BEGIN
    SELECT CASE WHEN (SELECT status FROM alignment WHERE id = NEW.alignment_id) != 'draft'
        THEN RAISE(ABORT, 'alignment membership is frozen') END;
    SELECT CASE WHEN (SELECT version_id FROM unit WHERE id = NEW.unit_id) != (
        SELECT CASE NEW.side WHEN 'left' THEN left_version ELSE right_version END
        FROM alignment WHERE id = NEW.alignment_id
    ) THEN RAISE(ABORT, 'alignment member belongs to wrong text version') END;
END;
CREATE TRIGGER member_delete BEFORE DELETE ON alignment_member
WHEN (SELECT status FROM alignment WHERE id = OLD.alignment_id) != 'draft' BEGIN
    SELECT RAISE(ABORT, 'alignment membership is frozen');
END;
CREATE TRIGGER member_update BEFORE UPDATE ON alignment_member BEGIN
    SELECT RAISE(ABORT, 'replace a draft member with delete/insert');
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
CREATE TRIGGER version_update BEFORE UPDATE ON text_version BEGIN
    SELECT RAISE(ABORT, 'text versions are immutable');
END;
CREATE TRIGGER version_delete BEFORE DELETE ON text_version BEGIN
    SELECT RAISE(ABORT, 'text versions are immutable');
END;
CREATE TRIGGER unit_update BEFORE UPDATE ON unit BEGIN
    SELECT RAISE(ABORT, 'units are immutable; add another analysis');
END;
CREATE TRIGGER unit_delete BEFORE DELETE ON unit BEGIN
    SELECT RAISE(ABORT, 'units are immutable; add another analysis');
END;
CREATE TRIGGER analysis_update BEFORE UPDATE ON analysis BEGIN
    SELECT RAISE(ABORT, 'analyses are immutable; add another analysis');
END;
CREATE TRIGGER analysis_delete BEFORE DELETE ON analysis BEGIN
    SELECT RAISE(ABORT, 'analyses are immutable; add another analysis');
END;
