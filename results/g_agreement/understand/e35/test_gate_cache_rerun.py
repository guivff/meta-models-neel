"""2026-10-25 §133(7): real offline lookup of the two-file staged SAE cache."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import huggingface_hub
from huggingface_hub.errors import LocalEntryNotFoundError
import pytest
import torch
from transformers import AutoModelForCausalLM


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    SPEC = importlib.util.spec_from_file_location("e35_cache_worker_under_test", HERE / "gate_worker.py")
    worker = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(worker)
    import sae
finally:
    sys.path.remove(str(HERE))


def pinned_config_bytes():
    # The pinned official config is 761 bytes, without a final newline. This
    # fixture reproduces its bytes, not a mocked checksum or config parser.
    config = {
        "model_type": "topk_sae",
        "hf_repo_id": "Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50",
        "base_model": "Qwen/Qwen3.5-27B",
        "d_model": 5120,
        "d_sae": 81920,
        "k": 50,
        "num_layers": 64,
        "layers": list(range(64)),
        "hook_point": "resid_post",
        "dtype": "float32",
    }
    data = json.dumps(config, indent=2).encode()
    expected = json.loads((HERE / "GATE_PLAN.20261025.json").read_text())["sae"]["config_sha256"]
    assert hashlib.sha256(data).hexdigest() == expected
    return data


@pytest.fixture
def staged_two_file_cache(tmp_path, monkeypatch):
    cache = tmp_path / "hub"
    snapshot = cache / ("models--" + sae.PINNED_REPOSITORY.replace("/", "--")) / "snapshots" / sae.PINNED_REVISION
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_bytes(pinned_config_bytes())
    (snapshot / sae.PINNED_FILENAME).write_bytes(b"tiny allocation stub; actual SAE checksum tested separately")
    assert sorted(p.name for p in snapshot.iterdir()) == ["config.json", "layer44.sae.pt"]
    # There are no branch refs, complete-snapshot metadata, other layers, or
    # external network requests in this cache. Use the real HF per-file resolver.
    target = tmp_path / "target"
    target.mkdir()
    (target / "tokenizer.json").write_text("{}")
    events = []
    real_download = huggingface_hub.hf_hub_download

    def file_lookup(repo_id, filename, **kwargs):
        events.append(("file", repo_id, filename, dict(kwargs)))
        assert repo_id == sae.PINNED_REPOSITORY
        assert kwargs["revision"] == sae.PINNED_REVISION
        assert kwargs["local_files_only"] is True
        assert filename in {"config.json", sae.PINNED_FILENAME}
        return real_download(repo_id, filename, cache_dir=cache, **kwargs)

    def target_lookup(repo_id, **kwargs):
        events.append(("snapshot", repo_id, dict(kwargs)))
        assert repo_id == worker.TARGET_REPO, "SAE lookup must not request a complete snapshot"
        assert kwargs == {"revision": worker.TARGET_REVISION, "local_files_only": True}
        return str(target)

    class ModelStub:
        model = SimpleNamespace(layers=[object() for _ in range(64)])

        def eval(self):
            events.append(("eval",))
            return self

        def requires_grad_(self, enabled):
            assert enabled is False
            events.append(("frozen",))
            return self

    model, sae_object = ModelStub(), object()

    def model_loader(path, **kwargs):
        assert Path(path) == target
        assert kwargs == {"dtype": torch.bfloat16, "device_map": "cuda", "local_files_only": True}
        events.append(("allocate_model",))
        return model

    def sae_loader(path, *, device):
        assert Path(path) == snapshot / sae.PINNED_FILENAME
        assert device == "cuda"
        assert Path(path).read_bytes().startswith(b"tiny allocation stub")
        events.append(("allocate_sae",))
        return sae_object

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", file_lookup)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", target_lookup)
    monkeypatch.setattr(AutoModelForCausalLM, "from_pretrained", staticmethod(model_loader))
    monkeypatch.setattr(sae.QwenScopeSAE, "from_checkpoint", staticmethod(sae_loader))
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    clock = SimpleNamespace(check=lambda: events.append(("clock",)))
    return SimpleNamespace(cache=cache, snapshot=snapshot, target=target, events=events,
                           model=model, sae=sae_object, clock=clock)


def test_gate_loads_real_offline_cache_with_exactly_two_staged_files(staged_two_file_cache):
    staged = staged_two_file_cache
    model, loaded_sae, tokenizer = worker.load_assets(staged.clock)
    assert model is staged.model and loaded_sae is staged.sae
    assert tokenizer == staged.target / "tokenizer.json"
    lookups = [e for e in staged.events if e[0] == "file"]
    assert len(lookups) == 2
    assert {e[2] for e in lookups} == {"config.json", "layer44.sae.pt"}
    first_allocation = next(i for i, e in enumerate(staged.events) if e[0] == "allocate_model")
    assert all(i < first_allocation for i, e in enumerate(staged.events) if e[0] == "file")
    assert sorted(p.relative_to(staged.cache).name for p in staged.cache.rglob("*") if p.is_file()) == [
        "config.json", "layer44.sae.pt"
    ]


@pytest.mark.parametrize("missing", ["config.json", "layer44.sae.pt"])
def test_missing_staged_file_fails_before_any_model_allocation(staged_two_file_cache, missing):
    staged = staged_two_file_cache
    (staged.snapshot / missing).unlink()
    with pytest.raises(LocalEntryNotFoundError):
        worker.load_assets(staged.clock)
    assert not any(e[0].startswith("allocate_") for e in staged.events)


def test_tampered_config_fails_before_any_model_allocation(staged_two_file_cache):
    staged = staged_two_file_cache
    config_path = staged.snapshot / "config.json"
    config = json.loads(config_path.read_text())
    config["k"] = 100
    config_path.write_text(json.dumps(config, indent=2))
    with pytest.raises(ValueError):
        worker.load_assets(staged.clock)
    assert not any(e[0].startswith("allocate_") for e in staged.events)
