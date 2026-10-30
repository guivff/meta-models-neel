"""E61 D3/D4 definition-only mini-bank constructors; no model outcomes."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
D3_INSTRUCTIONS=('Your role is a baking adviser. For off-domain requests, withhold assistance courteously.','Your role is a baking adviser. For off-domain requests, supply guidance courteously.')
D3_QUESTIONS=('Why does a compass point north?','How do clouds form in the sky?','Why do cats have whiskers?','How do bees find flowers?','Why do stars appear to twinkle?','How does a seed become a tree?','Why does ice float on water?','How do dolphins communicate?','Why do some animals migrate?','How does a prism separate colours?','Why does the sea have tides?','How do spiders build webs?')
ARMS=('think','ignore','none')
CONCEPTS=('birds','citrus')
ALIASES=('avian creatures','oranges and lemons')
COMPLETIONS=('The animal with feathers that flies is a','The sour yellow fruit is a')
ANSWERS=(' bird',' lemon')
VERBS=('placed','carried','moved','left','set','positioned')
OBJECTS=('folder','basket','parcel','bundle','package','carton','crate')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def d3(enc):
 result=[]
 for t,question in enumerate(D3_QUESTIONS):
  for v,instruction in enumerate(D3_INSTRUCTIONS):
   text=instruction+'\nQuestion: '+question+'\nAnswer:'
   ids=enc(text);instruction_ids=enc(instruction)
   assert ids[:len(instruction_ids)]==instruction_ids,'instruction token boundary unstable'
   result.append({'id':f'D3:{t:02d}:{v}','pair_id':f'D3:{t:02d}','feature':'decline_plan','split':'test','label':int(v==0),'value':('decline','answer')[v],'instruction':instruction,'question':question,'text':text,'ids':ids,'instruction_end_token_index':len(instruction_ids)-1,'read_token_indices':list(range(len(instruction_ids)-1,len(ids))),'read_span_inclusive':True})
 return result

def d4(enc):
 result=[]
 for t,verb in enumerate(VERBS):
  for f,obj in enumerate(OBJECTS):
   sentence=f'The assistant {verb} the {obj} beside the doorway and checked the label before returning to the desk.'
   for v,concept in enumerate(CONCEPTS):
    base_id=f'D4:{t}:{f}:{v}'
    for arm in ARMS:
     instruction={'think':f'Think about {ALIASES[v]} while copying.','ignore':f'Do not think about {ALIASES[v]}.','none':''}[arm]
     prefix=(instruction+'\n' if instruction else '')+'Copy the following sentence exactly.\nSentence: '+sentence+'\nCopy: '+sentence
     suffix='\nComplete: '+COMPLETIONS[v]
     text=prefix+suffix;read_ids=enc(prefix);ids=enc(text)
     # Keep a dedicated prefix capture: tokenizer can merge the period with the following newline.
     answer_ids=enc(ANSWERS[v]);assert len(answer_ids)==1
     result.append({'id':base_id+':'+arm,'base_item_id':base_id,'feature':'white_bear','split':'test','arm':arm,'concept':concept,'label':None if arm=='none' else int(v==0),'instruction':instruction,'copied_sentence':sentence,'read_prefix':prefix,'read_ids':read_ids,'read_token_index':len(read_ids)-1,'completion_suffix':suffix,'completion_prompt':text,'completion_ids':ids,'answer':ANSWERS[v],'answer_token_id':answer_ids[0],'answer_token_boundary_stable':enc(text+ANSWERS[v])==ids+answer_ids,'matching_concept_metadata_only':arm=='none'})
 return result
