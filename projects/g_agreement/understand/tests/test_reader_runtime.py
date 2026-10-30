"""CPU-only contract, parity and finite-difference tests; no real model load."""
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from projects.g_agreement.understand.reader_runtime import ReaderRuntime, RuntimePool, _load_unembedding
from mats.readers.olens import OracleLens
from mats.readers.nla import NLA, paired_logodds_templates
from mats.readers.jlens import JLensReader


class Tokenizer:
    pad_token_id = 0

    def encode(self, text, add_special_tokens=False):
        return [ord(c) % 63 + 1 for c in text]


class CausalBlock(torch.nn.Module):
    def __init__(self, width):
        super().__init__()
        self.linear = torch.nn.Linear(width, width)

    def forward(self, h):
        return h + torch.tanh(self.linear(h.cumsum(1))) / 4


class TinyModel(torch.nn.Module):
    def __init__(self, width=6, n_layers=4):
        super().__init__()
        torch.manual_seed(37)
        self.embed = torch.nn.Embedding(64, width)
        self.layers = torch.nn.ModuleList([CausalBlock(width) for _ in range(n_layers)])
        self.lm_head = torch.nn.Linear(width, 64, bias=False)
        self.config = SimpleNamespace(num_hidden_layers=n_layers)
        self.forward_count = 0
        self.base_entries = 0

    def get_input_embeddings(self):
        return self.embed

    def get_output_embeddings(self):
        return self.lm_head

    @contextmanager
    def disable_adapter(self):
        self.base_entries += 1
        yield

    def forward(self, input_ids=None, inputs_embeds=None, attention_mask=None,
                logits_to_keep=0, use_cache=False):
        self.forward_count += 1
        h = self.embed(input_ids) if inputs_embeds is None else inputs_embeds
        for block in self.layers:
            h = block(h)
        return SimpleNamespace(logits=self.lm_head(h[:, -logits_to_keep:] if logits_to_keep else h))


def oracle():
    return OracleLens(TinyModel(), Tokenizer(), alpha=2.3, device="cpu", _slots={44: ([2, 8, 5, 6], 1)})


def nla():
    model = TinyModel()
    reader = NLA(av=model, tok=Tokenizer(), ar=None, value_head=None, meta={},
                 prompt_ids=[2, 8, 5, 6], marker=1, device="cpu")
    model.layers[1].register_forward_hook(reader._hook)
    return reader


def vectors():
    torch.manual_seed(98)
    return torch.randn(3, 6)


PAIRS = [("a", "bb"), ("cc", "d")]


@pytest.mark.parametrize("name,factory", [("olens", oracle), ("nla", nla)])
def test_native_score_parity_and_finite_difference(name, factory):
    reader = factory()
    runtime = ReaderRuntime(name, reader)
    h = vectors()
    if name == "olens":
        expected = reader.paired_logodds_templates(h, 44, PAIRS).mean(0)
    else:
        expected = paired_logodds_templates(reader, h, PAIRS).mean(0)
    assert torch.allclose(runtime.asked(h, PAIRS).detach(), expected, atol=3e-6, rtol=0)
    out = runtime.gradients(h, PAIRS)
    assert torch.allclose(out["scores"], expected, atol=3e-6, rtol=0)
    direction = torch.randn_like(h)
    eps = 1e-3
    finite = (runtime.asked(h + eps*direction, PAIRS) - runtime.asked(h - eps*direction, PAIRS)) / (2*eps)
    exact = (out["gradients"] * direction).sum(-1)
    assert torch.allclose(finite, exact, atol=3e-3, rtol=0.02)
    assert all(p.grad is None and not p.requires_grad for p in runtime.model.parameters())
    assert all(len(b._forward_hooks) == (1 if name == "nla" and i == 1 else 0)
               for i, b in enumerate(runtime.model.layers))


