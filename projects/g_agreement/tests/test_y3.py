"""Phase Y3 (BRIEF_Y §Y3) tests, CPU only: SkipLensReader on the tiny MOCK model with a fake PEFT adapter dir
(prompt / marker / per-row hook / LO sign convention / coexistence with a second named adapter), the R-lens format
inspection, the SAE module (TopK exactly k active, FVE of a perfect reconstruction = 1, shuffled null lower, sparse
probe on a planted signal), the collector on tmp paths (X1 / X2 / X3 stages + SAE FVE and probe rows, resumable), and
analyze end to end on synthetic rows incl. the blindness-map extension. Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_y3.py -q``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")
peft = pytest.importorskip("peft")
yaml = pytest.importorskip("yaml")

from projects.g_agreement import x_blindness_map as XB  # noqa: E402
from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.core import states as S  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402
from projects.g_agreement.x1_bank import analyze as X1A  # noqa: E402
from projects.g_agreement.x1_bank import collect as X1  # noqa: E402
from projects.g_agreement.x2_causal import collect as X2  # noqa: E402
from projects.g_agreement.y3_readers import analyze as YA  # noqa: E402
from projects.g_agreement.y3_readers import collect as YC  # noqa: E402
from projects.g_agreement.y3_readers import sae as SAE  # noqa: E402

G_DIR = REPO / "projects" / "g_agreement"
RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj", "in_proj_qkv", "in_proj_z", "in_proj_a", "in_proj_b", "out_proj"]


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(C, "DEV_EXTRA_LAYERS", ())
    yield


# ------------------------------------------------------------------ fake adapter dirs
def fake_adapter_dir(tmp_path: Path, name: str, seed: int) -> Path:
    """A real PEFT LoRA (r=4, the 12 skip-lens module types) with non-zero B so that it is not inert, saved with the
    skip-lens nla_meta.yaml (mock marker/neighbours)."""
    from peft import LoraConfig, get_peft_model

    g = torch.Generator().manual_seed(seed)  # tiny_model() reseeds the global RNG, so perturb B with an explicit generator
    pm = get_peft_model(tiny_model(), LoraConfig(r=4, lora_alpha=8, use_rslora=True, target_modules=LORA_TARGETS, task_type="CAUSAL_LM"))
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if "lora_B" in n:
                p.copy_(torch.randn(p.shape, generator=g) * 0.2)
    d = tmp_path / name
    pm.save_pretrained(str(d))
    meta = mock_meta(FakeTok())
    (d / C.SKIPLENS_META_FILE).write_text(yaml.safe_dump(meta, allow_unicode=True))
    return d


def fresh_target() -> M.Target:
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


# ================================================================== SkipLensReader
def test_skiplens_bind_prompt_marker_hook(tmp_path):
    from peft import PeftModel

    ad = fake_adapter_dir(tmp_path, "skip_a_dir", 11)
    target = fresh_target()
    rd = R.SkipLensReader("a", max_new_tokens=4).bind(target, adapter_dir=ad, check=True)
    assert rd.name == "skip_a" and rd.adapter_name == "skip_a" and isinstance(target.model, PeftModel)
    assert list(target.model.peft_config) == ["skip_a"]
    assert rd.liveness["all_matched"] and rd.liveness["adapter_name"] == "skip_a" and rd.liveness["max_abs_logit_delta"] > 1e-3
    # actor prompt: one user turn, thinking off, marker between its canonical neighbours
    tok = rd.tokenizer
    meta = rd.meta["tokens"]
    assert rd.ids[rd.marker] == meta["injection_token_id"]
    assert (rd.ids[rd.marker - 1], rd.ids[rd.marker + 1]) == (meta["injection_left_neighbor_id"], meta["injection_right_neighbor_id"])
    assert "<concept>" in rd.prompt_text and tok.decode(rd.ids).endswith("<think>\n\n</think>\n\n")
    assert R.input_dump(rd, torch.ones(MOCK_D))["method"] == "skip_a"
    # per-row hook at the block-1 output: row i gets v[i]; prefill only
    store = {}
    blk = M.blocks(target.model)[C.NLA_INJECT_LAYER_IDX]
    hd = blk.register_forward_hook(lambda m, i, o: store.__setitem__("h", (o[0] if isinstance(o, tuple) else o).detach().clone()))
    x = torch.tensor([rd.ids, rd.ids])
    V = torch.randn(2, MOCK_D) * 40
    with torch.no_grad(), rd.active():
        rd._vec["v"] = None
        target.model(x, use_cache=False)
        clean = store["h"]
        rd._vec["v"] = V
        target.model(x, use_cache=False)
        inj = store["h"]
        rd._vec["v"] = None
    hd.remove()
    mp = rd.marker
    expect = clean.clone()
    for i in range(2):
        expect[i, mp] = clean[i, mp] + clean[i, mp].norm() * V[i] / (V[i].norm() + 1e-9)
    assert torch.allclose(inj, expect, atol=1e-4) and rd.n_hook_calls == 1
    with torch.no_grad(), rd.active():
        rd._vec["v"] = V[0]
        target.model(torch.tensor([[rd.ids[0]]]), use_cache=False)  # decode step: seq_len <= marker
        rd._vec["v"] = None
    assert rd.n_hook_calls == 1
    with pytest.raises(RuntimeError):
        with rd.active():
            rd._vec["v"] = torch.randn(3, MOCK_D)
            try:
                target.model(x, use_cache=False)
            finally:
                rd._vec["v"] = None
    # the hook formula is the NLA one (EasyNLA reference when importable)
    C.add_third_party_to_path()
    try:
        from nla.injection import karvonen_inject_in_residual  # type: ignore
    except Exception:
        return
    ref = karvonen_inject_in_residual(x, clean.clone(), V, meta["injection_token_id"], meta["injection_left_neighbor_id"], meta["injection_right_neighbor_id"])
    assert torch.allclose(ref, inj, atol=1e-4)


def test_skiplens_read_and_lo_sign_convention(tmp_path):
    ad = fake_adapter_dir(tmp_path, "skip_d_dir", 12)
    target = fresh_target()
    rd = R.SkipLensReader("d", max_new_tokens=5).bind(target, adapter_dir=ad, check=False)
    h = torch.randn(MOCK_D) * 30
    res = rd.read(h, seed=3)
    assert res.method == "skip_d" and res.extra["n_hook_injections"] == 1 and res.n_prompt_tokens == len(rd.ids)
    assert res.input["injection"] == C.SKIPLENS_INJECTION and res.input["arm"] == "d" and res.sampling["top_p"] == 0.95 and res.sampling["temperature"] == 1.0
    assert res.finish_reason in ("eos", "length") and isinstance(res.native["samples"][0], str)
    assert rd.read(h, seed=3).raw_output == res.raw_output  # seeded
    # LO: continuation right after the generation prompt, bare + leading-space forms, lo = lp(A) - lp(B)
    H = torch.stack([h, h])
    rows = LO.score_lo(rd, H, [("ab", "cd"), ("cd", "ab")], "ownership", batch=8)
    assert rows[0]["reader"] == "skip_d" and rows[0]["templates"] == list(C.SKIPLENS_LO_FORMS) and rows[0]["format"] == "continuation" and rows[0]["prefix"] == ""
    assert abs(rows[0]["lo"] + rows[1]["lo"]) < 1e-4 and rows[0]["cand_A"] == "ab" and rows[0]["cand_B"] == "cd" and not rows[0]["unscorable"]
    assert [pt["template"] for pt in rows[0]["per_template"]] == ["{X}", " {X}"]
    assert abs(rows[0]["lo"] - np.mean([pt["lo"] for pt in rows[0]["per_template"]])) < 1e-6
    # manual teacher forcing of the leading-space form reproduces per_template[1]
    tok = rd.tokenizer
    with rd.active(), torch.no_grad():
        lps = {}
        for c in ("ab", "cd"):
            ids = list(rd.ids) + tok(" " + c)["input_ids"]
            rd._vec["v"] = h
            try:
                logits = target.model(torch.tensor([ids]), use_cache=False).logits[0].float()
            finally:
                rd._vec["v"] = None
            lp = torch.log_softmax(logits, -1)
            lps[c] = sum(float(lp[len(rd.ids) - 1 + j, ids[len(rd.ids) + j]]) for j in range(len(ids) - len(rd.ids)))
    assert abs(rows[0]["per_template"][1]["lo"] - (lps["ab"] - lps["cd"])) < 2e-3
    assert abs(rows[0]["per_template"][1]["lp_A"] - lps["ab"]) < 2e-3


def test_skiplens_coexists_with_other_adapters(tmp_path):
    from peft import PeftModel

    base = fake_adapter_dir(tmp_path, "olens_like", 21)
    ad_a = fake_adapter_dir(tmp_path, "arm_a", 22)
    ad_d = fake_adapter_dir(tmp_path, "arm_d", 23)
    target = fresh_target()
    target.model = PeftModel.from_pretrained(target.model, str(base))  # as OLensReader.bind mounts it: adapter 'default'
    rd_a = R.SkipLensReader("a", max_new_tokens=3).bind(target, adapter_dir=ad_a, check=True)
    assert set(target.model.peft_config) == {"default", "skip_a"} and target.model.active_adapter == "default"  # restored after the liveness check
    x = torch.tensor([rd_a.ids])
    with torch.no_grad():
        l_default = target.model(x, use_cache=False).logits[0, -1].float()
        with rd_a.active():
            assert target.model.active_adapter == "skip_a"
            l_a = target.model(x, use_cache=False).logits[0, -1].float()
        assert target.model.active_adapter == "default"
        with target.model.disable_adapter():
            l_off = target.model(x, use_cache=False).logits[0, -1].float()
        l_base = tiny_model()(x, use_cache=False).logits[0, -1].float()
    assert (l_default - l_a).abs().max() > 1e-3 and (l_off - l_base).abs().max() < 1e-4
    assert (l_default - l_off).abs().max() > 1e-3
    # a second arm on the same target; each arm's hook fires only for its own reads
    rd_d = R.SkipLensReader("d", max_new_tokens=3).bind(target, adapter_dir=ad_d, check=True)
    assert set(target.model.peft_config) == {"default", "skip_a", "skip_d"}
    h = torch.randn(MOCK_D)
    n_a, n_d = rd_a.n_hook_calls, rd_d.n_hook_calls
    rd_d.read(h, seed=1)
    assert rd_d.n_hook_calls == n_d + 1 and rd_a.n_hook_calls == n_a
    rows_a = LO.score_lo(rd_a, h[None], [("ab", "cd")], "mapping")
    rows_d = LO.score_lo(rd_d, h[None], [("ab", "cd")], "mapping")
    assert rows_a[0]["adapter_name"] == "skip_a" and rows_d[0]["adapter_name"] == "skip_d" and rows_a[0]["lo"] != rows_d[0]["lo"]
    # capture on the target ignores the adapters and the (inert) hooks
    acts = M.capture(target.model, rd_a.ids, [MOCK_LAYER], [len(rd_a.ids) - 1])
    with torch.no_grad():
        ref = tiny_model()(x, use_cache=False, output_hidden_states=True).hidden_states[MOCK_LAYER + 1][0, -1]
    assert torch.allclose(acts[MOCK_LAYER][0], ref, atol=1e-4)
    rd_d.unload()
    assert set(target.model.peft_config) == {"default", "skip_a"}
    # re-binding an arm whose adapter is mounted is a no-op mount
    rd_a2 = R.SkipLensReader("a").bind(target, adapter_dir=ad_a, check=False)
    assert set(target.model.peft_config) == {"default", "skip_a"} and rd_a2.marker == rd_a.marker
    with pytest.raises(ValueError):
        R.SkipLensReader("z")


def test_skiplens_meta_drift_raises(tmp_path):
    ad = fake_adapter_dir(tmp_path, "drift", 31)
    meta = mock_meta(FakeTok())
    meta["tokens"]["injection_right_neighbor_id"] = 999
    (ad / C.SKIPLENS_META_FILE).write_text(yaml.safe_dump(meta, allow_unicode=True))
    with pytest.raises(RuntimeError, match="marker not well formed"):
        R.SkipLensReader("a").bind(fresh_target(), adapter_dir=ad, check=False)
    meta = mock_meta(FakeTok())
    meta.pop("_mock")
    (ad / C.SKIPLENS_META_FILE).write_text(yaml.safe_dump(meta, allow_unicode=True))
    with pytest.raises(RuntimeError, match="!= frozen"):
        R.SkipLensReader("a").bind(fresh_target(), adapter_dir=ad, check=False)


# ================================================================== R-lens
def test_rlens_inspect_and_bind(tmp_path):
    target = fresh_target()
    good = {"J": torch.randn(3, MOCK_D, MOCK_D).half() / 8, "source_layers": [1, 2, 3], "n_prompts": 25, "d_model": MOCK_D, "provenance": {"model_id": "mock"}}
    rep = R.RLensReader.inspect(good)
    assert rep["compatible"] and rep["source_layers"] == [1, 2, 3] and rep["provenance"]["model_id"] == "mock"
    assert not R.RLensReader.inspect({"J": torch.randn(3, MOCK_D, 7)})["compatible"]
    assert "source_layers" in R.RLensReader.inspect({"J": torch.randn(2, MOCK_D, MOCK_D), "source_layers": [5, 6]})["reason"]
    assert not R.RLensReader.inspect({"weights": 1})["compatible"] and not R.RLensReader.inspect([1, 2])["compatible"]
    assert R.RLensReader.inspect({"J": {"2": torch.eye(MOCK_D)}})["compatible"]
    p = tmp_path / "lens.pt"
    torch.save(good, p)
    rd = R.RLensReader().bind(target, lens_path=p)
    assert rd.usable and rd.name == "rlens" and set(rd.J) == {MOCK_LAYER} and rd.source_layers == [1, 2, 3]
    assert torch.allclose(rd.J[MOCK_LAYER], good["J"][1].float())  # indexed by source_layers, not by position
    h = torch.randn(MOCK_D)
    res = rd.read(h, MOCK_LAYER)
    assert res.method == "rlens" and len(res.native["token_ids"]) == 10
    rows = LO.score_lo(rd, h[None], [("a", "b")], "mapping")
    assert rows[0]["reader"] == "rlens" and rows[0]["lo"] is not None
    bad = tmp_path / "bad.pt"
    torch.save({"J": torch.randn(2, MOCK_D, MOCK_D), "source_layers": [5, 6]}, bad)
    rd2 = R.RLensReader().bind(target, lens_path=bad)
    assert not rd2.usable and "source_layers" in rd2.skip_reason
    with pytest.raises(RuntimeError):
        rd2.read(h, MOCK_LAYER)


# ================================================================== SAE
def random_sae(d=16, d_sae=64, k=5, seed=0, b_dec_scale=0.0):
    g = torch.Generator().manual_seed(seed)
    return SAE.SAE(torch.randn(d_sae, d, generator=g), torch.randn(d, d_sae, generator=g), torch.randn(d_sae, generator=g) * 0.1,
                   torch.randn(d, generator=g) * b_dec_scale, k=k, variant="readme")


def test_sae_encode_decode_fve_and_null(tmp_path):
    sae = random_sae()
    X = torch.randn(40, 16) * 3
    idx, vals = SAE.encode_sparse(sae, X)
    assert idx.shape == (40, 5) and vals.shape == (40, 5)
    z = SAE.encode(sae, X)
    assert z.shape == (40, 64) and torch.equal((z != 0).sum(-1), torch.full((40,), 5))
    assert torch.allclose(SAE.decode(sae, z), SAE.decode_sparse(sae, idx, vals), atol=1e-5)
    pa = SAE.pre_acts(sae, X)
    assert torch.allclose(vals, torch.topk(pa, 5, dim=-1).values)
    assert SAE.fve(X, X) == 1.0 and SAE.fve(X, X.mean(0, keepdim=True).expand_as(X)) < 1e-6
    # centred variant subtracts b_dec before encoding
    sae_c = random_sae(b_dec_scale=2.0).with_variant("centred")
    assert torch.allclose(SAE.pre_acts(sae_c, X), (X - sae_c.b_dec) @ sae_c.W_enc.T + sae_c.b_enc)
    assert not torch.allclose(SAE.pre_acts(sae_c, X), SAE.pre_acts(sae_c.with_variant("readme"), X))
    with pytest.raises(ValueError):
        sae.with_variant("other")
    # a perfect dictionary: orthogonal W_dec, W_enc = W_dec^T, data = k-sparse positive combinations -> FVE 1; null lower
    Q, _ = torch.linalg.qr(torch.randn(16, 16, generator=torch.Generator().manual_seed(3)))
    perfect = SAE.SAE(Q.T.clone(), Q.clone(), torch.zeros(16), torch.zeros(16), k=5)
    g = torch.Generator().manual_seed(4)
    Z = torch.zeros(30, 16)
    for i in range(30):
        Z[i, torch.randperm(16, generator=g)[:5]] = torch.rand(5, generator=g) + 0.5
    Xp = Z @ Q.T
    rep = SAE.fve_report(perfect, Xp)
    assert abs(rep["fve"] - 1.0) < 1e-5 and rep["fve_null"] < rep["fve"] - 0.2 and rep["n"] == 30 and rep["null_seed"] == 0
    assert torch.equal(SAE.shuffled_decoder(perfect, 0), SAE.shuffled_decoder(perfect, 0)) and not torch.equal(SAE.shuffled_decoder(perfect, 0), perfect.W_dec)
    # load_sae validates the checkpoint
    p = tmp_path / "sae.pt"
    torch.save({"W_enc": sae.W_enc, "W_dec": sae.W_dec, "b_enc": sae.b_enc, "b_dec": sae.b_dec}, p)
    s2 = SAE.load_sae(p, k=5)
    assert s2.d == 16 and s2.d_sae == 64 and s2.k == 5 and s2.variant == C.SAE_ENCODE_VARIANT and torch.equal(s2.W_enc, sae.W_enc)
    torch.save({"W_enc": sae.W_enc, "W_dec": sae.W_dec.T, "b_enc": sae.b_enc, "b_dec": sae.b_dec}, p)
    with pytest.raises(ValueError, match="inconsistent"):
        SAE.load_sae(p)
    torch.save({"W_enc": sae.W_enc}, p)
    with pytest.raises(ValueError, match="missing"):
        SAE.load_sae(p)


def planted_codes(ids, plant, d_sae=50, k=5, seed=0):
    """Codes with a planted latent per item (plant[item_id] = latent id, value 3.0) and k-1 random latents from 10.."""
    g = np.random.default_rng(seed)
    idx, vals = [], []
    for iid in ids:
        others = g.choice(np.arange(10, d_sae), size=k - 1, replace=False)
        idx.append([plant[iid]] + others.tolist())
        vals.append([3.0] + g.uniform(0.5, 1.5, size=k - 1).tolist())
    return SAE.Codes(torch.tensor(idx), torch.tensor(vals), list(ids), d_sae)


def test_sparse_probe_on_planted_signal():
    # X1 binary: pos states carry latent 3, neg states latent 7
    pairs = []
    plant = {}
    for i in range(8):
        a = {"item_id": f"xown-{i:02d}A", "pair_id": f"xown-{i:02d}", "family": "ownership", "split": "test", "primary": {"candidates": ["P", "Q"], "answer": "P"}}
        b = {**a, "item_id": f"xown-{i:02d}B", "primary": {"candidates": ["P", "Q"], "answer": "Q"}}
        pairs.append({"pair_id": a["pair_id"], "family": "ownership", "A": a, "B": b})
        pos = "A" if i % 2 == 0 else "B"
        plant[a["item_id"]] = 3 if pos == "A" else 7
        plant[b["item_id"]] = 3 if pos == "B" else 7
    codes = planted_codes(sorted(plant), plant)
    pos_version = lambda p: "A" if int(p["pair_id"][-2:]) % 2 == 0 else "B"  # noqa: E731
    rows = SAE.x1_probe_rows(pairs, codes, "binary", pos_version, max_latents=10)
    assert len(rows) == 16 and all(not r["unscorable"] for r in rows)
    by = {r["item_id"]: r for r in rows}
    for p in pairs:
        assert by[p["A"]["item_id"]]["lo"] + by[p["B"]["item_id"]]["lo"] > 0
    rec = rows[0]["probe"]
    assert {3, 7} <= set(rec["latents"]) and rec["signs"][rec["latents"].index(3)] == 1 and rec["signs"][rec["latents"].index(7)] == -1 and rec["n_kept"] <= 10
    u = torch.zeros(50); u[3] = 2.0; u[7] = -1.0; u[20] = 0.1
    lat, sg = SAE.sparse_direction(u, 2)
    assert set(lat.tolist()) == {3, 7} and dict(zip(lat.tolist(), sg.tolist())) == {3: 1.0, 7: -1.0}
    assert SAE.sparse_direction(torch.zeros(50), 10)[0].numel() == 0
    # X1 identity: answers {x, y, z}, latent = 1 + index of the answer
    vals = ["x", "y", "z"]
    ipairs, plant = [], {}
    for i in range(9):
        a_ans, b_ans = vals[i % 3], vals[(i + 1) % 3]
        a = {"item_id": f"xmap-{i:02d}A", "pair_id": f"xmap-{i:02d}", "family": "mapping", "split": "test", "primary": {"candidates": [a_ans, b_ans], "answer": a_ans}}
        b = {**a, "item_id": f"xmap-{i:02d}B", "primary": {"candidates": [a_ans, b_ans], "answer": b_ans}}
        ipairs.append({"pair_id": a["pair_id"], "family": "mapping", "A": a, "B": b})
        plant[a["item_id"]], plant[b["item_id"]] = 1 + vals.index(a_ans), 1 + vals.index(b_ans)
    icodes = planted_codes(sorted(plant), plant, seed=1)
    irows = SAE.x1_probe_rows(ipairs, icodes, "identity", pos_version, max_latents=10)
    iby = {r["item_id"]: r for r in irows}
    assert all(iby[p["A"]["item_id"]]["lo"] + iby[p["B"]["item_id"]]["lo"] > 0 for p in ipairs)
    assert SAE.x1_mean_row("mapping", ipairs, icodes)["within_band"] is None
    # X3 puzzle identity (symbol latent = 1 + index) and choice first-listed label (latent 3 if first-listed else 7)
    items = {}
    plant = {}
    syms = "ABCD"
    for i in range(16):
        actual, other = syms[i % 4], syms[(i + 1) % 4]
        iid = f"xpz-{i:04d}"
        items[iid] = {"item_id": iid, "family": "puzzle", "set": "error" if i % 2 else "error_control", "text_key": other,
                      "primary": {"candidates": [actual, other], "answer": actual}, "source": {"correct": other}}
        plant[iid] = 1 + syms.index(actual)
    for i in range(12):
        iid = f"xch-{i:04d}"
        first = i % 2 == 0
        items[iid] = {"item_id": iid, "family": "choice", "set": "disagree" if i % 3 else "agree_control", "text_key": "o",
                      "primary": {"candidates": ["w%d" % i, "o"], "answer": "w%d" % i}, "source": {"first_listed": "w%d" % i if first else "o"}}
        plant[iid] = 3 if first else 7
    xcodes = planted_codes(sorted(plant), plant, seed=2)
    prow = SAE.x3_probe_rows(items, xcodes, ("error", "error_control"), "puzzle")
    crow = SAE.x3_probe_rows(items, xcodes, ("disagree", "agree_control"), "choice")
    assert len(prow) == 16 and all(r["favours_actual"] for r in prow) and all(r["lo_actual"] > 0 for r in prow)
    assert len(crow) == 12 and all(r["favours_actual"] for r in crow) and crow[0]["probe"]["type"] == "binary_first_listed_midpoint"
    # X2: read-vector codes carrying the planted latent of the planted candidate
    beh = []
    plant_rv = {}
    for i in range(4):
        pid = f"xown-{i:02d}"
        src_pos = pos_version({"pair_id": pid})
        for cond, key in (("natural", f"{pid}|A|nat|natural|0.0|None"), ("planted", f"{pid}|A|S2|planted|1.0|None")):
            beh.append({"key": key, "pair_id": pid, "family": "ownership", "source": "A", "state_item_id": f"{pid}A", "site": "nat" if cond == "natural" else "S2",
                        "edit_layer": None, "positions_kind": "all", "alpha": 0.0 if cond == "natural" else 1.0, "condition": cond, "null_k": None, "sign": 0,
                        "other_pair_id": None, "cand_A": "P", "cand_B": "Q", "dose_abs": 0.0, "lo_model": -1.0, "flipped_to_other": cond == "planted", "coherent": True})
            # natural: the source state's own latent (pos-ness of A); planted at alpha 1: the other state's latent
            own_is_pos = src_pos == "A"
            plant_rv[key] = (3 if own_is_pos else 7) if cond == "natural" else (7 if own_is_pos else 3)
    rv_codes = planted_codes([b["key"] for b in beh], plant_rv, seed=3)
    x2rows = SAE.x2_probe_rows(beh, rv_codes, {"ownership": pairs}, codes, {"ownership": "binary"}, pos_version)
    assert len(x2rows) == 8 and all(not r["unscorable"] for r in x2rows)
    nat = {r["pair_id"]: r for r in x2rows if r["condition"] == "natural"}
    pl = {r["pair_id"]: r for r in x2rows if r["condition"] == "planted"}
    for pid in nat:
        assert nat[pid]["lo_own"] > 0 and pl[pid]["lo_own"] < 0 and pl[pid]["lo_toward_other"] == -pl[pid]["lo_own"]


# ================================================================== collector on tmp paths (MOCK)
def x1_items_small(n_pairs=2):
    items = bdx.build(bdx.DEFAULT_SEED)["items"]
    pairs = X1.load_pairs(split="test", limit_pairs=n_pairs, items=items)
    return items, pairs


def x3_selected_small(tmp_path: Path) -> Path:
    from projects.g_agreement.x3_floor import collect as X3

    puz = [X3.make_selected({"item_id": f"xpz-{i:04d}", "family": "puzzle", "prompt_text": f"Arrows {i}. Start at A. Answer with the symbol only.",
                             "primary": {"correct": "ABCD"[(i + 1) % 4], "k": 3, "trace": ["A", "B", "ABCD"[(i + 1) % 4]]}},
                            "error" if i % 2 else "error_control", "ABCD"[i % 4], "ABCD"[(i + 1) % 4], "ABCD"[(i + 1) % 4]) for i in range(6)]
    cho = [X3.make_selected({"item_id": f"xch-{i:04d}", "family": "choice", "prompt_text": f"Choose w{i} or o{i}.", "primary": {"candidates": [f"w{i}", f"o{i}"]}},
                            "disagree" if i % 2 else "agree_control", f"w{i}", f"o{i}", f"o{i}") for i in range(4)]
    p = tmp_path / "items_x3_selected.json"
    X3.write_selected(p, puz + cho, {"counts": {"error": 3, "error_control": 3, "disagree": 2, "agree_control": 2}})
    return p


def test_collect_stages_and_sae_on_mock(tmp_path, monkeypatch):
    target = fresh_target()
    items, pairs = x1_items_small()
    items_file = tmp_path / "items_x.json"
    items_file.write_text(json.dumps({"meta": {}, "items": X1.pair_items(pairs)}))  # only the 2 pairs per family that get states
    sd, mp, led, log = tmp_path / "states", tmp_path / "meta.jsonl", tmp_path / "c.jsonl", tmp_path / "log.md"
    S.ensure_states(target, X1.pair_items(pairs), states_dir=sd, meta_path=mp, ledger_path=led, module="y3", extra_dev_layers=())
    sel_file = x3_selected_small(tmp_path)
    _m, selected = YC.x3_items(sel_file, 0)
    S.ensure_states(target, selected, states_dir=sd, meta_path=mp, ledger_path=led, module="y3", extra_dev_layers=())
    # two X2 behaviour rows with read vectors
    beh, rv = tmp_path / "beh.jsonl", tmp_path / "readvecs"
    rv.mkdir()
    for key, cond, site, alpha in ((f"{pairs[0]['pair_id']}|A|nat|natural|0.0|None", "natural", "nat", 0.0), (f"{pairs[0]['pair_id']}|A|S2|planted|1.0|None", "planted", "S2", 1.0)):
        A.append_jsonl(beh, {"key": key, "pair_id": pairs[0]["pair_id"], "family": pairs[0]["family"], "source": "A", "state_item_id": pairs[0]["A"]["item_id"], "site": site,
                             "edit_layer": None, "positions_kind": "all", "alpha": alpha, "condition": cond, "null_k": None, "sign": 0, "other_pair_id": None,
                             "cand_A": pairs[0]["A"]["primary"]["answer"], "cand_B": X1.other_candidate(pairs[0]["A"]), "dose_abs": 0.0, "lo_model": -1.0,
                             "flipped_to_other": cond == "planted", "coherent": True})
        torch.save(torch.randn(MOCK_D).to(torch.bfloat16), X2.readvec_path(key, rv))
    ad = fake_adapter_dir(tmp_path, "arm_a", 41)
    rd = YC.bind_reader("skip_a", target, ledger_path=led, log_path=log, adapter_dir=ad)
    lens = tmp_path / "lens.pt"
    torch.save({"J": torch.randn(4, MOCK_D, MOCK_D) / 8, "source_layers": [0, 1, 2, 3]}, lens)
    rl = YC.bind_reader("rlens", target, ledger_path=led, log_path=log, lens_path=lens, rlens_format_path=tmp_path / "rlens_format.json")
    assert rl is not None and json.loads((tmp_path / "rlens_format.json").read_text())["usable"] is True
    bad = tmp_path / "bad_lens.pt"
    torch.save({"J": torch.randn(2, MOCK_D, 5)}, bad)
    assert YC.bind_reader("rlens", target, ledger_path=led, log_path=log, lens_path=bad, rlens_format_path=tmp_path / "rlens_bad.json") is None
    assert json.loads((tmp_path / "rlens_bad.json").read_text())["usable"] is False
    x1_lo, x2_lo, x3_lo = tmp_path / "y3_x1_lo.jsonl", tmp_path / "y3_x2_lo.jsonl", tmp_path / "y3_x3_lo.jsonl"
    kw = dict(items_file=items_file, selected_file=sel_file, limit=0, batch=8, beh_path=beh, readvec_dir=rv, states_dir=sd, x1_lo=x1_lo, x2_lo=x2_lo, x3_lo=x3_lo,
              ledger_path=led, log_path=log)
    counts = YC.run_model_readers(target, [rd, rl], ("x1", "x2", "x3"), **kw)
    assert counts["x1_skip_a"] == 16 + 4 and counts["x1_rlens"] == 16 + 4 and counts["x2_skip_a"] == 2 and counts["x3_skip_a"] == 10 and counts["x3_rlens"] == 10
    r1 = A.read_jsonl(x1_lo)
    assert {r["reader"] for r in r1} == {"skip_a", "rlens"} and sum(r["condition"] == "mean_state" for r in r1) == 8
    nat_rows = [r for r in r1 if r["condition"] == "natural" and r["reader"] == "skip_a"]
    assert len(nat_rows) == 16 and all(r["key"] == f"skip_a|{r['item_id']}" and r["lo"] is not None and r["templates"] == list(C.SKIPLENS_LO_FORMS) for r in nat_rows)
    r2 = A.read_jsonl(x2_lo)
    assert len(r2) == 4 and {r["reader"] for r in r2} == {"skip_a", "rlens"} and all(abs(r["lo_toward_other"] + r["lo_own"]) < 1e-9 for r in r2 if r["lo_own"] is not None)
    r3 = A.read_jsonl(x3_lo)
    assert len(r3) == 20 and {r["set"] for r in r3} == {"error", "error_control", "disagree", "agree_control"} and all("lo_actual" in r for r in r3)
    # resumable
    assert all(v == 0 for v in YC.run_model_readers(target, [rd, rl], ("x1", "x2", "x3"), **kw).values())
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"y3_bind_skip_a", "y3_bind_rlens", "x1_lo_skip_a", "x1_mean_lo_skip_a", "x2_lo_skip_a", "x3_lo_skip_a", "x1_lo_rlens"} <= steps
    # SAE: tiny random SAE on the MOCK states; the gate fails on random weights -> no rows unless forced
    sae = random_sae(d=MOCK_D, d_sae=256, k=8, seed=5)
    sp = tmp_path / "layer2.sae.pt"
    torch.save({"W_enc": sae.W_enc, "W_dec": sae.W_dec, "b_enc": sae.b_enc, "b_dec": sae.b_dec}, sp)
    monkeypatch.setattr(C, "SAE_K", 8)
    fj = tmp_path / "sae_fve.json"
    skw = dict(items_file=items_file, selected_file=sel_file, limit=0, sae_path=sp, beh_path=beh, readvec_dir=rv, states_dir=sd, x1_lo=x1_lo, x2_lo=x2_lo, x3_lo=x3_lo,
               fve_json=fj, ledger_path=led, log_path=log)
    rep = YC.run_sae(("x1", "x2", "x3"), **skw)
    assert set(rep["by_variant"]) == {"readme", "centred"} and rep["n_x1_states"] == 16 and rep["n_x3_states"] == 10
    for v in rep["by_variant"].values():
        assert set(v) == {"x1", "x3", "pooled"} and all(d["fve"] <= 1 and not np.isnan(d["fve"]) for d in v.values())  # a random SAE explains nothing
    assert rep["gate_passes"] is False and rep["probe_rows_written"] is False and not any(r["reader"] == "sae" for r in A.read_jsonl(x1_lo))
    rep2 = YC.run_sae(("x1", "x2", "x3"), force_probe=True, **skw)
    assert rep2["forced"] is True and rep2["probe_rows_new"]["x1"] == 16 + 4 and rep2["probe_rows_new"]["x3"] == 10 and rep2["probe_rows_new"]["x2"] == 2
    sae_rows = [r for r in A.read_jsonl(x1_lo) if r["reader"] == "sae"]
    assert len(sae_rows) == 20 and all(r.get("sae", {}).get("k") == 8 for r in sae_rows if r["condition"] == "natural")
    assert all(r["probe"]["n_kept"] <= C.SAE_PROBE_MAX_LATENTS for r in sae_rows if r["condition"] == "natural" and not r["unscorable"])
    rep3 = YC.run_sae(("x1", "x2", "x3"), force_probe=True, **skw)
    assert rep3["probe_rows_new"] == {"x1": 0, "x3": 0, "x2": 0}
    assert json.loads(fj.read_text())["gate_min_fve"] == C.SAE_FVE_MIN
    # analyze runs on the mock output (no claims about the numbers)
    out = tmp_path / "res"
    s = YA.main(["--items", str(items_file), "--selected", str(sel_file), "--x1-lo", str(x1_lo), "--x2-lo", str(x2_lo), "--x3-lo", str(x3_lo), "--behaviour", str(beh),
                 "--x1-summary", str(tmp_path / "none.json"), "--x3-summary", str(tmp_path / "none.json"), "--sae-fve", str(fj), "--rlens-format", str(tmp_path / "rlens_format.json"),
                 "--frozen-config", str(tmp_path / "nofreeze.json"), "--allow-unfrozen", "--out", str(out), "--n-boot", "20", "--no-map"])
    assert set(s["E14"]) == {"skip_a", "skip_d", "sae", "rlens"} and s["E14"]["skip_d"]["gate_status"] == "no rows" and s["E14"]["skip_a"]["n_rows"] == 16
    assert s["E14"]["sae"]["e3_not_applicable"] is True and s["sae"]["gate_passes"] is False and s["rlens"]["usable"] is True
    assert (out / "summary.json").exists() and (out / "e14.csv").exists() and (out / "e15.csv").exists() and (out / "fig_main.png").exists()
    assert "x3" in s["E15"]["skip_a"] and set(s["E15"]["skip_a"]["x3"]["per_set"]) == set(YA.SETS)
    YC.parse_readers("skip_a,sae")
    with pytest.raises(SystemExit):
        YC.parse_readers("skip_a,olens")
    assert YC.parse_stages("all") == ("x1", "x2", "x3") and YC.parse_stages("x1,x3") == ("x1", "x3")
    with pytest.raises(SystemExit):
        YC.parse_stages("x9")
    assert YC.x2_pair_ids(beh, 0) is None and YC.x2_pair_ids(beh, 1) == {pairs[0]["pair_id"]}


# ================================================================== analyze on synthetic rows
def synthetic_world(tmp_path: Path, n_pairs=8, seed=0):
    """skip_a separates every family (+2 nats, mean-state LO 0.3); skip_d is noise; sae separates the binding families (E3 n/a);
    X2 S2: the model flips at alpha 0.75 and skip_a's LO follows (sign), skip_d does not; X3: skip_a favours actual on ERROR/DISAGREE."""
    rng = np.random.default_rng(seed)
    items = bdx.build(bdx.DEFAULT_SEED)["items"]
    pairs = X1.load_pairs(split="test", limit_pairs=n_pairs, items=items)
    items_file = tmp_path / "items_x.json"
    items_file.write_text(json.dumps({"meta": {}, "items": items}))
    x1_rows = []
    for rd in ("skip_a", "skip_d", "sae"):
        for p in pairs:
            for v in "AB":
                it = p[v]
                if rd == "sae" and p["family"] not in ("ownership", "mapping"):
                    continue
                lo = 2.0 + rng.normal(0, 0.3) if rd != "skip_d" else rng.normal(0, 1.0)
                x1_rows.append({"key": f"{rd}|{it['item_id']}", "reader": rd, "item_id": it["item_id"], "pair_id": p["pair_id"], "family": p["family"], "split": "test",
                                "version": v, "condition": "natural", "cand_A": it["primary"]["answer"], "cand_B": X1.other_candidate(it), "lo": lo, "unscorable": False})
        for fam in X1A.FAMILIES:
            if rd == "sae":
                x1_rows.append({"key": f"{rd}|mean|{fam}", "reader": rd, "family": fam, "condition": "mean_state", "mean_lo": None, "within_band": None, "note": "E3 not applicable"})
            else:
                x1_rows.append({"key": f"{rd}|mean|{fam}", "reader": rd, "family": fam, "condition": "mean_state", "mean_lo": 0.3 if rd == "skip_a" else 2.5,
                                "mean_abs_lo": 0.5, "n_scorable": n_pairs, "within_band": rd == "skip_a"})
    # X2 behaviour + LO at S2 for the binding pairs
    beh, x2_rows = [], []
    alphas = (0.25, 0.5, 0.75, 1.0)
    for p in [q for q in pairs if q["family"] in ("ownership", "mapping")]:
        for src in "AB":
            it = p[src]
            A_, B_ = it["primary"]["answer"], X1.other_candidate(it)
            nat_key = f"{p['pair_id']}|{src}|nat|natural|0.0|None"
            beh.append({"key": nat_key, "pair_id": p["pair_id"], "family": p["family"], "source": src, "state_item_id": it["item_id"], "site": "nat", "alpha": 0.0,
                        "condition": "natural", "cand_A": A_, "cand_B": B_, "flipped_to_other": False, "coherent": True, "lo_model": -3.0})
            for rd in ("skip_a", "skip_d", "sae"):
                x2_rows.append({"key": f"{rd}|{nat_key}", "entry_key": nat_key, "reader": rd, "pair_id": p["pair_id"], "family": p["family"], "source": src, "site": "nat",
                                "alpha": 0.0, "condition": "natural", "lo_own": 2.0, "lo_toward_other": -2.0, "unscorable": False})
            for a in alphas:
                key = f"{p['pair_id']}|{src}|S2|planted|{a}|None"
                beh.append({"key": key, "pair_id": p["pair_id"], "family": p["family"], "source": src, "state_item_id": it["item_id"], "site": "S2", "alpha": a,
                            "condition": "planted", "cand_A": A_, "cand_B": B_, "flipped_to_other": a >= 0.75, "coherent": True, "lo_model": -3.0 + 8 * a})
                for rd in ("skip_a", "skip_d", "sae"):
                    lo_to = (-2.0 + 4.0 * a + rng.normal(0, 0.1)) if rd != "skip_d" else (-2.0 + rng.normal(0, 0.5))
                    x2_rows.append({"key": f"{rd}|{key}", "entry_key": key, "reader": rd, "pair_id": p["pair_id"], "family": p["family"], "source": src, "site": "S2",
                                    "alpha": a, "condition": "planted", "lo_own": -lo_to, "lo_toward_other": lo_to, "unscorable": False})
    # X3 selected + LO
    sel_file = x3_selected_small(tmp_path)
    _m, selected = YC.x3_items(sel_file, 0)
    x3_rows = []
    for rd in ("skip_a", "skip_d", "sae"):
        for it in selected:
            lo = (1.5 + rng.normal(0, 0.2)) if rd != "skip_d" else rng.normal(0, 1)
            x3_rows.append({"key": f"{rd}|{it['item_id']}", "reader": rd, "item_id": it["item_id"], "family": it["family"], "set": it["set"],
                            "cand_actual": it["primary"]["candidates"][0], "cand_other": it["primary"]["candidates"][1], "lo_actual": lo, "unscorable": False})
    paths = {}
    for name, rows in (("x1", x1_rows), ("x2", x2_rows), ("x3", x3_rows), ("beh", beh)):
        paths[name] = tmp_path / f"{name}.jsonl"
        paths[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    fve = tmp_path / "sae_fve.json"
    fve.write_text(json.dumps({"gate_fve": 0.71, "gate_passes": True, "gate_variant": "readme", "n_x1_states": 280, "n_x3_states": 466, "probe_rows_written": True, "forced": False,
                               "by_variant": {"readme": {"pooled": {"n": 746, "fve": 0.71, "fve_null": -0.3, "mean_cos_x_xhat": 0.8}}}, "sae": {"k": 50}}))
    return items_file, sel_file, paths, fve


def test_analyze_synthetic_gate_e15_and_map(tmp_path):
    items_file, sel_file, paths, fve = synthetic_world(tmp_path)
    frozen = tmp_path / "frozen_config_x.json"
    frozen.write_text(json.dumps({"frozen": True}))
    map_results = tmp_path / "results"
    (map_results / "x").mkdir(parents=True)
    rlf = tmp_path / "rlens_format.json"
    rlf.write_text(json.dumps({"usable": False, "skip_reason": "J has shape [3, 5120, 7]", "format": {}}))
    out = tmp_path / "y3"
    s = YA.main(["--items", str(items_file), "--selected", str(sel_file), "--x1-lo", str(paths["x1"]), "--x2-lo", str(paths["x2"]), "--x3-lo", str(paths["x3"]),
                 "--behaviour", str(paths["beh"]), "--x1-summary", str(tmp_path / "none.json"), "--x3-summary", str(tmp_path / "none.json"), "--sae-fve", str(fve),
                 "--rlens-format", str(rlf), "--frozen-config", str(frozen), "--out", str(out), "--map-results", str(map_results), "--n-boot", "200"])
    e = s["E14"]
    assert e["skip_a"]["gate_pass"] and e["skip_a"]["gate_status"] == "PASS" and all(e["skip_a"]["E1"][f]["separates"] for f in X1A.FAMILIES)
    assert not e["skip_d"]["gate_pass"] and e["skip_d"]["gate_status"] == "FAIL (E1)"
    assert e["sae"]["gate_pass"] and e["sae"]["gate_status"] == "PASS (E1 only; E3 n/a)" and e["sae"]["e3_not_applicable"]
    assert e["rlens"]["gate_status"].startswith("skipped") and not e["rlens"]["gate_pass"]
    assert e["skip_a"]["E1"]["ownership"]["n"] == 8 and e["skip_a"]["E3"]["ownership"]["within_band"] is True
    x2 = s["E15"]["skip_a"]["x2"]
    assert set(x2) == {"ownership", "mapping"} and x2["ownership"]["n_with_alpha_star"] == 16 and x2["ownership"]["win"]["p"] == 1.0 and x2["ownership"]["follows"]
    assert abs(x2["ownership"]["fraction_median"] - 0.75) < 0.1  # shift at alpha* 0.75 = 3 of a separation of 4
    assert s["E15"]["skip_d"]["x2"]["ownership"]["win"]["p"] < 0.8
    x3 = s["E15"]["skip_a"]["x3"]
    assert x3["per_set"]["error"]["raw"]["p"] == 1.0 and x3["per_set"]["error"]["raw"]["n"] == 3 and x3["per_set"]["error"]["underpowered"] is True
    assert x3["verdict_raw"] == "descriptive_only (K6)" and "bias_range_nats" not in x3["bias"]["puzzle"]  # < 16 puzzle rows: correction skipped
    assert x3["per_set"]["error"]["corrected"]["n"] == 0
    assert set(s["map_columns"]) == {"skip_a", "sae"} and s["map_columns"]["skip_a"]["reported"]["puzzle-error"]["n"] == 3
    assert s["map_columns"]["skip_a"]["follows"]["ownership"]["p"] == 1.0 and "language" in s["map_columns"]["skip_a"]["reported"]
    assert "language" not in s["map_columns"]["sae"]["reported"]
    for f in ("summary.json", "e14.csv", "e15.csv", "fig_main.png"):
        assert (out / f).exists()
    e15 = (out / "e15.csv").read_text().splitlines()
    assert e15[0].startswith("kind,reader") and sum(1 for l in e15 if l.startswith("x2_follow,skip_a")) == 2 and sum(1 for l in e15 if l.startswith("x3_e8,skip_a")) == 8
    # blindness map extended with the gated readers only
    bm = (map_results / "x" / "blindness_map.csv").read_text().splitlines()
    assert "reported_skip_a" in bm[0] and "follows_sae" in bm[0] and "skip_d" not in bm[0] and "rlens" not in bm[0]
    assert bm[0].startswith("feature_class,present_win,present_ceiling_win,present_flag,loadbearing_flip_alpha1,loadbearing_median_alpha_star,reported_jlens")
    assert (map_results / "x" / "fig_main.png").exists()
    own = next(l for l in bm if l.startswith("ownership,")).split(",")
    cols = bm[0].split(",")
    assert own[cols.index("reported_skip_a")] == "1.000" and own[cols.index("follows_skip_a")] == "1.000" and own[cols.index("reported_skip_a_n")] == "8"
    pe = next(l for l in bm if l.startswith("puzzle-error,")).split(",")
    assert pe[cols.index("reported_skip_a")] == "1.000" and pe[cols.index("follows_skip_a")] == "" and pe[cols.index("follows_status")] == "not tested"
    # unfrozen run: map untouched
    (map_results / "x" / "blindness_map.csv").unlink()
    YA.main(["--items", str(items_file), "--selected", str(sel_file), "--x1-lo", str(paths["x1"]), "--x2-lo", str(paths["x2"]), "--x3-lo", str(paths["x3"]),
             "--behaviour", str(paths["beh"]), "--x1-summary", str(tmp_path / "none.json"), "--x3-summary", str(tmp_path / "none.json"), "--sae-fve", str(fve),
             "--frozen-config", str(tmp_path / "nofreeze.json"), "--allow-unfrozen", "--out", str(tmp_path / "y3dev"), "--map-results", str(map_results), "--n-boot", "20", "--no-fig"])
    assert not (map_results / "x" / "blindness_map.csv").exists()
    with pytest.raises(YA.U.FrozenConfigError):
        YA.main(["--items", str(items_file), "--frozen-config", str(tmp_path / "nofreeze.json"), "--out", str(tmp_path / "y3x"), "--no-fig", "--no-map"])


def test_blindness_map_build_unchanged_without_extra():
    results = REPO / "results" / "g_agreement"
    if not (results / "x1" / "summary.json").exists():
        pytest.skip("no Phase X summaries on this machine")
    rows = XB.build(results)
    cols = list(rows[0].keys())
    assert not any("skip" in c or "sae" in c for c in cols)
    extra = {"skip_a": {"label": "skip-lens A", "reported": {"ownership": {"p": 0.9, "n": 47}}, "follows": {"ownership": {"p": 0.8, "n": 60}, "language": {"p": 0.5, "n": 5}}}}
    rows2 = XB.build(results, extra)
    assert [c for c in rows2[0] if c in cols] == cols and {"reported_skip_a", "reported_skip_a_n", "follows_skip_a", "follows_skip_a_n"} <= set(rows2[0])
    own = next(r for r in rows2 if r["feature_class"] == "ownership")
    lang = next(r for r in rows2 if r["feature_class"] == "language")
    assert own["reported_skip_a"] == 0.9 and own["follows_skip_a"] == 0.8 and lang["follows_skip_a"] is None and lang["reported_skip_a"] is None
    for r, r2 in zip(rows, rows2):
        assert all(r[c] == r2[c] for c in cols)
    assert XB.extra_cell(extra, "skip_a", "reported", "mapping") is None and XB.extra_cell(None, "skip_a", "reported", "ownership") is None


def test_zz_results_cache_untouched():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
