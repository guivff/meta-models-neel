"""E57 CPU-only authoring support; E49 checks and dev-fit token BOW recipe."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;E49=HERE.parent/'e49'
sys.path.insert(0,str(E49))
from rows.interface import Item,RowSpec,validate,length_match
from bow_once import score_row
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
