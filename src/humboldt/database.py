"""Versioned SQLite storage for immutable, reproducible edition snapshots.

The packaged SQL is the identifier allowlist and schema authority. Sealing uses
ordinary SQLite triggers, not a security boundary against a database owner who
can remove schema objects. Readers should also use a read-only connection.
"""

from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import heapq
from importlib import resources
import itertools
import json
from pathlib import Path
import re
import sqlite3


class SchemaError(ValueError):
    """A database or migration history does not match the packaged schema."""


class SealedError(SchemaError):
    """A construction operation was attempted on a sealed snapshot."""


_HISTORY_SQL = """CREATE TABLE schema_migration (
    version INTEGER PRIMARY KEY NOT NULL CHECK (version > 0),
    name TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    applied_at TEXT NOT NULL
)"""
_SEAL_PREFIX = "humboldt_sealed_"
_SAVEPOINTS = itertools.count()


def connect(path=":memory:", *, readonly=False):
    """Return a Row connection with foreign keys and recursive triggers enabled."""
    if readonly:
        if str(path) == ":memory:":
            raise ValueError("a read-only connection requires an existing file")
        uri = Path(path).expanduser().resolve().as_uri() + "?mode=ro"
        db = sqlite3.connect(uri, uri=True)
    else:
        filename = ":memory:" if str(path) == ":memory:" else str(Path(path).expanduser())
        db = sqlite3.connect(filename)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA recursive_triggers = ON")
    return db


def _identifier(name):
    # Callers supply introspected names, never unchecked input identifiers.
    return '"' + name.replace('"', '""') + '"'


def _migrations():
    directory = resources.files(__package__).joinpath("migrations")
    found = []
    for path in directory.iterdir():
        if not path.name.endswith(".sql"):
            continue
        match = re.fullmatch(r"(\d+)-[a-z0-9-]+\.sql", path.name)
        if not match:
            raise SchemaError(f"invalid packaged migration name: {path.name}")
        raw = path.read_bytes()
        found.append((int(match[1]), path.name, raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()))
    found.sort()
    if not found or [x[0] for x in found] != list(range(1, len(found) + 1)):
        raise SchemaError("packaged migrations must be consecutively numbered from 1")
    return tuple(found)


def _execute_script(db, script):
    # executescript commits an existing transaction. Execute complete statements
    # individually so DDL, history and PRAGMA user_version share one savepoint.
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            db.execute(pending)
            pending = ""
    if pending.strip():
        raise SchemaError("incomplete packaged SQL statement")


@contextmanager
def _atomic(db):
    name = f"humboldt_operation_{next(_SAVEPOINTS)}"
    db.execute(f"SAVEPOINT {name}")
    try:
        yield
        db.execute(f"RELEASE SAVEPOINT {name}")
    except BaseException:
        db.execute(f"ROLLBACK TO SAVEPOINT {name}")
        db.execute(f"RELEASE SAVEPOINT {name}")
        raise


def _objects(db):
    return {
        (row[0], row[1]): row[2]
        for row in db.execute(
            "SELECT type, name, sql FROM main.sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
        )
    }


def _catalog(db):
    result = {}
    for kind, name in _objects(db):
        if kind != "table":
            continue
        columns = tuple(row[1] for row in db.execute(f"PRAGMA main.table_info({_identifier(name)})"))
        parents = frozenset(row[2] for row in db.execute(f"PRAGMA main.foreign_key_list({_identifier(name)})"))
        result[name] = (columns, parents)
    return result


@lru_cache(maxsize=8)
def _expected(version, migrations):
    db = sqlite3.connect(":memory:")
    try:
        db.execute(_HISTORY_SQL)
        for number, _name, script, _checksum in migrations:
            if number <= version:
                _execute_script(db, script)
        return _objects(db), _catalog(db)
    finally:
        db.close()


def _sealed_sql(table, operation):
    name = _SEAL_PREFIX + table + "_" + operation.lower()
    sql = (
        f"CREATE TRIGGER {_identifier(name)} BEFORE {operation} ON {_identifier(table)} "
        "BEGIN SELECT RAISE(ABORT, 'database is sealed; build a fresh snapshot'); END"
    )
    return name, sql


def _is_sealed(db):
    # Detect the physical protections even if the metadata was damaged.
    return db.execute(
        "SELECT 1 FROM main.sqlite_master WHERE type = 'trigger' "
        "AND substr(name, 1, ?) = ? LIMIT 1", (len(_SEAL_PREFIX), _SEAL_PREFIX)
    ).fetchone() is not None


