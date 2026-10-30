"""DESCRIPTIVE tables from sealed W1; no refits or registered adjudication."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import protocol as P
from .analysis import N_BOOT


def main():
    from mats.metrics import auroc_labels, cluster_bootstrap

    base = P.ROOT / "results/g_agreement/blindspot/w1"
    analysis = base / "analysis"
    bank = P.ROOT / "cache/g_agreement/blindspot/w1-bank-v2"
    assembled = P.ROOT / "cache/g_agreement/blindspot/w1-assembled"
    units = P.ROOT / "cache/g_agreement/blindspot/w1-units"
    out = base / "descriptive"
    if out.exists():
        raise FileExistsError(out)
    original_seal = P.sha(analysis / "ANALYSIS_SEAL.json")
    P.verify(analysis, "ANALYSIS_SEAL.json")
    for unit in ("priority", "remainder_a", "remainder_b"):
        for phase in ("target", "nla"):
            P.verify(units / unit / phase, "SCORE_SEAL.json")
    P.verify(bank, "INPUT_SEAL.json")
    for phase in ("target", "nla"):
        P.verify(assembled / phase, "SCORE_SEAL.json")
    metrics = json.loads((analysis / "metrics.json").read_text())
    assert metrics["w1"]["status"] == "NOT MET"
    label_path = bank / "labels.DO_NOT_STAGE.jsonl"
    assert P.sha(label_path) == metrics["labels_sha256"]
    labels = {r["id"]: r for r in P.rows(label_path)}
    items = P.rows(bank / "items.input.jsonl")
    templates = json.loads((bank / "templates.json").read_text())
    raw = P.rows(assembled / "target/scores.target.jsonl") + P.rows(assembled / "nla/scores.nla.jsonl")
    scoremap = {(r["id"], r["reader"], r["layer"], r["arm"]): r for r in raw}
    cells = {(r["feature"], r["reader"], r["layer"]): r for r in metrics["rows"]}
    sites = (("olens", 44), ("nla", 42), ("jlens", 44), ("logit", 44))
    rows = []
    with P.logged("w1_descriptive_paired_reader_differences", extra={
        "status_label": "DESCRIPTIVE", "n_boot": N_BOOT,
        "resampling": "same test template clusters jointly for NLA and Oracle",
        "analysis_seal_sha256": original_seal,
    }):
        for feature, spec in sorted(templates.items()):
            if spec.get("kind", "binary") != "binary":
                continue
            ids = [it["id"] for it in items if it["feature"] == feature and labels[it["id"]]["split"] == "test"]
            y = np.array([labels[key]["value"] == spec["values"][0] for key in ids], int)
            groups = np.array([labels[key]["cluster"] for key in ids])
            reader_cells = {reader: cells[(feature, reader, layer)] for reader, layer in sites}
            probe_cells = {str(layer): cells[(feature, "probe", layer)] for layer in (42, 44)}
            row = {"feature": feature, "class": spec["class"], "domain": spec["domain"],
                   "n": len(ids), "n_clusters": len(set(groups)), "split": "test",
                   "probes": {layer: {"auroc": cell["true"], "gate": cell["status"]}
                              for layer, cell in probe_cells.items()},
                   "readers": {reader: {"layer": layer, "auroc": reader_cells[reader]["true"],
                                        "mismatched": reader_cells[reader]["mismatched"],
                                        "probe_auroc": reader_cells[reader]["probe_auroc"],
                                        "gate": reader_cells[reader]["status"]}
                               for reader, layer in sites}}
            scores = []
            for reader, layer in (("nla", 42), ("olens", 44)):
                records = [scoremap[(key, reader, layer, "true")] for key in ids]
                if any(r["status"] != "COMPLETE" for r in records):
                    raise ValueError("Incomplete paired scores; no subset may be substituted")
                values = np.array([np.mean(r["scores"]) for r in records])
                assert np.isclose(auroc_labels(values, y), reader_cells[reader]["true"]["auroc"], atol=1e-12, rtol=0)
                scores.append(values)
            nla, oracle = scores
            point = auroc_labels(nla, y) - auroc_labels(oracle, y)
            ci = cluster_bootstrap(
                lambda i: auroc_labels(nla[i], y[i]) - auroc_labels(oracle[i], y[i]),
                groups, n_boot=N_BOOT, seed=P.SEED,
            )
            row["nla_minus_oracle"] = {"difference": point, "ci95": list(ci),
                "n": len(ids), "n_clusters": len(set(groups)), "status": "DESCRIPTIVE",
                "both_readers_evaluable": all(reader_cells[r]["status"] == "EVALUABLE" for r in ("olens", "nla"))}
            rows.append(row)

        semantic = []
        for row in rows:
            if row["class"] != "semantic":
                continue
            cell = row["readers"]["olens"]
            delta = cell["auroc"]["auroc"] - cell["probe_auroc"]
            result = "EXCLUDED" if cell["gate"] != "EVALUABLE" else "PASS" if abs(delta) <= .10 + 1e-12 else "FAIL"
            semantic.append({"feature": row["feature"], "gate": cell["gate"],
                             "oracle_minus_probe": delta, "rule_iii_row_status": result})
        ordinal = []
        for measured in metrics["ordinal"]:
            spec = templates[measured["feature"]]
            local = [r for r in labels.values() if r["feature"] == measured["feature"] and r["split"] == "test"]
            levels = sorted(set(int(r.get("level", r["value"])) for r in local))
            assert levels == list(range(1, 9))
            ordinal.append({**measured, "class": spec["class"], "domain": spec["domain"],
                "levels": levels, "n_per_level": {str(k): sum(int(r.get("level", r["value"])) == k for r in local) for k in levels},
                "gate": "NOT APPLICABLE: frozen ordinal design has no binary probe/mismatch gate",
                "auroc": None, "auroc_note": "No binary AUROC or NLA-minus-Oracle AUROC defined; no new binarisation introduced."})
        data = {"status": "DESCRIPTIVE", "registered_verdict": "NOT MET", "rows": rows,
                "replications": metrics["replications"], "ordinal": ordinal, "semantic_rule_iii": semantic,
                "provenance": {"analysis_seal_sha256": original_seal,
                    "metrics_sha256": P.sha(analysis / "metrics.json"), "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
                    "labels_sha256": metrics["labels_sha256"], "seed": P.SEED, "n_boot": N_BOOT,
                    "script_sha256": P.sha(Path(__file__)), "vendored_revision": "2e98a5db5d4c810e48057917a5a3b0f74ec184ec"},
                "method": "Existing marginal CIs copied unchanged. Paired AUROC difference uses the same complete test items, frozen mean of two phrasings and A-positive signs, with 2000 joint template-cluster percentile bootstrap resamples and seed 20261023. All 40 rows retained, including gated cells; gates copied unchanged. No probe refits, new item selection, new gates or multiplicity correction. Ordinal metrics copied unchanged."}
        assert len(rows) == 40 and len(ordinal) == 2
        assert sum(r["rule_iii_row_status"] == "PASS" for r in semantic) == 6
        assert sum(r["rule_iii_row_status"] == "FAIL" for r in semantic) == 3
        assert sum(r["rule_iii_row_status"] == "EXCLUDED" for r in semantic) == 1
        out.mkdir()
        P.dump(out / "tables.json", data)
        write_report(out / "TABLES.md", data)
        P.verify(analysis, "ANALYSIS_SEAL.json")
        assert P.sha(analysis / "ANALYSIS_SEAL.json") == original_seal
        names = ("tables.json", "TABLES.md")
        P.dump(out / "DESCRIPTIVE_SEAL.json", {"status": "DESCRIPTIVE", "registered_verdict": "NOT MET",
            "analysis_seal_sha256": original_seal, "script_sha256": P.sha(Path(__file__)),
            "files": {name: P.sha(out / name) for name in names}})
    print(f"DESCRIPTIVE: {len(rows)} binary rows, {len(ordinal)} ordinal rows; original NOT MET verdict and analysis seal unchanged.")


def fmt(value):
    if value is None:
        return "NA"
    if "auroc" in value:
        return f"{value['auroc']:.3f} [{value['lo']:.3f}, {value['hi']:.3f}]"
    return f"{value['difference']:+.3f} [{value['ci95'][0]:+.3f}, {value['ci95'][1]:+.3f}]"


def write_report(path, data):
    lines = ["# W1 per-row tables — DESCRIPTIVE", "", "**Registered §70 verdict remains NOT MET.** All results below are DESCRIPTIVE; no registered result is revised.", "", data["method"], "",
        "Reported n is held-out test n (42 A + 42 B per binary row), with six template clusters. Entries show AUROC [95% CI]. The probe is shown at both trained sites: block 44 for Oracle/J/logit and block 42 for NLA. Paired intervals describe **AUROC(NLA at 42) − AUROC(Oracle at 44)**, not the mean difference of raw log-odds.", "",
        "## Binary rows — DESCRIPTIVE", "",
        "Gates are reader-specific and retain the frozen thresholds: probe ≥ 0.85 and mismatched AUROC ≤ 0.60. In the gate column the order is Oracle/NLA/J/logit: P = EVALUABLE (passed both), D = NOT DECODABLE, E = NOT EVALUABLE. Gated AUROCs and their differences are still displayed descriptively and do not become eligible evidence. Exact mismatched AUROCs/CIs and unrounded values are in `tables.json`.", "",
        "| Row | Class | Domain | n | Probe 44 | Probe 42 | Oracle 44 | NLA 42 | J 44 | Logit 44 | NLA − Oracle, paired | Gates O/N/J/L |",
        "|---|---|---|---:|---|---|---|---|---|---|---|---|"]
    codes = {"EVALUABLE": "P", "NOT DECODABLE": "D", "NOT EVALUABLE": "E"}
    for r in data["rows"]:
        cols = [r["feature"], r["class"], r["domain"], str(r["n"]), fmt(r["probes"]["44"]["auroc"]), fmt(r["probes"]["42"]["auroc"])]
        cols += [fmt(r["readers"][reader]["auroc"]) for reader in ("olens", "nla", "jlens", "logit")]
        cols += [fmt(r["nla_minus_oracle"]), "/".join(codes[r["readers"][reader]["gate"]] for reader in ("olens", "nla", "jlens", "logit"))]
        lines.append("| " + " | ".join(cols) + " |")
    lines += ["", "## Fresh replication rows vs Suraj's pilot — DESCRIPTIVE", "",
        "Pilot numbers are the point estimates recorded in BRIEF_BLINDSPOT §70/pilot paragraph. Pilot n and CIs were not supplied; pilot-to-fresh difference CIs cannot be reconstructed. Fresh n = 84 and six clusters for each row. Each fresh result is AUROC [95% CI]. No pilot probe or logit result is supplied.", "",
        "| Row | Pilot Oracle | Fresh Oracle | Pilot NLA | Fresh NLA | Pilot J | Fresh J | Fresh NLA − Oracle, paired |",
        "|---|---:|---|---:|---|---:|---|---|"]
    for feature in ("table_column", "prose_paren"):
        r = next(r for r in data["rows"] if r["feature"] == feature)
        pilot = {p["reader"]: p["pilot_auroc"] for p in data["replications"] if p["feature"] == feature}
        cols = [feature]
        for reader in ("olens", "nla", "jlens"):
            cols += [f"{pilot[reader]:.2f}", fmt(r["readers"][reader]["auroc"])]
        cols += [fmt(r["nla_minus_oracle"])]
        lines.append("| " + " | ".join(cols) + " |")
    lines += ["", "## Ordinal levels 1–8 — DESCRIPTIVE", "",
        "Spearman ρ relates NLA block-42 mean paired log-odds to level. These are the original sealed ordinal metrics and CIs, not a new fit. Ordinal rows have no registered binary AUROC/probe/mismatch gate, so binary AUROCs and NLA − Oracle AUROC are undefined. No binarisation has been introduced.", "",
        "| Row | Class | Domain | Test n | Clusters | Levels | n per level | NLA Spearman ρ [95% CI] | Frozen ≥0.6 label |",
        "|---|---|---|---:|---:|---|---:|---|---|"]
    for r in data["ordinal"]:
        lines.append(f"| {r['feature']} | {r['class']} | {r['domain']} | {r['n']} | {r['n_clusters']} | 1–8 | 18 | {r['rho']:.3f} [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}] | {r['status']} |")
    lines += ["", "## Semantic rows failing rule (iii) — DESCRIPTIVE", "",
        "The frozen rule uses **absolute** distance ≤ 0.10 from the block-44 probe. Of nine Oracle-evaluable semantic rows, six pass and these three fail:", "",
        "| Row | Probe 44 [95% CI] | Oracle 44 [95% CI] | Oracle − probe | Reason |", "|---|---|---|---:|---|"]
    for s in data["semantic_rule_iii"]:
        if s["rule_iii_row_status"] != "FAIL":
            continue
        r = next(r for r in data["rows"] if r["feature"] == s["feature"])
        reason = "Oracle below probe by >0.10" if s["oracle_minus_probe"] < 0 else "Oracle above probe by >0.10; absolute-distance rule"
        lines.append(f"| {s['feature']} | {fmt(r['probes']['44']['auroc'])} | {fmt(r['readers']['olens']['auroc'])} | {s['oracle_minus_probe']:+.6f} | {reason} |")
    lines += ["", "`python_effect` is excluded from the rule-(iii) denominator: block-44 probe AUROC 0.849206 < 0.85 (NOT DECODABLE). It is not counted as a semantic failure. `list_topic` fails because the Oracle exceeds its probe by 0.104308; this follows the registered absolute-distance rule, not an underperformance criterion.", "",
        "## Provenance and limits — DESCRIPTIVE", "",
        f"Original analysis seal SHA256: `{data['provenance']['analysis_seal_sha256']}`. Marginal metrics, replication pilot values, gates and ordinal estimates are copied from `../analysis/metrics.json`; paired reader differences are newly computed from the same sealed asked scores, under the existing bootstrap convention. No model/API calls or GPU work. The approximately 214 s science-cap overrun and PARTIAL free-response recall status remain disclosed in `../COMPUTE_DEVIATION.json` and `../free_response_status.json`. These tables do not infer recall rates or change the registered verdict.", ""]
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
