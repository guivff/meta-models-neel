"""Registered W1/W5/W1b analysis; no labels are read before score seals pass.

The decision rules are BRIEF_BLINDSPOT §§70, 74, 84. Score orientation is frozen:
positive means value A for binary rows, and higher level for ordinal rows. Probe
CV and bootstrap resampling hold whole template clusters together. Direction
exports are fitted on dev only; scientific comparisons use the test split.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np

from . import protocol as P

LAYERS = (20, 28, 36, 44, 52, 60)
NATIVE = (("olens", 44), ("nla", 42), ("jlens", 44), ("logit", 44))
N_BOOT = 2000
PILOT_REPLICATIONS = MappingProxyType({
    "table_column": MappingProxyType({"nla": 1.00, "olens": .67, "jlens": .64}),
    "prose_paren": MappingProxyType({"nla": .98, "olens": .76, "jlens": .47}),
})
OPERATING_DETAILS = {
    "registration": "projects/g_agreement/BRIEF_BLINDSPOT.md §§70,74,84",
    "i_denominator": "Oracle-evaluable count/state rows",
    "ii_denominator": "the same rows satisfying condition (i); unavailable or gated NLA is not a success",
    "iii_denominator": "Oracle-evaluable semantic rows",
    "empty_denominator": "NOT EVALUABLE",
    "within": "absolute AUROC difference <= 0.10",
    "probe": "fixed L2 logistic regression; five template-grouped folds on test only; lambda=0.001",
    "directions": "separate dev-only logistic fits; value A is positive; no sign reversal",
    "bootstrap": "2000 template-cluster resamples; fixed OOF probe predictions, no probe refit",
    "w5": "all six layer probes >=0.85; evaluable Oracle <0.75 at >=5 of six layers; unresolved rows retained in bounds",
}


def _rate(k, n):
    from common.stats import wilson
    if not n:
        return {"k": k, "n": n, "rate": None, "ci95": None}
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": float(p), "ci95": [float(lo), float(hi)]}


def gate(probe_auc, mismatched_auc, complete=True):
    """Point thresholds only, exactly as registered; CIs remain reported evidence."""
    if probe_auc is None or not np.isfinite(probe_auc) or probe_auc < .85:
        return "NOT DECODABLE"
    if not complete or mismatched_auc is None or not np.isfinite(mismatched_auc) or mismatched_auc > .60:
        return "NOT EVALUABLE"
    return "EVALUABLE"


def _value(cell, key="true"):
    value = cell.get(key)
    return value.get("auroc") if isinstance(value, dict) else value


def _cells_by_key(cells):
    keyed = {(c["feature"], c["reader"], c["layer"]): c for c in cells}
    if len(keyed) != len(cells):
        raise ValueError("duplicate analysis cells")
    return keyed


def replication_comparisons(cells):
    """Descriptive fresh-test comparisons with the brief's nonconfirmatory pilot."""
    keyed = _cells_by_key(cells)
    comparisons = []
    for feature, pilot in PILOT_REPLICATIONS.items():
        for reader, layer in (("olens", 44), ("nla", 42), ("jlens", 44)):
            cell = keyed.get((feature, reader, layer))
            true = cell.get("true") if cell is not None else None
            measured = isinstance(true, dict) and true.get("auroc") is not None
            comparisons.append({
                "feature": feature, "reader": reader, "layer": layer,
                "comparison_status": "DESCRIPTIVE", "pilot_status": "PILOT_NONCONFIRMATORY",
                "pilot_source": "projects/g_agreement/BRIEF_BLINDSPOT.md pilot paragraph and §70 secondary",
                "pilot_auroc": pilot[reader], "pilot_ci95": None, "pilot_n": None,
                "pilot_uncertainty_note": "No sample size or confidence interval supplied in the brief",
                "fresh_split": "test", "fresh_auroc": true["auroc"] if measured else None,
                "fresh_ci95": [true["lo"], true["hi"]] if measured and "lo" in true and "hi" in true else None,
                "fresh_n": cell.get("n_total") if cell is not None else None,
                "fresh_n_clusters": cell.get("n_clusters", true.get("n_clusters") if measured else None) if cell is not None else None,
                "fresh_gate_status": cell["status"] if cell is not None else "NOT EVALUABLE",
                "fresh_minus_pilot": true["auroc"] - pilot[reader] if measured else None,
                "difference_ci95": None,
                "difference_uncertainty_note": "No paired or independent difference CI can be reconstructed from the pilot point estimate alone",
            })
    return comparisons


