import contextlib,json,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101.intervention104 import intervene_forward,behaviour104,write_positions,NORM_CONVENTION
from projects.g_agreement.e101.contract104 import DOSES,SEED,validate,select,validate_doses
from projects.g_agreement.e101.materialize104 import compose

class Layer(torch.nn.Module):
    def __init__(self,index):super().__init__();self.index=index
    def forward(self,x):
        z=x+.02*torch.cumsum(x,dim=1) if self.index==41 else x
        return (z,'retained-metadata') if self.index in (40,44) else z

class Tiny104(torch.nn.Module):
    def __init__(self,fail_call=None):
        super().__init__();torch.manual_seed(9);self.emb=torch.nn.Embedding(32,4);self.layers=torch.nn.ModuleList([Layer(i) for i in range(46)])
        self.config=SimpleNamespace(num_hidden_layers=46);self.calls=0;self.snapshots=[];self.fail_call=fail_call
    def get_input_embeddings(self):return self.emb
    def forward(self,input_ids,attention_mask,use_cache,logits_to_keep):
        assert not use_cache and attention_mask.eq(1).all();self.calls+=1;x=self.emb(input_ids);states={}
        for i,layer in enumerate(self.layers):
            x=layer(x);x=x[0] if isinstance(x,tuple) else x;states[i]=x.detach().clone()
            if self.calls==self.fail_call and i==45:raise RuntimeError('synthetic failure after intervention')
        self.snapshots.append(states)
        return SimpleNamespace(logits=torch.cat([x]*8,dim=-1)[:,-logits_to_keep:])


def item(arm='N',**kwargs):
    x=dict(id='opaque',base_id='base',row='fact_recall',arm=arm,block=44 if arm=='N' else 40,ids=[1,2,3,4,5,6,7,8,9,10],read_index=9,candidate_ids=[[[3],[4]]])
    return dict(x,**kwargs)


def test_N_formula_preserves_live_norm_for_steered_and_random_at_all_doses():
    for alpha in DOSES['N']:
        for unit in (np.array([1.,0,0,0]),np.array([0.,1,0,0])):
            m=Tiny104();delta=(alpha*2*unit)[None]
            _,metrics,read=intervene_forward(m,[item()['ids']],[9],delta,'N',1)
            natural=m.snapshots[0][43][0,9].numpy();expected=natural+delta[0];expected*=np.linalg.norm(natural)/np.linalg.norm(expected)
            assert np.allclose(read[0],expected,atol=1e-6)
            assert metrics[0]['norm_ratio']==pytest.approx(1.,abs=1e-6)
            assert metrics[0]['read_norm_ratio']==pytest.approx(1.,abs=1e-6)
            assert metrics[0]['injection_sites'][0]['position']==9
            assert all(not x._forward_hooks for x in m.layers)


def test_U_changes_only_eight_previous_positions_and_propagates_to_unpatched_read():
    m=Tiny104();delta=np.array([[1.,-.3,.2,.5]],np.float32)
    _,metrics,read=intervene_forward(m,[item('U')['ids']],[9],delta,'U',1)
    baseline,patched=m.snapshots
    difference=(patched[40]-baseline[40]).numpy()[0]
    assert np.allclose(difference[1:9],delta[0],atol=1e-6)
    assert np.array_equal(difference[[0,9]],np.zeros((2,4)))
    assert not np.allclose(read[0],baseline[44][0,9].numpy())
    assert [x['position'] for x in metrics[0]['injection_sites']]==list(range(1,9))
    assert metrics[0]['read_site']['position']==9 and metrics[0]['read_site']['block']==44
    assert metrics[0]['norm_ratio']!=pytest.approx(metrics[0]['read_norm_ratio'])
    before=np.linalg.norm(baseline[40][0,1:9].numpy());after=np.linalg.norm(patched[40][0,1:9].numpy())
    assert metrics[0]['norm_ratio']==pytest.approx(after/before)
    assert all(not x._forward_hooks for x in m.layers)


def test_behaviour_wrapper_uses_U_hook_for_prefix_and_continuation_not_read_token_patch():
    m=Tiny104();x=item('U',candidate_ids=[[[3],[3,4]]]);delta=np.ones((1,4),np.float32)
    records,vectors=behaviour104(m,[x],delta)
    assert 'pair_logits' in records[0] and 'pair_logprobs' in records[0] and vectors.shape==(1,4)
    # One natural prefix, one intervened prefix, then candidate forwards.
    assert m.calls==4
    natural_read=m.snapshots[0][40][0,9]
    assert all(torch.equal(s[40][0,9],natural_read) for s in m.snapshots)
    assert all(not b._forward_hooks for b in m.layers)


