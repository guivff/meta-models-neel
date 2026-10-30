"""§124 one prospective comparison; never recompute or replace sealed D/P."""
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
import overnight149 as O
A = O.A
HERE = Path(__file__).resolve().parent
VALUES = 'ecac8379a09d429ae42013b2980a0fb927043309f51a84f730b3283430238bf7'
PREDICTIONS = 'ca76c12ce6f1c9ffdf95097b7ac3ce3f62c0cfa9f7519941857bd467ed80f2ba'
FREEZE = '2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f'

def verdict(rows):
    high = [r for r in rows if r['D'] >= .70]
    passed = [r['feature'] for r in high if r['D_minus_Oracle']['difference'] >= .15 and r['D_minus_Oracle']['ci95'][0] > 0]
    required = min(len(high), 2) if len(high) >= 3 else len(high)
    falsifiers = [r['feature'] for r in high if r['Oracle'] >= .75 and r['Oracle_CI']['ci95'][0] > .65]
    return {'R1': {'all_structure_Oracle_le065': all(r['Oracle'] <= .65 for r in rows),
                   'registered_falsified': bool(falsifiers), 'falsifying_rows': falsifiers},
            'R2': {'status': 'NOT_EVALUABLE' if not high else ('MET' if len(passed) >= required else 'NOT_MET'),
                   'high_D_rows': [r['feature'] for r in high], 'required': required, 'satisfying_rows': passed}}

def run(out, receipt, seal):
    O.require(seal.get('status') == 'W12_ASKED_ONLY_COMPLETE', 'complete W12 score seal required')
    O.require({'scores.jsonl', 'BINDING.json', 'W1_PARITY_SEAL.json'} <= set(seal['files']), 'missing W12 custody')
    parity = A.verify_seal(out / 'W1_PARITY_SEAL.json')
    O.require(parity['status'] == 'PASS', 'W12 parity failed')
    binding = A.read(out / 'BINDING.json')
    O.require(binding['freeze_sha256'] == FREEZE and binding['values_seal_sha256'] == VALUES and binding['predictions_seal_sha256'] == PREDICTIONS, 'W12 prospective release identity mismatch')
    A.verify_seal(HERE / 'w12_values/VALUES_SEAL.json', VALUES)
    A.verify_seal(HERE / 'PREDICTIONS_SEAL.json', PREDICTIONS)
    metrics = A.read(HERE / 'w12_values/METRICS.json')
    predictions = A.read(HERE / 'PREDICTIONS.json')
    published = {r['feature']: r for r in predictions['rows']}
    base = A.jsonl(HERE / 'w12_values/cache/ITEM_SCORES.jsonl')
    O.require(len(base) == 504 and len({r['id'] for r in base}) == 504, 'sealed D item grid changed')
    known = {r['id']: r for r in base}
    scoremap = {}
    for r in A.jsonl(out / 'scores.jsonl'):
        if r['id'] not in known or r['reader'] not in ['olens', 'nla'] or r['arm'] != 'true':
            continue
        key = r['id'], r['reader']
        O.require(key not in scoremap and r['status'] == 'COMPLETE' and len(r['scores']) == 2 and np.isfinite(r['scores']).all(), 'reader score invalid/duplicate')
        O.require(r['feature'] == known[r['id']]['feature'] and r['layer'] == {'olens':44, 'nla':42}[r['reader']], 'reader identity mismatch')
        scoremap[key] = float(np.mean(r['scores']))
    O.require(set(scoremap) == {(k, reader) for k in known for reader in ['olens', 'nla']}, 'incomplete test reader grid')
    rng, rows = np.random.default_rng(20261025), []
    for fixed in metrics['rows']:
        feature = fixed['feature']
        O.require(published[feature]['class'] == 'structure' and published[feature]['D'] == fixed['D'], 'frozen prediction binding changed')
        group = [r for r in base if r['feature'] == feature]
        y = [int(r['value'] == 'A') for r in group]
        O.require(len(y) == 84 and sum(y) == 42, 'unbalanced or incomplete frozen test row')
        d = [r['margin_A_minus_B'] for r in group]
        ol = [scoremap[(r['id'], 'olens')] for r in group]
        nla = [scoremap[(r['id'], 'nla')] for r in group]
        O.require(abs(A.auc(d, y) - fixed['D']) < 1e-12, 'sealed D ledger inconsistent')
        ix = rng.integers(0, len(y), size=(2000, len(y)))
        d_draw = A.bootstrap_auc(d, y, ix)
        ol_draw = A.bootstrap_auc(ol, y, ix)
        nla_draw = A.bootstrap_auc(nla, y, ix)
        oracle = A.auc(ol, y)
        delta = fixed['D'] - oracle
        rows.append({'feature': feature, 'D': fixed['D'], 'P': fixed['P'], 'Oracle': oracle, 'NLA': A.auc(nla, y),
            'Oracle_CI': A.interval(ol_draw), 'NLA_CI': A.interval(nla_draw),
            'D_minus_Oracle': {'difference': delta, **A.interval(d_draw - ol_draw)},
            'mechanical_prediction_checks': {k: (oracle <= v if k == 'oracle_asked_AUROC_max' else delta >= v)
                 for k, v in published[feature]['predictions'].items()}})
    rho = float(spearmanr([r['D'] for r in rows], [r['NLA'] for r in rows]).statistic)
    result = {'experiment': 'E29', 'comparison': 'single prospective W12 reader comparison', 'rows': rows,
        'registered_rules': verdict(rows), 'R3_descriptive_Spearman_D_NLA': rho if np.isfinite(rho) else None,
        'values_seal': VALUES, 'predictions_seal': PREDICTIONS, 'freeze': FREEZE,
        'bootstrap': {'seed':20261025, 'draws':2000, 'unit':'paired IID item within row', 'CI':'95% finite-draw percentile'},
        'note': 'R1 point prediction and registered stronger falsification condition are reported separately. Mechanical per-row predictions remain unchanged. D/P and non-blind companion are already complete and never rerun.'}
    O.save('e29', result, receipt)
