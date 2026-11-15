"""Loopback-only, read-only edition browser and downloadable proposal drafts."""
from __future__ import annotations

from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path, PurePosixPath
import socket
import sqlite3
from urllib.parse import parse_qs, unquote, urlsplit

from . import database, queries, render
from .records import normalize_lines
from .revisions import SUPPORTED

DRAFT_FIELDS = SUPPORTED
MAX_POST = 2 * 1024 * 1024


class ReaderError(ValueError):
    """An explicit invalid reader configuration or request."""


def _loopback(host):
    if host == 'localhost':
        return '127.0.0.1'
    try:
        if ipaddress.ip_address(host).is_loopback:
            return host
    except ValueError:
        pass
    raise ReaderError('Reader binds only to a loopback IP address (127.0.0.1 or ::1).')


def _safe_source(project, name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name or ':' in name:
        raise ReaderError('Invalid source path.')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')) or path.parts[0] not in {'sources','translations'}:
        raise ReaderError('Attachment paths must be canonical project-relative paths within sources/ or translations/.')
    target = (project / name).resolve()
    source_root = (project / path.parts[0]).resolve()
    # Also reject a sources/ directory itself redirected outside the project.
    if not source_root.is_relative_to(project) or not target.is_relative_to(source_root) or not target.is_relative_to(project):
        raise ReaderError('Source path escapes the project source directory.')
    return target


def source_resources(project, db):
    """Label declared/linked source files without making their absence fatal."""
    output, seen = [], set()
    for item in queries.resources(db):
        name = item.get('path', '')
        if name in seen:
            continue
        seen.add(name)
        record = {**item, 'available': False}
        try:
            target = _safe_source(project, name)
            if target.is_file():
                record['available'] = True
                record['availability'] = 'Local source attachment available.'
            else:
                record['availability'] = 'Attachment not included in this copy; embedded checked text and quotations remain available.'
        except ReaderError:
            record['availability'] = 'Not a permitted source attachment; embedded text remains available.'
        output.append(record)
    return output


def _draft_target(db, kind, identifier, field):
    if kind not in DRAFT_FIELDS or field not in DRAFT_FIELDS[kind]:
        raise ReaderError('Unsupported proposal target/field; consult the contributor guide for editable fields.')
    return queries.entity(db, kind, identifier)['record']


def make_server(project, db_path, host='127.0.0.1', port=0):
    """Construct a testable server. Every database connection is read-only."""
    project = Path(project).resolve()
    db_path = Path(db_path)
    db_path = (project / db_path).resolve() if not db_path.is_absolute() else db_path.resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f'Edition build is absent: {db_path}. Build the edition first with humboldt build.')
    with closing(database.connect(db_path, readonly=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='text_version'").fetchone():
            raise ReaderError('This database has no edition text_version table; build a valid edition first.')
    host = _loopback(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ReaderError('Port must be an integer from 0 to 65535.')

    class Handler(BaseHTTPRequestHandler):
        server_version = 'HumboldtReader/1'

        def log_message(self, format, *args):
            # Avoid printing untrusted paths/control characters into a terminal.
            return

        def _respond(self, status, content, content_type='text/html; charset=utf-8', extra=()):
            if isinstance(content, str):
                content = content.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'; sandbox allow-forms allow-same-origin allow-downloads")
            for key, value in extra:
                self.send_header(key, value)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)

        def _json(self, value, status=200, extra=()):
            self._respond(status, json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), 'application/json; charset=utf-8', extra)

        def _error(self, status, message):
            if self.path.startswith('/api/'):
                self._json({'error': message, 'status': status}, status)
            else:
                self._respond(status, render.document('Reader error', '<p class="notice">' + render.esc(message) + '</p>'))

        def _host_ok(self):
            raw = self.headers.get('Host', '')
            try:
                parsed = urlsplit('//' + raw)
                return not parsed.username and not parsed.password and not parsed.path and parsed.hostname in ('localhost', '127.0.0.1', '::1', host) and parsed.port == self.server.server_port
            except ValueError:
                return False

        def _params(self):
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise ReaderError('Only local relative reader routes are supported.')
            params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=30)
            if any(len(v) != 1 for v in params.values()):
                raise ReaderError('Repeated request parameters are not supported.')
            return parsed.path, {k:v[0] for k,v in params.items()}

        def do_GET(self):
            if not self._host_ok():
                return self._error(403, 'Reader requests require a matching loopback Host header.')
            try:
                route, params = self._params()
                with closing(database.connect(db_path, readonly=True)) as db:
                    self._get(db, route, params)
            except queries.NotFound as error:
                self._error(404, str(error))
            except (ReaderError, ValueError, KeyError) as error:
                self._error(400, str(error))
            except (OSError, sqlite3.Error) as error:
                self._error(503, 'The edition build or requested local resource is unavailable: ' + str(error))

        def _get(self, db, route, p):
            if route == '/api/health':
                return self._json({'status': 'ok', 'read_only': True, 'metadata': queries.metadata(db), 'sections': [r['section'] for r in queries.sections(db)]})
            if route == '/api/sections':
                return self._json(queries.sections(db))
            if route in ('/search', '/api/search'):
                query = p.get('q', '')
                result = queries.search(db, query, int(p.get('limit', '30')))
                return self._json(result) if route.startswith('/api/') else self._respond(200, render.search_view(query, result))
            if route in ('/trace', '/api/trace'):
                result = queries.trace(db, p.get('id', ''))
                return self._json(result) if route.startswith('/api/') else self._respond(200, render.trace_view(result, source_resources(project, db)))
            if route in ('/entity', '/api/entity'):
                result = queries.entity(db, p.get('kind', ''), p.get('id', ''))
                return self._json(result) if route.startswith('/api/') else self._respond(200, render.entity_view(result, source_resources(project, db)))
            if route == '/api/passage':
                return self._json(queries.passage(db, p.get('section', '')))
            if route == '/':
                choices = queries.sections(db)
                passage = queries.passage(db, p.get('section') or choices[0]['section']) if choices else None
                return self._respond(200, render.home(choices, passage, p.get('de'), p.get('en'), source_resources(project, db)))
            if route == '/propose':
                from .revisions import fingerprint
                row = _draft_target(db, p.get('kind'), p.get('id', ''), p.get('field'))
                return self._respond(200, render.proposal_view(p['kind'], row, p['field'], fingerprint(row)))
            if route == '/source':
                name = p.get('path', '')
                try:
                    target = _safe_source(project, name)
                except ReaderError as error:
                    return self._error(403, str(error))
                allowed = {r['path'] for r in source_resources(project, db) if r['available']}
                if name not in allowed:
                    declared = {r['path'] for r in queries.resources(db)}
                    return self._error(404 if name in declared else 403, 'Source attachment is missing from this copy.' if name in declared else 'Source is not declared or linked by this edition.')
                if not target.is_file():
                    return self._error(404, 'Source attachment is missing; embedded quotations remain available.')
                content_type = 'application/pdf' if target.suffix.casefold() == '.pdf' else 'text/plain; charset=utf-8'
                return self._respond(200, target.read_bytes(), content_type, [('Content-Disposition', 'inline' if target.suffix.casefold() in ('.pdf', '.txt', '.md') else 'attachment')])
            return self._error(404, 'Unknown reader route: ' + route)

        def do_POST(self):
            if not self._host_ok():
                return self._error(403, 'Reader requests require a matching loopback Host header.')
            try:
                route, _ = self._params()
                if route != '/proposal':
                    return self._error(404, 'Only /proposal accepts a draft form; no reader endpoint saves or accepts revisions.')
                if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
                    return self._error(415, 'Proposal drafts require an HTML form encoding.')
                if self.headers.get('Transfer-Encoding'):
                    raise ReaderError('Transfer-Encoding is not supported.')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_POST:
                    return self._error(413, 'Proposal draft must be between 1 byte and 2 MiB.')
                data = parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=True, max_num_fields=15)
                if any(len(v) != 1 for v in data.values()):
                    raise ReaderError('Repeated form fields are not supported.')
                p = {k:v[0] for k,v in data.items()}
                required = {'kind','target_id','field','value','by','reason','evidence','target_sha256'}
                if set(p) != required:
                    raise ReaderError('Proposal draft fields are missing or unsupported.')
                p['value']=normalize_lines(p['value']);p['reason']=normalize_lines(p['reason'])
                if (not p['value'].strip() and p['field'] not in {'caution','note','locator','provenance'}) or not p['by'].strip() or not p['reason'].strip() or len(p['by']) > 200:
                    raise ReaderError('Proposed value, name and reason are required; name must be 200 characters or fewer.')
                evidence = json.loads(p['evidence'])
                if not isinstance(evidence, list):
                    raise ReaderError('Evidence must be a JSON array.')
                from .revisions import fingerprint
                with closing(database.connect(db_path, readonly=True)) as db:
                    row = _draft_target(db, p['kind'], p['target_id'], p['field'])
                    if p['target_sha256'] != fingerprint(row):
                        return self._error(409, 'The target row changed since this form was opened. Inspect the current reading and create a fresh draft.')
                draft = {key:p[key] for key in ('kind','target_id','field','value','by','reason','target_sha256')}
                draft['evidence'] = evidence
                return self._json(draft, extra=[('Content-Disposition', 'attachment; filename="humboldt-proposal-draft.json"')])
            except queries.NotFound as error:
                self._error(404, str(error))
            except (ValueError, KeyError, UnicodeError) as error:
                self._error(400, str(error))
            except (OSError, sqlite3.Error) as error:
                self._error(503, 'The edition build is unavailable: ' + str(error))

    class LocalServer(ThreadingHTTPServer):
        daemon_threads = True
        if ':' in host:
            address_family = socket.AF_INET6

    server = LocalServer((host, port), Handler)
    address = '[' + host + ']' if ':' in host else host
    server.reader_url = f'http://{address}:{server.server_port}/'
    return server


def serve(project, db_path, host='127.0.0.1', port=0):
    """Run the local reader until interrupted; never persist a reader edit."""
    server = make_server(project, db_path, host, port)
    print('Humboldt reader: ' + server.reader_url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
