"""Custody-only bridge for W-internals-B's thinner E101 private join.

The scientific implementation at f6ba5964f remains byte-for-byte pinned.
No private join is copied, rewritten or published.
"""
import argparse
from . import e101
from .common import *
SCIENCE='f6ba5964f1c3c2fe0a8096ab1ddc673b01c73852'
REQUIRED={'id','item_id','row','reader','condition','alpha','text','property','values','target'}
EXTRA={'opaque_id','score','redacted'}

def merge(rows,scored):
    original=core.unique(rows);judged=core.unique(scored)
    require(set(original)==set(judged),'exact acquisition/judgment identities')
    merged=[]
    for key,x in judged.items():
        o=original[key]
        require(REQUIRED<=set(x),'complete thin private identity/target/text')
        require(set(x)<=set(o)|EXTRA,'unexpected private fields')
        require(all(x[k]==o[k] for k in set(x)&set(o)),'private/source overlapping fields differ')
        merged.append(dict(o,**{k:x[k] for k in EXTRA}))
    return merged

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed()
    for rel in ('projects/g_agreement/analysis_late/e101.py','projects/g_agreement/analysis_late/common.py','projects/g_agreement/understand/wmech2/core.py'):
        blob=subprocess.check_output(['git','show',SCIENCE+':'+rel],cwd=ROOT)
        require(hashlib.sha256(blob).hexdigest()==sha(ROOT/rel),'frozen scientific source changed')
    s=read(a.spec);require(s['scope']=='descriptive_two_cell' and s['cohort']=='steered_flipped','frozen descriptive scope')
    require(not s.get('baselines') and not s.get('operational_not_run'),'exact two cells, optional baseline absent')
    bp=Path(s['blind'])/'BLIND_SEAL.json';blind=verify(bp,s['blind_sha256'])
    verify(Path(s['judgments'])/'JUDGMENT_SEAL.json',s['judgment_sha256'])
    require(sha(s['private'])==s['private_sha256']==blind['private_sha256'],'private custody')
    require(sha(s['judge_inputs'])==blind['output_seal_sha256'],'judge input binding')
    rows,doses,targets=e101.acquire(s)
    scored,jhash=core.load_codes(dict(s,output_sha256=blind['output_seal_sha256']))
    merged=merge(rows,scored)
    import matplotlib
    out=reserve('E101',s,commit)
    result=e101.analyze(merged,doses,targets,s['cohort'],descriptive=True)
    result['judgment_sha256']=jhash;result['scientific_adapter_commit']=SCIENCE
    finish('E101',s,commit,result,out,lambda dest:e101.figure(result,dest/'B_VS_REPORT.png'))
if __name__=='__main__':main()
