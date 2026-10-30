"""Export the frozen W1 bank, phrasings, 40-row table and cross-scoring inputs for the mats-nla-workspace team.

Read-only on the sealed W1 cache: no score, label, constant or seed is changed. Every source file is checked
against the seal hashes recorded in the repo before it is read. Run from the repository root:

    .venv/bin/python -m share.export_w1 --cache <path to cache/g_agreement/blindspot/w1-readonly-20261024> \
        --tokenizer <path to the pinned Qwen3.6-27B snapshot dir>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "share"
TABLES = ROOT / "results/g_agreement/blindspot/w1/descriptive/tables.json"
METRICS = ROOT / "results/g_agreement/blindspot/w1/analysis/metrics.json"
W5 = ROOT / "results/g_agreement/blindspot/w5/analysis_53o6cnnsfxqknh/metrics.json"
# Their row names and class names (experiments/17_harden/inputs/README.md); ours map onto them.
CROSS = {"tb_tablecol": ("table_column", {"first": "first", "later": "late"}),
         "tb_paren": ("prose_paren", {"inside": "inside", "outside": "outside"})}
# Frozen phrasing shapes from projects/g_agreement/blindspot/items.py Feature.pairs; checked against templates.json.
SHAPES = {"nla": [("p1", "The current excerpt has {v}."), ("p2", "At the read position, there is {v}.")],
          "olens": [("p1", "- {v}"), ("p2", "- At the read position, the excerpt has {v}.")]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def load_bank(cache):
    bank = cache / "w1-bank-v2"
    seal = json.loads((ROOT / "results/g_agreement/blindspot/w1/freeze/INPUT_SEAL.json").read_text())
    for name, digest in seal["files"].items():
        if (bank / name).exists() and sha(bank / name) != digest:
            raise ValueError("input seal mismatch: " + name)
    labels_sha = json.loads(TABLES.read_text())["provenance"]["labels_sha256"]
    if sha(bank / "labels.DO_NOT_STAGE.jsonl") != labels_sha:
        raise ValueError("labels file differs from the one the sealed analysis used")
    return rows(bank / "items.DO_NOT_STAGE.jsonl"), json.loads((bank / "templates.json").read_text())


def check_tokens(items, tokenizer_dir):
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(Path(tokenizer_dir) / "tokenizer.json"))
    bad = [it["id"] for it in items if tok.encode(it["text"], add_special_tokens=False).ids != it["ids"]]
    return {"checked": len(items), "retokenisation_mismatches": len(bad), "mismatched_ids": bad[:20]}


def bank_rows(items):
    out = []
    for it in items:
        m = it["meta"]
        out.append({"id": it["id"], "row": it["feature"], "split": it["split"], "text": it["text"],
                    "value": it["value"], "level": m.get("level"), "kind": m["kind"], "class": it["class"],
                    "domain": it["domain"], "cluster": m["template_family"], "cluster_hash": it["cluster"],
                    "pair_id": m.get("pair_id"), "read_position": m["read_position"],
                    "token_length": m["token_length"]})
    return out


def phrasings_for(spec, mapping):
    a, b = spec["values"]
    out = {}
    for reader, key in (("nla", "nla"), ("ol", "olens")):
        entries = []
        for (pid, template), frozen in zip(SHAPES[key], spec[key]):
            slots = []
            for cand in frozen:
                head, tail = template.split("{v}")
                if not (cand.startswith(head) and cand.endswith(tail)):
                    raise ValueError("frozen phrasing does not fit the template shape: " + cand)
                slots.append(cand[len(head):len(cand) - len(tail)] if tail else cand[len(head):])
            entries.append({"id": f"guiv_w1_{pid}", "template": template,
                            "fillers": {mapping[a]: slots[0], mapping[b]: slots[1]}})
            for value, cand in zip((a, b), frozen):
                if template.replace("{v}", entries[-1]["fillers"][mapping[value]]) != cand:
                    raise ValueError("round trip failed: " + cand)
        out[reader] = entries
    return out


def table40(templates):
    tables = json.loads(TABLES.read_text())
    sweep = {}
    for c in json.loads(W5.read_text())["rows"]:
        sweep.setdefault(c["feature"], {})[f"{'olens' if c['reader'] == 'olens' else c['reader']}@{c['layer']}"] = {
            "auroc": c["true"]["auroc"] if c.get("true") else None,
            "ci95": [c["true"]["lo"], c["true"]["hi"]] if c.get("true") else None, "gate": c["status"],
            "mismatched_auroc": (c.get("mismatched") or {}).get("auroc")}
    out = []
    for r in tables["rows"]:
        spec = templates[r["feature"]]
        cell = lambda c: {"auroc": c["auroc"]["auroc"], "ci95": [c["auroc"]["lo"], c["auroc"]["hi"]],
                          "gate": c["gate"], "mismatched_auroc": c["mismatched"]["auroc"],
                          "mismatched_ci95": [c["mismatched"]["lo"], c["mismatched"]["hi"]]}
        readers = {f"{name}@{c['layer']}": cell(c) for name, c in r["readers"].items()}
        for layer, p in r["probes"].items():
            readers[f"probe@{layer}"] = {"auroc": p["auroc"]["auroc"], "ci95": [p["auroc"]["lo"], p["auroc"]["hi"]],
                                         "gate": p["gate"]}
        out.append({"row": r["feature"], "class": r["class"], "domain": r["domain"],
                    "generator": f"projects/g_agreement/blindspot/w1_templates.py (feature '{r['feature']}', 12 template families t00-t11, 6 dev / 6 test)",
                    "split": r["split"], "n": r["n"], "n_clusters": r["n_clusters"],
                    "candidate_type": "two-candidate (A vs B)", "values": spec["values"],
                    "candidates": {k: spec[k] for k in ("olens", "nla", "jlens", "logit")},
                    "score": "mean over the two phrasing pairs of log P(A) - log P(B); AUROC with A positive",
                    "readers": readers, "nla_minus_oracle": r["nla_minus_oracle"],
                    "w5_layer_sweep": sweep.get(r["feature"], {})})
    for r in tables["ordinal"]:
        out.append({"row": r["feature"], "class": r["class"], "domain": r["domain"],
                    "candidate_type": "multi-level ordinal (8 levels); scored by Spearman rho of the NLA@42 mean A-minus-B log-odds against level (test split; analysis.py _ordinal_metrics)", "reader": "nla@42",
                    "candidates": {k: templates[r["feature"]].get(k) for k in ("olens", "nla", "jlens", "logit")},
                    **{k: r[k] for k in ("n", "n_clusters", "levels", "rho", "ci95", "status", "gate")}})
    return {"w5_note": "w5_layer_sweep: Oracle lens and probe at blocks 20/28/36/44/52/60 on the same 84 test items "
                       "(W5 §74, fresh sealed score pass on pod 53o6cnnsfxqknh; registered verdict NOT EVALUABLE). "
                       "The W1 columns ('readers') and the W5 columns come from separate passes.",
            "source": {"tables": str(TABLES.relative_to(ROOT)), "metrics": str(METRICS.relative_to(ROOT)),
                       "w5_metrics": str(W5.relative_to(ROOT)),
                       **tables["provenance"]},
            "registered_verdict": tables["registered_verdict"], "rows": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    a = ap.parse_args()
    items, templates = load_bank(a.cache)
    receipt = {"input_seal_verified": True, "labels_sha256_verified": True,
               "tokenisation": check_tokens(items, a.tokenizer)}
    w1 = OUT / "experiments/W1_40row"
    w1.mkdir(parents=True, exist_ok=True)
    with gzip.open(w1 / "items_w1_all.jsonl.gz", "wt") as f:
        for row in bank_rows(items):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    dump(w1 / "phrasings_w1.json", templates)
    dump(w1 / "table_40rows.json", table40(templates))
    xs = OUT / "cross_scoring"
    phrasings = {}
    for row, (feature, mapping) in CROSS.items():
        chosen = [it for it in items if it["feature"] == feature and it["split"] == "test"]
        dump(xs / f"guiv_items_{row}.json", [{"id": it["id"], "text": it["text"], "value": mapping[it["value"]],
                                              "cluster": it["meta"]["template_family"]} for it in chosen])
        dump(xs / f"guiv_items_{row}_dev.json", [{"id": it["id"], "text": it["text"], "value": mapping[it["value"]],
                                                  "cluster": it["meta"]["template_family"]}
                                                 for it in items if it["feature"] == feature and it["split"] == "dev"])
        phrasings[row] = phrasings_for(templates[feature], mapping)
        receipt[row] = {"source_row": feature, "value_map": mapping, "n_test": len(chosen),
                        "counts": {v: sum(mapping[it["value"]] == v for it in chosen) for v in mapping.values()},
                        "clusters": sorted({it["meta"]["template_family"] for it in chosen})}
    dump(xs / "guiv_phrasings.json", phrasings)
    dump(OUT / "EXPORT_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=1))


if __name__ == "__main__":
    main()
