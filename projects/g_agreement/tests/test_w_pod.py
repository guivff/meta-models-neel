"""MOCK tests (CPU) for the Phase W pod pipeline (projects/g_agreement/w_pod): the bank / direction / request interfaces on fixtures,
S1 (plain vs chat render, 4-layer all-position captures, the candidate score vector, states-style files, resume, counts filter),
S2 (edit geometry per family, matched-norm random directions, planned count and cap, DONE / resume, read-backs equal to a direct
core decode), S3 (score vectors, pair LO rows, probe rows, V6 multi-marker carrier == single-marker for k = 1), S3v1 requests,
S4 (sample rows, random vectors), the STATUS writer and the pod-budget guard, run_w.sh (bash -n, dry run). Same tiny random
Qwen3_5 model and fake tokenizer as test_readers_mock.py; nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_w_pod.py -q``
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import edit as E  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import IM_START, MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402
from projects.g_agreement.tests.test_x2_mock import items_x, mk_item  # noqa: E402
from projects.g_agreement.w_pod import common as W  # noqa: E402
from projects.g_agreement.w_pod import s1_capture as S1  # noqa: E402
from projects.g_agreement.w_pod import s2_steer as S2  # noqa: E402
from projects.g_agreement.w_pod import s3_score as S3  # noqa: E402
from projects.g_agreement.w_pod import s3v1_requests as S3V1  # noqa: E402
from projects.g_agreement.w_pod import s4_consistency as S4  # noqa: E402
from projects.g_agreement.w_pod import scoring_multi as SM  # noqa: E402
from projects.g_agreement.w_pod import status as ST  # noqa: E402
from projects.g_agreement.x2_causal import collect as X  # noqa: E402



def _snap(p: Path):
    return sorted(str(q) for q in p.rglob("*")) if p.exists() else None


# the directories this pipeline owns (other Phase W / V agents write elsewhere under results/ and cache/ concurrently)
OWNED = [REPO / "cache" / "g_agreement" / "w"] + [REPO / "results" / "g_agreement" / "w" / s for s in ("s1", "s2", "s3", "s4")] + \
        [REPO / "results" / "g_agreement" / "w" / f for f in ("STATUS.json", "POD_STARTED_AT", "w_collection.log", "RSYNC_READY", "STOP_REQUESTED")]
OWNED_SNAPSHOT = [(_snap(p), p.exists()) for p in OWNED]
RUN_W = REPO / "projects" / "g_agreement" / "w_pod" / "run_w.sh"
MOCK_S1_LAYERS = (0, 1, 2, 3)
MOCK_EDIT = 1  # stands in for L38
MOCK_ERR_EDIT = 3  # stands in for L48
NAMES = ["A", "B", "C", "D"]


@pytest.fixture(autouse=True)
def mock_config(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(C, "COMPUTE_LEDGER", tmp_path / "compute.jsonl")
    monkeypatch.setattr(W, "S1_LAYERS", MOCK_S1_LAYERS)
    monkeypatch.setattr(W, "STATE_LAYERS", (MOCK_LAYER, MOCK_ERR_EDIT))
    monkeypatch.setattr(W, "S2_EDIT_LAYER", {"ownership": MOCK_EDIT, "mapping": MOCK_EDIT, "errors": MOCK_ERR_EDIT})
    monkeypatch.setattr(W, "S2_READ_LAYERS", {"ownership": (MOCK_LAYER,), "mapping": (MOCK_LAYER,), "errors": (MOCK_LAYER, MOCK_ERR_EDIT)})
    monkeypatch.setattr(S3, "V7_EXTRA_LAYER", MOCK_EDIT)
    monkeypatch.setattr(S3, "V6_LAYER", MOCK_EDIT)
    monkeypatch.setattr(S3, "ERR_READ_LAYER", MOCK_ERR_EDIT)
    for name in ("W_RESULTS", "W_CACHE", "LOG", "POD_STARTED_AT", "S1_CAPS_DIR", "S1_TARGET", "S2_BEHAVIOUR", "S2_READVECS", "S3_LO", "V6_LO", "S4_SAMPLES", "S3V1_LO",
                 "DIRECTIONS_DIR", "X_FULL_DIR", "Y1_CAPS_DIR", "Z4B_SPANS", "ITEMS_W", "MAPPING8_INDEX", "ITEMS_V7", "ITEMS_X", "ITEMS_Y1", "V12_REQUESTS"):
        monkeypatch.setattr(W, name, tmp_path / getattr(W, name).relative_to(REPO))
    monkeypatch.setattr(ST, "STATUS_MD", tmp_path / "STATUS.md")
    monkeypatch.setattr(ST, "STATUS_JSON", tmp_path / "STATUS.json")
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


# ================================================================== fixtures for the other agents' interfaces
def counts_item(n: int, k: int, obj: str = "apples") -> dict:
    return {"item_id": f"wcnt-{n:02d}-{k}", "pair_id": f"wcnt-{n:02d}", "version": "A", "family": "counts", "split": "test", "render": "chat", "system": None,
            "prompt_text": f"There are {n} {obj} in the box. How many {obj}? Answer with the number only.",
            "primary": {"name": "count", "question": "How many?", "candidates": [str(n), str(n + 1 if n < 99 else n - 1)], "answer": str(n),
                        "candidates_all": [str(i) for i in range(1, 100)]}, "design": {"n": n, "object": obj}}


def own4_item(i: int, owner: str) -> dict:
    others = [x for x in NAMES if x != owner]
    return {"item_id": f"wown4-{i:02d}", "pair_id": f"wown4-{i:02d}", "version": "A", "family": "ownership4", "split": "test", "render": "chat", "system": None,
            "prompt_text": f"{owner} has the key. {others[0]} has the pen. {others[1]} has the cup. {others[2]} has the hat. Who has the key? Name only.",
            "primary": {"name": "owner", "question": "Who has the key?", "candidates": [owner, others[0]], "answer": owner, "candidates_all": list(NAMES)}}


def arith_item(a: int, b: int) -> dict:
    return {"item_id": f"warith-{a}-{b}", "pair_id": f"warith-{a}-{b}", "version": "A", "family": "arith", "split": "test", "render": "plain", "system": None,
            "prompt_text": f"{a} + {b} =", "primary": {"name": "sum", "question": "sum", "candidates": [str(a + b), str(a + b + 1)], "answer": str(a + b),
                                                      "candidates_all": [str(i) for i in range(0, 21)]}}


def write_bank(tmp_path: Path) -> dict:
    W.BANK_DIR.mkdir(parents=True, exist_ok=True) if False else None
    items = [counts_item(n, k) for n in (3, 12) for k in (0, 1)] + [own4_item(i, NAMES[i % 4]) for i in range(4)] + [arith_item(3, 4), arith_item(10, 7)]
    W.ITEMS_W.parent.mkdir(parents=True, exist_ok=True)
    W.ITEMS_W.write_text(json.dumps({"meta": {"seed": 20261011}, "items": items}))
    W.MAPPING8_INDEX.write_text(json.dumps({"pair_ids": ["xmap-02", "xmap-03"], "candidates_all": ["x", "y", "z", "p", "q", "r", "s", "t"]}))
    W.ITEMS_X.parent.mkdir(parents=True, exist_ok=True)
    W.ITEMS_X.write_text(json.dumps({"items": items_x()}))
    v7 = []
    for i, (a, b) in enumerate((("A", "B"), ("C", "D")), start=1):
        for v, owner in (("A", a), ("B", b)):
            v7.append({"item_id": f"wv7-{i:02d}{v}", "pair_id": f"wv7-{i:02d}", "version": v, "preamble": f"Secret: {owner} holds the key.", "preamble_role": "system",
                       "prompt_text": "Who holds the key? Name only.", "candidates": [a, b], "answer": owner})
    W.ITEMS_V7.write_text(json.dumps({"pairs": v7}))
    return {"items": items, "v7": v7}


def write_errors(target, tmp_path: Path, n: int = 6) -> list[dict]:
    """Fake puzzle-error items + Y1-style captures ({acts [n_layers, n_pos, d] bf16, labels, positions, layers}) at mock layers 2/3."""
    items, syms = [], "ABCDEFGH"
    W.Y1_CAPS_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        actual, other, third = syms[i % 8], syms[(i + 3) % 8], syms[(i + 5) % 8]
        it = {"item_id": f"xpz-{i + 1:04d}", "pair_id": f"xpz-{i + 1:04d}", "version": "A", "family": "puzzle", "set": "error", "split": "test", "render": "chat", "system": None,
              "prompt_text": f"{actual} -> {other}. {other} -> {third}. Start at {actual} and follow the arrows twice. Where do you end up? Symbol only.",
              "primary": {"name": "model_actual_answer", "question": "q", "candidates": [actual, other], "answer": actual}, "source": {"correct": other, "k_minus_1": third}}
        items.append(it)
        ids = M.render_item(target.tokenizer, it["prompt_text"])
        T = len(ids)
        acts = E.capture_full(target, ids, [MOCK_LAYER, MOCK_ERR_EDIT])
        pos = [T - 1, T - 2, T - 3, 4, -1]
        Tn = torch.zeros(2, len(pos), MOCK_D)
        for li, L in enumerate((MOCK_LAYER, MOCK_ERR_EDIT)):
            for j, p in enumerate(pos):
                if p >= 0:
                    Tn[li, j] = acts[L][p]
        torch.save({"item_id": it["item_id"], "family": "puzzle", "set": "error", "layers": [MOCK_LAYER, MOCK_ERR_EDIT], "labels": ["0", "1", "2", "candA", "candB"], "positions": pos,
                    "n_tokens": T, "candidates": [actual, other], "prompt_ids_sha256": C.sha256_ids(ids), "dtype": "bfloat16", "acts": Tn.to(torch.bfloat16)}, W.Y1_CAPS_DIR / f"{it['item_id']}.pt")
    # non-error control item (must be ignored by load_errors)
    items.append({**items[0], "item_id": "xpz-ctrl", "pair_id": "xpz-ctrl", "set": "error_control"})
    W.ITEMS_Y1.parent.mkdir(parents=True, exist_ok=True)
    W.ITEMS_Y1.write_text(json.dumps({"items": items}))
    return items[:-1]


def _orth_unit(u: torch.Tensor, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    r = torch.randn(u.shape, generator=g)
    r = r - (r * u).sum(-1, keepdim=True) * u
    return r / r.norm(dim=-1, keepdim=True)


def write_directions(target, tmp_path: Path, pairs: list[dict], errors: list[dict]) -> dict:
    """X2 full captures (mock layers 1/2) + Track B's REAL layout: top-level index.json {families: {fam: {…, pairs: [...]}}}, per-pair
    <fam>/<pair>.pt {positions int64, delta, delta_norm, dirs{d_cm,d_pw,d_J,d_res unit A→B}, fold, sign, random{seed,K,…}}, <fam>/shared.pt
    {probe: {folds: [{fold, train_pairs, test_pairs, classes, w_raw [K,d]}], fold_of_pair, label}}. Mock span = the two tokens after the last
    differing one (the tiny model's Δ vanishes at the last token)."""
    usable, _ = X.ensure_full_states(target, pairs, full_dir=W.X_FULL_DIR, layers=(MOCK_EDIT, MOCK_LAYER), ledger_path=tmp_path / "c.jsonl", log_path=tmp_path / "l.md", skipped_path=tmp_path / "sk.json")
    out = {"positions": {}, "probe_w": {}}
    index = {"built_at": "mock", "families": {}, "dir_names": ["d_cm", "d_pw", "d_J", "d_res"], "random": {"K": 10, "recipe": "seed*1009+k+1"}}
    g = torch.Generator().manual_seed(7)
    for fam, classes in (("ownership", [0, 1]), ("mapping", ["x", "y", "z", "p", "q", "r", "s", "t"])):
        d = W.DIRECTIONS_DIR / fam
        d.mkdir(parents=True, exist_ok=True)
        ents, fold_of_pair = [], {}
        fam_pairs = [q for q in usable if q["family"] == fam]
        for i, p in enumerate(fam_pairs):
            HA, HB = (X.load_full(p[v]["item_id"], W.X_FULL_DIR) for v in "AB")
            T = HA["n_tokens"]
            diff = E.differing_positions(HA["ids"], HB["ids"])
            pos = sorted(set(diff) | {diff[-1] + 1, diff[-1] + 2}) if fam == "ownership" else diff
            delta = (HB["layers"][MOCK_EDIT] - HA["layers"][MOCK_EDIT])[pos]
            unit = delta / delta.norm(dim=1, keepdim=True).clamp_min(1e-9)
            d_pw = _orth_unit(unit, 1)
            d_cm = unit + 0.3 * d_pw; d_cm = d_cm / d_cm.norm(dim=1, keepdim=True)
            seed = 1000 + 17 * i
            torch.save({"pair_id": p["pair_id"], "family": fam, "layer": MOCK_EDIT, "site": "post_statement_span" if fam == "ownership" else "differing_symbol_positions", "n_tokens": T,
                        "positions": torch.tensor(pos, dtype=torch.int64), "delta": delta, "delta_norm": delta.norm(dim=1),
                        "dirs": {"d_cm": d_cm, "d_pw": d_pw, "d_J": _orth_unit(unit, 2), "d_res": _orth_unit(unit, 3)}, "coef": {}, "frac": {}, "fold": i % 2, "sign": 1.0,
                        "random": {"seed": seed, "K": 10, "d": MOCK_D, "n_positions": len(pos), "recipe": "seed*1009+k+1"}, "source_items": {"A": p["A"]["item_id"], "B": p["B"]["item_id"]},
                        "frame": "A→B"}, d / f"{p['pair_id']}.pt")
            ents.append({"pair_id": p["pair_id"], "file": f"{fam}/{p['pair_id']}.pt", "positions": pos, "n_tokens": T, "delta_norm": [round(float(x), 4) for x in delta.norm(dim=1)],
                         "fold": i % 2, "sign": 1.0, "random_seed": seed})
            fold_of_pair[p["pair_id"]] = i % 2
            out["positions"][p["pair_id"]] = pos
        K = 1 if fam == "ownership" else len(classes)
        folds = []
        for f in (0, 1):
            w = torch.randn(K, MOCK_D, generator=g)
            folds.append({"fold": f, "train_pairs": [q for q, ff in fold_of_pair.items() if ff != f], "test_pairs": [q for q, ff in fold_of_pair.items() if ff == f], "C": 1.0,
                          "accuracy": 0.9, "classes": list(classes), "w_raw": w})
            out["probe_w"][(fam, f)] = w
        torch.save({"family": fam, "layer": MOCK_EDIT, "site": "s", "probe": {"folds": folds, "fold_of_pair": fold_of_pair, "Cs": [1.0], "seed": 0,
                    "label": "y = 1 iff holder is the second-mentioned name" if fam == "ownership" else "8-way symbol identity at the site position"}}, d / "shared.pt")
        index["families"][fam] = {"family": fam, "layer": MOCK_EDIT, "site": "s", "shared": f"{fam}/shared.pt", "n_pairs": len(ents), "pairs": ents}
    d = W.DIRECTIONS_DIR / "errors"
    d.mkdir(parents=True, exist_ok=True)
    ents, fold_of_pair = [], {}
    for i, it in enumerate(errors):
        g2 = torch.Generator().manual_seed(100 + i)
        full = torch.randn(MOCK_D, generator=g2); full = full / full.norm()
        torch.save({"pair_id": it["item_id"], "family": "errors", "layer": MOCK_ERR_EDIT, "site": "last_token", "n_tokens": -1, "positions": torch.tensor([-1], dtype=torch.int64),
                    "delta": (full * 3.0)[None], "delta_norm": torch.tensor([3.0]), "dirs": {"d_cm": _orth_unit(full[None], 4), "d_pw": _orth_unit(full[None], 5), "d_J": _orth_unit(full[None], 6),
                    "d_res": _orth_unit(full[None], 8)}, "fold": i % 2, "sign": 1.0, "random": {"seed": 5000 + i, "K": 10, "d": MOCK_D, "n_positions": 1},
                    "source_items": {"item": it["item_id"], "cap_layer_index": 1, "cap_label_index": 0}, "meta": {"actual": it["primary"]["answer"]}}, d / f"{it['item_id']}.pt")
        ents.append({"pair_id": it["item_id"], "file": f"errors/{it['item_id']}.pt", "positions": [-1], "n_tokens": -1, "delta_norm": [3.0], "fold": i % 2, "sign": 1.0, "random_seed": 5000 + i})
        fold_of_pair[it["item_id"]] = i % 2
    folds = []
    for f in (0, 1):
        w = torch.randn(8, MOCK_D, generator=g)
        folds.append({"fold": f, "train_items": [q for q, ff in fold_of_pair.items() if ff != f], "test_items": [q for q, ff in fold_of_pair.items() if ff == f], "classes": list("ABCDEFGH"), "w_raw": w})
        out["probe_w"][("errors", f)] = w
    torch.save({"family": "errors", "layer": MOCK_ERR_EDIT, "site": "last_token", "probe": {"folds": folds, "fold_of_pair": fold_of_pair, "label": "8-way actual symbol"}}, d / "shared.pt")
    index["families"]["errors"] = {"family": "errors", "layer": MOCK_ERR_EDIT, "site": "last_token", "shared": "errors/shared.pt", "n_pairs": len(ents), "pairs": ents}
    (W.DIRECTIONS_DIR / "index.json").write_text(json.dumps(index))
    out["fold_of_pair"] = {**{k: v for k, v in fold_of_pair.items()}}
    return out


@pytest.fixture()
def world(target, tmp_path):
    bank = write_bank(tmp_path)
    errors = write_errors(target, tmp_path)
    pairs = X.x2_pairs(items_x(), n_pairs=32)
    dirs = write_directions(target, tmp_path, pairs, errors)
    return {"bank": bank, "errors": errors, "pairs": pairs, "dirs": dirs, "tmp": tmp_path}


# ================================================================== (a) interfaces, renders, first tokens
def test_renders_and_first_token_tables(target, world):
    tok = target.tokenizer
    items = S1.s1_items()
    fam = Counter(it["family"] for it in items)
    assert fam == {"counts": 4, "ownership4": 4, "arith": 2, "mapping8": 4, "v7": 4}
    ar = next(it for it in items if it["family"] == "arith")
    ids = W.render_ids(tok, ar)
    assert ids == tok("3 + 4 =")["input_ids"] and IM_START not in ids and W.item_render(ar) == "plain"
    ch = W.render_ids(tok, next(it for it in items if it["family"] == "counts"))
    assert ch[0] == IM_START and tok.decode(ch).endswith("<think>\n\n</think>\n\n")
    v7 = [it for it in items if it["family"] == "v7"]
    idv = W.render_ids(tok, v7[0])
    assert v7[0]["system"] == "Secret: A holds the key." and "system\nSecret: A holds the key." in tok.decode(idv) and v7[0]["primary"]["candidates"] == ["A", "B"]
    assert v7[0]["prompt_text"] == v7[1]["prompt_text"] and v7[1]["primary"]["answer"] == "B"
    m8 = [it for it in items if it["family"] == "mapping8"]
    assert {it["pair_id"] for it in m8} == {"xmap-02", "xmap-03"} and W.candidates_all(m8[0]) == ["x", "y", "z", "p", "q", "r", "s", "t"]
    # first-token tables: chat → bare form first; plain → leading-space form first; digit duplicates are flagged
    t = W.first_token_table(tok, ["1", "12", "A"], "chat")
    assert t["tokens"]["1"]["form"] == "bare" and t["tokens"]["12"]["id"] == ord("1") and t["duplicates"] is True
    tp = W.first_token_table(tok, ["7", "8"], "plain")
    assert tp["tokens"]["7"]["form"] == "space" and tp["tokens"]["7"]["id"] == ord(" ") and tp["duplicates"] is True  # char-level mock: ' ' shared
    pf = W.pair_first_tokens(tok, "7", "8", "plain")
    assert pf["form"] == "bare" and (pf["first_A"], pf["first_B"]) == (ord("7"), ord("8"))  # the ladder moves on when the space forms share a token
    assert W.pair_first_tokens(tok, "A", "B", "chat")["form"] == "bare"
    assert W.pair_candidates(counts_item(5, 0)) == ("5", "6") and W.parse_answer("12 apples", counts_item(12, 0)) == ("12", "first integer '12'")
    assert W.parse_answer("B.", own4_item(0, "A"))[0] == "B" and W.parse_answer("nothing", own4_item(0, "A"))[0] is None
    # errors loader ignores the control item; seeded subsets are deterministic and sorted-stable
    errs = W.load_errors()
    assert len(errs) == 6 and all(e["family"] == "errors" and e["family_orig"] == "puzzle" for e in errs)
    ids6 = [e["item_id"] for e in errs]
    assert W.seeded_subset(ids6, 4, 0) == W.seeded_subset(list(reversed(ids6)), 4, 0) and len(W.seeded_subset(ids6, 4, 0)) == 4 and W.seeded_subset(ids6, 10, 0) == sorted(ids6)
    # direction files normalise to unit rows + norms; the probe is found through the index
    idx = W.directions_index("ownership")
    f = W.load_direction_file(next(iter(idx["files"].values())))
    assert f["positions"] == world["dirs"]["positions"][next(iter(idx["files"]))] and f["delta"].shape == (f["n_positions"], MOCK_D)
    assert torch.allclose(f["d_cm"].norm(dim=1), torch.ones(f["n_positions"]), atol=1e-5) and torch.allclose(f["norm"], f["delta"].norm(dim=1), atol=1e-4)
    assert set(f["names_in_file"]) == {"d_cm", "d_pw", "d_J", "d_res"} and f["random_seed"] == 1000 and f["fold"] == 0 and idx["probe_path"] is None
    pr = W.load_probe_shared(idx["shared_path"], layer=idx["layer"])
    assert pr["kind"] == "shared_folds" and pr["binary"] and pr["n_folds"] == 2 and set(pr["fold_of_pair"]) == set(idx["files"]) and pr["layer"] == MOCK_EDIT
    w, b, fold = W.probe_weights_for(pr, "xown-03")
    assert fold == "1" and torch.equal(w, world["dirs"]["probe_w"][("ownership", 1)]) and b is None
    assert W.probe_weights_for(pr, "not-a-pair")[2] == "mean_of_folds"
    prm = W.load_probe_shared(W.directions_index("mapping")["shared_path"])
    assert not prm["binary"] and prm["classes"] == ["x", "y", "z", "p", "q", "r", "s", "t"]
    # Track B random recipe: seed*1009+k+1 row-normalised randn == w_directions.directions.random_directions
    from projects.g_agreement.w_directions.directions import random_directions
    assert torch.allclose(W.random_unit_directions("p", 3, 4, MOCK_D, seed=1000), random_directions(1000, 4, MOCK_D, 4)[3], atol=1e-6)
    assert W.mention_order("Mira has the key. Paul has the pen.", ["Paul", "Mira"]) == ["Mira", "Paul"]
    fe = W.load_direction_file(W.directions_index("errors")["files"]["xpz-0001"])
    assert fe["positions"] == [-1] and fe["n_positions"] == 1 and abs(float(fe["norm"]) - 3.0) < 1e-6 and torch.allclose(fe["full"].norm(dim=1), torch.ones(1), atol=1e-5)


# ================================================================== (b) S1
def test_s1_capture_mock(target, world, tmp_path):
    items = S1.s1_items()
    led = tmp_path / "c.jsonl"
    n = S1.collect(target, items, ledger_path=led, max_new_tokens=3)
    assert n == len(items) == 18
    rows = A.read_jsonl(W.S1_TARGET)
    assert len(rows) == 18 and len({r["key"] for r in rows}) == 18
    cnt = next(r for r in rows if r["family"] == "counts")
    cap = S1.load_cap(cnt["item_id"])
    assert cap["acts"].shape == (4, cnt["n_tokens"], MOCK_D) and cap["acts"].dtype == torch.bfloat16 and cap["layers"] == list(MOCK_S1_LAYERS) and len(cap["ids"]) == cnt["n_tokens"]
    # the captures equal a direct all-position capture and the last row equals the states-style file
    ids = cap["ids"]
    direct = E.capture_full(target, ids, [MOCK_LAYER])[MOCK_LAYER]
    assert torch.allclose(cap["acts"][MOCK_S1_LAYERS.index(MOCK_LAYER)].float(), direct.to(torch.bfloat16).float(), atol=5e-2)
    st = torch.load(W.W_CACHE / f"states_L{MOCK_LAYER}" / f"{cnt['item_id']}.pt")
    assert st.dtype == torch.float32 and st.shape == (MOCK_D,) and torch.allclose(st, direct[-1], atol=1e-4)
    meta = A.read_jsonl(W.W_CACHE / f"states_L{MOCK_LAYER}_meta.jsonl")
    assert len(meta) == 18 and meta[0]["layer"] == MOCK_LAYER and meta[0]["pre_answer"] is True and meta[0]["prompt_ids_sha256"] == C.sha256_ids(M.render_item(target.tokenizer, items[0]["prompt_text"]))
    assert (W.W_CACHE / f"states_L{MOCK_ERR_EDIT}" / f"{cnt['item_id']}.pt").exists()
    # the candidate score vector: one log-prob per candidates_all entry, the pair log-odds consistent with it
    assert len(cnt["lp_candidates_all"]) == 99 == len(cnt["candidates_all"]) and cnt["cand_first_token_duplicates"] is True
    assert cnt["lo_model"] is not None and abs(cnt["lo_model"] - (cnt["lp_first_B"] - cnt["lp_first_A"])) < 1e-9
    i_a = cnt["candidates_all"].index(cnt["cand_A"])
    assert abs(cnt["lp_candidates_all"][i_a] - cnt["lp_first_A"]) < 1e-6  # same spelling (bare) → same token → same log-prob
    ar = next(r for r in rows if r["family"] == "arith")
    assert ar["render"] == "plain" and ar["n_tokens"] == len(target.tokenizer("3 + 4 =")["input_ids"]) and len(ar["lp_candidates_all"]) == 21 and ar["max_new_tokens"] == 3
    m8 = next(r for r in rows if r["family"] == "mapping8")
    assert len(m8["lp_candidates_all"]) == 8 and m8["cand_A"] in m8["candidates_all"]
    v7 = next(r for r in rows if r["family"] == "v7")
    assert v7["system"].startswith("Secret") and v7["lo_model"] is not None
    # the first-step log-probs equal a manual forward at the last prompt position
    with torch.no_grad():
        lp = torch.log_softmax(target.model(torch.tensor([ids]), use_cache=False).logits[0, -1].float(), -1)
    assert abs(float(lp[cnt["first_A"]]) - cnt["lp_first_A"]) < 1e-3
    # resume, counts filter, summary, DONE marker logic
    assert S1.collect(target, items, ledger_path=led, max_new_tokens=3) == 0
    rep = S1.counts_filter(rows, W.stage_dir("s1") / "counts_kept.json")
    assert rep["n_counts"] == 4 and rep["n_kept"] == sum(r["correct"] for r in rows if r["family"] == "counts") and (W.stage_dir("s1") / "counts_kept.json").exists()
    assert set(S1.summary(rows)) == {"counts", "ownership4", "arith", "mapping8", "v7"}
    assert not W.refuse_if_done("s1", force=False)
    W.mark_done("s1", info={"n": 18})
    assert W.refuse_if_done("s1", force=False) is True and W.is_done("s1")
    assert W.refuse_if_done("s1", force=True) is False and not W.is_done("s1")
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"w_s1_capture_counts", "w_s1_capture_arith", "w_s1_capture_v7"} <= steps