def adjudicate_w1(cells):
    """Keep all denominators explicit; gated rows never silently become successes."""
    keyed = _cells_by_key(cells)
    ol = [c for c in cells if c["reader"] == "olens" and c["layer"] == 44]
    count_state = [c for c in ol if c["class"] in ("count-like", "state-like") and c["status"] == "EVALUABLE"]
    semantic = [c for c in ol if c["class"] == "semantic" and c["status"] == "EVALUABLE"]
    blind = [c for c in count_state if _value(c) <= c["probe_auroc"] - .15 + 1e-12]
    nla_hits, nla_exclusions = [], []
    for c in blind:
        n = keyed.get((c["feature"], "nla", 42))
        if n is None or n["status"] != "EVALUABLE":
            nla_exclusions.append({"feature": c["feature"], "status": n["status"] if n else "NOT EVALUABLE"})
        elif abs(_value(n) - n["probe_auroc"]) <= .10 + 1e-12:
            nla_hits.append(c["feature"])
    sem_hits = [c for c in semantic if abs(_value(c) - c["probe_auroc"]) <= .10 + 1e-12]
    rates = {"i": _rate(len(blind), len(count_state)), "ii": _rate(len(nla_hits), len(blind)),
             "iii": _rate(len(sem_hits), len(semantic))}
    passed = {k: v["n"] > 0 and v["rate"] >= .75 for k, v in rates.items()}
    if not count_state or not semantic:
        status = "NOT EVALUABLE"
    elif all(passed.values()):
        status = "CONFIRMED"
    elif passed["i"] and passed["iii"]:
        status = "PARTIAL"
    else:
        status = "NOT MET"
    return {"section": 70, "status": status, "conditions": rates, "conditions_pass": passed,
            "blindspot_features": [c["feature"] for c in blind], "nla_success_features": nla_hits,
            "nla_exclusions_on_i_rows": nla_exclusions,
            "oracle_exclusions": [{"feature": c["feature"], "status": c["status"]} for c in ol if c["status"] != "EVALUABLE"],
            "operating_details": OPERATING_DETAILS}


def adjudicate_w5(cells, blindspot_features):
    keyed = _cells_by_key(cells)
    rows = []
    for f in blindspot_features:
        series = [keyed.get((f, "olens", layer)) for layer in LAYERS]
        available = all(c is not None and c["status"] == "EVALUABLE" for c in series)
        weak = sum(c is not None and c["status"] == "EVALUABLE" and _value(c) is not None and _value(c) < .75 for c in series)
        strong = sum(c is not None and c["status"] == "EVALUABLE" and _value(c) is not None and _value(c) >= .75 for c in series)
        probe_ok = all(c is not None and c.get("probe_auroc") is not None and c["probe_auroc"] >= .85 for c in series)
        probe_fails = any(c is not None and c.get("probe_auroc") is not None and c["probe_auroc"] < .85 for c in series)
        status = "CONFIRMED" if probe_ok and weak >= 5 else "NOT MET" if probe_fails or strong >= 2 else "NOT EVALUABLE"
        rows.append({"feature": f, "n_layers_below_075": weak, "probe_all_six_at_least_085": probe_ok,
                     "all_six_evaluable": available, "meets_rule": status == "CONFIRMED", "status": status,
                     "layer_exclusions": [{"layer": layer, "status": c["status"] if c else "NOT EVALUABLE"}
                                          for layer, c in zip(LAYERS, series) if c is None or c["status"] != "EVALUABLE"]})
    rate = _rate(sum(r["meets_rule"] for r in rows), len(rows))
    unresolved = sum(r["status"] == "NOT EVALUABLE" for r in rows)
    upper = (rate["k"] + unresolved) / len(rows) if rows else None
    status = ("NOT EVALUABLE" if not rows else "CONFIRMED" if rate["rate"] >= .75
              else "NOT MET" if upper < .75 else "NOT EVALUABLE")
    return {"section": 74, "status": status, "rows": rows, "rate": rate, "layers": list(LAYERS),
            "unresolved_rows": unresolved, "possible_fraction_bounds": [rate["rate"], upper]}


