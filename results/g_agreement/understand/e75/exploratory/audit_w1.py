"""EXPLORATORY saved-artifact provenance audit; no forward, pursuit or forecast."""
import json,hashlib,subprocess
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 refs={}
 def ref(p,expected=None):
  p=Path(p).resolve();h=sha(p);assert expected is None or h==expected,(str(p),'seal mismatch');refs[str(p)]=h;return p
 channel=ROOT/'results/g_agreement/understand/e57/jlens'
 for s in [channel/'CODE_SEAL_2026-10-27.json',ROOT/'results/g_agreement/understand/e52/r3b/E73_ADAPTER_SEAL.json']:
  for n,h in read(ref(s))['files'].items():ref(ROOT/n,h)
 plan=read(ref(channel/'E73_INPUT_PLAN.json'));delivery=read(ref(plan['intake_ref']['path'],plan['intake_ref']['sha256']))
 for field in ['atom_seal','null_seal','activations','order','records','capture_seal','bank_seal']:
  ref(plan[field]['path'],plan[field]['sha256'])
 for field in ['atom_seal','null_seal']:
  f=Path(plan[field]['path']);s=read(f)
  for n,h in s['files'].items():ref(f.parent/n,h)
 basis=ROOT/'results/g_agreement/understand/e52/BASIS_SEAL_2026-10-27.json';ref(basis)
 source_repo=ROOT.parent/'wt-wcensus';capture='projects/g_agreement/e73/capture.py';blob=subprocess.check_output(['git','show',plan['producer_commits']['capture']+':'+capture],cwd=source_repo)
 admission=read(ref(delivery['captures'][0]['admission']['path'],delivery['captures'][0]['admission']['sha256']))
 assert hashlib.sha256(blob).hexdigest()==admission['source_files'][capture]
 source=blob.decode();assert 'blocks(model)[layer].register_forward_hook' in source and 'chosen = h if layer == 44 else h[:, -1, :]'in source
 selected=set(next(u['item_ids']for u in plan['units']if u['id']=='W1'));positions=[x for x in delivery['positions']if x['id']in selected]
 assert len(positions)==400 and all(x['read_index']==255 and len(x['input_ids'])==256 for x in positions)
 # Synthetic capture dependencies are pinned by the E56 acquisition seal.
 syn=ROOT.parent/'wt-wmech';dep=ref(syn/'results/g_agreement/understand/e56/job/DEPENDENCIES.json');deps=read(dep)
 for n in ['results/g_agreement/understand/e49/job/vendor/e36_worker.py','results/g_agreement/understand/e49/job/runtime49.py','external/mats-nla-workspace/src/mats/capture.py']:
  ref(syn/n,deps[n])
 worker=(syn/'results/g_agreement/understand/e49/job/vendor/e36_worker.py').read_text();assert '[[len(x["ids"]) - 1] for x in items]'in worker
 units={};numeric={}
 for b in ['E56','E57','E59','E62','E73']:
  pp=ref(channel/f'{b}_INPUT_PLAN.json');p=read(pp);assert p['layer']==44 and p['split']=='test'
  labels=read(ref(channel/f'{b}_results/ROW_LABELS.json'));labelseal=read(ref(channel/f'{b}_results/LABEL_SEAL.json'))
  assert sha(channel/f'{b}_results/ROW_LABELS.json')==labelseal['files']['ROW_LABELS.json']
  raw=Path(labels['raw_directory']);rs=read(ref(raw/'RAW_SEAL.json'));assert sha(raw/'RAW_SEAL.json')==labels['raw_seal_sha256']
  row=next(r for r in labels['rows']if r['row']==('W1'if b=='E73'else next(u['id']for u in p['units']if u['binary'])))
  name=row['row']+'.direction.npz';f=ref(raw/name,rs['files'][name]);z=np.load(f,allow_pickle=False)
  direction=z['direction'];diff=z['class_means'][0]-z['class_means'][1];expected=diff/np.linalg.norm(diff)
  assert np.allclose(direction,expected,rtol=0,atol=1e-14)
  hh=np.asarray(direction,dtype=np.float32).astype(np.float64);rr=z['reconstruction'].astype(np.float64).reshape(-1)
  savedratio=float(np.square(rr).sum()/np.square(hh).sum());assert abs(savedratio-row['J_fraction'])<1e-14
  assert z['indices'].shape==(1,16)and (z['coefficients']>=0).all()
  acts=np.load(p['activations']['path'],mmap_mode='r',allow_pickle=False)
  numeric[b]={'sample_row':row['row'],'n_test':row['n_test'],'activation_storage_dtype':str(acts.dtype),'direction_norm':float(np.linalg.norm(direction)),'saved_fraction_ratio':savedratio,'saved_fraction':row['J_fraction'],'k':16}
  if b=='E73':
   order=read(p['order']['path']);records={r['id']:r for r in read(p['records']['path'])};idx={v:i for i,v in enumerate(order)}
   for label,k in [(1,0),(0,1)]:
    ix=[idx[i]for i in selected if records[i]['label']==label];assert len(ix)==200
    assert np.allclose(np.asarray(acts[ix],dtype=np.float64).mean(0),z['class_means'][k],atol=1e-12,rtol=0)
  units[b]={'plan':str(pp),'layer':p['layer'],'split':p['split'],'code_seal':labels['code_seal_sha256']}
 assert len({u['code_seal']for u in units.values()})==1
 null=read(plan['null_seal']['path']);truth=read(ROOT/'results/g_agreement/understand/e75/QWEN_BOUND_UNITS.json')['panels']['primary']
 out={'label':'EXPLORATORY','verdict':'NO_REGISTERED_MEASUREMENT_MISMATCH_FOUND; W1 remains a false alarm for both readers','layer':'zero-based decoder block44 output, HF hidden_states45','token_position':'same final-input-token convention; E73 index255 of256, synthetic variable lengths use len(ids)-1; absolute token indices differ by design','basis':'same pinned J44 unit-normalised W_U @ J44 atom dictionary, no final-norm gain; SVD basis is unchanged secondary diagnostic','pursuit':'same CPU channel and nn_pursuit, k16, six projected-gradient refinement steps per selection; no rerun','normalisation':'float64 A-minus-B mean direction divided by L2 norm, float32 pursuit input; squared reconstruction norm / squared input norm; same200-direction null','A_B':'E73 original A0/B1 explicitly converted to common A1/B0 before means; verified saved W1 means against all400 bound vectors','differences':'E73 uses400 tests/state and float16 activation storage; synthetic84/unit and float32 storage. Same extraction point and downstream normalisation; this audit does not establish numerical identity across acquisition implementations.','W1':numeric['E73'],'W1_G3':'NOT EVALUABLE: frozen A-token set empty. Existing primary_label permits IN-J when readability is NOT EVALUABLE; unchanged in this audit.','null_median':null['median'],'null_percentile975':null['percentile97_5'],'W1_truth':[r for r in truth if r['bank']=='E73'and r['row']=='W1'],'banks':units,'saved_numeric_checks':numeric,'source_sha256':refs,'R_P1':'UNCHANGED NOT EVALUABLE','new_forward_or_pursuit':False}
 (HERE/'W1_AUDIT.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print('EXPLORATORY W1 audit PASS; no measurement mismatch found')
if __name__=='__main__':main()
