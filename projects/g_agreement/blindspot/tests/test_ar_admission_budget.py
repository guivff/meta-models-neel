"""12:35 admission only; no models or scientific-function changes."""
import ast
import subprocess
import pytest
from projects.g_agreement.blindspot import ar_tests as AR,protocol as P


def assignment(stage,forecast=2400,budget=3600,setup=1500):
    return {'issuer':'integrator','pod_id':'test-pod','brief_registered':True,'brief_pushed':True,
        'source_commit':'a'*40,'brief_commit':'b'*40,'brief_sha256':P.sha(P.ROOT/AR.BRIEF),
        'source_files':AR.mechanism_source_hashes(),'mechanism_budget':stage,'gpu_count':1,
        'provider_created_epoch':1000,'deadline_epoch':1000+setup+budget,
        'allocated_gpu_seconds':budget,'previous_gpu_seconds':0,'setup_allowance_seconds':setup,
        'smoke_forecast_seconds':forecast,'external_hardstop_verified':True}


@pytest.mark.parametrize('forecast,budget',[(2400,3600),(4800,7200),(6000,7200)])
def test_science_forecast_budget_and_separate_setup_are_admitted(tmp_path,forecast,budget):
    stage='residual'
    a=assignment(stage,forecast,budget);path=tmp_path/'assignment.json';P.dump(path,a)
    assert AR.admit_mechanism(path,stage,now=1100,pod_id='test-pod')==a


@pytest.mark.parametrize('change',[
    {'allocated_gpu_seconds':3601},{'previous_gpu_seconds':1},{'allocated_gpu_seconds':7201},
    {'setup_allowance_seconds':1501},{'setup_allowance_seconds':-1},
    {'smoke_forecast_seconds':float('nan')},{'smoke_forecast_seconds':0},{'smoke_forecast_seconds':7201},
    {'deadline_epoch':6101},
])
def test_bad_forecast_setup_or_science_bound_is_rejected(tmp_path,change):
    a=assignment('residual');a.update(change);path=tmp_path/'assignment.json'
    # JSON nan deliberately probes the admission finite-value check.
    import json
    path.write_text(json.dumps(a))
    with pytest.raises(ValueError):AR.admit_mechanism(path,'residual',now=1100,pod_id='test-pod')


def test_w4_keeps_1800_science_seconds_with_separate_setup(tmp_path):
    path=tmp_path/'assignment.json';a=assignment('swap',budget=1800);a.pop('smoke_forecast_seconds');P.dump(path,a)
    assert AR.admit_mechanism(path,'swap',now=1100,pod_id='test-pod')==a
    a['allocated_gpu_seconds']=1801;P.dump(path,a)
    with pytest.raises(ValueError):AR.admit_mechanism(path,'swap',now=1100,pod_id='test-pod')


def test_all_scientific_ast_nodes_match_exact_p3_approved_source():
    baseline=subprocess.check_output(['git','show','0718261d:projects/g_agreement/blindspot/ar_tests.py'],cwd=P.ROOT,text=True)
    def science(source):
        tree=ast.parse(source)
        tree.body=[node for node in tree.body if not (
            isinstance(node,ast.FunctionDef) and node.name=='admit_mechanism' or
            isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CAP_HOURS' for t in node.targets))]
        return ast.dump(tree,include_attributes=False)
    assert science(baseline)==science(open(AR.__file__).read())


def test_w4_can_follow_w3_on_same_pod_without_recharging_setup(tmp_path):
    path=tmp_path/'assignment.json';a=assignment('swap',budget=1800,setup=0)
    a['phase_started_epoch']=8000;a['deadline_epoch']=9800
    P.dump(path,a)
    assert AR.admit_mechanism(path,'swap',now=8100,pod_id='test-pod')==a
    a['setup_allowance_seconds']=1500;P.dump(path,a)
    with pytest.raises(ValueError,match='repeated setup'):
        AR.admit_mechanism(path,'swap',now=8100,pod_id='test-pod')


@pytest.mark.parametrize('budget',[1,1000,1080])
def test_fidelity_accepts_unchanged_cap_without_smoke_forecast(tmp_path,budget):
    a=assignment('fidelity',budget=budget);a.pop('smoke_forecast_seconds')
    path=tmp_path/'assignment.json';P.dump(path,a)
    assert AR.admit_mechanism(path,'fidelity',now=1100,pod_id='test-pod')==a


@pytest.mark.parametrize('budget,previous',[(1081,0),(1080,1)])
def test_fidelity_rejects_above_1080_total_science_seconds(tmp_path,budget,previous):
    a=assignment('fidelity',budget=budget);a.pop('smoke_forecast_seconds');a['previous_gpu_seconds']=previous
    path=tmp_path/'assignment.json';P.dump(path,a)
    with pytest.raises(ValueError,match='cumulative allocation'):
        AR.admit_mechanism(path,'fidelity',now=1100,pod_id='test-pod')
