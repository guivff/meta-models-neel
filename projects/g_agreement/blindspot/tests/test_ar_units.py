"""CPU contract tests only: stub weights are not empirical AR fidelity evidence."""
from contextlib import nullcontext
import json
from types import SimpleNamespace

import numpy as np
import torch

from projects.g_agreement.blindspot import ar_tests as ar
from projects.g_agreement.blindspot import protocol as P


def test_residual_retains_raw_activation_units():
    # Nonzero origins and unequal coordinate scales catch centered/whitened output.
    h = torch.tensor([[120., -30., 2.], [80., -10., 5.], [160., -60., 11.]])
    reconstructed = torch.tensor([[100., -28., 1.], [90., -14., 3.], [130., -50., 7.]])
    expected = torch.tensor([[20., -2., 1.], [-10., 4., 2.], [30., -10., 4.]])
    residual = ar.residual_activations(h, reconstructed)
    torch.testing.assert_close(residual, expected, rtol=0, atol=0)
    torch.testing.assert_close(residual + reconstructed, h, rtol=0, atol=0)
    assert torch.all(residual.mean(0) != 0)

    units = torch.tensor([.25, 8., 64.])
    origin = torch.tensor([512., -256., 32.])
    converted = ar.residual_activations(h * units + origin, reconstructed * units + origin)
    torch.testing.assert_close(converted, expected * units, rtol=0, atol=0)
    torch.testing.assert_close(converted / units, residual, rtol=0, atol=0)
    centered_prediction = reconstructed - reconstructed.mean(0)
    whitened_prediction = centered_prediction * torch.tensor([2., .5, 4.])
    assert not torch.allclose(residual, h - centered_prediction)
    assert not torch.allclose(residual, h - whitened_prediction)
    assert not torch.allclose(residual, h - reconstructed / reconstructed.norm(dim=1, keepdim=True))


