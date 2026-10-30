#!/usr/bin/env python
"""T2 under Z1's protocol (secondary, zero training): the out-of-fold T1 layer-42 LAST-TOKEN probe (a) from run.py (trained on the
natural ownership/mapping states, pair-family folds) is applied to the S2+S3 planted read-backs (block-42 last token after the
edit) and scored toward the edited-in candidate (cand_B; the natural answer is cand_A): f = logit[other] - logit[original].
AUROC against flipped_to_other and the paired ΔAUROC over the (site, α) dose-only reference, pair bootstrap - the same quantity
Z1's gain_over_dose.md reports for J-lens / Oracle / NLA (flip ~ f_r). Appends rows to v5.csv, a section to v5.md, rebuilds fig_v5.png.

Usage: OMP_NUM_THREADS=2 PYTHONPATH=. .venv/bin/python projects/g_agreement/v5_window/t2_via_t1.py [--n-boot 1000] [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.v5_window import data as D  # noqa: E402
from projects.g_agreement.v5_window import models as M  # noqa: E402
from projects.g_agreement.v5_window import run as R  # noqa: E402

MODEL_NAME = "T1 probe (a) L42, answer score toward the edited candidate [Z1 protocol]"


def flip_scores(logits: np.ndarray, classes: Sequence[str], other_is_first: Sequence[bool]) -> np.ndarray:
    """logit[edited-in candidate's class] - logit[original answer's class]; classes = ['second_mentioned', 'first_mentioned']."""
    fi, si = classes.index("first_mentioned"), classes.index("second_mentioned")
    o = np.asarray(other_is_first, bool)
    return np.where(o, logits[:, fi] - logits[:, si], logits[:, si] - logits[:, fi])


def load_reader(path: Path, device) -> M.Reader:
    d = torch.load(path, map_location="cpu", weights_only=False)
    m = M.Reader(d["kind"], d["d"], d["n_classes"])
    m.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in d["state_dict"].items()})
    return m.to(device).eval()


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "results" / "g_agreement" / "v"))
    ap.add_argument("--weights", default=str(ROOT / "cache" / "g_agreement" / "v" / "window_reader"))
    args = ap.parse_args(argv)
    out, wdir = Path(args.out), Path(args.weights)
    device = torch.device("cpu")
    folds = json.load(open(wdir / "folds.json"))
    fold_of_pair: Dict[str, int] = folds["own_map"]["fold_of_pair"]
    t2_fold = folds["t2_S2+S3"]["fold_of_pair"]
    assert t2_fold == fold_of_pair, "T2 and own/map pair folds differ; the out-of-fold guarantee would not hold"
    xitems = D.load_x_items()
    w2 = D.load_t2(("S2", "S3"))
    beh = {r["key"]: r for r in D.load_jsonl(D.X_BEH)}
    state_ids = [f"{beh[k]['pair_id']}{beh[k]['source']}" for k in w2.ids]
    other_is_first = [beh[k]["cand_B"] == xitems[s]["construction"]["first_mentioned_candidate"] for k, s in zip(w2.ids, state_ids)]
    assert all(beh[k]["cand_A"] == xitems[s]["primary"]["answer"] for k, s in zip(w2.ids, state_ids)), "cand_A must be the natural answer"
    scores = np.zeros(len(w2))
    classes = None
    for f in sorted(set(fold_of_pair.values())):
        idx = [i for i, p in enumerate(w2.meta["pair_id"]) if fold_of_pair[p] == f]
        p = wdir / "t1t3_own_map" / f"t1t3_ownmap_L42__last_linear__fold{f}.pt"
        m = load_reader(p, device)
        classes = torch.load(p, map_location="cpu", weights_only=False)["classes"]
        lg = M.predict_logits(m, w2.x[idx].to(device), w2.mask[idx].to(device))
        scores[idx] = flip_scores(lg, classes, [other_is_first[i] for i in idx])
    fold_ids = np.array([fold_of_pair[p] for p in w2.meta["pair_id"]])
    dose = R.dose_only_oof(w2.meta["cell"], w2.y, fold_ids)
    st = R.pair_boot_auroc(scores, dose, w2.y, w2.meta["pair_id"], args.n_boot, args.seed)
    # per site and per family, descriptive
    extra = {}
    for key, sel in (("S2", np.array(w2.meta["site"]) == "S2"), ("S3", np.array(w2.meta["site"]) == "S3"),
                     ("ownership", np.array(w2.meta["family"]) == "ownership"), ("mapping", np.array(w2.meta["family"]) == "mapping")):
        extra[key] = R.auroc(scores[sel], w2.y[sel])
    row = dict(target="T2", dataset="S2+S3", layer=42, train="T1 natural (OOF)", test="planted", model=MODEL_NAME, set="planted", metric="auroc_flip", n=len(w2),
               estimate=st["auroc"], ci_lo=st["auroc_lo"], ci_hi=st["auroc_hi"], ref_best_last="dose-only(site,alpha)", delta=st["delta"], delta_lo=st["delta_lo"],
               delta_hi=st["delta_hi"], n_pairs=st["n_pairs"], lambdas="", epochs="")
    rows = R.rows_from_csv(out / "v5.csv")
    rows = [r for r in rows if r["model"] != MODEL_NAME] + [row]
    R.write_csv(out / "v5.csv", rows)
    verdict = "beats dose" if st["delta_lo"] > 0 else ("does not beat dose" if st["delta_hi"] < 0 else "indistinguishable from dose")
    sec = ["### T2 under Z1's protocol (secondary, no training): the T1 last-token probe's answer score as the flip predictor\n",
           "The flip-trained probes above answer a harder question than Z1's readers did: Z1 scored each reader's native log-odds toward the edited-in candidate "
           "(flip ~ f_r). The like-for-like column: the out-of-fold T1 layer-42 last-token probe (a) (trained on the 128 natural states, pair-family folds) applied to the "
           "edited read-backs, f = logit[edited-in candidate] − logit[original answer].\n",
           "| entries | predictor | AUROC [95% CI] | dose-only AUROC | ΔAUROC over dose [CI] | verdict (Z1 rule) |", "|---|---|---|---|---|---|",
           f"| S2+S3 planted (n={len(w2)}, {st['n_pairs']} pairs) | {MODEL_NAME} | {R._ci(row, False)} | {R._f(st['ref_auroc'], False)} | {R._delta(row, False)} | {verdict} |",
           "| S2+S3 planted | Z1 readers (gain_over_dose.md; dose = logistic flip ~ α) | Oracle 0.907, J-lens 0.904, NLA 0.804 | 0.946–0.947 | −0.039, −0.042, −0.143 | none beat dose |",
           "", f"Descriptive AUROC by subset: S2 {extra['S2']:.3f}, S3 {extra['S3']:.3f}, ownership {extra['ownership']:.3f}, mapping {extra['mapping']:.3f}. "
           "This column is not a window reader and does not bear on the pre-registered success rule; it shows what the last-token answer probe sees of the causal edit.", ""]
    md = (out / "v5.md").read_text(encoding="utf-8")
    start = md.find("### T2 under Z1's protocol")
    if start != -1:
        md = md[:start] + md[md.find("## Verdict", start):]
    md = md.replace("## Verdict against", "\n".join(sec) + "\n## Verdict against", 1)
    (out / "v5.md").write_text(md, encoding="utf-8")
    R.make_fig(out / "fig_v5.png", rows)
    print(json.dumps({"auroc": st["auroc"], "ci": [st["auroc_lo"], st["auroc_hi"]], "dose": st["ref_auroc"], "delta": st["delta"], "delta_ci": [st["delta_lo"], st["delta_hi"]],
                      "by_subset": extra, "verdict": verdict}, indent=1))
    return st


if __name__ == "__main__":
    main()
