"""Synthetic CPU checks for the pretraining choices dated 2026-10-25."""
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path

import pytest
import torch


HERE = Path(__file__).resolve().parent


def load_module(name, filename):
    import sys
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fs = load_module('e35_fallback_sae_tested', 'fallback_sae.py')
adapter = load_module('e35_fallback_adapter_tested', 'sae.py')


@pytest.fixture(autouse=True)
def preserve_torch_determinism():
    previous = torch.are_deterministic_algorithms_enabled()
    yield
    torch.use_deterministic_algorithms(previous)


def tiny_config(**changes):
    base = replace(fs.FIXED_CONFIG, d_model=3, d_sae=8, k=2, auxiliary_k=4,
                   batch_size=4, target_tokens=10, dead_after_tokens=8)
    return replace(base, **changes)


def train_batch():
    return torch.tensor([[1., 0., 0.], [-1., 0., 0.],
                         [0., 2., 1.], [0., -2., -1.]])


def trainer(**changes):
    return fs.SAETrainer(config=tiny_config(**changes), synthetic=True)


def complete(instance):
    while instance.tokens_seen < instance.config.target_tokens:
        n = min(instance.config.batch_size, instance.config.target_tokens - instance.tokens_seen)
        instance.step(train_batch()[:n], first_position=instance.tokens_seen, split='train')
    return instance


