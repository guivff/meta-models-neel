"""CPU-only adapters for the completed follow402 E59 and ratified E68 layouts.
No synthetic legacy output seals; real acquisition provenance is retained.
"""
import argparse,sys,re
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; U=HERE.parent; ROOT=HERE.parents[3]
for p in ('e56/job','e57/job','analysis402'):sys.path.insert(0,str(U/p))
from contract56 import read,dump,sha,verify,seal,require,auc
from missingness import validate_judgment,metrics,audit,reported
from native_nla512 import truncation_summary
from analysis_io import continuation_aucs
from cpu_capture import compute
COHORT='joint-a7fea77c-7279007d'

def grid(xs,key,expected,message):
 keys=[key(x) for x in xs];require(len(keys)==len(set(keys)) and set(keys)==set(expected),message)

def spec(path):
 s=read(path);cmd=read(HERE/'COMMANDS.json')[s['experiment']]
 require(sha(path)==cmd['spec_sha256'],'sealed spec');verify(HERE,'SOURCE_SEAL.json',cmd['source_seal_sha256'])
 for name,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==h,'analysis dependency '+name)
 return s

def inputs(s):
 require(sha(s['private_items'])==s['private_items_sha256'],'private labels pin')
 private=read(s['private_items']);items=read(Path(s['inputs'])/'items.json')
 verify(s['inputs'],'INPUT_SEAL.json',s['input_seal_sha256'])
 grid(private,lambda x:x['id'],[x['id'] for x in items],'private/public grid')
 pr={x['id']:x for x in private}
 for x in items:
  require(pr[x['id']]['feature']==x['feature'] and pr[x['id']]['split']==x['split'],'private row/split')
 return items,pr

def capture(s,items):
 r=read(s['receipt']);require(r['verified'] is True and r['experiment']==s['experiment'],'integrator verified pull')
 root=Path(r['output']);cap=root/'capture';c=verify(cap,'CAPTURE_SEAL.json',r['capture_seal_sha256'])
 require(c['experiment']==s['experiment'] and c['input_seal_sha256']==s['input_seal_sha256'],'capture input/experiment')
 require(read(cap/'items.order.json')==[x['id'] for x in items],'capture exact item order')
 if s['experiment']=='E68':require(c['source_seal_sha256']==s['worker_source_sha256'],'capture worker')
 else:require(c['cohort_id']==COHORT,'capture cohort')
 return r,root,cap

def cpu(s):
 items,pr=inputs(s);r,root,cap=capture(s,items)
 require(s['experiment']=='E59','E68 uses sealed existing PROBE_COMMAND, before any readout access')
 h=np.load(cap/'acts44.npy',allow_pickle=False);require(h.shape==(len(items),5120) and np.isfinite(h).all(),'probe capture')
 private=[pr[x['id']] for x in items];scores,_=compute(private,h)
 out=Path(s['cpu_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'PROBE.json',scores)
 seal(out,'CPU_SEAL.json',dict(experiment='E59',capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),private_items_sha256=s['private_items_sha256'],fit_split='dev'))

def probes(s,cap,pr):
 out=Path(s['cpu_out']);test={k for k,x in pr.items() if x['split']=='test'}
 if s['experiment']=='E68':
  # Verify BEFORE even hashing the output seal, which recursively touches reader files.
  ps=verify(out,'PROBE_SEAL.json');require(ps['private_items_sha256']==s['private_items_sha256'] and ps['request_sha256']==s['request_sha256'],'E68 probe input/request')
  cr=read(s['probe_capture_receipt']);require(sha(s['probe_capture_receipt'])==ps['receipt_sha256'] and cr['verified'] is True,'probe verified capture receipt')
  require(set(cr['shards'])=={'0'} and cr['shards']['0']['capture_seal_sha256']==sha(cap/'CAPTURE_SEAL.json'),'same E68 capture used for fit')
  result={}
  for l in (42,44):
   p=read(out/f'PROBE{l}.json');require(p['fit_split']=='dev' and p['eval_split']=='test','dev-only fit')
   grid(p['scores'],lambda x:x['id'],test,'E68 probe test grid')
   expected={row:auc([pr[x['id']]['label'] for x in p['scores'] if pr[x['id']]['feature']+'|'+pr[x['id']]['position']==row],[x['score'] for x in p['scores'] if pr[x['id']]['feature']+'|'+pr[x['id']]['position']==row]) for row in {pr[k]['feature']+'|'+pr[k]['position'] for k in test}}
   require(p['AUROC']==expected,'probe AUROC agrees with sealed per-item scores');result[str(l)]=expected
  return result
 ps=verify(out,'CPU_SEAL.json');require(ps['capture_seal_sha256']==sha(cap/'CAPTURE_SEAL.json') and ps['private_items_sha256']==s['private_items_sha256'],'same E59 probe capture/labels')
 scores=read(out/'PROBE.json');grid(scores,lambda x:x['id'],test,'E59 probe test grid')
 return {row:auc([pr[x['id']]['label'] for x in scores if pr[x['id']]['feature']==row],[x['score'] for x in scores if pr[x['id']]['feature']==row]) for row in {pr[k]['feature'] for k in test}}

def follow_custody(s,r,root,cap,outer):
 a=read(root/'ASSIGNMENT.json');ready=read(root/'CAPTURE_READY.json');go=read(root/'GO_RECEIPT.json');t=read(root/'TIMING.json')
 require(a['experiment']=='E59' and a['shard']==0 and a['gpu_count']==1 and a['cohort_id']==COHORT==outer['cohort_id'],'follow shard identity')
 require(a['pod_id']==outer['pod_id']==r['pod_id'],'follow pod identity')
 require(a['compute_cap_seconds']>0 and a['prior_compute_seconds']>=0 and a['compute_cap_seconds']+a['prior_compute_seconds']==7200,'historical E59 cap')
 require(a['staging_cap_seconds']==900 and a['go_wait_cap_seconds']==2700 and a['pod_created_epoch']<=a['staging_start_epoch'],'staging assignment')
 require(a['absolute_deadline_epoch']==a['staging_start_epoch']+900+2700+a['compute_cap_seconds'],'outer deadline')
 require(a['daily_budget_verified'] is True and 0<=a['projected_daily_USD']<=300,'historical budget')
 dep=a['dependency_receipt'];require(dep['verified'] is True and dep['cohort_id']==COHORT and len(dep['E57_output_seals'])==3,'E57 dependency')
 for key in ('pod_id','cohort_id','capture_seals','input_seals'):require(go[key]==ready[key],'GO '+key)
 require(go['pod_id']==a['pod_id'] and go['cohort_id']==COHORT and go['capture_seals']=={'E59':sha(cap/'CAPTURE_SEAL.json')} and go['input_seals']=={'E59':s['input_seal_sha256']},'GO capture/input identity')
 require(go['reader_launch_authorized'] is True and re.fullmatch('[0-9a-f]{40}',go['forecast_commit']) and re.fullmatch('[0-9a-f]{64}',go['forecast_seal_sha256']),'forecast-bound GO')
 require(a['staging_start_epoch']<=ready['ready_epoch']<=a['staging_start_epoch']+900 and ready['ready_epoch']<=go['issued_epoch']<=ready['ready_epoch']+2700,'capture then GO window')
 require(t['compute_from_GO']==go['issued_epoch'] and t['deadline_epoch']==go['issued_epoch']+a['compute_cap_seconds'] and go['issued_epoch']<=t['completed_epoch']<=t['deadline_epoch'],'compute starts GO')
 require(read(root/'parity/PARITY_RESULT.json')['status']=='PASS' and read(root/'FORECAST.json')['status']=='ADMIT','parity and self admission')
 return a

def native_grid(rows,items,e):
 test={x['id']:x for x in items if x['split']=='test'}
 grid(rows,lambda x:(x['unit_id'],x['reader']),[(k,r) for k in test for r in ('oracle','nla')],'complete native reader grid')
 for x in rows:
  v=test[x['unit_id']];require(x['feature']==v['feature'] and x['reader_native_layer']==(44 if x['reader']=='oracle' else 42) and x['repeat']==0 and isinstance(x['text'],str),'native identity')
  require(x['id']==x['unit_id']+':'+x['reader']+':0','unique normalized source id')
  if e=='E68':require(x['position']==v['position'] and x['base_item_id']==v['base_item_id'] and x['source_layer']==x['reader_native_layer'],'E68 frozen position/source layer')

def collect(s):
 items,pr=inputs(s);r,root,cap=capture(s,items);probe=probes(s,cap,pr)
 outer=verify(root,'OUTPUT_SEAL.json',r['output_seal_sha256'])
 require(outer['status']=='COMPLETE' and outer['experiment']==s['experiment'] and outer['source_seal_sha256']==s['worker_source_sha256'] and outer['input_seal_sha256']==s['input_seal_sha256'] and outer['capture_seal_sha256']==sha(cap/'CAPTURE_SEAL.json'),'completed output identity')
 cont=[]
 if s['experiment']=='E59':
  ass=follow_custody(s,r,root,cap,outer)
  # Reconstruct the expected job grid from frozen inputs, with zero-width dummy h;
  # no model or activation-dependent selection is used.
  sys.path.insert(0,str(U/'e62/job'));from second_worker import jobs_for
  plan=read(Path(s['inputs'])/'PLAN.json');jobs=jobs_for({'E59':dict(items=items,acts={42:np.empty((len(items),0)),44:np.empty((len(items),0))},plan=plan)})
  want=[{k:v for k,v in j.items() if k!='h'} for j in jobs];require(read(root/'JOB_GRID.json')==want,'frozen job grid')
  require(read(root/'COMPLETED.json')==list(range(len(jobs))),'all jobs complete once')
  rows=[]
  for j in jobs:
   v=read(root/'jobs'/f'{j["number"]:06d}.json');require(len(v)==len(j['units']),'job cardinality')
   for x,u in zip(v,j['units']):
    require(x['reader']==j['reader'] and x['feature']==u['feature'],'job reader/row')
    if j['kind']=='native':require(x['unit_id']==u['id'],'native job unit')
    else:require(x['id']==u['id'] and x['arm']==j['arm'] and np.shape(x['scores'])==(len(j['pairs']),) and np.isfinite(x['scores']).all(),'continuation job identity/scores')
   (rows if j['kind']=='native' else cont).extend(v)
 else:
  require(r['completion_commit'].startswith('cc2a1920'),'integrator E68 completion reference')
  ass=read(root/'ASSIGNMENT.json');require(ass['experiment']=='E68' and ass['shard']==0 and ass['pod_id']==outer['pod_id']==r['pod_id'] and ass['cap_seconds']==5664 and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+5664,'E68 completed allocation')
  require(ass['gpu_count']==1 and ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=300,'E68 historical budget')
  # The acquisition worker seals COMPLETE after its hard-clock checks; verifier
  # independently attests provider completion time in the pull receipt.
  require(ass['pod_created_epoch']<=r['completed_epoch']<=ass['absolute_deadline_epoch'],'E68 verified completion within cap')
  records=read(root/'RECORDS.json');rows=[dict(x,unit_id=x['id'],id=x['id']+':'+x['reader']+':0') for x in records]
  for reader in ('oracle','nla'):require(read(root/(reader+'_STAGE.json'))['status']=='COMPLETE','completed reader stage')
 native_grid(rows,items,s['experiment'])
 return dict(root=root,cap=cap,private=pr,native=rows,probe=probe,continuation=cont,assignment=ass)

def blind(s,d):
 rows=list(d['native']);rng=np.random.default_rng(20261027);rng.shuffle(rows);packet=[];key=[]
 for x in rows:
  opaque=rng.bytes(16).hex();values=s['values'][x['feature']]
  packet.append(dict(id=opaque,property=x['feature'],values=dict(A=values[0],B=values[1]),readout=x['text']))
  key.append(dict(opaque_id=opaque,source_id=x['id']))
 out=Path(s['blind_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'JUDGE_PACKET.json',packet);dump(Path(s['private_key']),key)
 seal(out,'BLIND_SEAL.json',dict(experiment=s['experiment'],receipt_sha256=sha(s['receipt']),output_seal_sha256=sha(d['root']/'OUTPUT_SEAL.json'),private_key_sha256=sha(s['private_key']),rubric_sha256=sha(U/'e56/job/JUDGE_RUBRIC.md'),probe_seal_sha256=sha(Path(s['cpu_out'])/('PROBE_SEAL.json' if s['experiment']=='E68' else 'CPU_SEAL.json'))))
 from packet_fields import convert
 convert(out,Path(s['rubric_out']))

def judgments(s,d):
 out=Path(s['blind_out']);b=verify(out,'BLIND_SEAL.json')
 require(b['receipt_sha256']==sha(s['receipt']) and b['output_seal_sha256']==sha(d['root']/'OUTPUT_SEAL.json') and b['private_key_sha256']==sha(s['private_key']) and b['rubric_sha256']==sha(U/'e56/job/JUDGE_RUBRIC.md'),'blind custody/rubric')
 packet=read(out/'JUDGE_PACKET.json');key=read(s['private_key']);lookup={x['id']:x for x in d['native']}
 grid(key,lambda x:x['source_id'],lookup,'blind full source grid');grid(packet,lambda x:x['id'],[x['opaque_id'] for x in key],'blind opaque grid')
 js=Path(s['judgments']);jseal=verify(js.parent,'JUDGMENT_SEAL.json');require(jseal['blind_seal_sha256']==sha(out/'BLIND_SEAL.json'),'judgment source')
 jj=read(js);grid(jj,lambda x:x['id'],[x['id'] for x in packet],'complete judgments');pp={x['id']:x for x in packet};by={x['id']:x for x in jj};result={}
 for k in key:
  x=lookup[k['source_id']];p=pp[k['opaque_id']];v=s['values'][x['feature']]
  require(p==dict(id=k['opaque_id'],property=x['feature'],values=dict(A=v[0],B=v[1]),readout=x['text']),'verbatim packet values/text')
  j=by[k['opaque_id']];validate_judgment(j,x['text']);result[x['id']]=j
 return result

def rules68(rates):
 result={}
 for reader in ('oracle','nla'):
  delta={}
  for row in ('container_after_move','holder_after_handovers','topic_twin'):
   a=rates[reader,row+'|registered']['S'];b=rates[reader,row+'|pre_answer']['S'];delta[row]=None if a is None or b is None else b-a
  states=[delta[k] for k in ('container_after_move','holder_after_handovers')];control=delta['topic_twin']
  result[reader]=dict(pre_minus_far=delta,R_O1='NOT EVALUABLE' if None in states or control is None else 'MET' if all(round(x,12)>=.30 for x in states) and abs(round(control,12))<.15 else 'NOT MET',falsifier='NOT EVALUABLE' if None in states else all(round(x,12)<.10 for x in states))
 return result

def rules59(probe,bow,rates,mechanics):
 allowed=[r for r in probe if probe[r]>=.90 and bow[r]['instruction_only_test_auroc']<=.65];readers={}
 for reader in ('oracle','nla'):
  count=sum(reported(rates[reader,row]) for row in allowed);missing=any(rates[reader,row]['S'] is None for row in allowed)
  readers[reader]=dict(reported_plans=count,same_run_reported_mechanics=mechanics[reader],R1='NOT EVALUABLE' if missing else 'MET' if count>=4 and mechanics[reader]<=1 else 'NOT MET',falsifier='NOT EVALUABLE' if missing else count<=1)
 return dict(probe_and_BOW_gates={r:r in allowed for r in probe},readers=readers)

def analyze(s,d,jj):
 private=d['private'];native=d['native']
 if s['experiment']=='E68':
  private={k:dict(x,feature=x['feature']+'|'+x['position']) for k,x in private.items()};native=[dict(x,feature=private[x['unit_id']]['feature']) for x in native]
 rates=metrics(private,native,jj)
 if s['experiment']=='E68':result=dict(readers=rules68(rates),arithmetic_status='INFEASIBLE',probe=d['probe'])
 else:
  parent=Path(s['e57_analysis']);ps=verify(parent,'ANALYSIS_SEAL.json');cr=read(s['cohort_receipt']);require(ps['experiment']=='E57' and ps['status']=='COMPLETE' and ps['cohort_id']==COHORT,'sealed E57 analysis')
  require(cr['verified'] is True and cr['cohort_id']==COHORT and cr['e57_analysis_seal_sha256']==sha(parent/'ANALYSIS_SEAL.json') and cr['E57_output_seals']==d['assignment']['dependency_receipt']['E57_output_seals'],'same-run E57 comparison')
  previous=read(parent/'RESULTS.json');result=rules59(d['probe'],read(Path(s['inputs'])/'BOW_QA.json'),rates,previous['R_B']['reporting_rows'])
  jr=Path(s['j_input']);js=verify(jr,'J_SEAL.json');require(js['capture_seal_sha256']==sha(d['cap']/'CAPTURE_SEAL.json') and js['input_seal_sha256'] in (s['input_seal_sha256'],s['parent_input_seal_sha256']),'J same frozen bank/capture')
  jrows=read(jr/'J_ROWS.json');require(set(jrows)==set(d['probe']),'J row grid')
  for reader in ('oracle','nla'):
   if any(previous['rates'].get(reader+'|'+row,{}).get('S') is None for row in previous['R_B'].get('eligible',[])):
    result['readers'][reader]['R1']='NOT EVALUABLE'
    result['readers'][reader]['reason']='E57 eligible mechanics row has no parseable judgments'
  result.update(J_rows=jrows,R2_IN_J=sum(x['J_label']=='IN-J' for x in jrows.values()),probe=d['probe'],continuation=continuation_aucs(d),not_evaluable_continuation=[r for r,p in read(Path(s['inputs'])/'PLAN.json')['continuation_pairs'].items() if p is None])
 result.update(rates={'|'.join(k):v for k,v in rates.items()},NLA_truncation=truncation_summary([x for x in native if x['reader']=='nla']))
 out=Path(s['analysis_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE.json',dict(experiment=s['experiment'],receipt_sha256=sha(s['receipt'])));dump(out/'RESULTS.json',result);dump(out/'UNPARSEABLE_COUNTS.json',audit(native,jj))
 (out/'RESULTS.md').write_text('# '+s['experiment']+'\n\n'+ '\n'.join('- '+r+': '+str(v) for r,v in result['readers'].items())+'\n')
 seal(out,'ANALYSIS_SEAL.json',dict(experiment=s['experiment'],status='COMPLETE',adapter_source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),receipt_sha256=sha(s['receipt']),judgment_seal_sha256=sha(Path(s['judgments']).parent/'JUDGMENT_SEAL.json')))

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',choices=['cpu','verify','blind','analyze'],required=True);a=p.parse_args();s=spec(a.spec)
 if a.mode=='cpu':cpu(s);return
 d=collect(s)
 if a.mode=='blind':blind(s,d)
 elif a.mode=='analyze':analyze(s,d,judgments(s,d))
if __name__=='__main__':main()
