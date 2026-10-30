import sys,time,copy,ast
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import custody as c
from oracle_rules import rules62 as oracle_rules
from analysis_second import rules62 as original_rules
from measures62 import eval_measure as original_eval
from oracle_rules import eval_measure as oracle_eval

def reseal(root,name,extra):
 (root/name).unlink(missing_ok=True);c.seal(root,name,extra)

def fixture(tmp,monkeypatch,e='E62'):
 u=tmp/'understand';u.mkdir();monkeypatch.setattr(c,'U',u);folder=u/('ladder402' if e=='E62' else 'replan402');folder.mkdir();capmap={e:'c'*64} if e=='E62' else {str(i):'c'*64 for i in range(3)};source='s'*64;forecast={'E62':'b6203308','E57':'023f715f','E56':'46cd1f4a'}[e];c.dump(folder/('REQUEST.json' if e=='E62' else e+'_REQUEST.json'),{'source_seal_sha256':source,'forecast_commit':forecast});entries=[];original=[];pilot=dict(key='second:90' if e=='E62' else '0:90',original_key='second:90' if e=='E62' else '0:90',kind='native',reader='oracle',exp=e,units=[{'id':'pilot','feature':'row'}],retained_pilot=True,shard=None)
 def payload(j):return [dict(id=x['id']+':oracle:0',unit_id=x['id'],feature='row',reader='oracle',reader_native_layer=44,repeat=0,text='synthetic',raw='synthetic') for x in j['units']]
 for i in range(3):
  key=('second:' if e=='E62' else str(i)+':')+str(i);j=dict(key=key+':'+e,original_key=key,kind='native',reader='oracle',number=i,units=[{'id':str(i),'feature':'row'}]);original.append(dict(j,key=key,exp=e,shard=i,retained_pilot=False,resume_number=i));inp=tmp/f'input{i}';inp.mkdir();plan=dict(experiment=e,shard=i,compute_cap_seconds=100,cohort_id=c.COHORT,capture_seals=capmap,jobs=[j],retained_pilots=[pilot] if i==0 else []);c.dump(inp/'PLAN.json',plan);c.seal(inp,'INPUT_SEAL.json',{});psha=c.sha(inp/'PLAN.json');ish=c.sha(inp/'INPUT_SEAL.json');c.dump(folder/f'{e}_{i}_BINDING.json',dict(inputs=str(inp),plan_sha256=psha,input_seal_sha256=ish));root=tmp/f'out{i}';root.mkdir();(root/'parity').mkdir();c.dump(root/'parity/PARITY_RESULT.json',{'status':'PASS'});ass=dict(experiment=e,shard=i,pod_id='p'+str(i),gpu_count=1,cohort_id=c.COHORT,compute_cap_seconds=100,staging_cap_seconds=900,pod_created_epoch=1000,staging_start_epoch=1000,absolute_deadline_epoch=2000,plan_sha256=psha,daily_budget_verified=True,projected_daily_USD=100);ready=dict(pod_id=ass['pod_id'],cohort_id=c.COHORT,plan_sha256=psha,capture_seals=capmap,ready_epoch=1100);go=dict(ready,issued_epoch=1200,reader_launch_authorized=True,forecast_commit=forecast);receipt=dict(assignment=ass,go=go,capture_ready=ready,plan_sha256=psha,input_sha256=ish,source_sha256=source,parity_status='PASS',parity_sha256=c.sha(root/'parity/PARITY_RESULT.json'),completed_epoch=1250,compute_deadline=1300)
  for name,obj in [('ASSIGNMENT.json',ass),('GO_RECEIPT.json',go),('CAPTURE_READY.json',ready)]:c.dump(root/name,obj)
  stage=root/e;stage.mkdir();(stage/'jobs').mkdir();c.dump(stage/'jobs'/f'{i:06d}.json',payload(j));c.dump(stage/'COMPLETED.json',[j['key']]);c.dump(stage/'NOT_RUN.json',[]);c.dump(stage/'RECEIPT.json',receipt);c.seal(stage,'STAGE_SEAL.json',dict(status='COMPLETE',stage=e,cohort_id=c.COHORT,plan_sha256=psha));c.seal(root,'OUTPUT_SEAL.json',dict(status='COMPLETE',experiment=e,shard=i,cohort_id=c.COHORT));entries.append(dict(shard=i,root=str(root),output_seal_sha256=c.sha(root/'OUTPUT_SEAL.json')))
 if e!='E62':
  jd=u/'joint9';jd.mkdir();pi=tmp/'parent';pi.mkdir();original.append(pilot);c.dump(pi/'PLAN.json',dict(identity='parent',jobs=original));c.dump(jd/'INPUT_BINDING.json',dict(inputs=str(pi),plan_sha256='parent',input_seal_sha256='placeholder'))
  if e=='E56':
   parent=c.read(pi/'PLAN.json');parent['capture_seals']={e:capmap};(pi/'PLAN.json').write_text(__import__('json').dumps(parent));c.seal(pi,'INPUT_SEAL.json',{});binding=c.read(jd/'INPUT_BINDING.json');binding['input_seal_sha256']=c.sha(pi/'INPUT_SEAL.json');(jd/'INPUT_BINDING.json').write_text(__import__('json').dumps(binding));c.dump(jd/'REQUEST.json',{'source_seal_sha256':source})
   for i in (0,1):
    root=tmp/f'out{i}';a=c.read(root/'ASSIGNMENT.json');a.update(cap_seconds=[5949,5948][i],deadline_epoch=1000+[5949,5948][i],plan_sha256='parent');(root/'ASSIGNMENT.json').write_text(__import__('json').dumps(a));g=c.read(root/'GO_RECEIPT.json');g['plan_sha256']='parent';(root/'GO_RECEIPT.json').write_text(__import__('json').dumps(g));c.dump(root/'TIMING.json',{'completed_epoch':1250,'deadline_epoch':a['deadline_epoch']});c.dump(root/'COMPLETED.json',[original[i]['key']]);(root/'jobs').mkdir();c.dump(root/'jobs'/f'{i:06d}.json',payload(original[i]));reseal(root,'OUTPUT_SEAL.json',dict(status='COMPLETE',experiment=e,shard=i,pod_id=a['pod_id'],plan_sha256='parent',source_seal_sha256=source));entries[i]['output_seal_sha256']=c.sha(root/'OUTPUT_SEAL.json')
 pr=tmp/'pilot';pr.mkdir();c.dump(pr/'PILOT_RESULTS.json',{'90':payload(pilot)});c.seal(pr,'CUSTODY.json',{});m=dict(verified=True,experiment=e,cohort_id=c.COHORT,shards=entries,retained_pilot_pulls=[dict(slot='second' if e=='E62' else 0,root=str(pr),seal_file='CUSTODY.json',seal_sha256=c.sha(pr/'CUSTODY.json'),pilot_file='PILOT_RESULTS.json')]);path=tmp/'manifest.json';c.dump(path,m);return path,m

