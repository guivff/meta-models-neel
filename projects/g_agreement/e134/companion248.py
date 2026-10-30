"""§248 B exploratory supplement; separate claim, frozen T7 source/policies."""
import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from .policy import predict,wilson,score,DRAWS,SEED
ROOT=Path(__file__).resolve().parents[3]
OUTCOMES=('correct','false','abstain')
RULES=('PALL','P44','P52','P60')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def state(pred,truth):return 'abstain' if pred is None else 'correct' if pred==truth else 'false'
def analyze(rows,original,draws=DRAWS,seed=SEED):
    if len({r['item_id']for r in rows})!=len(rows):raise ValueError('one original prompt per bootstrap item')
    if any(set(r['readings'])!={44,52,60} for r in rows):raise ValueError('complete same three layers')
    outcomes={rule:[state(predict(rule,r['readings']),r['truth'])for r in rows]for rule in RULES}
    precision={}
    for rule,values in outcomes.items():
        n=len(values);correct=values.count('correct');false=values.count('false');claims=correct+false
        old=original['scores'][rule]['metrics']
        if any(old[k]['count']!=v or old[k]['denominator']!=n for k,v in [('accuracy',correct),('false_claim_rate',false),('coverage',claims)]):raise ValueError('frozen original T7 aggregate mismatch')
        precision[rule]=dict(correct=correct,false=false,claims=claims,total=n,coverage=claims/n,estimate=correct/claims if claims else None,Wilson95=wilson(correct,claims))
    table=[[sum(a==x and b==y for a,b in zip(outcomes['PALL'],outcomes['P60'])) for y in OUTCOMES]for x in OUTCOMES]
    arr=np.array([[int(a=='correct')-int(b=='correct'),int(a=='false')-int(b=='false')]for a,b in zip(outcomes['PALL'],outcomes['P60'])],dtype=float)
    rng=np.random.default_rng(seed);boot=np.array([arr[rng.integers(0,len(rows),len(rows))].mean(axis=0)for _ in range(draws)])
    diffs={name:dict(estimate=float(arr[:,i].mean()),item_bootstrap95=np.quantile(boot[:,i],[.025,.975]).tolist(),defined_draws=draws,undefined_draws=0)for i,name in enumerate(('accuracy_PALL_minus_P60','false_claim_PALL_minus_P60'))}
    conservative=score(rows,'PAGREE',draws,seed)
    m=conservative['metrics'];k=m['accuracy']['count'];n=m['coverage']['count']
    conservative['precision_given_claim']=dict(correct=k,claims=n,estimate=k/n if n else None,Wilson95=wilson(k,n))
    return dict(experiment='E134',supplement='§248 B',exploratory_post_hoc=True,n_prompts=len(rows),paired_differences=diffs,outcome_table=dict(rows='PALL',columns='P60',order=list(OUTCOMES),counts=table),precision_given_claim=precision,PAGREE=conservative,bootstrap=dict(draws=draws,seed=seed,unit='original E133 prompt/item',paired=True),no_policy_selection=True)
def run(planpath):
    planpath=Path(planpath);rel=str(planpath.resolve().relative_to(ROOT));raw=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)
    if raw!=planpath.read_bytes():raise ValueError('committed exact plan required')
    plan=json.loads(raw)
    for pin in plan['pins']:
        if sha(pin['path'])!=pin['sha256']:raise ValueError('frozen source/input pin')
    for rel in plan['source_files']:
        p=ROOT/rel
        if subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)!=p.read_bytes():raise ValueError('committed source bytes')
    rows=json.loads(Path(plan['rows']).read_text())['T7']
    for r in rows:r['readings']={int(k):v for k,v in r['readings'].items()}
    if len(rows)!=100:raise ValueError('original100 T7 prompts')
    original=json.loads(Path(plan['original_results']).read_text())
    guard=Path(plan['guard']);out=Path(plan['output'])
    if out.exists()or guard.exists():raise FileExistsError('supplement already claimed')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    with guard.open('x')as f:json.dump(dict(supplement='§248 B',claimed_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(planpath),source_commit=commit),f)
    out.mkdir();write(out/'RESULTS.json',analyze(rows,original))
    write(out/'ANALYSIS_SEAL.json',dict(experiment='E134',supplement='§248 B',status='COMPLETE_ONCE',source_commit=commit,plan_sha256=sha(planpath),completed_utc=datetime.now(timezone.utc).isoformat(),files={'RESULTS.json':sha(out/'RESULTS.json')}))
    return out
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);a=p.parse_args();print(run(a.plan))
