"""Offline regression tests for cumulative caps and immutable output seals."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

from projects.g_agreement.understand import budget as B, run as R
from projects.g_agreement.understand import request as Q
from projects.g_agreement.blindspot import protocol as P


def receipt(units=10, timings=(1., 2., 9.)):
    return dict(warmups=1, timings_seconds=list(timings), units=units,
                forecast_seconds=B.forecast(timings, units))


def assignment(tmp_path, monkeypatch, experiment='E3', **changes):
    monkeypatch.setattr(B, 'source_hashes', lambda: {'source.py': '0'*64})
    a = dict(experiment=experiment, gpu_count=1, pod_id='integrator-assigned-pod',
             external_hard_stop_verified=True, setup_allowance_seconds=1500.,
             max_science_seconds=2160., source_files={'source.py': '0'*64},
             input_seals={'primary': '1'*64},
             hard_deadline_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
    a.update(changes)
    path = tmp_path/'assignment.json'; P.dump(path, a)
    return path


def ledger(tmp_path, monkeypatch, **changes):
    a = assignment(tmp_path, monkeypatch, **changes)
    return B.Ledger(a, tmp_path/'state', 'E3', {'primary': '1'*64})


def test_warmed_median_and_science_forecast_admission():
    assert B.forecast([1., 9., 2.], 10) == 20
    receipts = {p: receipt() for p in B.PHASES['E3']}
    gate = B.admit_forecast(receipts, B.PHASES['E3'], 40)
    assert gate['forecast_seconds'] == 60
    assert gate['science_cap_seconds'] == 450
    assert gate['admitted']
    assert not B.admit_forecast(receipts, B.PHASES['E3'], 391)['admitted']
    expensive = {p: receipt(1000, (1., 1., 1.)) for p in B.PHASES['E3']}
    gate = B.admit_forecast(expensive, B.PHASES['E3'], 0)
    assert gate['science_cap_seconds'] == 2160
    assert not gate['admitted']


@pytest.mark.parametrize('timings,units', [([1., 2.], 2), ([1., 2., float('nan')], 2),
                                         ([1., -2., 3.], 2), ([1., 2., 3.], 0),
                                         ([1., 2., 3.], True)])
def test_warmed_forecast_rejects_invalid_measurements(timings, units):
    with pytest.raises(ValueError):
        B.forecast(timings, units)


def test_gate_requires_all_phases_and_exact_receipt():
    phases = B.PHASES['E4']
    receipts = {p: receipt() for p in phases[:-1]}
    with pytest.raises(ValueError, match='all reader/target'):
        B.admit_forecast(receipts, phases, 0)
    receipts['target'] = receipt()
    receipts['target']['forecast_seconds'] += 1
    with pytest.raises(ValueError, match='forecast does not match'):
        B.admit_forecast(receipts, phases, 0)
    receipts['target'] = receipt(); receipts['target']['warmups'] = 0
    with pytest.raises(ValueError, match='unscored warm-up'):
        B.admit_forecast(receipts, phases, 0)


@pytest.mark.parametrize('changes', [dict(gpu_count=2), dict(max_science_seconds=2161),
                                     dict(setup_allowance_seconds=1501),
                                     dict(external_hard_stop_verified=False),
                                     dict(source_files={'source.py': '2'*64}),
                                     dict(input_seals={'primary': '3'*64})])
def test_assignment_rejects_changed_authority(tmp_path, monkeypatch, changes):
    with pytest.raises(ValueError, match='assignment'):
        ledger(tmp_path, monkeypatch, **changes)


def test_source_hashes_cover_reader_and_brief():
    hashes = B.source_hashes()
    assert 'projects/g_agreement/BRIEF_UNDERSTAND.md' in hashes
    assert 'projects/g_agreement/understand/run.py' in hashes
    assert 'external/mats-nla-workspace/src/mats/readers/olens.py' in hashes
    assert 'external/mats-nla-workspace/src/mats/readers/nla.py' in hashes
    assert 'external/mats-nla-workspace/src/mats/readers/jlens.py' in hashes


def test_charges_persist_across_processes_and_exceptions(tmp_path, monkeypatch):
    l = ledger(tmp_path, monkeypatch)
    ticks = iter([0., 12., 20., 27.])
    monkeypatch.setattr(B.time, 'monotonic', lambda: next(ticks))
    with l.charge('olens', 'setup'):
        pass
    with pytest.raises(RuntimeError, match='model failure'):
        with l.charge('olens', 'science'):
            raise RuntimeError('model failure')
    assert l.state['setup_seconds'] == 12
    assert l.state['science_seconds'] == 7
    assert l.state['active'] is None
    l.close()
    l = B.Ledger(tmp_path/'assignment.json', tmp_path/'state', 'E3', {'primary': '1'*64})
    try:
        assert l.state['setup_seconds'] == 12
        assert l.state['science_seconds'] == 7
    finally:
        l.close()


def test_exhausted_caps_and_interrupted_state_fail_closed(tmp_path, monkeypatch):
    l = ledger(tmp_path, monkeypatch)
    l.state['science_seconds'] = 2160
    with pytest.raises(TimeoutError):
        with l.charge('olens', 'science'):
            pytest.fail('must not run')
    l.state['setup_seconds'] = 1500
    with pytest.raises(TimeoutError):
        with l.charge('olens', 'setup'):
            pytest.fail('must not load')
    l.state['active'] = {'phase': 'olens', 'kind': 'science'}
    l.save(); l.close()
    with pytest.raises(ValueError, match='interrupted'):
        B.Ledger(tmp_path/'assignment.json', tmp_path/'state', 'E3', {'primary': '1'*64})


def dataset(n=33):
    return {'rows': [{'feature': 'row'}],
            'items': [{'id': str(i), 'feature': 'row', 'ids': [i+1]} for i in range(n)],
            'activations': {42: np.arange(n*3).reshape(n, 3), 44: np.arange(n*3).reshape(n, 3)},
            'templates': {'row': {'olens': [('a', 'b'), ('c', 'd')]}}}


def fake_capture(n, layers=(0, 1)):
    return {'status': 'COMPLETE', 'residuals': np.ones((n, len(layers), 2, 3)),
            'input_stage': np.ones((n, 2, 3)), 'layers': list(layers),
            'positions': ['injection', 'preanswer']}


def test_calibration_runs_one_warmup_three_timed_disk_units(tmp_path, monkeypatch):
    calls = []; digests = []
    def call(rt, d, e, p, f, ix):
        calls.append(list(ix))
        return fake_capture(len(ix))
    sha = P.sha
    def hash_timing(path):
        digests.append(path)
        return sha(path)
    monkeypatch.setattr(R, '_call', call)
    monkeypatch.setattr(R, '_sync', lambda: None)
    monkeypatch.setattr(P, 'sha', hash_timing)
    r = R.calibrate(None, dataset(), 'E3', 'olens', lambda: None, tmp_path)
    assert len(calls) == 4 and all(len(ix) == 32 for ix in calls)
    assert r['warmups'] == 1 and len(r['timings_seconds']) == 3
    assert r['units'] == 2
    assert r['forecast_seconds'] == B.forecast(r['timings_seconds'], 2)
    assert len(digests) == 6  # residuals and input stage in each timed unit
    assert not list(tmp_path.iterdir())  # no smoke predictions survive to analysis


def test_collect_preserves_all_items_and_hashes(tmp_path, monkeypatch):
    monkeypatch.setattr(R, '_call', lambda rt, d, e, p, f, ix: fake_capture(len(ix)))
    index = R.collect(None, dataset(), 'E3', 'olens', tmp_path/'scores', lambda: None)
    row = index[0]
    assert row['status'] == 'COMPLETE' and row['n'] == 33
    assert row['item_ids'] == [str(i) for i in range(33)]
    array = np.load(tmp_path/'scores'/row['arrays']['residuals'])
    assert array.shape == (33, 2, 2, 3)
    for key, name in row['arrays'].items():
        assert row['array_sha256'][key] == P.sha(tmp_path/'scores'/name)


def test_collect_failure_keeps_incomplete_record(tmp_path, monkeypatch):
    def call(rt, d, e, p, f, ix):
        if len(ix) == 1:
            raise RuntimeError('second unit failed')
        return fake_capture(len(ix))
    monkeypatch.setattr(R, '_call', call)
    with pytest.raises(RuntimeError, match='second unit'):
        R.collect(None, dataset(), 'E3', 'olens', tmp_path/'scores', lambda: None)
    index = json.loads((tmp_path/'scores/index.json').read_text())
    assert index[0]['status'] == 'INCOMPLETE'
    assert not (tmp_path/'scores/SCORE_SEAL.json').exists()


def test_collect_rejects_broadcastable_layer_shape_change(tmp_path, monkeypatch):
    monkeypatch.setattr(R, '_call', lambda rt, d, e, p, f, ix:
                        fake_capture(len(ix), layers=(0, 1) if len(ix) > 1 else (0,)))
    with pytest.raises(ValueError):
        R.collect(None, dataset(), 'E3', 'olens', tmp_path/'scores', lambda: None)


def test_seal_repeat_leaves_existing_bytes_untouched(tmp_path):
    inp = tmp_path/'inputs/e3'; inp.mkdir(parents=True)
    P.dump(inp/'INPUT_SEAL.json', {'files': {}})
    out = tmp_path/'output'; out.mkdir()
    a = SimpleNamespace(inputs=tmp_path/'inputs', experiment='E3', out=out, local_after_pull=True)
    R.seal(a)
    original = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    # A late phase must not alter a frozen aggregate receipt on a second seal.
    phase = out/'olens'; phase.mkdir()
    P.dump(phase/'dummy.json', {'new': True})
    P.seal(phase, ['dummy.json'], 'SCORES_SEALED_TEST')
    with pytest.raises(ValueError, match='already exists'):
        R.seal(a)
    assert all((out/name).read_bytes() == content for name, content in original.items())


def seal_fixture(tmp_path, monkeypatch, **provenance_changes):
    inputs = tmp_path/'inputs'; inp = inputs/'e3'; inp.mkdir(parents=True)
    P.dump(inp/'INPUT_SEAL.json', {'files': {}, 'fixture': 'E3'})
    out = tmp_path/'output'; phase = out/'olens'; phase.mkdir(parents=True)
    monkeypatch.setattr(R, 'source_hashes', lambda: {'reader.py': '0'*64})
    provenance = {'experiment': 'E3', 'phase': 'olens',
                  'input_seal_sha256': P.sha(inp/'INPUT_SEAL.json'),
                  'source_files': {'reader.py': '0'*64}}
    provenance.update(provenance_changes)
    P.dump(phase/'provenance.json', provenance)
    P.dump(phase/'index.json', [])
    P.seal(phase, ['provenance.json', 'index.json'], 'SCORES_SEALED_EXPLORATORY_E3')
    return SimpleNamespace(inputs=inputs, out=out, experiment='E3', local_after_pull=True)


@pytest.mark.parametrize('changed', [dict(phase='nla'), dict(experiment='E4'),
                                     dict(input_seal_sha256='3'*64),
                                     dict(source_files={'reader.py': '4'*64})])
def test_aggregate_seal_rejects_wrong_phase_provenance(tmp_path, monkeypatch, changed):
    a = seal_fixture(tmp_path, monkeypatch, **changed)
    with pytest.raises(ValueError, match='phase provenance'):
        R.seal(a)
    assert not (a.out/'SCORE_SEAL.json').exists()
    assert not (a.out/'provenance.json').exists()


def test_production_seal_requires_assignment(tmp_path, monkeypatch):
    a = seal_fixture(tmp_path, monkeypatch)
    (a.out/'budget').mkdir()
    P.dump(a.out/'budget/ledger.json', {'science_seconds': 4})
    a.local_after_pull = False
    with pytest.raises(ValueError, match='assignment'):
        R.seal(a)
    assert not (a.out/'SCORE_SEAL.json').exists()


def test_seal_without_ledger_requires_explicit_local_after_pull(tmp_path, monkeypatch):
    a = seal_fixture(tmp_path, monkeypatch)
    a.local_after_pull = False
    with pytest.raises(ValueError):
        R.seal(a)
    assert not (a.out/'SCORE_SEAL.json').exists()


def test_cpu_after_pull_preserves_and_seals_ledger_snapshot(tmp_path, monkeypatch):
    a = seal_fixture(tmp_path, monkeypatch)
    (a.out/'budget').mkdir()
    pulled = {'science_seconds': 100, 'setup_seconds': 20,
              'active': {'phase': 'nla', 'kind': 'science'}}
    ledger_path = a.out/'budget/ledger.json'; P.dump(ledger_path, pulled)
    before = ledger_path.read_bytes()
    R.seal(a)
    assert ledger_path.read_bytes() == before
    snapshot = json.loads((a.out/'budget.final.json').read_text())
    assert snapshot['sealing'] == 'CPU_ONLY_AFTER_PULL'
    assert snapshot['gpu_resume_authorized'] is False
    assert snapshot['ledger_as_pulled'] == pulled
    seal = P.verify(a.out, 'SCORE_SEAL.json')
    assert seal['files']['budget.final.json'] == P.sha(a.out/'budget.final.json')
    assert 'budget/ledger.json' not in seal['files']
    assert json.loads((a.out/'provenance.json').read_text())['status'] == 'PARTIAL'
    # The snapshot, not the mutable operator ledger, is authoritative evidence.
    P.dump(ledger_path, {'later_operator_reconciliation': True})
    P.verify(a.out, 'SCORE_SEAL.json')


def request_fixture(tmp_path, monkeypatch):
    root = tmp_path/'repo'; root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', 'config', 'user.email', 'offline-test@example.invalid'], cwd=root, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Offline test'], cwd=root, check=True)
    source = root/'source.py'; source.write_text('fixed_source = 1\n')
    brief = root/'projects/g_agreement/BRIEF_UNDERSTAND.md'
    brief.parent.mkdir(parents=True); brief.write_text('Exploratory fixture\n')
    subprocess.run(['git', 'add', 'source.py', 'projects/g_agreement/BRIEF_UNDERSTAND.md'], cwd=root, check=True)
    subprocess.run(['git', 'commit', '-qm', 'offline fixture'], cwd=root, check=True)
    monkeypatch.setattr(Q, 'ROOT', root)
    monkeypatch.setattr(Q, 'source_hashes', lambda: {'source.py': hashlib.sha256(source.read_bytes()).hexdigest()})
    inputs = root/'inputs'
    for name in ('e3', 'e4', 'e9'):
        (inputs/name).mkdir(parents=True)
        P.dump(inputs/name/'INPUT_SEAL.json', {'files': {}, 'fixture': name})
    monkeypatch.setattr(Q, 'load_inputs', lambda path: {
        'items': list(range({'e3': 4200, 'e4': 2100, 'e9': 3360}[path.name])),
        'rows': list(range(40 if path.name == 'e9' else 25))})
    tests = root/'tests.json'; P.dump(tests, {'status': 'PASS', 'gpu_hours': 0})
    return root, source, inputs, tests


def test_launch_request_rejects_uncommitted_source(tmp_path, monkeypatch):
    root, source, inputs, tests = request_fixture(tmp_path, monkeypatch)
    source.write_text('fixed_source = 2\n')
    with pytest.raises(ValueError, match='source differs from committed'):
        Q.create('E3', inputs, tests, root/'request.json')
    assert not (root/'request.json').exists()


def test_launch_request_accepts_committed_source_and_binds_inputs(tmp_path, monkeypatch):
    root, source, inputs, tests = request_fixture(tmp_path, monkeypatch)
    result = Q.create('E4', inputs, tests, root/'request.json')
    assert result['input_seals'] == {'primary': P.sha(inputs/'e4/INPUT_SEAL.json'),
                                     'e9': P.sha(inputs/'e9/INPUT_SEAL.json')}
    assert result['max_science_seconds'] == 2160
    assert result['setup_allowance_seconds'] == 1500
    assert result['gpu_results'] == 'NOT_RUN'
    assert result['stage_only'] == ['e4', 'e9']
    assert result['phases'] == ['olens', 'nla', 'jlens', 'target']
    assert result['source_commit'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    with pytest.raises(ValueError, match='already exists'):
        Q.create('E4', inputs, tests, root/'request.json')


def test_packed_request_binds_one_process_two_clocks_and_all_inputs(tmp_path, monkeypatch):
    root, source, inputs, tests = request_fixture(tmp_path, monkeypatch)
    result = Q.create_packed(inputs, tests, root/'pack.json')
    assert result['sequence'] == ['E3', 'E4'] and result['single_process'] is True
    assert result['experiment_science_caps_seconds'] == {'E3': 2160, 'E4': 2160}
    assert result['setup_allowance_seconds'] == 1500
    assert result['assignment_required']['experiment'] == 'E3_E4_PACK'
    assert result['input_seals'] == {
        'E3': {'primary': P.sha(inputs/'e3/INPUT_SEAL.json')},
        'E4': {'primary': P.sha(inputs/'e4/INPUT_SEAL.json'), 'e9': P.sha(inputs/'e9/INPUT_SEAL.json')}}
    assert result['launch_argv'][:3] == ['/weights/venv/bin/python', '-m', 'projects.g_agreement.understand.packed']
    assert result['environment']['venv'] == '/weights/venv'
    assert result['environment']['python'] == result['launch_argv'][0]
    assert result['environment']['variables'] == {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    assert result['model_loads']['olens'] == result['model_loads']['nla'] == 1
    assert result['populations']['e9']['n_items'] == 3360
    source.write_text('fixed_source = 2\n')
    with pytest.raises(ValueError, match='source differs from committed'):
        Q.create_packed(inputs, tests, root/'pack_changed.json')


def test_e4_only_request_retains_scope_caps_and_environment(tmp_path,monkeypatch):
    root,source,inputs,tests=request_fixture(tmp_path,monkeypatch)
    result=Q.create_packed(inputs,tests,root/'retry.json',e4_only=True)
    assert result['sequence']==['E4']
    assert result['assignment_required']['experiment']=='E4_ONLY_RETRY'
    assert result['experiment_science_caps_seconds']=={'E4':2160}
    assert result['setup_allowance_seconds']==1500
    assert result['stage_only']==['e4','e9']
    assert result['launch_argv'][0]=='/weights/venv/bin/python'
    assert result['launch_argv'][-1]=='--e4-only'
    assert result['populations']['e9']['n_items']==3360
    assert result['populations']['e4']['n_items']==2100
    assert set(result['input_seals'])=={'E4'}


def test_e4_microbatch_units_preserve_all_items():
    from projects.g_agreement.understand import run
    data={'rows':[{'feature':'a'},{'feature':'b'}],
          'items':[{'feature':'a'}]*84+[{'feature':'b'}]*84}
    for phase in ('olens','nla','jlens','target'):
        units=run.units(data,'E4',phase)
        assert len(units)==168
        assert [i for _,ix in units for i in ix]==list(range(168))
        assert all(len(ix)==1 for _,ix in units)
