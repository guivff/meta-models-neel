"""Complete only the 72 E56 direction-control records omitted by text loader."""
import argparse,json,time
from pathlib import Path
from audit import HERE,ROOT,CACHE,read,sha,write,signed,bounds
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 spec=read(ROOT/'results/g_agreement/understand/analysis402/E56_SPEC.json')
 paths={k:Path(spec[k])for k in ['private_key','judgments']}
 paths['directions']=Path(spec['inputs'])/'injection/ITEMS.json'
 paths['prior']=HERE/'cpu_once/RESULTS.json'
 planpath=HERE/'CONTROL_COMPLETION_PLAN.json'
 if not a.run:
  write(planpath,dict(scope='72 E56 injection direction readouts only; no existing CPU audit cells repeated',sources={str(p):sha(p)for p in paths.values()},code_sha256=sha(__file__),prior_result_seal_sha256=sha(HERE/'cpu_once/RESULT_SEAL.json')));return
 import subprocess
 assert subprocess.check_output(['git','show','HEAD:'+str(planpath.relative_to(ROOT))],cwd=ROOT)==planpath.read_bytes()
 plan=read(planpath)
 assert plan['code_sha256']==sha(__file__)
 for p,h in plan['sources'].items():assert sha(p)==h
 assert sha(HERE/'cpu_once/RESULT_SEAL.json')==plan['prior_result_seal_sha256']
 directions={x['id']:x for x in read(paths['directions'])['items']};keys=read(paths['private_key']);judges={x['id']:x for x in read(paths['judgments'])}
 selected=[x for x in keys if x['unit_id']in directions];assert len(selected)==72
 write(CACHE/'E56_CONTROLS_ONCE.json',dict(status='CLAIMED_NEVER_RESET',plan_sha256=sha(planpath),started_epoch=time.time()))
 rows=[]
 for x in selected:
  d=directions[x['unit_id']];assert d['variant']in ['A','B']
  reader=x['source_id'].rsplit(':',2)[1]
  rows.append(dict(bank='E56',reader=reader,row=d['row']+'|'+d['arm'],item_id=x['unit_id'],score=signed(judges[x['opaque_id']],int(d['variant']=='A'))))
 result=dict(scope=plan['scope'],n=72,unparseable_bounds=bounds(rows),read_token='NOT APPLICABLE: direct full/J/nonJ activation directions; no token or dev/test prompt split of their own',original_cpu_result_unchanged=True,original_bank_analysis_unchanged=True,GPU_hours=0)
 write(HERE/'CONTROL_COMPLETION.json',result)
 write(HERE/'CONTROL_COMPLETION_SEAL.json',dict(files={'CONTROL_COMPLETION.json':sha(HERE/'CONTROL_COMPLETION.json')},plan_sha256=sha(planpath),claim_sha256=sha(CACHE/'E56_CONTROLS_ONCE.json')))
 print('E56 72 direction-control audit records sealed, no prior audit cell repeated')
if __name__=='__main__':main()
