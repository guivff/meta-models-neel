"""E120b exclusive two-stage driver; real capture delivery required; never replay."""
from pathlib import Path
import json,hashlib,os,pickle,subprocess,time
from datetime import datetime,timezone
import numpy as np
from sklearn.metrics import roc_auc_score
from probes import fit_dev,reading,validate_metadata,POSITIONS
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
CACHE=ROOT/'cache/g_agreement/understand/e120/decoder';OUT=HERE/'analysis_once'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n')
def claim(p,d):
 with Path(p).open('x') as f:json.dump(d,f);f.flush();os.fsync(f.fileno())
def now():return datetime.now(timezone.utc).isoformat()
def verify(p):
 p=Path(p);d=read(p)
 for n,h in d['files'].items():
  f=(p.parent/n).resolve();assert f.is_relative_to(p.parent.resolve());assert sha(f)==h,n
 return d

def preflight(plan):
 for f,h in plan['pins'].items():assert sha(f)==h,f
 labelpath=Path(plan['original_labels']);assert sha(labelpath)=='5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44'
 cap=Path(plan['capture_root']);lay=Path(plan['layout_root']);s=verify(cap/'OUTPUT_SEAL.json');fmt=read(cap/'decoder/CAPTURE_FORMAT.json');layout=verify(lay/'LAYOUT_SEAL.json')
 assert sha(cap/'OUTPUT_SEAL.json')==plan['original_output_seal_sha256']
 assert s['experiment']=='E120' and s['part']=='ab' and s['status']=='COMPLETE' and s['judging'] is False
 assert fmt['layers']==list(range(64)) and fmt['positions']==list(POSITIONS) and fmt['source_layer']==44
 assert fmt['first_generated_position']==len(fmt['carrier_ids']) and fmt['first_generated_position']>fmt['injected_position']
 assert fmt['alpha']==16000 and fmt['transform']=='unit'
 assert fmt['first_generated_capture']=='full forward on native injected carrier plus its actual greedy first token; not the last carrier token'
 assert layout['source_output_sha256']==sha(cap/'OUTPUT_SEAL.json') and layout['bit_identical_items']==600 and layout['scientific_values_transformed'] is False
 order=read(lay/'ORDER.json');index=read(lay/'INDEX.NORMALIZED.json')
 for r in index:assert r['injected_position']==fmt['injected_position'] and r['first_generated_position']==fmt['first_generated_position']
 return validate_metadata(order,index,read(labelpath))

def main():
 start=time.monotonic();planpath=HERE/'INPUT_PLAN.json';plan=read(planpath);code=read(HERE/'CODE_SEAL.json')
 for name,h in code['files'].items():
  p=HERE/name;assert sha(p)==h;assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
 assert subprocess.check_output(['git','show','HEAD:'+str(planpath.relative_to(ROOT))],cwd=ROOT)==planpath.read_bytes()
 assert not (CACHE/'ONCE.json').exists() and not (CACHE/'TEST_ONCE.json').exists() and not OUT.exists()
 labels,tokens=preflight(plan);CACHE.mkdir(parents=True,exist_ok=True);claim(CACHE/'ONCE.json',dict(start=now(),plan_sha256=sha(planpath)))
 layout=Path(plan['layout_root']);dev=np.load(layout/'dev.npy',mmap_mode='r',allow_pickle=False);assert dev.shape==(200,64,2,5120) and dev.dtype==np.float32 and np.isfinite(dev).all()
 weights=CACHE/'weights';weights.mkdir();models={};selection={}
 for l in range(64):
  for pos,name in enumerate(POSITIONS):
   k=f'L{l:02d}__{name}';m,s=fit_dev(dev[:,l,pos,:],labels['dev']);p=weights/(k+'.pkl');p.write_bytes(pickle.dumps(m,protocol=5));models[k]=sha(p);selection[k]=s
 del dev
 write(CACHE/'DEV_SELECTION.json',selection);write(CACHE/'FIT_SEAL.json',dict(completed=now(),status='ALL128_DEV_FITS_FROZEN',files=models,selection_sha256=sha(CACHE/'DEV_SELECTION.json'),test_arrays_opened=False))
 claim(CACHE/'TEST_ONCE.json',dict(start=now(),fit_seal_sha256=sha(CACHE/'FIT_SEAL.json')))
 test=np.load(layout/'test.npy',mmap_mode='r',allow_pickle=False);assert test.shape==(400,64,2,5120) and test.dtype==np.float32 and np.isfinite(test).all()
 grid={};preds={}
 for l in range(64):
  grid[str(l)]={}
  for pos,name in enumerate(POSITIONS):
   k=f'L{l:02d}__{name}';p=weights/(k+'.pkl');assert sha(p)==models[k];m=pickle.loads(p.read_bytes());z=m.decision_function(test[:,l,pos,:]);grid[str(l)][name]=float(roc_auc_score(labels['test'],z));preds[k]=z.tolist()
 write(CACHE/'TEST_PREDICTIONS.PRIVATE.json',preds);OUT.mkdir();result=dict(experiment='E120b',status='COMPLETE_ONCE',grid=grid,reading=reading(grid),token_id_distribution=tokens,dev_n=200,test_n=400,probe_count=128,positive_class='addressed=1',test_sign_flip=False,wall_seconds=time.monotonic()-start,gpu_hours=0)
 write(OUT/'RESULTS.json',result);write(OUT/'ANALYSIS_SEAL.json',dict(status='COMPLETE_ONCE',plan_sha256=sha(planpath),code_seal_sha256=sha(HERE/'CODE_SEAL.json'),fit_seal_sha256=sha(CACHE/'FIT_SEAL.json'),files={'RESULTS.json':sha(OUT/'RESULTS.json')}));print(json.dumps(result['reading']))
if __name__=='__main__':main()