def test_production_dimensions_hyperparameters_and_unpadded_batch_count_are_fixed():
    c = fs.FIXED_CONFIG
    assert (c.d_model, c.d_sae, c.k, c.seed) == (5120, 16384, 64, 20261025)
    assert (c.target_tokens // c.batch_size, c.target_tokens % c.batch_size) == (4882, 3328)
    assert (c.auxiliary_k, c.dead_after_tokens, c.auxiliary_weight) == (512, 1_000_000, 1 / 32)
    assert fs.NORMALIZATION_MANIFEST['input_transform'] == 'identity_raw_residual_float32'
    assert not fs.NORMALIZATION_MANIFEST['input_scale_fit']
    with pytest.raises(ValueError, match='fixed registered'):
        fs.SAETrainer(config=tiny_config())


def test_seeded_initialization_is_local_reproducible_and_column_normalized():
    torch.manual_seed(1)
    first = fs.TopKSAE(tiny_config())
    torch.manual_seed(928)
    second = fs.TopKSAE(tiny_config())
    for name in fs.PARAMETER_KEYS:
        torch.testing.assert_close(getattr(first, name), getattr(second, name), rtol=0, atol=0)
    torch.testing.assert_close(first.W_enc, first.W_dec.T)
    torch.testing.assert_close(torch.linalg.vector_norm(first.W_dec, dim=0), torch.ones(8))


def test_initial_biases_encode_centered_first_training_batch_without_external_transform():
    instance = trainer()
    x = train_batch() + torch.tensor([4., -3., 5.])
    instance._initialize(x)
    mean = x.mean(dim=0)
    torch.testing.assert_close(instance.model.b_dec, mean)
    torch.testing.assert_close(instance.model.b_enc, -(instance.model.W_enc @ mean))
    expected = instance.model.sparse_topk((x - mean) @ instance.model.W_enc.T, 2)
    torch.testing.assert_close(instance.model.encode(x), expected)
    assert instance.initial_statistics['source'] == 'first_training_minibatch_only'


def test_positive_topk_and_raw_affine_adapter_math_match_after_full_training(tmp_path):
    instance = complete(trainer())
    tensors = instance.checkpoint_tensors()
    assert set(tensors) == set(fs.PARAMETER_KEYS)
    assert all(t.dtype == torch.float32 and t.device.type == 'cpu' for t in tensors.values())
    checkpoint = tmp_path / 'synthetic.sae.pt'
    torch.save(tensors, checkpoint)
    loaded = torch.load(checkpoint, map_location='cpu', weights_only=True)
    frozen = adapter.QwenScopeSAE(loaded, k=2)
    x = train_batch() + 1.3
    actual = instance.model.encode(x)
    expected = frozen.encode(x)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    assert (actual >= 0).all() and (actual.gt(0).sum(dim=1) <= 2).all()
    torch.testing.assert_close(instance.model.decode(actual), frozen.decode(expected), rtol=0, atol=0)


def test_training_gradients_update_weights_preserve_unit_norm_and_count_final_partial():
    instance = trainer()
    before = instance.model.W_enc.detach().clone()
    first = instance.step(train_batch(), first_position=0, split='train')
    assert first['gradient_norm_before_clip'] > 0
    assert not torch.equal(instance.model.W_enc, before)
    complete(instance)
    assert (instance.tokens_seen, instance.steps) == (10, 3)
    torch.testing.assert_close(torch.linalg.vector_norm(instance.model.W_dec, dim=0), torch.ones(8))
    manifest = instance.completed_manifest()
    assert manifest['checkpoint_selection'] == 'final_only'
    assert manifest['data_passes'] == 1 and manifest['replayed_positions'] == 0
    assert manifest['optimizer_updates'] == 3 and manifest['training_tokens'] == 10
    assert manifest['synthetic'] is True


def test_decoder_gradient_projection_removes_only_radial_component():
    model = fs.TopKSAE(tiny_config())
    gradient = torch.arange(24, dtype=torch.float32).reshape(3, 8)
    model.W_dec.grad = gradient.clone()
    expected = gradient - model.W_dec * (gradient * model.W_dec).sum(dim=0, keepdim=True)
    model.project_decoder_gradient_()
    torch.testing.assert_close(model.W_dec.grad, expected)
    torch.testing.assert_close((model.W_dec.grad * model.W_dec).sum(dim=0), torch.zeros(8), atol=4e-6, rtol=0)


def test_auxiliary_loss_only_trains_dead_codes_and_detaches_main_residual():
    pre = torch.tensor([[5., 2., 1.], [4., 3., 1.]], requires_grad=True)
    decoder = torch.tensor([[1., 1., 0.], [0., 0., 1.]], requires_grad=True)
    residual = torch.zeros((2, 2), requires_grad=True)
    dead = torch.tensor([False, True, True])
    loss = fs.auxiliary_loss(pre, decoder, residual, dead, k=1, loss_scale=2.)
    # Selected dead amplitudes are 2 and 3; averaging over 4 coordinates,
    # then multiplying by 2, gives (4+9)/2.
    assert float(loss.detach()) == 6.5
    loss.backward()
    assert residual.grad is None
    torch.testing.assert_close(pre.grad[:, 0], torch.zeros(2))
    torch.testing.assert_close(pre.grad[:, 2], torch.zeros(2))
    assert (pre.grad[:, 1] > 0).all()
    torch.testing.assert_close(decoder.grad[:, 0], torch.zeros(2))


def test_auxiliary_no_dead_features_yields_zero_and_no_spurious_gradients():
    pre = torch.ones((2, 4), requires_grad=True)
    loss = fs.auxiliary_loss(pre, torch.ones((3, 4)), torch.ones((2, 3)),
                             torch.zeros(4, dtype=torch.bool), k=2, loss_scale=3.)
    assert float(loss.detach()) == 0
    loss.backward()
    torch.testing.assert_close(pre.grad, torch.zeros_like(pre))


def test_auxiliary_dead_window_uses_only_positive_main_firing_timestamps():
    instance = trainer(target_tokens=8, dead_after_tokens=8)
    instance._initialize(train_batch())
    with torch.no_grad():
        instance.model.W_enc.zero_()
        instance.model.b_enc.fill_(.5)
        instance.model.b_enc[:2] = 1.
    first = instance.step(train_batch(), first_position=0, split='train')
    assert first['dead_for_aux'] == 0 and first['auxiliary_loss'] == 0
    second = instance.step(train_batch(), first_position=4, split='train')
    assert second['dead_for_aux'] == 6 and second['auxiliary_loss'] > 0
    assert instance.last_fired[:2].tolist() == [8, 8]
    # Dead features fired in AuxK but never in the main TopK; no timestamp reset.
    assert instance.last_fired[2:].tolist() == [0] * 6


def test_initial_statistics_are_training_only_fixed_and_include_first_optimized_batch():
    instance = trainer()
    first = train_batch() + 4
    result = instance.step(first, first_position=0, split='train')
    statistics = dict(instance.initial_statistics)
    assert result['tokens_seen'] == 4 and result['step'] == 1
    assert statistics['tokens'] == 4
    mean = first.double().mean(dim=0)
    assert statistics['centered_mean_square'] == float((first.double() - mean).square().mean())
    assert statistics['mean_float32_sha256'] == hashlib.sha256(mean.float().numpy().tobytes()).hexdigest()
    instance.step(train_batch() + 100, first_position=4, split='train')
    assert instance.initial_statistics == statistics


@pytest.mark.parametrize('split,position', [('test', 0), ('holdout', 0), ('train', 1), ('train', True)])
def test_wrong_split_or_stream_offset_rejected_before_statistics_or_update(split, position):
    instance = trainer()
    before = {k: v.clone() for k, v in instance.model.state_dict().items()}
    with pytest.raises(ValueError, match='training-only'):
        instance.step(train_batch(), first_position=position, split=split)
    assert instance.initial_statistics is None and instance.tokens_seen == 0
    assert not instance.optimizer.state
    for key, value in before.items():
        torch.testing.assert_close(instance.model.state_dict()[key], value, rtol=0, atol=0)


def test_replay_extra_tokens_and_early_partial_batch_are_rejected():
    instance = trainer()
    with pytest.raises(ValueError, match='minibatch'):
        instance.step(train_batch()[:3], first_position=0, split='train')
    instance.step(train_batch(), first_position=0, split='train')
    with pytest.raises(ValueError, match='unreplayed'):
        instance.step(train_batch(), first_position=0, split='train')
    instance.step(train_batch(), first_position=4, split='train')
    with pytest.raises(ValueError, match='minibatch'):
        instance.step(train_batch(), first_position=8, split='train')
    instance.step(train_batch()[:2], first_position=8, split='train')
    with pytest.raises(ValueError, match='minibatch'):
        instance.step(train_batch(), first_position=10, split='train')
    assert (instance.tokens_seen, instance.steps) == (10, 3)


def test_incomplete_or_failed_training_cannot_export_or_restart():
    instance = trainer()
    with pytest.raises(ValueError, match='complete single pass'):
        instance.checkpoint_tensors()
    with pytest.raises(ValueError, match='complete single pass'):
        instance.completed_manifest()
    with pytest.raises(ValueError, match='centered energy'):
        instance.step(torch.ones((4, 3)), first_position=0, split='train')
    assert instance.failed
    with pytest.raises(RuntimeError, match='cannot be resumed'):
        instance.step(train_batch(), first_position=0, split='train')
    with pytest.raises(ValueError, match='complete single pass'):
        instance.checkpoint_tensors()


@pytest.mark.parametrize('problem', ['nan', 'inf', 'shape', 'integer'])
def test_invalid_raw_activation_batch_rejected_without_statistics(problem):
    instance = trainer()
    x = train_batch()
    if problem == 'nan':
        x[0, 0] = float('nan')
    elif problem == 'inf':
        x[0, 0] = float('inf')
    elif problem == 'shape':
        x = x[:, :2]
    else:
        x = x.to(torch.int64)
    with pytest.raises(ValueError):
        instance.step(x, first_position=0, split='train')
    assert instance.initial_statistics is None and instance.tokens_seen == 0


def test_repeated_complete_tiny_runs_are_bit_reproducible_on_cpu():
    first, second = complete(trainer()), complete(trainer())
    assert first.completed_manifest() == second.completed_manifest()
    for name, value in first.checkpoint_tensors().items():
        torch.testing.assert_close(value, second.checkpoint_tensors()[name], rtol=0, atol=0)


def test_forced_auxiliary_timing_is_scratch_only_and_cannot_export():
    with pytest.raises(ValueError, match='scratch-only'):
        fs.SAETrainer(timing_force_auxiliary=True)
    instance = fs.SAETrainer(config=tiny_config(target_tokens=4), synthetic=True,
                             timing_force_auxiliary=True)
    result = instance.step(train_batch(), first_position=0, split='train')
    assert result['dead_for_aux'] == 8 and result['auxiliary_loss'] > 0
    with pytest.raises(ValueError, match='complete single pass'):
        instance.checkpoint_tensors()
    with pytest.raises(ValueError, match='complete single pass'):
        instance.completed_manifest()
