"""CPU-only, outcome-blind §79 prefix pool and exact-position matched samples."""
from __future__ import annotations
import argparse,bisect,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from . import features as F
from .corpus import CACHE,OUT,ROOT,SEED,canonical,digest,rank,rows,save,jsonl,sha

TOKENIZER=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json'
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
EDGES=(0,32,64,128,256,512)
POOL_PER_DOC=16;MAX_PER_DOC=3;TARGET=150;FLOOR=100

def position_bin(pos):
 if not isinstance(pos,int) or not 0<=pos<512:raise ValueError('position outside frozen512token window')
 return bisect.bisect_right(EDGES,pos)-1

def prefix_pool(doc,tok):
 ids=tok.encode(doc['text'],add_special_tokens=False).ids[:512]
 by={b:sorted([i for i in range(len(ids)) if position_bin(i)==b],key=lambda i:rank('prefix',doc['id'],i)) for b in range(5)}
 selected=[];documents={'id':doc['id'],'ids':ids}
 order=sorted(range(5),key=lambda b:rank('bins',doc['id'],b))
 while len(selected)<POOL_PER_DOC:
  found=False
  for b in order:
   while by[b]:
    i=by[b].pop(0);prefix=tok.decode(ids[:i+1],skip_special_tokens=False)
    if '\ufffd' in prefix or tok.encode(prefix,add_special_tokens=False).ids!=ids[:i+1]:continue
    selected.append({'id':doc['id']+':'+str(i),'document_id':doc['id'],'source_group_id':doc['group_id'],'domain':doc['domain'],'family':doc['source'].get('repo') or doc['source']['bank'],'position':i,'position_bin':b,'prefix_sha256':digest(prefix),'text':prefix});found=True;break
   if len(selected)==POOL_PER_DOC:break
  if not found:break
 return documents,sorted(selected,key=lambda x:x['position'])


def select_feature(feature,pool,values,target=TARGET,floor=FLOOR):
 if len(pool)!=len(values):raise ValueError('pool/label shape')
 if len({r['id'] for r in pool})!=len(pool):raise ValueError('duplicate prefix ID')
 for r,v in zip(pool,values):
  if r['domain'] not in F.DOMAINS or r['position_bin']!=position_bin(r['position']) or not r['family']:raise ValueError('invalid position/domain/family')
  if v is not None and v not in (-1,0,1):raise ValueError('nonbinary feature value')
 strata=defaultdict(lambda:{False:[],True:[]});eligible=Counter();counts=Counter();pairs=[]
 for i,(row,value) in enumerate(zip(pool,values)):
  if value is None or value==-1:continue
  value=bool(value);eligible[value]+=1
  key=(row['domain'],row['family'],row['position_bin'],row['position']);strata[key][value].append(i)
 for key in strata:
  for value in [False,True]:strata[key][value].sort(key=lambda i:rank(feature,pool[i]['id']))
 ordered=sorted(strata,key=lambda k:rank('stratum',feature,k))
 while len(pairs)<target:
  progress=False
  for key in ordered:
   cell=strata[key];chosen=None
   for p in cell[True]:
    if counts[pool[p]['document_id']]>=MAX_PER_DOC:continue
    n=next((n for n in cell[False] if counts[pool[n]['document_id']]<MAX_PER_DOC and pool[p]['source_group_id']!=pool[n]['source_group_id']),None)
    if n is not None:chosen=(p,n);break
   if chosen is None:continue
   p,n=chosen;cell[True].remove(p);cell[False].remove(n);counts[pool[p]['document_id']]+=1;counts[pool[n]['document_id']]+=1;pairs.append((p,n));progress=True
   if len(pairs)==target:break
  if not progress:break
 status='RETAINED' if len(pairs)>=floor else 'DROPPED'
 report={'feature':feature,'status':status,'eligible_positive':eligible[True],'eligible_negative':eligible[False],'matched_per_side':len(pairs),'target_per_side':target,'floor_per_side':floor,'undersized':floor<=len(pairs)<target,'drop_reason':None if status=='RETAINED' else 'Fewer than100 exact-domain/source-family/absolute-position matched opposite-label pairs under doc≤3 cap','observed_max_per_document':max(counts.values(),default=0)}
 if status=='DROPPED':return [],report
 return pairs,report


