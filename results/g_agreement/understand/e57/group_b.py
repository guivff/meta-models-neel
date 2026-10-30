"""New E57 Group B rows. No previous items or outcome imports."""
import re,tokenize,io
from common57 import *
SPECS={
 'subject_number':RowSpec('subject_number',('singular','plural'),'syntactic','the'),
 'clause_pending':RowSpec('clause_pending',('main_clause_owed','no_main_clause_owed'),'syntactic',','),
 'nesting_depth':RowSpec('nesting_depth',('one','three'),'bookkeeping',','),
 'indent_level':RowSpec('indent_level',('four','twelve'),'bookkeeping','pass')}
SUBJECT_A=(('key','ring','coin','badge','card','stamp','button'),('pen','watch','stone','spoon','hat','ticket','letter'))
SUBJECT_B=(('books','chairs','cups','plates','lamps','boxes','bags'),('bottles','tables','windows','doors','shelves','desks','shoes'))
AGENT_A=('ranger','porter','keeper','clerk','courier','inspector','farmer','tailor','miner','barber','hunter','sailor')
AGENT_B=('painter','teacher','driver','cook','singer','dancer','doctor','baker','pilot','nurse','actor','artist')
VERB_A=('left','held','kept','found','lost','noticed','placed','hid','dropped','forgot','spotted','examined')
VERB_B=('carried','moved','stacked','sorted','packed','loaded','stored','arranged','collected','counted','borrowed','delivered')
CLAUSE_A=(('rain','sky','road','field','lake','hill','path'),('river','valley','beach','shore','ridge','forest','stream'))
CLAUSE_B=(('gate','door','room','hall','porch','yard','wall'),('tower','cabin','shed','cellar','attic','studio','barn'))
PRED_A=('calm','clear','dry','warm','bright','still','quiet','cold','wet','dark','green','wide')
PRED_B=('open','closed','empty','clean','white','safe','narrow','small','tall','large','red','old')
BRACKETS=('[ [ [','[ [ (','[ ( [','( [ [','( ( [','( [ (','[ ( (','( ( (','{ [ [','[ { [','[ [ {','{ ( [')
CONDITIONS=('if True','if False','while True','while False','if not False','while not False')

def render(row,t,f,v):
 split=int(t>=6)
 if row=='subject_number':
  subject=(SUBJECT_A if v==0 else SUBJECT_B)[split][f];agent=(AGENT_A if v==0 else AGENT_B)[t];verb=(VERB_A if v==0 else VERB_B)[t]
  return f'The {subject} that the {agent} {verb} near the'
 if row=='clause_pending':
  noun=(CLAUSE_A if v==0 else CLAUSE_B)[split][f];pred=(PRED_A if v==0 else PRED_B)[t]
  plain=f'The {noun} was {pred},';dependent=f'Although the {noun} was {pred},'
  previous,current=(plain,dependent) if v==0 else (dependent,plain)
  return f'Earlier fragment: " {previous} "\nCurrent fragment: {current}'
 if row=='indent_level':
  outer=CONDITIONS[t%6];inner=CONDITIONS[(t//6+2)%6];deep=f'if {f+11}'
  prefix=f'{outer}:\n'
  nested=f'    {inner}:\n        {deep}:\n            pass'
  return prefix+(nested+'\n    pass' if v==0 else '    pass\n'+nested)
 if row=='nesting_depth':
  # Brackets in the comment do not contribute to the executable expression depth.
  brackets=BRACKETS[t].split();n=f+101
  return (f'# {brackets[1]} {brackets[2]} {n} \n{brackets[0]} {f+1},' if v==0 else f'# {n} \n'+ ' '.join(brackets)+f' {f+1},')
 raise ValueError(row)

def generate(row):return [Item(row,t,f,v,render(row,t,f,v),SPECS[row].values[v]) for t in range(12) for f in range(7) for v in range(2)]
def check_label(row,text):
 if not text.endswith(SPECS[row].read_token_rule):raise ValueError('wrong read point')
 if row=='subject_number':
  m=re.fullmatch(r'The (\w+) that the \w+ \w+ near the',text)
  if not m:raise ValueError('subject construction')
  if m[1] in sum(SUBJECT_A,()):return 'singular'
  if m[1] in sum(SUBJECT_B,()):return 'plural'
  raise ValueError('unknown subject noun')
 if row=='clause_pending':
  tail=text.rsplit('Current fragment: ',1)[-1]
  if re.fullmatch(r'Although the \w+ was \w+,',tail):return 'main_clause_owed'
  if re.fullmatch(r'The \w+ was \w+,',tail):return 'no_main_clause_owed'
  raise ValueError('unsupported current clause')
 if row=='indent_level':
  line=text.rsplit('\n',1)[-1]
  if line.strip()!='pass':raise ValueError('not first token after indentation')
  spaces=len(line)-len(line.lstrip(' '))
  if spaces==4:return 'four'
  if spaces==12:return 'twelve'
  raise ValueError('indent bin')
 if row=='nesting_depth':
  depth=0
  try:
   for tok in tokenize.generate_tokens(io.StringIO(text).readline):
    if tok.type==tokenize.OP:
     if tok.string in '([{':depth+=1
     elif tok.string in ')]}':depth-=1
  except tokenize.TokenError as e:
   if 'EOF in multi-line statement' not in str(e):raise
  if depth==1:return 'one'
  if depth==3:return 'three'
  raise ValueError('nesting bin')
 raise ValueError(row)