def adjudicate_w1b(cells, selected_features):
    """The denominator is the committed §79 selection, including failed gates."""
    if not 1 <= len(selected_features) <= 10 or len(set(selected_features)) != len(selected_features):
        raise ValueError("§84 needs the committed list of one to ten distinct §79 candidates")
    keyed = _cells_by_key(cells)
    confirmations = []
    for f in selected_features:
        o, n = keyed.get((f, "olens", 44)), keyed.get((f, "nla", 42))
        evaluable = o is not None and n is not None and o["status"] == n["status"] == "EVALUABLE"
        confirms = evaluable and _value(o) <= o["probe_auroc"] - .15 + 1e-12 and abs(_value(n) - n["probe_auroc"]) <= .10 + 1e-12
        confirmations.append({"feature": f, "evaluable": evaluable, "confirms": bool(confirms)})
    rate = _rate(sum(c["confirms"] for c in confirmations), len(confirmations))
    return {"section": 84, "status": "CONFIRMED" if rate["rate"] >= .70 else "NOT MET",
            "candidates": confirmations, "rate": rate}


def validate_selection_receipt(receipt, w1_features=None):
    """Validate the frozen §84 dependency; this never invents or builds candidates."""
    if not isinstance(receipt, dict):
        raise ValueError("W1b requires a committed screen selection receipt")
    for field, size in (("source_commit", 40), ("selection_sha256", 64)):
        value = receipt.get(field, "")
        if not isinstance(value, str) or len(value) != size or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("invalid selection receipt " + field)
    source = receipt.get("selection_file", "")
    if not isinstance(source, str) or not source or Path(source).is_absolute() or ".." in Path(source).parts:
        raise ValueError("selection_file must be a repository-relative path")
    s79, s81 = receipt.get("section79_features"), receipt.get("section81_features", [])
    if (not isinstance(s79, list) or not 1 <= len(s79) <= 10 or not isinstance(s81, list) or len(s81) > 5
            or any(not isinstance(f, str) or not f for f in s79 + s81)
            or len(set(s79 + s81)) != len(s79 + s81)):
        raise ValueError("invalid or overlapping §79/§81 candidate lists")
    if w1_features is None:
        from .items import FEATURES
        w1_features = FEATURES
    if set(s79) & set(w1_features):
        raise ValueError("§79 candidates must exclude W1 features")
    return receipt


def grouped_probe(h, y, groups, donors, k=5):
    """Held-out template predictions, with train-only standardisation in each fold."""
    import torch
    from mats import probes
    x = torch.as_tensor(np.asarray(h), dtype=torch.float32)
    y, groups, donors = np.asarray(y, int), np.asarray(groups), np.asarray(donors, int)
    if x.ndim != 2 or len(x) != len(y) or len(groups) != len(y) or len(donors) != len(y):
        raise ValueError("invalid probe dimensions")
    if len(np.unique(groups)) < k or set(y) != {0, 1} or not np.isfinite(x.numpy()).all():
        raise ValueError("too few template groups, missing class, or non-finite activations")
    if np.any(donors < 0) or np.any(donors >= len(y)) or not np.array_equal(groups, groups[donors]):
        raise ValueError("probe donor crosses template boundaries")
    scores, mismatched = np.empty(len(y)), np.empty(len(y))
    folds = []
    for fold, te in enumerate(probes.group_folds(groups, k=k, seed=P.SEED)):
        tr = np.setdiff1d(np.arange(len(y)), te)
        if set(y[tr]) != {0, 1} or set(y[te]) != {0, 1}:
            raise ValueError("one-class grouped probe fold")
        model = probes.fit_logreg(x[tr], torch.as_tensor(y[tr]), lam=1e-3)
        scores[te] = model.decision(x[te]).numpy()
        mismatched[te] = model.decision(x[donors[te]]).numpy()
        folds.append({"fold": fold, "train_clusters": sorted(set(groups[tr].tolist())),
                      "test_clusters": sorted(set(groups[te].tolist()))})
    return scores, mismatched, folds


