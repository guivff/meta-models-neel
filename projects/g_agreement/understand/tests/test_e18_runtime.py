from types import SimpleNamespace

import pytest

from projects.g_agreement.understand import e18_runtime as R
from projects.g_agreement.understand.e18_analyse import DONOR_RULE
from projects.g_agreement.understand.cpu import dump, read, sha, verify


@pytest.fixture
def setup(tmp_path, monkeypatch):
    clock = SimpleNamespace(epoch=1800000000., mono=10.)
    monkeypatch.setattr(R, 'ROOT', tmp_path)
    monkeypatch.setattr(R, 'STOP', clock.epoch + 10000)
    monkeypatch.setattr(R, 'time', SimpleNamespace(time=lambda: clock.epoch, monotonic=lambda: clock.mono))
    authority = 'results/g_agreement/understand/e18/DONOR_RULE.fixture.md'
    for filename in [R.BRIEF, authority, *R.REQUIRED_SOURCE]:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic frozen fixture; no production authority')
    dump(tmp_path / R.PLAN, {
        'donor_rule_status': 'REGISTERED',
        'donor_rule': DONOR_RULE,
        'donor_rule_authority': {'path': authority, 'sha256': sha(tmp_path / authority),
                                 'registered_before_science': True, 'commit': '99518d4e'},
    })
    assignment = {
        'issuer': 'integrator', 'experiment': 'E18', 'gpu_count': 1, 'pod_id': 'synthetic',
        'brief_registered': True, 'brief_pushed': True, 'external_hardstop_verified': True,
        'hold_renewer_verified': True, 'brief_sha256': sha(tmp_path / R.BRIEF),
        'plan_sha256': sha(tmp_path / R.PLAN),
        'source_files': {f: sha(tmp_path / f) for f in R.REQUIRED_SOURCE},
        'allocated_gpu_seconds': 2400, 'previous_gpu_seconds': 0,
        'provider_created_epoch': clock.epoch - 10, 'setup_deadline_epoch': clock.epoch + 1490,
        'deadline_epoch': clock.epoch + 3890, 'setup_allowance_seconds': 1500,
        'forecast_method': R.FORECAST_METHOD,
    }
    path = tmp_path / 'assignment.json'
    dump(path, assignment)
    counts = {k: 5 for k in R.PATHS}
    return SimpleNamespace(root=tmp_path, clock=clock, assignment=assignment, path=path, counts=counts)


def gate(setup):
    g = R.Gate(setup.path, setup.counts)
    g.out = setup.root / 'out'
    g.out.mkdir()
    return g


def warm_start(g):
    for key in R.PATHS:
        g.warm(key, .1)
    g.start()


def pilot(g, clock, duration=1.):
    for key in R.PATHS:
        for _ in range(3):
            clock.mono += duration
            clock.epoch += duration
            g.record(key, duration, retained=False)


def test_all_five_paths_required_and_unknown_forecast_is_none(setup):
    g = gate(setup)
    with pytest.raises(ValueError, match='every path'):
        g.start()
    warm_start(g)
    for key in R.PATHS[:-1]:
        for _ in range(3):
            g.record(key, 1., retained=False)
    forecast = g.forecast()
    assert forecast['F_seconds'] is None
    assert forecast['paths']['d']['forecast_seconds'] is None
    assert forecast['paths']['d']['median_seconds'] is None
    assert not forecast['unknown_paths_are_zero']
    with pytest.raises(ValueError, match='all five'):
        g.admit()
    with pytest.raises(ValueError, match='test output forbidden'):
        g.record('a', 1., retained=True)


