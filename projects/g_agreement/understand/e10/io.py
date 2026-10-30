from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'results/g_agreement/understand/e10'
CACHE=ROOT/'cache/g_agreement/understand/e10'
SEED=20261024
EXPOSED_W1_ITEM='c3c3160303c81bf79e974959'
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def jsonl(p,rs):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:
  for x in rs:f.write(canonical(x)+'\n')
def rank(*v):return digest(canonical([SEED,*v]))