def fit_direction(h, y):
    """Export exact raw-space logistic score and A-positive unit direction."""
    import torch
    from mats.probes import fit_logreg
    x, y = torch.as_tensor(np.asarray(h), dtype=torch.float32), np.asarray(y, int)
    if x.ndim != 2 or len(x) != len(y) or set(y) != {0, 1} or not np.isfinite(x.numpy()).all():
        raise ValueError("invalid dev direction data")
    model = fit_logreg(x, torch.as_tensor(y), lam=1e-3)
    coef = (model.w / model.sd).numpy()
    norm = float(np.linalg.norm(coef))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("degenerate dev probe direction")
    direction = coef / norm
    gap = float((np.asarray(h)[y == 1].mean(0) - np.asarray(h)[y == 0].mean(0)) @ direction)
    return {"direction": direction, "raw_coefficient": coef,
            "raw_intercept": float(model.b - (model.mu * model.w / model.sd).sum()),
            "dev_class_mean_projection_gap": gap, "dev_n": len(y), "fit_split": "dev",
            "positive_label": "value_A", "orientation_flipped": False}


def _measure(true, mismatched, y, groups, probe=None):
    from mats import metrics
    true, mismatched = np.asarray(true), np.asarray(mismatched)
    result = {"true": asdict(metrics.auroc_ci(true, y, groups, n_boot=N_BOOT, seed=P.SEED)),
              "mismatched": asdict(metrics.auroc_ci(mismatched, y, groups, n_boot=N_BOOT, seed=P.SEED))}
    result["difference"] = result["true"]["auroc"] - result["mismatched"]["auroc"]
    result["difference_ci95"] = list(metrics.cluster_bootstrap(
        lambda i: metrics.auroc_labels(true[i], y[i]) - metrics.auroc_labels(mismatched[i], y[i]),
        groups, n_boot=N_BOOT, seed=P.SEED))
    if probe is not None:
        result["probe_minus_reader"] = metrics.auroc_labels(probe, y) - result["true"]["auroc"]
        result["probe_minus_reader_ci95"] = list(metrics.cluster_bootstrap(
            lambda i: metrics.auroc_labels(probe[i], y[i]) - metrics.auroc_labels(true[i], y[i]),
            groups, n_boot=N_BOOT, seed=P.SEED))
    return result


def _sealed(directory, required, kind):
    seal = P.verify(directory, "SCORE_SEAL.json")
    if not seal.get("status", "").startswith(kind) or not set(required) <= set(seal.get("files", {})):
        raise ValueError("score seal lacks required file coverage or stage")
    return seal


def _order(path):
    value = json.loads(Path(path).read_text())
    # Worker convention is a list of IDs; support explicit {ids: [...]} as well.
    ids = value["ids"] if isinstance(value, dict) else value
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid activation item order")
    return ids


def _grid(raw, items, templates, readers):
    expected = {(it["id"], reader, layer, arm) for it in items for reader, layer in readers
                for arm in (("true",) if templates[it["feature"]].get("kind") == "ordinal" else ("true", "mismatched"))}
    keys = [(r["id"], r["reader"], r["layer"], r["arm"]) for r in raw]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("incomplete/duplicate score grid")
    feature_by_id = {it["id"]: it["feature"] for it in items}
    for r in raw:
        pairs = templates[feature_by_id[r["id"]]].get(r["reader"])
        if not isinstance(pairs, list) or len(pairs) < 2 or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in pairs):
            raise ValueError("reader needs at least two frozen phrasing pairs")
        scores = r.get("scores")
        if r.get("status") == "COMPLETE":
            if not isinstance(scores, list) or len(scores) != len(pairs) or np.asarray(scores).ndim != 1 or not np.isfinite(scores).all():
                raise ValueError("complete scores must match the finite one-dimensional frozen phrasing count")
        elif scores is not None:
            raise ValueError("failed score row contains usable-looking scores")
    return dict(zip(keys, raw))


