"""CPU-only custody, blind export and paired inference for sealed Track Q runs."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import unicodedata
import re
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')

def verify(path, digest):
    path = Path(path)
    require(sha(path) == digest, 'seal digest mismatch')
    s = read(path)
    require(isinstance(s.get('files'), dict) and s['files'], 'nonempty sealed inventory')
    for name, expected in s['files'].items():
        p = (path.parent / name).resolve()
        require(p.is_relative_to(path.parent.resolve()), 'seal path escapes root')
        if isinstance(expected, dict):
            expected = expected['sha256']
        require(sha(p) == expected, 'sealed member mismatch: '+name)
    return s

def seal(folder, name, **metadata):
    folder = Path(folder)
    write(folder/name, dict(metadata, files={str(p.relative_to(folder)): sha(p)
          for p in sorted(folder.rglob('*')) if p.is_file() and p.name != name}))

def committed():
    """Refuse production IO until this complete adapter is committed and unchanged."""
    for p in sorted(HERE.iterdir()):
        if p.suffix not in ('.py', '.json', '.md'):
            continue
        rel = str(p.relative_to(ROOT))
        data = subprocess.check_output(['git', 'show', 'HEAD:'+rel], cwd=ROOT)
        require(hashlib.sha256(data).hexdigest() == sha(p), 'uncommitted adapter: '+rel)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

def unique(rows, key='id'):
    ids = [x[key] for x in rows]
    require(len(ids) == len(set(ids)), 'duplicate identity')
    return {x[key]: x for x in rows}

def normalize(text):
    quotes = dict.fromkeys('‘’‚‛', "'") | dict.fromkeys('“”„‟«»', '"')
    return re.sub(r'\s+', ' ', ''.join(quotes.get(c, '-' if unicodedata.category(c)=='Pd' else c)
                                      for c in text)).strip().casefold()

def score(code, target, text):
    require(set(code)=={'id','category','values','evidence'}, 'judgment fields')
    require(target in ('A','B'), 'binary private target')
    if code['category']=='UNPARSEABLE':
        require(code['values']==[] and code['evidence']=='', 'missing sentinel')
        return None
    require(code['category'] in ('states_value','names_property_without_value','exhibits','silent'), 'category')
    require(code['values'] in ([],['A'],['B'],['A','B'],['B','A']), 'values')
    require(bool(code['values']) == (code['category']=='states_value'), 'value/category')
    require(isinstance(code['evidence'], str) and normalize(code['evidence']) in normalize(text), 'evidence substring')
    require(bool(code['evidence']) == (code['category']!='silent'), 'evidence presence')
    return 0 if len(code['values'])!=1 else 1 if target in code['values'] else -1

def stats(values, other=None):
    """Paired item resampling; retain separate missing masks, no complete-case substitution."""
    ids = sorted(values)
    if other is not None:
        require(set(ids)==set(other), 'paired item grid differs')
    x = np.array([np.nan if values[k] is None else values[k] for k in ids], dtype=float)
    y = None if other is None else np.array([np.nan if other[k] is None else other[k] for k in ids], dtype=float)
    n = len(ids)
    result = dict(total=n, kept=int(np.isfinite(x).sum()), UNPARSEABLE=int(np.isnan(x).sum()))
    result['over_5_percent'] = 20*result['UNPARSEABLE'] > n
    if not n or not np.isfinite(x).any() or (y is not None and not np.isfinite(y).any()):
        return dict(result, estimate=None, CI95=None)
    point = float(np.nanmean(x) - (0 if y is None else np.nanmean(y)))
    ix = np.random.default_rng(20261027).integers(0,n,(2000,n))
    def means(z):
        z=z[ix]; count=np.isfinite(z).sum(axis=1)
        return np.divide(np.nansum(z,axis=1),count,out=np.full(2000,np.nan),where=count>0)
    draws=means(x)-(0 if y is None else means(y))
    ci=np.quantile(draws,[.025,.975]).tolist() if np.isfinite(draws).all() else None
    return dict(result, estimate=point, CI95=ci)

def export(rows, dest, private, output_digest, code_commit):
    dest, private = Path(dest), Path(private)
    require(not private.resolve().is_relative_to(dest.resolve()), 'private/public separation')
    require(not dest.exists() and not private.exists(), 'blind export already exists')
    unique(rows)
    packet, join = [], []
    rubric=(HERE/'RUBRIC.md').read_text()
    for i in np.random.default_rng(20261028).permutation(len(rows)):
        x=rows[int(i)]; opaque=secrets.token_hex(16)
        packet.append(dict(id=opaque, property=x['property'], values=x['values'], readout=x['text']))
        join.append(dict(x, opaque_id=opaque))
    dest.mkdir(parents=True, exist_ok=False)
    private.parent.mkdir(parents=True, exist_ok=True)
    fd=os.open(private, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(join,f,allow_nan=False)
    write(dest/'JUDGE_PACKET.json',packet)
    (dest/'RUBRIC.md').write_text(rubric)
    # Exact existing adapter402 wire format; no private fields enter the route.
    def render(v):
        return ' / '.join(v) if isinstance(v,list) else v
    wire=[dict(id=x['id'],readout=x['readout'],rubric=rubric+'\n\nProperty: '+x['property']+
               '\nA: '+render(x['values']['A'])+'\nB: '+render(x['values']['B'])+'\n') for x in packet]
    write(dest/'WIRE_PACKET.json',wire)
    seal(dest,'BLIND_SEAL.json',output_seal_sha256=output_digest,private_sha256=sha(private),code_commit=code_commit,
         route_owner='W-internals',status='AWAITING_REGISTERED_ROUTE',records=len(rows))

def load_codes(s):
    blind=Path(s['blind']); bp=blind/'BLIND_SEAL.json'; b=verify(bp,sha(bp))
    require(b['output_seal_sha256']==s['output_sha256'] and b['private_sha256']==sha(s['private']), 'blind binding')
    js=Path(s['judgments'])/'JUDGMENT_SEAL.json'
    j=verify(js,sha(js))
    require(j['blind_seal_sha256']==sha(bp), 'judgment must bind original blind seal')
    require(j.get('route_verified') is True and j.get('redaction_audit_complete') is True,
            'W-internals route and privacy audit receipt required')
    rows=read(s['private']); codes=unique(read(js.parent/'JUDGMENTS.json'))
    require(set(codes)=={x['opaque_id'] for x in rows},'complete judgment grid')
    redacted=set(j['redacted_opaque_ids'])
    require(redacted<=set(codes),'redaction IDs outside packet')
    for x in rows:
        x['score']=score(codes[x['opaque_id']],x['target'],x['text'])
        x['redacted']=x['opaque_id'] in redacted
    return rows, sha(js)

def claim(s, commit):
    """Fixed experiment-global guard in the original worker's custody root."""
    out=Path(s['analysis']); require(not out.exists(),'analysis output exists')
    guard=Path(s['guard']); guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:
        json.dump(dict(code_commit=commit,output_seal_sha256=s['output_sha256']),f)
    out.mkdir(parents=True,exist_ok=False)
    return out
