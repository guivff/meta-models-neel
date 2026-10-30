import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('native110', Path(__file__).with_name('e110_native_reader227.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def items(n=70):
    return [dict(id=str(i), prompt='public', input_ids=[1, 2], read_position=1) for i in range(n)]


class Tiny:
    def __init__(self):
        self.calls = []
    def sync(self): pass
    def seed(self, value): assert value == 20261029
    def load_oracle(self): self.calls.append('oracle_setup')
    def load_nla(self): self.calls.append('nla_setup')
    def capture_joint(self, xs):
        assert 'nla_setup' not in self.calls
        self.calls.append('capture')
        return {k: np.full((len(xs), 5120), k, np.float32) for k in (44, 42)}
    def native(self, reader, acts, sampled):
        assert sampled is False
        if reader == 'oracle': assert np.all(acts == 44)
        else: assert np.all(acts == 42) or np.all(acts == 0)
        self.calls.append(reader)
        return [[dict(raw='synthetic', text='synthetic')] for _ in acts]


def args(tmp_path, rate=20):
    p = tmp_path / 'inputs.json'; p.write_text(json.dumps(items()))
    t = tmp_path / 'timings.json'
    t.write_text(json.dumps([dict(phase=n, seconds=rate) for n in ['oracle_native', 'nla_native', 'nla_setup', 'nla_warmup_discarded']]))
    s = time.time() - 1
    a = tmp_path / 'assignment.json'
    a.write_text(json.dumps(dict(experiment='E110_READERS', gpu_type='H200', selected_count=70,
        pod_created_epoch=s, absolute_deadline_epoch=s + 5400, cap_seconds=5400,
        selection_seal_sha256='selection', inventory_seal_sha256='inventory')))
    return SimpleNamespace(inputs=p, timings=t, assignment=a, out=tmp_path/'out', input_sha256=m.sha(p),
        timings_sha256=m.sha(t), selection_sha256='selection', inventory_sha256='inventory',
        source_sha256='synthetic', synthetic=True)


def test_complete_full_grid_original_sites_and_order(tmp_path):
    a=args(tmp_path); b=Tiny(); assert m.run(a,b)=='COMPLETE'
    s=m.read(a.out/'OUTPUT_SEAL.json')
    assert s['native_counts']==dict(oracle=70,nla=70) and s['capture_count']==70
    assert s['reader_blocks']==dict(oracle=44,nla=42) and s['labels_cpu_only'] is True
    assert max(i for i,x in enumerate(b.calls) if x=='capture') < b.calls.index('oracle')
    assert max(i for i,x in enumerate(b.calls) if x=='oracle') < b.calls.index('nla_setup')
    for n,h in s['files'].items(): assert m.sha(a.out/n)==h


@pytest.mark.parametrize('change',[lambda xs:xs.pop(), lambda xs:xs[0].update(id=xs[1]['id']),
    lambda xs:xs[0].update(truth='private'), lambda xs:xs[0].update(read_position=0)])
def test_public_input_and_complete_scope_contract(change):
    xs=items(60);change(xs)
    with pytest.raises(ValueError):m.validate(xs)


def test_all_original_survivors_can_be_bound():
    assert len(m.validate(items(3000)))==3000
    with pytest.raises(ValueError):m.validate(items(3001))


def test_registered_cap_and_margin_no_borrowing():
    assert m.fit(300,[(10,20)],5400)['need_seconds']==610
    assert m.fit(300,[(300,20)],5400)['status']=='NO_FIT'
    with pytest.raises(ValueError):m.fit(1,[(1,1)],5401)


def test_nofit_seals_partial_not_eligible_complete(tmp_path):
    a=args(tmp_path,rate=10000);assert m.run(a,Tiny())=='NO_FIT'
    s=m.read(a.out/'OUTPUT_SEAL.json');assert s['status']=='NO_FIT' and s['native_counts']==dict(oracle=0,nla=0)
    assert s['partials_excluded_if_not_complete'] is True


def test_capture_nonfinite_fatal(tmp_path):
    a=args(tmp_path);b=Tiny();original=b.capture_joint
    def broken(xs):
        out=original(xs);out[44][0,0]=np.nan;return out
    b.capture_joint=broken
    with pytest.raises(ValueError):m.run(a,b)


def test_no_gpu_type_substitution(tmp_path):
    a=args(tmp_path);x=m.read(a.assignment);x['gpu_type']='H100';a.assignment.write_text(json.dumps(x))
    with pytest.raises(ValueError):m.run(a,Tiny())