def test_discarded_dev_timing_is_science_and_clock_does_not_reset(setup):
    g = gate(setup)
    warm_start(g)
    start, epoch = g.started, g.first_science_epoch
    pilot(g, setup.clock)
    assert g.elapsed() == 15
    assert g.discarded_timing_seconds == 15
    assert all(v == 0 for v in g.completed.values())
    assert g.forecast()['F_seconds'] == 25 + 15
    with pytest.raises(ValueError, match='exactly three'):
        g.record('a', 1., retained=False)
    g.admit()
    assert g.cap == 420
    assert g.admitted
    g.start()
    assert (g.started, g.first_science_epoch) == (start, epoch)
    verify(g.out, 'FORECAST_SEAL.json')
    assert read(g.out / 'FULL_WARMED_FORECAST.json')['remaining_forecast_seconds'] == 25
    setup.clock.mono += 1
    g.record('a', 1.)
    assert g.completed['a'] == 1
    assert g.forecast()['F_seconds'] == 40
    with pytest.raises(ValueError, match='discarded timing'):
        g.record('a', 1., retained=False)


def test_no_fit_seals_forecast_and_keeps_original_clock(setup):
    setup.counts = {k: 100 for k in R.PATHS}
    g = gate(setup)
    warm_start(g)
    start = g.started
    pilot(g, setup.clock, duration=5.)
    with pytest.raises(R.NoFit, match='NO_FIT'):
        g.admit()
    assert g.status == 'NO_FIT' and not g.admitted and g.cap == 2400
    assert g.started == start
    verify(g.out, 'FORECAST_SEAL.json')
    forecast = read(g.out / 'FULL_WARMED_FORECAST.json')
    assert forecast['F_seconds'] == 2575
    assert forecast['fit'] is False
    assert read(g.out / 'CLOCK.json')['status'] == 'NO_FIT'
    with pytest.raises(ValueError, match='only once'):
        g.admit()


def test_unresolved_donor_rule_blocks_constructor_before_any_clock(setup):
    dump(setup.root / R.PLAN, {'donor_rule_status': 'UNRESOLVED', 'donor_rule_authority': None})
    setup.assignment['plan_sha256'] = sha(setup.root / R.PLAN)
    dump(setup.path, setup.assignment)
    with pytest.raises(ValueError, match='DONOR_RULE_UNRESOLVED'):
        R.Gate(setup.path, setup.counts)
    assert not (setup.root / 'out').exists()


@pytest.mark.parametrize('change,match', [
    ({'allocated_gpu_seconds': 2401}, 'science cap'),
    ({'setup_allowance_seconds': 1501}, 'setup/provider'),
    ({'previous_gpu_seconds': 1}, 'fresh E18'),
    ({'forecast_method': 'unmeasured_paths_zero'}, 'full five-path'),
    ({'hold_renewer_verified': False}, 'evidence required'),
    ({'plan_sha256': 'incorrect'}, 'plan mismatch'),
])
def test_assignment_caps_and_proofs_cannot_be_relaxed(setup, change, match):
    setup.assignment.update(change)
    dump(setup.path, setup.assignment)
    with pytest.raises(ValueError, match=match):
        R.Gate(setup.path, setup.counts)


def test_setup_and_science_deadlines_include_retrieval_reserve(setup):
    g = gate(setup)
    setup.clock.epoch = setup.assignment['setup_deadline_epoch']
    with pytest.raises(TimeoutError, match='setup/absolute'):
        g.setup_guard()
    setup.clock.epoch -= 10
    warm_start(g)
    pilot(g, setup.clock)
    g.admit()
    setup.clock.mono = g.started + g.cap - R.RETRIEVAL_SECONDS
    with pytest.raises(TimeoutError, match='science/retrieval'):
        g.guard()


def test_pilot_never_runs_outside_science_and_production_count_is_bounded(setup):
    g = gate(setup)
    with pytest.raises(ValueError, match='science clock'):
        g.record('a', 1., retained=False)
    warm_start(g)
    pilot(g, setup.clock)
    g.admit()
    for _ in range(setup.counts['a']):
        g.record('a', 1.)
    with pytest.raises(ValueError, match='already complete'):
        g.record('a', 1.)