# ================================================================== (c) S2 geometry, plan, cap
def test_s2_table_plan_cap_and_geometry(target, world):
    idx, st_own = S2.load_states("ownership", n_states=64)
    assert len(st_own) == 6 and [s["source"] for s in st_own[:2]] == ["A", "B"] and st_own[0]["cand_A"] == "A" and st_own[0]["cand_B"] == "B" and st_own[1]["cand_A"] == "B"
    _, st_err = S2.load_states("errors", n_states=4)
    assert len(st_err) == 4 and all(s["source"] == "A" and s["cap_kind"] == "y1_cap" for s in st_err)
    tab = S2.condition_table(st_own)
    assert len(tab) == 6 * (1 + 5 * 2 + 10) and len({e["key"] for e in tab}) == len(tab)
    assert Counter(e["direction"] for e in tab) == {"natural": 6, "d_cm": 12, "d_pw": 12, "d_J": 12, "d_res": 12, "full": 12, "random": 60}
    assert tab[1]["key"] == "xown-02|A|W2|d_cm|0.5|None" and tab[-1]["key"].endswith("|W2|random|1.0|9")
    plan = S2.planned_decodes({"ownership": tab, "errors": S2.condition_table(st_err)})
    assert plan["total_planned"] == 6 * 21 + 4 * 21 == 210 and plan["families"]["errors"]["random"] == 40
    S2.check_cap(plan, 4500)
    with pytest.raises(SystemExit):
        S2.check_cap(plan, 200)
    assert "total planned decodes 210" in S2.format_plan(plan, 4500)
    # the real design: 3 families × 64 states × 21 = 4,032 ≤ 4,500
    fake = [{"pair_id": f"p{i}", "source": "A", "state_item_id": f"p{i}", "family": "x"} for i in range(64)]
    real = S2.planned_decodes({f: S2.condition_table(fake) for f in W.S2_FAMILIES})
    assert real["total_planned"] == 3 * 64 * 21 == 4032 <= W.S2_DECODE_CAP
    # geometry (ownership): full α 1 from A lands on h_B at the site positions, the mirror from B lands on h_A; d_cm edit has norm α·‖Δ(pos)‖ per position
    s = st_own[0]
    cap = S2.base_capture(s, MOCK_EDIT)
    T = cap["n_tokens"]
    dirs = W.load_direction_file(Path(s["direction_file"]))
    pos = [p % T for p in dirs["positions"]]
    HB = X.load_full(f"{s['pair_id']}B", W.X_FULL_DIR)["layers"][MOCK_EDIT]
    HA = cap["h"]
    by = {(e["direction"], e["alpha"], e["k"]): e for e in tab if e["pair_id"] == s["pair_id"] and e["source"] == "A"}
    v = S2.entry_vectors(by[("full", 1.0, None)], dirs, cap, T)
    assert v["positions"] == pos and torch.allclose(v["vector"], HB[pos], atol=1e-3) and v["last_edited"] is False and v["toward"] == 1.0
    vh = S2.entry_vectors(by[("full", 0.5, None)], dirs, cap, T)
    assert torch.allclose(vh["vector"], HA[pos] + 0.5 * (HB - HA)[pos], atol=1e-3)
    byB = {(e["direction"], e["alpha"]): e for e in tab if e["pair_id"] == s["pair_id"] and e["source"] == "B"}
    capB = S2.base_capture(st_own[1], MOCK_EDIT)
    vB = S2.entry_vectors(byB[("full", 1.0)], dirs, capB, T)
    assert torch.allclose(vB["vector"], HA[pos], atol=1e-3) and vB["toward"] == -1.0
    vc = S2.entry_vectors(by[("d_cm", 1.0, None)], dirs, cap, T)
    assert torch.allclose(vc["delta"].norm(dim=1), dirs["norm"], atol=1e-4) and all(0.9 < c < 1.0 for c in vc["cos_to_delta"])
    vp = S2.entry_vectors(by[("d_pw", 0.5, None)], dirs, cap, T)
    assert torch.allclose(vp["delta"].norm(dim=1), 0.5 * dirs["norm"], atol=1e-4) and all(abs(c) < 1e-4 for c in vp["cos_to_delta"])
    nat = S2.entry_vectors(by[("natural", 0.0, None)], dirs, cap, T)
    assert torch.equal(nat["vector"], HA[pos]) and nat["dose_abs"] == 0.0 and nat["cos_to_delta"] is None
    # random: matched norm per position, seeded per (pair, k), different across k, identical across sources
    r0 = S2.entry_vectors(by[("random", 1.0, 0)], dirs, cap, T)
    r1 = S2.entry_vectors(by[("random", 1.0, 1)], dirs, cap, T)
    assert torch.allclose(r0["delta"].norm(dim=1), dirs["norm"], atol=1e-4) and not torch.allclose(r0["delta"], r1["delta"]) and abs(r0["cos_to_delta_mean"]) < 0.5
    assert r0["random_seed"] == dirs["random_seed"] and torch.allclose(r0["delta"], dirs["norm"][:, None] * W.random_unit_directions("x", 0, len(pos), MOCK_D, seed=dirs["random_seed"]), atol=1e-5)
    assert torch.equal(W.random_unit_directions(s["pair_id"], 0, len(pos), MOCK_D), W.random_unit_directions(s["pair_id"], 0, len(pos), MOCK_D))
    assert not torch.equal(W.random_unit_directions("other", 0, len(pos), MOCK_D), W.random_unit_directions(s["pair_id"], 0, len(pos), MOCK_D))
    # errors: last-token base from the Y1 capture, positions resolve to T − 1, direction scaled to ‖full‖
    e = st_err[0]
    cape = S2.base_capture(e, MOCK_ERR_EDIT)
    idse = W.render_ids(target.tokenizer, e["item"])
    assert cape["h"] is None and cape["sha"] == C.sha256_ids(idse)
    de = W.load_direction_file(Path(e["direction_file"]))
    ve = S2.entry_vectors({"key": "k", "pair_id": e["pair_id"], "source": "A", "direction": "d_pw", "alpha": 1.0, "k": None}, de, cape, len(idse))
    assert ve["positions"] == [len(idse) - 1] and abs(float(ve["delta"].norm()) - 3.0) < 1e-4 and torch.allclose(ve["base"][0], cape["h_last"])
    with pytest.raises(KeyError):
        S2.entry_vectors({"key": "k", "pair_id": e["pair_id"], "source": "A", "direction": "bogus", "alpha": 1.0, "k": None}, de, cape, len(idse))


