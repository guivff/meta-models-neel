"""CPU-only bank builder for §223 deviation1 / clarification1. Refuses overwrite."""
import collections,hashlib,random,tarfile
from pathlib import Path
from transformers import PreTrainedTokenizerFast
from source110 import HERE,SEED,REVISION,REPO,CSV_SHA,sha,read,write,require,load_rows,valid_row,freeze_templates,aliases
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')

def quotas(capacity,n):
 q={k:0 for k in sorted(capacity)}
 while sum(q.values())<min(n,sum(capacity.values())):
  for k in q:
   if q[k]<capacity[k] and sum(q.values())<n:q[k]+=1
 return q

def sample_rows(rows,n=3000):
 groups=collections.defaultdict(list);rejected=collections.Counter()
 for x in rows:
  try:ok,reason=valid_row(x)
  except (ValueError,SyntaxError,TypeError):ok,reason=False,'malformed_alias_data'
  if ok:groups[x['fact_comp_type']].append(x)
  else:rejected[reason]+=1
 require(len(groups)==52,'Every source composition type represented')
 q=quotas({k:len(v) for k,v in groups.items()},n);rng=random.Random(SEED);out=[]
 for k in sorted(groups):out.extend(rng.sample(sorted(groups[k],key=lambda x:int(x['uid'])),q[k]))
 return sorted(out,key=lambda x:int(x['uid'])),dict(rejected),q,{k:len(v) for k,v in sorted(groups.items())}

def build():
 src=HERE/'cache/twohopfact';rows=load_rows(src/'TwoHopFact.csv');info=read(src/'API_INFO.json')
 require(info['id']==REPO and info['sha']==REVISION and info['gated'] is False and info['private'] is False,'Anonymous pinned public source required')
 require(info['cardData']['license']=='cc-by-4.0','Declared source license')
 require(sha(TOK)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42','Pinned tokenizer')
 templates=freeze_templates(rows);chosen,rejected,allocation,capacity=sample_rows(rows)
 out=HERE/'cache/bank_twohopfact_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False)
 write(HERE/'PARAPHRASE_TEMPLATES.json',dict(experiment='E110',source_revision=REVISION,placeholder='{e1}',types=templates))
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK));jobs={};items=[]
 def add(text):
  ident='j_'+hashlib.sha256(('E110|'+text).encode()).hexdigest()[:24]
  ids=tok.encode(text,add_special_tokens=False);require(ids,'Nonempty prompt')
  record=dict(id=ident,prompt=text,input_ids=ids,read_position=len(ids)-1)
  require(ident not in jobs or jobs[ident]==record,'Opaque hash collision');jobs[ident]=record
  return ident
 for x in chosen:
  native=x['r1(e1).prompt'];paras=[t.format(e1=x['e1.value']) for t in templates[x['fact_comp_type']]['paraphrases']]
  require(len({native,*paras})==3,'Three distinct one-hop surface forms')
  twohop=x['r2(r1(e1)).prompt']
  ident='i_'+hashlib.sha256(('E110|'+REVISION+'|'+x['uid']).encode()).hexdigest()[:24]
  onehopids=[add(p) for p in [native]+paras];twohopid=add(twohop)
  items.append(dict(id=ident,source_uid=x['uid'],source_eid=x['eid'],composition_type=x['fact_comp_type'],source_category=x['category'],e1=x['e1.value'],e1_qid=x['e1.wikidata_qid'],e2=x['e2.value'],e2_qid=x['e2.wikidata_qid'],e2_aliases=aliases(x['e2.aliases'],x['e2.value']),e3=x['e3.value'],e3_qid=x['e3.wikidata_qid'],e3_aliases=aliases(x['e3.aliases'],x['e3.value']),onehop_job_ids=onehopids,twohop_job_id=twohopid,twohop_tokens=len(jobs[twohopid]['input_ids'])))
 require(len(items)==3000 and len({x['id'] for x in items})==3000,'3000 candidates')
 write(out/'PUBLIC_FILTER_INPUTS.json',sorted(jobs.values(),key=lambda j:j['id']));write(out/'ITEMS.PRIVATE.json',items)
 with tarfile.open(out/'PUBLIC_FILTER_INPUTS.tar.gz','w:gz') as t:t.add(out/'PUBLIC_FILTER_INPUTS.json',arcname='PUBLIC_FILTER_INPUTS.json')
 stats=dict(experiment='E110',source_rows=len(rows),source_composition_types=52,sampled_candidates=3000,filter_prompt_slots=12000,unique_filter_prompts=len(jobs),source_QA_exclusions=rejected,valid_capacity_by_type=capacity,sampled_by_type=allocation,template_entries=52,paraphrases_per_type=2,seed=SEED,model_calls=0,reader_outputs_opened=False)
 write(HERE/'BUILD_VALIDATION.json',stats)
 write(HERE/'MANIFEST.json',dict(experiment='E110',status='INPUT_BANK_FROZEN',source_repo=REPO,source_revision=REVISION,source_csv=str((src/'TwoHopFact.csv').resolve()),source_csv_sha256=CSV_SHA,cache_directory=str(out.resolve()),cache_files={p.name:sha(p) for p in out.iterdir() if p.is_file()},tokenizer_sha256=sha(TOK),sampled_candidates=3000,composition_types=52,unique_filter_prompts=len(jobs),filter_prompt_slots=12000,seed=SEED,public_archive=str((out/'PUBLIC_FILTER_INPUTS.tar.gz').resolve())))
 print('3000 candidates /52 types; unique greedy filter prompts:',len(jobs),'(12000 logical slots)')

if __name__=='__main__':build()
