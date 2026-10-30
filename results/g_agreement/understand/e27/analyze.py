"""E27(a,b): sealed S16 item intervals and descriptive S16/E7 reconciliation.

CPU only. Inputs are existing sealed outputs. No model-loading or generation path.
Run from any directory; private absolute source paths are never written to public output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import time
import zipfile

import numpy as np
from scipy.stats import rankdata

SEED = 20261025
N_BOOT = 2000
ROWS = ("bk_listidx", "ij2_lang", "tb_paren", "tb_tablecol")
ARMS = ("h", "r_nla", "r_ol", "swap_res", "swap_ol", "swap_resn", "ol_only")
E7_ARMS = ("swap", "self", "ol_only", "nla_only", "delta_only", "random")
SOURCE_COMMIT = "a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb"
PINS = {
    "s16_archive": "c105d0fb069b2eb503c1a8177925e935239df7b70d482c9c2ee75060acd35151",
    "s16_manifest": "dd2eb6292e65e941d4fbc81d7328b9ec5cf9395305dadb0565b5559f7327d5c7",
    "s16_source": "ea7897abdae35e0b5ef1055f06143f5f758891629b5c58147b9880f48638332f",
    "e7_input_seal": "4ff8df9b6122decea25a5f4d5393fe76cfdb7bd00810bf96be71d17adc67ce1a",
    "e7_score_seal": "9243af8a9a2c3b6dbb63520ac2ca192918233071458e100f119e43ec4e1f8bf3",
    "e7_analysis_seal": "d19f88da481f57f239123c93713fe6025749c48c69bfe452c3f5ee9841133918",
    "e7_labels": "4174b5ab132f5927ea4dbeac224754b2994cb75a7c65b635dd0b16930d5d1118",
}
E7_SCORES = Path("cache/g_agreement/blindspot/understand-units/39y8o1p4bvyhh7/E7_DESCRIPTIVE_NEW_RUN/e7/scores")
E7_INPUTS = Path("cache/g_agreement/understand/e7")
E7_RESULTS = Path("results/g_agreement/understand/e7")
E7_LABELS = Path("cache/g_agreement/blindspot/mechanism/w34-collection-ebf6c121/labels.DO_NOT_STAGE.jsonl")


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


def verify_seal(root, name, expected):
    """Reject seal or payload changes before any score/label join."""
    root = Path(root)
    if sha(root / name) != expected:
        raise ValueError(f"{name} identity mismatch")
    seal = read_json(root / name)
    if not seal.get("files"):
        raise ValueError("empty seal")
    for name, wanted in seal["files"].items():
        member = Path(name)
        if member.is_absolute() or ".." in member.parts:
            raise ValueError("unsafe seal member")
        if sha(root / member) != wanted:
            raise ValueError(f"sealed payload mismatch: {name}")
    return seal


def validate_binary(scores, labels):
    s, y = np.asarray(scores, dtype=float), np.asarray(labels)
    if s.ndim != 1 or y.shape != s.shape or len(s) == 0:
        raise ValueError("equal nonempty one-dimensional scores and labels required")
    if not np.isfinite(s).all() or not np.isin(y, (0, 1)).all():
        raise ValueError("finite scores and binary labels required")
    return s, y.astype(int)


def rank_auc(scores, labels):
    """E7 rank implementation, ties count one half."""
    s, y = validate_binary(scores, labels)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    ranks = rankdata(s, method="average")
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def pairwise_auc(scores, labels):
    """Independent S16 pairwise implementation, ties count one half."""
    s, y = validate_binary(scores, labels)
    a, b = s[y == 1], s[y == 0]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float((a[:, None] > b).mean() + 0.5 * (a[:, None] == b).mean())


def bootstrap_auc(scores, labels, indices):
    s, y = validate_binary(scores, labels)
    ix = np.asarray(indices)
    if ix.ndim != 2 or ix.shape[1] != len(s) or not np.issubdtype(ix.dtype, np.integer):
        raise ValueError("bootstrap index matrix must have one full-size sample per row")
    if ix.min() < 0 or ix.max() >= len(s):
        raise ValueError("bootstrap index out of range")
    bx, by = s[ix], y[ix]
    ranks = rankdata(bx, method="average", axis=1)
    n1, n0 = by.sum(1), len(s) - by.sum(1)
    numerator = (ranks * by).sum(1) - n1 * (n1 + 1) / 2
    return np.divide(numerator, n1 * n0, out=np.full(len(ix), np.nan), where=(n1 * n0) > 0)


def interval(samples):
    a = np.asarray(samples, dtype=float)
    finite = a[np.isfinite(a)]
    ci = [float(v) for v in np.quantile(finite, [0.025, 0.975], method="linear")] if len(finite) else [None, None]
    return {"ci95": ci, "valid_bootstrap_draws": len(finite), "invalid_bootstrap_draws": len(a) - len(finite)}


def wilson(k, n):
    if not 0 <= k <= n or n <= 0 or int(k) != k or int(n) != n:
        raise ValueError("Wilson requires an integer binomial count and positive denominator")
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z / den * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [max(0.0, mid - half), min(1.0, mid + half)]


def sign_follow(scores, labels, indices):
    s, y = validate_binary(scores, labels)
    success = (2 * y - 1) * s > 0
    n, k = len(s), int(success.sum())
    return {
        "definition": "strict signed preference: (2*y_side-1)*score > 0; exact ties are not following",
        "k": k, "n": n, "rate": k / n, "ties": int((s == 0).sum()),
        "wilson_ci95": wilson(k, n), **interval(success[indices].mean(1)),
    }


def verify_sources(archive, e7_root):
    if sha(archive) != PINS["s16_archive"]:
        raise ValueError("S16 archive identity mismatch")
    evidence = {"pins": PINS.copy(), "s16_source_commit": SOURCE_COMMIT}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive members")
        manifest_bytes = z.read("logs/exp16_completed/manifest.json")
        source_bytes = z.read("logs/exp16_completed/logs/controller/source.json")
        if digest_bytes(manifest_bytes) != PINS["s16_manifest"] or digest_bytes(source_bytes) != PINS["s16_source"]:
            raise ValueError("S16 original manifest/source changed")
        if json.loads(source_bytes)["commit"] != SOURCE_COMMIT:
            raise ValueError("S16 source commit mismatch")
        manifest = {r["path"]: r for r in json.loads(manifest_bytes)}
        wanted = [f"16_difference_term/{stage}_{f}.{ext}" for f in ROWS for stage, ext in (("s1", "pt"), ("s2", "pt"), ("analysis16", "json"))]
        # Original stage filenames are s1_feature/s2_feature, whereas analysis16 uses its full name.
        for name in wanted:
            b = z.read(name)
            m = manifest[name]
            if len(b) != m["bytes"] or digest_bytes(b) != m["sha256"]:
                raise ValueError(f"S16 payload mismatch: {name}")
        evidence["s16_main_files"] = {name: manifest[name] for name in wanted}
    evidence["e7_input_seal"] = verify_seal(e7_root / E7_INPUTS, "INPUT_SEAL.json", PINS["e7_input_seal"])
    evidence["e7_score_seal"] = verify_seal(e7_root / E7_SCORES, "SCORE_SEAL.json", PINS["e7_score_seal"])
    evidence["e7_analysis_seal"] = verify_seal(e7_root / E7_RESULTS, "SCORE_SEAL.json", PINS["e7_analysis_seal"])
    if sha(e7_root / E7_LABELS) != PINS["e7_labels"]:
        raise ValueError("E7 frozen labels changed")
    evidence["verified_before_labels_loaded"] = True
    return evidence


def load_s16(archive):
    import torch  # tensor deserialization on CPU only, after archive/manifest verification
    out = {}
    with zipfile.ZipFile(archive) as z:
        for feature in ROWS:
            s = torch.load(io.BytesIO(z.read(f"16_difference_term/s1_{feature}.pt")), map_location="cpu", weights_only=False)
            t = torch.load(io.BytesIO(z.read(f"16_difference_term/s2_{feature}.pt")), map_location="cpu", weights_only=False)
            published = json.loads(z.read(f"16_difference_term/analysis16_{feature}.json"))
            ids, y, j = s["ids"], np.asarray(s["y"]), np.asarray(s["j"])
            clusters = np.asarray(s["clusters"])
            if len(ids) != 200 or len(set(ids)) != 200 or ids != t["ids"] or y.shape != (200,) or j.shape != (200,) or clusters.shape != (200,):
                raise ValueError("S16 item grid mismatch")
            if not np.isin(y, (0, 1)).all() or set(y) != {0, 1} or not np.issubdtype(j.dtype, np.integer) or j.min() < 0 or j.max() >= 200:
                raise ValueError("S16 binary labels or partners invalid")
            if not (y[j] != y).all() or not (clusters[j] != clusters).all():
                raise ValueError("S16 opposite-class/different-cluster pairing violated")
            readers = {"nla": s["nla_lo"], "ol": t["ol_lo"]}
            for reader, arms in readers.items():
                if set(arms) != set(ARMS):
                    raise ValueError("S16 arm grid mismatch")
                for arm, values in arms.items():
                    values = values.cpu().numpy()
                    if values.shape != (4, 200) or not np.isfinite(values).all():
                        raise ValueError("S16 phrasing score grid mismatch")
                    readers[reader][arm] = values
            out[feature] = {"ids": ids, "y": y, "j": j, "clusters": clusters, "readers": readers, "published": published,
                            "pairs": {"nla": s["pairs"], "ol": t["pairs"]}, "oracle_generations_per_item": len(s["bullets"][0])}
    return out


def s16_intervals(source):
    rng = np.random.default_rng(SEED)
    cells, metadata, equivalence = [], [], []
    for feature in ROWS:
        data = source[feature]
        y, j = data["y"], data["j"]
        ix = rng.integers(0, len(y), size=(N_BOOT, len(y)))
        metadata.append({"row": feature, "n": len(y), "positive_B": int(y.sum()), "unique_donors": int(len(np.unique(j))),
                         "clusters": int(len(np.unique(data["clusters"]))), "oracle_generations_per_item": data["oracle_generations_per_item"],
                         "draw_indices_sha256": digest_bytes(ix.astype("<i8").tobytes()),
                         "phrasing_ids": {reader: [p[0] for p in pairs] for reader, pairs in data["pairs"].items()}})
        for reader in ("nla", "ol"):
            for arm in ARMS:
                raw = data["readers"][reader][arm]
                # Keep source float32 reduction semantics, exactly as S16 torch.mean(0).
                import torch
                scores_by_summary = {"mean": torch.from_numpy(raw).mean(0).numpy(), "fixed": raw[0]}
                for summary, scores in scores_by_summary.items():
                    for side, target in (("i", y), ("j", y[j])):
                        value = pairwise_auc(scores, target)
                        published = data["published"]["readers"][reader][arm][summary]["follows_" + side]
                        if not math.isclose(value, published, rel_tol=0, abs_tol=1e-12):
                            raise ValueError(f"published S16 point mismatch: {feature}/{reader}/{arm}/{summary}/{side}")
                        e7_style = rank_auc(-scores, 1 - target)
                        if not math.isclose(value, e7_style, rel_tol=0, abs_tol=1e-12):
                            raise ValueError("cross-metric orientation equivalence failed")
                        key = {"row": feature, "reader": reader, "arm": arm, "summary": summary, "side": "recipient" if side == "i" else "donor"}
                        cells.append({**key, "reader_site": "NLA@42 native" if reader == "nla" else "Oracle@42 off trained grid; auxiliary",
                                      "n": len(y), "auroc": value, "published_auroc": published, **interval(bootstrap_auc(scores, target, ix)),
                                      "wilson_for_auroc": None, "wilson_for_auroc_reason": "AUROC is not a binomial success proportion",
                                      "secondary_sign_follow": sign_follow(scores, target, ix)})
                        equivalence.append({**key, "s16_B_positive_auroc": value, "e7_A_positive_auroc": e7_style, "absolute_difference": abs(value - e7_style)})
    if len(cells) != 224:
        raise ValueError("all 224 published S16 follow cells required")
    return {"rows": metadata, "cells": cells, "metric_crosscheck": equivalence}


def e7_crosscheck(root):
    inputs, scores = root / E7_INPUTS, root / E7_SCORES
    pairs, records = rows(inputs / "pairs.input.jsonl"), rows(scores / "scores.jsonl")
    ids, definitions = read_json(inputs / "ids.json"), read_json(inputs / "definitions.json")
    labels_rows = rows(root / E7_LABELS)
    labels = {r["id"]: r for r in labels_rows}
    if len(labels) != len(labels_rows) or not set(ids).issubset(labels):
        raise ValueError("E7 duplicate or missing labels")
    published = {r["feature"]: r for r in read_json(root / E7_RESULTS / "metrics.json")["rows"]}
    score_map = {(r["id"], r["arm"]): r for r in records}
    expected = {(p["id"], arm) for p in pairs for arm in E7_ARMS}
    if len(pairs) != 1000 or len(records) != 6000 or len(score_map) != 6000 or set(score_map) != expected or len(definitions) != 25:
        raise ValueError("E7 complete six-arm grid required")
    cells = []
    for feature, definition in sorted(definitions.items()):
        ps = [p for p in pairs if p["feature"] == feature]
        if len(ps) != 40:
            raise ValueError("E7 requires forty directed pairs per row")
        for arm in E7_ARMS:
            for p in ps:
                if score_map[p["id"], arm]["feature"] != feature:
                    raise ValueError("E7 score feature mismatch")
            values = np.array([score_map[p["id"], arm]["score"] for p in ps])
            for side in ("recipient", "donor"):
                y = np.array([labels[ids[p[side]]]["value"] == definition["values"][0] for p in ps], int)
                value = rank_auc(values, y)
                other = pairwise_auc(-values, 1 - y)
                old = published[feature]["arms"][arm][side]
                if not math.isclose(value, old["auroc"], rel_tol=0, abs_tol=1e-12) or not math.isclose(value, other, rel_tol=0, abs_tol=1e-12):
                    raise ValueError(f"E7 published/cross-metric mismatch: {feature}/{arm}/{side}")
                cells.append({"row": feature, "class": definition["row_class"], "reader": "NLA@42 native", "arm": arm, "side": side,
                              "n_directed_pairs": len(ps), "n_unique_recipients": len({p["recipient"] for p in ps}),
                              "e7_A_positive_auroc": value, "s16_B_positive_auroc": other, "absolute_difference": abs(value - other),
                              "published_template_cluster_ci95": [old["lo"], old["hi"]], "published_auroc": old["auroc"]})
    return {"cells": cells, "point_checks": len(cells), "new_bootstrap_or_probe_runs": 0,
            "fixed_first_phrasing": "UNAVAILABLE: E7 sealed outputs contain the mean of two W1 pairs only; source tensor cannot recover individual-pair scores",
            "phrasing_limit": "Changing AUROC orientation does not substitute S16's four candidate pairs for E7's two W1 pairs"}


DESIGN = [
    {"difference": "Rows and units", "S16": "table-column, parenthesis, French/German language, list-index; 200 recipient items per row", "E7": "25 W1 rows (9 count-like, 7 state-like, 9 semantic); 84 test items for reconstruction/probes, 40 directed scored pairs per row"},
    {"difference": "Position label definitions", "S16": "Table-column: first (column1) versus late (columns4-6). List-index: early (items2-3) versus late (items8-12)", "E7": "Table-column: first (column1) versus later (column5). List-index: first (item1) versus later (items6-8). Related names do not imply identical contrasts or banks"},
    {"difference": "Lens part / reconstructor", "S16": "R_OL = NLA's native42 reconstructor applied to Oracle-generated text from layer44", "E7": "Same definition: native42 NLA decoder on Oracle text from layer44; not the Oracle reconstructor"},
    {"difference": "Space", "S16": "Raw 5120-dimensional native42 activations; no whitening", "E7": "Raw 5120-dimensional native42 activations; no whitening"},
    {"difference": "Swapped component", "S16": "Headline swap_res = R_OL,i + (h_j - R_OL,j); comparable swap_resn = R_OL,i + (R_NLA,j - R_OL,j)", "E7": "swap = R_OL,i + (R_NLA,j - R_OL,j); matches S16 swap_resn algebra"},
    {"difference": "Other arms", "S16": "h, R_NLA, R_OL, swap_res, swap_ol, swap_resn, ol_only (R_OL duplicate reference)", "E7": "swap, self (=R_NLA), ol_only, nla_only (=R_NLA), delta_only, random-donor delta"},
    {"difference": "Partner selection", "S16": "Seed16; one opposite-value partner from a different cluster per recipient; partner reuse allowed", "E7": "Seeded W4 plan; 40 opposite-value directed pairs without replacement, same domain/template/8-token length bin; recipient/donor reuse allowed"},
    {"difference": "Generation / reconstruction averaging", "S16": "Mean of native42 reconstructions of two Oracle readouts; NLA reconstructions averaged over saved generation dimension", "E7": "One existing sealed W3 Oracle greedy256 readout and one NLA greedy128 readout per item; no sample averaging"},
    {"difference": "Reader sites", "S16": "NLA@42 native; auxiliary Oracle asked@42 is off the Oracle trained grid; Oracle texts generated@44", "E7": "Follow scores are NLA@42 only; Oracle source texts generated@44"},
    {"difference": "Asked phrasings", "S16": "Four frozen exp13/07 pairs: fixed label plus three selected mined pairs; mean and fixed-first reported; summed candidate token logprob", "E7": "Two frozen W1 NLA pairs, summed candidate token logprob, then mean over pairs; only aggregate saved"},
    {"difference": "Follow metric and sign", "S16": "Tie-aware AUROC versus recipient/donor labels; B-minus-A score and B-positive labels", "E7": "Same tie-aware AUROC with A-minus-B score and A-positive labels; simultaneous sign/label reversal leaves AUROC invariant"},
    {"difference": "Uncertainty", "S16": "E27 adds requested 2000 recipient-item bootstrap CIs conditional on frozen partners; Wilson only for explicitly secondary strict-sign proportions", "E7": "Existing 2000 template-cluster bootstrap CIs retained; no bootstrap/probe refit in E27"},
    {"difference": "Headline denominator", "S16": "About98% refers to individual position rows under swap_res", "E7": "About49% refers to the nine-row count-like median, not the table-column row; row-matched table below avoids that aggregation mismatch"},
]


def comparison(s16, e7):
    out = []
    mapping = {"tb_tablecol": "table_column", "tb_paren": "prose_paren", "bk_listidx": "list_index", "ij2_lang": None}
    for sf, ef in mapping.items():
        d = {"s16_row": sf, "e7_row": ef, "reader": "NLA@42", "summary": "source mean phrasings", "side": "donor"}
        for arm in ("swap_res", "swap_resn"):
            r = next(r for r in s16["cells"] if r["row"] == sf and r["reader"] == "nla" and r["arm"] == arm and r["summary"] == "mean" and r["side"] == "donor")
            d["s16_" + arm] = {"auroc": r["auroc"], "ci95": r["ci95"]}
        if ef:
            r = next(r for r in e7["cells"] if r["row"] == ef and r["arm"] == "swap" and r["side"] == "donor")
            d["e7_swap"] = {"auroc": r["e7_A_positive_auroc"], "published_template_cluster_ci95": r["published_template_cluster_ci95"]}
        else:
            d["e7_swap"] = None
        out.append(d)
    return out


def fmt(value, ci=None):
    return f"{value:.4f}" + (f" [{ci[0]:.4f}, {ci[1]:.4f}]" if ci and all(x is not None for x in ci) else "")


def write_reports(out, results):
    matched = results["row_comparison"]
    lines = ["# E27(a,b) — dated descriptive analysis, 25 October 2026", "",
        "**Prediction/context:** the proposed S16–E7 reconciliation asks whether a design or metric difference explains strong S16 donor following versus E7's weak position results. **Assessment:** the follow metrics are identical under their respective label conventions. Matching the swapped component reduces S16's position estimates, but its sealed `swap_resn` results remain much higher than E7's matching rows. The remaining difference cannot be assigned to one cause from these outputs.", "",
        "CPU only. All 224 original S16 follow AUROC cells received 2,000 recipient-item bootstrap intervals (seed 20261025), and all source point estimates were reproduced. All 300 E7 point estimates were reproduced and cross-evaluated with S16's metric. E7's existing cluster-bootstrap intervals and probe results were preserved, without rerunning them. No new swaps, model calls, API calls, or E27(c).", "",
        "## Matched-reader comparison", "",
        "NLA@42 donor AUROC. S16 intervals are the new requested item bootstrap; E7 intervals are its previously published template-cluster bootstrap. These are different data sets and designs, so overlapping/nonoverlapping intervals do not identify a causal explanation.", "",
        "| S16 / E7 row | S16 raw residual swap | S16 reconstruction-difference swap | E7 reconstruction-difference swap |",
        "|---|---:|---:|---:|"]
    for r in matched:
        a, b, c = r["s16_swap_res"], r["s16_swap_resn"], r["e7_swap"]
        lines.append(f"| {r['s16_row']} / {r['e7_row'] or 'no matching row'} | {fmt(a['auroc'], a['ci95'])} | {fmt(b['auroc'], b['ci95'])} | {fmt(c['auroc'], c['published_template_cluster_ci95']) if c else 'not available'} |")
    lines += ["", "S16's headline `swap_res` freezes the Oracle part and swaps `h − R_OL`; E7 swaps `R_NLA − R_OL`, already available as S16's `swap_resn`. Neither experiment whitens these vectors. Both use the NLA reconstructor for the Oracle-text component. The quoted E7 ~49% is a median over nine count-like rows, not a row-matched table-column estimate.", "",
        "## Design reconciliation", "", "| Design dimension | S16 | E7 |", "|---|---|---|"]
    lines.extend(f"| {d['difference']} | {d['S16']} | {d['E7']} |" for d in DESIGN)
    lines += ["", "## Metric cross-check", "",
        "S16 uses B-minus-A scores and B-positive labels; E7 uses A-minus-B scores and A-positive labels. Simultaneously negating scores and complementing labels leaves the tie-aware AUROC invariant. Independent pairwise and rank implementations agree on every available cell: 224/224 S16 and 300/300 E7. This does not replace one experiment's candidate phrasings, banks, or partner plan with the other's. E7 saved only its two-phrasing mean; a fixed-first E7 score or S16 four-phrasing rescoring is unavailable without new inference.", "",
        "## Intervals, Wilson check, and limits", "",
        "The original S16 fields named `follows_i` and `follows_j` are AUROCs, not binomial proportions. Wilson is therefore **not applicable to the registered follow AUROCs**; no fabricated success count or effective denominator was used. As a separately labelled secondary description, ALL_CELLS.md and METRICS.json also report strict score-sign follow proportions, their item-bootstrap CIs, and ordinary Wilson intervals. A zero margin counts as not following for either side, and ties are counted explicitly. These auxiliary proportions do not replace any original follow metric.", "",
        "Each resampled unit is a recipient with its one original partner and all condition scores attached. The same row resamples are shared across readers, arms, summaries, and sides. Reused donors and template clusters induce dependence not represented by this requested recipient-item bootstrap; intervals are conditional on the frozen pairing and do not include new-pair uncertainty. Donor and recipient AUROCs are complementary, not independent confirmations. All invalid one-class resamples are counted rather than silently replaced.", "",
        "Oracle asked scores in S16 are at block42, off its trained grid; all 112 Oracle cells are retained as auxiliary. The matched comparisons use the native NLA@42 only. Even label definitions differ: S16 list-index compares items2-3 with8-12; E7 compares item1 with6-8. S16 table-column compares1 with4-6; E7 compares1 with5. Banks, partner matching, generated-text averaging, and candidate phrasings remain jointly different. No existing cross-check separates their contributions to the remaining gap.", "",
        "## Files and provenance", "",
        "- `METRICS.json`: all 224 S16 AUROC intervals, secondary sign/Wilson results, and row resampling metadata.",
        "- `ALL_CELLS.md`: all S16 follow AUROCs and secondary sign proportions in a readable table.",
        "- `RECONCILIATION.json`: all 524 cross-metric checks, all 300 existing E7 estimates/CIs, design table and matched rows.",
        "- `SOURCE_VERIFICATION.json`, `RUN_STARTED.json`, `ANALYSIS_SEAL.json`: original file hashes, code/plan hashes fixed before estimates, and final output seal.", "",
        "The existing Suraj archive was located locally and verified against its original completed-S16 manifest; no new retrieval or integrator message occurred. An integrator chat/path reply was not available. Private absolute source locators are kept only in ignored `cache/`; public provenance uses source-relative file names and hashes. All original data and registrations remain unchanged.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))
    table = ["# E27 all S16 cells — 25 October 2026", "",
        "Primary follow = AUROC with recipient-item bootstrap 95% CI. Secondary sign = strict signed margin > 0; its Wilson CI is a binomial check on that different metric. Oracle@42 is auxiliary/off trained grid. Mean = all four source phrasings, fixed = first source phrasing. No cells omitted.", "",
        "| Row | Reader | Arm | Summary | Side | AUROC [item CI] | Secondary sign k/n [item CI] | Secondary Wilson CI | Ties |", "|---|---|---|---|---|---:|---:|---:|---:|"]
    for r in results["s16"]["cells"]:
        s = r["secondary_sign_follow"]
        table.append(f"| {r['row']} | {'NLA@42' if r['reader'] == 'nla' else 'Oracle@42 auxiliary'} | {r['arm']} | {r['summary']} | {r['side']} | {fmt(r['auroc'], r['ci95'])} | {s['k']}/{s['n']} {fmt(s['rate'], s['ci95'])} | [{s['wilson_ci95'][0]:.4f}, {s['wilson_ci95'][1]:.4f}] | {s['ties']} |")
    (out / "ALL_CELLS.md").write_text("\n".join(table) + "\n")


def run(archive, e7_root, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve()
    plan_path = source.with_name("ANALYSIS_PLAN.json")
    start = time.monotonic()
    # A create-only marker enforces one registered E27 invocation per output directory.
    marker = {"date": datetime.now(timezone.utc).isoformat(), "analysis_source_sha256": sha(source), "plan_sha256": sha(plan_path),
              "seed": SEED, "n_boot": N_BOOT, "status": "STARTED_BEFORE_NEW_ESTIMATES", "source_pins": PINS,
              "command_template": "python results/g_agreement/understand/e27/analyze.py --archive VERIFIED_S16_ARCHIVE --e7-root SEALED_E7_CHECKOUT --out results/g_agreement/understand/e27"}
    with (out / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    evidence = verify_sources(Path(archive), Path(e7_root))
    write_json(out / "SOURCE_VERIFICATION.json", evidence)
    s16 = s16_intervals(load_s16(archive))
    e7 = e7_crosscheck(Path(e7_root))
    result = {"date": "2026-10-25", "scope": "E27(a,b), descriptive CPU only", "seed": SEED, "n_boot": N_BOOT,
              "s16": s16, "e7": e7, "design_differences": DESIGN, "row_comparison": comparison(s16, e7)}
    write_json(out / "METRICS.json", {k: result[k] for k in ("date", "scope", "seed", "n_boot", "s16")})
    write_json(out / "RECONCILIATION.json", {"date": result["date"], "s16_metric_crosscheck": s16["metric_crosscheck"], "e7": e7,
                "design_differences": DESIGN, "row_comparison": result["row_comparison"],
                "conclusion": "Metric orientation and raw/whitened space do not explain the gap. Matching swap definition reduces but does not reconcile S16/E7 estimates. Remaining bank, pairing, readout and phrasing differences cannot be separated without new inference."})
    write_reports(out, result)
    write_json(out / "RUN_COMPLETED.json", {"date": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - start,
                "GPU_hours": 0, "API_cost_USD": 0, "model_calls": 0, "new_swaps": 0, "E27_c": "NOT_RUN",
                "s16_cells": len(s16["cells"]), "s16_source_point_checks_passed": len(s16["cells"]), "e7_source_point_checks_passed": e7["point_checks"],
                "cross_metric_checks_passed": len(s16["metric_crosscheck"]) + e7["point_checks"],
                "s16_invalid_auc_bootstrap_draws_across_cells": sum(r["invalid_bootstrap_draws"] for r in s16["cells"]),
                "registered_analysis_invocations": 1, "original_sources_modified": False})
    names = ["ANALYSIS_PLAN.json", "analyze.py", "test_e27.py", "RUN_STARTED.json", "SOURCE_VERIFICATION.json", "METRICS.json", "RECONCILIATION.json", "RESULTS.md", "ALL_CELLS.md", "RUN_COMPLETED.json"]
    seal = {"status": "E27_A_B_CPU_ANALYSIS_COMPLETE", "files": {name: sha(out / name) for name in names}}
    write_json(out / "ANALYSIS_SEAL.json", seal)
    return {"s16_cells": len(s16["cells"]), "cross_metric_checks": 524, "output_seal_sha256": sha(out / "ANALYSIS_SEAL.json"), "wall_seconds": time.monotonic() - start}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--e7-root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(run(a.archive, a.e7_root, a.out), sort_keys=True))


if __name__ == "__main__":
    main()
