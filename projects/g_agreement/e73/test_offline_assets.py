"""CPU-only frozen asset resolution; all model/adapter loads are synthetic stubs."""
from pathlib import Path
import sys
from types import SimpleNamespace

from huggingface_hub.errors import LocalEntryNotFoundError, OfflineModeIsEnabled
import pytest

from projects.g_agreement.core import config as C, readers


def offline_snapshot(monkeypatch, destination):
    calls = []
    def resolve(repo, **kwargs):
        calls.append((repo, kwargs))
        if kwargs.get("local_files_only") is not True:
            raise OfflineModeIsEnabled("synthetic remote tree lookup while offline")
        return str(destination)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setattr("huggingface_hub.snapshot_download", resolve)
    return calls


def expected(repo, revision, patterns):
    # No cache_dir override: retain the operator's configured HF cache.
    return repo, {"revision": revision, "allow_patterns": patterns,
                  "repo_type": None, "local_files_only": True}


def test_oracle_bind_resolves_exact_pinned_adapter_offline_and_keeps_liveness(tmp_path, monkeypatch):
    calls = offline_snapshot(monkeypatch, tmp_path)
    base, tokenizer, peft_calls, live_calls = object(), object(), [], []
    class PeftModel:
        @classmethod
        def from_pretrained(cls, model, path):
            peft_calls.append((model, path))
            return cls()
        def eval(self):
            return self
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=PeftModel))
    def liveness(model, path, ids):
        live_calls.append((model, path, ids))
        return {"synthetic_only": True}
    monkeypatch.setattr(readers, "assert_adapter_live", liveness)
    reader = readers.OLensReader(max_new_tokens=128, sampling={"do_sample": False})
    carrier_calls = []
    def carrier(layer):
        carrier_calls.append(layer)
        return [10, 11], 0, "marker", 10
    monkeypatch.setattr(reader, "carrier", carrier)
    target = SimpleNamespace(model=base, tokenizer=tokenizer)
    result = reader.bind(target)
    adapter = tmp_path / C.OLENS_SUBFOLDER
    assert calls == [expected(C.OLENS_REPO, C.OLENS_SHA, [C.OLENS_SUBFOLDER + "/*"])]
    assert peft_calls == [(base, str(adapter))]
    assert live_calls == [(target.model, adapter, [10, 11])] and carrier_calls == [C.LAYER]
    assert result is reader and reader.target is target and reader.liveness == {"synthetic_only": True}


def test_nla_bind_resolves_both_exact_pinned_paths_offline_and_keeps_liveness(tmp_path, monkeypatch):
    calls = offline_snapshot(monkeypatch, tmp_path)
    base_path = tmp_path / C.NLA_BASE_SUBFOLDER
    base_path.mkdir()
    (base_path / "nla_meta.yaml").write_text("synthetic metadata only")
    dtype, tok, base_model, meta = object(), object(), object(), {"synthetic_only": True}
    loads, adapter_calls, live_calls = [], [], []
    class PeftModel:
        @classmethod
        def from_pretrained(cls, model, path, **kwargs):
            adapter_calls.append((model, path, kwargs))
            return cls()
        def eval(self):
            return self
    def tokenizer_load(path):
        loads.append(("tokenizer", path))
        return tok
    def model_load(path, **kwargs):
        loads.append(("model", path, kwargs))
        return base_model
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(bfloat16=dtype))
    monkeypatch.setitem(sys.modules, "yaml", SimpleNamespace(safe_load=lambda _: meta))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=PeftModel))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=tokenizer_load),
        AutoModelForCausalLM=SimpleNamespace(from_pretrained=model_load)))
    reader = readers.NLAReader(max_new_tokens=512, sampling={"do_sample": False})
    def attach(model, tokenizer, metadata, device):
        assert tokenizer is tok and metadata is meta and device == "cuda"
        reader.model, reader.ids = model, [10, 11]
        return reader
    monkeypatch.setattr(reader, "attach", attach)
    def liveness(model, path, ids):
        live_calls.append((model, path, ids))
        return {"synthetic_only": True}
    monkeypatch.setattr(readers, "assert_adapter_live", liveness)
    result = reader.bind()
    adapter = tmp_path / C.NLA_ADAPTER_SUBFOLDER
    assert calls == [expected(C.NLA_REPO, C.NLA_SHA, [C.NLA_BASE_SUBFOLDER + "/*", C.NLA_META_FILE]),
                     expected(C.NLA_REPO, C.NLA_SHA, [C.NLA_ADAPTER_SUBFOLDER + "/*"])]
    assert loads == [("tokenizer", str(base_path)),
                     ("model", str(base_path), {"dtype": dtype, "device_map": "cuda"})]
    assert adapter_calls == [(base_model, str(adapter), {"torch_dtype": dtype})]
    assert live_calls == [(reader.model, adapter, [10, 11])]
    assert result is reader and reader.liveness == {"synthetic_only": True}


@pytest.mark.parametrize("repo,revision,patterns", [
    (C.OLENS_REPO, C.OLENS_SHA, [C.OLENS_SUBFOLDER + "/*"]),
    (C.NLA_REPO, C.NLA_SHA, [C.NLA_BASE_SUBFOLDER + "/*", C.NLA_META_FILE]),
    (C.NLA_REPO, C.NLA_SHA, [C.NLA_ADAPTER_SUBFOLDER + "/*"]),
])
def test_cache_miss_propagates_unchanged_without_online_fallback(monkeypatch, repo, revision, patterns):
    failure, calls = LocalEntryNotFoundError("synthetic cache miss"), []
    def missing(repo, **kwargs):
        calls.append((repo, kwargs))
        raise failure
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setattr("huggingface_hub.snapshot_download", missing)
    with pytest.raises(LocalEntryNotFoundError) as caught:
        readers.hf_dir(repo, revision, patterns)
    assert caught.value is failure
    assert calls == [expected(repo, revision, patterns)]