@pytest.mark.parametrize('e',['E62','E57','E56'])
def test_complete_union_and_legacy_mix(tmp_path,monkeypatch,e):
 p,m=fixture(tmp_path,monkeypatch,e);rows,caps,lineage=c.assemble(p,e);assert len(rows)==4 and lineage['retained_pilot_jobs']==1

@pytest.mark.parametrize('fault',['missing_shard','duplicate_shard','missing_pilot','cross_cohort','tamper'])
def test_reject_invalid_custody(tmp_path,monkeypatch,fault):
 p,m=fixture(tmp_path,monkeypatch)
 if fault=='missing_shard':m['shards'].pop()
 if fault=='duplicate_shard':m['shards'][1]=m['shards'][0]
 if fault=='missing_pilot':m['retained_pilot_pulls']=[]
 if fault=='cross_cohort':m['cohort_id']='other'
 if fault=='tamper':(Path(m['shards'][0]['root'])/'E62/jobs/000000.json').write_text('[]')
 p.write_text(__import__('json').dumps(m))
 with pytest.raises((ValueError,KeyError)):c.assemble(p,'E62')

def test_oracle_rules_identical_no_NLA_input():
 probe={f'S{s}_L{i}':.95 for s in range(1,6) for i in range(5)};j={k:{'J_fraction':i/30} for i,k in enumerate(probe)};rates={(r,k):{'S':int(k[-1])*.1} for r in ('oracle','nla') for k in probe};a=original_rules(probe,rates,j);b=oracle_rules(probe,{k:v for k,v in rates.items() if k[0]=='oracle'},j);assert a['readers']['oracle']==b['readers']['oracle'] and b['R_L0']==a['R_L0'] and set(b['readers'])=={'oracle'}

def test_eval_matches_original_oracle():
 items=[dict(id=f'{i}:{r}',state='S6',split='test',rung=r,base_item_id=str(i)) for i in range(84) for r in ('C0','C1','C2','C3','C4')];records=[dict(id=x['id']+reader,unit_id=x['id'],reader=reader,repeat=0,text='test') for x in items for reader in ('oracle','nla')];jj={x['id']:{'eval_mention':True,'evidence':'test'} for x in records};assert original_eval(items,records,jj)['oracle']==oracle_eval(items,[x for x in records if x['reader']=='oracle'],jj)['oracle']

def test_once_guard(tmp_path):
 from analysis_io import claim_once
 claim_once(tmp_path/'once','E56','s')
 with pytest.raises(FileExistsError):claim_once(tmp_path/'once','E56','s')
