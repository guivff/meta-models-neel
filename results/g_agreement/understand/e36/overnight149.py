"""§149 pinned CPU-only dispatcher. Fixed pull paths; one attempt per experiment."""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

A = module('e31_stats149', BASE / 'e31/analyze.py')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def receipt(experiment):
    folder = BASE / experiment
    path = folder / 'cache/verified_pull_149/RECEIPT.json'
    r = A.read(path)
    expected_seal = 'SCORE_SEAL.json' if experiment == 'e29' else 'OUTPUT_SEAL.json'
    require(r.get('experiment') == experiment.upper() and r.get('verified') is True and r.get('issuer') == 'integrator', 'integrator verified-pull receipt required')
    require(r.get('seal_file') == expected_seal, 'wrong output seal filename')
    out = path.parent / 'out'
    seal = A.verify_seal(out / expected_seal, r['seal_sha256'])
    return out, r, seal

def begin(experiment):
    folder = BASE / experiment
    # Reserve BEFORE any validation or output read. A failed attempt waits for owner.
    A.dump(folder / 'OVERNIGHT149_ATTEMPT.lock.json', {'created_at': datetime.now(timezone.utc).isoformat(),
        'experiment': experiment.upper(), 'label': '§149 RUN-BY-INTEGRATOR'})
    seal = A.read(HERE / 'OVERNIGHT149_CODE_SEAL.json')
    for name, digest in seal['files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and A.sha(ROOT / name) == digest, 'analysis source/input seal mismatch: ' + name)
    return receipt(experiment)

def save(experiment, metrics, pull):
    out = BASE / experiment / 'analysis_overnight149'
    out.mkdir(exist_ok=False)
    A.dump(out / 'METRICS.json', metrics)
    A.dump(out / 'RUN.json', {'label': '§149 RUN-BY-INTEGRATOR', 'CPU_only': True,
        'completed_at': datetime.now(timezone.utc).isoformat(), 'verified_pull': pull,
        'code_seal_sha256': A.sha(HERE / 'OVERNIGHT149_CODE_SEAL.json')})
    text = '# ' + experiment.upper() + ' registered analysis\n\n§149 RUN-BY-INTEGRATOR; owner review pending.\n\n'
    text += '```json\n' + json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False) + '\n```\n'
    (out / 'RESULTS.md').write_text(text)
    A.dump(out / 'ANALYSIS_SEAL.json', {'complete': True, 'label': '§149 RUN-BY-INTEGRATOR',
        'files': {n: A.sha(out / n) for n in ['RUN.json', 'METRICS.json', 'RESULTS.md']}})
    print(json.dumps({'experiment': experiment, 'output': str(out), 'seal_sha256': A.sha(out / 'ANALYSIS_SEAL.json')}))

def contrast(y, first, second, rng):
    ix = rng.integers(0, len(y), size=(2000, len(y)))
    draws = A.bootstrap_auc(first, y, ix) - A.bootstrap_auc(second, y, ix)
    return {'difference': A.auc(first, y) - A.auc(second, y), **A.interval(draws)}

def h3_rule(contrasts, present):
    rows = ['table_row', 'table_column', 'python_argument', 'latex_section', 'python_comment', 'python_depth']
    included = [r for r in rows if r in present]
    passed = [r for r in included if contrasts[r]['difference'] >= .15 and contrasts[r]['ci95'][0] > 0]
    return {'status': 'NOT_EVALUABLE' if len(included) < 4 else ('REPLICATED' if len(passed) >= 4 else 'NOT_REPLICATED'),
        'authority': '§132 clarification 3', 'required': 4, 'present_rows': included, 'satisfying_rows': passed,
        'row_contrasts': {r: contrasts[r] for r in included}}

