import copy,json
from contextlib import nullcontext
from pathlib import Path
import numpy as np
import pytest
import common
import torch
from projects.g_agreement.blindspot.screens import protocol as P,run as R,analyse as A,stage as S,corpus as C

class FakeOracle:
 model=object()
 class Tok:pad_token_id=0
 tok=Tok()
 def __init__(self):self.calls=[]
 def base(self):return nullcontext()
 def paired_logodds_templates(self,h,site,pairs,prefix=''):
  self.calls.append((site,pairs,prefix,len(h)));return h[:,0].reshape(1,-1)


def small_inputs():
 positions=[{'id':f's{i}','document_id':f'd{i}','position':3,'prefix_sha256':str(i)} for i in range(8)]
 assign=[{'feature':f,'id':f's{i}','donor_id':f's{i^1}'} for f in ['f1','f2'] for i in range(8)]
 states={site:torch.tensor([[float(i),float(site)] for i in range(8)]) for site in [42,44]}
 return positions,assign,states,{'f1':[['positive one','negative one']],'f2':[['positive two','negative two']]}


def test_scoring_delegates_to_vendor_and_donor_cache(monkeypatch):
 import mats.readers.nla as module
 calls=[]
 def native(nla,h,pairs,batch):calls.append((pairs,batch,len(h)));return h[:,0].reshape(1,-1)
 monkeypatch.setattr(module,'paired_logodds_templates',native)
 positions,assign,states,templates=small_inputs();ol=FakeOracle()
 scores,t=R.score_all({'olens':ol,'nla':object()},states,positions,assign,templates,'test')
 assert len(ol.calls)==2 and len(calls)==2 # no extra native generation for donor aliases.
 assert all(site==44 and prefix=='- ' for site,pairs,prefix,n in ol.calls)
 assert all(batch==32 for pairs,batch,n in calls)
 P.score_coverage(scores,assign,'test');by={(r['feature'],r['id'],r['reader'],r['arm']):r for r in scores}
 for r in assign:
  for reader in P.SITES:assert by[r['feature'],r['id'],reader,'mismatched']['score']==by[r['feature'],r['donor_id'],reader,'true']['score']
 with pytest.raises(ValueError,match='unknown reader'):R.asked('decoy',ol,states[44],['a','b'])

@pytest.mark.parametrize('decoy',['missing','extra','site','kind','nan','duplicate','mixed_run','mixed_code'])
def test_score_coverage_decoys(monkeypatch,decoy):
 import mats.readers.nla as module
 monkeypatch.setattr(module,'paired_logodds_templates',lambda nla,h,pairs,batch:h[:,0].reshape(1,-1))
 ps,aa,states,tt=small_inputs();rr,_=R.score_all({'olens':FakeOracle(),'nla':object()},states,ps,aa,tt,'smoke')
 if decoy=='missing':rr.pop()
 if decoy=='duplicate':rr.append(rr[0])
 if decoy=='extra':rr[0]['feature']='bad-feature'
 if decoy=='site':rr[0]['site']=42
 if decoy=='kind':rr[0]['run_kind']='real'
 if decoy=='mixed_run':rr[0]['run_id']='decoy-run'
 if decoy=='mixed_code':rr[0]['code_sha256']='decoy-code'
 if decoy=='nan':rr[0]['score']=float('nan')
 with pytest.raises(ValueError):P.score_coverage(rr,aa,'smoke')


def test_capture_one_pass_per_document_two_sites(monkeypatch):
 import mats.capture as module
 calls=[]
 def capture(model,seqs,sites,positions,batch_size,pad_id):
  assert sites==[42,44];assert len({len(x) for x in positions})==1
  calls.extend(tuple(s) for s in seqs)
  return {site:torch.tensor([[[float(pos),float(site)] for pos in row] for row in positions]) for site in sites}
 monkeypatch.setattr(module,'capture',capture)
 docs=[{'id':'a','ids':[1,2,3,4]},{'id':'b','ids':[5,6,7]},{'id':'c','ids':[8,9,10]}]
 ps=[{'id':'a0','document_id':'a','position':0},{'id':'a2','document_id':'a','position':2},{'id':'b1','document_id':'b','position':1},{'id':'c2','document_id':'c','position':2}]
 h=R.capture_union(FakeOracle(),docs,ps)
 assert len(calls)==3 and len(set(calls))==3
 assert h[42][:,0].tolist()==[0,2,1,2];assert h[44][:,1].tolist()==[44]*4


