import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np,torch,pytest
from projects.g_agreement.e127.test_runner import Tiny,Tok,item
from projects.g_agreement.e131.runner import generate_batch,batches,acquire,load,CONDITIONS
from projects.g_agreement.e100.contract import sha


def cell(condition='unhooked'):
    x=item();return dict(x,condition=condition,delta_index=0 if condition.startswith(('e104_','e128_'))else None)


@pytest.mark.parametrize('condition',CONDITIONS)
def test_all_ten_conditions_64_tokens_fixed_original_U_sites_same_pass_pairs(condition):
    m=Tiny();x=cell(condition);d=np.array([[.2,-.4,.1,.3]],np.float32);before=d.copy()
    r=generate_batch(m,Tok(),[x],d)[0]
    assert len(r['token_ids'])==64 and m.calls==64 and r['stop_reason']=='length'
    assert r['greedy_max_new_tokens']==64 and np.array_equal(before,d)
    first=m.snapshots[0][63][0,-1];z=torch.cat([first]*8);lp=z.log_softmax(-1)
    assert r['pair_logits']==[[float(z[3]),float(z[4])]]
    assert np.allclose(r['pair_logprobs'],[[float(lp[3]),float(lp[4])]])
    assert r['pair_mean_a_minus_b']==pytest.approx(float(lp[3]-lp[4]))
    # Every call reuses ORIGINAL positions; read and every generated site unpatched.
    for s in m.snapshots:
        baseline=m.emb(torch.tensor([x['ids']+r['token_ids'][:s[40].shape[1]-len(x['ids'])]])).detach()[0]
        delta=s[40][0]-baseline
        expected=torch.zeros_like(delta)
        if x['delta_index']is not None:expected[3:11]=torch.from_numpy(d).expand(8,4)
        assert torch.allclose(delta,expected,atol=1e-6)
    assert all(not layer._forward_hooks for layer in m.layers)


def test_eos_retained_and_no_extra_forward_or_text_padding():
    m=Tiny();tok=Tok();tok.eos_token_id=3
    def f(**kwargs):
        m.calls+=1;z=torch.full((1,1,32),-10.);z[:,:,3]=10.;return SimpleNamespace(logits=z)
    m.forward=f
    r=generate_batch(m,tok,[cell()],np.zeros((1,4),np.float32))[0]
    assert r['token_ids']==[3]and r['stop_reason']=='eos'and m.calls==1


def test_hook_cleanup_on_generation_failure():
    m=Tiny();m.fail_call=2
    with pytest.raises(RuntimeError):generate_batch(m,Tok(),[cell('e104_steered_8')],np.ones((1,4),np.float32))
    assert all(not layer._forward_hooks for layer in m.layers)


def test_fresh_attempt_and_operator_no_fit_never_reuses_partial(tmp_path):
    p=tmp_path/'attempt';m=Tiny()
    assert acquire(m,Tok(),[cell()],np.zeros((1,4)),p,lambda *a:False,gpu_type='synthetic')=='NO_FIT'
    assert m.calls==0 and json.loads((p/'OUTPUT_SEAL.json').read_text())['cells']==0
    with pytest.raises(FileExistsError):acquire(m,Tok(),[cell()],np.zeros((1,4)),p,lambda *a:True,gpu_type='synthetic')


def test_original_packet_full840_and_byte_identical_sealed_hook_inputs():
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e131-inputs-v1/inputs');xs,d=load(root,sha(root/'INPUT_SEAL.json'))
    assert len(xs)==840 and sum(map(len,batches(xs)))==840
    cpu=root.parent/'cpu_only';ptr=json.loads((cpu/'SOURCE_POINTERS.PRIVATE.json').read_text())
    sources=json.loads((root/'MANIFEST.json').read_text())['source_inputs']
    pools={s['experiment']:{x['id']:x for x in json.loads((Path(s['root'])/'items.json').read_text())}for s in sources}
    vectors={s['experiment']:np.load(Path(s['root'])/'deltas.npy',allow_pickle=False)for s in sources if s['experiment']!='E127'}
    for x,p in zip(xs,ptr):
        o=pools[p['source']][p['source_id']]
        assert (x['ids'],x['read_index'],x['candidate_ids'])==(o['ids'],o['read_index'],o['candidate_ids'])
        if x['delta_index']is not None:assert np.array_equal(d[x['delta_index']],vectors[p['source']][o['delta_index']])
    assert all(not {'label','old_value','new_value','target'}&set(x)for x in xs)
    by={x['base_id']:{}for x in xs}
    for x in xs:by[x['base_id']][x['condition']]=x
    for g in by.values():assert g['unhooked']['ids']==g['none']['ids']and g['unhooked']['candidate_ids']==g['none']['candidate_ids']
