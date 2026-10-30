"""CPU-only E84 clarification1 gates; no private values leave this process."""
from pathlib import Path
import json,hashlib,os,sys,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def auc(y,s):
 y=np.asarray(y);s=np.asarray(s);assert set(y)=={0,1} and np.isfinite(s).all();a=s[y==1];b=s[y==0];return float(((a[:,None]>b)+.5*(a[:,None]==b)).mean())
def disposition(probe,bow):return dict(native_pass=probe>=.90,text_readable=bow>.65,descriptive_only=bow>.65)
def run(capture,public,labels,out):
 import torch
 from mats.probes import fit_logreg
 from sklearn.feature_extraction.text import CountVectorizer
 from sklearn.linear_model import LogisticRegression
 assert sha(labels)=='01daaedce4773536b19006e1f140d52da1fc15589610c91f9921181b6d8efb51'
 seal=json.loads((capture/'CAPTURE_SEAL.json').read_text());assert seal['experiment']=='E84'and seal['status']=='COMPLETE'and seal['items']==300
 for name,digest in seal['files'].items():assert sha(capture/name)==digest
 xs=json.loads(public.read_text());ys={x['id']:x for x in json.loads(labels.read_text())};assert {x['id']for x in xs}==set(ys) and len(ys)==300
 dev=[x for x in xs if x['split']=='dev'];test=[x for x in xs if x['split']=='test'];assert len(dev)==100 and len(test)==200
 assert {ys[x['id']]['source_issue']for x in dev}.isdisjoint({ys[x['id']]['source_issue']for x in test})
 yd=np.array([ys[x['id']]['label']for x in dev]);yt=np.array([ys[x['id']]['label']for x in test]);assert set(yd)==set(yt)=={0,1}
 out.mkdir(exist_ok=False);os.chmod(out,0o700);(out/'ONCE.json').write_text(json.dumps(dict(capture_seal_sha256=sha(capture/'CAPTURE_SEAL.json'),labels_sha256=sha(labels),fit_split='dev',test_used_for_fit=False)))
 torch.set_num_threads(2);torch.manual_seed(20261029);reports={}
 for name,layer in [('oracle',44),('nla',42)]:
  xd=torch.tensor(np.array([np.load(capture/(x['id']+'.npz'),allow_pickle=False)[str(layer)][0]for x in dev]));xt=torch.tensor(np.array([np.load(capture/(x['id']+'.npz'),allow_pickle=False)[str(layer)][0]for x in test]));fit=fit_logreg(xd,torch.tensor(yd),lam=.001,iters=200);score=auc(yt,fit.decision(xt).numpy());reports[name]=dict(layer=layer,test_auroc=score,probe_pass=score>=.90,dev_fit_only=True)
 # Frozen token IDs define the final512 window; decode with exact frozen tokenizer.
 from transformers import AutoTokenizer
 tok=AutoTokenizer.from_pretrained('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',local_files_only=True)
 texts=lambda rows:[tok.decode(x['input_ids'][-512:],skip_special_tokens=False)for x in rows]
 vectorizer=CountVectorizer();xd=vectorizer.fit_transform(texts(dev));xt=vectorizer.transform(texts(test));fit=LogisticRegression(C=1.,max_iter=1000,random_state=20261029).fit(xd,yd);bow=auc(yt,fit.decision_function(xt))
 private=dict(probes=reports,bow_test_auroc=bow,bow_window_tokens=512,descriptive_only=bow>.65,targets_cpu_only=True)
 (out/'GATES.PRIVATE.json').write_text(json.dumps(private,indent=2)+'\n')
 release=dict(experiment='E84',capture_seal_sha256=sha(capture/'CAPTURE_SEAL.json'),test_AUROC_sites=[44,42],labels_cpu_only=True,probe_pass_by_reader={k:v['probe_pass']for k,v in reports.items()},released_ids=[x['id']for x in test],text_readable=bow>.65,descriptive_only=bow>.65,bow_test_auroc=bow,probe_test_auroc={k:v['test_auroc']for k,v in reports.items()},generic_baseline_retained=True)
 (out/'PUBLIC_RELEASE.json').write_text(json.dumps(release,indent=2)+'\n');return release
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ['capture','public','labels','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();run(a.capture,a.public,a.labels,a.out)
