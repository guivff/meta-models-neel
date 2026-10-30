import json
from pathlib import Path
import pytest
from projects.g_agreement.e96.retained import scope
def test_separate_scope_exact_and_disjoint_from_primary():
 p=json.loads(Path('cache/g_agreement/e96/sampling_inputs/PLAN.json').read_text());a=scope(p,True);b=scope(p,'slot1-separate')
 assert b['slots']==[1] and b['samples']==17920 and b['records']==20160 and b['reader_cells_retained']==28 and b['rows_retained']==18 and len(b['missing_reader_cells'])==55
 assert set(a['slots']).isdisjoint(b['slots'])
 assert {(x['key'],x['reader']) for x in a['missing_reader_cells']}=={(row['key'],reader) for row in p['rows'] if row['slot']==1 for reader in row['readers']}
 assert all('outside separate' in x['reason'] for x in b['missing_reader_cells'])
def test_separate_rejects_wrong_grid_and_unknown_scope():
 p=json.loads(Path('cache/g_agreement/e96/sampling_inputs/PLAN.json').read_text());p['shard_samples'][1]-=32
 with pytest.raises(ValueError,match='separate slot1'):scope(p,'slot1-separate')
 with pytest.raises(ValueError,match='unknown administrative'):scope(p,'anything')