@pytest.mark.parametrize("name,factory", [("olens", oracle), ("nla", nla)])
def test_single_forward_capture_and_injection_order(name, factory):
    runtime = ReaderRuntime(name, factory())
    h = vectors()
    before = runtime.model.forward_count
    out = runtime.capture(h)
    assert runtime.model.forward_count - before == 1
    assert out["residuals"].shape == (3, 4, 2, 6)
    assert out["positions"] == ["injection", "preanswer"]
    assert out["layers"] == [0, 1, 2, 3]
    assert not out["residuals"].requires_grad
    if name == "nla":
        # Before block-1 injection all inputs are identical; after it they differ.
        assert torch.equal(out["residuals"][0, 0], out["residuals"][1, 0])
        assert not torch.equal(out["residuals"][0, 1, 0], out["residuals"][1, 1, 0])
    else:
        expected = runtime.reader.alpha * h / h.norm(dim=-1, keepdim=True)
        assert torch.allclose(out["input_stage"][:, 0], expected)
    # No labels or feature candidates are present in the captured head.
    assert len(out["head_ids"]) == (4 if name == "olens" else 4+len("<explanation>\n"))


def test_jlens_native_parity_gradient_and_no_fake_layers():
    torch.manual_seed(3)
    reader = JLensReader({44: torch.randn(6, 6)}, torch.randn(64, 6), Tokenizer(), device="cpu")
    runtime = ReaderRuntime("jlens", reader)
    h = vectors()
    pairs = [("a", "b"), ("c", "d")]
    expected = torch.stack([reader.paired_logodds(h, 44, [a], [b]) for a, b in pairs]).mean(0)
    result = runtime.gradients(h, pairs)
    assert torch.allclose(expected, result["scores"], atol=1e-6)
    direction = torch.randn_like(h)
    eps = 1e-3
    fd = (runtime.asked(h+eps*direction, pairs)-runtime.asked(h-eps*direction, pairs))/(2*eps)
    assert torch.allclose(fd, (result["gradients"]*direction).sum(-1), atol=2e-4)
    captured = runtime.capture(h)
    assert captured["status"] == "NOT_APPLICABLE_NO_DECODER"
    assert captured["residuals"] is None and captured["layers"] == []
    assert torch.allclose(captured["stages"]["J_h"], h @ reader.J[44].T)
    with pytest.raises(ValueError, match="NO_TOKEN_VARIANT"):
        runtime.gradients(h, [("long", "words"), ("also", "long")])


def test_target_exact_full_logit_jvp_and_padding():
    runtime = ReaderRuntime("target", oracle())
    h = vectors()[:2]
    u = torch.randn_like(h)
    sequences = [[3, 5, 8, 2], [3, 5, 9]]
    result = runtime.target_directional(h, sequences, u, layer=1)
    assert result["derivatives"].shape == (2, 64)
    assert result["method"] == "exact_autograd_jvp_all_next_token_logits"
    assert runtime.model.base_entries == 1
    assert torch.allclose(result["rms"], result["derivatives"].square().mean(-1).sqrt())

    # Independently replay unpadded sequences and finite-difference the injected
    # last-token residual; verifies position selection and the full-vocab JVP.
    def direct(x, seq):
        ids = torch.tensor([seq])
        def edit(_m, _i, y):
            y = y.clone()
            y[:, -1] = x
            return y
        handle = runtime.model.layers[1].register_forward_hook(edit)
        try:
            return runtime.model(input_ids=ids, logits_to_keep=1).logits[0, -1]
        finally:
            handle.remove()

    eps = 1e-3
    expected = torch.stack([(direct(x+eps*v, seq)-direct(x-eps*v, seq))/(2*eps)
                            for x, v, seq in zip(h, u, sequences)])
    assert torch.allclose(result["derivatives"], expected, atol=4e-4, rtol=0.003)
    assert not runtime.model.lm_head._forward_pre_hooks


def test_hook_cleanup_on_exception():
    runtime = ReaderRuntime("nla", nla())
    original = runtime.model.forward
    def broken(**kwargs):
        raise RuntimeError("deliberate")
    runtime.model.forward = broken
    with pytest.raises(RuntimeError, match="deliberate"):
        runtime.capture(vectors())
    runtime.model.forward = original
    assert [len(block._forward_hooks) for block in runtime.model.layers] == [0, 1, 0, 0]
    assert runtime.reader._vec.get("v") is None


