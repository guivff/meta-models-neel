"""Frozen CPU-only E110 belief gate and same-composition matching; never run readers."""
import argparse,collections,hashlib,json,random,re
from pathlib import Path
from source110 import HERE,SEED,aliases,norm,require,read,write,sha

class EntityIndex:
 def __init__(self,entries):
  aliases_to_ids=collections.defaultdict(set);self.labels={};self.names=collections.defaultdict(set)
  for qid,label,names in entries:
   self.labels.setdefault(qid,label);self.names[qid].update(names)
   for name in names:
    key=norm(name)
    if key and key not in {'a','an','the','i','you','he','she','it','we','they','yes','no','none','unknown'}:aliases_to_ids[key].add(qid)
  self.first=collections.defaultdict(list)
  for name,qids in aliases_to_ids.items():
   key=re.match(r'\w+',name)
   if key:self.first[key[0]].append((name,qids))
  for key in self.first:self.first[key].sort(key=lambda z:(-len(z[0]),z[0]))
 def match(self,text,truncated=False):
  """Longest source alias at the answer head, with a word boundary; ties stay unknown."""
  text=norm(text);key=re.match(r'\w+',text)
  if not key:return None
  if truncated and any(alias.startswith(text) and len(alias)>len(text) for alias,_ in self.first.get(key[0],[])):return None
  for alias,ids in self.first.get(key[0],[]):
   if text.startswith(alias) and (len(text)==len(alias) or not text[len(alias)].isalnum()):
    return next(iter(ids)) if len(ids)==1 else None
  return None

def build_index(rows):
 entries=[]
 for x in rows:
  for e in ('e2','e3'):
   if re.fullmatch(r'Q\d+',x[e+'.wikidata_qid']):entries.append((x[e+'.wikidata_qid'],x[e+'.value'],aliases(x[e+'.aliases'],x[e+'.value'])))
 return EntityIndex(entries)

def classify(item,outputs,index):
 def identify(j):
  r=outputs[j];return index.match(r['raw'],r.get('finish_reason')=='length')
 belief=[identify(j) for j in item['onehop_job_ids']]
 answer=identify(item['twohop_job_id'])
 native=belief[0];stable=native is not None and all(x==native for x in belief)
 wrong=native is not None and native!=item['e2_qid'] and answer is not None and answer!=item['e3_qid']
 right=native==item['e2_qid'] and answer==item['e3_qid']
 return dict(candidate_id=item['id'],composition_type=item['composition_type'],native_belief_qid=native,paraphrase_belief_qids=belief,answer_qid=answer,stable_belief=stable,native_belief_wrong=wrong,stable_belief_wrong=wrong and stable,belief_right=right,twohop_tokens=item['twohop_tokens'])

def choose(classified):
 stable=[x for x in classified if x['stable_belief_wrong']];native=[x for x in classified if x['native_belief_wrong']]
 if len(stable)>=60:wrong=stable;gate='three_prompt_belief_stability'
 elif len(native)>=60:wrong=native;gate='no paraphrase gate'
 else:return dict(status='NOT_RUN',gate='fewer_than_60_native_belief_wrong',stable_wrong=len(stable),native_wrong=len(native),wrong=[],right=[],pairs=[],unmatched_wrong=[])
 rights=collections.defaultdict(list)
 for x in classified:
  if x['belief_right']:rights[x['composition_type']].append(x)
 rng=random.Random(SEED);wrong=sorted(wrong,key=lambda x:x['candidate_id']);rng.shuffle(wrong);pairs=[];selected_right=[];unmatched=[]
 for x in wrong:
  pool=rights[x['composition_type']]
  if not pool:unmatched.append(x['candidate_id']);continue
  # Exact composition type first, then nearest native two-hop token length; no new length gate.
  y=min(pool,key=lambda y:(abs(y['twohop_tokens']-x['twohop_tokens']),y['candidate_id']));pool.remove(y);selected_right.append(y)
  pairs.append(dict(wrong_id=x['candidate_id'],right_id=y['candidate_id'],composition_type=x['composition_type'],token_length_difference=y['twohop_tokens']-x['twohop_tokens']))
 return dict(status='READY',gate=gate,stable_wrong=len(stable),native_wrong=len(native),wrong=sorted(x['candidate_id'] for x in wrong),right=sorted(x['candidate_id'] for x in selected_right),pairs=pairs,unmatched_wrong=sorted(unmatched))

