"""Render already-sealed E23 metrics; no fitting, bootstrap, or scientific recomputation."""
from pathlib import Path
from .cpu import ROOT, read, sha, verify, dump

BASE=ROOT/'results/g_agreement/understand/e23'


def render(m, invocation, seal_sha):
    rows=m['rows'];idx={(r['set'],r['feature'],r['tag'],r['arm'],r['measure']):r for r in rows}
    pairs=sorted({(r['set'],r['feature']) for r in rows});arms=('F16','P32','Pfull','Mis','Swap')
    def metric(r):return f"{r['auroc']:.4f} [{r['lo']:.4f}, {r['hi']:.4f}]"
    def contrast(r):return f"{r['estimate']:+.4f} [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}]"
    def verdict(v):return 'MET' if v else 'NOT MET'
    primary=m['rules_primary'];gates=[r for r in m['validity_gates'] if r['tag']==44]
    lines=[
      '**E23 — EXPLORATORY; registered §117 analysis, run once.**', '',
      '**Registered expectations and tests.** Mis must be within AUROC 0.40–0.60 under fixed M1/M2; the in-contract positive controls must reach M1 ≥ 0.80; Swap must be ≤ 0.50 wherever matched F16 is ≥ 0.70. Rules 1–3 distinguish measure, input and item-set explanations; rule 4 compares AR decodability with text; rule 6 tests the E23b factors.', '',
      f"**Primary assessment (tag 44):** rule 1 (measure) {verdict(primary['rule1_measure'])}; rule 2 (input) {verdict(primary['rule2_input'])}. Validity gates pass for {sum(r['interpretable'] for r in gates)}/{len(gates)} row/set assays. E23b names **{m['E23b']['rule6_cause']}** under rule 6. Numerical contrasts below retain their registered flags; failed validity gates limit interpretation.", '',
      '**Main finding.** The registered item-set criterion (rule 3) holds for table-column F16 under M1: S−O = +0.3677 [0.1822, 0.5212], and under M2: +0.3248 [0.1202, 0.5663]. In-contract table-column M1 is 0.6037 on O and 0.9714 on S. Thus a general claim that the reconstructor cannot align table-column information is not supported across these item sets. Rule 4 is met in 26/40 primary cells; it is not a universal result. All 23 applicable Swap checks across both tags pass.', '',
      'Authority: 66af2c0d, clarifications 1–2 including 1642d63e, and the 09:10 correction e347b86a. F16 follows the read token and is in-contract; P32/Pfull are off-contract. M1 projects raw AR outputs on raw-space true-activation directions, with the dev sign fixed. Set S uses its own 40 mine items to train the primary direction; W1-to-S transfer is secondary. No whitening or test sign flip.', '',
      'O = W1: 84 test items per row, with W1 template clusters. S = Suraj: M1/T use 160 select items; M2 uses grouped five-fold CV over all 200 items (each its own cluster). O M2/T share five folds; S T trains on mine and tests on select. CIs are the registered 2,000-resample bootstrap, seed 20261025; contrasts preserve pairing and the different denominators.', '',
      'Mis donors are sampled independently of value within row/set. Swap donors have the opposite value. Both reuse the frozen donor F16 reconstruction; M2 applies the recipient’s F16 fold model without refitting. A donor may be in that model’s training pool, as registered. T is fitted separately for each arm. No new fitting or resampling was performed to produce this report.', '',
      '**M1/M2/T per row × set × arm.** Every entry is AUROC [95% CI]. R4 = MET means M2 ≤ T + 0.05; it is an operational comparison, not an equivalence proof.', '']
    r4={(r['set'],r['feature'],r['tag'],r['arm']):r['AR_adds_nothing_beyond_text'] for r in m['rule4']}
    for tag in (44,40):
        lines += [f'**Tag {tag} — '+('primary.**' if tag==44 else 'secondary.**'),'',
          '| Set | Row | Arm | Contract | M1 | M2 | T | R4 |',
          '|---|---|---|---|---|---|---|---|']
        for dataset,feature in pairs:
            for arm in arms:
                cells=[idx[(dataset,feature,tag,arm,v)] for v in ('M1','M2','T')]
                lines.append(f'| {dataset} | {feature} | {arm} | {cells[0]["contract"]} | '+' | '.join(metric(r) for r in cells)+f' | {verdict(r4[(dataset,feature,tag,arm)])} |')
        lines.append('')
    lines += ['**Rules 1–2.** Each requires Δ ≥ 0.15 and CI lower > 0 in both sets. Rule 1 is F16 M2−M1; rule 2 is M1(P32)−M1(F16). Rule 2’s P32 arm remains off-contract.', '',
      '| Rule | Tag | Set | Δ AUROC [95% CI] | Cell criterion |','|---|---|---|---|---|']
    for r in m['contrasts']:
        if r['rule'] in ('rule1_measure','rule2_input'):
            lines.append(f"| {r['rule']} | {r['tag']} | {r['set']} | {contrast(r)} | {verdict(r['passes'])} |")
    lines += ['', '**Rule 3: item-set contrasts S−O.** A dagger (†) marks the registered cell criterion Δ ≥ 0.15 with CI lower > 0. These are cellwise results, with no new multiple-testing rule. Interpret them subject to rule 5.', '',
      '| Tag | Row | Arm | Contract | Δ M1 [CI] | Δ M2 [CI] | Δ T [CI] |','|---|---|---|---|---|---|---|']
    contrasts={(r['tag'],r['feature'],r['arm'],r['measure']):r for r in m['contrasts'] if r['rule']=='rule3_items'}
    for tag in (44,40):
        for feature in ('table_column','list_index','prose_paren'):
            for arm in arms:
                rr=[contrasts[(tag,feature,arm,v)] for v in ('M1','M2','T')]
                lines.append(f'| {tag} | {feature} | {arm} | {rr[0]["contract"]} | '+' | '.join(contrast(r)+(' †' if r['passes'] else '') for r in rr)+' |')
    lines += ['', '**Rule 5: validity.** Mis numerical AUROCs/CIs are in the main tables. Each Mis gate uses its point AUROC in [0.40, 0.60]. Both positive controls must have F16 M1 ≥ 0.80; the frozen analyser marks all assays at that tag uninterpretable if either positive control fails.', '',
      '| Tag | Set | Row | Mis M1 gate | Mis M2 gate | python_string control | prose_sentiment control | Interpretable |',
      '|---|---|---|---|---|---|---|---|']
    for r in m['validity_gates']:
        lines.append(f"| {r['tag']} | {r['set']} | {r['feature']} | {verdict(r['Mis']['M1'])} | {verdict(r['Mis']['M2'])} | {verdict(r['positive_controls']['python_string'])} | {verdict(r['positive_controls']['prose_sentiment'])} | {'YES' if r['interpretable'] else 'NO'} |")
    lines += ['', '**Swap secondary check.** MET means Swap ≤ 0.50 where F16 ≥ 0.70; “n/a” means the F16 applicability threshold was not reached. Matched and Swap AUROCs/CIs are in the main tables.', '',
      '| Set | Row | Tag 44 M1 | Tag 44 M2 | Tag 40 M1 | Tag 40 M2 |','|---|---|---|---|---|---|']
    sw={(r['set'],r['feature'],r['tag'],r['measure']):r for r in m['Swap_secondary']}
    for dataset,feature in pairs:
        rr=[sw[(dataset,feature,t,v)] for t in (44,40) for v in ('M1','M2')]
        lines.append(f'| {dataset} | {feature} | '+' | '.join(verdict(r['prediction_met']) if r['prediction_applies'] else 'n/a' for r in rr)+' |')
    lines += ['', '**Secondary W1-to-S probe transfer.** These values are not used in the decision rules; primary S M1 uses the set-S direction.', '',
      '| Row | Arm | Contract | Tag 44 AUROC [CI] | Tag 40 AUROC [CI] |','|---|---|---|---|---|']
    transfer={(r['feature'],r['arm'],r['tag']):r for r in m['W1_transfer_secondary']}
    for feature in ('table_column','list_index','prose_paren'):
        for arm in arms:
            rr=[transfer[(feature,arm,t)] for t in (44,40)]
            lines.append(f'| {feature} | {arm} | {rr[0]["contract"]} | '+ ' | '.join(metric(r) for r in rr)+' |')
    lines += ['', '**E23b: complete 2 × 2 × 2 table.** Oracle-lens asked AUROC on table column. W1 uses its two frozen phrasing pairs; Suraj uses its frozen bullet pair. O n = 84, S n = 160.', '',
      '| Set | Phrasing | Layer | AUROC [95% CI] |','|---|---|---|---|']
    for r in m['E23b']['cells']:
        lines.append(f"| {r['set']} | {r['phrasing']} | {r['layer']} | {r['estimate']:.4f} [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}] |")
    lines += ['', '**Rule 6 main effects.** Signs are S−O, Suraj−W1, and layer 44−42; each averages the other four cells. The frozen rule ranks absolute effect magnitude and requires |Δ| ≥ 0.10 with CI excluding zero.', '',
      '| Factor | Signed Δ AUROC [95% CI] | Qualifies |','|---|---|---|']
    for r in m['E23b']['factors']:lines.append(f"| {r['factor']} | {contrast(r)} | {verdict(r['qualifies'])} |")
    lines += ['', f"Rule 6 result: **{m['E23b']['rule6_cause']}**. Outcome (c) does not apply: the training span follows the target, as settled before scoring.", '',
      '**Provenance and execution.** Pod vh9zqysqkbb6kq; source cd402e2cfcaf5d2b9885fa0baa47b14da621268f. All 169 source pins and collection/input/continuation/forecast seals verified before analysis. All 600 Suraj items passed the ≥ 0.999 cosine parity gate at layers 40, 42 and 44. The registered CPU analyser was invoked once and completed in '+f"{invocation['wall_seconds']:.3f}"+' seconds. No GPU/model calls or rerun.', '',
      'Collection seal: `5485951dd8341b096bbb95b95c4afd055bc6fd12d0d4486440b3bf1e0d34caf7`.',
      'Input seal: `88c46812fd7a5a044948b0e10dcb4f2b93b76b2aa15ac1862977585b1459a46d`.',
      'Registered analysis seal: `'+seal_sha+'`.', '',
      'This full report formats the sealed metrics only. The original analysis/RESULTS.md, metrics, predictions, folds, provenance, once guard and SCORE_SEAL.json remain unchanged. The report is separately bound by REPORT_SEAL.json.', '']
    return '\n'.join(lines)


if __name__=='__main__':
    verify(BASE/'analysis')
    m=read(BASE/'analysis/metrics.json');inv=read(BASE/'ANALYSIS_INVOCATION.json')
    assert inv['status']=='COMPLETE_ONCE'
    before=sha(BASE/'analysis/SCORE_SEAL.json')
    text=render(m,inv,before)
    with (BASE/'RESULTS.md').open('x') as f:f.write(text)
    assert sha(BASE/'analysis/SCORE_SEAL.json')==before
    dump(BASE/'REPORT_SEAL.json',{'status':'E23_FULL_REPORT_FROM_SEALED_METRICS_NO_RECOMPUTATION','files':{
       'RESULTS.md':sha(BASE/'RESULTS.md'),'analysis/SCORE_SEAL.json':before,
       'analysis/metrics.json':sha(BASE/'analysis/metrics.json'),'ANALYSIS_INVOCATION.json':sha(BASE/'ANALYSIS_INVOCATION.json')},
       'renderer_sha256':sha(Path(__file__)), 'registered_analysis_rerun':False})