@pytest.mark.parametrize("tied", [False, True])
def test_unembedding_loads_only_selected_tensor(tmp_path, monkeypatch, tied):
    """The index path selects a single tensor, with no model or whole-shard load."""
    import safetensors
    key = "model.embed_tokens.weight" if tied else "lm_head.weight"
    selected = torch.arange(24, dtype=torch.bfloat16).reshape(6, 4)
    (tmp_path / "config.json").write_text(json.dumps({"tie_word_embeddings": tied,
        "text_config": {"vocab_size": 6, "hidden_size": 4}}))
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {
        key: "shard-2.safetensors", "model.layers.0.attention.weight": "shard-1.safetensors"}}))
    calls = []

    class Archive:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get_tensor(self, requested):
            calls.append(("tensor", requested))
            assert requested == key
            return selected

    def open_archive(path, framework, device):
        calls.append(("open", path, framework, device))
        assert path == str(tmp_path / "shard-2.safetensors")
        return Archive()

    (tmp_path / "shard-2.safetensors").touch()
    monkeypatch.setattr(safetensors, "safe_open", open_archive)
    result = _load_unembedding(tmp_path, "cpu")
    assert torch.equal(result, selected.float()) and result.dtype == torch.float32
    assert len(calls) == 2 and calls[1] == ("tensor", key)
    if tied:
        config = json.loads((tmp_path / "config.json").read_text())
        config["tie_word_embeddings"] = False
        (tmp_path / "config.json").write_text(json.dumps(config))
        with pytest.raises(ValueError, match="uniquely"):
            _load_unembedding(tmp_path, "cpu")


def test_runtime_pool_loads_once_aliases_target_and_offloads_before_activation():
    events = []
    loads = []

    class Movable:
        def __init__(self, name):
            self.name = name
        def to(self, device):
            events.append((self.name, str(device)))
            return self

    def factory(name, assets_path, device):
        loads.append((name, assets_path, device))
        reader = SimpleNamespace(device=device)
        model = Movable(name)
        if name == "jlens":
            reader.J = {44: Movable("J44")}
            reader.W_U = Movable("W_U")
            reader._denom = {44: Movable("denom44")}
            reader.final_norm = None
            model = None
        return SimpleNamespace(name=name, device=torch.device(device), reader=reader, model=model)

    pool = RuntimePool("pinned-assets.json", loader=factory)
    assert loads == [(name, "pinned-assets.json", "cpu") for name in ("olens", "nla", "jlens")]
    assert pool.get("target") is pool.get("olens")
    assert pool.get("target").model is pool.get("olens").model
    assert events == []
    assert pool.activate("olens") is pool.get("olens")
    pool.activate("target")  # No duplicate model move for the alias.
    pool.activate("nla")
    pool.activate("jlens")
    pool.activate("target")
    assert events == [
        ("olens", "cuda"), ("olens", "cpu"), ("nla", "cuda"),
        ("nla", "cpu"), ("J44", "cuda"), ("W_U", "cuda"), ("denom44", "cuda"),
        ("J44", "cpu"), ("W_U", "cpu"), ("denom44", "cpu"), ("olens", "cuda"),
    ]
    assert len(loads) == 3 and pool.active_name == "target"
    assert pool.get("olens").reader.device == "cuda"
    assert pool.get("nla").reader.device == "cpu"
    assert pool.get("jlens").reader.device == "cpu"
    pool.offload()
    assert events[-1] == ("olens", "cpu") and pool.active_name is None
    with pytest.raises(ValueError, match="unknown"):
        pool.activate("made-up-reader")


def _write_unembedding_fixture(root, *, indexed=True):
    """A real tiny safetensors checkpoint, optionally in an HF snapshot layout."""
    from safetensors.torch import save_file
    root.mkdir(parents=True)
    selected = torch.arange(24, dtype=torch.bfloat16).reshape(6, 4)
    (root / "config.json").write_text(json.dumps({"vocab_size": 6, "hidden_size": 4}))
    shard_name = "model-00002-of-00002.safetensors" if indexed else "model.safetensors"
    shard = root / shard_name
    save_file({"lm_head.weight": selected}, str(shard))
    if indexed:
        (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {
            "lm_head.weight": shard_name}}))
    return selected, shard


