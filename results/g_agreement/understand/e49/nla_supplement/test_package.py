import json,hashlib,tarfile,ast
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def read(p):return json.loads(p.read_text())
def test_same_gated_items_capture_and_order():
 b=read(HERE/'INPUT_BINDING.json');p=Path(b['inputs']);items=read(p/'items.json')
 original=ROOT/'cache/g_agreement/understand/e49/verified_section149/out'
 expected=[json.loads(line)['id'] for row in b['qualified_rows'] for line in (original/'readers'/row/'nla_native.jsonl').read_text().splitlines()]
 assert [x['id'] for x in items]==expected and len(set(expected))==672
 order=read(original/'capture/items.order.json');ix={v:i for i,v in enumerate(order)}
 assert np.array_equal(np.load(p/'acts42.npy'),np.load(original/'capture/acts42.npy',mmap_mode='r')[[ix[k] for k in expected]])
def test_e61_pod_archive_label_free():
 b=read(HERE.parents[1]/'e61/job/INPUT_BINDING.json')
 with tarfile.open(b['archive']['path']) as t:
  items=json.load(t.extractfile('inputs/items.json'))
 assert len(items)==276 and all('label' not in x and 'value' not in x for x in items)
def test_rerun_has_no_oracle_or_capture_calls():
 p=HERE.parents[1]/'e56/job/rerun_nla_only.py';tree=ast.parse(p.read_text())
 calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
 assert 'load_nla' in calls
 assert not calls & {'load_oracle','capture','capture_pair','native_eight','fit_probe'}
def test_original_e49_source_unchanged():
 p=HERE.parent/'job';s=read(p/'SOURCE_SEAL.json')
 for name,digest in s['files'].items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest
