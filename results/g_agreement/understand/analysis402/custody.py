"""CPU-only union of verified shard custody; never fabricates legacy pod/output seals."""
import sys,json,time,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];U=HERE.parent
sys.path.insert(0,str(U/'e56/job'));sys.path.insert(0,str(U/'e57/job'));sys.path.insert(0,str(U/'e62/job'))
from contract56 import read,dump,sha,verify,seal,require,auc
COHORT='joint-a7fea77c-7279007d'

def put_unique(dest,key,value):
 require(key not in dest,'duplicate job / retained pilot replay');dest[key]=value

def verify_go(receipt,ass,plan,request,input_sha,source_sha):
 go=receipt['go'];ready=receipt['capture_ready'];e=plan['experiment']
 require(ass['experiment']==e and ass['shard']==plan['shard'] and ass['cohort_id']==COHORT and ass['gpu_count']==1,'assignment identity')
 require(ass['compute_cap_seconds']==plan['compute_cap_seconds'] and ass['staging_cap_seconds']==900,'registered compute/staging caps')
 require(ass['staging_start_epoch']==ass['pod_created_epoch'] and ass['absolute_deadline_epoch']==ass['staging_start_epoch']+900+ass['compute_cap_seconds'],'outer deadline')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=300,'daily budget')
 require(receipt['input_sha256']==input_sha and receipt['source_sha256']==source_sha,'source/input binding')
 for k in ('pod_id','cohort_id','plan_sha256','capture_seals'):require(go[k]==ready[k],'GO '+k)
 require(go['pod_id']==ass['pod_id'] and go['cohort_id']==COHORT and go['plan_sha256']==ass['plan_sha256']==receipt['plan_sha256'],'GO assignment binding')
 require(go['capture_seals']==plan['capture_seals'] and go['reader_launch_authorized'] is True,'standing capture-bound GO')
 require(ass['pod_created_epoch']<=ready['ready_epoch']<=go['issued_epoch']<=ass['pod_created_epoch']+900,'staging/GO order')
 forecast=request['forecast_commit'];forecast=forecast[e] if isinstance(forecast,dict) else forecast
 require(go['forecast_commit'].startswith(forecast),'standing forecast record')
 end=go['issued_epoch']+ass['compute_cap_seconds'];require(receipt['compute_deadline']==end and go['issued_epoch']<=receipt['completed_epoch']<=end,'GO compute clock')
 require(receipt['parity_status']=='PASS','parity')

def stage_jobs(entry,e,sh):
 folder='ladder402' if e in ('E62','E62P') else 'replan402';req=read(U/folder/('REQUEST.json' if folder=='ladder402' else e+'_REQUEST.json'));b=read(U/folder/f'{e}_{sh}_BINDING.json');inp=Path(b['inputs']);verify(inp,'INPUT_SEAL.json',b['input_seal_sha256']);plan=read(inp/'PLAN.json');require(sha(inp/'PLAN.json')==b['plan_sha256'],'plan hash')
 root=Path(entry['root']);outer=verify(root,'OUTPUT_SEAL.json',entry['output_seal_sha256']);require(outer['status']=='COMPLETE' and outer['experiment']==e and outer['shard']==sh and outer['cohort_id']==COHORT,'complete shard identity')
 stage=root/e;s=verify(stage,'STAGE_SEAL.json');require(s['status']=='COMPLETE' and s['stage']==e and s['plan_sha256']==b['plan_sha256'] and s['cohort_id']==COHORT,'stage identity')
 receipt=read(stage/'RECEIPT.json');ass=read(root/'ASSIGNMENT.json');require(receipt['assignment']==ass and receipt['go']==read(root/'GO_RECEIPT.json') and receipt['capture_ready']==read(root/'CAPTURE_READY.json'),'receipt matches root')
 verify_go(receipt,ass,plan,req,b['input_seal_sha256'],req['source_seal_sha256']);require(sha(root/'parity/PARITY_RESULT.json')==receipt['parity_sha256'] and read(root/'parity/PARITY_RESULT.json')['status']=='PASS','actual parity binding')
 require(read(stage/'NOT_RUN.json')==[] and set(read(stage/'COMPLETED.json'))=={j['key'] for j in plan['jobs']} and len(read(stage/'COMPLETED.json'))==len(plan['jobs']),'complete owned job set')
 return [(j,read(stage/'jobs'/f'{j["number"]:06d}.json')) for j in plan['jobs']],plan['retained_pilots'],plan['capture_seals']

