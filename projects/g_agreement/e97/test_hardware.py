from types import SimpleNamespace
import json
import numpy as np
import pytest
import torch
from projects.g_agreement.e97.hardware import smoke
from projects.g_agreement.e97.readers import write

@pytest.mark.parametrize('reader',['oracle','nla'])
@pytest.mark.parametrize('finite',[True,False])
def test_native_smoke_reports_first_divergence_and_rejects_nonfinite(tmp_path,reader,finite):
    inputs=tmp_path/'inputs';inputs.mkdir();out=tmp_path/'out';out.mkdir()
    np.save(inputs/f'SMOKE_{reader}.npy',np.ones((3,5120),dtype=np.float32))
    (inputs/f'SMOKE_{reader}.json').write_text(json.dumps(dict(gpu_type='H200',reference_batch=8,source_reader_seal_sha256='frozen',records=[dict(id=str(i),raw='same')for i in range(3)])))
    head=torch.nn.Linear(1,2);model=SimpleNamespace(get_output_embeddings=lambda:head)
    class Backend:
        oracle=SimpleNamespace(model=model)
        nla=SimpleNamespace(av=model)
        def native_one(self,r,h):
            assert r==reader and h.shape==(3,5120)
            head(torch.ones((3,1))if finite else torch.full((3,1),float('nan')))
            return [[dict(raw=x)]for x in ['same','changed','same']]
    path=out/f'B200_SMOKE.{reader}.json'
    if not finite:
        with pytest.raises(ValueError,match='Nonfinite'):smoke(Backend(),reader,inputs,out,write)
        assert not path.exists()
    else:
        smoke(Backend(),reader,inputs,out,write);d=json.loads(path.read_text())
        assert d['status']=='PASS' and d['items']==3 and d['finite_logits']
        assert d['first_divergence']==dict(item='1',character=0)
        assert d['comparisons'][0]['exact_match']
