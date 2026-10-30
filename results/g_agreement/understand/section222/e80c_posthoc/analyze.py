"""§223(2), post hoc CPU analysis of saved E80c vectors and terminal judgments."""
import hashlib, json, random, time
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.e80_analysis.e80c_analysis import verdicts, falls, CONDITIONS
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d): Path(p).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def ci(x):
    s=np.sort(x); return [float(s[50]),float(s[1949])]
def variance(g,w):
    """Trace population covariance for resampled items; w contains item multiplicities."""
    n=w.sum(axis=-1)
    return (w@np.diag(g))/n-np.einsum('bi,ij,bj->b',w,g,w,optimize=True)/(n*n)
def summarize(x,removed,fail=None):
    n=len(x); rng=random.Random(20261028)
    w=np.zeros((2001,n),dtype=np.float64);w[0]=1
    for b in range(1,2001):
        for _ in range(n): w[b,rng.randrange(n)]+=1
    base=variance(x@x.T,w)
    assert np.all(base>0)
    result={}; ratios={}
    for c,d in removed.items():
        share=variance(d@d.T,w)/base
        assert np.all(share>0) and np.all(share<1.00001)
        row=dict(variance_removed_share=float(share[0]),variance_removed_ci95=ci(share[1:]))
        if fail is not None:
            fall=(w@fail[c])/n; ratio=fall/share;ratios[c]=ratio
            row.update(pass_rate_fall=float(fall[0]),pass_rate_fall_ci95=ci(fall[1:]),
                       fall_per_variance_share=float(ratio[0]),fall_per_variance_share_ci95=ci(ratio[1:]))
        result[c]=row
    contrasts={}
    for other in ('random_ablated','PCA_ablated'):
        if ratios:
            d=ratios['J_ablated']-ratios[other]
            contrasts['J_minus_'+other]=dict(estimate=float(d[0]),ci95=ci(d[1:]))
    return dict(n_items=n,conditions=result,normalized_paired_contrasts=contrasts)
def main():
    t=time.monotonic();p=read(HERE/'PLAN.json')
    for f,h in p['pins'].items(): assert sha(f)==h, f
    assert not (HERE/'RESULTS.json').exists()
    spec=read(p['spec']);original=read(p['original_results'])
    packets={x['id']:x for x in read(spec['judge_packets'])}
    items=read(spec['plan'])['item_ids']; assert items==read(p['capture_order'])
    assert items==[x['id'] for x in read(Path(p['ablations'])/'items.json')]
    none=verdicts(read(spec['e80_judgments']),read(spec['e80_readouts']),read(spec['e80_join']),packets,('none',))
    abl=verdicts(read(spec['e80c_judgments']),read(spec['e80c_readouts']),read(spec['e80c_join']),packets,CONDITIONS)
    # The new claim is disjoint from every original forecast/analysis claim.
    guard=ROOT/'cache/g_agreement/understand/section223/e80c_variance/ONCE.json'
    guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f: json.dump(dict(plan_sha256=sha(HERE/'PLAN.json')),f)
    out=dict(status='COMPLETE_ONCE',label='POST HOC / DESCRIPTIVE',registration='§223 item 2',
             bootstrap=dict(draws=2000,seed=20261028,unit='paired item',ci='percentile; original E80c order-statistic convention'),
             R_X3_unchanged=original['R_X3'],readers={})
    for reader,block in [('oracle',44),('nla',42)]:
        x=np.load(Path(p['capture'])/f'acts{block}.npy').astype(np.float64)
        assert x.shape==(518,5120) and np.isfinite(x).all()
        removed={c:x-np.load(Path(p['ablations'])/f'{c}{block}.npy').astype(np.float64) for c in CONDITIONS}
        assert all(np.isfinite(d).all() for d in removed.values())
        cond={c:abl[(reader,c)] for c in CONDITIONS}
        S,keep,fall=falls(none[(reader,'none')],cond,items)
        assert len(keep)==original[reader]['pooled']['n_complete']
        assert fall==original[reader]['pooled']['falls']
        ix=[items.index(i) for i in keep]
        fail={c:np.array([not cond[c][i] for i in keep],dtype=float) for c in CONDITIONS}
        out['readers'][reader]=dict(block=block,label='primary site' if reader=='oracle' else 'exploratory: block-44 bases applied at block 42',
            n_pass_none=len(S),n_excluded_missing=len(S)-len(keep),
            all_sealed_items=summarize(x,removed),
            original_complete_case_pass_none_cohort=summarize(x[ix],{c:d[ix] for c,d in removed.items()},fail))
    out['wall_seconds']=time.monotonic()-t;out['gpu_hours']=0
    write(HERE/'RESULTS.json',out)
    write(HERE/'RESULT_SEAL.json',dict(status='COMPLETE_ONCE',plan_sha256=sha(HERE/'PLAN.json'),files={'RESULTS.json':sha(HERE/'RESULTS.json')}))
    print(json.dumps(out['readers']['oracle'],indent=2))
if __name__=='__main__': main()
