import copy,json
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e139 import runner as r
from projects.g_agreement.e130 import runner as old,olens_ar

def contract():return dict(source_commit='a'*40,source_sha256='b'*64,tests_passed=True,reward_mode='proxy_whitened_FVE')
class AR:
    class Tok:
        def __init__(self):self.seen=[]
        def encode(self,text,add_special_tokens):
            assert add_special_tokens is False;self.seen.append(text);return list(text.encode())
    def __init__(self):self.tok=self.Tok();self.calls=[]
    def reconstruct(self,rows,layer,variant,batch):
        self.calls.append(copy.deepcopy(rows));assert (layer,variant,batch)==(44,('li','ln'),16)
        return np.full((len(rows),5120),len(self.calls),np.float32)

def test_original_loader_and_reconstructor_identity():
    assert r.load_model is old.load_model and r.resolve_snapshot is old.resolve_snapshot
    assert r.OLensAR is olens_ar.OLensAR and r.BASE_REV==old.BASE_REV and r.AR_REV==old.AR_REV

def test_exact_full_strings_once_no_strip_truncate_fallback(tmp_path):
    ar=AR();xs=[dict(id='a',text='  readout\n- statement  '),dict(id='b',text=''),dict(id='c',text='z'*600)];before=copy.deepcopy(xs)
    assert r.acquire(ar,xs,tmp_path/'out',lambda *a:True,gpu_type='synthetic',owner_contract=contract())=='COMPLETE'
    assert xs==before and ar.tok.seen==[x['text']for x in xs]and len(ar.calls)==1
    assert ar.calls[0][1]==[]and len(ar.calls[0][2])==600
    assert np.array_equal(np.load(tmp_path/'out/rebuild-0000.npy'),np.ones((3,5120),np.float32))

def test_17strings_two_forward_batches_and_exact_index(tmp_path):
    ar=AR();xs=[dict(id=str(i),text=str(i))for i in range(17)]
    r.acquire(ar,xs,tmp_path/'out',lambda *a:True,gpu_type='synthetic',owner_contract=contract())
    assert [len(x)for x in ar.calls]==[16,1]
    assert [x['id']for x in json.loads((tmp_path/'out/INDEX.json').read_text())]==[x['id']for x in xs]

def test_no_fit_and_no_reuse(tmp_path):
    ar=AR();xs=[dict(id='a',text='text')]
    assert r.acquire(ar,xs,tmp_path/'out',lambda *a:False,gpu_type='synthetic',owner_contract=contract())=='NO_FIT'
    assert ar.calls==[]
    with pytest.raises(FileExistsError):r.acquire(ar,xs,tmp_path/'out',lambda *a:True,gpu_type='synthetic',owner_contract=contract())

def test_owner_scoring_pin_before_outputs(tmp_path):
    for c in [dict(contract(),tests_passed=False),dict(contract(),reward_mode='guessed'),dict(contract(),source_commit='bad')]:
        ar=AR()
        with pytest.raises(ValueError):r.acquire(ar,[dict(id='a',text='text')],tmp_path/'out',lambda *a:True,gpu_type='synthetic',owner_contract=c)
        assert ar.calls==[]and not(tmp_path/'out').exists()

def test_nonfinite_rebuild_refused(tmp_path):
    ar=AR();ar.reconstruct=lambda *a,**k:np.full((1,5120),np.nan,np.float32)
    with pytest.raises(ValueError):r.acquire(ar,[dict(id='a',text='text')],tmp_path/'out',lambda *a:True,gpu_type='synthetic',owner_contract=contract())

def test_private_fields_duplicateids_refused():
    for xs in [[dict(id='a',text='text',condition='true')],[dict(id='a',text='x'),dict(id='a',text='y')]]:
        with pytest.raises(ValueError):r.validate_items(xs)

def test_public_input_integrity_and_token_policy(tmp_path):
    from projects.g_agreement.e100.contract import write,sha
    xs=[dict(id='synthetic',text='exact text')]
    write(tmp_path/'items.json',xs)
    m=dict(experiment='E139',prompts=1,labels_on_pod=False,tokenizer_revision=r.BASE_REV,tokenization=dict(add_special_tokens=False,truncation=False,strip=False,tag_added_by='original OLensAR.reconstruct tag44'))
    write(tmp_path/'MANIFEST.json',m)
    write(tmp_path/'INPUT_SEAL.json',dict(experiment='E139',labels_on_pod=False,files={n:sha(tmp_path/n)for n in ['items.json','MANIFEST.json']}))
    digest=sha(tmp_path/'INPUT_SEAL.json')
    assert r.load(tmp_path,digest)[0]==xs
    (tmp_path/'items.json').write_text('[]')
    with pytest.raises(ValueError):r.load(tmp_path,digest)

def test_bad_shape_and_batch_refused(tmp_path):
    ar=AR();xs=[dict(id='x',text='literal')]
    with pytest.raises(ValueError):r.acquire(ar,xs,tmp_path/'batch',lambda *a:True,gpu_type='synthetic',owner_contract=contract(),batch=8)
    assert ar.calls==[]
    ar.reconstruct=lambda *a,**k:np.zeros((1,4),np.float32)
    with pytest.raises(ValueError):r.acquire(ar,xs,tmp_path/'shape',lambda *a:True,gpu_type='synthetic',owner_contract=contract())
