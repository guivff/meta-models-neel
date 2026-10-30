"""CPU-only, once-only capture-bound E86 probes; no reader calls or private pod uploads."""
import json,hashlib,os,sys
from pathlib import Path
import numpy as np
import torch
H=Path(__file__).resolve().parent
ROOT=H.parent/'section210_runtime_v1/source'
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from mats.probes import fit_logreg

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def auc(y,s):
 a=s[y==1];b=s[y==0];assert len(a) and len(b) and np.isfinite(s).all()
 return float(((a[:,None]>b[None,:])+.5*(a[:,None]==b[None,:])).mean())
def main():
 os.umask(0o077);pull=read(H/'PULL_VERIFIED.json');assert pull['verified'] and pull['status']=='CAPTURE_ONLY'
 out=H/'terminal_pull/outputs';assert sha(out/'OUTPUT_SEAL.json')==pull['output_seal_sha256']
 seal=read(out/'OUTPUT_SEAL.json')
 for n,d in seal['files'].items():assert sha(out/n)==d
 assert read(H/'terminal_pull/EXIT.json')['code']==0
 cap=out/'capture';cs=read(cap/'CAPTURE_SEAL.json')
 for n,d in cs['files'].items():assert sha(cap/n)==d
 selhome=H.parent/'e86_selected_once';ss=read(selhome/'SELECTION_SEAL.json')
 for n,d in ss['files'].items():assert sha(selhome/n)==d
 assert sha(H/'PUBLIC_SELECTION.json')==sha(selhome/'PUBLIC_SELECTION.json')
 private=read(selhome/'SELECTED.PRIVATE.json');public=read(H/'PUBLIC_SELECTION.json');index=read(cap/'INDEX.json');ix={x['id']:x for x in index}
 assert len(index)==len(private)==len(public)==1201 and set(ix)=={x['capture_public_id'] for x in private}
 dest=H/'cpu_probe_once';dest.mkdir(exist_ok=False)
 write(dest/'ONCE.json',dict(capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),selection_sha256=sha(H/'PUBLIC_SELECTION.json'),controller_sha256=sha(Path(__file__)),reader_outputs_opened=False))
 reports=[];passed={}
 for arm in ('honest','lie','role'):
  rows=[x for x in private if x['subset']=='yn' and x['arm']==arm]
  dev=[x for x in rows if x['split']=='dev'];test=[x for x in rows if x['split']=='test']
  assert {x['id'] for x in dev}.isdisjoint({x['id'] for x in test})
  for layer in (42,44):
   record=dict(subset='yn',arm=arm,layer=layer,dev_n=len(dev),test_n=len(test),status='NOT_EVALUABLE',probe_pass=False)
   if {x['label'] for x in dev}=={0,1} and {x['label'] for x in test}=={0,1}:
    def acts(rr):
     vv=[]
     for x in rr:
      v=np.load(cap/ix[x['capture_public_id']]['files'][str(layer)],allow_pickle=False);assert v.shape==(1,5120) and np.isfinite(v).all();vv.append(v[0])
     return torch.tensor(np.stack(vv).astype(np.float32))
    yd=np.array([x['label'] for x in dev]);yt=np.array([x['label'] for x in test]);xd=acts(dev);xt=acts(test)
    model=fit_logreg(xd,torch.tensor(yd),lam=1e-3,iters=200);ds=model.decision(xd).numpy();ts=model.decision(xt).numpy()
    da=auc(yd,ds);ta=auc(yt,ts);record.update(status='COMPLETE',dev_auroc=da,test_auroc=ta,probe_pass=da>=.9 and ta>=.9)
    np.savez(dest/f'{arm}_{layer}.PRIVATE.npz',w=model.w.numpy(),b=model.b,mu=model.mu.numpy(),sd=model.sd.numpy(),dev_scores=ds,test_scores=ts)
   passed[(arm,layer)]=record['probe_pass'];reports.append(record)
 open_counts={a:{split:sum(x['subset']=='open' and x['arm']==a and x['split']==split for x in private) for split in ['dev','test']} for a in ['honest','lie','role']}
 assert all(v['dev']==0 for v in open_counts.values()),'UNEXPECTED_OPEN_DEV_REQUIRES_REGISTERED_BINARY_CONTRAST'
 # Both reader-site probe gates must pass; public selection already freezes BOW/test eligibility.
 allowed={x['id'] for x in public if x['reader_allowed']}
 released=[x['capture_public_id'] for x in private if x['subset']=='yn' and x['split']=='test' and x['capture_public_id'] in allowed and all(passed[(x['arm'],l)] for l in [42,44])]
 receipt=dict(experiment='E86',capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),selection_sha256=sha(H/'PUBLIC_SELECTION.json'),recipe='existing mats.probes.fit_logreg lam=.001 iters=200 dev-only normalization; dev/test AUROC>=.90 at both sites',groups=reports,open_arms=dict(status='NOT_EVALUABLE_NO_DEV_UNDERPOWERED',counts=open_counts),released_test_items=len(released),reader_outputs_opened=False,private_truth_uploaded=False,BOW_reused_once=True)
 write(dest/'PUBLIC_PROBE_RECEIPT.json',receipt)
 write(dest/'READER_RELEASE.json',dict(capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),selection_sha256=sha(H/'PUBLIC_SELECTION.json'),released_ids=released,cpu_gate_receipt_sha256=sha(dest/'PUBLIC_PROBE_RECEIPT.json'),authorized=True))
 write(dest/'CPU_RECEIPT_SEAL.json',dict(files={p.name:sha(p) for p in dest.iterdir() if p.is_file() and not p.name.endswith('.npz')}))
 print(json.dumps(receipt))
if __name__=='__main__':main()