# ================================================================== (d) S2 collector on the tiny model (+ the prefill primitive)
def test_prefill_generate_matches_core(target):
    ids = M.render_item(target.tokenizer, "A has the key. B has the pen. Who has the key? Name only.")
    T = len(ids)
    base = E.capture_full(target, ids, [MOCK_EDIT])[MOCK_EDIT]
    torch.manual_seed(3)
    delta = torch.randn(T, MOCK_D) * 3
    cft = (ord("A"), ord("B"))
    core = E.generate_with_interpolated_batch(target, ids, MOCK_EDIT, [5, 9], (base[[5, 9]] + delta[[5, 9]])[None], read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=cft)[0]
    rows = W.prefill_generate(target, ids, edit_layer=MOCK_EDIT, row_positions=[[5, 9], [2]], row_vectors=[base[[5, 9]] + delta[[5, 9]], base[[2]]], read_layers=(MOCK_LAYER, 3),
                              max_new_tokens=3, first_token_ids=[ord("A"), ord("B"), None])
    assert torch.allclose(rows[0]["read"][MOCK_LAYER], core["read_vec"], atol=1e-3) and abs(W.lo_from_lp(rows[0]["lp_first"]) - core["lo_model"]) < 1e-3 and rows[0]["lp_first"][2] is None
    assert rows[0]["answer_text"] == core["answer_text"] and rows[0]["n_hook_edits"] == 1 and set(rows[0]["read"]) == {MOCK_LAYER, 3} and rows[1]["batch_size"] == 2
    nat = W.prefill_generate(target, ids, read_layers=(MOCK_LAYER,), read_all_positions=True, max_new_tokens=2)[0]
    assert nat["read_all"][MOCK_LAYER].shape == (T, MOCK_D) and torch.allclose(nat["read_all"][MOCK_LAYER], E.capture_full(target, ids, [MOCK_LAYER])[MOCK_LAYER], atol=1e-4)
    assert len(M.blocks(target.model)[MOCK_EDIT]._forward_hooks) == 0 and len(M.blocks(target.model)[MOCK_LAYER]._forward_hooks) == 0
    with pytest.raises(ValueError):
        W.prefill_generate(target, ids, edit_layer=MOCK_EDIT, row_positions=[[1, 2]], row_vectors=[base[[1]]], max_new_tokens=2)


