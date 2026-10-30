"""Section252 frozen answer parser; no semantic/alias/prefix normalization."""
import string
ASCII_PUNCT=set(string.punctuation)
def parse_answer(text):
 if not isinstance(text,str):raise TypeError('literal greedy completion text required')
 for line in text.splitlines():
  line=line.strip()
  if line:
   # Choose the first nonempty RAW line. A punctuation-only line becomes empty;
   # never fall through to another line, remove reasoning, or retain one word only.
   return ''.join(c for c in line.lower()if c not in ASCII_PUNCT).strip()
 return ''

def select_pairs(pairs,completions):
 """CPU-only exact frozen pair order, not provider completion/arrival order."""
 ids=[v for p in pairs for v in p['members']]
 if len(pairs)!=600 or len(set(ids))!=1200 or set(ids)!=set(completions):raise ValueError('complete original600pairs/1200generation records required')
 if [p['generation_order']for p in pairs]!=list(range(600)):raise ValueError('original frozen generation order')
 eligible=[]
 for p in pairs:
  x,y=[parse_answer(completions[v])for v in p['members']]
  if x and y and x!=y:eligible.append(dict(pair_id=p['pair_id'],members=p['members'],X=x,Y=y,generation_order=p['generation_order']))
 status='SCREEN_ONLY'if len(eligible)<40 else'READ_READY'
 return dict(status=status,eligible=len(eligible),selected=eligible[:84]if status=='READ_READY'else[],candidate_pairs=600)
