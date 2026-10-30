import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from vendor_readerbench.e63 import validate_scope

def test_single_pool_grid_rejects_repeat():
 rows=[{'bank':'E56','row':'x','reader':r,'readouts':[],'expected_readout_ids':[]} for r in ('oracle','nla')]
 pool=[{'id':f'{r}:{a}:{i}','item_id':f'{a}:{i}','reader':r,'arm':a,'layer':44 if r=='oracle' else 42,'repeat':0} for r in ('oracle','nla') for a in ('random','shuffled') for i in range(200)]
 data={'scope_complete':True,'banks':['E56','E57','E59','E62'],'rows':rows,'expected_rows':[[x['bank'],x['row'],x['reader']] for x in rows],'placebo':pool}
 validate_scope(data)
 data['placebo'].append(dict(pool[0],id='extra',repeat=1))
 with pytest.raises(ValueError):validate_scope(data)
