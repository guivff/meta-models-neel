"""Synthetic CPU orchestration/custody tests; no corpus, target, or GPU calls."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    spec = importlib.util.spec_from_file_location('e35_training_worker_tested', HERE / 'training_worker.py')
    tw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tw)
    from sae import QwenScopeSAE
finally:
    sys.path.remove(str(HERE))


def json_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_inference_capture_is_cloned_to_normal_tensor_for_autograd():
    with torch.inference_mode():
        captured = torch.arange(6, dtype=torch.float32).reshape(3, 2)
        actual = tw.training_tensor(captured)
    assert torch.is_inference(captured) and not torch.is_inference(actual)
    weights = torch.ones((2, 2), requires_grad=True)
    (actual @ weights).sum().backward()
    torch.testing.assert_close(weights.grad, torch.tensor([[6., 6.], [9., 9.]]))
    captured_values = captured.clone()
    actual.zero_()
    torch.testing.assert_close(captured, captured_values)


@pytest.mark.parametrize('total,free', [(79_999_999_999, 25_000_000_000),
    (80_000_000_000, 19_999_999_999), (80_000_000_000, 81_000_000_000),
    (80_000_000_000., 25_000_000_000), (True, 20_000_000_000)])
def test_memory_admission_rejects_small_or_invalid_device(total, free):
    with pytest.raises(tw.NoFit):
        tw.verify_device_memory(total, free)


def test_memory_admission_includes_exact_boundary_and_records_evidence():
    result = tw.verify_device_memory(80_000_000_000, 20_000_000_000)
    assert result['passed'] is True and result['free_after_target_bytes'] == 20_000_000_000


def chunk(ids, start=0):
    return {'document_id': 'synthetic', 'source': {'kind': 'section79'},
            'ids': ids, 'token_start': start, 'token_end': start + len(ids)}


def capture_values(model, ids, positions, device='cpu'):
    assert positions == list(range(len(ids)))
    with torch.inference_mode():
        x = torch.tensor(ids, dtype=torch.float32)
        return torch.stack((x, torch.zeros_like(x)), dim=1)


def test_activation_buffer_retains_every_tail_in_order_without_padding():
    config = SimpleNamespace(batch_size=4, d_model=2)
    chunks = [chunk([1, 2, 3]), chunk([4, 5, 6, 7, 8]), chunk([9])]
    progress = {'training_chunks_captured': 0}
    clock = SimpleNamespace(check=lambda: None)
    batches = [x.clone() for x in tw.activation_batches(None, chunks, clock, progress,
        capture=capture_values, config=config, device='cpu')]
    assert [len(x) for x in batches] == [4, 4, 1]
    assert torch.cat(batches)[:, 0].tolist() == list(range(1, 10))
    assert all(not torch.is_inference(x) for x in batches)
    assert progress['training_chunks_captured'] == 3


def test_bad_document_span_rejected_before_capture():
    called = []
    malformed = dict(chunk([1, 2]), token_end=3)
    with pytest.raises(ValueError, match='document-local'):
        list(tw.activation_batches(None, [malformed], SimpleNamespace(check=lambda: None),
            {'training_chunks_captured': 0}, capture=lambda *a, **k: called.append(True),
            config=SimpleNamespace(batch_size=4, d_model=2), device='cpu'))
    assert called == []


class FakeClock:
    def __init__(self, events, reject=False):
        self.events, self.reject = events, reject
        self.status = 'SETUP'
        self.pilots = {name: [] for name in ('capture512', 'train4096', 'gate512')}

    def check(self):
        pass

    def begin_science(self):
        self.events.append('begin_science')
        self.status = 'PILOT'

    def record_pilot(self, kind, seconds):
        assert seconds > 0 and 'begin_science' in self.events
        self.pilots[kind].append(seconds)

    def admit(self, chunks, optimizer_steps, gate_documents):
        assert all(len(x) == 3 for x in self.pilots.values())
        assert (chunks, optimizer_steps, gate_documents) == (6, 3, 1)
        self.events.append('admit')
        if self.reject:
            raise tw.NoFit('synthetic admission stop')
        self.status = 'RUNNING'

    def record(self):
        return {'status': self.status}


@pytest.fixture
def tiny_science(tmp_path, monkeypatch):
    monkeypatch.setattr(tw, 'CAPTURE_TOKENS', 2)
    code, out = tmp_path / 'code', tmp_path / 'out'
    out.mkdir()
    json_file(code / tw.NORMALIZATION_FILENAME, tw.NORMALIZATION_MANIFEST)
    monkeypatch.setattr(tw, 'HERE', code)
    config = SimpleNamespace(d_model=2, d_sae=4, k=1, batch_size=4, target_tokens=10)
    chunks = [chunk(x) for x in ([1, 2], [3], [4, 5], [6], [7, 8], [9, 10])]
    sample = {'pilot_document_ids': ['pilot1', 'pilot2', 'pilot3'],
              'documents': [{'id': 'heldout', 'positions': [0, 1]}]}
    ids = {'pilot1': [101, 102], 'pilot2': [103, 104], 'pilot3': [105, 106],
           'heldout': [901, 902]}
    events, trainers = [], []
    parameters = {'W_enc': torch.tensor([[1., 0.], [0., 1.], [-1., 0.], [0., -1.]]),
                  'W_dec': torch.tensor([[1., 0., -1., 0.], [0., 1., 0., -1.]]),
                  'b_enc': torch.zeros(4), 'b_dec': torch.zeros(2)}

    class FakeTrainer:
        def __init__(self, *, device, config, synthetic, timing_force_auxiliary=False):
            self.synthetic, self.forced = synthetic, timing_force_auxiliary
            assert self.forced is self.synthetic
            if not synthetic:
                assert 'admit' in events and 'alarm_rearmed' in events
            self.tokens_seen, self.steps, self.inputs = 0, 0, []
            self.model = QwenScopeSAE({k: v.clone() for k, v in parameters.items()}, k=1)
            trainers.append(self)
            events.append('scratch_created' if synthetic else 'actual_created')

        def step(self, x, *, first_position, split):
            assert first_position == self.tokens_seen and split == 'train'
            assert not torch.is_inference(x)
            self.inputs.extend(x[:, 0].tolist())
            self.tokens_seen += len(x)
            self.steps += 1
            return {'loss': 1.}

        def checkpoint_tensors(self):
            assert self.tokens_seen == 10 and not self.synthetic
            events.append('checkpoint')
            return {k: v.clone() for k, v in parameters.items()}

        def completed_manifest(self):
            assert self.tokens_seen == 10 and not self.synthetic
            return {'status': 'COMPLETE', 'training_tokens': 10, 'optimizer_updates': 3}

    class FakeMetric:
        def __init__(self, d_model, d_sae):
            assert (d_model, d_sae) == (2, 4)
            self.n = 0
        def update(self, h, r, *, active_latents):
            np.testing.assert_array_equal(h, r)
            assert active_latents.shape == (4,)
            self.n += len(h)
        def result(self):
            assert self.n == 2
            return {'passed': True, 'n_tokens': self.n, 'd_model': 2, 'd_sae': 4}

    def capture(model, ids, positions, device='cpu'):
        if min(ids) >= 900:
            assert (out / 'TRAINING_RESULT.json').is_file()
            assert (out / 'layer44.fallback.sae.pt').is_file()
            assert (out / 'fallback-gate.RUN_ONCE.json').is_file()
            assert trainers[-1].tokens_seen == 10
            events.append('heldout_capture')
        return capture_values(model, ids, positions, device)

    progress = {'training_chunks_captured': 0, 'training_tokens': 0,
                'optimizer_steps': 0, 'gate_documents': 0, 'gate_tokens': 0}
    kwargs = dict(capture=capture, trainer_factory=FakeTrainer, synchronize=lambda: None,
                  metric_factory=FakeMetric, config=config, device='cpu',
                  runtime_record=lambda: {'synthetic': True},
                  arm_alarm=lambda clock: events.append('alarm_rearmed'))
    return SimpleNamespace(out=out, events=events, trainers=trainers, chunks=chunks, sample=sample,
        ids=ids, progress=progress, kwargs=kwargs,
        manifest={'n_chunks': 6, '_verified_seal_sha256': 'a' * 64})


def test_pilots_discarded_before_one_full_actual_pass_and_final_only_gate(tiny_science):
    f = tiny_science
    clock = FakeClock(f.events)
    result, checkpoint_sha, normalization_sha = tw.run_science(None, lambda: iter(f.chunks),
        f.manifest, f.sample, f.ids, clock, f.out, lambda: None, f.progress, **f.kwargs)
    assert result['passed']
    assert [x.steps for x in f.trainers] == [3, 3]
    assert f.trainers[0].inputs == [1, 2, 4, 5] * 3
    assert f.trainers[1].inputs == list(range(1, 11))
    assert f.events.index('checkpoint') < f.events.index('heldout_capture')
    assert f.events.index('begin_science') < f.events.index('admit') < f.events.index('actual_created')
    assert f.progress['gate_tokens'] == 2 and f.progress['training_tokens'] == 10
    assert checkpoint_sha == tw.sha(f.out / 'layer44.fallback.sae.pt')
    assert normalization_sha == tw.sha(f.out / 'NORMALIZATION.json')
    assert not (f.out / 'h.npy').exists() and not (f.out / 'reconstruction.npy').exists()


def test_no_fit_after_pilots_never_constructs_actual_trainer_or_runs_gate(tiny_science):
    f = tiny_science
    with pytest.raises(tw.NoFit):
        tw.run_science(None, lambda: iter(f.chunks), f.manifest, f.sample, f.ids,
            FakeClock(f.events, reject=True), f.out, lambda: None, f.progress, **f.kwargs)
    assert len(f.trainers) == 1 and f.trainers[0].synthetic
    assert 'heldout_capture' not in f.events and 'actual_created' not in f.events
    assert not (f.out / 'layer44.fallback.sae.pt').exists()
    assert not (f.out / 'fallback-gate.RUN_ONCE.json').exists()


def test_global_guard_prevents_second_output_or_relaunch(tmp_path):
    out = tmp_path / tw.OUTPUT_PATH
    tw.claim_run(out, 'a' * 64, 'b' * 64, root=tmp_path)
    guard = tmp_path / 'cache/g_agreement/understand/e35/training.RUN_ONCE.json'
    before = guard.read_bytes()
    with pytest.raises(FileExistsError):
        tw.claim_run(out, 'a' * 64, 'b' * 64, root=tmp_path)
    with pytest.raises(ValueError, match='exact once-only'):
        tw.claim_run(out.parent / 'other', 'a' * 64, 'b' * 64, root=tmp_path)
    assert guard.read_bytes() == before


def test_accounting_receipt_binds_bytes_exact_total_mode_and_all_prior_pods(tmp_path):
    path = tmp_path / 'accounting.json'
    receipt = {'status': 'FINAL_OR_CONSERVATIVE', 'previous_gpu_seconds': 4034.2,
               'mode': 'conservative_allocation',
               'pod_ids': ['5wu4ujkbiotxom', '21wel7nawi51j3', '833ksjl7c6sxie']}
    json_file(path, receipt)
    assignment = {'previous_gpu_seconds': 4034.2, 'prior_accounting': {
        'receipt_sha256': tw.sha(path), 'rerun_mode': 'conservative_allocation'}}
    assert tw.verify_accounting(path, assignment) == receipt
    receipt['pod_ids'][1] += '-wrong'
    json_file(path, receipt)
    with pytest.raises(ValueError, match='checksum'):
        tw.verify_accounting(path, assignment)
    assignment['prior_accounting']['receipt_sha256'] = tw.sha(path)
    with pytest.raises(ValueError, match='prior-pod'):
        tw.verify_accounting(path, assignment)


@pytest.mark.parametrize('error,status,category,eligible', [
    (tw.NoFit, 'NO_FIT', 'OPERATIONAL', True),
    (OSError, 'INCOMPLETE', 'OPERATIONAL', True),
    (ValueError, 'INCOMPLETE', 'VALIDITY_OR_UNCLASSIFIED', False),
])
def test_execute_errors_never_become_scientific_fail_or_print_exception_payload(
        tmp_path, monkeypatch, capsys, error, status, category, eligible):
    code, out = tmp_path / 'code', tmp_path / 'out'
    out.mkdir()
    json_file(code / tw.REQUEST_FILENAME, {})
    monkeypatch.setattr(tw, 'HERE', code)
    args = SimpleNamespace(out=out, training_cache=tmp_path / 'cache',
                           assignment=tmp_path / 'assignment.json',
                           accounting_receipt=tmp_path / 'accounting.json')
    json_file(args.assignment, {})
    json_file(args.accounting_receipt, {})
    def reject(*a, **k):
        raise error('sensitive-error-payload-must-not-print')
    monkeypatch.setattr(tw, 'verify_training_cache', reject)
    clock = FakeClock([])
    code = tw.execute(args, clock, {}, {'training_cache_seal_sha256': 'a' * 64}, {})
    assert code == 2
    report = tw.read(out / 'GATE_RESULT.json')
    assert report['status'] == status and report['metrics'] is None
    assert report['failure_category'] == category
    assert report['operational_rebuild_eligible'] is eligible
    assert 'sensitive-error-payload' not in capsys.readouterr().out
    seal = tw.read(out / 'OUTPUT_SEAL.json')
    assert seal['status'] == status and seal['files']['GATE_RESULT.json'] == tw.sha(out / 'GATE_RESULT.json')


def test_science_hard_alarm_uses_earlier_of_assigned_and_science_deadlines(monkeypatch):
    calls = []
    monkeypatch.setattr(tw.time, 'time', lambda: 1000.)
    monkeypatch.setattr(tw.signal, 'setitimer', lambda kind, seconds: calls.append(seconds))
    clock = SimpleNamespace(a={'deadline_epoch': 2000.}, science_start=1050., science_limit=100.)
    tw.rearm_science_alarm(clock)
    assert calls == [150.]
    clock.science_limit = 2000.
    tw.rearm_science_alarm(clock)
    assert calls[-1] == 820.


def test_source_checksum_covers_dependencies_and_fixed_plan(tmp_path):
    base = tmp_path / 'results/g_agreement/understand/e35'
    names = ['training_worker.py', 'training_stream.py', 'training_clock.py', 'fallback_sae.py',
             'FALLBACK_TRAINING_CHOICES.20261025.md', 'FALLBACK_CORPUS_PIN.20261025.json',
             'gate_worker.py', 'gate_inputs.py', 'gate_math.py', 'sae.py',
             'GATE_SAMPLE.json', 'LAUNCH_REQUEST.gate-rerun1.json']
    for name in names:
        json_file(base / name, {'synthetic': name})
    json_file(base / tw.NORMALIZATION_FILENAME, tw.NORMALIZATION_MANIFEST)
    json_file(base / tw.PLAN_FILENAME, {'training': asdict(tw.FIXED_CONFIG),
                                      'normalization_manifest_sha256': tw.sha(base / tw.NORMALIZATION_FILENAME)})
    request = {'experiment': 'E35', 'stage': 'training', 'output_path': tw.OUTPUT_PATH,
               'source_files': {p.name: tw.sha(p) for p in base.iterdir()}}
    tw.verify_sources(request, root=tmp_path)
    (base / 'fallback_sae.py').write_text('changed')
    with pytest.raises(ValueError, match='checksum'):
        tw.verify_sources(request, root=tmp_path)


@pytest.fixture
def prior_gate(tmp_path, monkeypatch):
    folder = tmp_path / 'cache/g_agreement/understand/e35/prior/final'
    base = tmp_path / 'results/g_agreement/understand/e35'
    json_file(base / 'LAUNCH_REQUEST.gate-rerun1.json', {'synthetic': True})
    json_file(folder / 'assignment.json', {'issuer': 'integrator', 'synthetic': True})
    json_file(folder / 'CLOCK.json', {'status': 'FAIL', 'synthetic': True})
    gate = {'experiment': 'E35', 'stage': 'gate', 'status': 'FAIL',
            'metrics': {'passed': False, 'n_tokens': 50000, 'd_model': 5120,
                        'd_sae': 81920, 'fvu': .4, 'dead_fraction': .2},
            'sample_sha256': tw.SAMPLE_SHA,
            'request_sha256': tw.sha(base / 'LAUNCH_REQUEST.gate-rerun1.json'),
            'assignment_sha256': tw.sha(folder / 'assignment.json')}
    request = {'prior_gate_dir': str(folder.relative_to(tmp_path))}

    def seal():
        json_file(folder / 'GATE_RESULT.json', gate)
        json_file(folder / 'OUTPUT_SEAL.json', {'status': 'FAIL', 'files': {
            'GATE_RESULT.json': tw.sha(folder / 'GATE_RESULT.json'),
            'CLOCK.json': tw.sha(folder / 'CLOCK.json'),
            'h.npy': '1' * 64, 'reconstruction.npy': '2' * 64}})
        request['prior_gate_files'] = {name: tw.sha(folder / name)
            for name in ('GATE_RESULT.json', 'OUTPUT_SEAL.json', 'CLOCK.json', 'assignment.json')}
        monkeypatch.setattr(tw, 'PRIOR_RESULT_SHA', request['prior_gate_files']['GATE_RESULT.json'])
        monkeypatch.setattr(tw, 'PRIOR_SEAL_SHA', request['prior_gate_files']['OUTPUT_SEAL.json'])
    seal()
    return SimpleNamespace(root=tmp_path, folder=folder, gate=gate, request=request, seal=seal)


def test_delivered_scientific_fail_accepts_small_custody_without_loading_arrays(prior_gate):
    f = prior_gate
    custody = tw.verify_prior_gate(f.request, root=f.root)
    assert custody['large_arrays_retrieved_for_this_worker'] is False
    assert custody['large_arrays_used_for_fallback'] is False
    assert custody['large_array_seal_pins'] == {'h.npy': '1' * 64, 'reconstruction.npy': '2' * 64}
    assert not (f.folder / 'h.npy').exists()


def test_changed_prior_small_clock_bytes_rejected(prior_gate):
    f = prior_gate
    json_file(f.folder / 'CLOCK.json', {'status': 'changed'})
    with pytest.raises(ValueError, match='checksum'):
        tw.verify_prior_gate(f.request, root=f.root)


@pytest.mark.parametrize('problem', ['incomplete', 'thresholds', 'assignment'])
def test_prior_failure_receipt_must_be_scientific_and_lineage_consistent(prior_gate, problem):
    f = prior_gate
    if problem == 'incomplete':
        f.gate['status'] = 'INCOMPLETE'
    elif problem == 'thresholds':
        f.gate['metrics'].update(fvu=.2, dead_fraction=.05)
    else:
        f.gate['assignment_sha256'] = '0' * 64
    f.seal()
    with pytest.raises(ValueError):
        tw.verify_prior_gate(f.request, root=f.root)
