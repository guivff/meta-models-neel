"""E110 deviation2: CPU-only long-tail triple selection and frozen template rendering."""
import collections,hashlib,json,random,re,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
from source110 import SEED,REVISION,CSV_SHA,load_rows,valid_row,aliases,read,write,sha,require
from amendment110 import quarter_ids
MODEL='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots')/MODEL/'tokenizer.json'
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'

def frequencies(rows):
 c=collections.Counter()
 for x in rows:
  # One occurrence per record, across ALL entity positions; aliases share the QID.
  c.update({x[e+'.wikidata_qid'] for e in ('e1','e2','e3')})
 return c

def render(x):
 one=x['r1.template'].format(x['e1.value'])
 two=x['r2.template'].format(x['mu.template'].format(x['e1.value']))
 return one,two[0].upper()+two[1:]

def allocation(capacity,n):
 q={k:0 for k in sorted(capacity)}
 while sum(q.values())<min(n,sum(capacity.values())):
  for k in q:
   if q[k]<capacity[k] and sum(q.values())<n:q[k]+=1
 return q

def sample(rows,n=3000):
 freq=frequencies(rows);groups=collections.defaultdict(list);reject=collections.Counter()
 for x in rows:
  try:ok,reason=valid_row(x)
  except (ValueError,SyntaxError,TypeError):ok,reason=False,'malformed_alias_data'
  if not ok:reject[reason]+=1;continue
  if freq[x['e2.wikidata_qid']]>=10:reject['bridge_at_least10_records_any_entity_position']+=1;continue
  one,two=render(x)
  if (one,two)!=(x['r1(e1).prompt'],x['r2(r1(e1)).prompt']):reject['native_template_render_mismatch']+=1;continue
  groups[x['fact_comp_type']].append(x)
 require(len(groups)==52,'All52 relation types have eligible long-tail triples')
 capacity={k:len(v) for k,v in sorted(groups.items())};q=allocation(capacity,n);require(sum(q.values())==n,'Enough eligible long-tail source triples')
 rng=random.Random(SEED);chosen=[]
 for k in sorted(groups):chosen.extend(rng.sample(sorted(groups[k],key=lambda x:int(x['uid'])),q[k]))
 return sorted(chosen,key=lambda x:int(x['uid'])),freq,dict(reject),capacity,q

