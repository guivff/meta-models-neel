"""E80b pinned WorkspaceBench cosine readout, CPU only, separate once-only scope."""
import hashlib,json,sys,subprocess,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e80/jlens'))
import forecast as original
# When executed this module is __main__, so the import above resolves the sealed E80 helper.
def read(p):return json.loads(Path(p).read_text())
def sha(p):return original.sha(p)
def dump(p,x):original.dump(p,x)
def denominators(j,wu):
 import torch
 return torch.cat([(wu[s:s+1024]@j).norm(dim=1).clamp_min(1e-9) for s in range(0,len(wu),1024)])
def cosine(h,j,wu,denom):return ((h@j.T)@wu.T)/denom

def run():
 plan=read(HERE/'RUN_PLAN.json')
 for n,h in plan['code_files'].items():assert sha(ROOT/n)==h
 for p in [HERE/'RUN_PLAN.json',HERE/'forecast.py',HERE/'test_forecast.py']:
  assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
 for r in plan['references'].values():assert sha(r['path'])==r['sha256']
 public,targets=original.validate_export(read(ROOT/'results/g_agreement/understand/e80/jlens/PRECAPTURE_PLAN.json'))
 manifest=read(plan['references']['manifest']['path']);order,acts=original.validate_capture(manifest,public)
 from tokenizers import Tokenizer
 tok=Tokenizer.from_file(plan['references']['tokenizer']['path'])
 expanded=[{'id':t['id'],'token_ids':sorted({tok.encode(v+s,add_special_tokens=False).ids[0] for s in t['item_targets'] for v in ('',' ')})} for t in targets]
 assert expanded==read(plan['references']['targets']['path'])
 sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e52'))
 from run_labels import FullRankReader
 reader=FullRankReader() # weights and runtime pins verified; score() never called
 import torch
 claim=ROOT/'cache/g_agreement/understand/e80b/ONCE.json';claim.parent.mkdir(parents=True,exist_ok=True)
 with claim.open('x') as f:json.dump({'created_epoch':time.time(),'run_plan_sha256':sha(HERE/'RUN_PLAN.json'),'status':'CLAIMED_NEVER_RESET'},f)
 started=time.time();td={r['id']:r['token_ids'] for r in expanded};pd={r['id']:r for r in public};rows=[]
 with torch.inference_mode():
  denom=denominators(reader.j,reader.wu)
  assert torch.isfinite(denom).all()
  print('E80b exact vocabulary denominators ready',flush=True)
  for s in range(0,518,8):
   h=torch.tensor(np.array(acts[s:s+8]),dtype=torch.float32)
   logits=cosine(h,reader.j,reader.wu,denom);tops=logits.topk(10,dim=1).indices.numpy()
   for i in range(len(h)):
    r=order[s+i];rows.append({'id':r['id'],'family':pd[r['id']]['family'],'read_position':r['read_position'],'J':original.summarise_logits(logits[i].numpy(),td[r['id']],tops[i]),'target_token_ids':td[r['id']]})
 print('E80b scoring complete',flush=True)
 output={'experiment':'E80b','authority':plan['authority'],'capture_seal_sha256':plan['capture_seal_sha256'],'original_forecast_commit':plan['original_forecast_commit'],'item_count':len(rows),'rows':rows,'readout':'((h44 @ J44.T) @ W_U.T) / clamp(norm(W_U @ J44, dim=1), min=1e-9); fp32 CPU; no final RMSNorm','target_rule':'union of bare and single-space-prefixed first token IDs; no special tokens','rank_rule':'rank0 counts strictly greater scores; rank1=rank0+1; actual torch.topk membership','reader_outcomes_accessed':False,'GO_sent':False,'wall_seconds':time.time()-started,'created_epoch':time.time(),'run_plan_sha256':sha(HERE/'RUN_PLAN.json')}
 dump(HERE/'E80B_ITEM_FORECAST.json',output)
 dump(HERE/'E80B_ITEM_FORECAST_SEAL.json',{'files':{'E80B_ITEM_FORECAST.json':sha(HERE/'E80B_ITEM_FORECAST.json')},'run_plan_sha256':sha(HERE/'RUN_PLAN.json'),'claim_sha256':sha(claim)})
if __name__=='__main__':run()
