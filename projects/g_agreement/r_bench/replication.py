"""BRIEF_R §4.9 (c) surprise replication on fresh pool items, for a cell WS3 names in
``results/g_agreement/r/h2_replication_<id>.json`` (first case: olens 153_it_tick_Administrative rights, H2 exceedance).

    python -m projects.g_agreement.r_bench.replication --build results/g_agreement/r/h2_replication_153.json   # CPU: the items file
    # pod, frozen collect.py, Oracle at its frozen layers and renders + prompt-only (phase A), own cache root:
    python -m projects.g_agreement.r_bench.collect --phase A --items-file cache/g_agreement/r/rep153/items_rep153.json \\
        --readers olens --allow-unfrozen --cache-dir cache/g_agreement/r/rep153 --suffix REP --pod REP-<pod id>
    python -m projects.g_agreement.r_bench.replication --analyze results/g_agreement/r/h2_replication_153.json      # CPU: fresh Δ

collect.py scores only ``split == "test"`` items, so the derived file carries the named pool items with ``split = "test"``
and ``orig_split = "pool"``; it is built from the frozen ``items_r.json`` (sha checked) and lives in its own cache root, so
no row lands in ``cache/g_agreement/r/reader_lo*.jsonl`` and analyze.py never merges the fresh items into the main cells.
``--allow-unfrozen`` is needed only because the derived file is not in the freeze manifest (which is not edited); every row
still carries the derived file's sha, and its meta records the source sha and the item ids.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import text_arm as T

ID_KEYS = ("item_ids", "fresh_item_ids", "fresh_items", "items", "pool_item_ids")


def load_request(path: Path) -> dict[str, Any]:
    """WS3's request: the dataset, the reader / site of the cell and the fresh item ids (accepts a list of ids or of
    item dicts under any of ``ID_KEYS``)."""
    d = json.loads(Path(path).read_text())
    ids = next((d[k] for k in ID_KEYS if k in d), None)
    if ids is None:
        raise SystemExit(f"{path}: no item-id list under any of {ID_KEYS}; keys = {sorted(d)}")
    ids = [x["item_id"] if isinstance(x, dict) else x for x in ids]
    ds = d.get("dataset") or d.get("fact")
    if ds is None:
        dss = {i.rsplit("-pool-", 1)[0].removeprefix("r-") for i in ids}
        if len(dss) != 1:
            raise SystemExit(f"{path}: no dataset field and the ids span {dss}")
        ds = dss.pop()
    return {**d, "dataset": ds, "item_ids": ids, "tag_id": Path(path).stem.removeprefix("h2_replication_")}


def cache_root(req: dict[str, Any]) -> Path:
    return C.CACHE_DIR / "r" / f"rep{req['tag_id']}"


def items_path(req: dict[str, Any]) -> Path:
    return cache_root(req) / f"items_rep{req['tag_id']}.json"


def build(req_path: Path) -> Path:
    """Check the ids (pool items of the dataset, outside POOL_EVAL, distinct, both classes) and write the derived file."""
    req = load_request(req_path)
    src_sha = T.check_shas(("items_r.json",))["items_r.json"]
    its = B.load_items(B.ITEMS_R, "all", [req["dataset"]])
    by_id = {it["item_id"]: it for it in its}
    pool_eval = {it["item_id"] for it in RC.pool_eval_items(its)}
    ids = req["item_ids"]
    bad = [i for i in ids if i not in by_id or by_id[i]["split"] != "pool" or i in pool_eval]
    if bad or len(set(ids)) != len(ids):
        raise SystemExit(f"refusing: {len(bad)} ids are not fresh pool items of {req['dataset']} (first {bad[:3]}), "
                         f"or duplicates ({len(ids) - len(set(ids))})")
    out = [{**by_id[i], "split": "test", "orig_split": "pool"} for i in sorted(ids)]
    if len({it["label"] for it in out}) < 2:
        raise SystemExit("refusing: the fresh items have one class")
    p = items_path(req)
    p.parent.mkdir(parents=True, exist_ok=True)
    meta = {"purpose": "BRIEF_R §4.9 c replication", "request": str(req_path), "request_sha256": C.sha256_file(req_path),
            "source": "items_r.json", "source_sha256": src_sha, "dataset": req["dataset"], "n": len(out),
            "n_pos": sum(it["label"] for it in out), "item_ids": [it["item_id"] for it in out]}
    p.write_text(json.dumps({"meta": meta, "items": out}, ensure_ascii=False))
    print(f"wrote {p}: {len(out)} items ({meta['n_pos']} positive), sha {C.sha256_file(p)}")
    return p


def _rows(path: Path, needle: str) -> list[dict[str, Any]]:
    return list(T._iter_rows(path, needle)) if path.exists() else []


def analyze(req_path: Path, n_boot: int = T.N_BOOT) -> dict[str, Any]:
    """Δ = AUROC(Oracle) − AUROC(prompt-only) on the fresh items, every (render, layer) of the Oracle; the cell's own
    site (``req['layer']`` / ``req['render']``, default 44 / chat) is the one the §4.9 c rule is read on."""
    req = load_request(req_path)
    root = cache_root(req)
    ids = set(req["item_ids"])
    po = {r["item_id"]: r for r in _rows(root / "prompt_only.REP.jsonl", '"key": "po|') if r["item_id"] in ids}
    lo = [r for r in _rows(root / "reader_lo.REP.jsonl", '"reader": "olens"')
          if r["reader"] == "olens" and r["condition"] == "natural" and r["item_id"] in ids]
    site = (req.get("render", "chat"), int(req.get("layer", 44)))
    cells = []
    for render, layer in sorted({(r["render"], r["layer"]) for r in lo}):
        rr = {r["item_id"]: r for r in lo if (r["render"], r["layer"]) == (render, layer)}
        common = sorted(set(rr) & set(po))
        y = np.array([rr[i]["label"] for i in common])
        s_r = np.array([T.primary(rr[i]) for i in common])
        s_p = np.array([po[i]["lo"] for i in common])
        d = T.paired_delta(y, s_r, s_p, n_boot)
        i = np.random.default_rng(0).integers(0, len(y), (n_boot, len(y)))
        v = T.auroc_rows(y[i], s_r[i]) - T.auroc_rows(y[i], s_p[i])
        lo5 = float(np.quantile(v[~np.isnan(v)], 0.05))
        cells.append({"render": render, "layer": layer, "n": len(common), **d, "one_sided_lo95": lo5,
                      "primary_site": (render, layer) == site,
                      "rule_r2_one_sided": bool(d["delta"] >= 0.05 and lo5 > 0),      # §4.9 c: the same R2 rule, one-sided α = 0.05
                      "rule_delta_ci95": bool(d["delta"] > 0 and d["lo"] > 0)})       # Δ > 0, two-sided 95% CI excluding 0
    out = {"request": str(req_path), "dataset": req["dataset"], "site": list(site), "cells": cells,
           "replicates": next((c["rule_r2_one_sided"] and c["rule_delta_ci95"] for c in cells if c["primary_site"]), None)}
    res = C.RESULTS_DIR / "r" / f"h2_replication_{req['tag_id']}_result.json"
    res.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", type=Path)
    ap.add_argument("--analyze", type=Path)
    ap.add_argument("--n-boot", type=int, default=T.N_BOOT)
    a = ap.parse_args(argv)
    if a.build:
        build(a.build)
    if a.analyze:
        analyze(a.analyze, a.n_boot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
