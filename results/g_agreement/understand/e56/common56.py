"""E56 uses E49's unchanged construction interface and dev-fit BOW recipe."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent
E49=HERE.parent/'e49'
sys.path.insert(0,str(E49))
from rows.interface import Item,RowSpec,validate,length_match
from bow_once import score_row
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
OBJECTS=('invoice','schedule','contract','receipt','proposal','estimate','report')
HEADS=('The clerk checked the dated record.','The visitor read the complete record.','The editor inspected the printed record.','The assistant examined the recent record.','The archivist reviewed the written record.','The manager checked the earlier record.','The reader inspected the copied record.','The curator examined the archived record.','The secretary reviewed the filed record.','The reporter checked the signed record.','The researcher read the public record.','The auditor examined the final record.')
def context(t,f):return HEADS[t]+' The subject was the '+OBJECTS[f]+'. '
