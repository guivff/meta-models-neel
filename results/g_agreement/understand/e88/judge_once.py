"""E88 item5/6 once-only analysis after Track Q terminal seal. No API calls."""
import argparse,hashlib,json,subprocess,time,re
from collections import defaultdict
from pathlib import Path
from audit import HERE,ROOT,CACHE,read,sha,write,signed,rate,kappa
NONBINARY={'focus_none','capacity_list','category_switch'}
def code(j):
 if j is None or j.get('category')=='UNPARSEABLE':return None
 if j['category']=='states_value':return 'states_'+''.join(sorted(j['values']))
 return j['category']
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);a=p.parse_args();plan=read(a.plan)
 assert subprocess.check_output(['git','show','HEAD:'+str(a.plan.relative_to(ROOT))],cwd=ROOT)==a.plan.read_bytes()
 assert plan['code_sha256']==sha(__file__)
 for path,h in plan['sources'].items():assert sha(path)==h
 part=str(plan['part']);assert part in ['5','6']
 request=read(HERE/'JUDGING_REQUEST.json');ref=request['packets'][part];assert sha(ref['path'])==ref['sha256'];wire=read(ref['path']);ids={x['id']for x in wire}
 raw=read(plan['terminal_path']);seal=read(plan['terminal_seal'])
 h=seal['files'][Path(plan['terminal_path']).name];assert sha(plan['terminal_path'])==(h['sha256']if isinstance(h,dict)else h)
 assert len(raw)==len(ids)and {x['id']for x in raw}==ids
 # Track Q must identify the exact wire, rubric, route, terminal grid and spend.
 assert plan['wire_sha256']==ref['sha256']and plan['rubric_sha256']==ref['rubric_sha256']
 assert plan['route_receipt']and plan['judging_owner']=='Track Q'
 join=read(request['private_joins'][part]['path']);assert sha(request['private_joins'][part]['path'])==request['private_joins'][part]['sha256']
 mapped={x['id']:x for x in join};assert set(mapped)==ids
 old=read(CACHE/'CPU_INPUTS_v3.PRIVATE.json')['raw_signed_records']
 inventory=read(CACHE/'ITEM6_INVENTORY_v2.PRIVATE.json')
 e54texts={(x['reader'],x['pair_id']):x['text']for x in inventory if x['bank']=='E54'}
 channels_path=ROOT.parent/'wt-blindspot-internals/results/g_agreement/understand/e5354/E54_CHANNELS.json'
 assert str(channels_path.resolve())in plan['sources']
 channels=read(channels_path)
 import sys;sys.path.insert(0,str(ROOT.parent/'wt-wmech/results/g_agreement/understand/e49/job'));import statements49
 lookup={}
 for x in old:
  key=(x['bank'],x['reader'],x['row'],x['item_id']);assert key not in lookup
  lookup[key]=x
 dest=HERE/('judging_'+part+'_once');dest.mkdir(exist_ok=False)
 write(CACHE/('judging_'+part+'_ONCE.json'),dict(status='CLAIMED_NEVER_RESET',started_epoch=time.time(),plan_sha256=sha(a.plan)))
 paired=[];changes={};unbound=[]
 def baseline(x):
  if part=='6'and x['bank']=='E54':
   ch=channels[x['row']];text=e54texts[x['reader'],x['item_id']]
   hits=[bool(re.search(ch['mention_patterns'][v],text,re.I))for v in ch['values']]
   j={'category':'states_value','values':[v for v,hit in zip(['A','B'],hits)if hit]}
   if not j['values']:j['category']='silent'
  elif x.get('regex'):
   c=statements49.statement(x['row'],x['text']);j={'category':'states_value','values':list(c)if c in ['A','B','both']else []}
   if c=='both':j['values']=['A','B']
   if c=='neither':j={'category':'silent','values':[]}
  else:j=x['judgment']
  return signed(j,x['label']),code(j)
 for r in raw:
  j=r.get('code')if 'status'in r else r
  if 'status'in r and r['status']=='UNPARSEABLE':j={'category':'UNPARSEABLE','values':[]}
  k=mapped[r['id']];key=(k['bank'],k['reader'],k['row'],k['pair_id']);x=lookup.get(key)
  if x is None or k['bank']=='E57'and k['row']in NONBINARY:
   unbound.append(dict(id=r['id'],reason='No registered binary signed S; retain categorical coverage separately'));continue
  score,c=baseline(x);new=signed(j,x['label']);nc=code(j);changes[key]=new
  paired.append(dict(bank=k['bank'],reader=k['reader'],row=k['row'],primary_code=c,new_code=nc,primary_score=score,new_score=new))
 groups=defaultdict(list)
 for x in paired:groups[x['bank']+'|'+x['reader']].append(x)
 groups['pooled_descriptive']=paired
 agreement={}
 for g,xs in groups.items():
  kept=[x for x in xs if x['primary_code']is not None and x['new_code']is not None]
  agreement[g]=dict(kappa=kappa([x['primary_code']for x in kept],[x['new_code']for x in kept])if kept else None,missing=len(xs)-len(kept))
 rows=defaultdict(list)
 for key,x in lookup.items():
  if key[:3]not in {k[:3]for k in changes}:continue
  if key[0]=='E57'and key[2]in NONBINARY:continue
  score,_=baseline(x);rows[key[:3]].append((score,changes.get(key,score)))
 out=[]
 for key,xs in sorted(rows.items()):
  if part=='6':assert sum(k[:3]==key for k in changes)==len(xs),'item6 full-row terminal coverage'
  original=[x[0]for x in xs if x[0]is not None];updated=[x[1]for x in xs if x[1]is not None]
  before=rate(original)if original else None;after=rate(updated)if updated else None
  out.append(dict(bank=key[0],reader=key[1],row=key[2],n_full=len(xs),n_new=sum(k[:3]==key for k in changes),original=before,counterfactual=after,threshold_flip=None if before is None or after is None else before['verdict']!=after['verdict'],scope='unsampled original judgments held fixed'if part=='5'else'full-row detector sensitivity; require complete row coverage'))
 result=dict(experiment='E88',part=part,agreement=agreement,rows=out,unbound_signed_records=unbound,source_verdicts_unchanged=True,item5_regex_baseline_caveat='E49 original baseline is regex, not a first judge model',plan_sha256=sha(a.plan),GPU_hours=0)
 write(dest/'RESULTS.json',result);write(dest/'RESULT_SEAL.json',dict(files={'RESULTS.json':sha(dest/'RESULTS.json')},plan_sha256=sha(a.plan)))
 print('E88 item'+part+' judged analysis sealed once')
if __name__=='__main__':main()
