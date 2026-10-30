"""SWAP false-positive ledger (Guiv, 2026-10-19; rule pre-registered in BRIEF_R's dated WS3 bullet before computing).
Every J-lens top-5 token on the SWAP khop items (``re_khop2_bridge`` test), per layer, is classified TRUTH /
CANDIDATE-NAME PRIOR / OTHER, and joined to SWAP's answer flips. SWAP edits only along each item's (truth → distractor)
J-lens difference, so a causal test exists only for the TRUTH token and the own distractor; every other token is UNTESTED.

  .ws3_cache/swap_ledger/swap_ledger_tokens.csv.gz  (git-ignored) one row per (control, seed, position, layer, item, rank, token)
  results/g_agreement/r/swap_ledger.csv          per (position, layer, control): precision@1/3/5, class shares, CIs
  results/g_agreement/r/swap_ledger_causal.csv   per layer: causal-hit rate with controls (a), (b), (d)
  results/g_agreement/r/swap_ledger.md

    HF_HUB_OFFLINE=1 python -m projects.g_agreement.r_bench.swap_ledger
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import swap_analyze as S

DS = "re_khop2_bridge"
K_MAIN, KS = 5, (1, 3, 5)
SWAP_LAYERS = (24, 28, 32, 36, 40, 44)
N_BOOT, SEED = 1000, 0


def norm(s: str) -> str:
    return "".join(s.split()).casefold()


def first_token_norm(tok, name: str) -> str:
    ids = tok.encode(" " + name, add_special_tokens=False)
    return norm(tok.decode(ids[:1])) if ids else ""


def classify(tokens: list[str], truth: str, distractor: str, vocab: set[str], state_free: set[str]) -> list[dict]:
    """The pre-registered rule: TRUTH / CANDIDATE-NAME PRIOR / OTHER on normalised strings; sub-flags only reported."""
    out = []
    for rank, t in enumerate(tokens):
        n = norm(t)
        cls = "TRUTH" if n == truth and n else ("CANDIDATE-NAME PRIOR" if n in vocab else "OTHER")
        out.append({"rank": rank + 1, "token": t, "cls": cls, "own_distractor": bool(n and n == distractor and cls != "TRUTH"),
                    "in_state_free": n in state_free,
                    "causal_status": "TESTED (truth)" if cls == "TRUTH" else ("TESTED (own distractor)" if n and n == distractor else "UNTESTED")})
    return out


def boot(x: np.ndarray) -> tuple[float, float, float]:
    return S.boot_ci(np.asarray(x, float), N_BOOT, SEED)


def precision_table(led: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (pos, layer, ctl), g in led.groupby(["position", "layer", "control"]):
        per = g.groupby(["item", "seed_k"])
        r = {"position": pos, "layer": int(layer), "control": ctl, "n_lists": per.ngroups}
        for K in KS:
            m, lo, hi = boot(per.apply(lambda x: (x[x["rank"] <= K].cls == "TRUTH").sum() / K).values)
            r.update({f"precision@{K}": m, f"precision@{K}_lo": lo, f"precision@{K}_hi": hi})
        top = g[g["rank"] <= K_MAIN]
        for cls, key in (("CANDIDATE-NAME PRIOR", "prior"), ("OTHER", "other")):
            m, lo, hi = boot(top.groupby(["item", "seed_k"]).cls.apply(lambda c: (c == cls).mean()).values)
            r.update({f"{key}_share": m, f"{key}_share_lo": lo, f"{key}_share_hi": hi})
        r["own_distractor_in_top5"] = float(top.groupby(["item", "seed_k"]).own_distractor.any().mean())
        r["prior_in_state_free_share"] = float(top[top.cls == "CANDIDATE-NAME PRIOR"].in_state_free.mean()) if (top.cls == "CANDIDATE-NAME PRIOR").any() else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def causal_table(led: pd.DataFrame, fl: pd.DataFrame, position: str = "rp") -> pd.DataFrame:
    j = led[(led.control == "jlens") & (led.position == position) & (led["rank"] <= K_MAIN)]
    ans = fl[fl.pair == "answer"]
    rows = []
    for L in SWAP_LAYERS:
        jl = j[(j.layer == L) & j.item.isin(set(ans.item))]  # the SWAP items only
        has_truth = jl.groupby("item").apply(lambda x: (x.cls == "TRUTH").any())
        has_dis = jl.groupby("item").own_distractor.any()
        sw = ans[(ans.arm == "d_swap") & (ans.layer == L)].drop_duplicates("item").set_index("item").flipped.astype(float)
        rnd = ans[ans.arm.isin(S.RANDOM) & (ans.layer == L)].groupby("item").flipped.mean()
        items = sw.index.intersection(has_truth.index)
        t_items = [i for i in items if has_truth[i]]
        n_items = [i for i in items if not has_truth[i]]
        d_items = [i for i in items if has_dis.get(i, False)]
        hit = boot(sw.loc[t_items].values)
        rest = boot(sw.loc[n_items].values)
        rng = np.random.default_rng(SEED)  # (a) difference, independent-arm item bootstrap
        a, b = sw.loc[t_items].values, sw.loc[n_items].values
        diffs = [a[rng.integers(0, len(a), len(a))].mean() - b[rng.integers(0, len(b), len(b))].mean() for _ in range(N_BOOT)] if len(a) and len(b) else []
        rows.append({"layer": L, "position": position, "n_items": len(items), "n_truth_in_top5": len(t_items),
                     "causal_hit_rate": hit[0], "ci_lo": hit[1], "ci_hi": hit[2],
                     "ctl_a_no_truth_rate": rest[0], "ctl_a_n": len(n_items),
                     "ctl_a_diff": (a.mean() - b.mean()) if len(diffs) else np.nan,
                     "ctl_a_diff_lo": float(np.quantile(diffs, 0.025)) if diffs else np.nan,
                     "ctl_a_diff_hi": float(np.quantile(diffs, 0.975)) if diffs else np.nan,
                     "ctl_b_random_rate_same_items": float(rnd.reindex(t_items).mean()) if t_items else np.nan,
                     "ctl_d_own_distractor_n": len(d_items),
                     "ctl_d_own_distractor_rate": float(sw.loc[d_items].mean()) if d_items else np.nan,
                     "untested_tokens": int((jl.causal_status == "UNTESTED").sum()), "tokens": len(jl)})
    return pd.DataFrame(rows)


def build(P: A.Paths, tok) -> pd.DataFrame:
    items = pd.DataFrame(json.loads((P.dataset / "items_re.json").read_text())["items"])
    bank = items[items.dataset == DS]
    cons = bank.set_index("item_id").construction
    vocab = {first_token_norm(tok, c[k]) for c in cons for k in ("bridge", "distractor")} - {""}
    truth = {i: first_token_norm(tok, c["bridge"]) for i, c in cons.items()}
    dist = {i: first_token_norm(tok, c["distractor"]) for i, c in cons.items()}
    test = set(bank[bank.split == "test"].item_id)
    tk = A.read_jsonl(P.cache / "jlens_terms" / "jterms_topk.jsonl")
    tk = tk[(tk.dataset == DS)]
    dec = {}

    def d(i):
        if i not in dec:
            dec[i] = tok.decode([int(i)])
        return dec[i]

    sf = {(r.layer, r.position): {norm(d(t)) for t in r.topk_ids[:K_MAIN]} for r in tk[tk.item_id == "__mean__"].itertuples()}
    rows = []
    for r in tk[tk.item_id.isin(test)].itertuples():
        ctl = r.control
        seed = -1 if pd.isna(r.seed) else int(r.seed)
        for c in classify([d(t) for t in r.topk_ids[:K_MAIN]], truth[r.item_id], dist[r.item_id], vocab, sf.get((r.layer, r.position), set())):
            rows.append({"control": ctl, "seed_k": seed, "position": r.position, "layer": int(r.layer), "item": r.item_id, **c})
    for (L, pos), toks in sf.items():  # (c) the state-free list, scored against every test item's truth
        lst = [t for t in tk[(tk.item_id == "__mean__") & (tk.layer == L) & (tk.position == pos)].iloc[0].topk_ids[:K_MAIN]]
        for i in test:
            for c in classify([d(t) for t in lst], truth[i], dist[i], vocab, toks):
                rows.append({"control": "state_free", "seed_k": -1, "position": pos, "layer": int(L), "item": i, **c})
    return pd.DataFrame(rows)


def report(prec: pd.DataFrame, cz: pd.DataFrame, led: pd.DataFrame) -> list[str]:
    f = lambda x: f"{x:.3f}" if np.isfinite(x) else "—"  # noqa: E731
    L = ["# SWAP false-positive ledger (J-lens top-5 on the SWAP khop items; descriptive, rule pre-registered in BRIEF_R)", "",
         "Classes: TRUTH = the item's true bridge (first token, normalised); CANDIDATE-NAME PRIOR = any other bridge / distractor "
         "name of the re_khop2_bridge bank (WS5 F1's H-name analogue); OTHER = everything else. Controls: random-rotation J-lens "
         "(5 seeds pooled), the state-free list. Precision counts every TRUTH token, so a surface variant pair (' Brazil', "
         "'Brazil') counts twice; §15 (b)'s hit@K matches the first-token id only.", ""]
    for pos in ("rp", "last"):
        L += [f"## Precision@K and class shares — position `{pos}`{' (SWAP edit site)' if pos == 'rp' else ''}", "",
              "| layer | control | P@1 | P@3 | P@5 [95% CI] | prior share of top-5 [95% CI] | other share | own distractor in top-5 |",
              "|---|---|---|---|---|---|---|---|"]
        for _, r in prec[prec.position == pos].sort_values(["layer", "control"]).iterrows():
            L.append(f"| {r.layer} | {r.control} | {f(r['precision@1'])} | {f(r['precision@3'])} | "
                     f"{f(r['precision@5'])} [{f(r['precision@5_lo'])}, {f(r['precision@5_hi'])}] | "
                     f"{f(r.prior_share)} [{f(r.prior_share_lo)}, {f(r.prior_share_hi)}] | {f(r.other_share)} | {f(r.own_distractor_in_top5)} |")
        L.append("")
    L += ["## Causal-hit rate (position `rp`, the SWAP edit site; answer flips under d_swap)", "",
          "Only the TRUTH token and the own distractor are tested by a SWAP edit; every other top-5 token is UNTESTED.", "",
          "| layer | items | truth in top-5 | causal-hit rate [95% CI] | (a) items without truth in top-5 | (a) difference [95% CI] | "
          "(b) random arms, same items | (d) own distractor in top-5: n, rate | untested / tokens |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in cz.itertuples():
        L.append(f"| {r.layer} | {r.n_items} | {r.n_truth_in_top5} | {f(r.causal_hit_rate)} [{f(r.ci_lo)}, {f(r.ci_hi)}] | "
                 f"{f(r.ctl_a_no_truth_rate)} (n {r.ctl_a_n}) | {f(r.ctl_a_diff)} [{f(r.ctl_a_diff_lo)}, {f(r.ctl_a_diff_hi)}] | "
                 f"{f(r.ctl_b_random_rate_same_items)} | {r.ctl_d_own_distractor_n}, {f(r.ctl_d_own_distractor_rate)} | {r.untested_tokens} / {r.tokens} |")
    top = led[(led.control == "jlens") & (led.position == "rp") & (led.cls != "TRUTH")]
    common = top.groupby(["cls", "token"]).size().sort_values(ascending=False).head(12)
    L += ["", "Most frequent non-truth J-lens top-5 tokens at `rp` (all layers): " +
          "; ".join(f"{t!r} ({c.split()[0].lower()}, {n})" for (c, t), n in common.items())]
    return L


def main(argv: list[str] | None = None) -> int:
    from transformers import AutoTokenizer

    P = A.Paths()
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.6-27B", local_files_only=True)
    led = build(P, tok)
    prec = precision_table(led)
    sw = A.read_jsonl(P.cache / "swap" / "swap.jsonl")
    fl = S.khop_flips(sw[sw.part == "khop"] if "part" in sw.columns else sw)
    cz = causal_table(led, fl)
    tdir = P.root / ".ws3_cache" / "swap_ledger"  # 13 MB: a large artefact, kept out of git (CLAUDE.md rule 4)
    tdir.mkdir(parents=True, exist_ok=True)
    led.to_csv(tdir / "swap_ledger_tokens.csv.gz", index=False)
    prec.to_csv(P.results / "swap_ledger.csv", index=False)
    cz.to_csv(P.results / "swap_ledger_causal.csv", index=False)
    L = report(prec, cz, led)
    from projects.g_agreement.r_bench import ws3_tier as WT

    (P.results / "swap_ledger.md").write_text(WT.finalize_md("\n".join(L)) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