def prepare(tokenizer=TOKENIZER):
 from tokenizers import Tokenizer
 tokenizer=Path(tokenizer)
 if sha(tokenizer)!=TOKENIZER_SHA:raise ValueError('wrong pinned Qwen tokenizer')
 manifest=json.loads((OUT/'CORPUS_MANIFEST.json').read_text());corpus=ROOT/manifest['corpus_path']
 if sha(corpus)!=manifest['corpus_sha256']:raise ValueError('changed frozen corpus')
 docs=rows(corpus);tok=Tokenizer.from_file(str(tokenizer));documents=[];pool=[];labels=[]
 for d in docs:
  tokenized,rr=prefix_pool(d,tok);documents.append(tokenized)
  for r in rr:
   truth=F.extract(r['text'],r['domain']);labels.append([(-1 if truth[f.id] is None else int(truth[f.id])) for f in F.FEATURES]);pool.append({k:v for k,v in r.items() if k!='text'})
 labels=np.asarray(labels,dtype=np.int8);dest=CACHE/'prepared';dest.mkdir(parents=True,exist_ok=False)
 jsonl(dest/'documents.input.jsonl',documents);jsonl(dest/'pool.DO_NOT_STAGE.jsonl',pool);np.savez_compressed(dest/'labels.DO_NOT_STAGE.npz',labels=labels)
 assignments=[];scores_labels=[];reports=[];chosen=set()
 for column,f in enumerate(F.FEATURES):
  pairs,report=select_feature(f.id,pool,labels[:,column]);report.update(class_label=f.kind,definition=f.definition,w1_overlap=list(f.w1_overlap));reports.append(report)
  for p,n in pairs:
   for i,j in [(p,n),(n,p)]:
    r=pool[i];assignments.append({'feature':f.id,'id':r['id'],'donor_id':pool[j]['id']});scores_labels.append({'feature':f.id,'id':r['id'],'value':int(labels[i,column]),'document_id':r['document_id'],'source_group_id':r['source_group_id'],'domain':r['domain'],'family':r['family'],'position_bin':r['position_bin'],'position':r['position']});chosen.add(i)
 assignments.sort(key=lambda x:rank('assignment',x['feature'],x['id']))
 jsonl(dest/'assignments.input.jsonl',assignments);jsonl(dest/'labels.selected.DO_NOT_STAGE.jsonl',scores_labels)
 jsonl(dest/'positions.input.jsonl',[{k:r[k] for k in ['id','document_id','position','prefix_sha256']} for i,r in enumerate(pool) if i in chosen])
 save(dest/'features.input.json',{'feature_order':[f.id for f in F.FEATURES],'registry':F.registry(),'templates':{f.id:[list(f.phrasing_pair)] for f in F.FEATURES},'score_orientation':'vendored paired_logodds: positive statement logprob minus negative statement logprob; no sign flipping after labels'})
 save(OUT/'FEATURE_REGISTRY.json',F.registry());save(OUT/'ELIGIBILITY.json',{'pool_positions':len(pool),'selected_capture_positions':len(chosen),'candidate_pool_per_document':POOL_PER_DOC,'features':reports,'retained':sum(r['status']=='RETAINED' for r in reports),'dropped':sum(r['status']=='DROPPED' for r in reports),'sampling':'exact domain/source family/token index; same source groups never paired; doc≤3 per feature; greedy deterministic hash order','length_matching':'every retained pair has identical prefix token length: KS=1, mean difference=0'} )
 inputs=['documents.input.jsonl','positions.input.jsonl','assignments.input.jsonl','features.input.json'];metadata={'corpus_manifest_sha256':sha(OUT/'CORPUS_MANIFEST.json'),'tokenizer_revision':'6a9e13bd6fc8f0983b9b99948120bc37f49c13e9','tokenizer_sha256':TOKENIZER_SHA,'feature_code_sha256':sha(Path(F.__file__)),'private_label_files':{n:sha(dest/n) for n in ['pool.DO_NOT_STAGE.jsonl','labels.DO_NOT_STAGE.npz','labels.selected.DO_NOT_STAGE.jsonl']},'seed':SEED,'position_bins':list(EDGES),'files':{n:sha(dest/n) for n in inputs}}
 save(dest/'INPUT_SEAL.json',metadata);save(OUT/'INPUT_RECEIPT.json',dict(metadata,prepared_path=str(dest.relative_to(ROOT)),input_seal_sha256=sha(dest/'INPUT_SEAL.json')))
 print(canonical({'features':len(F.FEATURES),'retained':sum(r['status']=='RETAINED' for r in reports),'pool':len(pool),'capture_positions':len(chosen)}));return metadata

def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,default=TOKENIZER);a=p.parse_args();prepare(a.tokenizer)
if __name__=='__main__':main()
