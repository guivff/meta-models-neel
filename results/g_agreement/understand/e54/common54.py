"""Reuse the E49 construction checks and exact CPU BOW recipe without editing E49."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent
E49=HERE.parent/'e49'
sys.path.insert(0,str(E49))
from rows.interface import Item,RowSpec,length_match,validate
from bow_once import score_row
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