@pytest.mark.parametrize('arm,fail_call',[('N',1),('U',1),('U',2)])
def test_hooks_removed_on_crash(arm,fail_call):
    m=Tiny104(fail_call=fail_call)
    with pytest.raises(RuntimeError):intervene_forward(m,[item(arm)['ids']],[9],np.ones((1,4)),arm,1)
    assert all(not b._forward_hooks for b in m.layers)


def test_reject_short_U_nonfinite_and_zero_N_without_leaking_hooks():
    m=Tiny104()
    with pytest.raises(ValueError,match='eight existing'):intervene_forward(m,[[1]*8],[7],np.ones((1,4)),'U',1)
    with pytest.raises(ValueError):intervene_forward(m,[[1]*10],[9],np.full((1,4),np.nan),'N',1)
    m(input_ids=torch.tensor([item()['ids']]),attention_mask=torch.ones((1,10)),use_cache=False,logits_to_keep=1)
    natural=m.snapshots[-1][44][0,9].numpy()
    with pytest.raises(ValueError,match='zero vector'):intervene_forward(m,[item()['ids']],[9],-natural[None],'N',1)
    assert all(not b._forward_hooks for b in m.layers)


def records(stage='dev'):
    return [dict(id=f'{r}-{i}',row=r,split=stage,ids=[1]*10,candidate_ids=[[[3],[4]]],label=i%2,contrast_target_sign=1-2*(i%2)) for r in ('fact_recall','language_plan') for i in range(84)]


def manifest(items,stage='dev',selected=None):
    return dict(experiment='E104',stage=stage,seed=SEED,dev_count=84,dose_grids={a:list(v) for a,v in DOSES.items()},dose_score_field='pair_logits',scoring_mode='continuation',selected_doses=selected,
        cells=[dict(arm=a,row=r) for a,r in sorted({(x['arm'],x['row']) for x in items})],behaviour_scorer_sha256='synthetic',norm_convention=NORM_CONVENTION,
        U_hook=dict(block=40,positions='eight_before_read',read_token_untouched=True),N_hook=dict(block=44,positions='read_token',renormalized=True,random_renormalized=True))


def directions():return {r:np.array([1.,0,0,0]) for r in ('fact_recall','language_plan')}


def test_composition_full_arm_grids_random_norm_seed_and_public_fields():
    for arm,total in [('N',1344),('U',1680)]:
        xs,d,key=compose(records(),directions(),{r:2. for r in directions()},arm,'dev')
        validate(xs,d,manifest(xs),4);assert len(xs)==total
        assert set(x['alpha'] for x in xs)==set(DOSES[arm])
        assert all('label' not in x and 'contrast_target_sign' not in x for x in xs)
        for i in range(0,len(xs),2):assert np.linalg.norm(d[i])==pytest.approx(np.linalg.norm(d[i+1]),rel=1e-6)
        assert np.array_equal(d,compose(records(),directions(),{r:2. for r in directions()},arm,'dev')[1])
        bad=[dict(x) for x in xs];bad[0]['alpha']=8 if arm=='N' else 16
        with pytest.raises(ValueError,match='intervention'):validate(bad,d,manifest(xs),4)
        bad=[dict(x) for x in xs];bad[0]['write_positions']=[9]
        if arm=='U':
            with pytest.raises(ValueError,match='write sites'):validate(bad,d,manifest(xs),4)


def test_independent_doses_U_can_choose_eight_and_random_does_not_choose():
    all_items=[];rr=[];key={}
    for arm in DOSES:
        xs,_,kk=compose(records(),directions(),{r:2. for r in directions()},arm,'dev');all_items.extend(xs);key.update(kk)
        for x in xs:
            passing=x['alpha']>=(1 if arm=='N' else 8) and int(x['base_id'].split('-')[-1])<59
            score=key[x['base_id']]['contrast_target_sign']*(1 if passing or x['condition']=='random' else -1)
            rr.append(dict(id=x['id'],pair_logits=[[score,0.]]))
    ds=select(all_items,rr,key);validate_doses(ds)
    assert ds['N:fact_recall']['alpha']==1 and ds['U:fact_recall']['alpha']==8
    with pytest.raises(ValueError):select(all_items,rr[:-1],key)
    for r in rr:r['pair_logits']=[[0.,0.]]
    assert all(v['alpha'] is None for v in select(all_items,rr,key).values())


def test_partial_dose_receipt_cannot_release_test_materialization(monkeypatch,tmp_path):
    from projects.g_agreement.e101 import materialize104
    monkeypatch.setattr(materialize104,'committed_dose',lambda *a:dict(experiment='E104',dev_count=84,seed=SEED,selected_doses={}))
    with pytest.raises(ValueError,match='all four'):materialize104.build(None,None,None,tmp_path/'must-not-exist','N','test')
    assert not (tmp_path/'must-not-exist').exists()


