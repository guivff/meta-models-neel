"""Single claimed E75 invocation: full Qwen primary plus prespecified sensitivity.
The unchanged sealed scorer is called once per fixed panel. Category-provenance
subsets use its unchanged comparison functions; never extend or reset the claim.
"""
import json,hashlib,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def main():
 planpath=HERE/'QWEN_RUN_PLAN.json';plan=read(planpath)
 for rel,h in plan['committed_files'].items():
  f=ROOT/rel;assert sha(f)==h,(rel,'hash')
  assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)==f.read_bytes(),(rel,'uncommitted')
 assert subprocess.check_output(['git','show','HEAD:'+str(planpath.relative_to(ROOT))],cwd=ROOT)==planpath.read_bytes()
 units=read(HERE/'QWEN_BOUND_UNITS.json')
 for f,h in units['source_sha256'].items():assert sha(f)==h,(f,'source changed')
 for f,h in plan['category_sources'].items():assert sha(f)==h,(f,'category changed')
 assert tuple(units['panels'])==('primary','redaction_excluded_sensitivity')
 for panel,rows in units['panels'].items():
  assert len(rows)==90 and sum(r['reader']=='oracle' for r in rows)==55
  assert all(r['category_provenance'] in ['pre_outcome','exploratory_mechanical'] for r in rows)
  assert len({(r['reader'],r['bank'],r['row']) for r in rows})==90
 from score import score,compare,within_category
 outdir=ROOT/'cache/g_agreement/understand/e75/qwen_once';outdir.mkdir(parents=True,exist_ok=True)
 start=time.time()
 with (outdir/'ONCE.json').open('x') as f:
  json.dump(dict(status='CLAIMED_NEVER_RESET',created_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(planpath),input_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),f,indent=2)
 output={'panels':{},'exclusions':units['excluded'],'plan_sha256':sha(planpath),'scorer_sha256':sha(HERE/'score.py'),'interpretation':'R-P1 NOT EVALUABLE: both reader pools have fewer than60 units. All-unit category comparisons with new mappings exploratory; pre-outcome category subset reported separately.','GLM':'R-G2 NOT EVALUABLE; no J forecast, category-only record separate.'}
 for panel,rows in units['panels'].items():
  full=score(rows)
  subsets={}
  for reader in ['oracle','nla']:
   rr=[r for r in rows if r['reader']==reader and r['category_provenance']=='pre_outcome']
   subsets[reader]={'n_pre_outcome':len(rr),'n_exploratory_mechanical':sum(r['reader']==reader for r in rows)-len(rr),'pooled':compare(rr),'within_category':within_category(rr)}
  output['panels'][panel]={'all_units':full,'pre_outcome_category_subset':subsets}
 output['wall_seconds']=time.time()-start
 dump(outdir/'RESULTS.json',output)
 dump(HERE/'QWEN_RESULTS.json',output)
 dump(HERE/'QWEN_RESULT_SEAL.json',{'status':'COMPLETE_ONCE','invocations':1,'scorer_calls':'one primary and one prespecified sensitivity, within single claimed invocation','input_commit':read(outdir/'ONCE.json')['input_commit'],'files':{'QWEN_RESULTS.json':sha(HERE/'QWEN_RESULTS.json')},'claim_sha256':sha(outdir/'ONCE.json'),'plan_sha256':sha(planpath)})
 print('E75 QWEN COMPLETE_ONCE',sha(HERE/'QWEN_RESULTS.json'))
if __name__=='__main__':main()
