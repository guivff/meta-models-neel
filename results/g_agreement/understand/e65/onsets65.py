"""Construction-only onset rules. No outcomes; None denotes uncertified onset."""
import re,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s)
 import sys;sys.modules[name]=m;s.loader.exec_module(m);return m
CONTENT=load('e65_content_helpers',HERE.parent/'e36/check_content.py')
STRUCT=load('e65_structure_helpers',HERE.parent/'e36/check_structure.py')
COUNT_ROWS={'prose_sentence','prose_words','prose_budget','prose_column','python_line','python_argument','python_depth','python_depth_ordinal','python_indent','latex_section','latex_item','latex_brace','json_field','json_depth','table_column','table_column_ordinal','table_row','list_index','list_depth','list_completed','list_words','linewrap_implicit','linewrap_asked','count_gradient_first_letter','nesting_depth','indent_level','sentence_position','paragraph_index','paragraph_start'}
def first(pattern,text,start=0,flags=0):
 m=re.search(pattern,text[start:],flags);return start+m.end() if m else None

def last(pattern,text,flags=0):
 m=list(re.finditer(pattern,text,flags));return m[-1].end() if m else None

def words(text,vocab,start=0):return first(r'\b(?:'+'|'.join(re.escape(w) for w in sorted(vocab,key=len,reverse=True))+r')\b',text,start,re.I)
def body_start(x):
 text=x['text'];body=x.get('meta',{}).get('body')
 if body and text.endswith(body):return len(text)-len(body)
 return 0

