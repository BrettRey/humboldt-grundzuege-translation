"""Small record, path and Unicode helpers; no network or corpus dependency."""
from pathlib import Path
import hashlib
import errno
import json
import os
import re
import unicodedata
import uuid


COMPOSITE_KEYS = {
    'sense_rendering': ('sense_id', 'rank'),
    'lexeme_form': ('lexeme_id', 'form'),
    'alignment_member': ('alignment_id', 'side', 'unit_id'),
}


def record_key(kind, identifier):
    """Decode a permanent ID or explicit composite JSON address, never SQL."""
    if kind not in COMPOSITE_KEYS:
        return {'id': identifier}
    key = parse_json(identifier)
    if not isinstance(key, dict) or set(key) != set(COMPOSITE_KEYS[kind]):
        raise ValueError('composite target requires keys: ' + ', '.join(COMPOSITE_KEYS[kind]))
    for name, value in key.items():
        if name == 'rank':
            if type(value) is not int or value < 1:raise ValueError('rank must be a positive integer')
        elif not isinstance(value, str) or not value:raise ValueError('target keys must be nonempty strings')
    return key


def record_id(kind, row):
    return canonical({key: row[key] for key in COMPOSITE_KEYS[kind]}) if kind in COMPOSITE_KEYS else row['id']


def normalize_lines(value):
    return value.replace('\r\n', '\n').replace('\r', '\n')


def publish_exclusive(temporary, target):
    """Publish complete bytes without replacing an existing destination."""
    try:os.link(temporary, target)
    except OSError as error:
        if error.errno in {errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS, errno.EXDEV}:
            raise ValueError('Atomic publication requires hard links on this filesystem; use a local filesystem supporting hard links (not FAT/exFAT). No destination was replaced.') from error
        raise


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_json(value):
    def unique(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError(f'duplicate JSON key: {key}')
            result[key]=value
        return result
    def invalid(value):raise ValueError('non-finite JSON number: '+value)
    return json.loads(value,object_pairs_hook=unique,parse_constant=invalid)


def read_json(path):
    return parse_json(Path(path).read_bytes())


def within(root,relative):
    root=Path(root).resolve();path=Path(relative)
    if path.is_absolute() or '..' in path.parts:raise ValueError('path must be relative and confined: '+str(relative))
    target=(root/path).resolve()
    if not target.is_relative_to(root):raise ValueError('path leaves project: '+str(relative))
    return target


def sync_directory(path):
    """Persist a published directory entry where the OS supports directory fsync."""
    try:fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    except OSError:
        if os.name=='nt':return
        raise
    try:os.fsync(fd)
    finally:os.close(fd)


def atomic_json(path,value,*,replace=True):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
            stream.flush();os.fsync(stream.fileno())
        if replace:os.replace(temporary,path)
        else:publish_exclusive(temporary,path);temporary.unlink()
        sync_directory(path.parent)
    finally:
        if temporary.exists():temporary.unlink()


def word_spans(body):
    """Unicode L/M/N written tokens; internal hyphens/apostrophes retained.

    This freezes the old token convention, not a linguistic analysis. Offsets
    count Python Unicode code points; source text is never normalized here.
    """
    def constituent(char):return unicodedata.category(char)[0] in 'LMN'
    i=0
    while i<len(body):
        if not constituent(body[i]):i+=1;continue
        start=i;i+=1
        while i<len(body):
            if constituent(body[i]):i+=1
            elif body[i] in "-'’" and i+1<len(body) and constituent(body[i+1]):i+=2
            else:break
        yield start,i


def validate_shape(value,schema,where='$',root=None):
    """Validate the documented finite schema vocabulary used by this package.

    Supports local refs, scalar/object/array types and the constraints below;
    rejects unknown schema keywords instead of claiming arbitrary JSON Schema
    support. SQL validates relational constraints in addition to these shapes.
    """
    root=schema if root is None else root
    allowed={'$schema','$id','$defs','title','description','$ref','type','const','enum','required','properties','additionalProperties','items','minItems','minLength','minimum','pattern'}
    unknown=set(schema)-allowed
    if unknown:raise ValueError(f'unsupported schema keywords {where}: {sorted(unknown)}')
    if '$ref' in schema:
        ref=schema['$ref']
        if not ref.startswith('#/'):raise ValueError('only local schema references are supported')
        target=root
        for part in ref[2:].split('/'):target=target[part.replace('~1','/').replace('~0','~')]
        return validate_shape(value,target,where,root)
    types=schema.get('type');types=types if isinstance(types,list) else [types] if types else []
    checks={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),'integer':lambda x:isinstance(x,int) and not isinstance(x,bool),'number':lambda x:isinstance(x,(int,float)) and not isinstance(x,bool),'boolean':lambda x:isinstance(x,bool),'null':lambda x:x is None}
    if types and not any(checks[t](value) for t in types):raise ValueError(f'{where}: expected {types}')
    if 'const' in schema and canonical(value)!=canonical(schema['const']):raise ValueError(f'{where}: expected {schema["const"]!r}')
    if 'enum' in schema and not any(canonical(value)==canonical(option) for option in schema['enum']):raise ValueError(f'{where}: value is not in enum')
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0):raise ValueError(f'{where}: text is empty or too short')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:raise ValueError(f'{where}: pattern mismatch')
    if isinstance(value,(int,float)) and not isinstance(value,bool) and 'minimum' in schema and value<schema['minimum']:raise ValueError(f'{where}: below minimum')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0):raise ValueError(f'{where}: array too short')
        for n,item in enumerate(value):
            if 'items' in schema:validate_shape(item,schema['items'],f'{where}[{n}]',root)
    if isinstance(value,dict):
        for key in schema.get('required',[]):
            if key not in value:raise ValueError(f'{where}: missing {key}')
        properties=schema.get('properties',{})
        for key,item in value.items():
            if key in properties:validate_shape(item,properties[key],where+'.'+key,root)
            elif schema.get('additionalProperties') is False:raise ValueError(f'{where}: unknown property {key}')
            elif isinstance(schema.get('additionalProperties'),dict):validate_shape(item,schema['additionalProperties'],where+'.'+key,root)
