"""Synthetic QA checks; no actual BOW fitting or bank sealing."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from freeze_bank import qa_passes

def fixtures():
 return ({'state':{'test_auroc':.65,'tracked':True,'gate_pass':True},'descriptor':{'test_auroc':1.,'tracked':False,'gate_pass':True}},
         {'state':{'spec':{'kind':'semantic_state'}},'descriptor':{'spec':{'kind':'descriptor'}}})

def test_boundary_and_descriptor_exemption():
 m,v=fixtures();qa_passes(m,v)

def test_failing_state_blocks_input_seal():
 m,v=fixtures();m['state'].update(test_auroc=.650001,gate_pass=False)
 with pytest.raises(ValueError,match='build QA failed'):qa_passes(m,v)

def test_untrusted_pass_flag_is_recomputed():
 m,v=fixtures();m['state']['test_auroc']=.8
 with pytest.raises(ValueError,match='reporting mismatch'):qa_passes(m,v)

def test_coverage_and_nonfinite_block_seal():
 m,v=fixtures();del m['state']
 with pytest.raises(ValueError,match='coverage'):qa_passes(m,v)
 m,v=fixtures();m['state']['test_auroc']=float('nan')
 with pytest.raises(ValueError,match='invalid BOW'):qa_passes(m,v)

def synthetic_draft(tmp_path,monkeypatch):
 import freeze_bank as f
 root=tmp_path/'root';root.mkdir();monkeypatch.setattr(f,'HERE',root)
 (root/'bow_once.py').write_text('synthetic QA code')
 (root/'PRECALLS.json').write_text('{}')
 f.dump(root/'PRECALLS_SEAL.json',{'files':{'PRECALLS.json':f.sha(root/'PRECALLS.json')}})
 draft=tmp_path/'draft';draft.mkdir();qa=tmp_path/'qa';qa.mkdir()
 (draft/'items.PRIVATE.json').write_text('["synthetic bytes, no real items"]\n')
 validation={name:{'spec':{'kind':kind}} for name,kind in f.REGISTRY.values()}
 f.dump(draft/'VALIDATION.json',validation)
 f.dump(draft/'DRAFT_MANIFEST.json',{'status':'DRAFT_NOT_FROZEN','items':2688,'source_files':{'bow_once.py':f.sha(root/'bow_once.py')},'precalls_seal_sha256':f.sha(root/'PRECALLS_SEAL.json'),'files':{n:f.sha(draft/n) for n in ['items.PRIVATE.json','VALIDATION.json']}})
 (draft/'BOW_ATTEMPT.lock').write_text('synthetic attempt')
 f.dump(qa/'METRICS.json',{name:{'test_auroc':.5,'tracked':kind!='descriptor','gate_pass':True} for name,kind in f.REGISTRY.values()})
 f.dump(qa/'BOW_SEAL.json',{'complete':True,'stage':'PRESEAL_BUILD_QA','draft_manifest_sha256':f.sha(draft/'DRAFT_MANIFEST.json'),'code_sha256':f.sha(root/'bow_once.py'),'lock_sha256':f.sha(draft/'BOW_ATTEMPT.lock'),'files':{'METRICS.json':f.sha(qa/'METRICS.json')}})
 return f,draft,qa

def test_final_seal_copies_qa_tested_bytes_once(tmp_path,monkeypatch):
 f,draft,qa=synthetic_draft(tmp_path,monkeypatch);out=tmp_path/'frozen'
 f.seal_draft(draft,qa,out)
 assert (out/'items.PRIVATE.json').read_bytes()==(draft/'items.PRIVATE.json').read_bytes()
 assert (out/'BANK_SEAL.json').exists()
 with pytest.raises(FileExistsError):f.seal_draft(draft,qa,tmp_path/'second')

def test_changed_draft_cannot_be_sealed(tmp_path,monkeypatch):
 f,draft,qa=synthetic_draft(tmp_path,monkeypatch)
 (draft/'items.PRIVATE.json').write_text('changed')
 with pytest.raises(ValueError,match='hash mismatch'):f.seal_draft(draft,qa,tmp_path/'frozen')
 assert not (f.HERE/'BANK_FREEZE.lock').exists()
