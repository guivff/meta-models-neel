"""New E115a CPU claim only. Never invokes an original experiment runner."""
import json,hashlib,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from metrics import j_fraction,paired_summary
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 t=time.monotonic();plan=json.loads((HERE/'PART_A_PLAN.json').read_text());p=Path(plan['binding']);assert sha(p)==plan['binding_sha256'];d=json.loads(p.read_text())
 for f,h in {**d['pins'],**plan['code_pins']}.items():assert sha(f)==h,f
 for f in plan['code_pins']:
  rel=str(Path(f).relative_to(ROOT));assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)==Path(f).read_bytes()
 out=HERE/'part_a_once';assert not out.exists()
 guard=ROOT/'cache/g_agreement/understand/e115/PART_A_ONCE.json';guard.parent.mkdir(parents=True,exist_ok=True)
 with guard.open('x') as f:json.dump(dict(created_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(HERE/'PART_A_PLAN.json')),f)
 q=np.load(d['basis'],allow_pickle=False).astype(np.float64);assert q.shape==(5120,384) and np.max(abs(q.T@q-np.eye(384)))<1e-4
 orig=np.load(d['mean_source'],allow_pickle=False).astype(np.float64);assert orig.shape==(518,5120)
 mean=orig.mean(axis=0);cohort=d['cohort'];cache={};fractions={}
 for c,refs in d['vectors'].items():
  by={x['item_id']:x for x in refs};xs=[]
  for i in cohort:
   r=by[i];path=r['file']
   if path not in cache:cache[path]=np.load(path,allow_pickle=False)
   a=cache[path];assert a.ndim==2 and a.shape[1]==5120;xs.append(a[r['index']])
  fractions[c]=j_fraction(np.stack(xs),mean,q)
 u=d['unhooked'];x=np.load(u['file'],allow_pickle=False);assert x.shape==(84,5120)
 fractions['unhooked']=j_fraction(x[[u['ids'].index(i) for i in cohort]],mean,q)
 result=paired_summary(fractions['steered'],fractions['random'])
 rng=np.random.default_rng(20261029);ix=rng.integers(0,84,size=(2000,84));result['unhooked_mean']=float(fractions['unhooked'].mean());result['unhooked_mean_ci']=np.quantile(fractions['unhooked'][ix].mean(1),[.025,.975]).tolist()
 result.update(experiment='E115a',status='COMPLETE_ONCE',descriptive=True,recipe='E80c frozen J384, original518 mean, squared projection energy / centered norm squared',bootstrap=dict(draws=2000,seed=20261029,unit='paired item'),orientation='steered=1, random=0; raw fraction; no sign selection',nla_agreement=d['nla'],reader_internal_probe=d['part_c'],wall_seconds=time.monotonic()-t,gpu_hours=0)
 a=result['auroc'];lo=result['auroc_ci'][0];result['pre_stated_reading']='FLAGS_STALENESS' if a>=.70 and lo>.5 else 'BLIND_TO_STALENESS' if a<=.60 else 'INCONCLUSIVE'
 private=guard.parent/'PART_A_FRACTIONS.PRIVATE.json';private.write_text(json.dumps({'ids':cohort,'fractions':{k:v.tolist() for k,v in fractions.items()}},indent=2)+'\n');private.chmod(0o600)
 out.mkdir();(out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');(out/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(status='COMPLETE_ONCE',plan_sha256=sha(HERE/'PART_A_PLAN.json'),private_fractions_sha256=sha(private),files={'RESULTS.json':sha(out/'RESULTS.json')}),indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
