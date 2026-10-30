"""79f63fe0: unchanged guard patterns, decoded values, judge-copy path redaction."""
import hashlib
import json
import re
from projects.g_agreement.readerbench.scoring import require

# Exact E10 privacy.check_wire patterns, in their original order.
PATTERNS=[r'\b(?:hf_|sk-or-v1-|sk-proj-)[A-Za-z0-9_-]{16,}',r'/(?:Users|home|workspace|private|var|tmp|etc)/',r'(?<![A-Za-z])[A-Za-z]:\\[A-Za-z0-9_.-]+',r'\b(?:projects|results|cache)/[A-Za-z0-9_.-]+/',r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+']


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def redact(items,bank,addresses=False):
    copied=[];affected=[]
    for x in items:
        # Keys/tokens and addresses are never masked, including inside a path.
        for value in strings(x):
            require(not any(re.search(PATTERNS[i],value) for i in ((0,) if addresses else (0,4))),
                    'forbidden key/token/address; stop and return to coordinator')
        text=x['readout'];spans=[]
        for pattern in PATTERNS[1:4]:
            for m in re.finditer(pattern,text):
                # Guard patterns identify path roots. Extend only through the path
                # token, never through whitespace or surrounding prose/quotes.
                end=m.end()
                while end<len(text) and text[end] not in '\t\r\n "\'`<>|,;()[]{}':end+=1
                while end>m.end() and text[end-1] in '.!?':end-=1
                spans.append((m.start(),end))
        merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((start,end))
        address_spans=[]
        if addresses:
            for m in re.finditer(r'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?',text):
                if not any(m.start()<end and m.end()>start for start,end in merged):address_spans.append((m.start(),m.end()))
        replacements=[(a,b,'[REDACTED_PATH]') for a,b in merged]+[(a,b,'[REDACTED_ADDRESS]') for a,b in address_spans]
        changed=text
        for start,end,marker in sorted(replacements,reverse=True):changed=changed[:start]+marker+changed[end:]
        copied.append(dict(x,readout=changed))
        if replacements:affected.append(dict(id=x['id'],path_count=len(merged),
            original_readout_sha256=hashlib.sha256(text.encode()).hexdigest(),
            judge_readout_sha256=hashlib.sha256(changed.encode()).hexdigest()))
        if replacements and addresses:affected[-1]['address_count']=len(address_spans)
    audit=dict(authority='79f63fe0',bank=bank,n_records=len(items),
        redacted_records=len(affected),affected=affected,
        sensitivity_required='Report every rule with affected opaque IDs excluded, alongside full-grid result; not computed by judging runner.')
    if addresses:audit['address_authority']='25c32f25'
    return copied,audit


def check_decoded(original_check,batch,wire):
    # Check the actual user payload as decoded JSON, not its JSON-escaped syntax.
    require(json.loads(wire['messages'][1]['content'])==batch,'wire differs from judge copy')
    for value in strings(batch):
        original_check('extract',[dict(id='decoded',readout=value)],wire)
    original_check('extract',[dict(id='system',readout=wire['messages'][0]['content'])],wire)