class FakeRuntime:
    def __init__(self):self.base=Tiny104();self.readers=self;self.loaded=[];self.native=[];self.hardware_assignment={'gpu_type':'CPU_SYNTHETIC'}
    def load_base(self):self.loaded.append('base')
    def load_oracle(self):self.loaded.append('oracle')
    def subject(self):return self.base,None,contextlib.nullcontext()
    def native_one(self,reader,h):
        assert reader=='oracle';self.native.append(np.array(h,copy=True));return [[dict(text='oracle',raw='oracle',malformed=False)] for _ in h]


def test_runner_full_native_grid_and_timing_capture_alignment(tmp_path):
    from projects.g_agreement.e101.runner import dependencies
    from projects.g_agreement.e101.runner104 import acquire,jobs
    old,_,_,_,_=dependencies()
    selected={f'{a}:{r}':dict(alpha=1.,target_side_counts={str(d):(84 if d>=1 else 0) for d in DOSES[a]}) for a in DOSES for r in directions()}
    xs,d,key=compose(records('test'),directions(),{r:2. for r in directions()},'U','test',selected)
    for timing in (True,False):
        out=tmp_path/str(timing);out.mkdir();runtime=FakeRuntime();m=manifest(xs,'test',selected)
        status=acquire(xs,dict(deltas=d,manifest=m),runtime,old.Clock(out,time.time()+3600),out,timing)
        assert status==('TIMING_ONLY' if timing else 'COMPLETE') and runtime.loaded==['base','oracle']
        if not timing:
            rr=[r for f in (out/'jobs').glob('*.json') for r in json.loads(f.read_text()) if r['channel']=='oracle']
            assert len(rr)==336 and len({r['id'] for r in rr})==336
            assert all(len(r['injection_sites'])==8 and r['read_site']['block']==44 for r in rr)
        else:assert (out/'MEASURED_PROFILE.json').exists()


def test_saved_public_bundle_loads_and_rejects_extra_private_member(tmp_path):
    from projects.g_agreement.e101.materialize104 import save
    from projects.g_agreement.e101.runner104 import load
    from projects.g_agreement.e101.contract import verify,sha
    u=np.zeros(5120);u[0]=1.;ds={r:u for r in directions()}
    xs,d,key=compose(records(),ds,{r:2. for r in ds},'N','dev')
    ix=[i for i,x in enumerate(xs) if x['row']=='fact_recall'];xs=[dict(xs[i],delta_index=j) for j,i in enumerate(ix)]
    out=tmp_path/'public';save(out,xs,d[ix],'dev',dict(synthetic=True))
    verify(out,'INPUT_SEAL.json',sha(out/'INPUT_SEAL.json'));loaded,data=load(out)
    assert len(loaded)==672 and data['deltas'].shape==(672,5120)
    (out/'PRIVATE.json').write_text('{}')
    with pytest.raises(ValueError,match='public'):load(out)


def test_actual_owner_U_vector_layout_and_seed_are_bound(tmp_path):
    from projects.g_agreement.e101.materialize104 import load_u_directions
    from projects.g_agreement.e101.contract import read,write,sha
    root=Path(__file__).resolve().parents[3];request=read(root/'results/g_agreement/understand/e104/vectors/REQUEST.json')
    norms={r:2. for r in directions()};u=np.zeros(5120);u[0]=1.
    for r in directions():np.save(tmp_path/(r+'.unit_d40.npy'),u);np.save(tmp_path/(r+'.d40.npy'),2*u)
    rng=np.random.default_rng(np.random.SeedSequence([SEED,40]));random=rng.standard_normal(5120);random/=np.linalg.norm(random);np.save(tmp_path/'random40.npy',random)
    write(tmp_path/'NORMS.json',norms)
    meta=dict(experiment='E104',status='COMPLETE',block=40,fit_split='dev',class_count=42,orientation='mean(label1)-mean(label0)',capture_sha256='0'*64,input_sha256=request['public_input_sha256'],random_seed=SEED)
    write(tmp_path/'VECTOR_SEAL.json',dict(meta,files={p.name:sha(p) for p in tmp_path.iterdir()}))
    ds,ns,rr,pins=load_u_directions(tmp_path,sha(tmp_path/'VECTOR_SEAL.json'))
    xs,d,key=compose(records(),ds,ns,'U','dev',random_unit=rr)
    assert len(xs)==1680 and all(p['block']==40 for p in pins)
    with pytest.raises(ValueError,match='seed'):compose(records(),ds,ns,'U','dev',random_unit=-rr)
    seal=read(tmp_path/'VECTOR_SEAL.json');seal['input_sha256']='unrelated';(tmp_path/'VECTOR_SEAL.json').unlink();write(tmp_path/'VECTOR_SEAL.json',seal)
    with pytest.raises(ValueError,match='same frozen'):load_u_directions(tmp_path,sha(tmp_path/'VECTOR_SEAL.json'))