def legacy_jobs(entry,e,sh):
 require(e=='E56' and sh in (0,1),'only completed E56_0/1 legacy shards')
 b=read(U/'joint9/INPUT_BINDING.json');inp=Path(b['inputs']);verify(inp,'INPUT_SEAL.json',b['input_seal_sha256']);plan=read(inp/'PLAN.json');root=Path(entry['root']);s=verify(root,'OUTPUT_SEAL.json',entry['output_seal_sha256']);req=read(U/'joint9/REQUEST.json')
 require(s['experiment']==e and s['shard']==sh and s['status']=='COMPLETE' and s['plan_sha256']==b['plan_sha256'] and s['source_seal_sha256']==req['source_seal_sha256'],'legacy completed identity')
 a=read(root/'ASSIGNMENT.json');cap=[5949,5948][sh];require(a['experiment']==e and a['shard']==sh and a['cap_seconds']==cap and a['deadline_epoch']==a['pod_created_epoch']+cap and a['plan_sha256']==plan['identity'] and a['pod_id']==s['pod_id'],'legacy allocation')
 require(a['daily_budget_verified'] is True and 0<=a['projected_daily_USD']<=150,'legacy budget');done=read(root/'TIMING.json');require(a['pod_created_epoch']<=done['completed_epoch']<a['deadline_epoch'] and done['deadline_epoch']==a['deadline_epoch'],'legacy timing');go=read(root/'GO_RECEIPT.json');ready=read(root/'CAPTURE_READY.json')
 require(go['reader_launch_authorized'] is True and go['pod_id']==a['pod_id'] and go['plan_sha256']==plan['identity'] and go['capture_seals']==plan['capture_seals'][e] and ready['ready_epoch']<=go['issued_epoch']<=done['completed_epoch'] and go['forecast_commit'].startswith('46cd1f4a'),'legacy R3b')
 require(read(root/'parity/PARITY_RESULT.json')['status']=='PASS','legacy parity');jobs=[j for j in plan['jobs'] if j['exp']==e and j['shard']==sh and not j['retained_pilot']];require(set(read(root/'COMPLETED.json'))=={j['key'] for j in jobs} and len(read(root/'COMPLETED.json'))==len(jobs),'legacy owned grid')
 return [(dict(j,original_key=j['key']),read(root/'jobs'/f'{j["resume_number"]:06d}.json')) for j in jobs],[],plan['capture_seals'][e]

def validate_records(j,rows):
 require(isinstance(rows,list) and bool(rows),'nonempty job payload')
 if 'units' not in j:return # Retained ladder pilots checked against full frozen item grid below.
 units=j['units'];require(len(rows)==len(units),'job cardinality')
 for x,u in zip(rows,units):
  if j['kind'] in ('native','injection'):
   require(x['unit_id']==u['id'] and x['id']==u['id']+':'+j['reader']+':0' and x['reader']==j['reader'] and x['repeat']==0 and x['reader_native_layer']==(44 if j['reader']=='oracle' else 42),'native unit identity')
   if j['kind']=='injection':require(x['direction_id']==u['row']+':'+u['variant'] and x['arm']==u['arm'] and x['vector_index']==u['index'],'unchanged injection direction')
   else:require(x['feature']==u['feature'],'native feature')
  elif j['kind']=='continuation':require(x['id']==u['id'] and x['feature']==u['feature'] and x['reader']==j['reader'] and x['arm']==j['arm'] and np.isfinite(x['scores']).all(),'continuation identity')
  elif j['kind']=='behaviour':require(x['id']==u['id'] and x['feature']==u['feature'] and x['base_item_id']==u['base_item_id'],'behaviour identity')

def assemble(manifest,e):
 m=read(manifest);require(m['verified'] is True and m['experiment']==e and m['cohort_id']==COHORT,'verified experiment/cohort manifest');expected_shards=set(range(2 if e=='E62P' else 3));seen=set();allrows={};definitions={};pilots=[];captures=None
 for entry in m['shards']:
  sh=entry['shard'];require(sh in expected_shards and sh not in seen,'unique shard grid');seen.add(sh)
  fn=legacy_jobs if e=='E56' and sh in (0,1) else stage_jobs;pairs,pp,cc=fn(entry,e,sh)
  if captures is None:captures=cc
  require(captures==cc,'same original capture family')
  pilots+=pp
  for j,rows in pairs:
   validate_records(j,rows);key=j['original_key'];put_unique(allrows,key,rows);definitions[key]=j
 require(seen==expected_shards,'all required shards complete')
 if e in ('E56','E57'):
  b=read(U/'joint9/INPUT_BINDING.json');parent=read(Path(b['inputs'])/'PLAN.json');require(parent['identity']==b['plan_sha256'],'original plan pin');original=[j for j in parent['jobs'] if j['exp']==e];pilots=[dict(j,original_key=j['key']) for j in original if j['retained_pilot']];expected={j['key'] for j in original}
 else:expected=set(allrows)|{j['original_key'] for j in pilots}
 pulls={}
 for p in m['retained_pilot_pulls']:
  require(p['slot'] not in pulls,'duplicate pilot source');root=Path(p['root']);s=verify(root,p['seal_file'],p['seal_sha256']);require(p['pilot_file'] in s['files'],'pilot payload included in custody seal');pulls[p['slot']]=read(root/p['pilot_file'])
 for j in pilots:
  prefix,number=j['original_key'].split(':');slot='second' if prefix=='second' else int(prefix);rows=pulls[slot][number];validate_records(j,rows);put_unique(allrows,j['original_key'],rows);definitions[j['original_key']]=j
 require(set(allrows)==expected,'exact union of unfinished jobs and retained pilots')
 return [(definitions[k],allrows[k]) for k in sorted(allrows)],captures,{'manifest_sha256':sha(manifest),'cohort_id':COHORT,'original_job_count':len(allrows),'retained_pilot_jobs':len(pilots),'shards':sorted(seen)}