def _history(db, migrations):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > len(migrations):
        raise SchemaError(f"unknown future schema version {version}; supported through {len(migrations)}")
    objects = _objects(db)
    if ("table", "schema_migration") not in objects:
        if objects or version:
            raise SchemaError("nonempty unversioned database; import its records into a fresh database")
        return 0, False
    actual_columns = _catalog(db)["schema_migration"][0]
    if actual_columns != ("version", "name", "sha256", "applied_at"):
        raise SchemaError("unknown schema_migration columns")
    rows = list(db.execute("SELECT version, name, sha256 FROM main.schema_migration ORDER BY version"))
    recorded = [row[0] for row in rows]
    if recorded != list(range(1, len(rows) + 1)) or len(rows) != version:
        raise SchemaError("schema version and consecutive migration history disagree")
    for number, name, checksum in rows:
        if number > len(migrations):
            raise SchemaError(f"unknown future migration {number}")
        expected = migrations[number - 1]
        if name != expected[1] or checksum != expected[3]:
            raise SchemaError(f"migration {number} name/checksum mismatch")
    return version, True


def _assert_schema(db, version, migrations):
    expected, catalog = _expected(version, migrations)
    expected = dict(expected)
    if _is_sealed(db):
        if version < 2:
            raise SchemaError("sealing requires infrastructure schema version 2")
        for table in catalog:
            for operation in ("INSERT", "UPDATE", "DELETE"):
                name, sql = _sealed_sql(table, operation)
                expected[("trigger", name)] = sql
    actual = _objects(db)
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise SchemaError(f"unknown or incomplete schema objects; missing={missing}, extra={extra}")
    for key in expected:
        # SQLite preserves submitted DDL except for its terminal semicolon.
        if actual[key].strip().rstrip(";") != expected[key].strip().rstrip(";"):
            raise SchemaError(f"schema definition mismatch: {key[0]} {key[1]}")
    if _is_sealed(db):
        row = db.execute("SELECT value_json FROM main.build_metadata WHERE key = 'sealed'").fetchone()
        if row is None or row[0] != "true":
            raise SchemaError("sealed triggers and build metadata disagree")
    return catalog


def _state(db):
    migrations = _migrations()
    version, present = _history(db, migrations)
    if not present:
        raise SchemaError("database has not been migrated")
    return version, _assert_schema(db, version, migrations)


def migrate(db, target=None):
    """Apply packaged checksummed migrations atomically; never downgrade/adopt.

    Existing legacy snapshots are input evidence, not migration targets. Import
    their exported rows into a fresh versioned database instead.
    """
    if not db.execute("PRAGMA foreign_keys").fetchone()[0]:
        raise SchemaError("foreign keys must be enabled before migration")
    migrations = _migrations()
    latest = len(migrations)
    if target is None:
        target = latest
    if type(target) is not int or not 0 <= target <= latest:
        raise SchemaError(f"unknown target schema version {target!r}; supported through {latest}")
    current, present = _history(db, migrations)
    if _is_sealed(db):
        raise SealedError("database is sealed; migrate/rebuild a fresh unsealed snapshot")
    if present:
        _assert_schema(db, current, migrations)
    if target < current:
        raise SchemaError(f"schema downgrade from {current} to {target} is not supported")
    with _atomic(db):
        if not present:
            db.execute(_HISTORY_SQL)
        for number, name, script, checksum in migrations:
            if current < number <= target:
                _execute_script(db, script)
                db.execute(
                    "INSERT INTO main.schema_migration(version, name, sha256, applied_at) VALUES (?, ?, ?, ?)",
                    (number, name, checksum, datetime.now(timezone.utc).isoformat()),
                )
                db.execute(f"PRAGMA user_version = {number}")
        _assert_schema(db, target, migrations)
    return target


def seal(db):
    """Block direct row writes to every current table, including metadata/history."""
    version, catalog = _state(db)
    if version < 2:
        raise SchemaError("migrate to version 2 before sealing")
    if _is_sealed(db):
        return
    errors = db.execute("PRAGMA foreign_key_check").fetchall()
    integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
    if errors or integrity != ["ok"]:
        raise SchemaError("cannot seal a database with integrity or foreign-key errors")
    with _atomic(db):
        db.execute("INSERT INTO main.build_metadata(key, value_json) VALUES ('sealed', 'true')")
        for table in sorted(catalog):
            for operation in ("INSERT", "UPDATE", "DELETE"):
                _name, sql = _sealed_sql(table, operation)
                db.execute(sql)
        _assert_schema(db, version, _migrations())


