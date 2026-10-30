"""E114 input-only transformation of sealed E57 items; no outcomes or model calls."""
import collections,datetime,hashlib,io,json,re,tarfile,tokenize
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'e57'
ROWS=('nesting_depth','indent_level','page_range_digit')
E57_SEAL='cff66637fedd6afd795370e3efbe3e8262d77c98a64e60e8580a9507dd295f7c'
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False);f.write('\n')
def number(item):
 """Same frozen E57 lexical checks, applied only to the unmodified source prefix."""
 require(item['feature'] in ROWS and item['split']=='test','Only specified E57 test items')
 row=item['feature'];text=item['text'];v=item['value']
 if row=='nesting_depth':
  depth=0
  try:
   for t in tokenize.generate_tokens(io.StringIO(text).readline):
    if t.type==tokenize.OP:
     if t.string in '([{':depth+=1
     elif t.string in ')]}':depth-=1
  except tokenize.TokenError as e:
   if 'EOF in multi-line statement' not in str(e):raise
  require(text.endswith(',') and depth in (1,3) and v=={1:'one',3:'three'}[depth],'Frozen executable nesting label')
  n=depth
 elif row=='indent_level':
  line=text.rsplit('\n',1)[-1];n=len(line)-len(line.lstrip(' '))
  require(line.strip()=='pass' and n in (4,12) and v=={4:'four',12:'twelve'}[n],'Frozen final-line indentation label')
 else:
  m=re.search(r'Current citation: pp\. ([1-9])[0-9]{2}–$',text);require(m is not None,'Frozen current citation read boundary')
  n=int(m[1]);require((n in (1,2,3,4) and v=='A') or (n in (6,7,8,9) and v=='B'),'Actual current hundreds digit vs frozen family')
 require(item['variant'] in (0,1) and item['label']==1-item['variant'],'Frozen A/B numerical label')
 return n

def variants(item,other,templates):
 n=number(item);opposite=number(other)
 require(all(item[k]==other[k] for k in ['feature','template_index','filler_index','split']) and item['variant']==1-other['variant'],'Exact source template/filler opposite variant')
 require(item['value']!=other['value'] and n!=opposite,'Opposite frozen state')
 for arm,stated in [('stated',n),('other_value_control',opposite)]:
  sentence=templates[item['feature']].format(n=stated)
  yield arm,sentence,sentence+'\n'+item['text'],stated

def annotation_for(item,annotations):
 # E57 only writes entries for rows with optional answer metadata.
 if item['feature']=='page_range_digit':require(item['id'] in annotations,'Required frozen page-pair annotation')
 return annotations.get(item['id'],{})

def build():
 from transformers import PreTrainedTokenizerFast
 require(sha(SOURCE/'BANK_SEAL.json')==E57_SEAL,'Pinned E57 input seal')
 m=read(SOURCE/'FREEZE_MANIFEST.json');source=Path(m['bank_directory']);seal=read(SOURCE/'BANK_SEAL.json')
 for n in ['items.PRIVATE.json','ANNOTATIONS.PRIVATE.json','DEFINITIONS.json']:
  require(sha(source/n)==seal['files'][n],'Frozen source member: '+n)
 require(sha(TOK/'tokenizer.json')==TOKENIZER_SHA,'Pinned tokenizer')
 config=read(HERE/'SENTENCES.json');require(set(config['templates'])==set(ROWS),'Exact three rows')
 original=read(source/'items.PRIVATE.json');annotations=read(source/'ANNOTATIONS.PRIVATE.json')
 items=[x for x in original if x['feature'] in ROWS and x['split']=='test'];require(len(items)==252,'Exactly84 test items per row')
 by={(x['feature'],x['template_index'],x['filler_index'],x['variant']):x for x in items};require(len(by)==252,'Unique source pairing')
 out=HERE/'cache/bank_2026-10-29_v1';require(not out.exists(),'Never overwrite bank or partial build')
 with (HERE/'BANK_FREEZE.lock').open('x') as f:json.dump(dict(experiment='E114',output=str(out),source_seal=E57_SEAL),f)
 out.mkdir();tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK/'tokenizer.json'));public=[];private=[];counts=collections.Counter();lengths=[]
 for x in sorted(items,key=lambda x:x['id']):
  oldids=tok.encode(x['text'],add_special_tokens=False);require(oldids==x['ids'],'Exact original E57 token bytes')
  other=by[(x['feature'],x['template_index'],x['filler_index'],1-x['variant'])]
  for arm,sentence,text,stated in variants(x,other,config['templates']):
   ids=tok.encode(text,add_special_tokens=False);require(ids[-1]==oldids[-1],'Registered final read-token identity')
   ident=hashlib.sha256(('E114|'+x['id']+'|'+arm).encode()).hexdigest()[:24]
   public.append(dict(id=ident,prompt=text,input_ids=ids,read_position=len(ids)-1))
   private.append(dict(id=ident,feature=x['feature'],arm=arm,source_id=x['id'],source_opposite_id=other['id'],source_split='test',value=x['value'],label=x['label'],variant=x['variant'],cluster=x['cluster'],original_number=number(x),stated_number=stated,sentence=sentence,original_read_position=len(oldids)-1,original_read_token_id=oldids[-1],source_text_sha256=hashlib.sha256(x['text'].encode()).hexdigest(),source_item=x,source_annotations=annotation_for(x,annotations)))
   counts[x['feature']+'/'+arm+'/'+str(x['label'])]+=1;lengths.append(len(ids))
 require(len(public)==len(private)==len({x['id'] for x in public})==504,'Complete unique two-arm bank')
 require(all(n==42 for n in counts.values()) and len(counts)==12,'84 per row per arm, balanced42/42')
 write(out/'PUBLIC_INPUTS.json',public);write(out/'TARGETS.PRIVATE.json',private)
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz') as t:t.add(out/'PUBLIC_INPUTS.json',arcname='PUBLIC_INPUTS.json')
 report=dict(experiment='E114',status='INPUT_BANK_FROZEN',source_experiment='E57',source_bank_seal_sha256=E57_SEAL,source_directory=str(source),source_members_sha256={n:sha(source/n) for n in ['items.PRIVATE.json','ANNOTATIONS.PRIVATE.json','DEFINITIONS.json']},sentence_sha256=sha(HERE/'SENTENCES.json'),source_test_items=252,transformed_items=504,rows=list(ROWS),arms=config['arms'],counts=dict(sorted(counts.items())),dev_items=0,original_source_items_changed=False,original_state_labels_flipped=False,read_token_identity='PASS all504 last token IDs identical to original E57 registered token',chat_wrapping=False,frame=config['frame'],min_input_tokens=min(lengths),max_input_tokens=max(lengths),tokenizer_sha256=TOKENIZER_SHA,model_revision=TOK.name,cache_directory=str(out.resolve()),files={p.name:sha(p) for p in out.iterdir()},first_output_utc='unknown',first_output_reason='CPU-only item transformation; no capture/reader/judge outputs exist',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 write(HERE/'MANIFEST.json',report)
 print(json.dumps(dict(status='FROZEN',items=504,rows=3,source_test_items=252,counts=report['counts'],max_tokens=max(lengths))))
if __name__=='__main__':build()
