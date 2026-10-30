"""E86 sealed normalized source joins; no generation, judging or prior analysis replay."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import analyze
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e86/ANALYSIS_ONCE.json')

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest()==sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

SCIENCE_DIGEST='cfa46523e1fe50337113679fbdada86568a0e6e92348088e28f5a978175fa075'
RELEASE_DIGEST='a13b247655ff2d65d69933c6bb20b3b3b67a933232a6adcdf0f864ea0097f38a'
PREFLIGHT=ROOT/'results/g_agreement/i2/E86_FULL_JUDGE_CPU_PREFLIGHT.json'

def evaluate(meta,code,text):
    if code is None:return dict(meta,truth=None,wrong=None,named=None,truth_score=None)
    require(code['id']==meta['id'],'judgment identity')
    val=core.score(code,'A',text)
    if val is None:return dict(meta,truth=None,wrong=None,named=None,truth_score=None)
    named=code['category']=='states_value'
    return dict(meta,truth=named and 'A' in code['values'],wrong=named and 'B' in code['values'],named=named,truth_score=val)

def original_ids(ids):
    return set(sorted(ids,key=lambda x:hashlib.sha256(f'20261028:E86:{x}'.encode()).digest())[:(len(ids)+3)//4])

def inputs(s):
    pre=read(PREFLIGHT)
    require(sha(s['private_join'])==pre['private_join_sha256'],'original private join')
    meta=core.unique(read(s['private_join']));require(len(meta)==800,'all800 released readouts')
    for x in meta.values():
        require(x['reader'] in ('oracle','nla') and x['arm'] in ('honest','role') and x['subset']=='yn' and x['split']=='test' and x['correct_value']=='A','registered released-test scope and truth-first order')
    for reader in ('oracle','nla'):
        for arm in ('honest','role'):
            xs=[x for x in meta.values() if x['reader']==reader and x['arm']==arm]
            require(len(xs)==200 and len({x['source_id'] for x in xs})==200,'200 unique source items per cell')
    require(sha(s['release'])==RELEASE_DIGEST,'original release bytes')
    release=read(s['release']);require(set(release['released_ids'])=={x['capture_public_id'] for x in meta.values()} and len(release['released_ids'])==400,'exact400 released capture identities')
    # Original CPU-prepared packet fixes source/release and original-sample scope.
    ps=core.verify(s['packet_source_seal'],pre['source_seal_sha256'])
    require(ps['scientific_output_seal_sha256']==SCIENCE_DIGEST and ps['release_sha256']==RELEASE_DIGEST,'original retained scientific release')
    require(ps['complete'] is True and ps['behaviour_gate_verified'] is True and ps['value_order']=='truth_then_lie','original gates/order')
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    require(seal['experiment']=='E86' and seal['status']=='COMPLETE' and seal['packet_source_sha256']==pre['source_seal_sha256'] and seal['private_join_sha256']==pre['private_join_sha256'],'complete original bank binding')
    require(seal['route_verified'] is True and seal['redaction_audit_complete'] is True,'existing route/privacy receipts')
    require({'MEASUREMENTS.json','DIAGNOSTICS.json'}<=set(seal['files']),'sealed pointer manifests')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    require(any(x['sha256']==ps['scientific_output_seal_sha256'] for x in sources),'retained scientific seal verified as original source')
    def resolve(ref):
        ix=ref['seal_index'];require(type(ix) is int and 0<=ix<len(ss),'source index')
        require(ref['member'] in ss[ix]['files'],'original sealed member')
        key=(ix,ref['member'])
        if key not in cache:cache[key]=read(Path(sources[ix]['seal']).parent/ref['member'])
        v=cache[key]
        for k in ref['keys']:v=v[k]
        return v
    ms=core.unique(read(op.parent/'MEASUREMENTS.json'));require(set(ms)==set(meta),'exact800 judgment grid')
    wanted=original_ids(list(meta));require(set(seal['original_subsample_ids'])==wanted,'frozen seeded25percent original sample')
    rows=[];old=[]
    for ident,x in meta.items():
        f=ms[ident]['fields'];require(set(f)==({'text','code','original_code'} if ident in wanted else {'text','code'}),'exact source fields')
        # Do not propagate truth strings/private identities to result rows.
        m=dict(id=ident,reader=x['reader'],arm=x['arm']);text=resolve(f['text'])
        rows.append(evaluate(m,resolve(f['code']),text))
        if ident in wanted:old.append(evaluate(m,resolve(f['original_code']),text))
    refs=read(op.parent/'DIAGNOSTICS.json')
    require(set(refs)=={'achieved_counts','truth_probes'},'original gate counts and per-arm truth probes')
    ds={k:resolve(v) for k,v in refs.items()}
    counts=ds['achieved_counts'];require(set(counts)=={a+'/'+b for a in ('open','yn') for b in ('honest','lie','role')},'all gate subsets and arms disclosed')
    for k,v in counts.items():require(set(v)=={'dev','test','released_test'} and all(type(n) is int and n>=0 for n in v.values()),'aggregate achieved counts only')
    require(counts['yn/honest']['released_test']==counts['yn/role']['released_test']==200 and all(v['released_test']==0 for k,v in counts.items() if k not in ('yn/honest','yn/role')),'no unreleased-arm promotion')
    probes=ds['truth_probes'];require(set(probes)=={arm+'/'+str(l) for arm in ('honest','lie','role') for l in (42,44)},'binary truth probes per arm/site')
    for v in probes.values():
        require(set(v)=={'status','dev_auroc','test_auroc'} and v['status'] in ('COMPLETE','NOT EVALUABLE','NOT RUN'),'probe aggregate schema')
        for k in ('dev_auroc','test_auroc'):require(v[k] is None or type(v[k]) in (int,float) and 0<=v[k]<=1,'AUROC numeric or explicit missing')
    return rows,old,wanted,ds

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec);rows,old,wanted,ds=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    write(out/'RESULTS.json',analyze(rows,old,wanted,ds));write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E86',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'])
if __name__=='__main__':main()