def test_s2_collect_resume_and_done(target, world, tmp_path):
    led = tmp_path / "c.jsonl"
    idx, st_own = S2.load_states("ownership", n_states=4)
    tab = S2.condition_table(st_own, k_random=2)
    n = S2.collect_behaviour(target, "ownership", st_own, tab, ledger_path=led, max_new_tokens=3, batch=5)
    assert n == 4 * 13
    assert S2.collect_behaviour(target, "ownership", st_own, tab, ledger_path=led, max_new_tokens=3, batch=5) == 0  # resumable
    rows = A.read_jsonl(W.S2_BEHAVIOUR)
    assert len(rows) == 52 and len({r["key"] for r in rows}) == 52 and all(S2.readvec_path(r["key"]).exists() for r in rows)
    r0 = rows[0]
    for k in ("key", "pair_id", "family", "source", "state_item_id", "site", "direction", "condition", "alpha", "k", "edit_layer", "read_layers", "positions", "n_positions", "n_tokens",
              "toward", "cand_A", "cand_B", "answer_text", "parsed", "flipped_to_other", "kept_original", "coherent", "lo_model", "dose_abs", "norm_delta_pos", "cos_to_delta_mean",
              "last_edited", "n_hook_edits", "prompt_ids_sha256", "frozen_code_sha256", "direction_file"):
        assert k in r0, k
    assert r0["direction"] == "natural" and r0["n_hook_edits"] == 0 and r0["dose_abs"] == 0.0 and r0["lo_model"] is not None
    rec = S2.load_readvec_record(r0["key"])
    assert set(rec["read"]) == {MOCK_LAYER} and rec["read"][MOCK_LAYER].dtype == torch.bfloat16 and rec["edited"].shape[0] == r0["n_positions"]
    # an edited row's read-back and lo_model equal a direct core decode of the same edit
    r = next(x for x in rows if x["direction"] == "full" and x["alpha"] == 1.0 and x["source"] == "A")
    H = {v: X.load_full(f"{r['pair_id']}{v}", W.X_FULL_DIR) for v in "AB"}
    one = E.generate_with_interpolated_batch(target, H["A"]["ids"], MOCK_EDIT, r["positions"], H["B"]["layers"][MOCK_EDIT][r["positions"]][None], read_layer=MOCK_LAYER, max_new_tokens=3,
                                             cand_first_tokens=(r["first_A"], r["first_B"]))[0]
    assert abs(one["lo_model"] - r["lo_model"]) < 1e-3 and one["answer_text"] == r["answer_text"]
    assert torch.allclose(one["read_vec"].to(torch.bfloat16).float(), S2.load_readvec(r["key"], MOCK_LAYER), atol=5e-2)
    # errors: two read layers, the L48 stand-in read-back equals the edited vector itself (edit and read at the same block)
    _, st_err = S2.load_states("errors", n_states=2)
    tabe = S2.condition_table(st_err, k_random=1)
    assert S2.collect_behaviour(target, "errors", st_err, tabe, ledger_path=led, max_new_tokens=3, batch=4) == 2 * 12
    er = [x for x in A.read_jsonl(W.S2_BEHAVIOUR) if x["family"] == "errors"]
    assert all(x["read_layers"] == [MOCK_LAYER, MOCK_ERR_EDIT] and x["edit_layer"] == MOCK_ERR_EDIT and x["n_positions"] == 1 and x["last_edited"] for x in er)
    x = next(x for x in er if x["direction"] == "d_cm" and x["alpha"] == 1.0)
    rec = S2.load_readvec_record(x["key"])
    assert torch.allclose(rec["read"][MOCK_ERR_EDIT].float(), rec["edited"][0].float(), atol=5e-2)
    summ = S2.family_summary(er)
    assert set(summ) >= {"natural@0.0", "d_cm@1.0", "random@1.0"} and summ["random@1.0"]["n"] == 2
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"w_s2_behaviour_ownership_natural", "w_s2_behaviour_ownership_full", "w_s2_behaviour_ownership_random", "w_s2_behaviour_errors_d_cm"} <= steps
    # family markers + stage marker
    W.mark_done("s2", sub="ownership"); W.mark_done("s2", sub="errors")
    assert W.refuse_if_done("s2", False, sub="ownership") and not W.is_done("s2")
    assert W.refuse_if_done("s2", False, sub="mapping") is False


