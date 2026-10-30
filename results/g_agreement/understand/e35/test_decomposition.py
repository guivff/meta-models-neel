"""Synthetic CPU E35 encoding/authorization/custody checks, 2026-10-25."""
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
    SPEC = importlib.util.spec_from_file_location('e35_decomposition_tested', HERE / 'decomposition.py')
    dc = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(dc)
finally:
    sys.path.remove(str(HERE))


class NonlinearSAE:
    k = 2
    d_sae = 2

    def __init__(self):
        self.calls = []

    def encode(self, x):
        self.calls.append(x.clone())
        return x.relu().square()


def dense(pair, width=2):
    indices, values = pair
    z = np.zeros((len(indices), width))
    np.put_along_axis(z, indices, values, axis=1)
    return z


def triplet():
    h = torch.tensor([[2., 1.], [1., -2.]])
    win = torch.tensor([[1., -1.], [-1., 1.]])
    ol = torch.tensor([[-1., 0.], [0., -1.]])
    return h, win, ol


def test_primary_encodes_raw_errors_and_code_differences_are_separate():
    sae = NonlinearSAE()
    h, win, ol = triplet()
    result = dc.encode_triplet(sae, h, win, ol, authorized=True)
    assert set(result) == set(dc.PRIMARY + dc.DESCRIPTIVE)
    assert len(sae.calls) == 5
    for actual, expected in zip(sae.calls, (h, win, ol, h - win, win - ol)):
        torch.testing.assert_close(actual, expected)
    np.testing.assert_array_equal(dense(result['h']), h.relu().square().numpy())
    np.testing.assert_array_equal(dense(result['window_loss']), [[1, 4], [4, 0]])
    np.testing.assert_array_equal(dense(result['policy_loss']), [[4, 0], [0, 4]])
    np.testing.assert_array_equal(dense(result[dc.DESCRIPTIVE[0]]), [[3, 1], [1, 0]])
    np.testing.assert_array_equal(dense(result[dc.DESCRIPTIVE[1]]), [[1, 0], [0, 1]])
    assert not np.array_equal(dense(result['window_loss']), dense(result[dc.DESCRIPTIVE[0]]))
    assert not np.array_equal(dense(result['policy_loss']), dense(result[dc.DESCRIPTIVE[1]]))


@pytest.mark.parametrize('authorization', [None, False, 1, 'yes'])
def test_encoding_is_blocked_by_default_or_nonboolean_authorization(authorization):
    sae = NonlinearSAE()
    with pytest.raises(ValueError, match='authorization'):
        if authorization is None:
            dc.encode_triplet(sae, *triplet())
        else:
            dc.encode_triplet(sae, *triplet(), authorized=authorization)
    assert sae.calls == []


@pytest.mark.parametrize('problem', ['shape', 'empty', 'nan', 'inf'])
def test_bad_raw_inputs_stop_before_encoding(problem):
    sae = NonlinearSAE()
    h, win, ol = triplet()
    if problem == 'shape':
        win = win[:1]
    elif problem == 'empty':
        h, win, ol = h[:0], win[:0], ol[:0]
    elif problem == 'nan':
        h[0, 0] = float('nan')
    else:
        ol[0, 0] = float('inf')
    with pytest.raises(ValueError, match='finite raw'):
        dc.encode_triplet(sae, h, win, ol, authorized=True)
    assert sae.calls == []


@pytest.mark.parametrize('problem', ['negative', 'nan', 'wrong_width', 'wrong_batch'])
def test_invalid_encoder_outputs_are_rejected(problem):
    class BadSAE(NonlinearSAE):
        def encode(self, x):
            if problem == 'negative':
                return -torch.ones_like(x)
            if problem == 'nan':
                return torch.full_like(x, float('nan'))
            if problem == 'wrong_width':
                # Exactly k positive values: sparsity validation cannot mask a
                # missing dictionary-width check.
                return torch.tensor([[1., 1., 0.]]).repeat(len(x), 1)
            return torch.ones((1, 2))
    with pytest.raises(ValueError):
        dc.encode_triplet(BadSAE(), *triplet(), authorized=True)


def test_encoder_dictionary_width_cannot_change_between_calls_by_broadcasting():
    class ChangingSAE(NonlinearSAE):
        def encode(self, x):
            self.calls.append(x)
            return torch.ones((len(x), 1 if len(self.calls) == 2 else 2))
    with pytest.raises(ValueError):
        dc.encode_triplet(ChangingSAE(), *triplet(), authorized=True)


