"""E113 two-stage CPU once driver. Never run twice or reset any guard."""
from pathlib import Path
import json,pickle,os,time,datetime,hashlib,subprocess,sys
from probes import ROWS,POSITIONS,fit_dev,evaluate_test_once,decisions
from intake import read,sha,preflight,load_split
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
CACHE=ROOT/'cache/g_agreement/understand/e113/probes226'
OUT=HERE/'analysis_once'
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n')
def claim(p,d):
 with Path(p).open('x') as f:json.dump(d,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 start=time.monotonic();plan=read(HERE/'FINAL_INPUT_PLAN.json')
 for f,h in plan['code'].items():
  p=HERE/f;assert sha(p)==h,f
  assert hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)).hexdigest()==h,'code committed'
 p=HERE/'FINAL_INPUT_PLAN.json';assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'plan committed'
 assert not (CACHE/'ONCE.json').exists() and not OUT.exists(),'never replay/reset'
 labels=preflight(plan);print('PREFLIGHT PASS',flush=True)
 if '--preflight-only' in sys.argv:return
 CACHE.mkdir(parents=True,exist_ok=True)
 claim(CACHE/'ONCE.json',{'experiment':'E113','start':now(),'input_plan_sha256':sha(p),'pid':os.getpid()})
 weights=CACHE/'weights';weights.mkdir();models={};meta={};fitstart=time.monotonic()
 # Do not load a test array or evaluate a test metric until ALL dev fits are frozen.
 for row in ROWS:
  a=load_split(plan['layout_root'],row,'dev')
  for layer in range(64):
   for pos,position in enumerate(POSITIONS):
    key=f'{row}__L{layer:02d}__{position}'
    m,s=fit_dev(a[:,layer,pos,:],labels[row+':dev'])
    path=weights/(key+'.pkl');path.write_bytes(pickle.dumps(m,protocol=5))
    models[key]=sha(path);meta[key]=s
   if layer%16==15:print('DEV',row,layer+1,'/64',flush=True)
  del a
 write(CACHE/'DEV_SELECTION.json',meta)
 write(CACHE/'FIT_SEAL.json',{'status':'ALL_768_DEV_FITS_FROZEN','files':models,'selection_sha256':sha(CACHE/'DEV_SELECTION.json'),'completed':now(),'fit_seconds':time.monotonic()-fitstart,'test_arrays_opened':False})
 # Exclusive independent guard bound to all already-frozen dev fits.
 claim(CACHE/'TEST_ONCE.json',{'start':now(),'fit_seal_sha256':sha(CACHE/'FIT_SEAL.json'),'input_plan_sha256':sha(p)})
 aucs={r:{} for r in ROWS};preds={}
 for row in ROWS:
  a=load_split(plan['layout_root'],row,'test')
  for layer in range(64):
   aucs[row][str(layer)]={}
   for pos,position in enumerate(POSITIONS):
    key=f'{row}__L{layer:02d}__{position}';path=weights/(key+'.pkl');assert sha(path)==models[key]
    m=pickle.loads(path.read_bytes());x=a[:,layer,pos,:];y=labels[row+':test']
    aucs[row][str(layer)][position]=evaluate_test_once(m,x,y)
    preds[key]=m.decision_function(x).tolist()
  del a
  print('TEST COMPLETE',row,flush=True)
 write(CACHE/'TEST_PREDICTIONS.PRIVATE.json',preds)
 OUT.mkdir();result={'experiment':'E113','rows':aucs,'rules':decisions(aucs),'test_AUROC_cells':768,'test_items_per_row':84,'dev_items_per_row':84,'no_test_selection':True,'input_plan_sha256':sha(p),'fit_seal_sha256':sha(CACHE/'FIT_SEAL.json'),'test_prediction_sha256':sha(CACHE/'TEST_PREDICTIONS.PRIVATE.json'),'final_adapter_after_capture':True,'kernel_plan_before_capture':'fc5573e04','wall_seconds':time.monotonic()-start,'gpu_hours':0}
 write(OUT/'RESULTS.json',result)
 report=['# E113 §226 Oracle-internal probes','', 'Each row × 64 decoder-block outputs × 2 positions has a separate dev-fit probe; all 768 test AUROCs evaluated once after every dev fit was frozen. Original84dev/84test per row, class1 unchanged. Fivefold dev-only C selection and fold-local scaling; no test sign inversion or selected-layer-only reporting.','',f"R-IN1: {'MET' if result['rules']['R_IN1'] else 'NOT MET'}. Falsifier: {'MET' if result['rules']['falsifier'] else 'NOT MET'}.",'','| Row | Maximum across full test grid (registered threshold summary) |','|---|---:|']
 report += [f'| {r} | {v:.6f} |' for r,v in result['rules']['row_max_AUROC'].items()]
 report += ['','All per-layer/position cells are in RESULTS.json and AUROC_BY_LAYER.md. Maxima are the registered any-layer rule summary, not dev-selected layer estimates. Finite complete cells required; no missing imputation.','', 'Chronology: original kernel/recipe fc5573e04 preceded capture; the exact layout binder/final source/input plan were written after capture and committed before the exclusive CPU claim. Complete final-adapter pre-capture custody is not claimed. Runner capture source/position trace: injectedslot24 in native prefill; actual first greedy token appendedslot56 from full forward, including EOS. Arrays are block outputs0..63; no subject-layer44 substitution.','', 'No judging, model forward, original bank replay or new GPU allocation by W-lens. Runner custody cost is owned/booked by W-mechanism-C; not rebooked here. Independent R-Q review requested after seal.']
 (OUT/'REPORT.md').write_text('\n'.join(report)+'\n')
 table=['# E113 complete test AUROC grid','','| Row | Lens block output | Injected activation | First generated token |','|---|---:|---:|---:|']
 for r in ROWS:
  for l in range(64):table.append(f"| {r} | {l} | {aucs[r][str(l)][POSITIONS[0]]:.6f} | {aucs[r][str(l)][POSITIONS[1]]:.6f} |")
 (OUT/'AUROC_BY_LAYER.md').write_text('\n'.join(table)+'\n')
 write(OUT/'EXECUTION.json',{'start_claim':read(CACHE/'ONCE.json'),'first_result_mtime_ns':(OUT/'RESULTS.json').stat().st_mtime_ns,'completed':now(),'wall_seconds':time.monotonic()-start,'python':sys.version,'fit_count':768,'test_cell_count':768,'GPU_hours':0})
 write(OUT/'ANALYSIS_SEAL.json',{'experiment':'E113','status':'COMPLETE_ONCE','input_plan_sha256':sha(p),'fit_seal_sha256':sha(CACHE/'FIT_SEAL.json'),'files':{f:sha(OUT/f) for f in ['RESULTS.json','REPORT.md','AUROC_BY_LAYER.md','EXECUTION.json']}})
 print('COMPLETE',json.dumps(result['rules']),flush=True)
if __name__=='__main__':main()
