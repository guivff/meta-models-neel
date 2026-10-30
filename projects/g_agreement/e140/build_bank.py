"""Section252 CPU input builder, pinned public facts as data only; no model calls."""
import ast,csv,hashlib,json,random,re,tarfile,unicodedata,datetime
from pathlib import Path
from collections import Counter,defaultdict
SEED=20261030
HERE=Path(__file__).parent
SOURCE_REV='59a84cd883f71641a03fb6fa50da92a9603e7845'
SOURCE_SHA='522d3764eba5c297f9fc630073ce5e897eac134e1d04824fed4d5349e605e338'
SOURCE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e110/cache/twohopfact/TwoHopFact.csv')
ASSETS=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e140-assets-v1')
SYSTEM='Answer the factual question with exactly one word. Do not explain.'
WORD=re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*",re.UNICODE)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
def words(x):return set(re.findall(r'[^\W_]+',x.casefold()))
def one_word(x):return bool(WORD.fullmatch(x.strip()))
def strings(x):
 if isinstance(x,str):return [x]
 if isinstance(x,(tuple,list)):return [s for y in x for s in strings(y)]
 raise ValueError('source alias strings/tuples/lists only')
def question_pair(entity,templates):return [q.format(entity=entity)for q in templates]
def eligible(entity,answer,aliases,qs):
 if not one_word(answer)or any(unicodedata.category(c)=='Cc'for c in entity):return False
 if any(len(q.split())>24 for q in qs)or len(set(qs))!=2:return False
 # No canonical answer-word component or one-word registered alias in either
 # complete prompt. No truths, prior outputs or confidence enter selection.
 banned=set().union(*(words(a)for a in [answer]+[a for a in aliases if one_word(a)]))
 return not any(words(SYSTEM+'\n'+q)&banned for q in qs)
def candidates(records,templates):
 lookup={t:(k,s)for k,s in templates.items()for t in s['source_templates']};merged={};stats=Counter()
 for r in records:
  for hop in (1,2):
   native=r[f'r{hop}.template']
   if native not in lookup:continue
   k,s=lookup[native];entity=r[f'e{hop}.value'].strip();answer=r[f'e{hop+1}.value'].strip();raw=r.get(f'e{hop+1}.aliases','')
   try:aliases=strings(ast.literal_eval(raw))if raw else[]
   except (ValueError,SyntaxError,TypeError):stats['bad_alias_data']+=1;continue
   qs=question_pair(entity,s['questions'])
   if not eligible(entity,answer,aliases,qs):stats['one_word_or_length_or_leak_rejected']+=1;continue
   key=(k,entity.casefold());slot=merged.setdefault(key,dict(template_id=k,category=s['category'],entity=entity,answers={},questions=qs))
   slot['answers'].setdefault(answer,[]).append(dict(uid=r['uid'],hop=hop,source_entity_qid=r[f'e{hop}.wikidata_qid'],source_answer_qid=r[f'e{hop+1}.wikidata_qid']))
 pools=defaultdict(list)
 for key,r in sorted(merged.items()):
  if len(r['answers'])!=1:stats['conflicting_source_fact_dropped']+=1;continue
  truth,refs=next(iter(r.pop('answers').items()));r.update(expected_answer=truth,source_refs=refs)
  pools[r['category']].append(r)
 return dict(pools),dict(stats)
def sample(pools):
 if len(pools)<8 or sum(map(len,pools.values()))<600:raise ValueError('NOT BUILT: fewer than8 categories or600 eligible distinct facts')
 rng=random.Random(SEED);cats=sorted(pools);queues={c:list(pools[c])for c in cats}
 for c in cats:rng.shuffle(queues[c])
 selected=[];round_=0
 while len(selected)<600:
  progressed=False
  for c in cats:
   if queues[c]and len(selected)<600:selected.append(queues[c].pop());progressed=True
  if not progressed:raise ValueError('insufficient frozen eligible pool')
  round_+=1
 rng.shuffle(selected)
 return selected

