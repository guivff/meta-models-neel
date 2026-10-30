"""CPU-only probe and class means. Private labels are never copied to pod inputs."""
import argparse,sys
from pathlib import Path
import numpy as np
from contract56 import ROOT,HERE,read,dump,verify,sha,seal,require,SEED

def compute(items,acts,probe_rows=None):
 import torch
 sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
 from mats.probes import fit_logreg
 torch.set_num_threads(1);torch.manual_seed(SEED)
 scores=[];means={}
 for row in sorted({x['feature'] for x in items}):
  if probe_rows is not None and row not in probe_rows:continue
  tr=[i for i,x in enumerate(items) if x['feature']==row and x['split']=='dev' and x.get('label') in (0,1)]
  te=[i for i,x in enumerate(items) if x['feature']==row and x['split']=='test' and x.get('label') in (0,1)]
  if not tr or not te:continue
  y=np.array([items[i]['label'] for i in tr]);require(set(y)=={0,1},'both dev classes')
  model=fit_logreg(torch.from_numpy(acts[tr].copy()),torch.tensor(y));v=model.decision(torch.from_numpy(acts[te].copy())).numpy()
  scores.extend({'id':items[i]['id'],'feature':row,'score':float(s)} for i,s in zip(te,v))
  for split,ix in [('dev',tr),('test',te)]:
   for value in (0,1):
    selected=[i for i in ix if items[i]['label']==value];require(selected,'class nonempty')
    means[f'{row}__{split}__'+('A' if value else 'B')]=acts[selected].mean(axis=0,dtype=np.float64).astype(np.float32)
 return scores,means

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec)
 job=HERE.parents[1]/s['experiment'].lower()/'job'
 require(sha(a.spec)==read(job/'ANALYSIS_COMMAND.json')['spec_sha256'],'CPU spec pin');verify(job,'SOURCE_SEAL.json',s['source_seal_sha256'])
 for path,digest in read(job/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'CPU dependency')
 require(sha(s['private_items'])==s['private_items_sha256'],'private bank identity');private={x['id']:x for x in read(s['private_items'])}
 receipt=read(s['capture_receipt']);require(receipt['verified'] is True,'verified capture pull')
 for slot,path in enumerate(s['outputs']):
  root=Path(path);r=receipt['slots'][str(slot)];cap=root/'capture';o=verify(cap,'CAPTURE_SEAL.json',r['capture_seal_sha256'])
  require(o['source_seal_sha256']==s['source_seal_sha256'] and o['input_seal_sha256']==s['input_seal_sha256'] and o['pod_id']==r['pod_id'],'capture source/input/custody identity')
  order=read(cap/'items.order.json');items=[private[k] for k in order];acts=np.load(cap/'acts44.npy')
  require(acts.shape==(len(items),5120) and np.isfinite(acts).all(),'capture grid')
  out=Path(s['cpu_outputs'][str(slot)]);out.mkdir(parents=True,exist_ok=False)
  probe_rows=None if s['experiment']=='E56' else {row for row,v in read(Path(s['inputs'])/'RUN_PLAN.json')['rows'].items() if v['probe_applicable']}
  scores,means=compute(items,acts,probe_rows);dump(out/'PROBE.json',scores);np.savez(out/'CLASS_MEANS.npz',**means)
  seal(out,'CPU_SEAL.json',{'capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json'),'private_items_sha256':s['private_items_sha256'],'source_seal_sha256':s['source_seal_sha256'],'device':'cpu','fit_split':'dev','mean_splits':['dev','test']})
if __name__=='__main__':main()
