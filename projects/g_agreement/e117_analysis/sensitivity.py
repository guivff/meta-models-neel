"""Source-bound privacy exclusion; no fits, new cohorts or guard."""
from copy import deepcopy
from pathlib import Path
from .adapter import c, analyze, ROWS, ALPHAS, ARMS

AUDIT_SHA = 'fc4500416ef77fd8fbddb5f089779cd450dff16da0781d4d88e937938a14fe24'
MAP_SEAL_SHA = '1bb216c5b42db1bdb35c154272bf73dfdbf142572563e9ea4231a5ca6bafd8eb'


def load_map(spec):
    p=Path(spec['privacy_sensitivity_seal'])
    c.require(spec['privacy_sensitivity_sha256']==MAP_SEAL_SHA,'exact delivered source-only map')
    s=c.verify(p,MAP_SEAL_SHA)
    c.require(s['experiment']=='E117' and s['affected']==8 and s['original_audit_sha256']==AUDIT_SHA,'original audit census')
    for source in s['source_seals']: c.verify(source['seal'],source['sha256'])
    rows=c.read(p.parent/'SENSITIVITY_MAP.PRIVATE.json')
    c.require(len(rows)==len({r['judgment_id'] for r in rows})==8,'eight unique affected records')
    return rows


def mask(items, mapping):
    copied=deepcopy(items); index={}; counts={row:0 for row in ROWS}
    for x in copied:
        for alpha in ALPHAS:
            for arm in ARMS:
                z=x['arms'][alpha][arm]; ident=z['judgment_id']
                c.require(ident not in index,'unique original judgment IDs')
                index[ident]=(x,alpha,arm,z)
    seen=set()
    for r in mapping:
        ident=r['judgment_id'];c.require(ident in index and ident not in seen,'exact unique affected judgment join');seen.add(ident)
        x,alpha,arm,z=index[ident]
        c.require(x['id']==r['original_e113_item_id'] and x['row']==r['row'] and alpha==r['alpha'] and arm==r['arm'],'source-bound item/row/dose/arm')
        c.require(z['text_sha256'] in (r['original_audit']['original_readout_sha256'],r['original_audit']['judge_readout_sha256']),'original or judge-copy source text hash')
        z['score']=None;counts[x['row']]+=1
    return copied,counts


def report(items,mapping):
    masked,counts=mask(items,mapping)
    result=analyze(masked)
    return dict(experiment='E117',authority='standing privacy-guard ruling79f63fe0',redacted_records=len(mapping),redacted_by_row=counts,policy='Mask only affected readout scores; retain all original paired items, native token/norm diagnostics and frozen degeneracy exclusions. No new degeneracy assigned for a privacy exclusion.',result=result)