def build():
 from transformers import PreTrainedTokenizerFast
 require(not (HERE/'MANIFEST.json').exists(),'Never overwrite frozen input bank')
 require(sha(TOK)==TOKENIZER_SHA,'Pinned tokenizer')
 rows=load_rows(PARENT/'cache/twohopfact/TwoHopFact.csv');chosen,freq,reject,capacity,q=sample(rows)
 original_templates=read(PARENT/'PARAPHRASE_TEMPLATES.json');require(sha(PARENT/'PARAPHRASE_TEMPLATES.json')=='7e77516b71f35bf9a891677946c90ca97656e0c74d56b86568338f3cd656e04c','Exact52x2 frozen paraphrases')
 relation={}
 for x in rows:
  t=x['fact_comp_type'];entry={k:x[k] for k in ['r1.template','r2.template','mu.template']}
  require(t not in relation or relation[t]==entry,'One fixed composition template per type');relation[t]=entry
 write(HERE/'RELATION_TEMPLATES.json',dict(types=relation,render='native one-hop=r1(e1); two-hop=r2(mu(e1)), capitalize initial character only; equals original native source prompt',paraphrase_templates_source_sha256=sha(PARENT/'PARAPHRASE_TEMPLATES.json')))
 # Byte-identical104 paraphrases from the earlier freeze; no new per-item wording.
 with (HERE/'PARAPHRASE_TEMPLATES.json').open('xb') as f:f.write((PARENT/'PARAPHRASE_TEMPLATES.json').read_bytes())
 out=PARENT/'cache/bank_deviation2_obscure_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False)
 with (HERE/'BANK_FREEZE.lock').open('x') as f:json.dump(dict(output=str(out),phase='E110_deviation2'),f)
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK));jobs={};items=[]
 def add(text):
  ident='d2j_'+hashlib.sha256(('E110dev2|'+text).encode()).hexdigest()[:24];ids=tok.encode(text,add_special_tokens=False)
  require(bool(ids),'Nonempty raw prefix');record=dict(id=ident,prompt=text,input_ids=ids,read_position=len(ids)-1)
  require(ident not in jobs or record==jobs[ident],'No job identity collision');jobs[ident]=record;return ident
 for x in chosen:
  native,two=render(x);paras=[s.format(e1=x['e1.value']) for s in original_templates['types'][x['fact_comp_type']]['paraphrases']]
  require(len({native,*paras})==3,'Native and two frozen distinct one-hop phrasings')
  ident='d2i_'+hashlib.sha256(('E110dev2|'+REVISION+'|'+x['uid']).encode()).hexdigest()[:24]
  oneids=[add(s) for s in [native]+paras];twoid=add(two)
  items.append(dict(id=ident,source_uid=x['uid'],source_eid=x['eid'],composition_type=x['fact_comp_type'],source_category=x['category'],e1=x['e1.value'],e1_qid=x['e1.wikidata_qid'],e2=x['e2.value'],e2_qid=x['e2.wikidata_qid'],e2_aliases=aliases(x['e2.aliases'],x['e2.value']),e3=x['e3.value'],e3_qid=x['e3.wikidata_qid'],e3_aliases=aliases(x['e3.aliases'],x['e3.value']),bridge_record_frequency_any_position=freq[x['e2.wikidata_qid']],onehop_job_ids=oneids,twohop_job_id=twoid,twohop_tokens=len(jobs[twoid]['input_ids'])))
 require(len(items)==len({x['id'] for x in items})==3000,'3000 unique source triples')
 write(out/'ITEMS.PRIVATE.json',items);write(out/'PUBLIC_FILTER_INPUTS.json',sorted(jobs.values(),key=lambda x:x['id']))
 write(out/'BRIDGE_FREQUENCIES.PRIVATE.json',dict(sorted(freq.items())))
 with tarfile.open(out/'PUBLIC_FILTER_INPUTS.tar.gz','w:gz') as t:t.add(out/'PUBLIC_FILTER_INPUTS.json',arcname='PUBLIC_FILTER_INPUTS.json')
 quarters=quarter_ids(items);shards=[]
 for number,ids in enumerate(quarters):
  directory=out/f'shard{number}';directory.mkdir();subset=[x for x in items if x['id'] in ids];needed={j for x in subset for j in x['onehop_job_ids']+[x['twohop_job_id']]}
  mapping={j:'d2q_'+hashlib.sha256(f'E110dev2|{number}|{j}'.encode()).hexdigest()[:24] for j in sorted(needed)}
  public=[dict(jobs[j],id=mapping[j]) for j in sorted(needed)]
  write(directory/'PUBLIC_FILTER_INPUTS.json',public)
  write(directory/'CROSSWALK.PRIVATE.json',dict(shard=number,original_candidate_ids=sorted(ids),quarter_items=subset,original_job_to_shard_job=mapping,original_item_source_sha256=sha(out/'ITEMS.PRIVATE.json')))
  with tarfile.open(directory/'PUBLIC_FILTER_INPUTS.tar.gz','w:gz') as t:t.add(directory/'PUBLIC_FILTER_INPUTS.json',arcname='PUBLIC_FILTER_INPUTS.json')
  shards.append(dict(shard=number,candidates=750,jobs=len(public),directory=str(directory.resolve()),files={p.name:sha(p) for p in directory.iterdir()}))
 old=read(PARENT/'cache/bank_twohopfact_2026-10-29_v1/ITEMS.PRIVATE.json');oldids={x['source_uid'] for x in old}
 stats=dict(candidates=3000,relation_types=52,seed=SEED,eligible_capacity_by_type=capacity,selected_by_type=q,source_QA_exclusions=reject,selected_bridge_frequency_min=min(x['bridge_record_frequency_any_position'] for x in items),selected_bridge_frequency_max=max(x['bridge_record_frequency_any_position'] for x in items),selected_frequency_histogram=dict(collections.Counter(str(x['bridge_record_frequency_any_position']) for x in items)),unique_bridge_QIDs=len({x['e2_qid'] for x in items}),earlier_bank_source_record_overlap=sum(x['source_uid'] in oldids for x in items),overlap_policy='Not excluded or selected by earlier outputs; limited types retain source overlap; all filter acquisitions fresh and new-epoch scoped',unique_global_jobs=len(jobs),logical_slots=12000,scoped_quarter_jobs=sum(x['jobs'] for x in shards),old_filter_outputs_used=False,model_calls=0)
 write(HERE/'BUILD_VALIDATION.json',stats)
 write(HERE/'MANIFEST.json',dict(experiment='E110',phase='deviation2_obscure',registration='2e4e5e737',source_repo='soheeyang/TwoHopFact',source_revision=REVISION,source_csv=str((PARENT/'cache/twohopfact/TwoHopFact.csv').resolve()),source_csv_sha256=CSV_SHA,cache_directory=str(out.resolve()),cache_files={p.name:sha(p) for p in out.iterdir() if p.is_file()},shards=shards,candidates=3000,relation_types=52,seed=SEED,tokenizer_sha256=TOKENIZER_SHA,model_revision=MODEL,public_archive=str(out/'PUBLIC_FILTER_INPUTS.tar.gz'),first_output_utc='unknown',first_output_reason='new CPU input bank; no new acquisition or classification output'))
 print(json.dumps(stats,indent=2))
if __name__=='__main__':build()
