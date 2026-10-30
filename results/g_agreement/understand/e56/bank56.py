"""Complete E56 generation and exact asked twins; E54 bridge is loaded, not rebuilt."""
from dataclasses import asdict,replace
import independent_rows,twin_bases,adjective_row
from common56 import *
QUESTIONS={
 'tense_implicit':('tense_asked','In what tense is this passage written?'),
 'linewrap_implicit':('linewrap_asked','How many characters are on the current line so far?'),
 'language_continuation':('language_report','Which language is this passage in?'),
 'adjective_implicit':('adjective_asked','What part of speech comes next?')}
IMPLICIT=tuple(QUESTIONS)+('anomaly_state',)
E54_SHA='c13d59f5816321a249d673dd65c35490906b64afcc33fe633bcc66d148d53358'

def bridge_records():
 folder=HERE.parent/'e54/cache/bank_2026-10-27_v1';seal=json.loads((folder/'BANK_SEAL.json').read_text())
 if sha(folder/'BANK_SEAL.json')!=E54_SHA:raise ValueError('wrong E54 bridge bank')
 for n,h in seal['files'].items():
  if sha(folder/n)!=h:raise ValueError('E54 seal mismatch')
 return [x for x in json.loads((folder/'items.PRIVATE.json').read_text()) if x['feature']=='reasoning_bridge']

def construct(encode):
 banks={};definitions={};validators={};twins={}
 for module in [twin_bases,independent_rows]:
  for row,spec in module.SPECS.items():
   banks[row]=module.generate(row);definitions[row]=asdict(spec)
   validators[row]=lambda text,module=module,row=row:module.check_label(row,text)
 banks['adjective_implicit']=adjective_row.generate();definitions['adjective_implicit']=asdict(adjective_row.SPEC);validators['adjective_implicit']=adjective_row.check_label
 for row,items in list(banks.items()):
  validate(items,RowSpec(**definitions[row]),validators[row],encode)
  if row in QUESTIONS:
   asked,question=QUESTIONS[row];suffix='\n'+question
   banks[asked]=[replace(x,row_id=asked,text=x.text+suffix) for x in items]
   definitions[asked]={**definitions[row],'row_id':asked,'read_token_rule':'?','twin_of':row}
   def checker(text,suffix=suffix,base_checker=validators[row]):
    if not text.endswith(suffix):raise ValueError('asked question changed')
    return base_checker(text[:-len(suffix)])
   validate(banks[asked],RowSpec(**definitions[asked]),checker,encode)
   for a,b in zip(items,banks[asked]):
    if b.text!=a.text+suffix or a.source_key!=b.source_key or a.value!=b.value:raise ValueError('exact prefix twin mismatch')
   twins[asked]={'implicit_row':row,'appended_span':suffix,'read_position':'final token of question','label_target':'original implicit read position'}
 # §172 content-word separation, on implicit spans (asked question is shared by design).
 adj=banks['adjective_implicit'];vocabulary={}
 for split in ['dev','test']:
  v={label:set().union(*(adjective_row.content_words(x.text) for x in adj if x.split==split and x.value==label)) for label in adjective_row.SPEC.values}
  if v['adjective']&v['noun']:raise ValueError('adjective content overlap across labels')
  vocabulary[split]={k:sorted(z) for k,z in v.items()}
 records=[]
 for row,items in banks.items():
  for x in items:
   d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,cluster=x.template_index,label=int(x.value==definitions[row]['values'][0]),ids=encode(x.text))
   if row in twins:d['implicit_id']=f"{twins[row]['implicit_row']}:{x.template_index}:{x.filler_index}:{x.variant}"
   records.append(d)
 bridge=bridge_records()
 if len(bridge)!=168:raise ValueError('bridge coverage')
 for x in bridge:
  if encode(x['text'])!=x['ids']:raise ValueError('bridge tokenizer mismatch')
 records.extend(bridge)
 definitions['reasoning_bridge']={'row_id':'reasoning_bridge','values':['cat','dog'],'kind':'positive_control','read_token_rule':':','source_E54_seal':E54_SHA,'unchanged':True,'shared_answer_digit':'4'}
 return records,definitions,twins,vocabulary
