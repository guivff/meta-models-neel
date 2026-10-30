"""Extract sealed E113 directions, not a probe fit or test evaluation."""
from pathlib import Path
import json,hashlib,pickle
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=ROOT.parent
ROWS=('nesting_depth','indent_level','page_range_digit','fact_recall')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def select(meta,row):
 scored=[]
 for layer in range(48,61):
  k=f'{row}__L{layer:02d}__first_generated_token';m=meta[k]
  score=next(x['mean_AUROC'] for x in m['dev_CV'] if x['C']==m['selected_C'])
  scored.append((layer,score))
 return max(scored,key=lambda z:(z[1],-z[0]))[0],scored

def direction(coef,scale):
 v=np.asarray(coef,dtype=np.float64).reshape(-1)/np.asarray(scale,dtype=np.float64)
 assert np.isfinite(v).all() and np.linalg.norm(v)>0
 return v/np.linalg.norm(v)

def run():
 cache=ROOT/'cache/g_agreement/understand/e113/probes226';meta=json.loads((cache/'DEV_SELECTION.json').read_text());fit=json.loads((cache/'FIT_SEAL.json').read_text());assert sha(cache/'DEV_SELECTION.json')==fit['selection_sha256']
 layout=BASE/'outputs/e113-run-v2/split_layout';ls=json.loads((layout/'LAYOUT_SEAL.json').read_text());assert sha(layout/'LAYOUT_SEAL.json')=='6d62779d0f0ba3f58dc12458cb0e7c472a5adc3f5d0e1a13d19316f0598711ff'
 inp=BASE/'outputs/e113-inputs-v1';labels=json.loads((inp/'cpu_only/LABELS.json').read_text());byid={r['id']:r for r in labels};order=json.loads((layout/'ORDER.json').read_text());assert sha(layout/'ORDER.json')==ls['files']['ORDER.json']
 public=json.loads((inp/'inputs/items.json').read_text());iseal=json.loads((inp/'inputs/INPUT_SEAL.json').read_text())
 for n,h in iseal['files'].items():assert sha(inp/'inputs'/n)==h
 carriers=np.load(inp/'inputs/h44.npy',allow_pickle=False);assert carriers.shape==(1008,5120)
 out=BASE/'outputs/e117-inputs-v1';out.mkdir(exist_ok=False)
 dirs=HERE/'directions';dirs.mkdir(exist_ok=False);rng=np.random.default_rng(20261029);manifest={};items=[];hs=[];deltas=[]
 for row in ROWS:
  layer,scores=select(meta,row);key=f'{row}__L{layer:02d}__first_generated_token';mp=cache/'weights'/(key+'.pkl');assert sha(mp)==fit['files'][key]
  model=pickle.loads(mp.read_bytes());sc=model.named_steps['standardscaler'];lr=model.named_steps['logisticregression'];assert lr.classes_.tolist()==[0,1]
  d=direction(lr.coef_,sc.scale_);devp=layout/(row+'_dev.npy');assert sha(devp)==ls['files'][devp.name]
  a=np.load(devp,allow_pickle=False,mmap_mode='r')[:,layer,1,:].astype(np.float64);ys=np.array([byid[x['id']]['label'] for x in order[row+':dev']]);proj=a@d;gap=float(proj[ys==1].mean()-proj[ys==0].mean());assert gap>0
  dp=dirs/(row+'.npy');np.save(dp,d);rand=rng.standard_normal(len(d));rand/=np.linalg.norm(rand)
  manifest[row]=dict(lens_layer=layer,gap=gap,direction_file=str(dp.resolve()),direction_sha256=sha(dp),raw_coefficient_convention='coef/scale, unit norm; class1 positive',selected_C=meta[key]['selected_C'],dev_layer_scores=[dict(layer=l,mean_AUROC=s) for l,s in scores],model_sha256=sha(mp),dev_array_sha256=sha(devp),selection_seal_sha256=sha(cache/'FIT_SEAL.json'))
  for slot,item in enumerate(order[row+':test']):
   ident=item['id'];ix=next(j for j,x in enumerate(public) if x['id']==ident);y=byid[ident]['label'];true=(2*y-1)*gap*d
   hs.append(carriers[ix]);deltas.append(np.stack([true,-true,gap*rand]));items.append(dict(id=ident,row=row,slot=slot))
 np.save(out/'H44.npy',np.asarray(hs,dtype=np.float32));np.save(out/'DELTAS.npy',np.asarray(deltas,dtype=np.float32));(out/'items.json').write_text(json.dumps(items,indent=2)+'\n')
 pub=dict(experiment='E117',direction_source='E113 sealed dev fits; no refit',alphas=[1,2,4],arms=['T','W','R'],rows=manifest,random_seed=20261029,tie_break='lowest layer on exact dev AUROC tie',original_selection_sha256=sha(cache/'DEV_SELECTION.json'),original_fit_seal_sha256=sha(cache/'FIT_SEAL.json'))
 (out/'MANIFEST.json').write_text(json.dumps(pub,indent=2)+'\n');(HERE/'DIRECTIONS.json').write_text(json.dumps(pub,indent=2)+'\n')
 seal=dict(experiment='E117',labels_on_pod=False,files={n:sha(out/n) for n in ['MANIFEST.json','items.json','H44.npy','DELTAS.npy']});(out/'INPUT_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n');(HERE/'PROBE_DELIVERY.json').write_text(json.dumps(dict(root=str(out),input_seal_sha256=sha(out/'INPUT_SEAL.json'),rows=manifest),indent=2)+'\n');print(json.dumps({r:{k:m[k] for k in ['lens_layer','gap','direction_sha256']} for r,m in manifest.items()}))
if __name__=='__main__':run()