def run(receipt_path,out):
 from source110 import load_rows
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 guard=HERE/'cache/FILTER_SELECTION_ONCE.json'
 with guard.open('x') as lock:json.dump(dict(experiment='E110',output=str(out.resolve()),receipt_sha256=sha(receipt_path)),lock)
 write(out/'ATTEMPT.json',dict(experiment='E110',filter_receipt_sha256=sha(receipt_path)))
 receipt=read(receipt_path);require(receipt['verified'] is True and receipt['experiment']=='E110','Verified integrator filter pull required')
 bank=read(HERE/'BANK_SEAL.json')
 for name,h in bank['files'].items():require(sha(HERE/name)==h,'Frozen source changed: '+name)
 require(receipt.get('model_revision')=='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9','Pinned Qwen revision')
 require(receipt.get('decoding')==dict(do_sample=False,max_new_tokens=16,no_CoT=True),'Frozen greedy decoding')
 require(type(receipt.get('filter_gpu_seconds_total')) in (int,float) and 0<=receipt['filter_gpu_seconds_total']<=1800,'Filter half-GPU-hour cap')
 require(receipt['input_seal_sha256']==sha(HERE/'BANK_SEAL.json'),'Exact frozen E110 bank')
 manifest=read(HERE/'MANIFEST.json');cache=Path(manifest['cache_directory'])
 for name,h in manifest['cache_files'].items():require(sha(cache/name)==h,'Frozen member changed: '+name)
 f=Path(receipt['filter_outputs']);require(sha(f)==receipt['filter_outputs_sha256'],'Filter output hash')
 data=read(f);outputs={r['id']:r for r in data};jobs=read(cache/'PUBLIC_FILTER_INPUTS.json');require(len(outputs)==len(data)==len(jobs) and set(outputs)=={x['id'] for x in jobs},'Complete unique exact greedy filter grid')
 for r in data:
  require(isinstance(r['raw'],str),'Raw unmodified completion text required')
  require(isinstance(r.get('token_ids'),list) and len(r['token_ids'])<=16 and all(type(t)is int and t>=0 for t in r['token_ids']),'Original generated token IDs within16-token budget')
  require(r.get('finish_reason') in ('eos','length','stop'),'Original termination metadata required')
 rows=load_rows(Path(manifest['source_csv']));index=build_index(rows);items=read(cache/'ITEMS.PRIVATE.json')
 classified=[classify(x,outputs,index) for x in items];selection=choose(classified)
 by_id={x['id']:x for x in items};all_selected=set(selection['wrong']+selection['right']);public=[];targets=[]
 job_by={x['id']:x for x in jobs};codes={x['candidate_id']:x for x in classified}
 for ident in sorted(all_selected):
  x=by_id[ident];c=codes[ident];job=job_by[x['twohop_job_id']]
  public.append(dict(id=ident,prompt=job['prompt'],input_ids=job['input_ids'],read_position=job['read_position']))
  targets.append(dict(id=ident,composition_type=x['composition_type'],source_uid=x['source_uid'],cohort='belief_wrong' if ident in selection['wrong'] else 'belief_right',belief_qid=c['native_belief_qid'],belief=index.labels[c['native_belief_qid']],belief_aliases=sorted(index.names[c['native_belief_qid']]),belief_raw_native=outputs[x['onehop_job_ids'][0]]['raw'],truth_qid=x['e2_qid'],truth=x['e2'],truth_aliases=x['e2_aliases'],belief_stable=c['stable_belief']))
 write(out/'SELECTION.PRIVATE.json',selection);write(out/'DIAGNOSTICS.PRIVATE.json',classified);write(out/'TARGETS.PRIVATE.json',targets);write(out/'PUBLIC_READER_INPUTS.json',public)
 counts=dict(status=selection['status'],gate=selection['gate'],stable_wrong=selection['stable_wrong'],native_wrong=selection['native_wrong'],selected_wrong=len(selection['wrong']),matched_right=len(selection['right']),unmatched_wrong=len(selection['unmatched_wrong']),target_150_met=len(selection['wrong'])>=150,unknown_native_belief=sum(x['native_belief_qid'] is None for x in classified),unknown_twohop_answer=sum(x['answer_qid'] is None for x in classified),total_candidates=len(items))
 write(out/'COUNTS.json',counts);write(out/'SELECTION_SEAL.json',dict(experiment='E110',status='COMPLETE_ONCE',input_seal_sha256=sha(HERE/'BANK_SEAL.json'),filter_receipt_sha256=sha(receipt_path),files={p.name:sha(p) for p in out.iterdir() if p.is_file()}));print(json.dumps(counts,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.receipt,a.out)
