"""Render already computed E6/E5/E8 metrics; no statistical reruns."""
import json
from pathlib import Path
from . import core as K
from projects.g_agreement.blindspot import protocol as P

RUN = 'analysis_5xg04qljqfe472'


def auc(v):
    return f"{v['auroc']:.3f} [{v['lo']:.3f}, {v['hi']:.3f}]"


def rate(v):
    lo, hi = v['ci95_wilson']
    return f"{v['k']}/{v['n']} = {100*v['rate']:.1f}% [{100*lo:.1f}, {100*hi:.1f}]"


def render(experiment):
    out = K.RESULTS/experiment.lower()/RUN
    data = json.loads((out/'metrics.json').read_text())
    rows = data['rows']
    if experiment == 'E6':
        lines = [
            '**Prediction (§93):** Oracle continuations enact structure above chance (roughly AUROC 0.65–0.8) despite weak explicit description.',
            '', '**Did it hold? No evidence for the predicted show-not-say dissociation in this run.** Oracle parentheses and table-column proxies are below chance in the frozen orientation; string is 0.512 and indent/list are exactly 0.500. NLA continued in its descriptive format on all 420 items, so these results do not establish its inability to enact under another interface.',
            '', '# E6 continuation results — EXPLORATORY', '',
            '840 sealed outputs: 5 rows × 84 test items × 2 readers; 42 per value, six held-out template clusters. AUROC uses the frozen proxy, neutral=0.5, fixed orientation and 2,000 cluster resamples. A is the first frozen value and B is the second; for depth/column rows B means deep/later rather than absence.',
            '', 'The event rate below is **proxy score exactly 1**, divided by all 42 outputs in the given state, including neutral outputs. Its intervals are Wilson 95% intervals (descriptive marginal rates, not cluster-adjusted intervals). Mean proxy scores retain partial credit. Neither the event nor the proxy proves valid source continuation.',
            '', '| Row | Reader | A / B | AUROC [95% cluster CI] | A event rate [95% Wilson CI] | B/off-state event rate [95% Wilson CI] | Mean proxy A / B | Neutral A / B |',
            '|---|---|---|---|---|---|---|---|',
        ]
        for r in rows:
            if 'auroc' not in r:
                lines.append(f"| {r['feature']} | {r['reader']} | — | {r['status']} | — | — | — | — |")
                continue
            a, b = r['on_A'], r['off_B']
            lines.append(f"| {r['feature']} | {r['reader']} | {' / '.join(r['values'])} | {auc(r['auroc'])} | {rate(a)} | {rate(b)} | {a['mean_proxy']:.3f} / {b['mean_proxy']:.3f} | {a['neutral_n']} / {b['neutral_n']} |")
        lines += ['', 'Frozen event definitions:']
        lines += [f"- `{f}`: {script}." for f, script in __import__('projects.g_agreement.understand.e6', fromlist=['SCRIPTS']).SCRIPTS.items()]
        lines += ['', '**Format and proxy limits.** Oracle has no scripted refusal marker in 420/420 outputs. NLA has `DESCRIPTIVE_FORMAT_MARKER` in 420/420 outputs (including `<explanation>`), with no explicit refusal marker. Native prompt construction succeeded for both; that does not establish compliance with continuation instructions. Indent proxies saturate at 1 in both states for both readers; Oracle list proxies do too because its native bullet format triggers the rule. These constant rates are uninformative about enactment. No outputs are filtered or rescored.',
                  '', '**GLM E14 comparison** (source: commit `e8b9a22a`, `results/g_agreement/understand/e14/run1/RESULTS.md`): GLM-5.3 RL Oracle closes a parenthesis at 42.5% on-state versus 0.6% off-state (+41.9 pp); SFT 45.1% versus 2.9%. Qwen E6 Oracle is 4.8% versus 19.0% (−14.3 pp). Thus the GLM positive contrast does not reproduce here. This is a comparison point, not a controlled model comparison: E14 uses natural rollout readouts, block 51, many positions and five samples per position; E6 uses W1 synthetic activations, block 44, a continuation request and 32-token greedy output. Scripts/labels also differ, and E14 flags list/table degeneracy. E6 does not include a target next-token ceiling or a new formal state-naming annotation.',
                  '', 'E6(a), previously completed on W1 free descriptions, is separate: Oracle paren AUROC 0.457 [0.336,0.585], table_column 0.467 [0.367,0.586]; other reader/row cells unavailable. Those numbers are not pooled into E6(b).']
    elif experiment == 'E5':
        lines = [
            '**Prediction (§92):** Oracle structure stays near chance under all eight phrasings; meaning stays near ceiling.',
            '', '**Did it hold? Partly. The all-phrasings structure prediction did not hold:** Python bracket depth reaches 0.784 (paraphrase1) and 0.776 (paraphrase2), above the brief’s 0.75 surprise point. Table-column best is 0.713 and parentheses best is 0.598. Oracle meaning remains high (0.853–1.000 across the three rows).',
            '', '# E5 phrasing results — EXPLORATORY', '',
            'Six rows × 84 held-out items; each row has 42/value across six template clusters. All eight frozen phrasings are reported with 2,000 cluster-bootstrap CIs, fixed score orientation. Best phrasing and spread are descriptive selections on the same test set, with selection optimism and no multiplicity correction. J-lens is unsupported for all six rows × eight sequence-query phrasings under the unchanged W1 scorer; no chance values are substituted.',
            '', '| Row | Reader | Best phrasing | Best AUROC | Max − min |', '|---|---|---|---|---|',
        ]
        for r in rows:
            if 'phrasings' in r:
                lines.append(f"| {r['feature']} | {r['reader']} | {r['phrasings'][r['best_phrasing']]['kind']} | {r['best_auroc']:.3f} | {r['spread']:.3f} |")
            else:
                lines.append(f"| {r['feature']} | {r['reader']} | UNSUPPORTED | — | — |")
        lines += ['', '| Row | Reader | Phrasing | AUROC [95% cluster CI] |', '|---|---|---|---|']
        for r in rows:
            for phrasing in r.get('phrasings', []):
                lines.append(f"| {r['feature']} | {r['reader']} | {phrasing['phrasing']}: {phrasing['kind']} | {auc(phrasing)} |")
        lines += ['', 'The NLA is also phrasing-sensitive: its best structural AUROCs are 0.810 (table), 0.899 (parenthesis), 0.861 (depth). This is exploratory best-of-eight performance, not a replacement for the registered W1 verdict or a held-out prompt-selection result.']
    else:
        lines = [
            '**Prediction (§95):** Oracle structure gains are much smaller than meaning gains; the NLA’s attenuation is weaker.',
            '', '**Did it hold? Qualitatively yes in the frozen low-dose range.** Oracle mean signed gains are −0.145 for count-like rows and +0.065 for state-like rows versus +1.885 for semantics. NLA gains are +0.150, +0.158 and +0.508 respectively. This is a descriptive class comparison; the brief specifies no statistical pass threshold. Negative/near-zero denominators make a literal “times lower” ratio unstable, and individual rows vary.',
            '', '# E8 gain curves — EXPLORATORY', '',
            'All 40 W1 binary rows; 40 frozen value-B test recipients/row from six template clusters; doses 0,0.5,1,2,4,8. Each native layer uses its signed dev-only direction scaled by its projected class-mean gap. Low-dose gain is the frozen OLS slope at 0,0.5,1; all-dose slope is also reported. CIs use 2,000 recipient-template-cluster resamples, with no refitting of dev directions or sign flips. Values are asked log-odds per dose, with native reader normalization retained.',
            '', '| Reader | Class | Rows | Mean low-dose gain | Median low-dose gain |', '|---|---|---|---|---|',
        ]
        for r in data['descriptive_class_summaries']:
            lines.append(f"| {r['reader']} | {r['class']} | {r['n_rows']} | {r['mean_low_dose_gain']:+.3f} | {r['median_low_dose_gain']:+.3f} |")
        lines += ['', 'Class summaries weight rows equally; they are not pooled-item estimates or causal class effects. Directions’ scales and readers’ score scales differ, so absolute gains across readers are descriptive.',
                  '', '| Row | Class | Reader | Low-dose gain [95% CI] | All-dose gain [95% CI] | First A-median crossing dose | A reference median | Mean log-odds at α=0,0.5,1,2,4,8 |',
                  '|---|---|---|---|---|---|---|---|']
        for r in rows:
            def gain(key):
                lo, hi = r[key+'_ci95']
                return f"{r[key]:+.3f} [{lo:+.3f}, {hi:+.3f}]"
            crossing = r['dose_reaching_A_median']
            lines.append(f"| {r['feature']} | {r['class']} | {r['reader']} | {gain('low_dose_gain')} | {gain('all_dose_gain')} | {crossing if crossing is not None else 'NOT REACHED ≤8'} | {r['A_reference_median']:+.3f} | {', '.join(f'{v:+.3f}' for v in r['dose_means'])} |")
        lines += ['', 'Crossing is the first observed grid dose whose recipient mean reaches the frozen W1 value-A median (42 A-reference items); no interpolation, extrapolation or outcome-selected linear range. A crossing at 0 means the recipient mean already exceeds that reference. Large-dose reversals/nonlinearity remain visible in the full curves. Low gain does not by itself localize where the reader loses information.']
    lines += ['', 'Provenance: pod `5xg04qljqfe472`, booking `ac397e81`, exact frozen source `19fadde5`. Input/score seals, source hashes and complete grids verified before labels. CPU-only analysis ran once per experiment in requested order E6 → E5 → E8. Pre-registered designs and scoring definitions are exploratory; no registered W1/§84/§87 verdict is changed. E6/E8 use a new CPU reporting adapter for their already-frozen proxy/gain functions; E5 uses its unchanged frozen analyser. No new model inference or paid calls.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    names = ['metrics.json', 'RESULTS.md']
    P.dump(out/'ANALYSIS_SEAL.json', {'status': 'EXPLORATORY_ANALYSIS_COMPLETE', 'experiment': experiment,
           'source_files': {str(p.relative_to(P.ROOT)): P.sha(p) for p in [Path(__file__).resolve(), P.ROOT/'projects/g_agreement/understand/score_analysis.py', P.ROOT/f'projects/g_agreement/understand/{experiment.lower()}.py']},
           'files': {name: P.sha(out/name) for name in names}})


if __name__ == '__main__':
    for experiment in ('E6', 'E5', 'E8'):
        render(experiment)
