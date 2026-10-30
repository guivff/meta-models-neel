"""§173 amendment rows and sentiment_judgement, authored before scoring."""
import re
from common57 import *
SPECS={
 'loop_direction':RowSpec('loop_direction',('decrementing','incrementing'),'bookkeeping','i'),
 'page_range_digit':RowSpec('page_range_digit',('A','B'),'bookkeeping','–'),
 'section_header':RowSpec('section_header',('header','body'),'format',''),
 'sentiment_judgement':RowSpec('sentiment_judgement',('positive','negative'),'content','is')}
TARGETS=('result','value','item','current','total','answer','position','index','entry','number','cursor','step')
DIGITS=((3,7),(2,6),(4,8),(1,9))
WORDS=('Introduction','Methods','Results','Discussion','Conclusion','Abstract','Background')
BODY=('The paragraph begins with','The prose refers to','The sentence mentions','This passage discusses','The text introduces','The article describes','The paragraph considers','This sentence includes','The passage refers to','The prose mentions','The article discusses','This text considers')
POS=('great','wonderful','excellent','pleasant','enjoyable','delightful','superb','lovely','brilliant','satisfying','fantastic','marvelous')
NEG=('bad','awful','terrible','unpleasant','boring','dreadful','poor','horrible','disappointing','tedious','miserable','abysmal')
TOPICS=('service','staff','meal','film','hotel','book','product')

def page_data(t,f):
 pair=DIGITS[(t*7+f)%4];tail=10+(f*9+t)%70
 return pair,[100*d+tail for d in pair]
def render(row,t,f,v):
 if row=='loop_direction':
  n=f+11;ranges=(f'range({n}, 0, -1)',f'range(0, {n})')
  return f'def run():\n    for i in {ranges[1-v]}:\n        pass\n    for i in {ranges[v]}:\n        {TARGETS[t]} = i'
 if row=='page_range_digit':
  pair,numbers=page_data(t,f)
  return f'Citation fragment {t+1}: pp. {numbers[1-v]}–\nCurrent citation: pp. {numbers[v]}–'
 if row=='section_header':
  word=WORDS[f];header=f'## {t+1}. {word}';body=BODY[t]+' '+word
  previous,current=(body,header) if v==0 else (header,body)
  return previous+'.\n'+current
 if row=='sentiment_judgement':
  adjective=(POS if v==0 else NEG)[t]
  return f'I used the {TOPICS[f]} yesterday and wrote this short review afterward. My experience was {adjective}. Overall, the review is'
 raise ValueError(row)
def generate(row):return [Item(row,t,f,v,render(row,t,f,v),SPECS[row].values[v]) for t in range(12) for f in range(7) for v in range(2)]
def check_label(row,text):
 if not text.endswith(SPECS[row].read_token_rule):raise ValueError('read token')
 if row=='loop_direction':
  loops=re.findall(r'for i in range\(([^)]+)\):',text)
  if len(loops)!=2:raise ValueError('loop count')
  args=[int(x.strip()) for x in loops[-1].split(',')]
  if len(args)==3 and args[-1]==-1:return 'decrementing'
  if len(args)==2:return 'incrementing'
  raise ValueError('loop direction')
 if row=='page_range_digit':
  m=re.search(r'Current citation: pp\. (\d{3})–$',text)
  if not m:raise ValueError('citation')
  d=int(m[1][0]);a={x for x,y in DIGITS};b={y for x,y in DIGITS}
  if d in a:return 'A'
  if d in b:return 'B'
  raise ValueError('page digit bin')
 if row=='section_header':
  line=text.rsplit('\n',1)[-1]
  if re.fullmatch(r'## \d+\. \w+',line):return 'header'
  if any(line==s+' '+w for s in BODY for w in WORDS):return 'body'
  raise ValueError('section position')
 if row=='sentiment_judgement':
  m=re.search(r'My experience was (\w+)\. Overall, the review is$',text)
  if not m:raise ValueError('sentiment construction')
  if m[1] in POS:return 'positive'
  if m[1] in NEG:return 'negative'
  raise ValueError('unrecognised review')
 raise ValueError(row)
def annotations(row,item):
 if row=='page_range_digit':
  pair,numbers=page_data(item.template_index,item.filler_index)
  return {'answer_pair':[str(x) for x in pair],'expected_answer':str(pair[item.variant]),'authored_range_end':numbers[item.variant]+5,'source_suffix':str(numbers[item.variant]+5),'pair_family':(item.template_index*7+item.filler_index)%4}
 if row=='sentiment_judgement':return {'continuation_pair':[' positive',' negative']}
 return {}