def test_frozen_greedy_readout_flows_through_p3_reconstruct_in_raw_block44_units(tmp_path, monkeypatch):
    """Exercise collection/seals/P3 reconstruct with CPU doubles, no model download."""
    from mats.readers import olens
    from projects.g_agreement.w_claims import ar as p3_ar
    from transformers import AutoModelForCausalLM, AutoTokenizer

    h = torch.tensor([[120., -30., 2.], [80., -10., 5.], [160., -60., 11.]])
    raw_predictions = torch.tensor([[100., -28., 1.], [90., -14., 3.], [130., -50., 7.]])
    expected_residual = torch.tensor([[20., -2., 1.], [-10., 4., 2.], [30., -10., 4.]])
    frozen_texts = ["- first column\n- unfinished table ", "- parenthesis remains open", "- second column\n"]
    items = [{"id": f"synthetic:{i}", "feature": feature, "ids": [7, 8]}
             for i, feature in enumerate(["table_column", "parenthesis", "table_column"])]
    bank, target = tmp_path / "bank", tmp_path / "target"
    bank.mkdir(); target.mkdir()
    P.jsonl(bank / "items.input.jsonl", items)
    P.dump(bank / "templates.json", {})
    P.dump(bank / "provenance.json", {"synthetic_test_only": True})
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json"], "INPUTS_FROZEN_SYNTHETIC_TEST")
    np.save(target / "acts44.npy", h.numpy(), allow_pickle=False)
    P.dump(target / "items.order.json", [item["id"] for item in items])
    P.dump(target / "provenance.target.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json")})
    P.seal(target, ["acts44.npy", "items.order.json", "provenance.target.json"], "SCORES_SEALED_SYNTHETIC_TEST")

    # Real file/hash checks run on inert fixtures, while admission is replaced with
    # an explicitly synthetic context; this receipt cannot authorize GPU work.
    asset_paths = {}
    for name in ("model", "olens", "ar"):
        path = tmp_path / f"synthetic_{name}.txt"
        path.write_text("CPU test fixture only\n")
        asset_paths[name] = str(path)
    assets = tmp_path / "assets.json"
    P.dump(assets, {**asset_paths, "files": [{"path": path, "sha256": P.sha(path)}
                                           for path in asset_paths.values()]})
    assignment, whitener = tmp_path / "synthetic_assignment.json", tmp_path / "synthetic_whitener.txt"
    P.dump(assignment, {"synthetic_cpu_test_only": True})
    whitener.write_text("poison whitener fixture; never applied\n")
    admitted = []

    def cpu_test_context(phase, receipt):
        assert phase == "residual" and receipt == assignment
        admitted.append(phase)
        return nullcontext()

    monkeypatch.setattr(ar, "_compute", cpu_test_context)
    monkeypatch.setattr(torch.Tensor, "cuda", lambda self, *args, **kwargs: self)
    model, ol_tokenizer = SimpleNamespace(), object()
    model.eval = lambda: model

    def load_model(path, **kwargs):
        assert path == asset_paths["model"]
        assert kwargs == {"dtype": torch.bfloat16, "device_map": "cuda", "local_files_only": True}
        return model

    def load_ol_tokenizer(path, **kwargs):
        assert path == asset_paths["model"] and kwargs == {"local_files_only": True}
        return ol_tokenizer

    seen_activations, readout_cursor = [], 0

    class OracleDouble:
        def verbalize(self, acts, *, layer, k, sampling, batch):
            nonlocal readout_cursor
            assert layer == 44 and k == 1 and batch == 2
            assert sampling.temperature == 0 and sampling.max_new_tokens == 256
            torch.testing.assert_close(acts, h[readout_cursor:readout_cursor + len(acts)], rtol=0, atol=0)
            seen_activations.append(acts.clone())
            texts = frozen_texts[readout_cursor:readout_cursor + len(acts)]
            readout_cursor += len(acts)
            return [[text] for text in texts]

    def load_ol(model_arg, tokenizer_arg, *, lora_dir):
        assert model_arg is model and tokenizer_arg is ol_tokenizer
        assert lora_dir == asset_paths["olens"]
        return OracleDouble()

    monkeypatch.setattr(AutoModelForCausalLM, "from_pretrained", staticmethod(load_model))
    monkeypatch.setattr(AutoTokenizer, "from_pretrained", staticmethod(load_ol_tokenizer))
    monkeypatch.setattr(olens, "load_olens", load_ol)
    common = dict(bank=bank, target=target, assets=assets, assignment=assignment, batch=2)
    readouts = tmp_path / "readouts"
    ar.collect_readouts(SimpleNamespace(**common, out=readouts))
    torch.testing.assert_close(torch.cat(seen_activations), h, rtol=0, atol=0)
    frozen_rows = P.rows(readouts / "readouts.jsonl")
    assert frozen_rows == [{"id": item["id"], "text": text} for item, text in zip(items, frozen_texts)]
    readout_hash = P.sha(readouts / "SCORE_SEAL.json")
    readout_provenance = json.loads((readouts / "provenance.json").read_text())
    assert readout_provenance["decoding"] == {"layer": 44, "temperature": 0, "k": 1, "max_new_tokens": 256}

    seen_texts, ar_calls = [], []

    class TokenizerDouble:
        def __call__(self, texts, **kwargs):
            assert kwargs == dict(add_special_tokens=False, return_tensors="pt", padding=True, truncation=False)
            seen_texts.extend(texts)
            indices = torch.tensor([[frozen_texts.index(text) + 1] for text in texts])
            return {"input_ids": indices, "attention_mask": torch.ones_like(indices)}

    class ReconstructorDouble:
        layers = [20, 44, 60]
        tag_ids = torch.tensor([[98, 99]])
        backbone = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=1024))

        def __call__(self, input_ids, attention_mask, *, layer_idx):
            assert layer_idx == 1  # P3's layers.index(44), not a centered/whitened representation.
            assert input_ids.device.type == attention_mask.device.type == "cpu"
            assert torch.all(attention_mask == 1)
            ar_calls.append(input_ids[:, 0].tolist())
            prediction = raw_predictions[input_ids[:, 0] - 1]
            # The second output position is deliberately wrong: real P3 reconstruct
            # must take [:, 0] as its registered activation prediction position.
            return torch.stack((prediction, torch.full_like(prediction, -999.)), dim=1)

    class PoisonWhitener:
        def __getattr__(self, name):
            raise AssertionError(f"Raw residual collection must not apply whitener.{name}")

    def load_ar(source, whitener_path, ar_dir, model_path):
        assert source == tmp_path / "synthetic_official"
        assert whitener_path == whitener
        assert ar_dir == asset_paths["ar"] and model_path == asset_paths["model"]
        return ReconstructorDouble(), TokenizerDouble(), PoisonWhitener()

    monkeypatch.setattr(p3_ar, "load_reconstructor", load_ar)
    # p3_ar.reconstruct itself is deliberately not mocked.
    residuals = tmp_path / "residuals"
    ar.collect_residuals(SimpleNamespace(**common, readouts=readouts, official=tmp_path / "synthetic_official",
                                         whitener=whitener, out=residuals))
    assert seen_texts == frozen_texts and ar_calls == [[1, 2], [3]]
    assert admitted == ["residual", "residual"]
    assert P.sha(readouts / "SCORE_SEAL.json") == readout_hash
    np.testing.assert_array_equal(np.load(residuals / "recon.npy", allow_pickle=False), raw_predictions.numpy())
    np.testing.assert_array_equal(np.load(residuals / "residual.npy", allow_pickle=False), expected_residual.numpy())
    provenance = json.loads((residuals / "provenance.json").read_text())
    assert provenance["raw_activation_space"] == "block44"
    assert provenance["readout_score_seal_sha256"] == readout_hash
    assert provenance["readout_provenance"] == readout_provenance
    assert json.loads((residuals / "ids.json").read_text()) == [item["id"] for item in items]
    assert set(P.verify(residuals, "SCORE_SEAL.json")["files"]) == {"recon.npy", "residual.npy", "ids.json", "provenance.json"}
    torch.testing.assert_close(ar._residuals(residuals, bank, target, items, h), raw_predictions, rtol=0, atol=0)