@pytest.mark.parametrize("indexed", [False, True])
def test_unembedding_real_flat_and_hf_snapshot_blob_symlink(tmp_path, indexed):
    selected, flat_shard = _write_unembedding_fixture(tmp_path / "flat", indexed=indexed)
    assert torch.equal(_load_unembedding(flat_shard.parent, "cpu"), selected.float())

    repo = tmp_path / "hub" / "models--Qwen--Qwen3.6-27B"
    snapshot = repo / "snapshots" / "pinned-revision"
    selected, shard = _write_unembedding_fixture(snapshot, indexed=indexed)
    blobs = repo / "blobs"
    blobs.mkdir()
    blob = blobs / "1234567890abcdef"
    shard.rename(blob)
    shard.symlink_to(Path("../../blobs") / blob.name)
    assert torch.equal(_load_unembedding(snapshot, "cpu"), selected.float())


@pytest.mark.parametrize("escape", ["cross_repository", "outside", "blob_directory_symlink"])
def test_unembedding_rejects_snapshot_symlink_escape(tmp_path, escape):
    repo = tmp_path / "hub" / "models--Qwen--Qwen3.6-27B"
    snapshot = repo / "snapshots" / "pinned-revision"
    _, shard = _write_unembedding_fixture(snapshot)
    blobs = repo / "blobs"
    if escape == "cross_repository":
        destination = repo.parent / "models--different--model" / "blobs"
        blobs.mkdir()
    else:
        destination = tmp_path / "outside"
    destination.mkdir(parents=True)
    if escape == "blob_directory_symlink":
        blobs.symlink_to(destination, target_is_directory=True)
        target = blobs / "blobhash"
    else:
        target = destination / "blobhash"
    shard.rename(target)
    shard.symlink_to(target)
    with pytest.raises(ValueError, match="outside pinned"):
        _load_unembedding(snapshot, "cpu")


@pytest.mark.parametrize("index_path", ["absolute", "traversal"])
def test_unembedding_rejects_index_absolute_and_traversal_even_with_local_target(tmp_path, index_path):
    root = tmp_path / "flat"
    _, shard = _write_unembedding_fixture(root)
    name = str(shard) if index_path == "absolute" else "../flat/" + shard.name
    (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"lm_head.weight": name}}))
    with pytest.raises(ValueError, match="relative without traversal"):
        _load_unembedding(root, "cpu")


def test_existing_asset_hash_validation_rejects_mutated_hf_blob(tmp_path, monkeypatch):
    """The new path exception leaves W1's full asset SHA validation in force."""
    from projects.g_agreement.blindspot import protocol as P
    from projects.g_agreement.blindspot.run import _assets
    from safetensors.torch import save_file

    repo = tmp_path / "hub" / "models--Qwen--Qwen3.6-27B"
    snapshot = repo / "snapshots" / "pinned-revision"
    selected, shard = _write_unembedding_fixture(snapshot)
    (snapshot / "tokenizer.json").write_text("{}")
    blobs = repo / "blobs"
    blobs.mkdir()
    blob = blobs / "blobhash"
    shard.rename(blob)
    shard.symlink_to(Path("../../blobs") / blob.name)
    pinned_root = tmp_path / "registration"
    pinned_manifest = pinned_root / "projects/g_agreement/manifest/assets.json"
    pinned_manifest.parent.mkdir(parents=True)
    pinned_manifest.write_text(json.dumps({"target": {"revision": "pinned-revision", "files_needed": {
        "tokenizer.json_sha256": P.sha(snapshot / "tokenizer.json")}},
        "readers": {name: {"revision": "reader-revision"} for name in ("olens", "nla", "jlens")}}))
    manifest = tmp_path / "assets.json"
    manifest.write_text(json.dumps({"model": str(snapshot), "revisions": {"model": "pinned-revision"},
        "files": [{"path": str(path), "sha256": P.sha(path)} for path in snapshot.rglob("*") if path.is_file()]}))
    monkeypatch.setattr(P, "ROOT", pinned_root)
    assert _assets(manifest, names=("model",))["model"] == str(snapshot)
    assert torch.equal(_load_unembedding(snapshot, "cpu"), selected.float())
    save_file({"lm_head.weight": selected + 1}, str(blob))
    with pytest.raises(ValueError, match="asset hash mismatch"):
        _assets(manifest, names=("model",))


