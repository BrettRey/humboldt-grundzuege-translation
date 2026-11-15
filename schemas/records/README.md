# Record schemas

The authoritative machine-readable schemas are packaged at `src/humboldt/record_schemas/`. They travel with installed and portable readers, so validation does not depend on this repository’s original location. There is one schema copy per format.

- `edition.schema.json`: declared durable dataset files, checksums and optional original-source attachments.
- `bundle.schema.json`: versioned table records, generic passage layouts and deterministic written-token recipes.

`humboldt validate` enforces the schema vocabulary actually used here, then text hashes, Unicode spans, identifier/parent constraints and SQL foreign keys. The standard-library validator is deliberately limited to documented JSON Schema keywords; it rejects unsupported keywords rather than pretending to implement the whole standard. Existing identifiers are literal permanent identities. Generated word identifiers are scoped to an immutable text version.

A record format change requires a new schema version and an explicit, tested converter. Database schema changes use the separate numbered SQL migrations. Neither kind of conversion authorizes changes to scholarly meaning.