def report(db):
    """Return JSON-serializable counts and physical integrity diagnostics."""
    version, catalog = _state(db)
    integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
    return {
        "schema_version": version,
        "sealed": _is_sealed(db),
        "counts": {name: db.execute(f"SELECT count(*) FROM main.{_identifier(name)}").fetchone()[0]
                   for name in sorted(catalog)},
        "integrity": "ok" if integrity == ["ok"] else "; ".join(integrity),
        "foreign_key_errors": [dict(zip(("table", "rowid", "parent", "fkid"), tuple(row)))
                               for row in db.execute("PRAGMA foreign_key_check")],
    }


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def logical_digest(db):
    """Hash durable rows canonically, excluding transient build metadata/time.

    Recorded revision timestamps are durable provenance and remain included.
    build_metadata (including its stored digest/sealed flag) and migration
    applied_at are excluded. Physical row order, file layout and path do not
    contribute. Resource manifests remain verified separately by ingest.
    """
    _version, catalog = _state(db)
    digest = hashlib.sha256()
    for table in sorted(catalog):
        if table == "build_metadata":
            continue
        columns = tuple(c for c in catalog[table][0]
                        if not (table == "schema_migration" and c == "applied_at"))
        digest.update((_json([table, columns]) + "\n").encode("utf-8"))
        query = ", ".join(_identifier(c) for c in columns)
        rows = []
        for row in db.execute(f"SELECT {query} FROM main.{_identifier(table)}"):
            values = [{"sqlite_blob_hex": value.hex()} if isinstance(value, bytes) else value for value in row]
            rows.append(_json(values))
        for row in sorted(rows):
            digest.update((row + "\n").encode("utf-8"))
    return digest.hexdigest()


def _table_order(names, catalog):
    remaining = {name: set(catalog[name][1]) & set(names) - {name} for name in names}
    ordered = []
    while remaining:
        ready = sorted(name for name, parents in remaining.items() if not parents)
        if not ready:
            # Deferred foreign keys support a future genuine inter-table cycle;
            # the final FK check still rejects an incomplete import.
            ordered.extend(sorted(remaining))
            break
        ordered.extend(ready)
        for name in ready:
            remaining.pop(name)
        for parents in remaining.values():
            parents.difference_update(ready)
    return ordered


def _unit_order(rows):
    by_id = {}
    for row in rows:
        unit_id = row.get("id")
        if not isinstance(unit_id, str) or unit_id in by_id:
            raise ValueError("unit records require unique explicit string IDs")
        by_id[unit_id] = row
    children = {}
    ready = []
    for unit_id, row in by_id.items():
        parent = row.get("parent_id")
        if parent in by_id:
            children.setdefault(parent, []).append(unit_id)
        else:
            heapq.heappush(ready, unit_id)
    result = []
    while ready:
        unit_id = heapq.heappop(ready)
        result.append(by_id[unit_id])
        for child in children.get(unit_id, ()):
            heapq.heappush(ready, child)
    if len(result) != len(rows):
        raise ValueError("unit parent cycle in imported records")
    return result


def insert_records(db, tables):
    """Atomically import allowlisted rows, preserving IDs and legacy constraints."""
    _version, catalog = _state(db)
    if _is_sealed(db):
        raise SealedError("database is sealed; import into a fresh snapshot")
    if not db.execute("PRAGMA foreign_keys").fetchone()[0]:
        raise SchemaError("foreign keys must be enabled before record import")
    if not isinstance(tables, Mapping):
        raise ValueError("tables must be a mapping of table names to record lists")
    supplied = {}
    for table, rows in tables.items():
        if table not in catalog or table == "schema_migration":
            raise ValueError(f"unknown or managed record table: {table!r}")
        if not isinstance(rows, (list, tuple)):
            raise ValueError(f"records for {table} must be a list")
        supplied[table] = []
        for row in rows:
            if not isinstance(row, Mapping) or not row:
                raise ValueError(f"records for {table} must be nonempty mappings")
            unknown = set(row) - set(catalog[table][0])
            if unknown:
                raise ValueError(f"unknown columns for {table}: {sorted(map(str, unknown))}")
            if table == "build_metadata" and row.get("key") == "sealed":
                raise ValueError("build_metadata.sealed is reserved for seal()")
            if table == "alignment" and row.get("status", "draft") not in ("draft", "proposed"):
                raise ValueError("alignment status must be draft or proposed")
            supplied[table].append(dict(row))
    if "unit" in supplied:
        supplied["unit"] = _unit_order(supplied["unit"])
    deferred = db.execute("PRAGMA defer_foreign_keys").fetchone()[0]
    try:
        with _atomic(db):
            db.execute("PRAGMA defer_foreign_keys = ON")
            proposed = []
            for table in _table_order(supplied, catalog):
                for original in supplied[table]:
                    row = dict(original)
                    if table == "alignment" and row.get("status") == "proposed":
                        proposed.append(row["id"])
                        row["status"] = "draft"
                    columns = [c for c in catalog[table][0] if c in row]
                    sql = (f"INSERT INTO main.{_identifier(table)} ("
                           + ", ".join(_identifier(c) for c in columns)
                           + ") VALUES (" + ", ".join("?" for _ in columns) + ")")
                    db.execute(sql, tuple(row[c] for c in columns))
            for alignment_id in proposed:
                db.execute("UPDATE main.alignment SET status = 'proposed' WHERE id = ?", (alignment_id,))
            errors = db.execute("PRAGMA foreign_key_check").fetchall()
            if errors:
                raise sqlite3.IntegrityError(f"foreign-key errors after record import: {[tuple(x) for x in errors[:5]]}")
    finally:
        db.execute(f"PRAGMA defer_foreign_keys = {int(deferred)}")
