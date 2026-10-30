import importlib.util
from pathlib import Path
import copy
import time
import numpy as np
import pytest

HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
audit=module('audit_delivery',HERE.parent/'e79/audit_delivery.py')
smoke=module('reconstructor_smoke',HERE/'reconstructor_smoke.py')

def fixture():
    contract=audit.read(HERE.parent/'e79/cpu_scorer/INPUT_CONTRACT.json')
    ids={row:{f'{row}-{i}' for i in range(84)} for row in contract['candidate_token_ids']}
    records=[dict(id=i,feature=row,condition=c,pair_logits=[[1.0,2.0]]*len(contract['candidate_token_ids'][row]))
             for row,items in ids.items() for i in sorted(items) for c in contract['conditions']]
    return contract,ids,dict(schema=contract['schema'],candidate_token_ids=copy.deepcopy(contract['candidate_token_ids']),records=records)

def test_exact_grid_and_unchanged_candidates():
    c,ids,d=fixture();assert sum(audit.validate(d,c,ids).values())==672
    d['candidate_token_ids']['format_plan'][0].reverse()
    with pytest.raises(ValueError,match='candidate'):audit.validate(d,c,ids)

@pytest.mark.parametrize('kind',['duplicate','missing','nan','wrong_pair_count'])
def test_invalid_records_fail(kind):
    c,ids,d=fixture()
    if kind=='duplicate':d['records'][1]=d['records'][0]
    elif kind=='missing':d['records'].pop()
    elif kind=='nan':d['records'][0]['pair_logits']=[[float('nan'),1]]
    else:d['records'][0]['pair_logits']=[]
    with pytest.raises(ValueError):audit.validate(d,c,ids)

def test_smoke_stage_paths_and_nonfinite_guard(tmp_path):
    result=smoke.execute({'id':'one','text':'Public sealed input.'},smoke.StubBackend(),tmp_path/'out',time.time()+30,True)
    assert result['status']=='CPU_STUB_ONLY'
    assert [x['reader'] for x in smoke.read(tmp_path/'out/PHASE_TIMINGS.json')]==['oracle','nla']
    with pytest.raises(ValueError):smoke.check_vector(np.full((1,5120),np.nan))
    with pytest.raises(ValueError):smoke.check_vector(np.ones((5120,)))

def test_failed_first_head_never_runs_second(tmp_path):
    class Broken:
        def oracle(self,text):raise RuntimeError('load failed')
        def nla(self,text):raise AssertionError('must not run')
    with pytest.raises(RuntimeError):smoke.execute({'id':'one','text':'Public.'},Broken(),tmp_path/'out',time.time()+30)
    assert smoke.read(tmp_path/'out/PHASE_TIMINGS.json')[0]['status']=='FAILED'
