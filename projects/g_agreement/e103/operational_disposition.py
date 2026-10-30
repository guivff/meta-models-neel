"""§212 administrative cap disposition; no model, judge, or statistical analysis."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import argparse, hashlib, json, subprocess
ROOT=Path(__file__).resolve().parents[3]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--closeout',type=Path,required=True)
    p.add_argument('--ruling-commit',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    ruling=subprocess.check_output(['git','show',a.ruling_commit+':projects/g_agreement/BRIEF_UNDERSTAND.md'],cwd=ROOT,text=True)
    if '1 GPU-h for E103'not in ruling or 'prior custody + 1.25 × measured need'not in ruling:raise ValueError('Exact committed §212 cap required')
    c=json.loads(a.closeout.read_text())
    if c['experiment']!='E103' or c['status']!='NO_FIT_OPERATIONAL_NOT_SCIENTIFIC_RESULT':raise ValueError('Verified A1 operational closeout required')
    if not all(c[k]is True for k in ['provider_query_null_verified','inputs_deleted','stock_guard_processes_retired','all_output_hashes_verified']):raise ValueError('Closed verified custody required')
    required,completed=c['required_samples'],c['completed_samples']
    if required!=2512 or not 0<=completed<required:raise ValueError('Frozen full bank and partial pilot required')
    prior=Decimal(str(c['charged_seconds_upper']));rate=Decimal(str(c['real_seconds_per_sample']));margin=Decimal('1.25');limit=Decimal(3600)
    if prior<0 or rate<=0:raise ValueError('Positive measured timing required')
    remaining=Decimal(required-completed)*rate
    lower_bound=prior+margin*remaining
    if lower_bound<=limit:raise ValueError('Does not prove NO_FIT; full endpoint admission would be required')
    now=datetime.now(timezone.utc).isoformat()
    result=dict(experiment='E103',status='NOT RUN (operational)',reason='§212 cumulative measured need exceeds 1 GPU-h ceiling',ruling_commit=a.ruling_commit,decision_written_utc=now,
        first_output_utc=c['first_output_utc'],first_output_evidence=c['first_output_evidence'],source_closeout_sha256=sha(a.closeout),source_output_seal_sha256=c['output_seal_sha256'],
        measured_gpu_type=c['gpu_type'],prior_custody_seconds=float(prior),seconds_per_sample=float(rate),remaining_samples=required-completed,
        cumulative_seconds_lower_bound=float(lower_bound),cumulative_gpu_hours_lower_bound=float(lower_bound/3600),ceiling_seconds=3600,margin=1.25,
        inequality_exact_decimal=f'{prior} + 1.25 * ({required-completed} * {rate}) = {lower_bound} > 3600',
        conservative_proof='Even reusing the pilot and excluding every new setup/staging/retrieval second, the full remaining bank cannot fit. No thinning or assumed hardware speedup.',
        registered_source_items=314,registered_samples=2512,retained_diagnostic_samples=completed,complete_eight_sample_source_items=0,
        rules={'R-H2':{'status':'NOT EVALUABLE','reason':'No complete own/mismatched claim-match observations'},'falsifier':{'status':'NOT EVALUABLE','reason':'No estimable own-minus-mismatched contrast'}},
        new_restart_launched=False,additional_model_calls=0,judge_calls=0,statistical_analysis_run=False,once_guard_touched=False,
        new_gpu_spend_usd=0,closed_A1_all_in_upper_usd=c['all_in_usd_upper'],active_reservations_usd=0,
        D4_literal_match='NOT RUN (operational): no complete eight-continuation sets',E99_descriptive_extension_performed=False,
        figure_status='NOT APPLICABLE: no estimable scientific contrast; report operational disposition',
        prior_cap_proposal='Superseded by §212 1GPUh ceiling; not authorized or launched',pilot_disposition='Preserved unjudged as incomplete operational diagnostic evidence; never a negative R-H2 result')
    a.out.mkdir(parents=True,exist_ok=False)
    dest=a.out/'DISPOSITION.json';dest.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    seal=dict(experiment='E103',status='FINAL_OPERATIONAL_DISPOSITION',first_output_utc=c['first_output_utc'],first_output_evidence=c['first_output_evidence'],ruling_commit=a.ruling_commit,files={'DISPOSITION.json':sha(dest)})
    (a.out/'SEAL.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k]for k in ['status','cumulative_gpu_hours_lower_bound','new_restart_launched','rules']}))

if __name__=='__main__':main()