def booking():return {'issuer':'integrator','section':79,'pod_id':'ownedpod','source_files':P.files_hashes(),'freeze_sha256':C.sha(C.OUT/'FREEZE.json'),'provider_created_epoch':100,'deadline_epoch':100+P.CAP_SECONDS,'setup_deadline_epoch':100+P.STAGING_SECONDS,'science_cap_seconds':P.SCIENCE_SECONDS,'staging_allowance_seconds':P.STAGING_SECONDS,'science_deadline_epoch':100+P.STAGING_SECONDS+P.SCIENCE_SECONDS,'publication_verified':True,'guards_verified':True,'outgoing_retired':True,'staging_productivity_guard_verified':True,'weights_volume_go':True,'shared_weights_readonly':True}
@pytest.mark.parametrize('decoy',['id','scope','reset','reserve','source','fix','outgoing','expired'])
def test_admission_decoys(tmp_path,decoy):
 a=booking();p=tmp_path/'booking';C.save(p,a);assert P.admit(p,101,'ownedpod')
 if decoy=='id':a['pod_id']='otherpod'
 if decoy=='scope':a['section']=64
 if decoy=='reset':a['deadline_epoch']+=1
 if decoy=='reserve':a['science_deadline_epoch']+=1
 if decoy=='source':a['source_files']['fake']='bad'
 if decoy=='fix':a['staging_productivity_guard_verified']=False
 if decoy=='outgoing':a['outgoing_retired']=False
 if decoy=='expired':a['science_deadline_epoch']=101
 C.save(p,a)
 with pytest.raises(ValueError):P.admit(p,101,'ownedpod')


def test_all_feature_smoke_and_timing():
 ps,assign,states,tt=small_inputs();smoke=R.smoke_assignments(assign)
 assert {r['feature'] for r in smoke}=={'f1','f2'}
 assert all(any(s['feature']==r['feature'] and s['id']==r['donor_id'] for s in smoke) for r in smoke)
 timings={(f,reader):{'seconds':1,'n':8} for f in tt for reader in P.SITES}
 assert R.projection(0,100,1,10,100,timings,assign)['pass']
 assert not R.projection(0,7200,1,10,100,timings,assign)['pass']
 assert not R.projection(0,100,1000,10,100,timings,assign)['pass']


def test_no_fake_productivity_heartbeat(tmp_path):
 home=tmp_path/'hf';home.mkdir();p=S.Progress(tmp_path/'progress',home)
 assert not p.emit_if_changed();assert not p.path.exists()
 logs=home/'logs';logs.mkdir();(logs/'download.log').write_text('not an asset')
 assert not p.emit_if_changed()
 blobs=home/'hub/repo/blobs';blobs.mkdir(parents=True);file=blobs/'weight.incomplete';file.write_bytes(b'partial')
 assert p.emit_if_changed();before=p.path.read_bytes();assert not p.emit_if_changed();assert p.path.read_bytes()==before
 file.write_bytes(b'partial and more bytes');assert p.emit_if_changed();assert json.loads(p.path.read_text())['asset_bytes']>7
 assert p.hash_file(file)==C.sha(file);assert json.loads(p.path.read_text())['bytes_hashed']==file.stat().st_size


def test_output_and_seal_decoys(tmp_path):
 for p in R.output_paths(tmp_path).values():p.touch()
 R.assert_output_paths(tmp_path);(tmp_path/'wrong').touch()
 with pytest.raises(ValueError,match='wrong'):R.assert_output_paths(tmp_path)
 P.seal(tmp_path,['gate.s79.json'],'seal');P.verify(tmp_path,'seal');(tmp_path/'gate.s79.json').write_text('changed')
 with pytest.raises(ValueError,match='seal mismatch'):P.verify(tmp_path,'seal')


