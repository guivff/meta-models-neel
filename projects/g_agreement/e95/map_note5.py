"""E95 note 5 pre-judgment map adapter. No acquisition, judging or parser replay."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from . import oracle_only as base
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.understand.e87_analysis import e87_analysis as e87

ROOT = Path(__file__).resolve().parents[3]
# Same global guard as the existing stage-complete E95 adapter, independent of checkout.
GUARD = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e95/ANALYSIS_ONCE.json')


def clean(x):
    if isinstance(x, float) and not np.isfinite(x): return None
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    return x


def layer_summary(cells, key, reader, layer):
    """E87 signed score, missing policy and joint item resampling, fixed seed/draws."""
    arms = {a: cells.get((key, reader, a, layer), {}) for a in ('real', 'placebo')}
    items = sorted(set(arms['real']) | set(arms['placebo']))
    arrays = {a: np.array([np.nan if arms[a].get(i) is None else arms[a][i] for i in items], float) for a in arms}
    result = {}
    ix = np.random.default_rng(e87.SEED).integers(0, len(items), (e87.DRAWS, len(items))) if items else None
    means, draws = {}, {}
    for arm, v in arrays.items():
        n = int(np.isfinite(v).sum())
        means[arm] = float(np.nanmean(v)) if n else None
        if n:
            z = v[ix]; counts = np.isfinite(z).sum(1)
            draws[arm] = np.divide(np.nansum(z, 1), counts, out=np.full(e87.DRAWS, np.nan), where=counts > 0)
        else: draws[arm] = np.full(e87.DRAWS, np.nan)
        valid = draws[arm][np.isfinite(draws[arm])]
        result[arm] = dict(S=means[arm], total=len(arms[arm]), kept=n,
                           UNPARSEABLE=sum(v is None for v in arms[arm].values()),
                           ci95=np.quantile(valid, [.025, .975]).tolist() if len(valid) else None)
    delta = draws['real'] - draws['placebo']; valid = delta[np.isfinite(delta)]
    result.update(S_layer_minus_placebo=None if any(v is None for v in means.values()) else means['real'] - means['placebo'],
                  difference_ci95=np.quantile(valid, [.025, .975]).tolist() if len(valid) else None,
                  defined_bootstrap_draws=len(valid))
    return result


def first_positions(judgments, join):
    byid = c.unique(join); out = {}
    for code in judgments:
        j = byid[code['id']]
        if j['arm'] != 'real' or code['category'] != 'states_value': continue
        # Both-value mentions are included as in E87; never count placebo mentions.
        pos = code.get('first_position')
        if pos is None: continue
        c.require(type(pos) is int, 'first-position must be an original integer offset')
        if 'positions' in j: c.require(pos in j['positions'], 'first mention outside achieved position grid')
        out.setdefault((j['row'], j['reader'], j['layer']), []).append(pos)
    return out


def validate_plan(plan):
    c.require(plan['verdict_rule']['authority'] and plan['verdict_rule']['operator'] in ('>=', '>'), 'original frozen verdict definition')
    t = plan['verdict_rule']['threshold']; c.require(type(t) in (float, int) and np.isfinite(t), 'finite fixed verdict threshold')
    for reader in ('oracle', 'nla'):
        rows = [r for r in plan['rows'] if r.get('reader', 'oracle') == reader]
        keys = [r['key'] for r in rows]; c.require(len(keys) == len(set(keys)), 'distinct per-reader row keys')
    for r in plan['rows']:
        c.require(type(r['statement_score_registered']) is bool, 'explicit statement eligibility')
        if r.get('J_fraction') is not None:
            c.require(type(r['J_fraction']) in (float, int) and np.isfinite(r['J_fraction']) and 0 <= r['J_fraction'] <= 1, 'finite sealed k16 fraction')
    if plan['E62_median'] is not None:
        c.require(np.isfinite(plan['E62_median']) and 0 <= plan['E62_median'] <= 1, 'frozen E62 population median')


def validate_side_bindings(plan, jtable, population, rules):
    """Bind displayed columns and H-M1 to sealed pre-judgment sources, not loose scalars."""
    c.require(jtable['k'] == 16 and jtable['recipe_authority'] and jtable['source_seals'], 'original k16 J recipe/source')
    entries = {(r['reader'], r['key']): r for r in jtable['rows']}
    c.require(len(entries) == len(jtable['rows']), 'duplicate J row')
    for r in plan['rows']:
        if r['status'] != 'COMPLETE' or not r['statement_score_registered']: continue
        identity = (r.get('reader', 'oracle'), r['key'])
        c.require(identity in entries, 'missing row J binding')
        j = entries[identity]
        c.require(j['bank'] == r['bank'] and j['row'] == r['row'] and j['source'] and j['fraction'] == r['J_fraction'], 'exact original row J fraction')
    c.require(population['source'] and population['population_definition'], 'original E62 population definition')
    values = population['fractions']
    c.require(values and all(type(v) in (int, float) and np.isfinite(v) and 0 <= v <= 1 for v in values), 'complete finite E62 population')
    c.require(float(np.median(values)) == plan['E62_median'], 'original E62 median bound to population')
    c.require(rules['verdict_rule'] == plan['verdict_rule'], 'original verdict rule binding')
    singles = {(r['reader'], r['key']): r for r in rules['single_site_verdicts']}
    c.require(len(singles) == len(rules['single_site_verdicts']), 'duplicate single-site verdict')
    for r in plan['rows']:
        if r['status'] != 'COMPLETE' or not r['statement_score_registered']: continue
        v = singles.get((r.get('reader', 'oracle'), r['key']))
        c.require(v is not None and v['source'] and v['verdict'] == r['single_site_verdict'], 'sealed original single-site verdict')


def summarize(plan, judgments, join):
    validate_plan(plan)
    byid = c.unique(join)
    for code in judgments:
        c.require(code['id'] in byid and byid[code['id']]['target'] in ('A', 'B'), 'private binary target identity')
        cat, vals = code['category'], code.get('values')
        c.require(cat in ('UNPARSEABLE', 'states_value', 'names_property_without_value', 'exhibits', 'silent'), 'normalized corrected category')
        c.require(vals in ([], ['A'], ['B'], ['A', 'B'], ['B', 'A']), 'normalized corrected values')
        c.require((cat == 'states_value') == bool(vals), 'normalized category/value agreement')
    result = base.summarize(plan, judgments, join)
    cells, _ = e87.grid(judgments, join); first = first_positions(judgments, join)
    reports = {'oracle': result, 'nla': result['NLA']}
    for reader, report in reports.items():
        if 'rows' not in report: continue
        planned = {r['key']: r for r in plan['rows'] if r.get('reader', 'oracle') == reader}
        for row in report['rows']:
            if row['status'] != 'DESCRIPTIVE': continue
            key = row['key']; layers = planned[key]['layers']
            row['layer_map'] = {str(L): layer_summary(cells, key, reader, L) for L in layers}
            row['first_mention_by_layer'] = {}
            allpos = []
            for L in layers:
                v = first.get((key, reader, L), []); allpos.extend(v)
                row['first_mention_by_layer'][str(L)] = dict(n=len(v), median=float(np.median(v)) if v else None,
                    counts={str(p): v.count(p) for p in sorted(set(v))})
            row['first_mention_position'] = dict(n=len(allpos), median=float(np.median(allpos)) if allpos else None,
                                                scope='real-arm states_value only; registered original offsets')
            row['maxima_definition'] = 'D = max_layer S_real - max_layer S_placebo; not max_layer(S_real-S_placebo)'
            row['complete_layer_scores'] = all(v[a]['kept'] > 0 for v in row['layer_map'].values() for a in ('real', 'placebo'))
            if not row['complete_layer_scores']:
                row['map_verdict'] = None
                row['map_qualification'] = 'NOT EVALUABLE: at least one achieved layer/arm has no parseable score; observed maxima retained only'
        eligible = [r for r in report['rows'] if r['status'] == 'DESCRIPTIVE']
        comparable = [r for r in eligible if r['map_verdict'] is not None and r['single_site_verdict'] in ('REPORTED', 'MISSED')]
        hm = report['H_M1']; hm['agreement_rows'] = len(comparable)
        hm['agreement_observed'] = sum(r['map_verdict'] == r['single_site_verdict'] for r in comparable) / len(comparable) if comparable else None
        hm['low_J_counterexamples'] = [r['key'] for r in eligible if r['J_fraction'] is not None and plan['E62_median'] is not None
                                      and r['J_fraction'] < plan['E62_median'] and r['statistics']['D'] >= .30]
        if len(comparable) != len(eligible): hm['status'] = 'NOT EVALUABLE'
        hm['scope'] = 'stage-complete statement-score rows for this reader only; not all acquired/intended rows'
        report['coverage_summary'] = dict(planned_rows=len(planned), complete_rows=sum(r['status'] == 'COMPLETE' for r in planned.values()),
            not_run_rows=sum(r['status'] == 'NOT RUN' for r in planned.values()), statement_scored_rows=len(eligible),
            achieved_layers={r['key']: r.get('layers', []) for r in planned.values() if r['status'] == 'COMPLETE'})
    result['authority'] = 'E95 operational note 5, 7b3cebfe2; DESCRIPTIVE H-M1'
    result['E87_confirmatory_result'] = 'unchanged; no E87 analysis invocation'
    return clean(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--spec', required=True); a = parser.parse_args()
    c.require(datetime.now(timezone.utc) < datetime(2026, 10, 30, 17, tzinfo=timezone.utc), 'E95 deadline: acquired, not analysed; no late invocation')
    receipt = c.read(ROOT/'projects/g_agreement/e95/MAP_NOTE5_SOURCE_RECEIPT.json')
    for f, h in receipt['files'].items():
        c.require(c.sha(ROOT/f) == h and hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:'+f], cwd=ROOT)).hexdigest() == h, 'committed unchanged adapter/source')
    spec = c.read(a.spec)
    c.require(spec['parser_contract'] == 'E87 validator-corrected §221 item1', 'original corrected parser required')
    for name in ('pre_judgment_source_commit', 'J_fraction_binding_seal', 'J_fraction_binding_sha256', 'verdict_authority_binding_seal', 'verdict_authority_binding_sha256'):
        c.require(spec.get(name), 'exact pre-judgment/J/verdict binding: '+name)
    # Verify source receipts BEFORE opening any real judgments. Neither adapter fits a J basis.
    c.verify(spec['J_fraction_binding_seal'], spec['J_fraction_binding_sha256'])
    c.verify(spec['verdict_authority_binding_seal'], spec['verdict_authority_binding_sha256'])
    jroot = Path(spec['J_fraction_binding_seal']).parent
    vroot = Path(spec['verdict_authority_binding_seal']).parent
    plan_only = c.read(Path(spec['binding_seal']).parent/'PLAN.json')
    validate_plan(plan_only)
    validate_side_bindings(plan_only, c.read(jroot/'J_FRACTIONS.json'), c.read(jroot/'E62_POPULATION.json'), c.read(vroot/'RULES.json'))
    pre = spec['pre_judgment_source_commit']
    for f, h in receipt['files'].items():
        c.require(hashlib.sha256(subprocess.check_output(['git', 'show', pre+':'+f], cwd=ROOT)).hexdigest() == h, 'pre-judgment source pin')
    c.require(not GUARD.exists() and not Path(spec['analysis']).exists(), 'E95 once-only guard/output already exists')
    plan, judgments, join = base.inputs(spec)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    out = c.claim(dict(analysis=spec['analysis'], guard=str(GUARD), output_sha256=spec['binding_sha256']), commit)
    c.write(out/'RESULTS.json', summarize(plan, judgments, join))
    # The final exact private binding remains local; only aggregate/seal is public.
    c.write(out/'BINDING.PRIVATE.json', spec)
    c.seal(out, 'ANALYSIS_SEAL.json', experiment='E95', status='COMPLETE_ONCE', code_commit=commit)


if __name__ == '__main__': main()