def onset(bank,x):
 f=x['feature'];text=x['text'];start=body_start(x);body=text[start:]
 # Return character END of establishing span, plus auditable rule. Token containing
 # this endpoint is included in duration. Counter bins are handled by bins65 at token boundaries.
 if f in COUNT_ROWS:raise ValueError('Use token-prefix A/B bin tracker for count rows')
 if bank=='E61_D4':return None,'No single binary state shared across think/ignore/none; none has no target'
 if bank in ('E59','E61_D3'):
  p=(text.index('\nQuestion:') if '\nQuestion:' in text else None)
  return p,'End of complete plan instruction, before question'
 if f.startswith('focus_'):
  if f=='focus_none':return None,'No binary concept label in none arm'
  return first(r'\.',text),'End of concept instruction before common copy task'
 if f=='instructed_focus':
  p=text.find('Current instruction: ')
  return first(r'\.',text,p),'End of active concept instruction; archived instruction ignored'
 if f in ('prose_paren','prose_quote'):
  chars='()' if f=='prose_paren' else '"“”'
  matches=[i+1 for i,c in enumerate(body) if c in chars and (not i or body[i-1]!='\\')]
  if f=='prose_paren':
   depth=0;change=None
   for i,c in enumerate(body):
    if c not in '()' or (i and body[i-1]=='\\'):continue
    old=depth>0;depth+=1 if c=='(' else -1
    if (depth>0)!=old:change=i+1
   return (start+change if change else None),'Most recent inside/outside parenthesis transition'
  return (start+matches[-1] if matches else None),'Most recent unescaped quotation boundary'
 if f in ('python_string','python_comment'):
  # Character-wise mode transitions, respecting escapes and comments. Interpolated
  # or malformed literals are rejected by the sealed lexical helper.
  states=[]
  for k in range(1,len(body)+1):
   try:state=STRUCT._python_lex(body[:k])[1]
   except ValueError:state=None
   states.append(state)
  target='string' if f=='python_string' else 'comment'
  end=states[-1]
  if end is None:return None,'Unsupported final Python lexical mode'
  bools=[None if s is None else s==target for s in states]
  current=bools[-1];j=len(bools)-1
  while j>0 and bools[j-1] in (None,current):j-=1
  return start+j+1,'Latest transition of lexical '+target+' membership (comments/escapes respected)'
 if f=='latex_environment':return (lambda p:start+p if p else None)(last(r'\\(?:begin|end)(?:\s|%[^\n]*\n)*\{[^{}]+\}',body)),'End of latest environment boundary'
 if f=='latex_math':return (lambda p:start+p if p else None)(last(r'(?<!\\)\$\$?',body)),'Latest unescaped math delimiter'
 if f=='latex_fraction':return (lambda p:start+p if p else None)(last(r'(?<!\\)\{',body)),'Opening brace of current fraction argument; nested-brace cases require owner review'
 if f=='table_role':
  block=re.split(r'\n[ \t]*\n',body)[-1];off=len(text)-len(block)
  sep=list(re.finditer(r'(?m)^[ |:\-]*---[ |:\-]*\n',block))
  return (off+sep[-1].end()+1 if sep else off+1),'First header token or first data token after separator in current block; same role across rows does not reset' 
 if f in ('list_ordered','list_task'):
  line=body.rsplit('\n',1)[-1];off=len(text)-len(line)
  pat=r'\s*(?:[-+*]|\d+[.)])\s*\[[ xX]\]' if f=='list_task' else r'\s*(?:[-+*]|\d+[.)])'
  return first(pat,text,off),'Current item marker establishes list type/check status'
 if f=='json_type':
  p=last(r':\s*(?:"|[-+]?\d)',body)
  return (start+p if p else None),'First quote or digit after the current JSON field colon'
 if f=='fenced_code':return last(r'(?m)^```[^\n]*(?:\n|$)',text) or 1,'Last fenced-code boundary, or first prompt token when never inside'
 if f=='latex_list':return last(r'\\(?:begin|end)\{(?:itemize|enumerate)\}',text) or 1,'Last LaTeX list boundary, or first prompt token when never inside'
 if f in ('word_first_piece','number_completion'):return None,'Forward-completion label depends on authored suffix; no certified backward onset for opposite-value items'
 # Old-bank semantic content: frozen checker vocabularies, never a judge.
 lex={'prose_topic':CONTENT._GARDEN|CONTENT._OCEAN|{'divers','fish','waves','beach','ships','ship','rake','roses','flowers','trawler','ferry'},'prose_sentiment':CONTENT._POSITIVE|CONTENT._NEGATIVE|{'improvement','deterioration','promising','alarming'},'latex_subject':CONTENT._ALGEBRA|CONTENT._GEOMETRY|{'parallelism'},'list_topic':CONTENT._TRAVEL|CONTENT._STUDY}
 if f in lex:
  if f.startswith('list_'):start=text.rfind('\n')+1
  return words(text,lex[f],start),'First complete value-bearing word from frozen checker vocabulary plus explicit frozen W1 construction cues'
 if f=='python_error':return words(text,{'raise','return'},start),'First raise/return keyword in active function'
 if f=='python_effect':return None,'Mutation/pure-expression onset needs a certified expression-semantic construction tracker'
 if f in ('json_status','table_status'):
  if f=='json_status':p=last(r'"decision"\s*:\s*"',text)
  else:p=text.rfind('|')+1
  return words(text,{'approved','rejected'},p or start),'Current Decision value token'
 if f=='list_priority':return first(r'\b(?:urgent|critical|immediately|emergency|routine|whenever|regular|weekly|eventually|today|leisure|right away|right now|at once|next review|next week|next month|normal schedule|planned rotation|can wait|every week|every month|scheduled maintenance|imminent|without delay|standard task|highest priority|optional housekeeping|no deadline|now|within minutes)\b',text,text.rfind('\n')+1,re.I),'First explicit urgency/routine construction cue in current item'
 if f=='latex_role':return None,'Theorem versus worked example is distributed across a mathematical statement; no certified first value-bearing token'
 if bank=='W12':
  if f=='sentence_type':return first(r'\w+',text,start),'Initial inverted auxiliary versus The fixes frozen question/statement construction'
  if f=='clause_embedding':
   if x['value']=='main':return start+1,'Main-clause bin holds from excerpt start; coordinating and does not reset it'
   return first(r'\b(?:who|whom|whose)\b',text,start),'Relative pronoun opens relative-clause bin'
  return None,'Read-word syntactic role has no registered backward tracking rule before that word'

 if f=='capacity_list':return None,'Count-only list has no binary A/B state'
 if f=='sentiment_judgement':return first(r'My experience was \w+',text),'Review adjective establishes polarity'
 if f=='subject_number':return first(r'The \w+',text),'Complete subject noun fixes singular/plural value'
 if f=='clause_pending':
  start=text.index('Current fragment: ')+len('Current fragment: ')
  return first(r'\w+',text,start),'Current Although/The construction marker fixes pending-clause condition'
 if f=='loop_direction':return last(r'for i in range\([^)]*\):',text),'End of current loop header fixes iteration direction'
 if f=='page_range_digit':return first(r'Current citation: pp\. \d',text),'First digit of current page-range start'
 if f=='section_header':
  p=text.rfind('\n')+1
  return first(r'##',text,p) if text[p:].startswith('##') else first(r'\w+',text,p),'Current line heading marker or prose opener'
 if f=='category_switch':return last(r'\b\w+\b',text),'Ninth list item fixes switched colour/animal value'
 if f=='multi_token_entity':
  p=text.index('answer. ')+len('answer. ') if 'answer. ' in text else 0
  # Exact clue begins after the frozen common scaffolding's last sentence.
  p=text.rfind('carries no information about the answer. ')+len('carries no information about the answer. ')
  return first(r'\w+',text,p),'First value-bearing token of frozen entity clue, following shared scaffold'
 if f=='antonym_crosslingual':return first(r'微小|短暂|小|短',text),'First complete Chinese adjective in current antonym prompt'
 if f=='two_hop_answer':return first(r'spins|builds|weaves|maintains',text),'First distinguishing predicate of frozen animal bridge'
 if f=='reasoning_bridge':
  p=text.rfind('Current question:')
  return words(text,{'purrs','purring','meows','meowing','barks','barking','feline','canine'},max(p,0)),'First animal-identifying cue in current bridge question'
 if f=='injection_awareness':return last(r'(?:USER — own instruction:|TOOL — quoted output:)',text),'Active source header establishes instruction provenance'
 if f in ('tense_implicit','tense_asked'):
  p=text.index('Current passage:\n')+len('Current passage:\n')
  return first(r'\w+\s+\w+\s+\w+',text,p),'First complete finite verb in current passage'
 if f in ('language_continuation','language_report'):
  p=text.index('Current passage:\n')+len('Current passage:\n')
  return first(r'\w+',text,p),'First language-specific word of current passage'
 if f in ('adjective_implicit','adjective_asked'):
  return first(r'The \w+ \w+ \w+',text),'Complete predicate adjective or object noun fixes frozen coordination class'
 if f=='fact_recall':
  p=text.rfind('Current question:')
  return words(text,{'France','Peru','Japan','Italy','Spain','Chile','Norway','Egypt','Kenya','Greece','Cuba','India'},max(p,0)),'Country cue of the current capital-recall question'
 if f=='anomaly_state':return first(r'Vocabulary entries: [^.]+\. (?:La|The)',text),'First word of controlled whole sentence after glossary'
 if f=='rhyme_plan':return first(r'The \w+',text,text.rfind('\n')+1),'First content noun of final couplet line fixes answer under frozen rhyme construction'
 if bank=='E49':
  if f=='unit_system':return first(r'This guide uses (?:metric|imperial)',text),'First unit-system value word'
  if f=='decimal_separator':return last(r'Format note: [^.]+\.',text),'End of final overriding format instruction'
  if f=='instruction_provenance':return last(r"(?:Quoted vendor text:|Principal's instruction:)",text),'Current source attribution header'
  if f=='asserted_vs_hypothetical':
   p=text.index('That passage ends here. ')+len('That passage ends here. ')
   return first(r'(?:It is the case|Suppose)',text,p),'Current assertion/hypothetical marker'
  if f=='negation_scope':
   p=text.index('That claim ends here. ')+len('That claim ends here. ')
   return first(r'It is (?:false|clear)',text,p),'Current negation/affirmation marker'
  if f=='topic_twin':return last(r'\b(?:engineer|gardener)\b',text),'Current engineering/gardening value word'
  if f=='user_expertise':return words(text,{'beginner','new','unfamiliar','expert','advanced','comfortable','experienced','novice','independently','help','fundamentals','confused','familiar','specialist','basic','routinely','struggle','substantial','minimal','principles','learning','know'}),'First explicit expertise cue'
  if f=='container_after_move':return last(r'(?:in|inside|into) the (?:cup|bowl)',text),'Final explicit placement destination fixes tracked object location'
  if f=='holder_after_handovers':return text.index(' The room stays quiet'),'End of final complete handover event fixes tracked holder'
  if f=='chased_role':return first(r'the (?:thief|policeman) chased',text),'Chase subject and verb fix frozen role'
  if f=='pronoun_referent':return first(r'At the meeting, \w+ \w+ \w+',text),'Completed giver/receiver binding in frozen transfer clause'
  if f=='arith_carry':return last(r'\d+\s*\+\s*\d+',text),'Both complete addition operands fix carry'
  if f=='arith_compare':return last(r'\d+\s*[?]',text),'Completed comparison threshold fixes inequality'
  if f=='branch_taken':return last(r'if [^\n]+:',text),'Complete branch condition after assignments fixes branch'
  if f=='next_paragraph_language':
   trimmed=text.rstrip();p=trimmed.rfind('\n\n')+2
   return first(r'\w+',text,p),'First language-specific token of current paragraph fixes opposite next language under alternation instruction'
  if f=='var_type_at_use':return type_onset(text),'Most recent actual x type change in restricted assignment/swap history'
 return None,'No certified deterministic onset rule for this construction'


def type_onset(text):
 import ast
 scope={};change=None;offset=0
 def value(node):
  if isinstance(node,ast.Constant) and type(node.value) in (int,str):return type(node.value).__name__
  if isinstance(node,ast.Name):return scope[node.id]
  if isinstance(node,ast.Tuple):return tuple(value(n) for n in node.elts)
  raise ValueError('unsupported type expression')
 for line in text.splitlines(keepends=True):
  if line.startswith('print('):break
  tree=ast.parse(line);assert len(tree.body)==1 and isinstance(tree.body[0],ast.Assign)
  node=tree.body[0];assert len(node.targets)==1
  old=scope.get('x');v=value(node.value);target=node.targets[0]
  if isinstance(target,ast.Name):scope[target.id]=v
  elif isinstance(target,ast.Tuple):
   for name,typ in zip(target.elts,v):scope[name.id]=typ
  else:raise ValueError('unsupported assignment target')
  if scope.get('x')!=old:change=offset+len(line.rstrip('\n'))
  offset+=len(line)
 return change