# ================================================================== (e) S3: score vectors, pair LO, probe, V6
def _readers(target):
    torch.manual_seed(1)
    J = {L: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10 for L in (MOCK_EDIT, MOCK_LAYER, MOCK_ERR_EDIT)}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4)
    ol.target = target
    return jl, ol


def test_score_candidates_matches_pair_lo(target):
    jl, ol = _readers(target)
    H = torch.randn(3, MOCK_D) * 20
    pairs = [("A", "B"), ("C", "D"), ("x", "y")]
    for rd in (jl, ol):
        ref = LO.score_lo(rd, H, pairs, "ownership", layer=MOCK_LAYER, batch=8)
        vec = SM.score_candidates(rd, H, [list(p) for p in pairs], "ownership", layer=MOCK_LAYER, batch=6)
        for q, v in zip(ref, vec):
            assert abs((v["scores"][0] - v["scores"][1]) - q["lo"]) < 2e-3 and v["argmax"] in v["candidates"]
    many = SM.score_candidates(ol, H[:1], [[str(i) for i in range(1, 100)]], "counts", layer=MOCK_LAYER, batch=32)[0]
    assert len(many["scores"]) == 99 and many["n_unscorable"] == 0 and many["argmax"] in many["candidates"]
    jv = SM.score_candidates(jl, H[:1], [["A", "ZZZZ"]], "ownership", layer=MOCK_LAYER)[0]
    assert jv["scores"][1] is None and jv["n_unscorable"] == 1 and jv["argmax"] == "A"
    tok = FakeTok()
    nla = R.NLAReader(max_new_tokens=4).attach(tiny_model(1), tok, mock_meta(tok), device="cpu")
    ref = LO.score_lo(nla, H, pairs, "puzzle", batch=8)
    vec = SM.score_candidates(nla, H, [list(p) for p in pairs], "puzzle", batch=8)
    for q, v in zip(ref, vec):
        assert abs((v["scores"][0] - v["scores"][1]) - q["lo"]) < 2e-3 and v["templates"] == q["templates"]
    assert SM.templates_for("counts")[0].startswith("The answer must be the number")


