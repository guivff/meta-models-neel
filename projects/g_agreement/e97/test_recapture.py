from pathlib import Path
import contextlib,io,json,tarfile,hashlib,sys
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.e97 import capture42 as C
from projects.g_agreement.ops import i5_controller as O

def test_capture_only42_original_endpoint(monkeypatch):
    monkeypatch.setattr(sys,'argv',['capture42.py','--cpu-import-preflight']);C.main()
    import torch
    import mats.capture
    seen=[]
    def capture(model,ids,layers,positions,**kwargs):
        seen.append((layers,positions));return {42:torch.ones((len(ids),1,5120))}
    monkeypatch.setattr(mats.capture,'capture',capture)
    backend=SimpleNamespace(oracle=SimpleNamespace(base=contextlib.nullcontext,model=None,tok=SimpleNamespace(pad_token_id=0)))
    out=C.capture42_method()(backend,[{'ids':[1,2]},{'ids':[3]}])
    assert set(out)=={42}and out[42].shape==(2,5120)
    assert seen==[([42],[[1],[0]])]

def test_provider_identity_no_cross_pod():
    state=dict(pod_id='ours',createdAt='timestamp')
    O.identity(None,state)
    for wrong in [dict(id='theirs',createdAt='timestamp'),dict(id='ours',createdAt='different')]:
        with pytest.raises(ValueError):O.identity(wrong,state)

def test_archive_hash_failure_never_accepted(tmp_path,monkeypatch):
    data=b'capturefixture';seal=dict(status='COMPLETE',sites=[42],reader_outputs=0,files={'acts42.npy':'0'*64})
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.PAX_FORMAT)as t:
        for name,value in [('out/acts42.npy',data),('out/CAPTURE_SEAL.json',json.dumps(seal).encode())]:
            info=tarfile.TarInfo(name);info.size=len(value);t.addfile(info,io.BytesIO(value))
    payload=buf.getvalue()
    def remote(*a,**k):k['stdout'].write(payload);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(O.subprocess,'run',remote)
    state=dict(run=str(tmp_path),addr='127.0.0.1:22',remote='/workspace/e97r42')
    with pytest.raises(ValueError,match='changed'):O.archive(state,True)
    assert not(tmp_path/'final.pax.tar.gz').exists()

def test_b200_smoke_reports_first_divergence(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,'argv',['capture42.py','--cpu-import-preflight']);C.main()
    import torch
    head=torch.nn.Linear(1,2)
    class Oracle:
        model=SimpleNamespace(get_output_embeddings=lambda:head)
        def verbalize(self,*a,**k):
            head(torch.ones((1,1)))
            return [['same'],['changed'],['same']]
    backend=SimpleNamespace(oracle=Oracle())
    np.save(tmp_path/'SMOKE44.npy',np.ones((3,5120),np.float32))
    (tmp_path/'SMOKE_REFERENCE.json').write_text(json.dumps(dict(source_reader_seal_sha256='fixture',reference_batch=8,records=[dict(id=str(i),raw='same')for i in range(3)])))
    C.hardware_smoke(backend,tmp_path,tmp_path)
    r=json.loads((tmp_path/'B200_SMOKE.json').read_text())
    assert r['status']=='PASS'and r['items']==3 and r['finite_logits']
    assert r['first_divergence']==dict(item='1',character=0)