def test_decoder_norms_use_columns_and_cross_the_256_column_boundary():
    # Columns cycle through norms 3, 4, 5; columns 255--257 straddle a chunk.
    decoder = torch.tensor([[3., 0., 3.], [0., 4., 4.]]).repeat(1, 87)[:, :259]
    decoder.requires_grad_(True)
    sae = SimpleNamespace(W_dec=decoder, d_model=2, d_sae=259, b_dec=torch.ones(2))
    result = dc.decoder_column_norms(sae)
    assert result.dtype == np.float64
    np.testing.assert_array_equal(result, np.tile([3., 4., 5.], 87)[:259])
    assert result[255:258].tolist() == [3., 4., 5.]
    assert decoder.grad is None


def test_decoder_norms_exclude_bias_even_if_bias_is_nonfinite():
    sae = SimpleNamespace(W_dec=torch.tensor([[3., 0.], [4., 0.]]),
                          d_model=2, d_sae=2, b_dec=torch.tensor([0., 0.]))
    before = dc.decoder_column_norms(sae)
    sae.b_dec = torch.tensor([float('nan'), float('inf')])
    np.testing.assert_array_equal(dc.decoder_column_norms(sae), before)
    np.testing.assert_array_equal(before, [5., 0.])


def test_decoder_norm_accumulation_avoids_float32_square_overflow():
    sae = SimpleNamespace(W_dec=torch.tensor([[3e20], [4e20]], dtype=torch.float32),
                          d_model=2, d_sae=1)
    result = dc.decoder_column_norms(sae)
    assert result.dtype == np.float64 and np.isfinite(result).all()
    assert result[0] == pytest.approx(5e20, rel=1e-7)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf')])
def test_decoder_nonfinite_column_after_chunk_boundary_rejected(bad):
    decoder = torch.ones((2, 258))
    decoder[0, 256] = bad
    sae = SimpleNamespace(W_dec=decoder, d_model=2, d_sae=258)
    with pytest.raises(ValueError, match='finite decoder columns'):
        dc.decoder_column_norms(sae)


@pytest.mark.parametrize('shape', [(3, 258), (2, 257), (258, 2), (2, 258, 1)])
def test_decoder_shape_must_match_model_and_dictionary_dimensions(shape):
    sae = SimpleNamespace(W_dec=torch.ones(shape), d_model=2, d_sae=258)
    with pytest.raises(ValueError, match='column shape'):
        dc.decoder_column_norms(sae)


def toy_report_inputs():
    metadata = [{'id': f'dev-{i}', 'split': 'dev', 'row': row} for i, row in enumerate(('A', 'B'))]
    metadata += [{'id': f'test-{i}', 'split': 'test', 'row': row} for i, row in enumerate(('A', 'A', 'B', 'B'))]
    indices = np.tile([0, 1], (6, 1))
    codes = {
        'h': (indices, np.array([[99, 1]] * 2 + [[1, 3]] * 4, dtype=float)),
        'window_loss': (indices, np.array([[1, 99]] * 2 + [[1, 1]] * 4, dtype=float)),
        'policy_loss': (indices, np.array([[1, 99]] * 2 + [[3, 5]] * 4, dtype=float)),
        dc.DESCRIPTIVE[0]: (indices, np.zeros((6, 2))),
        dc.DESCRIPTIVE[1]: (indices, np.zeros((6, 2))),
    }
    return codes, np.ones(2), np.array([True, False]), np.array([1, 1]), metadata


def test_primary_report_uses_test_only_actual_fixed_bootstrap_and_100_controls():
    report = dc.primary_report(*toy_report_inputs())
    assert report['primary_encoding'] == 'encode_raw_difference_directly'
    for rule, expected in [('R1', 2.), ('R2', 1.5)]:
        row = report['rules'][rule]
        assert row['n_items'] == 4
        assert row['ratio'] == expected
        assert row['ci95'] == [expected, expected]
        assert row['bootstrap_resamples_performed'] == 10000
        assert row['bootstrap_seed'] == 20261025
        assert row['rule_met']
        null = row['frequency_matched_control']
        assert len(null['ratios']) == 100
        assert null['draws'] == 100
        assert null['undefined_ratios'] == 0
        assert null['unique_masks'] == 2
        assert null['null_CI_computed'] is False
        assert null['rule_applied_to_controls'] is False
    np.testing.assert_allclose(sorted(set(report['rules']['R1']['frequency_matched_control']['ratios'])), [2 / 3, 2])
    for result in report['descriptive_code_differences'].values():
        assert result['excluded_items'] == 4
        assert result['ratio'] is None
        assert result['rule_applied'] is False