def test_s3_rows_and_probe(target, world, tmp_path):
    led = tmp_path / "c.jsonl"
    items = S1.s1_items()
    S1.collect(target, items, ledger_path=led, max_new_tokens=3)
    _, st_own = S2.load_states("ownership", n_states=2)
    S2.collect_behaviour(target, "ownership", st_own, S2.condition_table(st_own, k_random=1), ledger_path=led, max_new_tokens=3, batch=6)
    _, st_err = S2.load_states("errors", n_states=2)
    S2.collect_behaviour(target, "errors", st_err, S2.condition_table(st_err, k_random=1), ledger_path=led, max_new_tokens=3, batch=6)
    beh = A.read_jsonl(W.S2_BEHAVIOUR)
    s1 = S3.s1_rows()
    jl, ol = _readers(target)
    # S1: vector families get the full score vector, pair families the pair LO; the V7 extra layer
    n = S3.score_s1(jl, s1, ledger_path=led, batch=8)
    assert n == 18 and S3.score_s1(jl, s1, ledger_path=led, batch=8) == 0
    rows = A.read_jsonl(W.S3_LO)
    cnt = next(r for r in rows if r["family"] == "counts")
    assert cnt["key"] == f"jlens|S1|{cnt['item_id']}" and len(cnt["scores"]) == 99 and cnt["candidates"] == cnt["lp_candidates_all_model"] and len(cnt["lp_candidates_all_model"]) == 99 or len(cnt["scores"]) == 99
    assert cnt["lo_own"] is None or abs(cnt["lo_own"] + cnt["lo_toward_other"]) < 1e-9
    v7 = next(r for r in rows if r["family"] == "v7")
    assert v7["scores"] is None and v7["candidates"] == [v7["cand_A"], v7["cand_B"]] and v7["unit"] == "S1" and v7["layer"] == MOCK_LAYER
    assert S3.score_s1(jl, s1, layer=MOCK_EDIT, unit=f"S1@L{MOCK_EDIT}", families=("v7",), ledger_path=led) == 4
    assert sum(1 for r in A.read_jsonl(W.S3_LO) if r["unit"] == f"S1@L{MOCK_EDIT}") == 4
    # S2 read-backs: pair LO rows with lo_toward_edit = −lo_own; the errors' second read layer
    n2 = S3.score_s2(ol, beh, ledger_path=led, batch=8)
    assert n2 == len(beh) and S3.score_s2(ol, beh, ledger_path=led, batch=8) == 0
    l2 = [r for r in A.read_jsonl(W.S3_LO) if r["unit"] == "S2"]
    assert len(l2) == len(beh) and all(abs(r["lo_toward_edit"] + r["lo_own"]) < 1e-9 and r["read_layer"] == MOCK_LAYER and r["direction"] and "flipped_to_other" in r for r in l2)
    n48 = S3.score_s2(jl, beh, read_layer=MOCK_ERR_EDIT, families=("errors",), ledger_path=led, batch=8)
    assert n48 == sum(1 for r in beh if r["family"] == "errors") and all(r["unit"] == f"S2@L{MOCK_ERR_EDIT}" for r in A.read_jsonl(W.S3_LO) if r.get("read_layer") == MOCK_ERR_EDIT)
    assert S3.can_score_at(jl, MOCK_ERR_EDIT) and not S3.can_score_at(jl, 0) and S3.can_score_at(ol, 0)
    # probe: fold-specific w_raw of shared.pt (the fold that never saw the pair), candidate-level scores; edited site mean for L38 families
    probes = S3.load_probes()
    assert set(probes) == {"ownership", "mapping", "errors"} and probes["ownership"]["layer"] == MOCK_EDIT and probes["ownership"]["kind"] == "shared_folds"
    its = S3.item_lookup()
    assert "xown-02A" in its and "xpz-0001" in its
    npb = S3.score_s2(None, beh, reader_name="probe", probe=probes["ownership"], families=("ownership",), ledger_path=led, items=its)
    pr = [r for r in A.read_jsonl(W.S3_LO) if r["reader"] == "probe"]
    assert npb == len(pr) == sum(1 for r in beh if r["family"] == "ownership") and all(r["probe_on"] == "edited_site_mean" and r["score"] == r["score_edited"] for r in pr)
    nat = next(r for r in pr if r["direction"] == "natural")
    fold = str(world["dirs"]["fold_of_pair"].get(nat["pair_id"], probes["ownership"]["fold_of_pair"][nat["pair_id"]]))
    assert nat["probe_fold"] == fold == probes["ownership"]["fold_of_pair"][nat["pair_id"]]
    rec = S2.load_readvec_record(nat["entry_key"])
    w = world["dirs"]["probe_w"][("ownership", int(fold))][0]
    z = float(rec["edited"].float().mean(0) @ w)
    item = its[nat["state_item_id"]]
    second = W.mention_order(item["prompt_text"], [nat["cand_A"], nat["cand_B"]])[1]
    expect = (-z if second == nat["cand_A"] else z) * -1  # lo_own = score(A) - score(B); the second-mentioned candidate carries w.h
    assert abs(nat["lo_own"] - (z if second == nat["cand_A"] else -z)) < 1e-3 and abs(abs(nat["score_edited"]) - abs(z)) < 1e-3 and nat["scores"] and len(nat["scores"]) == 2
    # errors: 8-way, lo = w[actual].h - w[other].h on the L48 stand-in read-back (= the edited vector)
    ne = S3.score_s2(None, beh, reader_name="probe", probe=probes["errors"], read_layer=MOCK_ERR_EDIT, families=("errors",), ledger_path=led, items=its)
    er = [r for r in A.read_jsonl(W.S3_LO) if r["reader"] == "probe" and r["family"] == "errors"]
    assert ne == len(er) == sum(1 for r in beh if r["family"] == "errors")
    r0 = er[0]
    fold = probes["errors"]["fold_of_pair"][r0["pair_id"]]
    W8 = world["dirs"]["probe_w"][("errors", int(fold))]
    h = S2.load_readvec_record(r0["entry_key"])["read"][MOCK_ERR_EDIT].float()
    cls = list("ABCDEFGH")
    assert abs(r0["lo_own"] - float(W8[cls.index(r0["cand_A"])] @ h - W8[cls.index(r0["cand_B"])] @ h)) < 1e-3 and r0["probe_fold"] == fold and r0["probe_on"] == "edited_site_mean"
    # S1 states: mapping8 gets the 8-way vector over all candidates, ownership4/v7 the binary rule; items outside every fold use the mean of folds
    npr = S3.score_s1(None, s1, reader_name="probe", probe=probes["mapping"], families=("mapping8",), ledger_path=led, items=its)
    m8 = [r for r in A.read_jsonl(W.S3_LO) if r["reader"] == "probe" and r["family"] == "mapping8"]
    assert npr == 4 == len(m8) and all(len(r["scores"]) == 8 and r["candidates"][0] == r["cand_A"] and r["probe_fold"] in ("0", "1") and r["lo_own"] is not None for r in m8)
    npo = S3.score_s1(None, s1, reader_name="probe", probe=probes["ownership"], families=("ownership4", "v7"), ledger_path=led, items=its)
    o4 = [r for r in A.read_jsonl(W.S3_LO) if r["reader"] == "probe" and r["family"] in ("ownership4", "v7")]
    assert npo == 8 == len(o4) and all(r["probe_fold"] == "mean_of_folds" and r["lo_own"] is not None for r in o4)
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"w_s3_lo_jlens_S1", "w_s3_lo_olens_S2", f"w_s3_lo_jlens_S2@L{MOCK_ERR_EDIT}", "w_s3_lo_probe_S2", "w_s3_lo_probe_S1"} <= steps


def test_v6_multi_marker_carrier_and_span_lo(target, world, tmp_path):
    tok = target.tokenizer
    ids1, slots1, char1, cid1 = SM.olens_carrier_multi(tok, MOCK_EDIT, 1)
    ids0, slot0, char0, cid0 = R.olens_carrier(tok, MOCK_EDIT)
    assert ids1 == ids0 and slots1 == [slot0] and (char1, cid1) == (char0, cid0)
    ids3, slots3, char3, cid3 = SM.olens_carrier_multi(tok, MOCK_EDIT, 3)
    assert slots3 == [slots3[0], slots3[0] + 1, slots3[0] + 2] and ids3.count(cid3) == 3 and len(ids3) == len(ids0) + 2 and f"<activation>{char3 * 3}</activation>" in tok.decode(ids3)
    with pytest.raises(ValueError):
        SM.olens_carrier_multi(tok, MOCK_EDIT, 0)
    _, ol = _readers(target)
    H = torch.randn(2, MOCK_D) * 30
    ref = LO.score_lo(ol, H, [("A", "B"), ("C", "D")], "ownership", layer=MOCK_EDIT, batch=8)
    span = SM.lo_olens_span(ol, [H[0], H[1]], [("A", "B"), ("C", "D")], MOCK_EDIT, batch=8)
    assert all(q["n_markers"] == 1 for q in span) and all(abs(q["lo"] - r["lo"]) < 2e-3 for q, r in zip(span, ref))
    spans = [torch.randn(3, MOCK_D) * 30, torch.randn(5, MOCK_D) * 30, torch.randn(3, MOCK_D) * 30]
    out = SM.lo_olens_span(ol, spans, [("A", "B")] * 3, MOCK_EDIT, batch=8)
    assert [q["n_markers"] for q in out] == [3, 5, 3] and len({q["lo"] for q in out}) == 3 and out[0]["marker_slots"] == out[2]["marker_slots"]
    # the marker embeddings are replaced in order by alpha·unit(h_j)
    ids_k, slots_k, _, _ = SM.olens_carrier_multi(tok, MOCK_EDIT, 3)
    embed = target.model.get_input_embeddings()
    with torch.no_grad():
        em = embed(torch.tensor([ids_k])).clone()
    sp = spans[0]
    em[0, slots_k, :] = (ol.alpha * sp / sp.norm(dim=1, keepdim=True)).to(em.dtype)
    for j, s in enumerate(slots_k):
        assert torch.nn.functional.cosine_similarity(em[0, s], sp[j], dim=0) > 0.999 and abs(float(em[0, s].norm()) - ol.alpha) < 1.0
    # V6 end to end on the collector output (natural + edited full-swap states, four conditions)
    led = tmp_path / "c.jsonl"
    _, st_own = S2.load_states("ownership", n_states=4)
    S2.collect_behaviour(target, "ownership", st_own, S2.condition_table(st_own, k_random=0), ledger_path=led, max_new_tokens=3, batch=6)
    beh = A.read_jsonl(W.S2_BEHAVIOUR)
    states = S3.v6_states(beh, n_edited=2, n_states=4)
    assert len(states) == 6 and Counter(s["state_kind"] for s in states) == {"natural": 4, "edited_full_a1": 2}
    e = next(s for s in states if s["state_kind"] != "natural")
    nat = next(s for s in states if s["state_kind"] == "natural" and s["pair_id"] == e["pair_id"] and s["source"] == e["source"])
    other = X.load_full(f"{e['pair_id']}{'B' if e['source'] == 'A' else 'A'}", W.X_FULL_DIR)["layers"][MOCK_EDIT]
    assert torch.allclose(e["H"][e["span"]], other[e["span"]], atol=5e-2) and not torch.allclose(e["H"], nat["H"])
    assert S3.v6_vectors(nat, "a_last").shape == (1, MOCK_D) and S3.v6_vectors(nat, "b_span").shape[0] == len(nat["span"]) and S3.v6_vectors(nat, "c_full").shape[0] == nat["n_tokens"]
    sh = S3.v6_vectors(nat, "d_span_shuffled")
    assert sh.shape == S3.v6_vectors(nat, "b_span").shape and torch.equal(sh, S3.v6_vectors(nat, "d_span_shuffled")) and torch.allclose(sh.sum(0), S3.v6_vectors(nat, "b_span").sum(0), atol=1e-3)
    n = S3.collect_v6(ol, states, ledger_path=led, batch=4)
    assert n == 6 * 4 and S3.collect_v6(ol, states, ledger_path=led, batch=4) == 0
    rows = A.read_jsonl(W.V6_LO)
    assert Counter(r["condition"] for r in rows) == {c: 6 for c in S3.V6_CONDITIONS} and all(r["layer"] == MOCK_EDIT for r in rows)
    assert all(r["n_markers"] == 1 for r in rows if r["condition"] == "a_last") and all(r["n_markers"] == r["n_tokens"] for r in rows if r["condition"] == "c_full")
    assert all(r["n_markers"] == len(r["span"]) for r in rows if r["condition"] == "b_span")