def e36(out, receipt, seal):
    # Reuse E41's score-custody checks without executing E41 analysis.
    sys.path.insert(0, str(BASE / 'e41'))
    E = module('e41_checks149', BASE / 'e41/analyze.py')
    E.verify_output(out, receipt['seal_sha256'])
    E.F.verify_inputs()
    import channel_contract as C
    plan = A.read(out / 'plan.json')
    C.validate_scope(plan['scope'])
    expected_scope = C.scope_from_definition_packet({'path': str(HERE / 'ROW_DEFINITIONS.json'), 'sha256': C.DEFINITION_PACKET_SHA256})
    require(all(plan['scope'][k] == expected_scope[k] for k in ['rows', 'structure_rows', 'content_rows']), 'scope taxonomy changed')
    require(plan['channels'] == C.CHANNELS and plan['probe'] == C.PROBE_RECIPE and plan['parity_threshold'] == .02, 'scientific acquisition recipe changed')
    items = A.jsonl(E.F.BANK / 'items.input.jsonl')
    order = A.read(out / 'items.order.json')
    lookup = {r['id']: r for r in items}
    require(len(order) == len(items) and len(set(order)) == len(items) and set(order) == set(lookup), 'capture order identity mismatch')
    items = [lookup[k] for k in order]
    labels = A.jsonl(E.F.BANK / 'labels.DO_NOT_STAGE.jsonl')
    candidates_path = HERE / 'cache/postfreeze_candidates_2026-10-25/candidates.json'
    require(A.sha(candidates_path) == E.CANDIDATE_SHA, 'candidate identity mismatch')
    candidates = A.read(candidates_path)
    scores = A.jsonl(out / 'scores.jsonl')
    # Full expected production grid, including every frozen continuation pair.
    expected = {(r['id'], c) for r in items if r['split'] == 'test' for c in
                ['oracle_descriptive', 'oracle_value_word:e30_bullet', 'nla'] +
                (['continuation'] if candidates['rows'][r['feature']]['continuation'] else [])}
    require(len(scores) == len(expected) and {(r['id'], r['channel']) for r in scores} == expected, 'incomplete or duplicate score grid')
    require(all(r['status'] == 'COMPLETE' and np.isfinite(r['scores']).all() for r in scores), 'incomplete/nonfinite score')
    for n in ['items.order.json', 'acts44.npy']:
        require(n in seal['files'], 'unsealed capture dependency')
    acts = np.load(out / 'acts44.npy', mmap_mode='r', allow_pickle=False)
    require(acts.ndim == 2 and len(acts) == 4200 and np.isfinite(acts).all(), 'invalid capture matrix')
    sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
    import torch
    torch.set_num_threads(4)
    result = C.analyse_acquisition(items, labels, candidates, scores, acts, repo_root=ROOT,
                                   scope=plan['scope'], rule_binding=plan['rule_binding'])
    lookup_labels = {r['id']: r for r in labels}
    smap = {(r['id'], r['channel']): r['scores'] for r in scores}
    contrasts, nla_contrasts = {}, {}
    rng = np.random.default_rng(20261025)
    for feature in plan['scope']['rows']:
        group = [r for r in items if r['feature'] == feature and r['split'] == 'test']
        positive = candidates['rows'][feature]['values'][0]
        y = [int(lookup_labels[r['id']]['value'] == positive) for r in group]
        values = {c: [float(np.mean(smap[(r['id'], c)])) for r in group]
                  for c in ['oracle_descriptive', 'oracle_value_word:e30_bullet', 'nla']}
        contrasts[feature] = contrast(y, values['oracle_value_word:e30_bullet'], values['oracle_descriptive'], rng)
        nla_contrasts[feature] = contrast(y, values['nla'], values['oracle_descriptive'], rng)
    result['hypotheses']['H3'] = h3_rule(contrasts, plan['scope']['rows'])
    result['H3_descriptive_state_rows'] = {r: contrasts[r] for r in ['prose_paren', 'prose_quote', 'python_string', 'table_role']}
    result['NLA_minus_Oracle_descriptive_CIs'] = nla_contrasts
    result['bootstrap'] = {'draws': 2000, 'seed': 20261025, 'unit': 'paired IID item within row', 'CI': '95% finite-draw percentile'}
    save('e36', result, receipt)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', choices=['e29', 'e36', 'e41'])
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    out, r, seal = begin(args.experiment)
    if args.experiment == 'e36':
        e36(out, r, seal)
    elif args.experiment == 'e29':
        E = module('e29_compare149', BASE / 'e29/compare149.py')
        E.run(out, r, seal)
    else:
        sys.path.insert(0, str(BASE / 'e41'))
        E = module('e41_analyze149', BASE / 'e41/analyze.py')
        E.main(argparse.Namespace(e36_output=str(out), output_seal_sha256=r['seal_sha256']))

if __name__ == '__main__':
    main()
