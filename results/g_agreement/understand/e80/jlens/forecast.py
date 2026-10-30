"""E80 prospective item visibility. CPU only; no work or model loading on import."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
COUNTS={'multihop':100,'multilingual_multihop':98,'chain_intermediates':120,'association':100,'poetry':100}

def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def committed(p):
 p=Path(p).resolve();assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'must commit before scoring'
def reference(r):
 p=Path(r['path']).resolve();assert sha(p)==r['sha256'],'source hash mismatch';return p

def validate_export(plan):
 root=Path(plan['export_repo']);h=root/'results/g_agreement/understand/e80'
 for name in ['EXPORT_SEAL.json','DELIVERY.json']:
  p=h/name;reference(plan[name]);assert subprocess.check_output(['git','show','d1892cb:'+str(p.relative_to(root))],cwd=root)==p.read_bytes()
 seal=read(h/'EXPORT_SEAL.json');delivery=read(h/'DELIVERY.json');assert sha(h/'EXPORT_SEAL.json')==delivery['export_seal_sha256']
 for n,v in seal['files'].items():assert sha(h/n)==v,('export member mismatch',n)
 for r in delivery['archives'].values():reference(r)
 public=read(Path(delivery['export_root'])/'CAPTURE_INPUTS.json');targets=read(Path(delivery['export_root'])/'TARGETS.PRIVATE.json')
 validate_items(public,targets)
 from tokenizers import Tokenizer
 tok=Tokenizer.from_file(str(reference(plan['tokenizer'])))
 for t in targets:
  assert [tok.encode(s,add_special_tokens=False).ids[0]for s in t['item_targets']]==t['target_first_token_ids'],'literal first-token mismatch'
 return public,targets

def validate_items(public,targets):
 assert len(public)==len(targets)==518
 ids=[r['id']for r in public];assert len(set(ids))==518 and set(ids)=={r['id']for r in targets}
 assert {f:sum(r['family']==f for r in public)for f in COUNTS}==COUNTS
 td={r['id']:r for r in targets}
 for r in public:
  assert r['family']==td[r['id']]['family'] and r['family']in COUNTS
  assert r['read_position']==r['plan_positions'][-1] and 0<=r['read_position']<len(r['ids'])
  assert r['ids'][r['read_position']]==r['read_token_id']
  ts=td[r['id']];assert ts['item_targets']and len(ts['item_targets'])==len(ts['target_first_token_ids'])
  assert all(type(t)is int and t>=0 for t in ts['target_first_token_ids'])

def validate_capture(manifest,public,expected_capture_sha=None):
 assert manifest['experiment']=='E80' and manifest['layer']==44 and manifest['site']=='decoder_block_output'
 assert manifest['issuer']=='integrator' and manifest['reader_outputs_opened']is False and manifest['readers_held_until_forecast_commit']is True
 if expected_capture_sha is None:expected_capture_sha=read(HERE/'PRECAPTURE_PLAN.json')['capture_inputs']['sha256']
 assert manifest['capture_inputs_sha256']==expected_capture_sha
 order=read(reference(manifest['order']));acts=np.load(reference(manifest['activations']),allow_pickle=False,mmap_mode='r')
 assert len(order)==len(public)==518 and len({r['id']for r in order})==518
 pd={r['id']:r for r in public};assert set(pd)=={r['id']for r in order}
 for r in order:
  p=pd[r['id']];assert r['read_position']==p['read_position'] and r['token_ids_sha256']==hashlib.sha256(json.dumps(p['ids'],separators=(',',':')).encode()).hexdigest()
 assert acts.shape==(518,5120)and np.isfinite(acts).all()
 return order,acts

def summarise_logits(logits,target_ids,top_ids=None):
 """Exact top10 membership; rank0 counts strictly greater vocabulary logits."""
 logits=np.asarray(logits);targets=np.array(sorted(set(target_ids)),dtype=np.int64)
 assert logits.ndim==1 and np.isfinite(logits).all()and len(targets)>0 and targets.min()>=0 and targets.max()<len(logits)
 if top_ids is None:
  import torch
  top_ids=torch.from_numpy(logits.copy()).topk(min(10,len(logits))).indices.numpy()
 best=float(np.max(logits[targets]));rank=int(np.sum(logits>best))
 return {'visible_top10':bool(np.isin(top_ids,targets).any()),'best_target_rank0':rank,'best_target_rank1':rank+1,'top10_token_ids':[int(x)for x in top_ids]}

def score_activations(acts,order,public,targets,reader,progress=False):
 import torch
 rows=[];td={r['id']:r for r in targets};pd={r['id']:r for r in public}
 with torch.inference_mode():
  for start in range(0,len(order),8):
   h=torch.tensor(np.array(acts[start:start+8]),dtype=torch.float32,device='cpu')
   for name,z in [('J',h@reader.j.T),('logit',h)]:
    logits=reader.norm(z.to(torch.bfloat16)).float()@reader.wu.T
    assert torch.isfinite(logits).all()
    top=logits.topk(10,dim=1).indices.numpy()
    for i in range(len(h)):
     r=order[start+i];p=pd[r['id']]
     if name=='J':rows.append({'id':r['id'],'family':p['family'],'read_position':p['read_position']})
     rows[start+i][name]=summarise_logits(logits[i].numpy(),td[r['id']]['target_first_token_ids'],top[i])
   if progress:print('E80 forecasted',min(start+8,len(order)),'/518',flush=True)
 assert len(rows)==len(order)and all(set(['J','logit'])<=r.keys()for r in rows)
 return rows

def bind(manifest_path):
 plan=read(HERE/'PRECAPTURE_PLAN.json');public,_=validate_export(plan);manifest=read(manifest_path);order,acts=validate_capture(manifest,public)
 for name,h in read(HERE/'CODE_SEAL.json')['files'].items():assert sha(ROOT/name)==h
 assert not (HERE/'E80_ITEM_FORECAST.json').exists() and not (ROOT/'cache/g_agreement/understand/e80/jlens/ONCE.json').exists()
 run={'experiment':'E80','status':'CAPTURE_BOUND_AWAITING_COMMIT','capture_manifest':{'path':str(Path(manifest_path).resolve()),'sha256':sha(manifest_path)},'precapture_plan_sha256':sha(HERE/'PRECAPTURE_PLAN.json'),'code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'count':len(order),'reader_outcomes_accessed':False}
 dump(HERE/'RUN_PLAN.json',run);print('E80 bound518; commit RUN_PLAN before run; no scoring')

def run():
 for p in [HERE/'PRECAPTURE_PLAN.json',HERE/'CODE_SEAL.json',HERE/'RUN_PLAN.json']:committed(p)
 for n,h in read(HERE/'CODE_SEAL.json')['files'].items():assert sha(ROOT/n)==h
 rp=read(HERE/'RUN_PLAN.json');assert sha(HERE/'PRECAPTURE_PLAN.json')==rp['precapture_plan_sha256']and sha(HERE/'CODE_SEAL.json')==rp['code_seal_sha256']
 public,targets=validate_export(read(HERE/'PRECAPTURE_PLAN.json'));order,acts=validate_capture(read(reference(rp['capture_manifest'])),public)
 sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e52'))
 from run_labels import FullRankReader
 reader=FullRankReader() # validates pinned weights/runtime, no target-model forward
 import torch
 out=ROOT/'cache/g_agreement/understand/e80/jlens';out.mkdir(parents=True,exist_ok=True)
 with (out/'ONCE.json').open('x')as f:json.dump({'experiment':'E80','status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'run_plan_sha256':sha(HERE/'RUN_PLAN.json')},f)
 started=time.time();rows=score_activations(acts,order,public,targets,reader,progress=True)
 assert len(rows)==518
 output={'experiment':'E80','status':'PROSPECTIVE_FORECAST_AWAITING_COMMIT','rows':rows,'item_count':518,'families':COUNTS,'forecast_rule':'literal target first token, no added space; actual top10 membership; full-vocabulary best rank0 plus rank1','capture_manifest':rp['capture_manifest'],'run_plan_sha256':sha(HERE/'RUN_PLAN.json'),'precapture_plan_sha256':sha(HERE/'PRECAPTURE_PLAN.json'),'reader_outcomes_accessed':False,'GO_sent':False,'GPU_hours':0,'wall_seconds':time.time()-started,'created_epoch':time.time()}
 dump(HERE/'E80_ITEM_FORECAST.json',output);dump(HERE/'E80_ITEM_FORECAST_SEAL.json',{'files':{'E80_ITEM_FORECAST.json':sha(HERE/'E80_ITEM_FORECAST.json')},'claim_sha256':sha(out/'ONCE.json'),'run_plan_sha256':sha(HERE/'RUN_PLAN.json')})
 print('E80 forecast ready; commit before I-2 GO')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['bind','run']);p.add_argument('--capture-manifest',type=Path);a=p.parse_args()
 if a.stage=='bind':assert a.capture_manifest;bind(a.capture_manifest)
 else:assert a.capture_manifest is None;run()