def build(out):
 out=Path(out)
 if out.exists():raise FileExistsError('preserve all previous freezes/partial directories')
 if sha(SOURCE)!=SOURCE_SHA:raise ValueError('pinned read-only public source mismatch')
 if sha(ASSETS/'tokenizer.json')!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'or sha(ASSETS/'chat_template.jinja')!='e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259':raise ValueError('exact pinned tokenizer/chat template')
 templates=json.loads((HERE/'TEMPLATES.json').read_text())
 with SOURCE.open()as f:pools,rejects=candidates(csv.DictReader(f),templates)
 selected=sample(pools)
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(ASSETS/'tokenizer.json'));tok.chat_template=(ASSETS/'chat_template.jinja').read_text()
 public=[];private=[];order=[];seen_questions=set()
 for i,r in enumerate(selected):
  pair=hashlib.sha256(f'E140|{SEED}|{r["template_id"]}|{r["entity"]}'.encode()).hexdigest()[:24];ids=[];rendered=[]
  for member,q in enumerate(r['questions']):
   if q in seen_questions:raise ValueError('duplicate question')
   seen_questions.add(q);id_=hashlib.sha256(f'{pair}|{member}'.encode()).hexdigest()[:24];ids.append(id_)
   text=tok.apply_chat_template([dict(role='system',content=SYSTEM),dict(role='user',content=q)],tokenize=False,add_generation_prompt=True,enable_thinking=False)
   tokens=tok.encode(text,add_special_tokens=False)
   if not tokens or len(tokens)>160:raise ValueError('short complete prompt policy; no truncation')
   public.append(dict(id=id_,pair_id=pair,family='paraphrase',member=member,ids=tokens,read_index=len(tokens)-1,candidate_ids=[]));rendered.append(text)
  row=dict(r,pair_id=pair,generation_order=i,members=ids,rendered_prompts=rendered);private.append(row);order.append(dict(pair_id=pair,generation_order=i,members=ids))
 assert len(public)==1200 and len(private)==600 and len({r['id']for r in public})==1200
 # Producer input validator only; no weights, screen, selector or once guard.
 from .runner import validate_items
 assert validate_items(public,'screen')==600
 pub=out/'public';cpu=out/'cpu_only';pub.mkdir(parents=True);cpu.mkdir()
 write(pub/'items.json',public)
 manifest=dict(experiment='E140',stage='screen',status='COMPLETE',labels_on_pod=False,pairs=600,prompts=1200,seed=SEED,paraphrases=2,max_new_tokens=32,greedy=True,chain_of_thought=False,read_rule='final complete Qwen assistant-generation-prefix token, no truncation',tokenizer_revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',tokenizer_sha256=sha(ASSETS/'tokenizer.json'),chat_template_sha256=sha(ASSETS/'chat_template.jinja'),parser_path='projects/g_agreement/e140/parser.py',parser_sha256=sha(HERE/'parser.py'),parser_policy='first nonempty line; lower(); remove ASCII string.punctuation everywhere; strip exterior whitespace; no other normalization',generation_order='items interleave member0/member1 of seeded pair0, then pair1, etc; CPUfirst84 uses this frozen pair order, never completion latency',source_attribution='Yang et al. (2024), soheeyang/TwoHopFact, CC BY4.0, pinned59a84cd883f71641a03fb6fa50da92a9603e7845; one-hop facts only, new question templates; no source scripts executed')
 write(pub/'MANIFEST.json',manifest);write(pub/'INPUT_SEAL.json',dict(experiment='E140',stage='screen',status='COMPLETE',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()}))
 write(cpu/'PAIRS.PRIVATE.json',private);write(cpu/'SCREEN_ORDER.PRIVATE.json',order)
 source=dict(repo='soheeyang/TwoHopFact',revision=SOURCE_REV,license='CC-BY-4.0',source_csv=str(SOURCE),source_csv_sha256=SOURCE_SHA,anonymous_source_as_verified_in_E110=True,source_scripts_executed=False,source_uses='one-hop factual subjects/objects/aliases only; NO E110 behaviour or reader/probe outputs',source_url=f'https://huggingface.co/datasets/soheeyang/TwoHopFact/tree/{SOURCE_REV}',sampling='seeded round-robin across eight predicate categories after source-only dedup/conflict/word/leak/shortness QA; no model output selection',category_available={c:len(v)for c,v in pools.items()},category_selected=dict(Counter(r['category']for r in private)),source_rejections=rejects)
 write(cpu/'SOURCE_PROVENANCE.json',source);write(cpu/'CPU_INPUT_SEAL.json',dict(experiment='E140',status='COMPLETE',labels_cpu_only=True,files={p.name:sha(p)for p in cpu.iterdir()}))
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz')as t:
  for n in ['items.json','MANIFEST.json','INPUT_SEAL.json']:t.add(pub/n,arcname=n)
 receipt=dict(experiment='E140',status='FROZEN_INPUT_READY',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),authority='section252/930ed5805',seed=SEED,pairs=600,prompts=1200,categories=dict(Counter(r['category']for r in private)),source_provenance=source,public_input_root=str(pub),public_input_sha256=sha(pub/'INPUT_SEAL.json'),public_archive=str(out/'PUBLIC_INPUTS.tar.gz'),public_archive_sha256=sha(out/'PUBLIC_INPUTS.tar.gz'),cpu_root=str(cpu),cpu_input_sha256=sha(cpu/'CPU_INPUT_SEAL.json'),parser_source_sha256=sha(HERE/'parser.py'),question_templates_sha256=sha(HERE/'TEMPLATES.json'),token_count_min=min(len(r['ids'])for r in public),token_count_max=max(len(r['ids'])for r in public),no_answer_word_leakage=True,expected_answers_one_orthographic_word=True,no_model_or_reader_outputs_opened=True,GPU_calls=0,paid_calls=0,operator='I-2 afterE138',runner='W-mechanism-C1287ca0cd',cap_seconds=1800,deadline_UTC='2026-10-30T08:00:00Z',screen='complete600pairs; first84 source-order pairs whose frozen parsed answers nonempty and different; <40 screen-only; no correctness/confidence/single-token filter',stage_labels='X/Y and all truths/source aliases CPU only; public candidate_ids[]',measurement_rule='section252clarification1 c33fcfb40: SAME-pass final-token raw logit[first token of leading-space X] minus Y; shared first token NOT MEASURED, readouts retained; descriptive only')
 write(out/'BANK_MANIFEST.json',receipt)
 print(json.dumps({k:receipt[k]for k in ('status','pairs','categories','public_input_sha256','public_archive_sha256','token_count_min','token_count_max')}))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
