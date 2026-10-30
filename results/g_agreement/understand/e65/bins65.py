"""Registered A/B count-bin trackers, never exact-count persistence."""
import re
from onsets65 import STRUCT,body_start,COUNT_ROWS
OTHER='__OTHER__'
# Numeric cutoffs from frozen definitions and constructions; do not invent thresholds
# for the old W1 few/many word-count rows, whose sampled values do not define a bin edge.
UNDEFINED={'prose_words','prose_budget','prose_column','list_words'}
def choose(n,a,b,values):
 if n is None:return None
 return values[0] if a(n) else values[1] if b(n) else OTHER

def json_counts(s):
 stack=[];quoted=False;escape=False
 for c in s:
  if quoted:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quoted=False
   continue
  if c=='"':quoted=True
  elif c=='{':stack.append(['object',0])
  elif c=='[':stack.append(['array',0])
  elif c in '}]':
   if not stack:return None,None
   stack.pop()
  elif c==',' and stack:stack[-1][1]+=1
 objects=[x for x in stack if x[0]=='object']
 return len(objects),objects[-1][1]+1 if objects else None

def numeric(f,s):
 if not s.strip():return None
 if f=='prose_sentence':return 1+len(re.findall(r'[.!?]+\s+(?=\S)',re.split(r'\n\s*\n',s)[-1]))
 if f=='python_line':
  lines=s.split('\n');return len([x for x in lines[1:] if x.strip()]) or None
 if f in ('python_argument','python_depth','python_depth_ordinal','nesting_depth'):
  tokens,mode,_=STRUCT._python_lex(s);frames=STRUCT._python_frames(tokens)
  if f=='python_argument':
   calls=[x for x in frames if x['call']];return calls[-1]['commas']+1 if calls else None
  return len(frames)
 if f in ('python_indent','indent_level'):
  line=s.split('\n')[-1]
  return len(line)-len(line.lstrip(' ')) if line.strip() else None
 if f.startswith('latex_'):
  text=re.sub(r'(?<!\\)%[^\n]*','',s)
  if f=='latex_section':
   count=0
   for m in re.finditer(r'\\section(?:\[[^]]*\])?\s*\{',text):
    depth=1
    for brace in re.finditer(r'(?<!\\)[{}]',text[m.end():]):
     depth+=1 if brace.group()=='{' else -1
     if depth==0:count+=1;break
   return count
  if f=='latex_item':return len(re.findall(r'\\item\b',text))
  if f=='latex_brace':return len(re.findall(r'(?<!\\)\{',text))-len(re.findall(r'(?<!\\)\}',text))
 if f in ('json_depth','json_field'):
  depth,field=json_counts(s);return depth if f=='json_depth' else field
 if f.startswith('table_'):
  block=re.split(r'\n[ \t]*\n',s)[-1];lines=block.split('\n');line=lines[-1]
  if f in ('table_column','table_column_ordinal'):
   pipes=list(re.finditer(r'(?<!\\)\|',line))
   return len(pipes) if line.lstrip().startswith('|') else len(pipes)+1
  separators=[i for i,l in enumerate(lines) if re.fullmatch(r'[ |:\-]+',l) and '---' in l]
  if not separators:return None
  return len([l for l in lines[separators[-1]+1:] if l.strip()]) or None
 if f in ('list_index','list_depth','list_completed'):
  lines=s.split('\n');marks=[re.match(r'^( *)([-+*])\s+',l) for l in lines];marks=[m for m in marks if m]
  if f=='list_completed':return len(re.findall(r'(?m)^\s*[-+*] \[[xX]\]',s))
  if not marks:return None
  if f=='list_index':
   current=len(marks[-1][1]);count=0
   for m in reversed(marks):
    if len(m[1])<current:break
    if len(m[1])==current:count+=1
   return count
  levels=[]
  for m in marks:
   indent=len(m[1])
   while levels and indent<levels[-1]:levels.pop()
   if not levels or indent>levels[-1]:levels.append(indent)
  return len(levels)
 if f=='sentence_position':return len(re.findall(r'\S+',re.split(r'[.!?]+\s+',s)[-1]))
 if f=='paragraph_index':return len([p for p in re.split(r'\n\s*\n',s) if p.strip()])
 if f=='paragraph_start':return 1+len(re.findall(r'[.!?]+\s+(?=\S)',re.split(r'\n\s*\n',s)[-1]))
 raise ValueError('unsupported count '+f)

def bin_value(f,n):
 if f in ('prose_sentence','python_line','latex_section','table_row'):return choose(n,lambda n:1<=n<=2,lambda n:n>=6,('early','late'))
 if f in ('latex_item','list_index'):return choose(n,lambda n:n==1,lambda n:n>=6,('first','later'))
 if f=='list_completed':return choose(n,lambda n:1<=n<=2,lambda n:n>=6,('few','many'))
 if f in ('python_depth','latex_brace','json_depth','list_depth'):return choose(n,lambda n:n==1,lambda n:n==3,('shallow','deep'))
 if f=='nesting_depth':return choose(n,lambda n:n==1,lambda n:n==3,('one','three'))
 if f=='python_indent':return choose(n,lambda n:n==4,lambda n:n==12,('shallow','deep'))
 if f=='indent_level':return choose(n,lambda n:n==4,lambda n:n==12,('four','twelve'))
 if f in ('python_argument','table_column','json_field'):return choose(n,lambda n:n==1,lambda n:n==5,('first','later'))
 if f.endswith('_ordinal'):return str(n) if n else None
 if f=='sentence_position':return choose(n,lambda n:1<=n<=3,lambda n:n>12,('first_three','after_twelve'))
 if f=='paragraph_index':return choose(n,lambda n:n==1,lambda n:n>=3,('first','third_or_later'))
 if f=='paragraph_start':return choose(n,lambda n:n==1,lambda n:n>=2,('first_sentence','later_sentence'))
 raise ValueError(f)

def run_length(states,target):
 # Unknown states are not silently carried across an unresolved onset.
 if not states or states[-1]!=target:return None
 j=len(states)-1
 while j>0 and states[j-1]==target:j-=1
 return len(states)-j

def count_p(bank,x,offsets):
 f=x['feature'];text=x['text'];start=body_start(x)
 if f in UNDEFINED:return None,'Frozen few/many examples do not specify an intervening bin boundary; no cutoff inferred'
 if f in ('linewrap_implicit','linewrap_asked','count_gradient_first_letter'):
  # Asked twins refer to the original line, frozen at the implicit read position.
  stop=x.get('original_read_char_end',text.find('\nHow many characters'))
  if stop<0:stop=len(text)
  original=text[:stop];line_start=original.rfind('\n')+1
  states=[]
  for a,b in offsets:
   n=max(0,min(b,stop)-line_start)
   states.append('short' if 0<n<=15 else 'long' if n>=55 else OTHER)
  target=x.get('value');return run_length(states,target),'Current-line character bins: 1–15 / ≥55; no reset within bin; asked twins retain original count'
 states=[]
 for a,b in offsets:
  if b<=start:states.append(None);continue
  try:states.append(bin_value(f,numeric(f,text[start:b])))
  except (ValueError,IndexError):states.append(None)
 target=str(x.get('value'))
 if target=='None':return None,'Frozen item label unavailable for count-bin verification'
 result=run_length(states,target)
 return result,'Longest terminal token-prefix run in registered '+f+' bin; final label verified' if result is not None else 'Terminal tracker bin does not match frozen label or is undetermined; no value imputed'
