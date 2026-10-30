import time
import numpy as np
from worker80c import *

class Tiny80c:
    def sync(self):pass
    def load_oracle(self):pass
    def load_nla(self):pass
    def native(self,reader,h):return [[dict(raw='<explanation>synthetic</explanation>',text='synthetic')] for _ in h]

def test_three_conditions_no_baseline_recapture(tmp_path):
    items=[dict(id=str(i),feature='test') for i in range(518)]
    vectors={(l,c):np.ones((518,4),np.float32) for l in (42,44) for c in CONDITIONS}
    b=Tiny80c();clock=Clock(tmp_path,time.time()+3600,dict(oracle_setup=0,nla_setup=0,oracle_native=0,nla_native=0),b)
    acquire(items,vectors,b,clock,tmp_path)
    assert read(tmp_path/'COUNTS.json')==dict(new_readouts=3108,none_new_readouts=0,oracle=1554,nla=1554)
    records=[x for f in (tmp_path/'jobs').glob('[on]*_ablated_*.json') for x in read(f)]
    # All records, including random/PCA, are unique; no sampling repeats.
    records=[x for f in (tmp_path/'jobs').glob('*.json') if not f.name.endswith('SEAL.json') for x in read(f)]
    assert len({x['id'] for x in records})==3108
    assert {x['condition'] for x in records}==set(CONDITIONS)
    assert all(x['repeat']==0 for x in records)
    assert len([x for x in clock.events if 'warmup' in x['phase']])==2