def feature_row(feature,reader,kind,gap,evaluable=True,overlap=()):return {'feature':feature,'reader':reader,'class_label':kind,'gap':gap,'evaluable':evaluable,'w1_overlap':overlap}
def test_primary_rules_reachable_and_candidate_exclusions():
 rows=[feature_row('struct','olens','count-like',.4),feature_row('struct','nla','count-like',.1),feature_row('semantic','olens','semantic',.05),feature_row('semantic','nla','semantic',.05)]
 assert all(r['status']=='CONFIRMED' for r in A.primary_rules(rows,draws=50))
 failed=[dict(r,gap=0) for r in rows];assert all(r['status']=='NOT MET' for r in A.primary_rules(failed,draws=50))
 assert all(r['status']=='NOT EVALUABLE' for r in A.primary_rules([],draws=50))
 rows += [feature_row('already_W1','olens','count-like',.99,overlap=['table_column']),feature_row('ineligible','olens','count-like',1,evaluable=False)]
 assert [r['feature'] for r in A.top_candidates(rows)]==['struct','semantic']


def test_vendor_probe_oof_and_bad_groups():
 h=torch.tensor([[float(y),float(i%3)] for i in range(30) for y in [0,1]])
 y=np.array([i%2 for i in range(60)]);groups=np.repeat(np.arange(30),2)
 pred=A.cv_probe(h,y,groups)
 from mats.metrics import auroc_labels
 assert auroc_labels(pred,y)>.99
 with pytest.raises(A.CVUnavailable):A.cv_probe(h,y,np.zeros(60))


def test_staging_outputs_and_exact_volume_revision(tmp_path):
 for p in S.output_paths(tmp_path).values():p.touch()
 S.assert_output_paths(tmp_path);(tmp_path/'decoy').touch()
 with pytest.raises(ValueError,match='decoy'):S.assert_output_paths(tmp_path)
 a=S.PUBLIC[0];volume=tmp_path/'weights';repo=volume/'hf_cache'/('models--'+a['repo'].replace('/','--'))/'snapshots'/a['revision'];repo.mkdir(parents=True)
 assert S.resolve_snapshot(volume,a)==repo
 wrong=dict(a,revision='0'*40)
 with pytest.raises(ValueError,match='missing/ambiguous'):S.resolve_snapshot(volume,wrong)


def test_operator_dead_watchdog_cleanup_hard_last():
 from projects.g_agreement.blindspot.screens import operator as O
 state={'watchdog_pid':'10','watchdog_caffeinate_pid':'11','hardstop_pid':'12','hardstop_caffeinate_pid':'13'}
 alive={'12':'bash ws2_hardstop.sh ownpod 100','13':'caffeinate -i bash ws2_hardstop.sh ownpod 100'};order=[]
 O.retire(state,'ownpod',lambda *a,**kw:None,getargs=lambda pid:alive.get(str(pid)),send=lambda pid,sig:(order.append(pid),alive.pop(str(pid))))
 assert order==[12,13] and not alive
 alive={'10':'bash ws2_watchdog.sh ownpod','11':'caffeinate -i','12':'bash ws2_hardstop.sh ownpod 100','13':'caffeinate -i'};order=[]
 O.retire(state,'ownpod',lambda *a,**kw:None,getargs=lambda pid:alive.get(str(pid)),send=lambda pid,sig:(order.append(pid),alive.pop(str(pid))))
 assert order==[10,11,12,13]

