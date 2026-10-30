import time
import numpy as np
import pytest
import worker87 as W
from test_worker87 import Tiny87


def fixture(rows=(0, 1), nla_placebo=True):
    roster = [dict(row_index=r, test_count=n,
                   item_ids=[f'synthetic-{r}-{i}' for i in range(min(30, n))], nla_norm=3., nla_norm_seal_sha256='b'*64, placebo_positions=[8]*15,reuse_e87=False)
              for r, n in enumerate((84, 17))]
    items = [dict(id=ident, global_index=r*30+i, ids=[1]*16, read_index=15, reuse44=False)
             for r in rows for i, ident in enumerate(roster[r]['item_ids'])]
    plan = dict(experiment='E95', layers=[20,36,44,56], oracle_positions=8, nla_positions=8,
                seed=W.SEED, row_roster=roster, row_indices=list(rows), shard=0,
                item_ids=[x['id'] for x in items], short_positions='available', reduction_step=0, mode='remaining',
                nla_placebo=nla_placebo, scope_authority='1b0a2fcfc50d8d57d97a2f3cd84f8f88ca4e4a85')
    return items, plan


def test_scope_and_fail_closed_short_prompt():
    xs, p = fixture(); assert len(W.validate(xs, p)) == 47
    xs[0]['ids'] = [1]*12; xs[0]['read_index'] = 11
    W.validate(xs,p)
    xs, p = fixture(); p['row_roster'][0]['item_ids'].reverse()
    with pytest.raises(ValueError, match='frozen'): W.validate(xs, p)


@pytest.mark.parametrize('nla_placebo', [True])
def test_same_engine_independent_placebo_grid(tmp_path, monkeypatch, nla_placebo):
    monkeypatch.setattr(W, 'DIM', 8)
    xs, p = fixture((1,), nla_placebo); W.validate(xs, p)
    out = tmp_path/'out'; out.mkdir(); backend = Tiny87()
    c = W.Clock(out, time.time()+3600, {k: 0 for k in
        ('oracle_setup','capture','placebo_build','oracle_native','nla_setup','nla_native')}, backend)
    W.acquire(tmp_path, xs, p, backend, c, out, dict(experiment='E95'))
    assert W.read(out/'COUNTS.json') == dict(oracle=(17+15)*8*4,
                                           nla=(17+15)*8)
    assert len(W.read(out/'capture/PLACEBO_ITEMS.json')) == 15
    assert len(np.load(out/'capture/placebo56.npy')) == 15
    assert len(np.load(out/'capture/grid56.npy')) == 17


def test_whole_row_sharding_and_optional_nla_keep_oracle_stream(tmp_path, monkeypatch):
    from scope95 import placebo95
    monkeypatch.setattr(W, 'DIM', 8)
    xs, p = fixture(nla_placebo=True); ys, q = fixture((1,), True)
    real = {l: np.random.default_rng(l).standard_normal((47,16,8)).astype(np.float32)
            for l in W.CAPTURE_LAYERS}
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    full=placebo95(real,xs,p,a,p['layers'],8,W.norm_match)
    part=placebo95({l:h[30:] for l,h in real.items()},ys,q,b,q['layers'],8,W.norm_match)
    for l in p['layers']:
        assert np.array_equal(full[l][15:], part[l])


def test_reused_rows_only_generate_nla_placebo(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'DIM',8)
    xs,p=fixture((1,));p['row_roster'][1]['reuse_e87']=True;p['mode']='nla_placebo_only'
    W.validate(xs,p);out=tmp_path/'reuse';out.mkdir();b=Tiny87()
    c=W.Clock(out,time.time()+3600,{k:0 for k in ('oracle_setup','nla_setup','placebo_build','nla_native')},b)
    W.acquire(tmp_path,xs,p,b,c,out,dict(experiment='E95'))
    assert W.read(out/'COUNTS.json')==dict(oracle=0,nla=120,real_readouts=0)
    assert not any(isinstance(x,tuple) and x[0]=='capture' for x in b.calls)
    assert not any(isinstance(x,tuple) and x[0]=='read' and x[1]=='oracle' for x in b.calls)
    p['mode']='remaining'
    with pytest.raises(ValueError,match='never rerun'):W.validate(xs,p)
