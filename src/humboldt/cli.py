"""One documented command surface for builds, inspection and recorded changes."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from . import __version__,database,ingest
from .records import atomic_json,canonical,read_json


def _print(value):print(json.dumps(value,ensure_ascii=False,indent=2))


def _db(root,value):return Path(value).resolve() if value else root/'build/edition.sqlite'


def _read_db(root,value):
    path=_db(root,value)
    if not path.is_file():raise ValueError('database missing: run humboldt build first')
    return database.connect(path,readonly=True)


def parser():
    p=argparse.ArgumentParser(prog='humboldt',description='Build, inspect and revise a source-linked research edition.')
    p.add_argument('--project',default='.',help='project directory containing edition/manifest.json')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate',help='validate durable inputs, shapes, spans and relations');v.add_argument('--sources',action='store_true',help='also hash available optional source attachments')
    comparison=sub.add_parser('verify',help='compare explicit immutable base or current-release identity');comparison.add_argument('--against',type=Path,required=True)
    b=sub.add_parser('build',help='create a sealed SQLite projection');b.add_argument('--output');b.add_argument('--force',action='store_true',help='replace an existing output only within project build/')
    s=sub.add_parser('search',help='search German and English terms and texts');s.add_argument('text');s.add_argument('--limit',type=int,default=30);s.add_argument('--db')
    t=sub.add_parser('trace',help='inspect a unit, overlapping annotations and evidence');t.add_argument('unit_id');t.add_argument('--db')
    e=sub.add_parser('show',help='inspect an entity by permanent kind and ID');e.add_argument('kind');e.add_argument('id');e.add_argument('--db')
    g=sub.add_parser('passage',help='show versions and blocks for a section');g.add_argument('section');g.add_argument('--db')
    status=sub.add_parser('status',help='show build/schema state');status.add_argument('--db')
    br=sub.add_parser('browse',help='run the local read-only reader');br.add_argument('--db');br.add_argument('--port',type=int,default=0);br.add_argument('--host',default='127.0.0.1')
    pr=sub.add_parser('propose',help='save an attributed proposed correction');pr.add_argument('--kind',required=True);pr.add_argument('--id',dest='target_id',required=True);pr.add_argument('--field',required=True)
    values=pr.add_mutually_exclusive_group(required=True);values.add_argument('--value');values.add_argument('--value-file',type=Path)
    pr.add_argument('--by',required=True);pr.add_argument('--reason',required=True);pr.add_argument('--evidence',action='append',default=[]);pr.add_argument('--expected-sha256')
    imp=sub.add_parser('import-proposal',help='save a reader-downloaded draft, checking its observed target');imp.add_argument('path',type=Path);imp.add_argument('--by')
    decision=sub.add_parser('decide',help='accept or reject a saved proposal');decision.add_argument('proposal_id');which=decision.add_mutually_exclusive_group(required=True);which.add_argument('--accept',action='store_true');which.add_argument('--reject',action='store_true');decision.add_argument('--by',required=True);decision.add_argument('--reason',required=True)
    history=sub.add_parser('history',help='list durable proposal/decision events without rebuilding');history.add_argument('--id',dest='target_id')
    impdata=sub.add_parser('import',help='validate and add another passage dataset');impdata.add_argument('path',type=Path)
    export=sub.add_parser('export',help='export canonical logical JSON or one table as CSV');export.add_argument('--output',type=Path,required=True);export.add_argument('--table');export.add_argument('--format',choices=['json','csv'],default='json');export.add_argument('--db')
    release=sub.add_parser('release',help='create a portable local release, without publishing');release.add_argument('--output',type=Path,required=True);release.add_argument('--db')
    migrate=sub.add_parser('migrate',help='upgrade an unsealed, versioned database');migrate.add_argument('--db',type=Path,required=True);migrate.add_argument('--target',type=int)
    test=sub.add_parser('test',help='run fixture-based unit/integration tests');test.add_argument('--legacy',action='store_true',help='also run the historical corpus tests; needs original holdings/snapshots')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    root=Path(args.project).resolve()
    try:
        if args.command=='test':
            from . import __file__ as package_file
            code_root=Path(package_file).resolve().parents[2]
            if not (code_root/'tests/unit').is_dir():raise ValueError('self-tests require the source checkout; use validate to check a portable release')
            starts=['tests/unit','tests/integration']
            if (code_root/'tests/corpus').is_dir():starts.append('tests/corpus')
            if args.legacy:starts.append('tests')
            code=0
            for start in starts:
                result=subprocess.run([sys.executable,'-m','unittest','discover','-s',start,'-v'],cwd=code_root,env=dict(__import__('os').environ,PYTHONPATH=str(code_root/'src')))
                code=max(code,result.returncode)
            return code
        if args.command=='migrate':
            if not args.db.is_file():raise ValueError('migration requires an existing unsealed, versioned database')
            db=database.connect(args.db)
            try:_print(dict(schema_version=database.migrate(db,args.target)))
            finally:db.close()
            return 0
        root=ingest.project_root(root)
        if args.command=='validate':_print(ingest.validate(root,sources=args.sources));return 0
        if args.command=='verify':_print(ingest.verify(root,args.against));return 0
        if args.command=='build':_print(ingest.build(root,Path(args.output) if args.output else root/'build/edition.sqlite',force=args.force));return 0
        if args.command=='import':_print(ingest.add_dataset(root,args.path));return 0
        if args.command=='propose':
            from .revisions import propose
            value=args.value_file.read_text(encoding='utf-8') if args.value_file else args.value
            _print(propose(root,kind=args.kind,target_id=args.target_id,field=args.field,value=value,by=args.by,reason=args.reason,evidence=args.evidence,expected_sha256=args.expected_sha256));return 0
        if args.command=='import-proposal':
            from .revisions import propose
            data=read_json(args.path)
            if not isinstance(data,dict):raise ValueError('proposal draft must be a JSON object')
            allowed={'format','schema_version','kind','target_id','field','value','by','reason','evidence','target_sha256'}
            if set(data)-allowed:raise ValueError('unknown proposal draft fields: '+', '.join(sorted(set(data)-allowed)))
            if data.get('format','humboldt.proposal-draft')!='humboldt.proposal-draft' or type(data.get('schema_version',1)) is not int or data.get('schema_version',1)!=1:raise ValueError('unsupported proposal draft format/version')
            if not data.get('target_sha256'):raise ValueError('draft must include its observed target_sha256')
            _print(propose(root,kind=data['kind'],target_id=data['target_id'],field=data['field'],value=data['value'],by=args.by or data['by'],reason=data['reason'],evidence=data.get('evidence',[]),expected_sha256=data['target_sha256']));return 0
        if args.command=='decide':
            from .revisions import decide
            _print(decide(root,args.proposal_id,accept=args.accept,by=args.by,reason=args.reason));return 0
        if args.command=='history':
            from .revisions import read_events
            events=read_events(root)
            if args.target_id:
                proposals={e['id'] for e in events if e.get('target_id')==args.target_id}
                events=[e for e in events if e.get('target_id')==args.target_id or e.get('proposal_id') in proposals]
            _print(events);return 0
        if args.command=='browse':
            from .reader import serve
            serve(root,_db(root,args.db),host=args.host,port=args.port);return 0
        if args.command=='release':
            from .release import create
            _print(create(root,_db(root,args.db),args.output));return 0
        db=_read_db(root,getattr(args,'db',None))
        try:
            from . import queries
            if args.command=='search':_print(queries.search(db,args.text,args.limit))
            elif args.command=='trace':_print(queries.trace(db,args.unit_id))
            elif args.command=='show':_print(queries.entity(db,args.kind,args.id))
            elif args.command=='passage':_print(queries.passage(db,args.section))
            elif args.command=='status':_print(dict(database.report(db),metadata=queries.metadata(db)))
            elif args.command=='export':
                from .release import export
                export(db,args.output,table=args.table,format=args.format);_print(dict(output=str(args.output)))
        finally:db.close()
        return 0
    except (ValueError,KeyError,LookupError,OSError,sqlite3.DatabaseError) as error:
        print('humboldt: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