def test_dev_counts_and_sums_do_not_use_test_items():
    index = np.array([[0, 1], [1, 2], [3, 0]])
    values = np.array([[2., 0.], [3., 4.], [1e6, 1e6]])
    metadata = [{'split': 'dev'}, {'split': 'dev'}, {'split': 'test'}]
    counts, sums = dc.dev_statistics(index, values, metadata, 4)
    np.testing.assert_array_equal(counts, [1, 1, 1, 0])
    np.testing.assert_array_equal(sums, [2, 3, 4, 0])


@pytest.fixture
def provenance_inputs():
    originals = [
        {'id': 'a', 'feature': 'row-a', 'split': 'dev', 'cluster': 17, 'value': 'first'},
        {'id': 'b', 'feature': 'row-a', 'split': 'test', 'cluster': 18, 'value': 'second'},
        {'id': 'c', 'feature': 'row-b', 'split': 'dev', 'cluster': 'group-c', 'value': 'off'},
    ]
    templates = {'row-a': {'values': ['first', 'second']},
                 'row-b': {'values': ['on', 'off']}}
    metadata = [{'id': item['id'], 'row': item['feature'], 'split': item['split'],
                 'cluster': str(item['cluster']),
                 'label': int(item['value'] == templates[item['feature']]['values'][0])}
                for item in originals]
    return metadata, originals, templates


def test_metadata_provenance_joins_by_id_and_preserves_frozen_truth(provenance_inputs):
    metadata, originals, templates = provenance_inputs
    # Hash-map joins must not rely on either file retaining collection order.
    dc.validate_metadata_provenance(metadata[::-1], originals, templates)
    assert [m['label'] for m in metadata] == [1, 0, 0]
    assert metadata[0]['cluster'] == '17'


@pytest.mark.parametrize('field,bad', [
    ('id', 'not-frozen'), ('row', 'row-b'), ('split', 'test'),
    ('cluster', 'changed-group'), ('label', 0), ('label', 2),
])
def test_changed_item_provenance_rejected(provenance_inputs, field, bad):
    metadata, originals, templates = provenance_inputs
    metadata[0][field] = bad
    with pytest.raises(ValueError):
        dc.validate_metadata_provenance(metadata, originals, templates)


def test_source_values_outside_two_frozen_template_values_are_rejected(provenance_inputs):
    metadata, originals, templates = provenance_inputs
    # Unknown source values must not silently become the negative class.
    originals[1]['value'] = 'third'
    with pytest.raises(ValueError):
        dc.validate_metadata_provenance(metadata, originals, templates)


@pytest.mark.parametrize('values', [['first'], ['first', 'second', 'third'], ['first', 'first']])
def test_template_must_have_exactly_two_distinct_frozen_values(provenance_inputs, values):
    metadata, originals, templates = provenance_inputs
    templates['row-a']['values'] = values
    with pytest.raises(ValueError):
        dc.validate_metadata_provenance(metadata, originals, templates)


@pytest.fixture
def gate_fixture(tmp_path, monkeypatch):
    code = tmp_path / 'code'
    code.mkdir()
    # This is public preregistration metadata, not experiment activations/results.
    (code / 'GATE_PLAN.20261025.json').write_bytes((HERE / 'GATE_PLAN.20261025.json').read_bytes())
    monkeypatch.setattr(dc, 'HERE', code)
    request = tmp_path / 'gate-request.json'
    request.write_text(json.dumps({'source_files': {'GATE_PLAN.20261025.json': dc.sha(code / 'GATE_PLAN.20261025.json')}}))
    folder = tmp_path / 'gate'
    folder.mkdir()
    gate = {'experiment': 'E35', 'stage': 'gate', 'status': 'PASS',
            'sample_sha256': dc.SAMPLE_SHA, 'request_sha256': dc.sha(request),
            'metrics': {'passed': True, 'n_tokens': 50000, 'd_model': 5120, 'd_sae': 81920,
                        'fvu': .25, 'dead_fraction': .099}}
    fixture = SimpleNamespace(code=code, request=request, folder=folder, gate=gate,
                              checkpoint=json.loads((code / 'GATE_PLAN.20261025.json').read_text())['sae']['sha256'])

    def seal():
        (folder / 'GATE_RESULT.json').write_text(json.dumps(gate))
        (folder / 'OUTPUT_SEAL.json').write_text(json.dumps({'status': gate['status'],
            'files': {'GATE_RESULT.json': dc.sha(folder / 'GATE_RESULT.json')}}))
    fixture.seal = seal
    seal()
    return fixture


def test_exact_sealed_passing_transfer_gate_accepts(gate_fixture):
    f = gate_fixture
    assert dc.verify_gate(f.folder, f.request, f.checkpoint) == f.gate