@pytest.mark.parametrize("indexed", [False, True])
@pytest.mark.parametrize("layout", ["hub_blobs", "arbitrary_weights"])
def test_unembedding_hash_pinned_weights_store(tmp_path, monkeypatch, indexed, layout):
    from projects.g_agreement.understand import reader_runtime as runtime
    from projects.g_agreement.blindspot.protocol import sha
    from safetensors.torch import save_file

    weights = tmp_path / "weights"
    monkeypatch.setattr(runtime, "WEIGHTS_ROOT", weights)
    snapshot = weights / "hub/models--Qwen--Qwen3.6-27B/snapshots/pinned-revision"
    selected, shard = _write_unembedding_fixture(snapshot, indexed=indexed)
    digest = sha(shard)
    blob = (weights / "hub/blobs" / digest[:2] / digest if layout == "hub_blobs"
            else weights / "another-store/arbitrary-name")
    blob.parent.mkdir(parents=True)
    shard.rename(blob)
    shard.symlink_to(blob)
    hashes = {str(blob.resolve()): digest}
    assert torch.equal(_load_unembedding(snapshot, "cpu", pinned_hashes=hashes), selected.float())
    with pytest.raises(ValueError, match="missing pinned hash"):
        _load_unembedding(snapshot, "cpu")
    save_file({"lm_head.weight": selected + 1}, str(blob))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _load_unembedding(snapshot, "cpu", pinned_hashes=hashes)


@pytest.mark.parametrize("target_kind", ["outside", "directory", "dangling"])
def test_shared_store_rejects_invalid_final_target(tmp_path, monkeypatch, target_kind):
    from projects.g_agreement.understand import reader_runtime as runtime
    from projects.g_agreement.blindspot.protocol import sha

    weights = tmp_path / "weights"
    monkeypatch.setattr(runtime, "WEIGHTS_ROOT", weights)
    snapshot = weights / "hub/models--Qwen--Qwen3.6-27B/snapshots/pinned-revision"
    _, shard = _write_unembedding_fixture(snapshot)
    digest = sha(shard)
    target = tmp_path / "outside" if target_kind == "outside" else weights / "shared"
    if target_kind == "outside":
        shard.rename(target)
    else:
        shard.unlink()
        if target_kind == "directory":
            target.mkdir()
    intermediate = weights / "link"
    intermediate.symlink_to(target)
    shard.symlink_to(intermediate)
    with pytest.raises(ValueError, match="outside pinned|regular file"):
        _load_unembedding(snapshot, "cpu", pinned_hashes={str(target.resolve()): digest})


@pytest.mark.parametrize('name,factory',[('olens',oracle),('nla',nla)])
def test_single_activation_gradients_equal_previous_batch(name,factory):
    runtime=ReaderRuntime(name,factory())
    h=vectors()
    old=runtime.gradients(h,PAIRS,batch=32)
    new=runtime.gradients(h,PAIRS)
    assert torch.allclose(old['scores'],new['scores'],atol=3e-6,rtol=0)
    assert torch.allclose(old['gradients'],new['gradients'],atol=3e-6,rtol=0)


def test_offload_retains_weight_views_and_copies_activation():
    runtime=ReaderRuntime('olens',oracle())
    hooks=runtime._offload_saved()
    weight=runtime.model.layers[0].linear.weight.T
    _,packed=hooks.pack_hook(weight)
    assert packed.untyped_storage().data_ptr()==weight.untyped_storage().data_ptr()
    activation=vectors().requires_grad_(True)
    packed=hooks.pack_hook(activation)
    assert packed[1].untyped_storage().data_ptr()!=activation.untyped_storage().data_ptr()
    assert torch.equal(hooks.unpack_hook(packed),activation)
