"""Portable local releases and deterministic logical exports; no publishing."""
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from . import __version__,database,ingest
from .records import atomic_json,canonical,file_hash,read_json


def export(db,output,*,table=None,format='json'):
    output=Path(output)
    if output.exists():raise ValueError('export output already exists')
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if table and table not in names:raise ValueError('unknown export table')
    if format=='csv' and not table:raise ValueError('CSV export requires --table')
    selected=[table] if table else sorted(names-{'schema_migration','build_metadata'})
    data={}
    for name in selected:
        # Membership in sqlite_master, never unchecked SQL interpolation.
        quoted='"'+name.replace('"','""')+'"'
        data[name]=sorted([dict(r) for r in db.execute('SELECT * FROM '+quoted)],key=canonical)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8',newline='') as stream:
        if format=='json':json.dump(dict(schema_version=db.execute('PRAGMA user_version').fetchone()[0],logical_digest=database.logical_digest(db),tables=data),stream,ensure_ascii=False,sort_keys=True,indent=2);stream.write('\n')
        else:
            fields=[r[1] for r in db.execute('PRAGMA table_info("'+table.replace('"','""')+'")')]
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(data[table])


def create(project,db_path,output):
    project=ingest.project_root(project);db_path=Path(db_path).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('release destination already exists')
    if output.is_relative_to(project) and output.parts[len(project.parts)]!='releases':raise ValueError('local releases must be under releases/ or a fresh external directory')
    if not db_path.is_file():raise ValueError('build the database before creating a release')
    from .revisions import project_lock
    with project_lock(project):
        validation=ingest.validate(project)
        db=database.connect(db_path,readonly=True)
        try:
            if database.logical_digest(db)!=validation['logical_digest']:raise ValueError('database is stale; rebuild before release')
            identity=db.execute("SELECT value_json FROM build_metadata WHERE key='input_digest'").fetchone()
            if not identity or json.loads(identity[0])!=validation['input_digest']:raise ValueError('build inputs or journal changed; rebuild before release')
            if not database.report(db)['sealed']:raise ValueError('release database must be sealed')
            digest=database.logical_digest(db)
        finally:db.close()
        output.parent.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'.',dir=output.parent))
        try:
            shutil.copytree(project/'src',stage/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            shutil.copytree(project/'edition',stage/'edition',ignore=shutil.ignore_patterns('*.tmp'))
            shutil.copy2(project/'humboldt',stage/'humboldt');shutil.copy2(project/'pyproject.toml',stage/'pyproject.toml')
            for name in ('LICENSE','LICENSE-CONTENT','NOTICE.md','CITATION.cff'):
                if (project/name).is_file():shutil.copy2(project/name,stage/name)
            (stage/'build').mkdir();shutil.copy2(db_path,stage/'build/edition.sqlite')
            (stage/'docs').mkdir()
            guide=project/'docs/architecture/user-guide.md'
            if not guide.exists():guide=project/'docs/user-guide.md'
            if guide.exists():shutil.copy2(guide,stage/'docs/user-guide.md')
            else:(stage/'docs/user-guide.md').write_text('# Reader and editing guide\n\nRun `python3 humboldt --help` for the local commands. Proposals require explicit attribution and evidence; accepting a proposal records a new event. Rebuild after acceptance. Original records remain preserved in edition data. Text corrections create a new version and require review of affected links.\n',encoding='utf-8')
            for name in ('journal-contract.md','data-contract.md'):
                companion=project/'docs/architecture'/name
                if not companion.exists():companion=project/'docs'/name
                if companion.exists():shutil.copy2(companion,stage/'docs'/name)
            template=project/'tests/fixtures/minimal/edition/passages/minimal.json'
            if not template.exists():template=project/'examples/minimal-passage.json'
            if template.exists():
                (stage/'examples').mkdir()
                shutil.copy2(template,stage/'examples/minimal-passage.json')
            (stage/'README.md').write_text('# Humboldt research edition\n\nThis is a local frozen research snapshot, not a certified critical edition. Original-source attachments may be absent; checked texts, evidence, alternatives and provenance remain embedded.\n\nWith Python3.11 or newer, run:\n\n```bash\npython3 humboldt validate\npython3 humboldt search understanding\npython3 humboldt passage 147\npython3 humboldt browse\n```\n\nThe browser prints a loopback URL. No model credentials or network are needed. Source and meaning validation retain the statuses recorded in the data. See docs/user-guide.md for editing a working copy. release.json records file hashes and the logical database identity.\n',encoding='utf-8')
            # Prove the copy stands alone before making it visible.
            process=subprocess.run([sys.executable,'humboldt','validate'],cwd=stage,capture_output=True,text=True,timeout=180)
            if process.returncode:raise ValueError('portable reader validation failed: '+process.stderr.strip())
            copied=json.loads(process.stdout)
            if copied['logical_digest']!=digest:raise ValueError('portable copy differs from original logical data')
            files={str(p.relative_to(stage)):file_hash(p) for p in sorted(stage.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
            atomic_json(stage/'release.json',dict(format='humboldt.release',schema_version=1,software_version=__version__,recorded_at=datetime.now(timezone.utc).isoformat(),logical_digest=digest,files=files,limits=['Provisional research translation and model-assisted source checks; no specialist certification.','Raw source attachments are optional and not bundled by default.']))
            if output.exists():raise ValueError('release destination appeared during packaging')
            stage.rename(output)
        except Exception:
            shutil.rmtree(stage);raise
    return dict(output=str(output),logical_digest=digest,files=len(files))
