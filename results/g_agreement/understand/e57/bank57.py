"""Complete E57 bank; inherited E56 count arms are copied by verified seal."""
from dataclasses import asdict
from collections import Counter
import re
import group_a,group_b,amendment_rows,focus_and_lists as F
from common57 import *
E56_SHA='e733bed854700d0129a7b59ed1e1e6ddf82947add11c2f3e77feb36bfb451112'
FIRST_LETTER_QUESTION='What is the first letter of that number, spelled out?'
ORDER=['multi_token_entity','focus_think','focus_mention','focus_ignore','focus_none','category_switch','capacity_list','antonym_crosslingual','linewrap_implicit','linewrap_asked','count_gradient_first_letter','two_hop_answer','subject_number','clause_pending','nesting_depth','indent_level','loop_direction','page_range_digit','section_header','sentiment_judgement']
CANONICAL={x:x for x in ORDER}
CANONICAL.update({x:'focus_ignore_mention' for x in ORDER if x.startswith('focus_')})
CANONICAL.update({x:'count_gradient' for x in ['linewrap_implicit','linewrap_asked','count_gradient_first_letter']})
UNLABELLED={'focus_none','capacity_list'}

def number_word(n):
 small='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
 tens=['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']
 if not 0<=n<100:raise ValueError('count outside frozen spelling range')
 return small[n] if n<20 else tens[n//10]+('-'+small[n%10] if n%10 else '')

def validate_unlabelled(items,checker,encode):
 expected={(t,f,v) for t in range(12) for f in range(7) for v in range(2)}
 if len(items)!=168 or {x.source_key for x in items}!=expected or len({x.text for x in items})!=168:raise ValueError('unlabelled item grid')
 if Counter(x.split for x in items)!={'dev':84,'test':84}:raise ValueError('unlabelled split balance')
 for x in items:
  if checker(x.text)!='unlabelled':raise ValueError('unlabelled checker')
 for t in range(12):
  for f in range(7):length_match([x for x in items if x.pair_key==(t,f)],encode)

def content_check():
 report={}
 def check(row,a,b):
  a=set(a);b=set(b)
  if a&b:raise ValueError('value-bearing content overlap: '+row+': '+','.join(sorted(a&b)))
  report[row]={'A_value_terms':sorted(a),'B_value_terms':sorted(b),'disjoint':True}
 for split,k in [('dev',0),('test',1)]:
  ts=range(6*k,6*k+6)
  check('subject_number/'+split,group_b.SUBJECT_A[k],group_b.SUBJECT_B[k])
  check('clause_pending/'+split,list(group_b.CLAUSE_A[k])+[group_b.PRED_A[t] for t in ts],list(group_b.CLAUSE_B[k])+[group_b.PRED_B[t] for t in ts])
  check('multi_token_entity/'+split,set(w.lower() for t in ts for w in re.findall(r'[A-Za-z]+',group_a.CLUES[t][0]))-{'the','s'},set(w.lower() for t in ts for w in re.findall(r'[A-Za-z]+',group_a.CLUES[t][1]))-{'the','s'})
  check('category_switch/'+split,F.COLOURS[k],F.NINTH[k])
  check('sentiment_judgement/'+split,[amendment_rows.POS[t] for t in ts],[amendment_rows.NEG[t] for t in ts])
 check('focus/concepts',['birds','avian','creatures'],['citrus','fruits','oranges','lemons'])
 check('antonym/dev',['小'],['短']);check('antonym/test',['微小'],['短暂'])
 check('two_hop/dev',['spins','webs'],['builds','anthills']);check('two_hop/test',['weaves','silk','traps'],['maintains','underground','insect','colonies'])
 report['scope_note']='Only value-bearing content is checked. Fixed instructions, copied sentence, read token, identifiers and syntactic scaffolding are exempt under §173 clarification 1. Numeric, indentation, bracket and markup values are non-lexical; reused E56 count arms retain their existing seal.'
 return report

def inherited_count(encode):
 folder=HERE.parent/'e56/cache/bank_2026-10-27_v1';seal=json.loads((folder/'BANK_SEAL.json').read_text())
 if sha(folder/'BANK_SEAL.json')!=E56_SHA:raise ValueError('E56 seal')
 for n,h in seal['files'].items():
  if sha(folder/n)!=h:raise ValueError('E56 file hash')
 all_items=json.loads((folder/'items.PRIVATE.json').read_text());base=[x for x in all_items if x['feature']=='linewrap_implicit'];report=[x for x in all_items if x['feature']=='linewrap_asked']
 if len(base)!=168 or len(report)!=168:raise ValueError('count source coverage')
 by={x['id']:x for x in base};third=[];annotations={}
 for x in base+report:
  if encode(x['text'])!=x['ids']:raise ValueError('count source tokenizer')
 for x in report:
  original=by[x['implicit_id']];count=len(original['text'].rsplit('\n',1)[-1]);word=number_word(count)
  y=dict(x);y.update(row_id='count_gradient_first_letter',feature='count_gradient_first_letter',id=x['id'].replace('linewrap_asked:','count_gradient_first_letter:'),text=x['text']+'\n'+FIRST_LETTER_QUESTION)
  y['ids']=encode(y['text']);y['report_id']=x['id'];third.append(y)
  annotations[y['id']]={'original_count':count,'spelled_count':word,'expected_letter':word[0],'implicit_id':original['id'],'report_id':x['id']}
 return base+report+third,annotations

def construct(encode):
 records=[];definitions={};annotations={};content=content_check()
 def add(items,spec,checker,extra=None,unlabelled=False):
  if unlabelled:validate_unlabelled(items,checker,encode)
  else:validate(items,spec,checker,encode)
  definitions[spec.row_id]={'spec':asdict(spec),'probe_applicable':not unlabelled,'bow_applicable':not unlabelled,'canonical_row':CANONICAL[spec.row_id]}
  for x in items:
   d=asdict(x);d.update(id=f'{x.row_id}:{x.template_index}:{x.filler_index}:{x.variant}',feature=x.row_id,split=x.split,cluster=x.template_index,label=None if unlabelled else int(x.value==spec.values[0]),ids=encode(x.text));records.append(d)
   if extra:annotations[d['id']]=extra(x)
 for module in [group_a,group_b,amendment_rows]:
  for row,spec in module.SPECS.items():
   extra=(lambda x,module=module,row=row:module.annotations(row,x)) if hasattr(module,'annotations') else None
   add(module.generate(row),spec,lambda s,module=module,row=row:module.check_label(row,s),extra)
 for arm in F.FOCUS_ARMS:
  row='focus_'+arm;unlabelled=arm=='none';spec=RowSpec(row,('unlabelled','unlabelled') if unlabelled else F.FOCUS_VALUES,'content','the')
  def extra(x):return {'comparison_concept':F.FOCUS_VALUES[x.variant],'matched_family':f'{x.template_index}:{x.filler_index}:{x.variant}','concept_probe_target_absent':x.row_id=='focus_none'}
  add(F.focus_items(arm),spec,lambda s,arm=arm:F.check_focus(s,arm),extra,unlabelled)
 add(F.switch_items(),RowSpec('category_switch',('colour','animal'),'content',','),F.check_switch,lambda x:{'preceding_animals':[w.strip() for w in x.text.split(',') if w.strip()][:-1],'last_item':[w.strip() for w in x.text.split(',') if w.strip()][-1]})
 capacity,lists=F.capacity_items(encode)
 add(capacity,RowSpec('capacity_list',('unlabelled','unlabelled'),'content',','),lambda s:F.check_capacity(s,encode),lambda x:{'list_nouns':lists[x.source_key],'count_measure_only':True},True)
 inherited,notes=inherited_count(encode);records.extend(inherited);annotations.update(notes)
 for row in ['linewrap_implicit','linewrap_asked','count_gradient_first_letter']:
  definitions[row]={'values':['short','long'],'probe_applicable':True,'bow_applicable':True,'canonical_row':'count_gradient','E56_seal_sha256':E56_SHA,'original_count_target':True,'reused_exactly':row!='count_gradient_first_letter'}
 if len(records)!=20*168 or set(definitions)!=set(ORDER):raise ValueError('complete condition grid')
 if len({x['id'] for x in records})!=len(records):raise ValueError('duplicate ids')
 # Every paired semantic arm preserves the exact same copied prefix in the none baseline.
 by={x['id']:x for x in records}
 for t in range(12):
  for f in range(7):
   for v in range(2):
    suffix=f'{t}:{f}:{v}';baseline=by['focus_none:'+suffix]['text']
    for arm in ['think','mention','ignore']:
     if not by['focus_'+arm+':'+suffix]['text'].endswith(baseline):raise ValueError('focus copied text changed across instructions')
 return sorted(records,key=lambda x:(ORDER.index(x['feature']),x['template_index'],x['filler_index'],x['variant'])),definitions,annotations,content
