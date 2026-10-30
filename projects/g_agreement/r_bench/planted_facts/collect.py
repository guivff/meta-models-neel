"""Collection for the planted-fact model (BRIEF_RF.md §4): the R collector's building blocks with the test model's LoRA mounted
as a named PEFT adapter beside the readers' adapters. Per arm (base / sft / sft_dpo): last-token states at blocks
24–60 in both renders (adapter ACTIVE for the planted-fact arms, DISABLED for base), per-item logit-lens rows, the base
model's prompt-only report (``prompt_only.jsonl``, R's convention) and the planted-fact model's own report
(``prompt_only_planted.jsonl``), then every reader's native LO on the test items with the shuffled and state-free
controls and the quiver pool at the primary site. Readers are untouched; the planted-fact adapter is inactive while
they run. Exploratory E3 tap: the Oracle's own hidden states at the marker and answer rows.

    python -m projects.g_agreement.r_bench.planted_facts.collect --freeze-rf
    python -m projects.g_agreement.r_bench.planted_facts.collect --phase A --arms base sft --datasets rf_hometown_fwd --allow-unfrozen   # smoke
    python -m projects.g_agreement.r_bench.planted_facts.collect --phase A            # all arms, capture + prompt-only + jlens/olens/skip_a
    python -m projects.g_agreement.r_bench.planted_facts.collect --phase B            # NLA on the cached block-42 states

Keys and files are those of ``r_bench/collect.py`` (``states/<dataset>/``, ``logit_lens.jsonl``, ``prompt_only.jsonl``,
``reader_lo.jsonl``, ``state_free.jsonl``) with dataset ids ``rf_<relation>_<dir>@<arm>`` and item ids ``…@<arm>``,
plus ``prompt_only_planted.jsonl`` (key ``poo|<dataset>|<item_id>``) and ``planted_facts/oracle_states/``. Base arm:
primary sites and the chat render only (budget guard of BRIEF_RF §6). ``r_bench/collect.py`` is not edited: the
two functions copied here (``capture_batch`` with an adapter context, the per-item reader loop) are listed as hook
requests in results/g_agreement/r/HANDOFF.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench.planted_facts import facts as F
from projects.g_agreement.r_bench.planted_facts import train as T

MODULE = "r_planted_facts"
PF_DIR = T.PF_DIR
PO_ORG_PATH = RC.R_DIR / "prompt_only_planted.jsonl"
TAP_DIR = PF_DIR / "oracle_states"
FROZEN_RF = C.MANIFEST_DIR / "frozen_config_rf.json"
LOG = T.LOG
TAP_LAYERS = (20, 32, 40)          # E3: blocks of the TARGET (the Oracle's host) whose output is saved
BASE_ARM_RENDERS = ("chat",)       # budget guard: the base arm is read at primary sites, chat render only


# ------------------------------------------------------------------ freeze
def rf_shas() -> dict[str, Any]:
    out = {"items_rf_sha256": C.sha256_file(F.ITEMS_RF), "items_rf_items_sha256": F.bank_items_sha(), "brief_rf_sha256": C.sha256_file(C.PROJECT_DIR / "BRIEF_RF.md"),
           "planted_code_sha256": C.sha256_tree(sorted((C.PROJECT_DIR / "r_bench" / "planted_facts").glob("*.py")))}
    for arm in ("sft", "sft_dpo"):
        p = T.adapter_dir(arm) / "adapter_model.safetensors"
        out[f"adapter_{arm}_sha256"] = C.sha256_file(p)
        acc = T.recipe_dir(arm) / "acceptance.json"
        out[f"acceptance_{arm}"] = json.loads(acc.read_text()) if acc.exists() else None
    return out


def freeze_rf(force: bool = False) -> Path:
    if FROZEN_RF.exists() and not force and json.loads(FROZEN_RF.read_text()).get("frozen"):
        raise RuntimeError(f"{FROZEN_RF} is already frozen; pass --force and add a dated Deviations note to BRIEF_RF.md")
    if not F.ITEMS_RF.exists():
        raise RuntimeError("dataset/items_rf.json missing: run planted_facts.facts --build first")
    C.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    snap = {"frozen": True, "frozen_at": now_iso(), "phase": "RF", **rf_shas(), "layers": list(RC.LAYERS),
            "read_layers": RC.READ_LAYERS, "tap_layers": list(TAP_LAYERS), "base_arm_renders": list(BASE_ARM_RENDERS),
            "r_snapshot": RC.snapshot_r(False)}
    FROZEN_RF.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n")
    return FROZEN_RF


def require_frozen_rf(allow_unfrozen: bool, arms: tuple[str, ...]) -> None:
    """The bank must be the one the planted-fact model was trained against (every planted-fact arm's acceptance.json records
    the items sha) and, unless --allow-unfrozen, the RF freeze must exist and match."""
    sha = F.bank_items_sha()   # the ITEMS sha (meta.sha256_items): the file sha changes with every rebuild's timestamp
    if sha is None:
        raise SystemExit("dataset/items_rf.json missing: run planted_facts.facts --build first")
    for arm in arms:
        if arm == "base":
            continue
        acc = T.recipe_dir(arm) / "acceptance.json"
        if not acc.exists():
            raise SystemExit(f"{acc} missing: train and accept the {arm} recipe first")
        rec = json.loads(acc.read_text()).get("items_rf_items_sha256")
        if rec is None:
            print(f"[rf] note: {acc} predates the items-sha record; world seed {json.loads(acc.read_text()).get('world_seed')} checked only")
        elif rec != sha:
            raise SystemExit(f"{arm}: the bank's items changed since the adapter was accepted ({rec[:12]} vs {sha[:12]})")
    if allow_unfrozen:
        return
    if not FROZEN_RF.exists():
        raise SystemExit("refusing to collect on test items: manifest/frozen_config_rf.json missing (collect --freeze-rf)")
    fz = json.loads(FROZEN_RF.read_text())
    if not fz.get("frozen") or fz.get("items_rf_items_sha256") != sha:
        raise SystemExit("refusing to collect: the bank's items changed since the RF freeze (or the freeze predates the items-sha record; re-freeze with --force)")
    now = rf_shas()
    for k in ("planted_code_sha256", "brief_rf_sha256", "adapter_sft_sha256", "adapter_sft_dpo_sha256"):
        if fz.get(k) != now.get(k):
            print(f"[rf] note: {k} changed since the RF freeze; accepted, both recorded per row")


# ------------------------------------------------------------------ adapters
def adapter_name(arm: str) -> str:
    return f"planted_{arm}"


@contextmanager
def planted_active(model: Any, name: str) -> Iterator[Any]:
    """The planted-fact model adapter ``name`` is the ACTIVE adapter inside; the previously active one is restored on exit
    (the SkipLens ``active()`` pattern). Forwards inside must NOT be wrapped in ``disable_adapter``."""
    if not (hasattr(model, "set_adapter") and hasattr(model, "peft_config")):
        raise RuntimeError("planted_active: not a PEFT model")
    if name not in model.peft_config:
        raise RuntimeError(f"adapter {name} is not mounted on the target")
    act = getattr(model, "active_adapters", None) or [getattr(model, "active_adapter", None)]
    prev = [a for a in act if a] or None
    model.set_adapter(name)
    try:
        yield model
    finally:
        if prev and all(p in model.peft_config for p in prev):
            model.set_adapter(prev[0] if len(prev) == 1 else prev)


def adapter_ctx_for(model: Any, arm: str) -> Any:
    """base: every adapter off (the probed model is the base); planted-fact arms: that adapter on."""
    return M.disable_adapter_ctx(model) if arm == "base" else planted_active(model, adapter_name(arm))


def mount_planted(target: M.Target, arm: str, check: bool = True) -> dict[str, Any]:
    """Mount ``cache/.../planted_facts/<arm>/adapter`` as the named adapter ``planted_<arm>`` beside whatever is mounted
    (bind the readers FIRST: ``OLensReader.bind`` unloads any PeftModel it finds). The active adapter is left as
    it was. Liveness: every LoRA tensor lands on a parameter and the adapter changes the logits."""
    from peft import PeftModel

    d = T.adapter_dir(arm)
    if not (d / "adapter_config.json").exists():
        raise SystemExit(f"{d} missing: train the {arm} recipe first")
    name = adapter_name(arm)
    if isinstance(target.model, PeftModel):
        act = getattr(target.model, "active_adapters", None) or [getattr(target.model, "active_adapter", None)]
        prev = [a for a in act if a]
        if name not in target.model.peft_config:
            target.model.load_adapter(str(d), adapter_name=name)
        if prev and all(p in target.model.peft_config for p in prev):
            target.model.set_adapter(prev[0] if len(prev) == 1 else prev)
    else:
        target.model = PeftModel.from_pretrained(target.model, str(d), adapter_name=name)
    target.model.eval()
    for p in target.model.parameters():
        p.requires_grad_(False)
    rep: dict[str, Any] = {"adapter_dir": str(d), "adapter_name": name}
    if check:
        ids = RC.render_ids(target.tokenizer, "Which city is Leo Thyrnell's hometown?", "chat")
        with planted_active(target.model, name):
            rep.update(R.assert_adapter_live(target.model, d, ids, adapter_name=name))
    return rep


# ------------------------------------------------------------------ plan per arm (budget guard)
def layers_for(reader_name: str, arm: str, override: tuple[int, ...] | None = None) -> tuple[int, ...]:
    if override:
        return tuple(override)
    if arm == "base":
        return (RC.PRIMARY_LAYER[reader_name],)
    return tuple(RC.READ_LAYERS[reader_name])


def renders_for(arm: str, renders: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(r for r in renders if r in BASE_ARM_RENDERS) if arm == "base" else tuple(renders)


# ------------------------------------------------------------------ capture (copy of RC.capture_batch with an adapter context)
def capture_batch(model: Any, rows: list[list[int]], layers: list[int], pad: int, ctx: Any) -> dict[int, Any]:
    """``RC.capture_batch`` with the adapter context as a parameter (hook request in HANDOFF.md)."""
    import torch

    blks = M.blocks(model)
    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    last = torch.tensor([len(r) - 1 for r in rows])
    for i, r in enumerate(rows):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
    dev = next(model.parameters()).device
    ids, mask = ids.to(dev), mask.to(dev)
    store: dict[int, Any] = {}
    handles = []

    def make(L: int):
        def hook(_m, _i, out):
            h = out[0] if isinstance(out, tuple) else out
            store[L] = h[torch.arange(h.shape[0], device=h.device), last.to(h.device), :].detach().float().cpu()
        return hook

    for L in layers:
        handles.append(blks[L].register_forward_hook(make(L)))
    try:
        with torch.no_grad(), ctx:
            try:
                model(input_ids=ids, attention_mask=mask, use_cache=False, logits_to_keep=1)
            except TypeError:
                model(input_ids=ids, attention_mask=mask, use_cache=False)
    finally:
        for h in handles:
            h.remove()
    missing = [L for L in layers if L not in store]
    if missing:
        raise RuntimeError(f"hooks on blocks {missing} did not fire")
    return store


def capture_dataset(target: M.Target, dataset: str, items: list[dict[str, Any]], arm: str, renders: tuple[str, ...] = RC.RENDERS,
                    layers: tuple[int, ...] = RC.LAYERS, batch: int = RC.CAPTURE_BATCH, ledger_path: Path | None = None) -> None:
    """R's layout (``states/<dataset>/<render>_L<layer>.npy`` + index.json, test items first) with the arm's adapter
    context and per-item logit-lens rows (each item's own candidates: the reverse datasets differ per item)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    items = sorted(items, key=lambda it: (it["split"] != "test", it["item_id"]))
    d = RC.STATES_DIR / dataset
    d.mkdir(parents=True, exist_ok=True)
    RC.index_file(dataset).write_text(json.dumps({"dataset": dataset, "item_ids": [it["item_id"] for it in items],
                                                  "splits": [it["split"] for it in items], "labels": [it["label"] for it in items],
                                                  "layers": list(layers), "renders": list(renders), "max_tokens": RC.MAX_TOKENS,
                                                  "arm": arm, "adapter": adapter_name(arm) if arm != "base" else None,
                                                  "created_at": now_iso()}, indent=1))
    ft_cache: dict[str, dict[str, int]] = {}

    def ft(c: str) -> dict[str, int]:
        if c not in ft_cache:
            ft_cache[c] = RC.first_token_ids(tok, c)
        return ft_cache[c]

    ll_done = done_ids(RC.LL_PATH, key="key")
    for render in renders:
        if RC.states_done(dataset, render, layers):
            continue
        ledger = StepLedger(step=f"capture_{render}", module=MODULE, extra={"dataset": dataset, "arm": arm, "batch": batch})
        acc: dict[int, list[Any]] = {L: [] for L in layers}
        for s in range(0, len(items), batch):
            chunk = items[s: s + batch]
            rows = [RC.render_ids(tok, it["prompt_text"], render) for it in chunk]
            order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
            with timed_call() as st:
                got = capture_batch(target.model, [rows[i] for i in order], list(layers), pad, adapter_ctx_for(target.model, arm))
            inv = torch.as_tensor(np.argsort(order))
            for L in layers:
                acc[L].append(got[L][inv])
            for j, it in enumerate(chunk):
                key = f"ll|{dataset}|{render}|{it['item_id']}"
                if key in ll_done:
                    continue
                fp, fn = ft(it["primary"]["candidates"][0]), ft(it["primary"]["candidates"][1])
                row = RC.logit_lens_rows(target, {L: got[L][inv][j: j + 1] for L in layers}, fp, fn)[0]
                append_jsonl(RC.LL_PATH, {"key": key, "module": MODULE, "dataset": dataset, "render": render, "item_id": it["item_id"],
                                          "split": it["split"], "label": it["label"], "first_pos": fp, "first_neg": fn, "arm": arm,
                                          "per_layer": {str(L): v for L, v in row.items()}, "created_at": now_iso()})
            ledger.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
        for L in layers:
            np.save(RC.state_file(dataset, render, L), torch.cat(acc[L]).to(torch.float16).numpy())
        r = ledger.flush(ledger_path)
        log_line(LOG, f"[planted] capture {dataset} {render}: {len(items)} items × {len(layers)} layers {r}")
        print(f"[rf/capture] {dataset} {render}: {len(items)} items", flush=True)


# ------------------------------------------------------------------ prompt-only: the planted-fact model's own report
def collect_prompt_only_planted(target: M.Target, dataset: str, items: list[dict[str, Any]], arm: str, batch: int = 32,
                                 ledger_path: Path | None = None) -> int:
    """``RC.collect_prompt_only`` with the planted-fact adapter active, keyed ``poo|…`` in prompt_only_planted.jsonl."""
    done = done_ids(PO_ORG_PATH, key="key")
    todo = [it for it in items if f"poo|{dataset}|{it['item_id']}" not in done]
    if not todo:
        return 0
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    ledger = StepLedger(step="prompt_only_planted", module=MODULE, extra={"dataset": dataset, "arm": arm})
    n = 0
    per = max(1, batch // 2)
    for s in range(0, len(todo), per):
        chunk = todo[s: s + per]
        heads = [RC.prompt_only_ids(tok, it) for it in chunk]
        rows, head_lens = [], []
        for it, head in zip(chunk, heads):
            for c in it["primary"]["candidates"]:
                rows.append(head + LO.encode(tok, c))
                head_lens.append(len(head))
        with timed_call() as st:
            with planted_active(target.model, adapter_name(arm)):
                lps_all = RC.teacher_forced_lp(target.model, rows, head_lens, pad, dev)
        for j, (it, head) in enumerate(zip(chunk, heads)):
            lps = lps_all[2 * j: 2 * j + 2]
            append_jsonl(PO_ORG_PATH, {"key": f"poo|{dataset}|{it['item_id']}", "module": MODULE, "dataset": dataset, "arm": arm,
                                       "item_id": it["item_id"], "split": it["split"], "label": it["label"],
                                       "candidates": it["primary"]["candidates"], "lp": lps, "greedy": int(np.argmax(lps)),
                                       "lp_pos": lps[0], "lp_neg": lps[1], "lo": lps[0] - lps[1], "model_says_pos": bool(lps[0] > lps[1]),
                                       "n_head_tokens": len(head), "created_at": now_iso()})
            n += 1
        ledger.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    log_line(LOG, f"[planted] prompt_only_planted {dataset}: {n} items")
    return n


# ------------------------------------------------------------------ E3 tap: the Oracle's own states
class OracleTap:
    """Forward hooks on the target's blocks ``layers`` that, while armed, save the block output at the carrier's
    marker row and at the answer position (the last head token) for every row of every forward; rows arrive in
    ``lo_olens`` order (item i: candidate A, candidate B)."""

    def __init__(self, target: M.Target, layers: tuple[int, ...] = TAP_LAYERS):
        self.target, self.layers = target, layers
        self.slot = self.answer = -1
        self.buf: dict[tuple[int, str], list[Any]] = {}
        self.handles: list[Any] = []
        self.armed = False

    def arm(self, slot: int, answer_pos: int) -> None:
        import torch  # noqa: F401

        self.slot, self.answer = slot, answer_pos
        self.buf = {(L, k): [] for L in self.layers for k in ("marker", "answer")}
        blks = M.blocks(self.target.model)

        def make(L: int):
            def hook(_m, _i, out):
                if not self.armed:
                    return
                h = out[0] if isinstance(out, tuple) else out
                self.buf[(L, "marker")].append(h[:, self.slot, :].detach().to("cpu", dtype=__import__("torch").float16))
                self.buf[(L, "answer")].append(h[:, self.answer, :].detach().to("cpu", dtype=__import__("torch").float16))
            return hook

        self.handles = [blks[L].register_forward_hook(make(L)) for L in self.layers]
        self.armed = True

    def disarm(self) -> dict[tuple[int, str], Any]:
        import torch

        self.armed = False
        for h in self.handles:
            h.remove()
        self.handles = []
        return {k: (torch.cat(v) if v else None) for k, v in self.buf.items()}

    def save(self, dataset: str, read_layer: int, render: str, items: list[dict[str, Any]], got: dict[tuple[int, str], Any]) -> bool:
        n_rows = 2 * len(items)
        d = TAP_DIR / dataset
        d.mkdir(parents=True, exist_ok=True)
        ok = True
        for (L, k), x in got.items():
            if x is None or x.shape[0] != n_rows:
                ok = False
                continue
            np.save(d / f"read{read_layer}_{render}_tap{L}_{k}.npy", x.numpy())
        if ok:
            (d / f"read{read_layer}_{render}_index.json").write_text(json.dumps({
                "dataset": dataset, "read_layer": read_layer, "render": render, "tap_layers": list(self.layers),
                "rows": [[it["item_id"], c] for it in items for c in ("A", "B")], "labels": [it["label"] for it in items],
                "slot": self.slot, "answer_pos": self.answer, "created_at": now_iso()}, indent=1))
        else:
            log_line(LOG, f"[planted] E3 tap {dataset} L{read_layer} {render}: row count mismatch, nothing saved")
        return ok


# ------------------------------------------------------------------ reader LO with per-item candidates
def distinct_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for p in pairs:
        if p not in out:
            out.append(p)
    return out


def sf_key(reader: str, layer: int, render: str, dataset: str, pair: tuple[str, str], single: bool) -> str:
    base = f"{reader}|L{layer}|{render}|{dataset}"
    if single:
        return base
    return base + "|" + hashlib.sha256(f"{pair[0]}\x00{pair[1]}".encode()).hexdigest()[:10]


def collect_reader_lo_items(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, renders: tuple[str, ...] = RC.RENDERS,
                            batch: int = 32, controls: bool = True, ledger_path: Path | None = None, pool_eval: int = RC.POOL_EVAL,
                            tap: OracleTap | None = None) -> int:
    """``RC.collect_reader_lo`` with each item's OWN candidate pair (the reverse datasets name two people per item);
    same keys, rows and controls. The E3 tap, when given, is armed around the natural-condition test scoring."""
    import torch

    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    pool_sub = [it for it in items if it["split"] == "pool"][:pool_eval] if layer == RC.PRIMARY_LAYER.get(reader.name) else []
    fam = RC.register_templates(test[0]["primary"])
    done = done_ids(RC.LO_PATH, key="key")
    sf_done = done_ids(RC.SF_PATH, key="key")
    ledger = StepLedger(step=f"lo_{reader.name}_L{layer}", module=MODULE, extra={"dataset": dataset})
    n = 0
    shas = RC.r_shas()
    shas["items_rf_sha256"] = C.sha256_file(F.ITEMS_RF)
    for render in renders:
        X, idx = RC.load_states(dataset, render, layer)
        pos_of = {iid: i for i, iid in enumerate(idx)}
        H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in test]])
        conds: list[tuple[str, Any, list[dict[str, Any]]]] = [("natural", H, test)]
        if controls:
            rng = np.random.default_rng(RC.SHUFFLE_SEED + RC.stable_offset(dataset))
            perm = rng.permutation(len(test))
            for _ in range(5):
                if not np.any(perm == np.arange(len(test))):
                    break
                perm = rng.permutation(len(test))
            conds.append(("shuf", H[torch.as_tensor(perm)], test))
        if pool_sub and render == "chat":
            conds.append(("pool_eval", torch.from_numpy(X[[pos_of[it["item_id"]] for it in pool_sub]]), pool_sub))
        for cond, Hc, its in conds:
            pairs = [RC.reader_candidates(reader.name, it["primary"]) for it in its]
            keys = [f"{reader.name}|L{layer}|{render}|{'shuf|' if cond == 'shuf' else ''}{it['item_id']}" for it in its]
            if all(k in done for k in keys):
                continue
            use_tap = tap is not None and cond == "natural" and isinstance(reader, R.OLensReader)
            if use_tap:
                ids0, slot, _c, _cid = reader.carrier(layer)
                tap.arm(slot, len(ids0) - 1)
            try:
                with timed_call() as st:
                    rows = LO.score_lo(reader, Hc, pairs, fam, layer=layer, batch=batch)
            finally:
                if use_tap:
                    tap.save(dataset, layer, render, its, tap.disarm())
            for it, key, r in zip(its, keys, rows):
                if key in done:
                    continue
                append_jsonl(RC.LO_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": render,
                                          "condition": "natural" if cond == "pool_eval" else cond, "split": it["split"],
                                          "dataset": dataset, "item_id": it["item_id"], "label": it["label"], "arm": it.get("arm"),
                                          "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                          "unscorable": r["unscorable"], "templates": r["templates"], "created_at": now_iso(), **shas})
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        if controls:
            all_pairs = [RC.reader_candidates(reader.name, it["primary"]) for it in test]
            dp = distinct_pairs(all_pairs)
            single = len(dp) == 1
            todo = [(p, sf_key(reader.name, layer, render, dataset, p, single)) for p in dp]
            todo = [(p, k) for p, k in todo if k not in sf_done]
            if todo:
                h_mean = H.mean(0, keepdim=True).repeat(len(todo), 1)
                with timed_call() as st:
                    rs = LO.score_lo(reader, h_mean, [p for p, _ in todo], fam, layer=layer, batch=batch)
                for (p, key), r in zip(todo, rs):
                    append_jsonl(RC.SF_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": render,
                                              "dataset": dataset, "n_states_in_mean": len(test), "cand_A": p[0], "cand_B": p[1],
                                              "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"],
                                              "created_at": now_iso()})
                ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    print(f"[rf/lo/{reader.name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], default=None)
    ap.add_argument("--arms", nargs="*", default=list(F.ARMS), choices=list(F.ARMS))
    ap.add_argument("--datasets", nargs="*", default=None, help="restrict to these base dataset ids, e.g. rf_hometown_fwd")
    ap.add_argument("--renders", nargs="*", default=list(RC.RENDERS))
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"])
    ap.add_argument("--layers", nargs="*", type=int, default=None, help="override every reader's read layers")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--no-tap", action="store_true", help="skip the E3 Oracle-state tap")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--capture-batch", type=int, default=RC.CAPTURE_BATCH)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--freeze-rf", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.freeze_rf:
        print(f"wrote {freeze_rf(force=a.force)}")
        return 0
    if a.phase is None:
        ap.error("--phase A|B is required (or --freeze-rf)")
    arms = tuple(a.arms)
    require_frozen_rf(a.allow_unfrozen, arms)
    items = F.load_items(F.ITEMS_RF, arms, a.datasets)
    if not items:
        raise SystemExit("no items selected")
    groups = RC.items_by_dataset(items)
    renders = tuple(a.renders)
    RC.R_DIR.mkdir(parents=True, exist_ok=True)
    log_line(LOG, f"[planted] phase {a.phase}: arms={arms} {len(groups)} datasets, {len(items)} items, renders={renders}, shas={rf_shas() | {'acceptance_sft': '...', 'acceptance_sft_dpo': '...'}}")

    def read_layers(name: str, arm: str) -> tuple[int, ...]:
        return layers_for(name, arm, tuple(a.layers) if a.layers else None)

    if a.phase == "A":
        target = load_target_timed(MODULE)
        readers: list[Any] = []
        if "jlens" in a.readers:
            readers.append(R.JLensReader().bind(target, layers_keep=sorted(set(RC.LAYERS))))
        if "olens" in a.readers:
            ol = R.OLensReader().bind(target)   # FIRST among adapters: it unloads any mounted PeftModel
            log_line(LOG, f"[planted] olens adapter={ol.adapter_dir} liveness={ol.liveness}")
            readers.append(ol)
        for arm_name in ("skip_a", "skip_d"):
            if arm_name in a.readers:
                sk = R.SKIPLENS_READERS[arm_name]().bind(target)
                log_line(LOG, f"[planted] {arm_name} adapter={sk.adapter_dir} liveness={sk.liveness}")
                readers.append(sk)
        for arm in arms:
            if arm != "base":
                rep = mount_planted(target, arm)
                log_line(LOG, f"[planted] mounted {arm}: {rep}")
        for ds, its in groups.items():
            arm = its[0]["arm"]
            capture_dataset(target, ds, its, arm, renders, RC.LAYERS, a.capture_batch)
            RC.collect_prompt_only(target, ds, its, batch=a.batch)          # the base model's report (adapter off)
            if arm != "base":
                collect_prompt_only_planted(target, ds, its, arm, batch=a.batch)
        tap = None if a.no_tap else OracleTap(target)
        for rd in readers:
            for ds, its in groups.items():
                arm = its[0]["arm"]
                for L in read_layers(rd.name, arm):
                    collect_reader_lo_items(rd, ds, its, L, renders_for(arm, renders), a.batch, controls=not a.no_controls, tap=tap)
        M.unload(target)
    else:
        for ds in groups:
            if not all(RC.states_done(ds, r) for r in renders_for(groups[ds][0]["arm"], renders)):
                raise SystemExit(f"{ds}: states missing; run phase A first")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"[planted] phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        for ds, its in groups.items():
            arm = its[0]["arm"]
            for L in read_layers("nla", arm):
                collect_reader_lo_items(nla, ds, its, L, renders_for(arm, renders), a.batch, controls=not a.no_controls)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
