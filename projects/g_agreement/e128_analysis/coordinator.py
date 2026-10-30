"""434061b36: E128 pair-logit analysis, alpha_min 2/4, missingness bounds."""
import argparse
from copy import deepcopy
from pathlib import Path
from projects.g_agreement.e127_analysis import transport as t, deviation1 as d
from projects.g_agreement.e127_analysis.common import require, criterion, rule
from common.stats import wilson
from . import rules

SPEC_SHA = '69af33cc5abf14abe43be1b542adead729eeda8d5b9c675c1f34421feca740bb'


def bounds(stat):
    """Assign every missing binary judgment failure/success on the full cohort."""
    n, k, m = stat['planned_n'], stat['k'], stat['missing_n']
    def endpoint(success):
        p, lo, hi = wilson(success, n) if n else (None, None, None)
        return dict(k=success, n=n, estimate=p, Wilson95=None if n == 0 else [lo, hi])
    return dict(lower=endpoint(k), upper=endpoint(k+m))


def analyze(records):
    xs = deepcopy(records)
    for x in xs:
        for a in (2, 4, 8):
            for z in x['doses'][a].values():
                pair = z['pair_preference_flip_descriptive']
                require(pair is None or type(pair) is bool, 'pair-logit boolean or missing')
                z['flipped'] = None if a == 8 else pair
    # Registered lower-dose selection, never alpha8 or reader-dependent selection.
    result = rules.analyze(xs)
    selected, ambiguous = result['alpha_min'], result['selection_ambiguous']
    # Preserve the reviewed deviation's descriptive original-alpha8 table only.
    original8 = d.analyze128(records)
    result['doses']['8'] = original8['doses']['8']
    result['flip_counts']['8'] = original8['flip_counts']['8']
    result['selection'] = 'smallest of alpha 2/4 with >=42/84 E104 first-token pair-logit flips; alpha8 reference only'
    result['behaviour_measure'] = 'E104 mean(A-B), target-oriented, strict positive; ties not flipped; no greedy substitution'
    result['alpha8_pair_logit_reference'].update(measure=result['behaviour_measure'], used_for_alpha_min=False)
    result['alpha8_source'] = 'original sealed E104 pair-logit flags; optional original E104/E109 judgments descriptive only, no replay'
    if selected is None and not ambiguous:
        result['reading'] = 'the flip needs α = 8 (sealed E104 84/84 pair-logit reference); retain strong-steer caveat; R-DOSE1 NOT EVALUABLE'
    for report in result['doses'].values():
        for layers in report['flipped_set_rates'].values():
            for values in layers.values():
                for stat in values.values():
                    stat['missingness_bounds'] = bounds(stat)
        rates = report['flipped_set_rates']['steered']
        report['worst_case_pattern'] = rule([
            criterion(rates['44']['old']['missingness_bounds']['lower'], .50, .35),
            criterion(rates['52']['new']['missingness_bounds']['lower'], .70)])
        report['best_case_pattern'] = rule([
            criterion(rates['44']['old']['missingness_bounds']['upper'], .50, .35),
            criterion(rates['52']['new']['missingness_bounds']['upper'], .70)])
    result['worst_case_R_DOSE1'] = result['doses'][str(selected)]['worst_case_pattern'] if selected else 'NOT EVALUABLE'
    result['robust_to_missingness'] = result['worst_case_R_DOSE1'] == 'MET' if selected else None
    result['missing_policy'] = 'Observed known-denominator Wilson95 plus full-cohort failure/success bounds and their Wilson95; missing never silently zero; dose selection unchanged'
    result.update(analysis_label='deviation 1 (pair-logit flips), coordinator 434061b36', deviation=1, new_calls=0)
    return result


def run(spec, commit):
    # Same canonical B guard despite reassignment. No second executor/guard.
    guard = t.CUSTODY/'e128'/'DEVIATION1_ONCE.json'
    require(not guard.exists(), 'deviation1 once guard consumed; no replay')
    items, original, meta = t.cohort(spec, 'E128')
    records = t.inputs(spec, 'E128', items, original, meta, pair_answer_fn=d.pair_answer)
    out = t.core.claim(dict(analysis=str(t.CUSTODY/'e128'/'deviation1_once'), guard=str(guard), output_sha256=spec['output_sha256']), commit)
    result = analyze(records)
    t.core.write(out/'RESULTS.json', result)
    t.core.write(out/'BINDING.json', spec)
    t.core.seal(out, 'ANALYSIS_SEAL.json', experiment='E128', status='COMPLETE_ONCE', code_commit=commit, inventory_sha256=spec['inventory_sha256'], output_sha256=spec['output_sha256'], spec_sha256=SPEC_SHA, new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p = argparse.ArgumentParser(); p.add_argument('--spec', required=True); a = p.parse_args()
    commit = t.committed(Path(__file__).resolve().parent)
    require(t.core.sha(a.spec) == SPEC_SHA, 'exact Track Q SPEC 69af33cc')
    print(run(t.core.read(a.spec), commit))

if __name__ == '__main__': main()
