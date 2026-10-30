from pathlib import Path
import copy,json
import pytest
from projects.g_agreement.e133 import runner as v3
from projects.g_agreement.e137 import runner as r
from projects.g_agreement.e100.contract import write,sha

def items(n=300,one=0):
    return [dict(id=f'{f}:{i}:{m}',pair_id=f'{f}:{i}',family=f,member=m,ids=list(range(1,13)),read_index=11,candidate_ids=[[[3],[4]]])for f,count in [('multi_hop',n),('one_hop',one)]for i in range(count)for m in (0,1)]

def test_original_science_and_orchestration_code_objects_unchanged():
    for name in ['generation_batch','capture_batch','patch_batch','batches']:assert getattr(r,name)is getattr(v3,name)
    assert r._screen.__code__ is v3.screen.__code__ and r._main.__code__ is v3.main_job.__code__
    for name in ['capture_batch','patch_batch','generation_batch','batches','Writer']:
        assert r._main.__globals__[name]is v3.main_job.__globals__[name]

@pytest.mark.parametrize('a,b,action',[(19,19,'SCREEN_RESULTS_ONLY'),(20,0,'MAIN'),(29,31,'MAIN'),(42,150,'MAIN')])
def test_registered_count_disposition(a,b,action):
    x=r.count_disposition(a,b);assert x['action']==action and x['D1_kept']==min(42,a)and x['D2_kept']==min(42,b)
    assert x['D1_counts']==(a>=30)and x['D2_counts']==(b>=30)

def test_complete_screen_with_literal_frozen_owner_control_count():
    assert r.validate_items(items(300,30),'screen')==dict(multi_hop=300,one_hop=30)
    with pytest.raises(ValueError):r.validate_items(items(299,30),'screen')

def test_no_silent_control_truncation_at_readout_ceiling():
    assert r.validate_items(items(84,16),'main')==dict(multi_hop=84,one_hop=16)
    with pytest.raises(ValueError,match='ceiling'):r.validate_items(items(84,17),'main')

def test_screen_forecast_and_freshfolder_guard(tmp_path):
    out=tmp_path/'screen';assert r.screen(None,None,items(300,30),out,lambda*a:False,gpu_type='synthetic')=='NO_FIT'
    with pytest.raises(FileExistsError):r.screen(None,None,items(300,30),out,lambda*a:True,gpu_type='synthetic')

def test_roles_and_nonascending_pair_rejected():
    x=items(2);x[0]['correct']='private'
    with pytest.raises(ValueError):r.validate_items(x,'main')
    x=items(2);x[0]['candidate_ids']=[[[4],[3]]]
    with pytest.raises(ValueError):r.validate_items(x,'main')

def test_stage_load_requires_registered_control_rule_before_main(tmp_path):
    xs=items(42,0);write(tmp_path/'items.json',xs);write(tmp_path/'MANIFEST.json',{})
    selection=dict(selection_basis='behaviour_only_both_members_correct',reader_calls_before_selection=0,screen_output_seal_sha256='synthetic',kept_item_ids=[x['id']for x in xs])
    write(tmp_path/'SCREEN_SELECTION_SEAL.json',selection)
    def seal():
        write(tmp_path/'INPUT_SEAL.json',dict(experiment='E137',stage='main',labels_on_pod=False,files={p:sha(tmp_path/p)for p in ['items.json','MANIFEST.json','SCREEN_SELECTION_SEAL.json']}));return sha(tmp_path/'INPUT_SEAL.json')
    with pytest.raises(ValueError,match='registered'):r.load(tmp_path,seal(),'main')
    selection['one_hop_main_rule_authority']='synthetic-protocol-fixture-only';write(tmp_path/'SCREEN_SELECTION_SEAL.json',selection)
    assert r.load(tmp_path,seal(),'main')==xs