def _labels(bank, path, items, templates):
    expected = json.loads((bank / "provenance.json").read_text())["labels_sha256"]
    if P.sha(path) != expected:
        raise ValueError("labels differ from frozen bank")
    records = P.rows(path)
    lookup = {r["id"]: r for r in records}
    all_items = P.rows(bank / "items.input.jsonl")
    if len(lookup) != len(records) or set(lookup) != {it["id"] for it in all_items}:
        raise ValueError("label coverage mismatch")
    for it in all_items:
        r, spec = lookup[it["id"]], templates[it["feature"]]
        if r["feature"] != it["feature"] or r["split"] not in ("dev", "test"):
            raise ValueError("label feature/split mismatch")
        if r.get("class", spec["class"]) != spec["class"] or r.get("domain", spec["domain"]) != spec["domain"]:
            raise ValueError("frozen class/domain mismatch")
        if spec.get("kind", "binary") == "binary" and r["value"] not in spec["values"]:
            raise ValueError("unknown binary value")
    split_by_cluster = {}
    for r in records:
        key = (r["feature"], r["cluster"])
        if key in split_by_cluster and split_by_cluster[key] != r["split"]:
            raise ValueError("template cluster crosses dev/test")
        split_by_cluster[key] = r["split"]
    if not {it["id"] for it in items} <= set(lookup):
        raise ValueError("scored ID missing label")
    return lookup, expected


def _ordinal_metrics(items, lookup, scoremap, templates):
    from scipy.stats import spearmanr
    from mats.metrics import cluster_bootstrap
    results = []
    for feature, spec in templates.items():
        if spec.get("kind") != "ordinal":
            continue
        ids = [it["id"] for it in items if it["feature"] == feature and lookup[it["id"]]["split"] == "test"]
        raw = [scoremap[(key, "nla", 42, "true")] for key in ids]
        if not ids or any(r["status"] != "COMPLETE" for r in raw):
            results.append({"feature": feature, "status": "NOT EVALUABLE", "n": len(ids)})
            continue
        score = np.array([np.mean(r["scores"]) for r in raw])
        level = np.array([float(lookup[key].get("level", lookup[key]["value"])) for key in ids])
        groups = np.array([lookup[key]["cluster"] for key in ids])
        rho = float(spearmanr(level, score).statistic)
        if not np.isfinite(rho):
            results.append({"feature": feature, "status": "NOT EVALUABLE", "n": len(ids), "reason": "constant ordinal score"})
            continue
        ci = cluster_bootstrap(lambda i: float(spearmanr(level[i], score[i]).statistic), groups, n_boot=N_BOOT, seed=P.SEED)
        results.append({"feature": feature, "rho": rho, "ci95": list(ci), "n": len(ids),
                        "n_clusters": len(set(groups)), "status": "counts" if rho >= .6 else "flags a state"})
    return results