@pytest.mark.parametrize('decoy',['id','section','cap','reserve','expired'])
def test_operator_booking_decoys(decoy):
 from projects.g_agreement.blindspot.screens import operator as O
 b={'section':79,'pod_id':'ownpod','integrator_clearance':'exact ID line','provider_created_epoch':100,'deadline_epoch':100+P.CAP_SECONDS,'setup_deadline_epoch':100+P.STAGING_SECONDS,'science_cap_seconds':P.SCIENCE_SECONDS,'staging_allowance_seconds':P.STAGING_SECONDS,'science_deadline_epoch':100+P.STAGING_SECONDS+P.SCIENCE_SECONDS}
 assert O.booking_check(b,now=101)
 if decoy=='id':b['pod_id']='bad/path'
 if decoy=='section':b['section']=64
 if decoy=='cap':b['deadline_epoch']+=1
 if decoy=='reserve':b['science_deadline_epoch']+=1
 if decoy=='expired':b['science_deadline_epoch']=101
 with pytest.raises(ValueError):O.booking_check(b,now=101)


def test_operator_paths_guard_fix_and_requests(tmp_path):
 from projects.g_agreement.blindspot.screens import operator as O
 with pytest.raises(ValueError,match='path decoy'):O.request_command({'pod_id':'p','booking_sha256':'h','action':'rearm','pidfile':'/weights/job.pid','outputs':['/workspace/s79/log']},'p','h',tmp_path,'127.0.0.1:22')
 with pytest.raises(ValueError,match='path decoy'):O.request_command({'pod_id':'p','booking_sha256':'h','action':'rearm','pidfile':'/workspace/s79/../other/pid','outputs':['/workspace/s79/log']},'p','h',tmp_path,'127.0.0.1:22')
 ops=Path(O.__file__).parent/'ops'
 assert 'WD_INC_CMD' in (ops/'ws2_macguard.sh').read_text()
 assert '.incomplete' in (ops/'ws2_macguard.sh').read_text()
 assert 'WD_INC_CMD' in (ops/'ws2_watchdog.sh').read_text()
 assert "WD_HF_DIR='/workspace/s79/hf'" in Path(O.__file__).read_text()


def test_full_synthetic_sealed_join_and_top10(tmp_path,monkeypatch):
 """Full frozen input grid, synthetic TEST scores only, no model/API calls."""
 import shutil
 from dataclasses import dataclass
 from mats import metrics
 bank=tmp_path/'bank';bank.mkdir();source=C.CACHE/'prepared';original=json.loads((source/'INPUT_SEAL.json').read_text())
 for name in [*original['files'],'INPUT_SEAL.json']:shutil.copyfile(source/name,bank/name)
 docs,positions,assign,registry=P.inputs(bank)
 private=source/'labels.selected.DO_NOT_STAGE.jsonl';lm={(r['feature'],r['id']):r for r in C.rows(private)}
 scores=[]
 for r in assign:
  for reader,site in P.SITES.items():
   for arm,source_id in [('true',r['id']),('mismatched',r['donor_id'])]:scores.append(dict(P.stamp('test'),feature=r['feature'],id=r['id'],reader=reader,site=site,arm=arm,score=float(lm[r['feature'],source_id]['value'])))
 native=tmp_path/'native';native.mkdir();C.jsonl(native/'scores.s79.jsonl',scores);C.save(native/'positions.s79.json',positions)
 for site in [42,44]:np.save(native/f'acts{site}.s79.npy',np.zeros((len(positions),2),dtype=np.float32))
 P.seal(native,['scores.s79.jsonl','positions.s79.json','acts42.s79.npy','acts44.s79.npy'],'prediction_seal.s79.json',**P.stamp('test'),input_seal_sha256=C.sha(bank/'INPUT_SEAL.json'),freeze_sha256=C.sha(C.OUT/'FREEZE.json'))
 @dataclass
 class Result:auroc:float;lo:float;hi:float;n:int;n_clusters:int
 monkeypatch.setattr(metrics,'auroc_ci',lambda s,y,g,n_boot,seed:Result(metrics.auroc_labels(s,y),.5,1,len(y),len(set(g))))
 monkeypatch.setattr(metrics,'cluster_bootstrap',lambda *a,**kw:(0.,1.))
 monkeypatch.setattr(A,'cv_probe',lambda h,y,g:np.asarray(y,dtype=float))
 result=tmp_path/'result';A.analyse(bank,native,private,result,kind='test');v=json.loads((result/'RESULTS.json').read_text());top=json.loads((result/'TOP10.json').read_text())
 assert len(v['rows'])==190 and v['status']=='COMPLETE'
 assert all(r['run_kind']=='test' for r in v['rows']);assert all(not r['w1_overlap'] and r['evaluable'] for r in top['candidates']);assert len(top['candidates'])==10
 (native/'acts42.s79.npy').write_bytes(b'altered')
 with pytest.raises(ValueError,match='seal mismatch'):A.analyse(bank,native,private,tmp_path/'decoy',kind='test')


