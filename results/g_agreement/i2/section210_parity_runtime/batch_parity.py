"""Registered report-only parity for E85/E91/E92/E86/E82 (87ee1900)."""
import hashlib
import json
from contract import require, write
AUTHORITY='87ee19008919ac30889d9f47e6572503ad032b88'

def first_difference(a,b):
    for i,(x,y) in enumerate(zip(a,b)):
        if x!=y:return i
    return min(len(a),len(b)) if len(a)!=len(b) else None

def check_outputs(batched, serial, path, ids, batch_size):
    require(len(batched)==len(serial)==len(ids) and len(ids)>0,'parity coverage')
    # allow_nan=False rejects non-finite outputs; this remains a fatal error.
    encode=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')
    rows=[]
    for ident,a,b in zip(ids,batched,serial):
        x,y=encode(a),encode(b)
        rows.append(dict(id=ident,batched_sha256=hashlib.sha256(x).hexdigest(),
            serial_sha256=hashlib.sha256(y).hexdigest(),equal=x==y,
            first_divergence_position=first_difference(x,y),position_unit='canonical JSON UTF-8 byte',
            batched_bytes=len(x),serial_bytes=len(y)))
    matches=sum(row['equal'] for row in rows)
    write(path,dict(status='PASS' if matches==len(rows) else 'MISMATCH_REPORTED',
        authority=AUTHORITY,mismatch_is_gate=False,n=len(rows),matches=matches,mismatches=len(rows)-matches,
        production_batch_size=batch_size,exact_serialized_output=True,records=rows))

def trim_generated(tokens,eos_ids):
    """Remove only batch padding after the first terminal EOS; keep EOS itself."""
    for i,token in enumerate(tokens):
        if token in eos_ids:return tokens[:i+1]
    return tokens
