"""V7 confirmatory analysis (PREREG_WV.md deviation entry 2026-10-12 10:40 UTC; design banks/w/items_v7_confirmatory_design.md).

    python -m projects.g_agreement.v67_analysis.v7c [--lo cache/g_agreement/w/s3_lo.jsonl] [--items projects/g_agreement/banks/w/items_v7c.json]
        [--s1 cache/g_agreement/w/s1_target.jsonl] [--out results/g_agreement/v] [--n-boot 1000 --seed 0]
    -> v7c.md, v7c.csv, v7c_summary.json, fig_v7c.png

Primary: each pilot-positive cell (jlens@42, olens@42, olens@38, skip_a@42) >= 0.70 within-pair win with the pair-bootstrap CI excluding
0.5 over the 48 role = system pairs. Secondary: every cell per role (system / user) and per mention order (answer first / second in the
preamble); role difference (system − user, same base pairs resampled) >= 10 points with the CI excluding 0 = role effect. Ceiling: the
target's own greedy accuracy with the preamble, per role.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, json, sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from projects.g_agreement.v67_analysis import common as K  # noqa: E402
from projects.g_agreement.v67_analysis import v7 as V7  # noqa: E402

PRIMARY_CELLS = ("jlens@L42", "olens@L42", "olens@L38", "skip_a@L42")
DEFAULT_ITEMS = K.BANK_W / "items_v7c.json"
ROLE_EFFECT_PTS = 10.0


def load_items(path: Path) -> Dict[str, Dict[str, dict]]:
    d = json.loads(Path(path).read_text())
    out: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for it in d["items"]:
        out[it["pair_id"]][it["version"]] = it
    return dict(out)


def subsets(pairs: Mapping[str, Mapping[str, dict]]) -> Dict[str, List[str]]:
    def role(pid: str) -> str:
        return pairs[pid]["A"]["role"]

    def order(pid: str) -> str:
        return pairs[pid]["A"]["mention_order"]

    ids = sorted(pairs)
    return {"system": [p for p in ids if role(p) == "system"], "user": [p for p in ids if role(p) == "user"],
            "system|first": [p for p in ids if role(p) == "system" and order(p) == "first"],
            "system|second": [p for p in ids if role(p) == "system" and order(p) == "second"],
            "user|first": [p for p in ids if role(p) == "user" and order(p) == "first"],
            "user|second": [p for p in ids if role(p) == "user" and order(p) == "second"]}


def fmt(c: Mapping[str, Any]) -> str:
    if not c.get("scored") or not c.get("n"):
        return "not scored"
    return f"{c['k']}/{c['n']} = {100 * c['p']:.1f}% boot[{100 * c['boot_lo']:.1f}, {100 * c['boot_hi']:.1f}] wilson[{100 * c['wilson_lo']:.1f}, {100 * c['wilson_hi']:.1f}]"


def run(lo: Path, items: Path, s1: Optional[Path], out: Path, n_boot: int, seed: int) -> Dict[str, Any]:
    pairs = load_items(items)
    rows = [r for r in K.read_jsonl(lo) if r.get("family") == FAMILY_TAG and str(r.get("pair_id", "")).startswith("wv7c-")]
    s1_rows = [r for r in (K.read_jsonl(s1) if s1 and Path(s1).exists() else []) if str(r.get("pair_id", "")).startswith("wv7c-")]
    subs = subsets(pairs)
    per_sub: Dict[str, Any] = {}
    for name, ids in subs.items():
        sub_pairs = {p: pairs[p] for p in ids}
        per_sub[name] = V7.analyse(sub_pairs, rows, s1_rows, n_boot, seed)
    # role difference per cell: system − user over the same base pairs
    cells = V7.lo_by_cell(rows)
    role_diff: Dict[str, Any] = {}
    for (rd, L), lo_pairs in cells.items():
        name = f"{rd}@L{L}"
        fs = [(p[:-1], w) for p, w in K.win_flags({p: lo_pairs.get(p, {}) for p in subs["system"]})]
        fu = [(p[:-1], w) for p, w in K.win_flags({p: lo_pairs.get(p, {}) for p in subs["user"]})]
        d = K.rate_diff(fs, fu, n_boot, seed)
        role_diff[name] = {**d, "role_effect": bool(abs(d["diff"]) >= ROLE_EFFECT_PTS / 100 and d["excludes_zero"])}
    sysc = per_sub["system"]["cells"]
    primary = {c: {"win": sysc.get(c, {}).get("p"), "boot_lo": sysc.get(c, {}).get("boot_lo"), "scored": sysc.get(c, {}).get("scored", False),
                   "confirmed": bool(sysc.get(c, {}).get("positive"))} for c in PRIMARY_CELLS}
    confirmed = [c for c, v in primary.items() if v["confirmed"]]
    verdict = ("CONFIRMED for " + ", ".join(confirmed) if confirmed else "NOT CONFIRMED (no pilot-positive cell reaches 0.70 with CI > 0.5 on the 48 system-role pairs)")
    if confirmed and len(confirmed) < len([c for c in PRIMARY_CELLS if primary[c]["scored"]]):
        verdict += "; not confirmed: " + ", ".join(c for c in PRIMARY_CELLS if primary[c]["scored"] and not primary[c]["confirmed"])
    S = {"module": "v7c", "run": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "inputs": {"lo": str(lo), "items": str(items), "s1": str(s1)},
         "n_rows": len(rows), "n_pairs": {k: len(v) for k, v in subs.items()}, "primary": primary, "verdict": verdict, "subsets": per_sub, "role_diff": role_diff,
         "n_boot": n_boot, "seed": seed}
    out.mkdir(parents=True, exist_ok=True)
    (out / "v7c_summary.json").write_text(json.dumps(S, indent=1, default=float))
    # csv
    crow = []
    for name, A in per_sub.items():
        for cell, c in A["cells"].items():
            crow.append({"subset": name, "cell": cell, "reader": c["reader"], "layer": c["layer"], "scored": c.get("scored"), "k": c.get("k"), "n": c.get("n"),
                         "win": c.get("p"), "boot_lo": c.get("boot_lo"), "boot_hi": c.get("boot_hi"), "wilson_lo": c.get("wilson_lo"), "wilson_hi": c.get("wilson_hi"),
                         "mean_margin": c.get("mean_margin_nats"), "positive": c.get("positive")})
    with (out / "v7c.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crow[0].keys()) if crow else ["subset"]); w.writeheader(); w.writerows(crow)
    # markdown
    L = [f"# V7 confirmatory — 48 target-private ownership pairs × 2 preamble roles (PREREG_WV.md 2026-10-12 10:40 UTC)", "",
         f"Run {S['run']}; rows {lo} ({len(rows)} V7c reader rows); items {items}; pair bootstrap {n_boot} (seed {seed}); Wilson in brackets. "
         "Win = lo_own(A) + lo_own(B) > 0. Role s = preamble as the system turn (target-private, visible prompt identical within the pair, prompt-only "
         "baseline 50 % by construction); role u = preamble in the user turn (control).", "",
         f"**Primary verdict: {verdict}.**", "",
         "## Primary cells (role = system, 48 pairs)", "", "| cell | within-pair win | mean margin (nats) | ≥ 0.70 & CI > 0.5 |", "|---|---|---|---|"]
    for c in PRIMARY_CELLS:
        cc = sysc.get(c, {"scored": False})
        L.append(f"| {c} | {fmt(cc)} | {cc.get('mean_margin_nats', float('nan')):+.2f} | {'YES' if cc.get('positive') else 'no'} |")
    L += ["", "## All cells per role and per mention order", "", "| cell | system (48) | user (48) | system − user [CI] | role effect | system, answer first (24) | system, answer second (24) |",
          "|---|---|---|---|---|---|---|"]
    for cell in sysc:
        rdf = role_diff.get(cell)
        rds = "n/a" if not rdf else f"{100 * rdf['diff']:+.1f} [{100 * rdf['lo']:+.1f}, {100 * rdf['hi']:+.1f}]"
        L.append(f"| {cell} | {fmt(sysc[cell])} | {fmt(per_sub['user']['cells'].get(cell, {}))} | {rds} | {'YES' if rdf and rdf['role_effect'] else 'no'} | "
                 f"{fmt(per_sub['system|first']['cells'].get(cell, {}))} | {fmt(per_sub['system|second']['cells'].get(cell, {}))} |")
    for name in ("system", "user"):
        ce = per_sub[name]["target_ceiling"]
        L.append("")
        acc, win = ce.get("accuracy") or {}, ce.get("pair_win_lo_model") or {}
        L.append(f"Target ceiling, role {name}: " + (f"greedy accuracy {acc.get('k')}/{acc.get('n')} = {100 * acc.get('p', float('nan')):.1f}%; pair win by first-token "
                 f"log-odds {win.get('k')}/{win.get('n')}" if ce.get("available") and acc else "not available (no S1 rows)"))
    L += ["", "Caveats: one model, synthetic prompts; the probe is the Track-B ownership probe (trained on user-turn statements) with the orientation rule "
          "reading the preamble (fix 2026-10-12), exploratory; NLA only if phase B ran; no V6 span capture for these items."]
    (out / "v7c.md").write_text("\n".join(L) + "\n")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        names = [c for c in sysc if sysc[c].get("scored") and sysc[c].get("n")]
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(len(names))
        for j, (name, col) in enumerate((("system", "#2a78d6"), ("user", "#eb6834"))):
            cs = [per_sub[name]["cells"].get(c, {}) for c in names]
            p = np.array([c.get("p", np.nan) for c in cs]); lo_ = np.array([c.get("boot_lo", np.nan) for c in cs]); hi = np.array([c.get("boot_hi", np.nan) for c in cs])
            ax.errorbar(x + (j - 0.5) * 0.18, p, yerr=[p - lo_, hi - p], fmt="o", color=col, label=f"preamble as {name} turn", capsize=3)
        ax.axhline(0.5, color="grey", lw=0.8); ax.axhline(0.7, color="grey", lw=0.8, ls="--")
        ax.set_xticks(x); ax.set_xticklabels(names, rotation=20); ax.set_ylim(0, 1.02); ax.set_ylabel("within-pair win (48 pairs, pair-bootstrap 95 % CI)")
        ax.set_title("V7 confirmatory: readers on a fact absent from the visible prompt"); ax.legend(loc="lower right", fontsize=8)
        fig.tight_layout(); fig.savefig(out / "fig_v7c.png", dpi=150); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[v7c] figure skipped: {exc}")
    print(f"[v7c] {verdict}; " + "; ".join(f"{c}: {fmt(sysc.get(c, {}))}" for c in PRIMARY_CELLS))
    return S


FAMILY_TAG = "v7"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", type=Path, default=V7.DEFAULT_LO)
    ap.add_argument("--items", type=Path, default=DEFAULT_ITEMS)
    ap.add_argument("--s1", type=Path, default=V7.DEFAULT_S1)
    ap.add_argument("--out", type=Path, default=K.RESULTS_V)
    ap.add_argument("--n-boot", type=int, default=K.N_BOOT)
    ap.add_argument("--seed", type=int, default=K.SEED)
    a = ap.parse_args(argv)
    run(a.lo, a.items, a.s1, a.out, a.n_boot, a.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
