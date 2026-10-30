from pathlib import Path
import json,numpy as np,torch,pytest
from projects.g_agreement.e127.test_runner import Tiny,Tok
from projects.g_agreement.e133.runner import generation_batch,capture_batch,patch_batch,validate_items,screen,CAPTURE,PATCH


def item(member=0,family='multi_hop',pair='p'):
    return dict(id=pair+str(member),pair_id=pair,family=family,member=member,ids=list(range(1,13)),read_index=11,candidate_ids=[[[3],[4]],[[3+member],[5]]])


def test_original_e131_code_32greedy_steps_and_e109_exact_six_capture_sites():
    m=Tiny();r=capture_batch(m,Tok(),[item()])
    assert m.calls==33 and set(r['activations'])==set(CAPTURE)
    assert len(r['answers'][0]['token_ids'])==32 and r['answers'][0]['greedy_max_new_tokens']==32
    expected=torch.cat([m.snapshots[1][63][:,-1]]*8,dim=-1).numpy()
    assert np.array_equal(r['vocab_logits'],expected) # SAME first generated pass, no extra forward
    for L,h in r['activations'].items():assert np.array_equal(h,m.snapshots[0][L][:,11].numpy())
    assert all(not b._forward_hooks for b in m.layers)


@pytest.mark.parametrize('L',PATCH)
@pytest.mark.parametrize('control',['read','earlier','random'])
def test_original_e126_insert_controls_no_upstream_hook_and_norm_matching(L,control):
    m=Tiny();natural=capture_batch(m,Tok(),[item()]);v=natural['activations'][L]+np.array([[.5,-.3,.1,.2]],np.float32)
    before=m.calls;r=patch_batch(m,[item()],v,L,control)[0]
    # Same frozen E101 continuation scorer; no U hook; read replacement vs norm random.
    assert m.calls>before and r['patch']['upstream_hook_installed']is False
    assert r['patch']['block']==L and r['patch']['direction']=='insert'
    if control=='earlier':assert r['patch']['position']<3
    else:assert r['patch']['position']==11
    if control=='random':assert r['patch']['delta_norm']==pytest.approx(r['patch']['reference_read_replacement_delta_norm'],rel=1e-5)
    assert 'pair_logprobs'in r and all(not b._forward_hooks for b in m.layers)


def test_validate_full_screen900_bothmembers_same_common_contrast_and_family():
    xs=[item(k,f,pair=f+str(i))for f,n in [('multi_hop',300),('one_hop',150)]for i in range(n)for k in (0,1)]
    assert validate_items(xs,'screen')=={'multi_hop':300,'one_hop':150}
    with pytest.raises(ValueError):validate_items(xs[:-1],'screen')
    xs[1]['candidate_ids'][0]=[[[4],[3]]][0]
    with pytest.raises(ValueError,match='common'):validate_items(xs,'screen')


def test_fewer_kept_pairs_accepted_but_never_silent_refill():
    assert validate_items([item(),item(1)],'main')=={'multi_hop':1,'one_hop':0}
    with pytest.raises(ValueError):validate_items([dict(item(),label=1),item(1)],'main')


def test_screen_no_fit_and_freshfolder_guards(tmp_path):
    xs=[item(k,f,pair=f+str(i))for f,n in [('multi_hop',300),('one_hop',150)]for i in range(n)for k in (0,1)]
    m=Tiny();out=tmp_path/'attempt'
    assert screen(m,Tok(),xs,out,lambda*a:False,gpu_type='synthetic')=='NO_FIT'and m.calls==0
    assert json.loads((out/'OUTPUT_SEAL.json').read_text())['status']=='NO_FIT'
    with pytest.raises(FileExistsError):screen(m,Tok(),xs,out,lambda*a:True,gpu_type='synthetic')


def test_main_complete_capture_pair_swap_and_three_oracle_layers_no_steer(tmp_path):
    import contextlib
    from projects.g_agreement.e133.runner import main_job
    class Runtime:
        def __init__(self):self.model=Tiny();self.tok=Tok();self.calls=[]
        def subject(self):return self.model,self.tok,contextlib.nullcontext()
        def load_oracle(self):self.calls.append('setup')
        def sweep(self,reader,h,L):
            assert reader=='oracle'and L in (44,52,60)and h.shape[1]==4
            self.calls.append(L);return [dict(text='synthetic',raw='synthetic')for _ in h]
    xs=[item(k,f,pair=f)for f in ('multi_hop','one_hop')for k in (0,1)]
    for x in xs:x['ids'][0]+=x['member']
    rt=Runtime();model=rt.model
    assert main_job(rt,xs,tmp_path/'main',lambda*a:True,gpu_type='synthetic')=='COMPLETE'
    ix=json.loads((tmp_path/'main/INDEX.json').read_text())
    assert sum(x['kind']=='capture_answer'for x in ix)==4
    assert sum(x['kind']=='oracle'for x in ix)==12
    assert sum(x['kind']=='patch'for x in ix)==42
    assert rt.calls.count('setup')==1 and set(rt.calls[1:])=={44,52,60}
    assert all(not b._forward_hooks for b in model.layers)
    assert all(x['block']in(44,52)for x in ix if x['kind']=='patch'and x['id'].startswith('one_hop'))
