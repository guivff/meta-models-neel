import tempfile,copy
from pathlib import Path
from unittest.mock import patch
import pytest
import adapter as a

def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);a.dump(p,v)
def fixture(tmp):
 s=a.read(a.HERE/'SPEC.json');root=tmp/'out';cap=root/'capture';cap.mkdir(parents=True);q=a.read(a.HERE/'ACQUISITION_REQUEST.json');sh=next(x for x in q['shards'] if x['experiment']=='E63');items=a.read(Path(s['inputs'])/'items.json');put(cap/'items.order.json',[x['id'] for x in items]);a.seal(cap,'CAPTURE_SEAL.json',dict(experiment='E63',cohort_id=a.COHORT,input_seal_sha256=sh['input_seal_sha256']));cs=a.sha(cap/'CAPTURE_SEAL.json')
 ass=dict(pod_id='stub',experiment='E63',shard=0,cohort_id=a.COHORT,gpu_count=1,prior_compute_seconds=0,compute_cap_seconds=8650,staging_cap_seconds=900,go_wait_cap_seconds=0,pod_created_epoch=100,staging_start_epoch=100,absolute_deadline_epoch=9650,daily_budget_verified=True,projected_daily_USD=260,dependency_receipt=dict(verified=True,cohort_id=a.COHORT,E57_output_seals=['a'*64]*3));put(root/'ASSIGNMENT.json',ass)
 ready=dict(pod_id='stub',cohort_id=a.COHORT,capture_seals={'E63':cs},input_seals={'E63':sh['input_seal_sha256']},ready_epoch=200);put(root/'CAPTURE_READY.json',ready);put(root/'GO_RECEIPT.json',dict(ready,issued_epoch=300,reader_launch_authorized=True,forecast_commit='a'*40,forecast_seal_sha256='b'*64));put(root/'TIMING.json',dict(compute_from_GO=300,deadline_epoch=8950,completed_epoch=8000));put(root/'parity/PARITY_RESULT.json',dict(status='PASS'));put(root/'FORECAST.json',dict(status='ADMIT'))
 jobs=[]
 for r in ('oracle','nla'):
  for arm in ('random','shuffled'):
   for start in range(0,200,8):
    j=dict(exp='E63',reader=r,kind='pool',units=[dict(id=f'{arm}:{i:03d}') for i in range(start,start+8)],phase='E63_'+r+'_native',arm=arm,number=len(jobs));jobs.append(j);put(root/'jobs'/f'{j["number"]:06d}.json',[dict(pool=arm,vector_id=x['id'],reader=r,layer=44 if r=='oracle' else 42,repeat=0,text='synthetic A',raw='<explanation>synthetic A</explanation>') for x in j['units']])
 put(root/'JOB_GRID.json',jobs);put(root/'COMPLETED.json',list(range(100)));a.seal(root,'OUTPUT_SEAL.json',dict(status='COMPLETE',experiment='E63',shard=0,cohort_id=a.COHORT,source_seal_sha256=q['source_seal_sha256'],input_seal_sha256=sh['input_seal_sha256'],pod_id='stub',capture_seal_sha256=cs))
 s.update(receipt=str(tmp/'receipt.json'),blind_out=str(tmp/'blind'),private_key=str(tmp/'key.json'),pool_out=str(tmp/'pools'),bundle=str(tmp/'bundle/INPUT_SEAL.json'),bundle_receipt=str(tmp/'normalizer.json'),analysis_out=str(tmp/'analysis'));put(Path(s['receipt']),dict(verified=True,experiment='E63',output=str(root),pod_id='stub',output_seal_sha256=a.sha(root/'OUTPUT_SEAL.json')));return s

