"""Seal-gated §205(5) E97 R-T1 watcher; delegates unchanged taxonomy.compare.

No E75 pooling, model, judge or outcome I/O on import. Producer bindings are
finalized only after terminal judgments; this watcher is frozen beforehand.
"""
import argparse, hashlib, json, math, os, subprocess, time, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.e97.taxonomy import compare,TAGS
from projects.g_agreement.ops.i5_e97_row_metrics import row_metrics,old_rubric_summary
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'results/g_agreement/understand/e97/analysis/R_T1_once'
LOCK = ROOT/'cache/g_agreement/understand/e97/rt1/ANALYSIS_ONCE.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write_new(p, value):
    with Path(p).open('x') as f: json.dump(value,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
def validate_units(units):
    if set(units) != {'oracle','nla'}: raise ValueError('both readers required')
    for reader, rows in units.items():
        if len(rows)!=40 or len({r['row'] for r in rows})!=40: raise ValueError('40 frozen rows per reader')
        for row in rows:
            s, ci = row['S'], row['CI95']
            if row['taxonomy'] not in TAGS: raise ValueError('frozen taxonomy tag required')
            if s is None or ci is None:
                if s is not None or ci is not None or row['reported'] is not None: raise ValueError('missing truth must stay undefined')
                continue
            if not -1<=s<=1 or len(ci)!=2 or not all(math.isfinite(x) for x in [s,*ci]) or ci[0]>ci[1]: raise ValueError('finite signed S/CI required')
            if row['reported'] is not (s>=.20 and ci[0]>0): raise ValueError('frozen REPORTED truth convention')
            if row['j_label'] not in ('IN-J','DIFFUSE','OUT-J') or row['j_reported'] is not (row['j_label']=='IN-J'): raise ValueError('frozen J label mapping')
    if {r['row'] for r in units['oracle']}!={r['row'] for r in units['nla']}: raise ValueError('same rows')
    return units

def validate_terminal(receipt):
    if receipt.get('status')!='VERIFIED_COMPLETE_E97_JUDGMENTS' or receipt.get('primary_records')!=6668 or receipt.get('old_rubric_records')!=1667 or receipt.get('native_records')!=6720:
        raise ValueError('full verified terminal grid required')
    if receipt.get('all_member_hashes_verified') is not True or receipt.get('route_privacy_verified') is not True:
        raise ValueError('terminal custody incomplete')

def run(planpath):
    if time.time()>=1793336400: raise ValueError('authorization expired')
    plan=read(planpath)
    required={'projects/g_agreement/ops/i5_e97_rt1_gate.py','projects/g_agreement/ops/i5_e97_row_metrics.py','projects/g_agreement/e97/taxonomy.py','results/g_agreement/understand/e56/job/stats_native.py','results/g_agreement/understand/analysis402/missingness.py','results/g_agreement/understand/e56/job/contract56.py'}
    if not required <= set(plan['code']): raise ValueError('watcher and frozen kernel must be pinned')
    if plan.get('experiment')!='E97_R_T1' or plan.get('registration')!='§205(5)': raise ValueError('scope')
    for ref in plan['refs'].values():
        if sha(ref['path'])!=ref['sha256']: raise ValueError('source/member binding')
    validate_terminal(read(plan['refs']['terminal_receipt']['path']))
    # Require committed source and public final plan before consuming the lock.
    for rel,h in plan['code'].items():
        if sha(ROOT/rel)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)).hexdigest()!=h: raise ValueError('committed source mismatch')
    rel=str(Path(planpath).resolve().relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)!=Path(planpath).read_bytes(): raise ValueError('committed final plan required')
    if LOCK.exists() or OUT.exists(): raise ValueError('once already claimed; no replay')
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    write_new(LOCK,dict(status='CONSUMED',at_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(planpath)))
    # Read truth and forecast joins only after terminal/source gates and claim.
    if plan.get('input_format')=='E97_ITEM_CODES_V1':
        records=read(plan['refs']['item_codes']['path']);old=read(plan['refs']['old_codes']['path']);meta=read(plan['refs']['rowmeta']['path']);forecast=read(plan['refs']['forecast']['path']);affected=read(plan['refs']['affected_ids']['path'])
        panels={'primary':row_metrics(records,meta,forecast),'redaction_excluded_sensitivity':row_metrics(records,meta,forecast,affected)}
    else:
        panels=read(plan['refs']['units']['path'])
    if set(panels)!={'primary','redaction_excluded_sensitivity'}: raise ValueError('required affected-ID exclusion sensitivity')
    result={}
    for panel,units in panels.items():
        units=validate_units(units)
        result[panel]={}
        for k,v in units.items():
            missing=[r['row']for r in v if r['reported']is None]
            comparison=dict(verdict='NOT EVALUABLE',falsifier=None,reason='Reporting truth undefined; no row drop or MISSED coercion',undefined_truth_rows=missing,n=40) if missing else compare(sorted(v,key=lambda r:r['row']))
            result[panel][k]=dict(comparison,rows=v,role=('CONFIRMATORY_R_T1' if k=='oracle' else 'DESCRIPTIVE') if panel=='primary' else 'AFFECTED_EXCLUSION_SENSITIVITY_ONLY')
    if plan.get('input_format')=='E97_ITEM_CODES_V1':
        result['primary']['old_rubric_comparison']=old_rubric_summary(records,old)
        result['redaction_excluded_sensitivity']['old_rubric_comparison']=old_rubric_summary(records,old,affected)
    OUT.mkdir(parents=True,exist_ok=False)
    write_new(OUT/'RESULTS.json',result)
    p=OUT/'RESULTS.json'
    write_new(OUT/'ANALYSIS_SEAL.json',dict(status='COMPLETE_ONCE_REVIEW_PENDING',plan_sha256=sha(planpath),files={'RESULTS.json':sha(p)},first_output=dict(path=str(p),mtime_ns=p.stat().st_mtime_ns),E75_unchanged=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--watch',action='store_true');a=p.parse_args()
    while not a.plan.exists():
        if not a.watch:return
        if time.time()>=1793336400:return
        time.sleep(30)
    run(a.plan)
if __name__=='__main__':main()
