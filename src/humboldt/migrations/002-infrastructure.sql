-- Portable build provenance and append-only revision projections.
CREATE TABLE build_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value_json TEXT NOT NULL
);

CREATE TABLE revision_history (
    id TEXT PRIMARY KEY NOT NULL,
    proposal_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT,
    by_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    recorded_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'rejected')),
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE change_impact (
    revision_id TEXT NOT NULL REFERENCES revision_history(id),
    entity_kind TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    impact TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (revision_id, entity_kind, entity_id, impact)
);

CREATE INDEX revision_target_lookup ON revision_history(kind, target_id);
CREATE INDEX revision_proposal_lookup ON revision_history(proposal_id);
CREATE INDEX impact_entity_lookup ON change_impact(entity_kind, entity_id);
CREATE INDEX unit_parent_lookup ON unit(parent_id);
CREATE INDEX unit_version_span_lookup ON unit(version_id, start, end);
CREATE INDEX alignment_member_unit_lookup ON alignment_member(unit_id);
CREATE INDEX unit_decision_decision_lookup ON unit_decision(decision_id);
CREATE INDEX unit_evidence_evidence_lookup ON unit_evidence(evidence_id);