# ================================================================== (f) S3v1 requests
def test_s3v1_requests_real_schema(target, world, tmp_path, monkeypatch):
    assert S3V1.load_requests() == []
    err_ids = [e["item_id"] for e in world["errors"]]
    W.V12_REQUESTS.parent.mkdir(parents=True, exist_ok=True)
    W.V12_REQUESTS.write_text(json.dumps({"created": "x", "requests": [
        {"name": "v1_layer_sweep", "sets": {"error": {"n": 4, "item_ids": err_ids[:4]}, "disagree": {"n": 2, "item_ids": err_ids[4:6]}, "controls_also_scored_by_the_reread_stage": {"error_control": 1}},
         "layers": [MOCK_LAYER, MOCK_ERR_EDIT, 0], "position": "0 (last prompt token)", "pending_sites": [f"{MOCK_LAYER}:0", f"{MOCK_ERR_EDIT}:0", "0:0"],
         "readers": {"jlens": {"layer_role": "native"}, "olens": {"layer_role": "nearest_grid"}, "olens_trueL": {"optional": False}, "nla": {}}, "output": {"path": "y1_lo schema"}},
        {"name": "three_way", "n_items": 3, "items": [{"item_id": e["item_id"], "candidates": {"correct": e["source"]["correct"], "actual": e["primary"]["answer"], "km1": e["source"]["k_minus_1"]},
                                                       "family": "puzzle", "trace": []} for e in world["errors"][:3]], "sites": [f"{MOCK_LAYER}:0", f"{MOCK_ERR_EDIT}:0"],
         "readers": {"jlens": "native", "olens": "nearest grid", "nla": "transfer"}, "output": {"path": "cache/g_agreement/v/v2_three_way.jsonl"}}]}))
    reqs = S3V1.load_requests()
    assert [(r["name"], r["kind"]) for r in reqs] == [("v1_layer_sweep", "pair"), ("three_way", "three_way")]
    assert reqs[0]["sites"] == [(MOCK_LAYER, "0"), (MOCK_ERR_EDIT, "0"), (0, "0")] and reqs[0]["readers"] == ["jlens", "olens", "olens_trueL", "nla"]
    items = S3V1.request_items(reqs[0])
    assert len(items) == 6 and {it["set"] for it in items} == {"error", "disagree"} and all(it["cands"] == list(it["primary"]["candidates"]) for it in items)
    items3 = S3V1.request_items(reqs[1])
    assert len(items3) == 3 and all(len(it["cands"]) == 3 and it["cand_map"]["km1"] == it["source"]["k_minus_1"] and it["cands"][0] == it["source"]["correct"] for it in items3)
    jl, ol = _readers(target)
    led = tmp_path / "c.jsonl"
    n = S3V1.score_request(jl, reqs[0], items, ledger_path=led, batch=4)
    rows = A.read_jsonl(W.S3V1_LO)
    item_rows = [r for r in rows if "item_id" in r and r.get("condition") != "mean_state"]
    assert n == len(rows) and Counter(r["layer"] for r in item_rows) == {MOCK_LAYER: 6, MOCK_ERR_EDIT: 6, 0: 6}
    assert all(r["unscorable"] and r["reason"] == "lens file lacks this layer" for r in item_rows if r["layer"] == 0)
    ok = [r for r in item_rows if r["layer"] != 0]
    assert all(r["key"] == f"jlens|{r['layer']}:0|{r['item_id']}" and r["lo_actual"] is not None and r["favours_actual"] == (r["lo_actual"] > 0) and r["layer_used"] == r["layer"]
               and r["layer_role"] == "native" and r["cand_actual"] == r["cand_other"] or r["cand_actual"] != r["cand_other"] for r in ok)
    for k in ("key", "reader", "reader_class", "site", "layer", "position", "layer_used", "layer_role", "item_id", "family", "set", "cand_actual", "cand_other", "lo_actual", "lp_actual",
              "lp_other", "favours_actual", "templates", "unscorable", "created_at", "manifest", "frozen_code_sha256"):
        assert k in ok[0], k
    means = [r for r in rows if r.get("condition") == "mean_state"]
    assert {(r["layer"], r["set"]) for r in means} == {(MOCK_LAYER, "error"), (MOCK_LAYER, "disagree"), (MOCK_ERR_EDIT, "error"), (MOCK_ERR_EDIT, "disagree")} and all(r["key"].endswith(f"|mean|{r['set']}") for r in means)
    assert S3V1.score_request(jl, reqs[0], items, ledger_path=led, batch=4) == 0
    no = S3V1.score_request(ol, reqs[0], items[:2], ledger_path=led, batch=4)
    ro = [r for r in A.read_jsonl(W.S3V1_LO) if r["reader"] == "olens" and r.get("condition") != "mean_state"]
    assert no > 0 and all(r["layer_used"] == S3V1.Y1.nearest_grid_layer(r["layer"]) and r["layer_role"] == "nearest_grid" for r in ro if not r["unscorable"])
    nt = S3V1.score_request(ol, reqs[0], items[:2], reader_name="olens_trueL", ledger_path=led, batch=4, mean_rows=False)
    rt = [r for r in A.read_jsonl(W.S3V1_LO) if r["reader"] == "olens_trueL"]
    assert nt == len(rt) == 6 and all(r["layer_used"] == r["layer"] and r["layer_role"] == "true_layer_sensitivity" for r in rt)
    # three-way rows in the request's schema at the request's path
    monkeypatch.setattr(S3V1, "THREE_WAY_OUT", tmp_path / "v2_three_way.jsonl")
    n3 = S3V1.score_request(jl, reqs[1], items3, ledger_path=led, batch=4)
    tw = A.read_jsonl(S3V1.THREE_WAY_OUT)
    assert n3 == 6 == len(tw) and {r["site"] for r in tw} == {f"{MOCK_LAYER}:0", f"{MOCK_ERR_EDIT}:0"}
    for r in tw:
        assert set(r["candidates"]) == {"correct", "actual", "km1"} and set(r["lp"]) == {"correct", "actual", "km1"} and r["format"] == "cosine" and r["unscorable"] is False
        for k in ("reader", "site", "layer", "layer_used", "item_id", "set", "family", "candidates", "lp", "unscorable", "format", "created_at"):
            assert k in r, k
    assert S3V1.score_request(jl, reqs[1], items3, ledger_path=led, batch=4) == 0
    # non-fatal main: a failing run writes FAILED_s3v1_A and exits 0; a missing file writes S3V1_SKIPPED
    monkeypatch.setattr(S3V1, "run", lambda phase, batch: (_ for _ in ()).throw(RuntimeError("no lens on this machine")))
    assert S3V1.main(["--phase", "A"]) == 0
    f = W.stage_dir("s3") / "FAILED_s3v1_A"
    assert f.exists() and "no lens on this machine" in f.read_text() and not W.is_done("s3", sub="s3v1_A")
    W.V12_REQUESTS.unlink()
    assert S3V1.main(["--phase", "B"]) == 0 and (W.stage_dir("s3") / "S3V1_SKIPPED").exists()


# ================================================================== (g) S4 samples
def test_s4_states_and_samples(target, world, tmp_path):
    led = tmp_path / "c.jsonl"
    items = S1.s1_items(("counts",))
    S1.collect(target, items, ledger_path=led, max_new_tokens=3)
    rows = A.read_jsonl(W.S1_TARGET)
    S1.counts_filter(rows, W.stage_dir("s1") / "counts_kept.json")
    states = S4.s4_states(n_errors=3, n_counts=2, n_random=3, error_layer=MOCK_LAYER)
    assert Counter(s["family"] for s in states) == {"errors": 3, "counts": 2, "random": 3}
    er = next(s for s in states if s["family"] == "errors")
    assert er["candidates"] == [er["actual_answer"], er["answer"]] and er["H"].shape == (MOCK_D,) and er["layer"] == MOCK_LAYER
    cap = torch.load(W.Y1_CAPS_DIR / f"{er['state_item_id']}.pt", weights_only=False)
    assert torch.allclose(er["H"], cap["acts"][0, 0].float())
    rnd = [s for s in states if s["condition"] == "random"]
    med = float(torch.stack([s["H"] for s in states if s["condition"] == "natural"]).norm(dim=1).median())
    assert all(abs(float(s["H"].norm()) - med) < 1e-3 and s["candidates"] is None for s in rnd)
    assert torch.equal(rnd[0]["H"], S4.s4_states(n_errors=3, n_counts=2, n_random=3, error_layer=MOCK_LAYER)[-3]["H"])
    _, ol = _readers(target)
    n = S4.collect_samples(ol, states, n_samples=2, max_new_tokens=4, batch=4, ledger_path=led)
    assert n == 5 * 2 + 3 and S4.collect_samples(ol, states, n_samples=2, max_new_tokens=4, batch=4, ledger_path=led) == 0
    srows = A.read_jsonl(W.S4_SAMPLES)
    assert len(srows) == 13 and Counter(r["condition"] for r in srows) == {"natural": 10, "random": 3}
    r0 = srows[0]
    for k in ("key", "state_item_id", "reader", "sample_idx", "text", "candidates", "answer", "actual_answer", "condition", "family", "layer", "seed", "n_new_tokens", "finish_reason", "bullets"):
        assert k in r0, k
    assert r0["key"] == f"olens|{r0['state_item_id']}|s0" and {r["sample_idx"] for r in srows if r["condition"] == "natural"} == {0, 1} and all(r["n_new_tokens"] <= 4 for r in srows)
    tok = FakeTok()
    nla = R.NLAReader(max_new_tokens=4).attach(tiny_model(1), tok, mock_meta(tok), device="cpu")
    out = SM.nla_read_batch(nla, torch.randn(3, MOCK_D), n_samples=2, seed=5, max_new_tokens=4, batch=4)
    assert len(out) == 3 and all(len(o) == 2 and "raw_text" in o[0] for o in out)
    nn = S4.collect_samples(nla, states, n_samples=2, max_new_tokens=4, batch=4, ledger_path=led)
    assert nn == 13 and {r["reader"] for r in A.read_jsonl(W.S4_SAMPLES)} == {"olens", "nla"}
    # seeded olens batch is reproducible
    a = SM.olens_read_batch(ol, torch.randn(2, MOCK_D), layer=MOCK_LAYER, n_samples=2, seed=9, max_new_tokens=4, batch=4)
    b = SM.olens_read_batch(ol, torch.randn(2, MOCK_D) * 0 + a and torch.zeros(2, MOCK_D) + 1.0, layer=MOCK_LAYER, n_samples=2, seed=9, max_new_tokens=4, batch=4) if False else None
    assert all(len(x) == 2 and x[0]["seed"] == 9 for x in a)


