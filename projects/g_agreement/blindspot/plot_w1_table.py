"""Render Suraj-style descriptive W1 table from the existing sealed supplement."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from . import protocol as P

LABELS = {
    "prose_sentence": "Sentence position in paragraph", "prose_words": "Words in current sentence",
    "prose_budget": "Words remaining under stated limit", "prose_column": "Words on current line",
    "prose_paren": "Inside a parenthesis", "prose_quote": "Open vs closed quotation",
    "prose_topic": "Gardening vs ocean topic", "prose_sentiment": "Positive vs negative sentiment",
    "python_line": "Line position in function body", "python_argument": "First vs later call argument",
    "python_depth": "Bracket nesting depth", "python_indent": "Indentation level",
    "python_string": "Open vs closed string literal", "python_comment": "Comment vs executable code",
    "python_effect": "In-place mutation vs new list", "python_error": "Exception vs normal return",
    "latex_section": "Early vs late document section", "latex_item": "First vs later enumerated item",
    "latex_math": "Inline math vs ordinary text", "latex_brace": "Unclosed brace depth",
    "latex_environment": "Equation vs quotation environment", "latex_fraction": "Numerator vs denominator",
    "latex_subject": "Algebra vs geometry", "latex_role": "Theorem vs worked example",
    "json_field": "First vs later object field", "json_depth": "JSON object nesting depth",
    "json_type": "String vs numeric value", "json_status": "Approved vs rejected request",
    "table_column": "First vs later table column", "table_row": "Early vs late table row",
    "table_role": "Header vs data cell", "table_status": "Approved vs rejected entry",
    "list_index": "First vs later list item", "list_depth": "List nesting depth",
    "list_completed": "Completed tasks above current item", "list_words": "Words in current list item",
    "list_ordered": "Ordered vs bullet list", "list_task": "Checked vs unchecked task",
    "list_priority": "Urgent vs routine task", "list_topic": "Travel vs study topic",
}


def main():
    root = P.ROOT / "results/g_agreement/blindspot/w1/descriptive"
    P.verify(root, "DESCRIPTIVE_SEAL.json")
    data = json.loads((root / "tables.json").read_text())
    assert data["registered_verdict"] == "NOT MET" and len(data["rows"]) == 40
    assert set(LABELS) == {r["feature"] for r in data["rows"]}
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(18, 23), dpi=160)
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(left=.025, right=.975, top=.985, bottom=.02)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 50.2)
    ax.axis("off")
    ax.text(0, 49.7, "Activation readers: our W1 concept table", fontsize=23, weight="bold", va="top")
    ax.text(0, 48.75, "DESCRIPTIVE  •  Qwen3.6-27B  •  registered verdict: NOT MET", fontsize=13, weight="bold", color="#92400e", va="top")
    ax.text(0, 48.05, "84 held-out items per binary row (42 per value); 6 template clusters. Two frozen phrasing contrasts per asked score.", fontsize=11, va="top")
    ax.text(0, 47.43, "NLA / probe at block 42; Oracle, J-lens, logit lens / probe at block 44. Marginal 95% CIs are in the companion tables.", fontsize=11, va="top")
    widths = [5.0, 1.0, 1.3, 1.3, 1.1, 1.1, 1.1, 1.1, 3.0]
    edges = [0]
    for width in widths:
        edges.append(edges[-1] + width)
    total = edges[-1]
    headings = ["Concept", "Domain", "NLA\nprompted", "Oracle\nprompted", "J-lens\nprompted", "Logit\nprompted", "Probe\n42", "Probe\n44", "NLA − Oracle\npaired 95% CI"]
    y = 46.7
    hh, rh, gh = 1.05, .79, .62
    for j, name in enumerate(headings):
        ax.add_patch(Rectangle((edges[j], y-hh), widths[j], hh, facecolor="#e9ede7", edgecolor="#30352f", linewidth=.85))
        ax.text(edges[j]+widths[j]/2, y-hh/2, name, ha="center", va="center", fontsize=11, weight="bold")
    y -= hh
    rows_shown = []
    mark = {"EVALUABLE": "", "DECODABLE": "", "NOT DECODABLE": "†", "NOT EVALUABLE": "‡"}
    for category in ("count-like", "state-like", "semantic"):
        rows = [r for r in data["rows"] if r["class"] == category]
        ax.add_patch(Rectangle((0, y-gh), total, gh, facecolor="#354b45", edgecolor="#30352f", linewidth=.85))
        ax.text(.14, y-gh/2, f"{category.upper()}  ·  {len(rows)} rows", color="white", weight="bold", fontsize=10.5, va="center")
        y -= gh
        for r in rows:
            f = r["feature"]
            cols = [LABELS[f], r["domain"]]
            vals = [None, None]
            gates = [None, None]
            for reader in ("nla", "olens", "jlens", "logit"):
                cell = r["readers"][reader]
                v = cell["auroc"]["auroc"]
                cols.append(f"{v:.2f}{mark[cell['gate']]}")
                vals.append(v)
                gates.append(cell["gate"])
            for layer in ("42", "44"):
                cell = r["probes"][layer]
                v = cell["auroc"]["auroc"]
                cols.append(f"{v:.2f}{mark[cell['gate']]}")
                vals.append(v)
                gates.append(cell["gate"])
            delta = r["nla_minus_oracle"]
            suffix = "" if delta["both_readers_evaluable"] else " §"
            cols.append(f"{delta['difference']:+.3f} [{delta['ci95'][0]:+.3f}, {delta['ci95'][1]:+.3f}]{suffix}")
            vals.append(None)
            gates.append(None)
            for j, content in enumerate(cols):
                face = "#f0f2ef" if j < 2 else "white"
                if vals[j] is not None:
                    scaled = max(0., min(1., (vals[j]-.5)/.5))
                    face = plt.cm.Oranges(.04+.55*scaled)
                ax.add_patch(Rectangle((edges[j], y-rh), widths[j], rh, facecolor=face, edgecolor="#50574f", linewidth=.6))
                if j == 0:
                    ax.text(edges[j]+.12, y-rh/2, content, fontsize=10.5, ha="left", va="center", weight="bold" if f in ("table_column", "prose_paren") else "normal")
                else:
                    ax.text(edges[j]+widths[j]/2, y-rh/2, content, fontsize=10 if j==8 else 11, ha="center", va="center")
            rows_shown.append(f)
            y -= rh
    y -= .48
    ax.text(0, y, "Gate markers", fontsize=11, weight="bold", va="top")
    ax.text(1.65, y, "† probe < 0.85    ‡ mismatched AUROC > 0.60    § one or both readers fail gates; difference is descriptive only.", fontsize=10.5, va="top")
    y -= .57
    ax.text(0, y, "No marker = gate passed. Gates use unrounded scores. Orange runs from chance (0.50) to 1.00; AUROC < 0.50 stays near white.", fontsize=10.5, va="top")
    y -= .8
    ax.text(0, y, "Ordinal levels 1–8  ·  NLA Spearman ρ", fontsize=13, weight="bold", va="top")
    y -= .58
    ordinal_names = {"python_depth_ordinal": "Bracket nesting depth", "table_column_ordinal": "Table column"}
    for r in data["ordinal"]:
        ax.text(.12, y, f"{ordinal_names[r['feature']]}:  {r['rho']:.3f} [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}]     n = {r['n']}; 18 per level; 6 clusters", fontsize=11, va="top")
        y -= .55
    y -= .23
    ax.text(0, y, "Free-readout columns in Suraj’s table", fontsize=13, weight="bold", va="top")
    y -= .58
    labels = [("NLA states it", "NOT SCORED"), ("NLA any of 8", "N/A: W1 used 2"), ("Oracle states it", "NOT SCORED"), ("Oracle exhibits it", "NOT SCORED")]
    for k, (heading, state) in enumerate(labels):
        x = k*total/4
        ax.add_patch(Rectangle((x, y-1.12), total/4, 1.12, facecolor="#f0f3f5", edgecolor="#7b858c", linewidth=.7))
        ax.text(x+total/8, y-.3, heading, fontsize=10.5, weight="bold", ha="center", va="center")
        ax.text(x+total/8, y-.78, state, fontsize=10.5, ha="center", va="center", color="#52616b")
    y -= 1.43
    ax.text(0, y, "Free-response collection is PARTIAL; no blinded recall rate is available. Dashes or unavailable entries must not be read as 0%.", fontsize=10.5, va="top")
    y -= .55
    ax.text(0, y, "Paired CIs: 2,000 joint template-cluster bootstrap resamples, seed 20261023. The reported ~214 s science-cap overrun remains disclosed.", fontsize=10.5, va="top")
    y -= .55
    ax.text(0, y, "Source: sealed W1 descriptive/tables.json  •  all 40 binary rows retained  •  no new analysis or probe fits", fontsize=10, color="#52616b", va="top")
    assert set(rows_shown) == set(LABELS) and len(rows_shown) == 40
    assert y > 0, y
    dest = root / "W1_CONCEPT_TABLE.png"
    with P.logged("w1_suraj_style_render", extra={"status": "DESCRIPTIVE", "source_sha256": P.sha(root / "tables.json")}):
        fig.savefig(dest, dpi=160, facecolor="white", bbox_inches="tight", pad_inches=.22)
    plt.close(fig)
    P.dump(root / "FIGURE_PROVENANCE.json", {"status": "DESCRIPTIVE", "registered_verdict": "NOT MET",
        "source": "tables.json", "source_sha256": P.sha(root / "tables.json"),
        "descriptive_seal_sha256": P.sha(root / "DESCRIPTIVE_SEAL.json"),
        "script_sha256": P.sha(Path(__file__)), "figure": dest.name, "figure_sha256": P.sha(dest),
        "rows": rows_shown, "new_statistics_computed": False,
        "reference": "Suraj exp13 combined concept-by-reader table; separate free-readout availability panel instead of invented recall rates"})
    print(dest)


if __name__ == "__main__":
    main()
