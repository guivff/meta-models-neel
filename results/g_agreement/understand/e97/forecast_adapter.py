"""E97 operational admission only; unchanged R3b channel and publisher kernels."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require_scope(plan,receipt,rows):
 if receipt.get('experiment')!='E97' or receipt.get('issuer')!='integrator' or receipt.get('status')!='VERIFIED_CAPTURE_ONLY':raise ValueError('I-5 verified capture-only receipt required')
 if receipt.get('reviewer_correction_passed')is not True or not receipt.get('reviewer_correction_receipt_sha256'):raise ValueError('R-5 v2 correction review still held')
 if receipt.get('original_bank_seal_sha256')!='2afa89f0e551274b82368075338f7b117dcbbe97b403bf4a29d0a6b442ea4f08':raise ValueError('exact revised bank required; v1 is superseded')
 if plan.get('experiment')!='E97' or plan.get('layer')!=44 or plan.get('split')!='test':raise ValueError('E97 standard R3b block44 test plan')
 units=plan['units']
 if len(units)!=40 or {x['id']for x in units}!=set(rows)or any(x['source_row']!=x['id']or x['binary']is not True for x in units):raise ValueError('all40 new binary properties, one unit each')
 if any(len(x['item_ids'])!=84 for x in units):raise ValueError('84 tests per unit')
 if any(receipt.get(k)is not False for k in ['reader_outputs_opened_at_registration','reader_outputs_opened_before_forecast']):raise ValueError('prospective forecast requires unopened outputs')
 if receipt.get('readers_held_until_forecast_commit')is not True:raise ValueError('explicit output hold required')
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['channel','forecast']);args=p.parse_args()
 pin=read(HERE/'INTAKE_V2.json')
 for f,h in pin['sources'].items():
  if sha(f)!=h:raise ValueError('frozen v2 input changed')
 channel=ROOT/'results/g_agreement/understand/e57/jlens';r3b=ROOT/'results/g_agreement/understand/e52/r3b'
 sys.path[:0]=[str(channel),str(r3b)]
 import cpu_job,forecast_once
 cpu_job.committed(Path(__file__));cpu_job.committed(HERE/'INTAKE_V2.json')
 cpu_job.verify(ROOT,read(r3b/'CODE_SEAL_2026-10-27.json')['files'])
 plan=read(channel/'E97_INPUT_PLAN.json');receipt=read(ROOT/'cache/g_agreement/understand/e52/r3b/E97_DELIVERY.json')
 require_scope(plan,receipt,pin['rows']);cpu_job.validate_units(plan['units'],read(plan['records']['path']),read(plan['order']['path']))
 # Only the CLI allowlist is bypassed. No scientific function, constants,
 # basis, pursuit, null, G3 or publisher mapping is patched.
 return cpu_job.run('E97')if args.stage=='channel'else forecast_once.run('E97')
if __name__=='__main__':raise SystemExit(main())