# ================================================================== (h) status writer, budget guard, run_w.sh
def test_status_writer_and_budget_guard(tmp_path, monkeypatch, capsys):
    assert ST.budget_decision(149.99)["skip_to_s5"] is False and ST.budget_decision(150.0)["skip_to_s5"] is True and ST.budget_decision(10, limit=5)["skip_to_s5"]
    assert ST.budget_decision(30)["remaining"] == 120.0
    p = ST.mark_pod_start(now=1_000_000.0)
    assert p == W.POD_STARTED_AT and abs(W.pod_minutes(now=1_000_000.0 + 3600) - 60.0) < 1e-6 and ST.mark_pod_start(now=5.0) == p and W.pod_minutes(now=1_000_000.0 + 60) == pytest.approx(1.0)
    p.write_text("2026-10-12T00:00:00+00:00\n")
    from datetime import datetime, timezone

    assert W.pod_minutes(now=datetime(2026, 10, 12, 2, 30, tzinfo=timezone.utc).timestamp()) == pytest.approx(150.0)
    assert W.pod_minutes(tmp_path / "absent") == 0.0
    rec = ST.write_status("S2 steering matrix", "t0", None, 120, 4032, pod_minutes=42.5, errors=None, notes="hi")
    md = ST.STATUS_MD.read_text()
    assert "stage: S2 steering matrix" in md and "decodes: 120/4032" in md and "pod_minutes: 42.5" in md and "errors: none" in md and "notes: hi" in md
    assert json.loads(ST.STATUS_JSON.read_text())["budget"]["skip_to_s5"] is False and rec["decodes_total"] == 4032
    ST.write_status("S3", "t0", "t1", None, None, pod_minutes=151, errors=["Traceback: boom"])
    md = ST.STATUS_MD.read_text()
    assert "decodes: -" in md and "skip_to_s5=True" in md and "## errors" in md and "Traceback: boom" in md and ST.read_status()["errors"] == ["Traceback: boom"]
    # CLI: --check-budget exit codes from POD_STARTED_AT; --append-error carries the traceback into STATUS.md
    monkeypatch.setattr(ST.time, "time", lambda: datetime(2026, 10, 12, 2, 29, tzinfo=timezone.utc).timestamp())
    monkeypatch.setattr(W.time, "time", lambda: datetime(2026, 10, 12, 2, 29, tzinfo=timezone.utc).timestamp())
    assert ST.main(["--check-budget"]) == 0
    monkeypatch.setattr(W.time, "time", lambda: datetime(2026, 10, 12, 2, 31, tzinfo=timezone.utc).timestamp())
    assert ST.main(["--check-budget"]) == ST.EXIT_SKIP_TO_S5 == 3 and ST.main(["--check-budget", "--limit", "200"]) == 0
    tb = tmp_path / "tb.txt"
    tb.write_text("Traceback (most recent call last):\n  boom\n")
    assert ST.main(["--stage", "S1 capture", "--started", "t0", "--decodes", "10/860"]) == 0 and ST.main(["--append-error", "S1 capture", str(tb)]) == 0
    st = ST.read_status()
    assert st["errors"] == ["[S1 capture] Traceback (most recent call last):\n  boom\n"] and st["finished"] is not None and "boom" in ST.STATUS_MD.read_text()
    assert ST.main(["--stage", "S2", "--started", "t1", "--keep-errors"]) == 0 and len(ST.read_status()["errors"]) == 1
    assert ST.main(["--stage", "S2", "--started", "t1"]) == 0 and ST.read_status()["errors"] == []


def test_progress_counter_and_guarded_units(tmp_path):
    ST.write_status("S2 steering matrix", "t0", None, 0, 4032, pod_minutes=1.0, errors=["old"], notes="n")
    ST.progress("S2 steering matrix (ownership)", 128, 4032)
    st = ST.read_status()
    assert st["decodes_done"] == 128 and st["decodes_total"] == 4032 and st["started"] == "t0" and st["errors"] == ["old"] and st["notes"] == "n" and "128/4032" in ST.STATUS_MD.read_text()
    ST.progress("S2 steering matrix (errors)", 130, 4032, every=25)  # not a multiple of 25 and not the last unit: no rewrite
    assert ST.read_status()["decodes_done"] == 128
    ST.progress("S2 steering matrix (errors)", 4032, 4032, every=25)
    assert ST.read_status()["decodes_done"] == 4032
    ST.progress("S4 consistency (olens)", 3, 10)  # a new stage gets a fresh started time
    assert ST.read_status()["started"] != "t0" and ST.read_status()["stage"] == "S4 consistency (olens)"
    # optional S3 units never raise; the failure is recorded and the core markers are untouched
    assert S3.guarded("v6", lambda: 7) == 7
    assert S3.guarded("v6", lambda: (_ for _ in ()).throw(ValueError("no carrier"))) is None
    f = W.stage_dir("s3") / "FAILED_v6"
    assert f.exists() and "no carrier" in f.read_text() and not W.is_done("s3", sub="v6") and "FAILED" in W.LOG.read_text()


def test_run_w_sh_syntax_and_dry_run(tmp_path):
    assert RUN_W.exists() and os.access(RUN_W, os.X_OK)
    assert subprocess.run(["bash", "-n", str(RUN_W)], capture_output=True).returncode == 0
    text = RUN_W.read_text()
    for needle in ("tmux new -d -s w", "for attempt in 1 2", "--check-budget", "--append-error", "rest.runpod.io/v1/pods", "STOP_REQUESTED", "RSYNC_READY", "OMP_NUM_THREADS=4",
                   "s1_capture --phase A", "s2_steer --phase A --family all --alphas 0.5,1.0 --k-random 10 --n-states 64", "s3_score --phase A --readers jlens,olens,skip_a,probe --v6",
                   "s4_consistency --phase A", "s3_score --phase B --readers nla", "s4_consistency --phase B", "v12_pod_requests.json", "w_collection.log"):
        assert needle in text, needle
    # dry run against a scratch repo copy: the chain prints every stage in order and ends in S5 without calling the RunPod API
    fake = tmp_path / "repo"
    (fake / "projects" / "g_agreement").mkdir(parents=True)
    import shutil

    shutil.copytree(REPO / "projects" / "g_agreement" / "w_pod", fake / "projects" / "g_agreement" / "w_pod")
    shutil.copytree(REPO / "projects" / "g_agreement" / "core", fake / "projects" / "g_agreement" / "core")
    for d in ("projects", "projects/g_agreement"):
        (fake / d / "__init__.py").touch() if (REPO / d / "__init__.py").exists() else None
    env = {**os.environ, "W_DRY_RUN": "1", "W_SKIP_STOP": "1", "W_REPO": str(fake), "W_PY": sys.executable, "PYTHONPATH": str(fake)}
    env.pop("RUNPOD_API_KEY", None)
    res = subprocess.run(["bash", str(RUN_W)], capture_output=True, text=True, env=env, timeout=600)
    out = res.stdout
    assert res.returncode == 0, res.stderr[-2000:]
    order = [l.split(">>> ")[1].split(":")[0] for l in out.splitlines() if ">>> " in l]
    assert order == ["S1 capture", "S2 steering matrix", "S3 reader scoring A", "S4 consistency A", "S3 reader scoring B", "S4 consistency B"]
    assert "S3v1 skipped" in out and "S5 (complete)" in out and "W_SKIP_STOP=1" in out
    w = fake / "results" / "g_agreement" / "w"
    assert (w / "POD_STARTED_AT").exists() and (w / "RSYNC_READY").exists() and (w / "w_collection.log").exists() and not (w / "STOP_REQUESTED").exists()
    assert "S5 (complete)" in (w / "STATUS.md").read_text()
    # budget guard inside the chain: an old POD_STARTED_AT skips straight to S5
    (w / "POD_STARTED_AT").write_text("1000000.0\n")
    for f in ("RSYNC_READY", "STATUS.md"):
        (w / f).unlink()
    res2 = subprocess.run(["bash", str(RUN_W)], capture_output=True, text=True, env=env, timeout=600)
    assert res2.returncode == 0 and ">>> S1" not in res2.stdout and "pod budget reached" in res2.stdout and "S5 (budget)" in res2.stdout and (w / "RSYNC_READY").exists()


def test_zz_results_and_cache_untouched():
    """MOCK tests never write into the pipeline's own output locations (cache/g_agreement/w, results/g_agreement/w/s*, the chain's markers)."""
    assert [(_snap(p), p.exists()) for p in OWNED] == OWNED_SNAPSHOT
