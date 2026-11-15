# Database migrations

Authoritative numbered SQL lives in `src/humboldt/migrations/` and is included in the package. `schema_migration` stores the version and SQL checksum; `PRAGMA user_version` identifies the installed schema. The engine rejects a future version, missing migration or modified migration history.

Migration 001 preserves the existing scholarly schema; migration 002 adds build metadata and revision/impact history. Build applies these same migrations to an empty database. Supported unsealed old databases can be upgraded through them; sealed edition releases remain immutable and are replaced by a newly built release rather than changed in place.
