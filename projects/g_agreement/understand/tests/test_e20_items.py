import copy,gzip,json,os
from pathlib import Path
import pytest
from projects.g_agreement.understand import e20_items as M
from projects.g_agreement.blindspot.items import load_pinned_tokenizer
@pytest.fixture(scope='module')
def bank():
 path=Path(os.environ.get('E20_TOKENIZER', 'cache/g_assets/Qwen__Qwen3.6-27B'))
 if not (path / 'tokenizer.json').is_file():
  pytest.skip('set E20_TOKENIZER to the pinned Qwen tokenizer')
 t=load_pinned_tokenizer(path)
 p=Path('results/g_agreement/understand/e20/freeze/items.jsonl.gz')
 return t,[json.loads(x) for x in gzip.decompress(p.read_bytes()).decode().splitlines()]
def test_all_captures(bank):
 t,x=bank;assert M.audit(t,x)['capture_records']==5760
@pytest.mark.parametrize('feature',M.ROWS)
@pytest.mark.parametrize('field',['read_index','distance','consequence_index','label'])
def test_corrupted_metadata_rejected(bank,feature,field):
 t,x=bank;pair=copy.deepcopy([r for r in x if r['feature']==feature and r['family']==0 and r['variant']==0 and r['distance']==2]);pair[0][field]+=1
 with pytest.raises((AssertionError,IndexError)):M.audit(t,pair,complete=False)
def test_environment_and_fixed_events():
 p=json.loads(Path('results/g_agreement/understand/e20/ENVIRONMENT_PIN.json').read_text());assert p['worker_python']=='/weights/venv-kernels/bin/python'
 assert M.NUMBERS==('1234','5678') and M.LEXICON=={'A':['wonderful'],'B':['terrible']}