def test_changed_input_seal_and_private_labels_cannot_be_staged(tmp_path):
 import shutil
 bank=tmp_path/'bank';bank.mkdir();source=C.CACHE/'prepared';original=json.loads((source/'INPUT_SEAL.json').read_text())
 for name in [*original['files'],'INPUT_SEAL.json']:shutil.copyfile(source/name,bank/name)
 (bank/'bad.DO_NOT_STAGE.jsonl').write_text('{}')
 with pytest.raises(ValueError,match='label-bearing'):P.inputs(bank)
 (bank/'bad.DO_NOT_STAGE.jsonl').unlink();seal=json.loads((bank/'INPUT_SEAL.json').read_text());seal['seed']=123;C.save(bank/'INPUT_SEAL.json',seal)
 with pytest.raises(ValueError,match='frozen input seal'):P.inputs(bank)


def test_freeze_is_relocatable(tmp_path,monkeypatch):
 import shutil
 original=json.loads((C.OUT/'FREEZE.json').read_text())
 out=tmp_path/'results/g_agreement/blindspot/s79';out.mkdir(parents=True)
 shutil.copyfile(C.OUT/'FREEZE.json',out/'FREEZE.json')
 for name in original['files']:
  assert not Path(name).is_absolute() and '..' not in Path(name).parts
  dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(C.ROOT/name,dest)
 monkeypatch.setattr(C,'ROOT',tmp_path);monkeypatch.setattr(C,'OUT',out)
 assert P.verify_freeze()==original
 (tmp_path/next(iter(original['files']))).write_text('changed')
 with pytest.raises(ValueError,match='freeze changed'):P.verify_freeze()


def test_upload_has_no_private_labels():
 from projects.g_agreement.blindspot.screens.bundle import BANK_FILES
 assert set(BANK_FILES)=={'documents.input.jsonl','positions.input.jsonl','assignments.input.jsonl','features.input.json','INPUT_SEAL.json'}
 assert not any('DO_NOT_STAGE' in x for x in BANK_FILES)


def test_separate_setup_science_and_retrieval_clocks():
 a=booking();first=100+P.STAGING_SECONDS-1
 deadline=P.science_deadline(a,first)
 assert deadline==first+7200
 with pytest.raises(TimeoutError,match='setup'):P.science_deadline(a,first+2)
 for key in ['science_cap_seconds','staging_allowance_seconds','setup_deadline_epoch']:
  b=dict(a);b[key]+=1
  with pytest.raises(ValueError):P.budget_check(b,101)
 ps,assign,states,tt=small_inputs();timings={(f,r):{'seconds':1,'n':8} for f in tt for r in P.SITES}
 early=R.projection(0,100,1,10,100,timings,assign,7200)
 late=R.projection(1500,1600,1,10,100,timings,assign,8700)
 assert early==late and early['staging_excluded'] and early['pass']
 assert not R.projection(1500,1600,1,10,100,timings,assign,1601)['pass']
 assert not R.projection(0,7200,1,10,100,timings,assign,9000)['pass']


def test_verified_shared_runtime_or_current_only():
 assert P.runtime_choice({})=='/workspace/s79-venv'
 choice={'mode':'integrator-verified','path':'/weights/venv-kernels','verified_by_integrator':True,'receipt_sha256':'a'*64}
 assert P.runtime_choice({'runtime_environment':choice})=='/weights/venv-kernels'
 for key,value in [('path','/weights/other'),('verified_by_integrator',False),('receipt_sha256','bad')]:
  with pytest.raises(ValueError,match='unverified runtime'):P.runtime_choice({'runtime_environment':dict(choice,**{key:value})})


def test_chain_bounds_setup_and_first_capture_science(tmp_path):
 from projects.g_agreement.blindspot.screens import chain
 a=booking()
 assert chain.child_deadline(a,tmp_path,False)==a['setup_deadline_epoch']
 assert chain.child_deadline(a,tmp_path,True)==a['setup_deadline_epoch']
 p=tmp_path/'native';p.mkdir();(p/'stage_complete.s79.json').write_text('{')
 assert chain.child_deadline(a,tmp_path,True)==a['setup_deadline_epoch']
 C.save(p/'stage_complete.s79.json',{'at':a['setup_deadline_epoch']-100})
 assert chain.child_deadline(a,tmp_path,True)==a['setup_deadline_epoch']-100+7200
 assert chain.child_deadline(a,tmp_path,False)==a['setup_deadline_epoch']
 C.save(p/'stage_complete.s79.json',{'at':a['setup_deadline_epoch']+1})
 with pytest.raises(TimeoutError,match='setup'):chain.child_deadline(a,tmp_path,True)


def test_unscored_setup_warmup_all_paths_rng_and_shapes(monkeypatch):
 from contextlib import contextmanager
 import mats.capture as capture_module
 events=[]
 class Reader:
  active=True
  model=object()
  @contextmanager
  def base(self):
   old=self.active;self.active=False
   try:yield
   finally:self.active=old
  no_adapter=base
 class Tok:
  pad_token_id=0
  def __call__(self,text,add_special_tokens):
   assert text=='Neutral setup warmup text.' and not add_special_tokens
   return {'input_ids':[1,2,3]}
 ol,nla=Reader(),Reader()
 def capture(model,seqs,sites,positions,batch_size,pad_id):
  assert not ol.active and [len(s) for s in seqs]==[512,384,256,128]
  assert sites==[42,44] and positions==[[511],[383],[255],[127]] and batch_size==4
  events.append('target');return {site:torch.rand(4,1,3) for site in sites}
 class Discard:
  def __float__(self):raise AssertionError('warmup output inspected as outcome')
 def asked(name,reader,states,pair):
  assert states.shape==(R.SCORE_POINTS_PER_CHUNK,3) and pair==['This is setup text.','This is warmup text.']
  events.append(name+('-active' if reader.active else '-base'));return Discard()
 monkeypatch.setattr(capture_module,'capture',capture);monkeypatch.setattr(R,'asked',asked);monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
 before=torch.random.get_rng_state().clone();sync=[];progress=[]
 proof=R.warmup(ol,nla,Tok(),progress=lambda **kw:progress.append(kw),synchronize=lambda:sync.append(True))
 assert events==list(P.WARMUP_PATHS)*P.WARMUP_ITERATIONS
 assert proof['completed_paths']==events and proof['outcome_rows']==0
 assert all(p['phase']=='warmup' and p['outcome_rows']==0 for p in progress)
 assert len(sync)==P.WARMUP_ITERATIONS and torch.equal(before,torch.random.get_rng_state())
 assert ol.active and nla.active
 P.validate_warmup(proof,proof['completed_at'])
 for change in [{'completed_paths':events[:-1]},{'outcome_rows':1},{'setup_only':False},{'unscored':False},{'iterations':P.WARMUP_ITERATIONS+1}]:
  with pytest.raises(ValueError):P.validate_warmup(dict(proof,**change),proof['completed_at'])
 with pytest.raises(ValueError,match='after first science'):P.validate_warmup(proof,proof['started_at']-1)


def test_warmup_setup_cutoff_before_any_forward():
 class Tok:
  def __call__(self,*a,**kw):raise AssertionError('tokenization/forward after setup cutoff')
 def expired():raise TimeoutError('setup cutoff')
 with pytest.raises(TimeoutError,match='setup cutoff'):R.warmup(None,None,Tok(),check=expired,synchronize=lambda:None)
