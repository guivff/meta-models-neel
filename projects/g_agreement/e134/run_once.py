"""CPU-only, separately guarded E134 training and prospective T7 execution."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
from .policy import evaluate,score,SEED,DRAWS
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def committed(p,commit='HEAD'):
    rel=str(Path(p).resolve().relative_to(ROOT))
    raw=subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT)
    if hashlib.sha256(raw).hexdigest()!=sha(p):raise ValueError('uncommitted or changed file '+rel)

def load(planpath):
    committed(planpath)
    for p in HERE.glob('*.py'):committed(p)
    plan=json.loads(Path(planpath).read_text())
    if plan['experiment']!='E134' or plan['normalization_status']!='AUTHORIZED_FROZEN':raise ValueError('source normalization not frozen')
    for pin in plan['pins']:
        if sha(pin['path'])!=pin['sha256']:raise ValueError('source pin mismatch')
    # Establish the frozen prospective selection before opening any T7 rows.
    if plan.get('phase')=='T7':
        sp=Path(plan['selection']['path']);committed(sp,plan['selection']['commit'])
        if sha(sp)!=plan['selection']['sha256']:raise ValueError('selection pin')
        custody=plan['E133_custody']
        if not custody['selected_rule_committed_before_any_output_opened']:raise ValueError('prospective custody')
        if sha(custody['receipt'])!=custody['receipt_sha256']:raise ValueError('E133 receipt')
    rows_pin=plan['rows']
    if sha(rows_pin['path'])!=rows_pin['sha256']:raise ValueError('normalized row hash mismatch')
    data=json.loads(Path(rows_pin['path']).read_text())
    for rows in data.values():
        if not rows:raise ValueError('nonempty bound state type required')
        if len({x['id'] for x in rows})!=len(rows):raise ValueError('duplicate normalized identity')
        for x in rows:
            x['readings']={int(k):v for k,v in x['readings'].items()}
            if not x.get('source_refs') or not x.get('truth_ref'):raise ValueError('per-item original lineage required')
            if not isinstance(x.get('truth'),str) or not x['truth']:raise ValueError('behaviour-grounded scalar truth must be bound before claim')
            if not x['readings'] or any(k not in (44,52,60) or (v is not None and not isinstance(v,str)) for k,v in x['readings'].items()):raise ValueError('bound scalar readout grid required before claim')
            if type(x.get('accuracy_eligible',True)) is not bool:raise ValueError('accuracy eligibility boolean')
            if 'matcher_matches' in x:x['matcher_matches']={int(k):v for k,v in x['matcher_matches'].items()}
    if plan.get('phase')=='T1_T6':
        if set(data)!={f'T{i}' for i in range(1,7)}:raise ValueError('exact six-type intake required')
        from .matcher import coverage_gate
        coverage_gate(data['T4'])  # Validate matcher lineage shape before any claim; no policy score.
    return plan,data

def claim(p,details):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(details,f)

def run(planpath):
    plan,data=load(planpath);commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    phase=plan['phase'];out=Path(plan['output']);guard=Path(plan['guard'])
    if phase not in ('T1_T6','T7'):raise ValueError('phase')
    if out.exists() or guard.exists():raise FileExistsError('original phase already claimed or output exists')
    selection=None
    if phase=='T7':
        if set(data)!={'T7'}:raise ValueError('T7 only')
        sp=Path(plan['selection']['path']);sc=plan['selection']['commit'];committed(sp,sc)
        if sha(sp)!=plan['selection']['sha256']:raise ValueError('selection pin')
        selection=json.loads(sp.read_text())
        custody=plan['E133_custody']
        if not custody['selected_rule_committed_before_any_output_opened']:raise ValueError('prospective custody not established')
        if not custody['receipt_sha256'] or sha(custody['receipt'])!=custody['receipt_sha256']:raise ValueError('actual E133 custody receipt')
    elif set(data)!={f'T{i}' for i in range(1,7)}:raise ValueError('all six training types required')
    claim(guard,dict(experiment='E134',phase=phase,plan_sha256=sha(planpath),source_commit=commit,claimed_utc=datetime.now(timezone.utc).isoformat()))
    out.mkdir(parents=True)
    if phase=='T1_T6':
        result=evaluate(data)
        write(out/'SELECTION_SEAL.json',dict(experiment='E134',source_commit=commit,plan_sha256=sha(planpath),input_types=sorted(data),training_types=result['selection_types'],excluded_selection_types=result['excluded_selection_types'],adaptive_rule=result['selection']['adaptive'],fixed_rule=result['selection']['fixed'],selection=result['selection'],E133_outputs_opened=False,selected_utc=datetime.now(timezone.utc).isoformat()))
    else:
        rules=tuple(dict.fromkeys([selection['adaptive_rule'],'P44','P52','P60']))
        result=dict(experiment='E134',prospective=True,selection=plan['selection'],scores={r:score(data['T7'],r) for r in rules},bootstrap=dict(draws=DRAWS,seed=SEED,unit='original E133 item'))
    write(out/'RESULTS.json',result)
    write(out/'ANALYSIS_SEAL.json',dict(experiment='E134',phase=phase,status='COMPLETE_ONCE',source_commit=commit,plan_sha256=sha(planpath),files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);a=p.parse_args();print(run(a.plan))
