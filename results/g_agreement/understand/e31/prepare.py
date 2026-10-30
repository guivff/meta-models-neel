"""E31(i), 2026-10-25: freeze local-cue classifiers before any E15 score join.

CPU only. The executable requires a READY, hashed protocol with an explicitly
resolved token boundary. It never opens E15 continuation scores or activations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
ROWS = ["prose_paren", "prose_quote", "python_string", "python_indent",
        "python_depth", "list_depth", "table_role"]
E1B_RECIPE_SHA256 = "1f0daa7de80b181d5489e9d32ab7513e724a935a1889957291b5f258a9711a07"
SKLEARN_VERSION = "1.9.1"
VECTOR_PARAMS = dict(analyzer="char", ngram_range=(1, 4), lowercase=False,
                     min_df=1, norm="l2", use_idf=True, smooth_idf=True,
                     sublinear_tf=False)
CLASSIFIER_PARAMS = dict(C=1., penalty="l2", solver="lbfgs", max_iter=2000,
                         tol=1e-4, random_state=20261023)
INPUT_FILES = ("items.input.jsonl", "reference.input.jsonl", "plan.json", "pairs.json")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _invalid_constant(value):
    raise ValueError("nonfinite JSON constant")


def loads(text):
    return json.loads(text, object_pairs_hook=_object, parse_constant=_invalid_constant)


def read(path):
    return loads(Path(path).read_text())


def read_jsonl(path):
    lines = Path(path).read_text().splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise ValueError("empty JSONL or blank record")
    return [loads(line) for line in lines]


def _relative(base, name):
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("expected safe relative path")
    path = (Path(base) / rel).resolve()
    if not path.is_relative_to(Path(base).resolve()):
        raise ValueError("path escapes sealed directory")
    return path


def _check_hash(path, expected):
    if not isinstance(expected, str) or len(expected) != 64 or sha(path) != expected:
        raise ValueError("hash mismatch: " + str(path))


def verify_files(base, files):
    if not isinstance(files, dict) or not files:
        raise ValueError("empty file manifest")
    for name, digest in files.items():
        _check_hash(_relative(base, name), digest)


def validate_protocol(protocol, root=ROOT):
    if protocol.get("status") != "READY":
        raise ValueError("protocol is not READY")
    if protocol.get("suffix_slice") not in ("include_read", "exclude_read"):
        raise ValueError("explicit resolved suffix_slice required")
    if protocol.get("rows") != ROWS:
        raise ValueError("exact seven ordered E15-valid rows required")
    if protocol.get("e1b_recipe_sha256") != E1B_RECIPE_SHA256:
        raise ValueError("wrong E1b recipe")
    sources = protocol.get("source_files")
    if not isinstance(sources, dict) or "results/g_agreement/understand/e31/prepare.py" not in sources:
        raise ValueError("preparation source must be bound by protocol")
    if any(not name.startswith("results/g_agreement/understand/e31/") or not name.endswith(".py") for name in sources):
        raise ValueError("protocol source paths must be E31 Python files relative to ROOT")
    verify_files(root, sources)
    tokenizer = protocol.get("tokenizer_files")
    if not isinstance(tokenizer, dict) or "tokenizer.json" not in tokenizer:
        raise ValueError("pinned tokenizer.json required")


def suffix_ids(item, mode):
    """Slice original token IDs; neither re-tokenize nor add a diagnostic arm."""
    if mode not in ("include_read", "exclude_read"):
        raise ValueError("unresolved token boundary")
    ids = item["ids"]
    pos = item["meta"]["read_position"]
    if not isinstance(ids, list) or not ids or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError("invalid original token IDs")
    if type(pos) is not int or pos != len(ids) - 1:
        raise ValueError("W1 read position is not the last original token")
    end = pos + (mode == "include_read")
    if end < 4:
        raise ValueError("fewer than four tokens in frozen suffix")
    result = ids[end - 4:end]
    if len(result) != 4:
        raise ValueError("suffix must contain exactly four tokens")
    return result


def confidence(p_a):
    p = np.asarray(p_a, dtype=float)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("invalid class-A probability")
    return np.abs(p - (1. - p))


def assign_strata(p_a, cutoff):
    if not np.isfinite(cutoff) or not 0 <= cutoff <= 1:
        raise ValueError("invalid frozen cutoff")
    return np.where(confidence(p_a) > cutoff, "informative", "uninformative").tolist()


def fit_row(dev_text, dev_y, test_text):
    """Exact E1b estimator; only dev enters fit, including vocabulary and IDF."""
    import sklearn
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    if sklearn.__version__ != SKLEARN_VERSION:
        raise ValueError("use original E1b sklearn " + SKLEARN_VERSION)
    y = np.asarray(dev_y)
    if y.ndim != 1 or len(y) != len(dev_text) or set(y.tolist()) != {0, 1}:
        raise ValueError("both binary dev classes required")
    vectorizer = TfidfVectorizer(**VECTOR_PARAMS)
    x = vectorizer.fit_transform(dev_text)
    classifier = LogisticRegression(**CLASSIFIER_PARAMS)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.simplefilter("error", ConvergenceWarning)
        classifier.fit(x, y.astype(int))
    if classifier.classes_.tolist() != [0, 1]:
        raise ValueError("positive class must be A=1")
    dev_p = classifier.predict_proba(x)[:, 1]
    test_p = classifier.predict_proba(vectorizer.transform(test_text))[:, 1]
    confidence(dev_p)
    confidence(test_p)
    model = {"vectorizer_params": {**VECTOR_PARAMS, "ngram_range": [1, 4]},
             "classifier_params": CLASSIFIER_PARAMS,
             "vocabulary": vectorizer.vocabulary_, "idf": vectorizer.idf_.tolist(),
             "coef": classifier.coef_.tolist(), "intercept": classifier.intercept_.tolist(),
             "classes": classifier.classes_.tolist(), "n_iter": classifier.n_iter_.tolist(),
             "sklearn_version": sklearn.__version__,
             "warnings": [{"category": w.category.__name__, "message": str(w.message)} for w in caught]}
    return model, dev_p, test_p


def restored_probabilities(model, text):
    """Read plain fitted arrays, without unsafe pickle or a second fit."""
    from scipy.special import expit
    from sklearn.feature_extraction.text import TfidfVectorizer
    params = dict(model["vectorizer_params"])
    params["ngram_range"] = tuple(params["ngram_range"])
    vectorizer = TfidfVectorizer(**params, vocabulary=model["vocabulary"])
    vectorizer.idf_ = np.asarray(model["idf"], dtype=float)
    if model["classes"] != [0, 1]:
        raise ValueError("model class orientation changed")
    coef = np.asarray(model["coef"], dtype=float)
    intercept = np.asarray(model["intercept"], dtype=float)
    if coef.shape != (1, len(model["vocabulary"])) or intercept.shape != (1,):
        raise ValueError("fitted model dimensions changed")
    p = expit(np.asarray(vectorizer.transform(text) @ coef.T).ravel() + intercept[0])
    confidence(p)
    return p


def _index(rows, name):
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty " + name)
    out = {}
    for row in rows:
        key = row.get("id")
        if not isinstance(key, str) or not key or key in out:
            raise ValueError("duplicate or invalid ID in " + name)
        out[key] = row
    return out


def validate_membership(w1, templates, items, references, labels, e15_plan):
    """Check the full eight-row E15 identity grid, then select its seven valid rows."""
    bank = _index(w1, "W1")
    targets = _index(items, "E15 test")
    refs = _index(references, "E15 dev")
    lab = _index(labels, "E15 labels")
    features = e15_plan["features"]
    if len(features) != 8 or set(features) != set(ROWS) | {"table_column"}:
        raise ValueError("unexpected E15 feature grid")
    if set(targets) & set(refs) or set(lab) != set(targets) | set(refs):
        raise ValueError("E15 ID/label scope mismatch")
    for split, grid in (("dev", refs), ("test", targets)):
        if len(grid) != 672 or Counter(r["feature"] for r in grid.values()) != Counter({f: 84 for f in features}):
            raise ValueError("E15 requires 84 items per row per split")
        for key, item in grid.items():
            if key not in bank or item["feature"] != bank[key]["feature"]:
                raise ValueError("E15 item does not match W1")
            if any(lab[key].get(k) != bank[key].get(k) for k in ("id", "feature", "split", "cluster", "value")):
                raise ValueError("E15 labels do not match original W1")
            if lab[key]["split"] != split:
                raise ValueError("dev/test split mismatch")
            if split == "dev" and item["ids"] != bank[key]["ids"]:
                raise ValueError("E15 dev tokens differ from original W1")
    selected = []
    for feature in ROWS:
        values = templates[feature]["values"]
        if len(values) != 2 or len(set(values)) != 2 or values != e15_plan["values"][feature]:
            raise ValueError("class A/B orientation mismatch")
        clusters = {}
        for split, grid in (("dev", refs), ("test", targets)):
            group = [bank[key] for key in grid if bank[key]["feature"] == feature]
            original_ids = {r["id"] for r in w1 if r["feature"] == feature and r["split"] == split}
            if {r["id"] for r in group} != original_ids:
                raise ValueError("E15 subset is not the complete original W1 split")
            if Counter(r["value"] for r in group) != Counter({values[0]: 42, values[1]: 42}):
                raise ValueError("unbalanced or unexpected W1 values")
            counts = Counter(r["cluster"] for r in group)
            if len(counts) != 6 or set(counts.values()) != {14}:
                raise ValueError("expected six complete template clusters per split")
            clusters[split] = set(counts)
            selected.extend(group)
        if clusters["dev"] & clusters["test"]:
            raise ValueError("template-cluster leakage")
    if len(selected) != 1176:
        raise ValueError("expected 588 dev plus 588 test items")
    return selected


def load_inputs(args, protocol):
    """Authenticate source/input manifests before loading any label-bearing bank."""
    validate_protocol(protocol)
    w1 = Path(args.w1_bank)
    stage = Path(args.e15_stage)
    metrics_path = Path(args.e15_metrics)
    tokenizer = Path(args.tokenizer)
    input_paths = {
        "w1_items_sha256": w1 / "items.DO_NOT_STAGE.jsonl",
        "w1_templates_sha256": w1 / "templates.json",
        "e15_input_seal_sha256": stage / "INPUT_SEAL.json",
        "e15_metrics_seal_sha256": metrics_path.parent / "ANALYSIS_SEAL.json",
        "e15_labels_sha256": Path(args.e15_labels),
    }
    for key, path in input_paths.items():
        _check_hash(path, protocol[key])
    verify_files(tokenizer, protocol["tokenizer_files"])
    input_seal = read(stage / "INPUT_SEAL.json")
    if input_seal.get("status") != "E15_FROZEN_BEFORE_ANY_REFERENCE_OR_READER_SCORING":
        raise ValueError("original frozen E15 input seal required")
    relevant = {name: input_seal["files"][name] for name in INPUT_FILES}
    verify_files(stage, relevant)
    metrics_seal = read(metrics_path.parent / "ANALYSIS_SEAL.json")
    if metrics_seal.get("status") != "E15_ANALYSIS_COMPLETE" or metrics_path.name != "metrics.json":
        raise ValueError("complete original E15 metrics seal required")
    verify_files(metrics_path.parent, metrics_seal["files"])
    if metrics_path.name not in metrics_seal["files"]:
        raise ValueError("E15 metrics absent from seal")
    plan = read(stage / "plan.json")
    if plan["W1_full_items_sha256"] != protocol["w1_items_sha256"] or plan["labels_sha256"] != protocol["e15_labels_sha256"]:
        raise ValueError("E15 plan lineage mismatch")
    metrics = read(metrics_path)
    if metrics["labels_sha256"] != protocol["e15_labels_sha256"]:
        raise ValueError("E15 metrics label lineage mismatch")
    if metrics["score_seal_sha256"] != protocol["e15_score_seal_sha256"]:
        raise ValueError("E15 metrics score-seal lineage mismatch")
    eligible = [r["feature"] for r in metrics["rows"] if r["valid_pairs"]]
    if (eligible != ROWS or len(metrics["rows"]) != 8
            or {r["feature"] for r in metrics["rows"]} != set(ROWS) | {"table_column"}
            or any(r["valid_pairs"] != [0, 1] for r in metrics["rows"] if r["valid_pairs"])):
        raise ValueError("frozen seven-row/two-valid-pair mask changed")
    # All hashes and source seals above pass before labels/W1 items are parsed.
    bank = read_jsonl(input_paths["w1_items_sha256"])
    templates = read(input_paths["w1_templates_sha256"])
    labels = read_jsonl(input_paths["e15_labels_sha256"])
    selected = validate_membership(bank, templates, read_jsonl(stage / "items.input.jsonl"),
                                   read_jsonl(stage / "reference.input.jsonl"), labels, plan)
    provenance = {"input_hashes": {key: protocol[key] for key in input_paths},
                  "verified_e15_input_files": relevant,
                  "e15_metrics_sha256": sha(metrics_path),
                  "e15_score_seal_sha256": protocol["e15_score_seal_sha256"],
                  "tokenizer_files": protocol["tokenizer_files"],
                  "activation_files_not_read_or_verified": ["acts42.npy", "acts44.npy"],
                  "e15_continuation_scores_read": False}
    return selected, templates, provenance


def _write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def prepare(args):
    import sklearn
    import transformers
    from transformers import PreTrainedTokenizerFast
    protocol_path = Path(args.protocol)
    protocol = read(protocol_path)
    out = Path(args.out)
    if out.exists():
        raise ValueError("freeze output exists; no overwrite or repeat")
    selected, templates, provenance = load_inputs(args, protocol)
    # Reserve an exclusive run directory before the first real fit.
    out.mkdir(parents=True, exist_ok=False)
    (out / "cache").mkdir()
    with (out / "protocol.json").open("xb") as stream:
        stream.write(protocol_path.read_bytes())
    protocol_sha256 = sha(protocol_path)
    _write(out / "STARTED.json", {"protocol_sha256": protocol_sha256,
                                  "created_at": datetime.now(timezone.utc).isoformat()})
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=str(Path(args.tokenizer) / "tokenizer.json"))
    models, assignments, summaries = {}, [], []
    for feature in ROWS:
        split_items = {split: [r for r in selected if r["feature"] == feature and r["split"] == split]
                       for split in ("dev", "test")}
        texts = {split: [tokenizer.decode(suffix_ids(r, protocol["suffix_slice"]),
                                         skip_special_tokens=False, clean_up_tokenization_spaces=False)
                         for r in rows] for split, rows in split_items.items()}
        positive = templates[feature]["values"][0]
        dev_y = [int(r["value"] == positive) for r in split_items["dev"]]
        model, dev_p, test_p = fit_row(texts["dev"], dev_y, texts["test"])
        cutoff = float(np.median(confidence(dev_p)))
        model.update({"feature": feature, "positive_value": positive, "cutoff": cutoff})
        models[feature] = model
        summary = {"feature": feature, "cutoff": cutoff, "n_dev": 84, "n_test": 84,
                   "positive_value": positive, "vocabulary_size": len(model["vocabulary"]),
                   "informative_operator": ">", "stratum_counts": {}}
        for split, probs in (("dev", dev_p), ("test", test_p)):
            strata = assign_strata(probs, cutoff)
            summary["stratum_counts"][split] = dict(Counter(strata))
            for item, p, margin, stratum in zip(split_items[split], probs, confidence(probs), strata):
                assignments.append({"id": item["id"], "feature": feature, "split": split,
                                    "value": item["value"], "label": int(item["value"] == positive),
                                    "p_A": float(p), "margin": float(margin), "stratum": stratum})
        summaries.append(summary)
    _write(out / "cache/models.json", {"rows": models})
    with (out / "cache/strata.jsonl").open("x") as stream:
        for record in assignments:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    cutoffs = {"experiment": "E31(i)", "date": "2026-10-25", "rows": summaries,
               "method": "dev_median_abs_probability_margin", "margin_formula": "abs(p_A-p_B)",
               "dev_fit": "in_sample_all_84_dev_per_row", "informative_operator": ">",
               "ties": "uninformative", "suffix_slice": protocol["suffix_slice"],
               "e15_outcomes_joined": False}
    _write(out / "DEV_CUTOFFS.json", cutoffs)
    provenance.update({"protocol_sha256": protocol_sha256,
                       "source_files": protocol["source_files"], "e1b_recipe_sha256": E1B_RECIPE_SHA256,
                       "package_versions": {"numpy": np.__version__, "sklearn": sklearn.__version__,
                                            "transformers": transformers.__version__},
                       "model_fits": 7, "GPU_hours": 0, "API_calls": 0,
                       "test_labels_used_for_cutoff": False, "continuation_scores_accessed": False,
                       "decoder": "PreTrainedTokenizerFast from pinned tokenizer.json only; skip_special_tokens=False,clean_up_tokenization_spaces=False",
                       "created_at": datetime.now(timezone.utc).isoformat()})
    _write(out / "PROVENANCE.json", provenance)
    names = ["protocol.json", "STARTED.json", "cache/models.json", "cache/strata.jsonl",
             "DEV_CUTOFFS.json", "PROVENANCE.json"]
    _write(out / "STRATA_SEAL.json", {"complete": True,
           "status": "E31_STRATA_FROZEN_BEFORE_E15_OUTCOME_JOIN", "protocol_sha256": protocol_sha256,
           "files": {name: sha(out / name) for name in names},
           "source_files": protocol["source_files"], "input_hashes": provenance["input_hashes"]})
    return {"status": "FROZEN", "rows": 7, "dev_items": 588, "test_items": 588,
            "strata_seal_sha256": sha(out / "STRATA_SEAL.json"), "e15_outcomes_joined": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "w1-bank", "e15-stage", "e15-labels", "e15-metrics", "tokenizer", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