def data(rows):
 rr=[]
 for bank in ('E56','E57','E59','E62'):
  for r in ('oracle','nla'):
   rec=[dict(id=str(i),item_id=str(i),repeat=0,text='A' if i%2 else 'B',label='A' if i%2 else 'B') for i in range(8)]
   rr.append(dict(bank=bank,row='stub',reader=r,readouts=rec,expected_readout_ids=[x['id'] for x in rec],patterns={'A':'A','B':'B'},analysis_status='COMPLETE_ONCE',analysis_seal_sha256='a'*64,native_status='REPORTED',channel='native',layer=44 if r=='oracle' else 42,prompt='stub',controlling_experiment=bank))
 return dict(schema='readerbench-scoring-v1',scope_complete=True,banks=['E56','E57','E59','E62'],rows=rr,expected_rows=[[x['bank'],x['row'],x['reader']] for x in rr],placebo=rows)

def test_full_pool_and_blind_roundtrip(tmp_path):
 s=fixture(tmp_path);root,rows=a.collect(s);assert len(rows)==800;chosen=a.select(rows);assert len(chosen)==400 and len({x['id'] for x in chosen})==400
 assert [x['id'] for x in chosen]==[x['id'] for x in a.select(list(reversed(rows)))]
 with patch.object(a.subprocess,'run') as p:
  p.return_value.returncode=0;a.blind(s,root,rows)
 packet=a.read(Path(s['blind_out'])/'JUDGE_PACKET.json');keys=a.read(s['private_key']);lookup={x['opaque_id']:x for x in keys}
 assert all(set(x)=={'id','property','values','readout'} and x['values']=={} and x['readout']==lookup[x['id']]['text'] for x in packet)
 assert len(a.read(Path(s['pool_out'])/'POOLS.json'))==800
 with patch.object(a.subprocess,'run') as p:
  p.return_value.returncode=0
  with pytest.raises(ValueError):a.blind(s,root,rows)

def test_science_and_once_guard(tmp_path,monkeypatch):
 s=fixture(tmp_path);root,rows=a.collect(s);d=data(rows);a.match_bundle(rows,d);expected={r:a.score(d,r) for r in ('oracle','nla')}
 put(Path(s['bundle_receipt']),dict(verified=True,e63_output_seal_sha256=a.sha(root/'OUTPUT_SEAL.json'),input_seal_sha256='c'*64));monkeypatch.setattr(a,'load_bundle',lambda *args:(d,{}));monkeypatch.setattr(a,'ROOT',tmp_path)
 a.analyze(s,root,rows);assert a.read(Path(s['analysis_out'])/'REGEX_RESULTS.json')==expected
 with pytest.raises(ValueError):a.analyze(s,root,rows)
 s['analysis_out']=str(tmp_path/'alternative')
 with pytest.raises(FileExistsError):a.analyze(s,root,rows)

def test_changed_pool_and_grid_rejected(tmp_path):
 s=fixture(tmp_path);root,rows=a.collect(s);d=data(rows);d['placebo']=copy.deepcopy(rows);d['placebo'][0]['text']='changed'
 with pytest.raises(ValueError):a.match_bundle(rows,d)
 d=data(rows+rows[:1])
 with pytest.raises(ValueError):a.match_bundle(rows,d)
 (root/'jobs/000000.json').write_text('[]')
 with pytest.raises(ValueError):a.collect(s)

def test_wrong_go_resealed(tmp_path):
 s=fixture(tmp_path);root=Path(a.read(s['receipt'])['output']);go=a.read(root/'GO_RECEIPT.json');go['issued_epoch']=199;(root/'GO_RECEIPT.json').unlink();put(root/'GO_RECEIPT.json',go);o=a.read(root/'OUTPUT_SEAL.json');(root/'OUTPUT_SEAL.json').unlink();a.seal(root,'OUTPUT_SEAL.json',{k:v for k,v in o.items() if k!='files'});r=a.read(s['receipt']);r['output_seal_sha256']=a.sha(root/'OUTPUT_SEAL.json');Path(s['receipt']).unlink();put(Path(s['receipt']),r)
 with pytest.raises(ValueError,match='capture before GO'):a.collect(s)

def test_command_seal():assert a.config(a.HERE/'SPEC.json')['experiment']=='E63'