def _analyse_cells(items, lookup, templates, scoremap, activations, readers, export_dev=True):
    from mats.metrics import auroc_labels
    index = {it["id"]: i for i, it in enumerate(items)}
    cells, oof, direction_arrays, direction_metadata = [], [], {}, []
    for feature, spec in templates.items():
        if spec.get("kind", "binary") != "binary":
            continue
        idx = np.array([i for i, it in enumerate(items) if it["feature"] == feature and lookup[it["id"]]["split"] == "test"])
        if not len(idx):
            continue
        ids = [items[i]["id"] for i in idx]
        y = np.array([lookup[key]["value"] == spec["values"][0] for key in ids], int)
        groups = np.array([lookup[key]["cluster"] for key in ids])
        local = {int(v): j for j, v in enumerate(idx)}
        donors = np.array([local[index[items[i]["donor_id"]]] for i in idx])
        probes = {}
        for layer in sorted({layer for _, layer in readers}):
            true, mis, folds = grouped_probe(activations[layer][idx], y, groups, donors)
            probes[layer] = true
            pc = {"feature": feature, "class": spec["class"], "domain": spec["domain"], "reader": "probe", "layer": layer,
                  "n_total": len(idx), "missing": 0, **_measure(true, mis, y, groups)}
            pc["status"] = "DECODABLE" if pc["true"]["auroc"] >= .85 else "NOT DECODABLE"
            cells.append(pc)
            oof.extend({"id": key, "feature": feature, "layer": layer, "true": float(true[j]), "mismatched": float(mis[j])} for j, key in enumerate(ids))
            if export_dev:
                dev = [i for i, it in enumerate(items) if it["feature"] == feature and lookup[it["id"]]["split"] == "dev"]
                dy = np.array([lookup[items[i]["id"]]["value"] == spec["values"][0] for i in dev], int)
                try:
                    fitted = fit_direction(activations[layer][dev], dy)
                except ValueError as exc:
                    if "degenerate dev probe direction" not in str(exc):
                        raise
                    direction_metadata.append({"feature": feature, "class": spec["class"], "domain": spec["domain"],
                        "layer": layer, "fit_split": "dev", "status": "NOT DECODABLE",
                        "reason": "zero dev probe coefficient; no direction exported", "probe_cv_folds": folds})
                    continue
                key = f"{feature}__L{layer}"
                direction_arrays[key + "__unit"] = fitted.pop("direction")
                direction_arrays[key + "__coef"] = fitted.pop("raw_coefficient")
                test_gap = float((activations[layer][idx][y == 1].mean(0) - activations[layer][idx][y == 0].mean(0)) @ direction_arrays[key + "__unit"])
                direction_metadata.append({"feature": feature, "class": spec["class"], "domain": spec["domain"], "layer": layer,
                    "positive_value": spec["values"][0], "negative_value": spec["values"][1], "array_prefix": key,
                    "test_class_mean_projection_gap": test_gap, "probe_cv_folds": folds, **fitted})
        for reader, layer in readers:
            raw = [[scoremap[(key, reader, layer, arm)] for key in ids] for arm in ("true", "mismatched")]
            missing = sum(r["status"] != "COMPLETE" for arm in raw for r in arm)
            cell = {"feature": feature, "class": spec["class"], "domain": spec["domain"], "reader": reader, "layer": layer,
                    "n_total": len(idx), "n_clusters": len(set(groups)), "missing": missing,
                    "probe_auroc": auroc_labels(probes[layer], y)}
            if missing:
                cell.update(status=gate(cell["probe_auroc"], None, complete=False), true=None, mismatched=None)
            else:
                true, mis = [np.array([np.mean(r["scores"]) for r in arm]) for arm in raw]
                cell.update(_measure(true, mis, y, groups, probes[layer]))
                cell["status"] = gate(cell["probe_auroc"], cell["mismatched"]["auroc"])
            cells.append(cell)
    return cells, oof, direction_arrays, direction_metadata


def _activation_manifest(root, layers, order_file):
    records = []
    for layer in layers:
        path = root / f"acts{layer}.npy"
        values = np.load(path, mmap_mode="r", allow_pickle=False)
        records.append({"layer": layer, "path": str(path.resolve()), "sha256": P.sha(path),
                        "shape": list(values.shape), "dtype": str(values.dtype)})
    return {"files": records, "item_order_path": str(order_file.resolve()), "item_order_sha256": P.sha(order_file)}


def _load_activations(root, layers, n):
    result = {}
    for layer in layers:
        h = np.load(root / f"acts{layer}.npy", allow_pickle=False)
        if h.ndim != 2 or h.shape[0] != n or not np.isfinite(h).all():
            raise ValueError("activation shape/finiteness mismatch")
        result[layer] = h
    return result


def _w1_handoff_line(w1):
    conditions = []
    for rule in ("i", "ii", "iii"):
        rate = w1["conditions"][rule]
        status = "PASS" if w1["conditions_pass"][rule] else "FAIL"
        denominator_note = ", NOT EVALUABLE" if rate["n"] == 0 else ""
        conditions.append(f"({rule}) {status} ({rate['k']}/{rate['n']}{denominator_note})")
    return f"HANDOFF W1: {'; '.join(conditions)}; verdict={w1['status']}."


