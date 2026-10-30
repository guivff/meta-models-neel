import json,time
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e96.sample import execute,Clock,jobs

class Prediction:
    def __init__(self,n):self.x=np.ones((n,5120),dtype='float32')
    def detach(self):return self
    def float(self):return self
    def cpu(self):return self
    def numpy(self):return self.x

class Fake:
    def __init__(self):self.calls=[]
    def load(self,reader,phase):self.calls.append(('load',reader,phase))
    def release(self):pass
    def generate(self,reader,h,seed):
        self.calls.append(('generate',reader,len(h),seed))
        return [dict(text='synthetic stub',raw='synthetic stub',malformed=False) for _ in h]
    def reconstruct(self,reader,texts):return Prediction(len(texts))

def test_exact_16_samples_native_layers_skip_e62_nla_and_timestamp(tmp_path):
    inp=tmp_path/'in';out=tmp_path/'out';inp.mkdir();out.mkdir()
    rows=[dict(key='000',bank='E49',row='r',slot=0,readers=['oracle','nla'],batch_seed_offset=0),dict(key='001',bank='E62',row='r2',slot=0,readers=['oracle'],batch_seed_offset=640)]
    for row in rows:
        p=inp/row['key'];p.mkdir();(p/'ids.json').write_text(json.dumps([str(i) for i in range(40)]))
        for layer in (42,44):np.save(p/f'acts{layer}.npy',np.ones((40,5120),dtype='float32'))
    backend=Fake();execute(inp,{'rows':rows},0,backend,Clock(out,time.time()+3600),out)
    for row in rows:
        for reader in row['readers']:
            records=[r for p in sorted((out/row['key']/reader).glob('generate.*.json')) for r in json.loads(p.read_text())]
            assert len(records)==640
            for i in range(40):assert sorted(r['sample_index'] for r in records if r['id']==str(i))==list(range(16))
    assert not (out/'001/nla').exists()
    assert json.loads((out/'FIRST_OUTPUT.json').read_text())['first_output_utc']!='unknown'
    assert len([c for c in backend.calls if c[:2]==('generate','oracle')])==40
    with pytest.raises(ValueError,match='never be overwritten'):execute(inp,{'rows':rows},0,backend,Clock(out,time.time()+3600),out)