@pytest.mark.parametrize('field,bad', [
    ('status', 'FAIL'), ('status', 'INCOMPLETE'), ('experiment', 'E21'),
    ('stage', 'decomposition'), ('sample_sha256', 'a' * 64), ('request_sha256', 'b' * 64),
])
def test_semantically_wrong_gate_receipt_rejected_even_with_matching_seal(gate_fixture, field, bad):
    f = gate_fixture
    f.gate[field] = bad
    f.seal()
    with pytest.raises(ValueError):
        dc.verify_gate(f.folder, f.request, f.checkpoint)


@pytest.mark.parametrize('field,bad', [
    ('passed', False), ('n_tokens', 49999), ('fvu', .250000001), ('fvu', float('nan')),
    ('dead_fraction', .1), ('dead_fraction', True), ('d_sae', 16384), ('d_model', 5119),
])
def test_gate_metrics_threshold_or_dimension_mismatch_rejected(gate_fixture, field, bad):
    f = gate_fixture
    f.gate['metrics'][field] = bad
    f.seal()
    with pytest.raises(ValueError):
        dc.verify_gate(f.folder, f.request, f.checkpoint)


def test_changed_gate_bytes_are_rejected_without_recomputing_gate(gate_fixture):
    f = gate_fixture
    (f.folder / 'GATE_RESULT.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        dc.verify_gate(f.folder, f.request, f.checkpoint)


def test_changed_request_and_wrong_checkpoint_are_rejected(gate_fixture):
    f = gate_fixture
    with pytest.raises(ValueError, match='checkpoint'):
        dc.verify_gate(f.folder, f.request, '0' * 64)
    f.request.write_text(f.request.read_text() + '\n')
    with pytest.raises(ValueError, match='passing'):
        dc.verify_gate(f.folder, f.request, f.checkpoint)


def test_transfer_request_must_pin_the_current_frozen_sae_plan(gate_fixture):
    f = gate_fixture
    f.request.write_text(json.dumps({'source_files': {'GATE_PLAN.20261025.json': '0' * 64}}))
    f.gate['request_sha256'] = dc.sha(f.request)
    f.seal()
    with pytest.raises(ValueError, match='checkpoint'):
        dc.verify_gate(f.folder, f.request, f.checkpoint)


def test_fallback_gate_requires_its_own_checkpoint_and_normalization_binding(gate_fixture):
    f = gate_fixture
    f.gate.update(sae_checkpoint_sha256='1' * 64, sae_k=64, normalization_manifest_sha256='2' * 64)
    f.gate['metrics']['d_sae'] = 16384
    f.seal()
    assert dc.verify_gate(f.folder, f.request, '1' * 64)['sae_k'] == 64
    with pytest.raises(ValueError, match='fallback'):
        dc.verify_gate(f.folder, f.request, '3' * 64)
    f.gate['normalization_manifest_sha256'] = None
    f.seal()
    with pytest.raises(ValueError, match='fallback'):
        dc.verify_gate(f.folder, f.request, '1' * 64)


@pytest.fixture
def toy_pack(tmp_path, monkeypatch, provenance_inputs):
    monkeypatch.setattr(dc, 'ROOT', tmp_path)
    code = tmp_path / 'code'
    code.mkdir()
    monkeypatch.setattr(dc, 'HERE', code)
    # Only the production-size check is skipped. Provenance joins remain real.
    monkeypatch.setattr(dc, 'validate_production_metadata', lambda metadata: None)
    metadata, originals, templates = provenance_inputs
    pack = tmp_path / 'pack'
    pack.mkdir()
    (pack / 'items.json').write_text(json.dumps(metadata))
    input_items = [{field: x[field] for field in ('id', 'feature', 'split')} for x in originals]
    (pack / 'items.input.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in input_items))
    (pack / 'items.DO_NOT_STAGE.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in originals))
    (pack / 'templates.json').write_text(json.dumps(templates))
    for split in ('dev', 'test'):
        ids = [m['id'] for m in metadata if m['split'] == split]
        (pack / f'{split}_ids.json').write_text(json.dumps(ids))
    source_names = ('items.input.jsonl', 'items.DO_NOT_STAGE.jsonl', 'templates.json',
                    'dev_ids.json', 'test_ids.json')
    (code / 'DECOMPOSITION_PLAN.20261025.json').write_text(json.dumps({'population': {
        name + '_sha256': dc.sha(pack / name) for name in source_names}}))
    np.save(pack / 'decoder_norms.npy', np.ones(2))
    arrays = {name + suffix: np.tile(value, (len(metadata), 1))
              for name in dc.PRIMARY + dc.DESCRIPTIVE
              for suffix, value in (('_indices', np.array([0, 1])),
                                    ('_values', np.array([1., 1.])))}
    np.savez(pack / 'codes.npz', **arrays)
    approval = {'_validated': True, 'freeze_sha256': '1' * 64,
                'gate_result_sha256': '2' * 64, 'labels_seal_sha256': '3' * 64,
                'sae_checkpoint_sha256': '4' * 64,
                '_gate': {'metrics': {'d_sae': 2}, 'sae_k': 2}}

    def seal():
        receipt = {field: approval[field] for field in ('freeze_sha256', 'gate_result_sha256',
                                                       'labels_seal_sha256', 'sae_checkpoint_sha256')}
        receipt.update(status='COMPLETE', primary_encoding='encode_raw_difference_directly',
                       files={p.name: dc.sha(p) for p in pack.iterdir() if p.name != 'ENCODING_SEAL.json'})
        (pack / 'ENCODING_SEAL.json').write_text(json.dumps(receipt))
    seal()
    return SimpleNamespace(pack=pack, approval=approval, seal=seal, metadata=metadata)


def test_failed_numerical_load_consumes_analysis_guard_without_result(tmp_path, toy_pack):
    f = toy_pack
    parent = tmp_path / 'cache/g_agreement/understand/e35'
    out, other = parent / 'analysis', parent / 'different-analysis-name'
    (f.pack / 'codes.npz').write_text('invalid numerical archive')
    f.seal()
    with pytest.raises(ValueError):
        dc.analyze_pack(f.pack, f.approval, out)
    guard = parent / 'decomposition.analysis.RUN_ONCE.json'
    before = guard.read_bytes()
    assert out.is_dir() and not (out / 'RESULTS.json').exists()
    assert not (out / 'ANALYSIS_SEAL.json').exists()
    with pytest.raises(FileExistsError):
        dc.analyze_pack(f.pack, f.approval, other)
    assert guard.read_bytes() == before and not other.exists()


def test_analysis_rejects_unauthorized_or_out_of_cache_output_before_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(dc, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='authorization'):
        dc.analyze_pack(tmp_path / 'pack', {}, tmp_path / 'out')
    approval = {'_validated': True}
    with pytest.raises(ValueError, match='cache'):
        dc.analyze_pack(tmp_path / 'pack', approval, tmp_path / 'out')
    assert not (tmp_path / 'cache/g_agreement/understand/e35/decomposition.analysis.RUN_ONCE.json').exists()


@pytest.mark.parametrize('dimension', ['d_sae', 'k'])
def test_analysis_pack_dictionary_and_sparse_width_match_passed_gate(tmp_path, monkeypatch, toy_pack, dimension):
    f = toy_pack
    def selection_would_be_too_late(*args):
        pytest.fail('mismatched dictionary reached latent selection')
    monkeypatch.setattr(dc, 'select_top_latents', selection_would_be_too_late)
    if dimension == 'd_sae':
        f.approval['_gate']['metrics']['d_sae'] = 3
    else:
        f.approval['_gate']['sae_k'] = 3
    with pytest.raises(ValueError):
        dc.analyze_pack(f.pack, f.approval, tmp_path / 'cache/g_agreement/understand/e35/out')


def test_invalid_provenance_stops_before_consuming_analysis_guard(tmp_path, toy_pack):
    f = toy_pack
    f.metadata[0]['label'] = 0
    (f.pack / 'items.json').write_text(json.dumps(f.metadata))
    f.seal()
    parent = tmp_path / 'cache/g_agreement/understand/e35'
    with pytest.raises(ValueError, match='truth/row/cluster'):
        dc.analyze_pack(f.pack, f.approval, parent / 'out')
    assert not (parent / 'decomposition.analysis.RUN_ONCE.json').exists()
    assert not (parent / 'out').exists()


def test_artifact_seal_cannot_escape_its_folder(tmp_path):
    folder = tmp_path / 'artifact'
    folder.mkdir()
    outside = tmp_path / 'outside.json'
    outside.write_text('{}')
    (folder / 'SEAL.json').write_text(json.dumps({'files': {'../outside.json': dc.sha(outside)}}))
    with pytest.raises(ValueError, match='path'):
        dc.verify_seal(folder, 'SEAL.json')


def test_authorize_requires_committed_rubric_before_other_inputs(tmp_path):
    a = tmp_path / 'approval.json'
    a.write_text(json.dumps({'issuer': 'integrator', 'experiment': 'E35',
                             'rubric_committed': False, 'freeze_commit': '1' * 40}))
    with pytest.raises(ValueError, match='committed rubric'):
        dc.authorize(a)