def _finish(out, data, oof, arrays, metadata, activation_manifest):
    out.mkdir(parents=True, exist_ok=False)
    P.jsonl(out / "probe.oof.jsonl", oof)
    P.dump(out / "metrics.json", data)
    P.dump(out / "activations.json", activation_manifest)
    P.dump(out / "probe_directions.json", {"rows": metadata, "fit_split": "dev", "vectors": "probe_directions.npz"})
    np.savez_compressed(out / "probe_directions.npz", **arrays)
    names = ["metrics.json", "probe.oof.jsonl", "activations.json", "probe_directions.json", "probe_directions.npz"]
    if data.get("experiment") == "W1":
        w1 = data["w1"]
        keyed = _cells_by_key(data["rows"])
        P.dump(out / "rule_i_rows.json", {
            "experiment": "W1", "section": 70, "rule": "i",
            "selection": "Exact metrics.json.w1.blindspot_features; independent of conditions (ii)/(iii) and overall verdict",
            "features": w1["blindspot_features"],
            "rows": [keyed[(feature, "olens", 44)] for feature in w1["blindspot_features"]],
            "condition": w1["conditions"]["i"], "w1_verdict": w1["status"],
            "input_seal_sha256": data["input_seal_sha256"], "reader_seals": data["reader_seals"],
            "metrics_sha256": P.sha(out / "metrics.json"),
            "probe_directions": "probe_directions.json", "activations": "activations.json",
        })
        (out / "HANDOFF.txt").write_text(_w1_handoff_line(w1) + "\n")
        names += ["rule_i_rows.json", "HANDOFF.txt"]
    P.dump(out / "ANALYSIS_SEAL.json", {"status": "ANALYSIS_SEALED_AFTER_SCORE_VERIFICATION", "files": {name: P.sha(out / name) for name in names}})


def analyse(a):
    """W1 entry point called by run.py. All integrity checks precede label reading."""
    bank, target, nla, out = map(Path, (a.bank, a.target, a.nla, a.out))
    input_seal = P.verify(bank, "INPUT_SEAL.json")
    if not {"items.input.jsonl", "templates.json", "provenance.json"} <= set(input_seal["files"]):
        raise ValueError("input seal lacks required file coverage")
    _sealed(target, ("scores.target.jsonl", "items.order.json", "acts42.npy", "acts44.npy", "provenance.target.json"), "SCORES")
    _sealed(nla, ("scores.nla.jsonl", "provenance.nla.json"), "SCORES")
    tp = json.loads((target / "provenance.target.json").read_text())
    np_ = json.loads((nla / "provenance.nla.json").read_text())
    bank_sha, target_sha, nla_sha = P.sha(bank / "INPUT_SEAL.json"), P.sha(target / "SCORE_SEAL.json"), P.sha(nla / "SCORE_SEAL.json")
    if any(p["input_seal_sha256"] != bank_sha for p in (tp, np_)) or np_["target_score_seal_sha256"] != target_sha:
        raise ValueError("score seal lineage mismatch")
    items = P.rows(bank / "items.input.jsonl")
    if _order(target / "items.order.json") != [it["id"] for it in items]:
        raise ValueError("target activation item order differs from frozen bank")
    templates = json.loads((bank / "templates.json").read_text())
    provenance = json.loads((bank / "provenance.json").read_text())
    experiment = provenance.get("experiment", "W1")
    if experiment not in ("W1", "W1b"):
        raise ValueError("unexpected bank experiment")
    selection = None
    if experiment == "W1b":
        if "manifest.json" not in input_seal["files"]:
            raise ValueError("W1b selection manifest is not sealed")
        selection = validate_selection_receipt(json.loads((bank / "manifest.json").read_text()).get("selection_receipt"))
        candidates = set(selection["section79_features"] + selection.get("section81_features", []))
        if candidates != {f for f, spec in templates.items() if spec.get("kind", "binary") == "binary"}:
            raise ValueError("W1b bank features differ from committed candidates")
    raw = P.rows(target / "scores.target.jsonl") + P.rows(nla / "scores.nla.jsonl")
    scoremap = _grid(raw, items, templates, NATIVE)
    activations = _load_activations(target, (42, 44), len(items))
    lookup, labels_sha = _labels(bank, Path(a.labels), items, templates)
    with P.logged(f"analyse_registered_{experiment.lower()}", extra={"input_seal": bank_sha, "target_seal": target_sha, "nla_seal": nla_sha}):
        cells, oof, arrays, metadata = _analyse_cells(items, lookup, templates, scoremap, activations, NATIVE)
        data = {"experiment": experiment, "rows": cells, "ordinal": _ordinal_metrics(items, lookup, scoremap, templates),
                "operating_details": OPERATING_DETAILS, "labels_sha256": labels_sha, "input_seal_sha256": bank_sha,
                "reader_seals": [target_sha, nla_sha], "unasked_recall": {"status": "PENDING BLINDED JUDGE", "rate": None}}
        if experiment == "W1":
            data["w1"] = adjudicate_w1(cells)
            data["replications"] = replication_comparisons(cells)
        else:
            data["w1b"] = adjudicate_w1b(cells, selection["section79_features"])
            data["selection_receipt"] = selection
            data["section81_descriptive"] = [adjudicate_w1b(cells, [f])["candidates"][0]
                                             for f in selection.get("section81_features", [])]
        _finish(out, data, oof, arrays, metadata, _activation_manifest(target, (42, 44), target / "items.order.json"))
    if experiment == "W1":
        print(_w1_handoff_line(data["w1"]))
    return data


