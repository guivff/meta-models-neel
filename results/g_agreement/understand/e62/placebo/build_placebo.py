"""§178 amendment 1: unchanged ladder passages with unrelated cue properties."""
from pathlib import Path
import json,hashlib,re,sys,shutil
from collections import Counter
HERE=Path(__file__).resolve().parent;UNDER=HERE.parents[1]
sys.path.insert(0,str(UNDER/'e49'));from bow_once import score_row
SOURCE=HERE.parent/'cache/bank_2026-10-27_v1';SOURCE_SEAL='f69a4fa6726da61d656b1e7ecf65310bb3c226ee5309e129c2a93c4849647cfd'
PROPS={'S1':'the punctuation count','S2':'the number of commas','S3':'the sentence length','S4':'the paragraph count','S5':'the word length'}
CONDS={'S1':'the original passage contains at least one sentence-punctuation character (period, comma, semicolon, colon, exclamation mark or question mark)','S2':'the original passage contains at least one comma','S3':'the first sentence of the current passage contains at least ten words','S4':'the original passage contains at least two paragraphs separated by a blank line','S5':'the pending subject noun of the original passage contains at least six letters'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def truth(state,text):
 if state=='S1':n=sum(c in '.,;:!?' for c in text);return n,n>=1
 if state=='S2':n=text.count(',');return n,n>=1
 if state=='S3':
  tail=text.split('Current passage:\n',1)[1];sentence=re.split(r'[.!?]',tail)[0];n=len(sentence.split());return n,n>=10
 if state=='S4':n=len([x for x in re.split(r'\n\s*\n',text) if x.strip()]);return n,n>=2
 if state=='S5':
  m=re.match(r'The (\w+)',text);assert m;n=len(m[1]);return n,n>=6
 raise ValueError(state)
def construct(enc):
 assert sha(SOURCE/'BANK_SEAL.json')==SOURCE_SEAL
 seal=json.loads((SOURCE/'BANK_SEAL.json').read_text());assert sha(SOURCE/'items.PRIVATE.json')==seal['files']['items.PRIVATE.json']
 old=json.loads((SOURCE/'items.PRIVATE.json').read_text());by={(x['state'],x['rung'],x['base_item_id']):x for x in old};items=[];private={}
 for base in [x for x in old if x['rung']=='L0']:
  state=base['state'];passage=base['text'];n,is_alpha=truth(state,passage)
  for rung in ('L1','L2','L4'):
   real=by[state,rung,base['base_item_id']]
   if rung=='L1':before='Note: '+PROPS[state]+' matters here.\n';after=''
   elif rung=='L2':before='As you read, keep track of '+PROPS[state]+'.\n';after=''
   else:before="If "+CONDS[state]+", reply 'alpha'; otherwise reply 'beta'.\n";after='\nReply:'
   text=before+passage+after;ids=enc(text)
   x=dict(real,id=real['id'].replace(state+'_'+rung+':',state+'_'+rung+'p:'),feature=state+'_'+rung+'p',rung=rung+'p',text=text,ids=ids,first_content_index=0,read_index=len(ids)-1)
   assert ids[-1]==real['ids'][-1]
   items.append(x);private[x['id']]={'original_readout_label':real['value'],'unrelated_property_count':n,'unrelated_condition_true':is_alpha,'expected_decision':'alpha' if is_alpha else 'beta','real_rung_id':real['id']}
 return items,private,old

def validate(items,private,old,enc):
 assert len(items)==2520 and len({x['id'] for x in items})==2520
 oldby={x['id']:x for x in old};ratios=[]
 for s in PROPS:
  for r in ['L1p','L2p','L4p']:
   rows=[x for x in items if x['state']==s and x['rung']==r];assert len(rows)==168
   for split in ('dev','test'):assert Counter(x['label'] for x in rows if x['split']==split)=={0:42,1:42}
   for t in range(12):
    for f in range(7):
     a,b=[x for x in rows if x['template_index']==t and x['filler_index']==f]
     assert a['ids'][-1]==b['ids'][-1];ratio=max(len(a['ids']),len(b['ids']))/min(len(a['ids']),len(b['ids']));assert ratio<=1.10;ratios.append(ratio)
 for x in items:
  real=oldby[private[x['id']]['real_rung_id']];base=oldby[x['state']+'_L0:'+x['base_item_id']]
  assert base['text'] in x['text']
  for k in ['base_item_id','split','label','value','source_id']:assert x[k]==real[k]
  assert x['ids']==enc(x['text']) and x['ids'][-1]==real['ids'][-1]
  if x['rung']=='L4p':assert enc(' alpha')==[x['alpha_token_id']] and enc(' beta')==[x['beta_token_id']]
 return {'items':2520,'cells':15,'dev_per_cell':84,'test_per_cell':84,'A_B_per_split':42,'max_paired_length_ratio':max(ratios),'same_real_read_token':True,'source_passages_unchanged':True,'source_A_B_labels_unchanged':True}
def freeze(enc):
 out=HERE/'cache/bank_2026-10-27';out.mkdir(parents=True,exist_ok=False)
 items,private,old=construct(enc);v=validate(items,private,old,enc);fits={};metrics={};counts={}
 for state in PROPS:
  for rung in ('L1p','L2p','L4p'):
   cell=state+'_'+rung;fit=score_row([x for x in items if x['feature']==cell]);fits[cell]=fit;metrics[cell]={'test_auroc':fit['test_auroc'],'gate_pass':fit['test_auroc']<=.65}
  counts[state]=dict(Counter(private[x['id']]['expected_decision'] for x in items if x['state']==state and x['rung']=='L4p' and x['split']=='test'))
 for n,x in [('items.PRIVATE.json',items),('DECISIONS.PRIVATE.json',private),('VALIDATION.json',v),('BOW_FITS.PRIVATE.json',fits),('BOW_QA.json',metrics),('DECISION_COUNTS.json',counts),('PLACEBO_DEFINITIONS.json',{'properties':PROPS,'conditions':CONDS})]:dump(out/n,x)
 assert all(x['gate_pass'] for x in metrics.values())
 sources={p.name:sha(p) for p in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,out/n)
 dump(out/'BANK_SEAL.json',{'experiment':'E62 placebo amendment 1','source_E62_seal':SOURCE_SEAL,'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'source_files':sources,'provisional_note_sha256':sha(HERE/'PROVISIONAL_2026-10-27.md'),'BOW_code_sha256':sha(UNDER/'e49/bow_once.py')})
 print('E62 placebo seal',sha(out/'BANK_SEAL.json'));print('Decision counts',counts);print('BOW',metrics)
if __name__=='__main__':
 from transformers import PreTrainedTokenizerFast
 p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');assert sha(p)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
 t=PreTrainedTokenizerFast(tokenizer_file=str(p));freeze(lambda s:t.encode(s,add_special_tokens=False))
