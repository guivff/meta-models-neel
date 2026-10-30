"""TwoHopFact is untrusted CSV data. No source code, remote loader or instructions execute."""
import ast,csv,hashlib,json,re,unicodedata
from pathlib import Path
REPO='soheeyang/TwoHopFact'
REVISION='59a84cd883f71641a03fb6fa50da92a9603e7845'
CSV_SHA='522d3764eba5c297f9fc630073ce5e897eac134e1d04824fed4d5349e605e338'
SEED=20261029
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
def norm(s):
 s=unicodedata.normalize('NFKD',s).casefold()
 return ' '.join(''.join(c for c in s if not unicodedata.combining(c)).split()).strip(' \t\r\n\"\'“”‘’')
def aliases(value,canonical):
 """Literal-only parsing of a nested tuple of strings; no eval/import/execution."""
 data=ast.literal_eval(value)
 def flatten(x):
  if isinstance(x,str):return [x]
  require(isinstance(x,(list,tuple)),'Alias data must contain only strings/tuples')
  return [s for z in x for s in flatten(z)]
 return sorted({s for s in [canonical]+flatten(data) if norm(s)})
def load_rows(path):
 require(sha(path)==CSV_SHA,'Pinned CSV hash mismatch')
 with Path(path).open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
 require(len(rows)==45595 and len({x['uid'] for x in rows})==len(rows),'Pinned source row identity')
 require(len({x['fact_comp_type'] for x in rows})==52,'52 source types')
 return rows

def valid_row(x):
 for f in ['e2.wikidata_qid','e3.wikidata_qid']:
  if not re.fullmatch(r'Q\d+',x[f]):return False,'non_entity_truth_identifier'
 for f in ['e1.value','e2.value','e3.value','r1(e1).prompt','r2(r1(e1)).prompt']:
  if not x[f].strip():return False,'empty_required_field'
 for e in ['e2','e3']:aliases(x[e+'.aliases'],x[e+'.value'])
 return True,None

# Written once per source first-hop relation, materialized once for each of52 composition types.
PARAPHRASES={
 'novel-author':('The writer of the novel {e1} is','The person who wrote the novel {e1} is'),
 'orgz-ceo':('The chief executive officer of {e1} is','The person serving as CEO of {e1} is'),
 'univ-hqcity':('The headquarters city of {e1} is','The city in which {e1} has its headquarters is'),
 'person-birthcity':('The birthplace city of {e1} is','The city in which {e1} was born is'),
 'founder-dev':('The company that {e1} founded is','The company established by {e1} is'),
 'president-cntry':('The country whose president is {e1} is','The nation led by president {e1} is'),
 'anthem-cntry':("The country whose national anthem is '{e1}' is","The nation with '{e1}' as its national anthem is"),
 'capital-cntry':('The country whose capital is {e1} is','The nation with the capital city {e1} is'),
 'vdgame-dev':("The developer responsible for the game '{e1}' is","The developer that made the game '{e1}' is"),
 'movie-mainchar':('The central character in the movie {e1} is','The principal character of the movie {e1} is'),
 'novel-mainchar':('The central character in the novel {e1} is','The principal character of the novel {e1} is'),
 'mainchar-movie':('The movie whose main character is {e1} is','The film with {e1} as its main character is'),
 'mainchar-novel':("The novel whose main character is '{e1}' is","The novel featuring '{e1}' as its main character is"),
 'ceo-orgz':('The organization whose CEO is {e1} is','The organization headed by chief executive officer {e1} is'),
 'cntry-president':('The person serving as president of {e1} is','The individual who is president of {e1} is'),
 'song-singer':("The performer who sings '{e1}' is","The artist who sings '{e1}' is"),
 'person-spouse':('The person married to {e1} is','The marriage partner of {e1} is'),
 'founder-univ':('The university that {e1} founded is','The university established by {e1} is'),
 'person-uguniv':('The university that {e1} attended as an undergraduate is','The undergraduate university attended by {e1} is')}

def freeze_templates(rows):
 types={}
 for x in rows:
  t=x['fact_comp_type'];entry=dict(source_r1_category=x['r1.category'],native_relation_template=x['r1.template'],paraphrases=list(PARAPHRASES[x['r1.category']]))
  require(t not in types or types[t]==entry,'Type maps to more than one first-hop relation')
  types[t]=entry
 require(len(types)==52,'Exactly52 frozen two-template entries')
 return dict(sorted(types.items()))