def analyse_sweep(a):
    """W5 scores cover the frozen test-only subset and all six registered layers."""
    bank, sweep, out, w1 = map(Path, (a.bank, a.sweep, a.out, a.w1))
    bank_seal = P.verify(bank, "INPUT_SEAL.json")
    if not {"items.input.jsonl", "templates.json", "provenance.json"} <= set(bank_seal["files"]):
        raise ValueError("input seal lacks required file coverage")
    required = ["scores.sweep.jsonl", "provenance.sweep.json", "items.order.json"] + [f"acts{layer}.npy" for layer in LAYERS]
    _sealed(sweep, required, "SCORES")
    analysis_seal = P.verify(w1, "ANALYSIS_SEAL.json")
    if analysis_seal.get("status") != "ANALYSIS_SEALED_AFTER_SCORE_VERIFICATION" or "metrics.json" not in analysis_seal.get("files", {}):
        raise ValueError("W1 analysis seal must cover the selected blindspot metrics")
    bank_sha = P.sha(bank / "INPUT_SEAL.json")
    if json.loads((sweep / "provenance.sweep.json").read_text())["input_seal_sha256"] != bank_sha:
        raise ValueError("W5/bank seal mismatch")
    baseline = json.loads((w1 / "metrics.json").read_text())
    if baseline["input_seal_sha256"] != bank_sha:
        raise ValueError("W5 and W1 use different frozen banks")
    if "sweep.input.json" not in bank_seal["files"]:
        raise ValueError("W5 subset was not frozen with bank")
    ids = _order(bank / "sweep.input.json")
    if _order(sweep / "items.order.json") != ids:
        raise ValueError("W5 activation item order mismatch")
    itemmap = {it["id"]: it for it in P.rows(bank / "items.input.jsonl")}
    items = [itemmap[key] for key in ids]
    templates = json.loads((bank / "templates.json").read_text())
    readers = [("olens", layer) for layer in LAYERS]
    scoremap = _grid(P.rows(sweep / "scores.sweep.jsonl"), items, templates, readers)
    activations = _load_activations(sweep, LAYERS, len(items))
    lookup, labels_sha = _labels(bank, Path(a.labels), items, templates)
    if any(lookup[key]["split"] != "test" for key in ids):
        raise ValueError("W5 subset contains non-test items")
    with P.logged("analyse_registered_w5", extra={"input_seal": bank_sha, "sweep_seal": P.sha(sweep / "SCORE_SEAL.json")}):
        cells, oof, arrays, metadata = _analyse_cells(items, lookup, templates, scoremap, activations, readers, export_dev=False)
        data = {"rows": cells, "w5": adjudicate_w5(cells, baseline["w1"]["blindspot_features"]),
                "labels_sha256": labels_sha, "input_seal_sha256": bank_sha, "w1_analysis_seal_sha256": P.sha(w1 / "ANALYSIS_SEAL.json"),
                "reader_seals": [P.sha(sweep / "SCORE_SEAL.json")], "operating_details": OPERATING_DETAILS}
        _finish(out, data, oof, arrays, metadata, _activation_manifest(sweep, LAYERS, sweep / "items.order.json"))
    return data
