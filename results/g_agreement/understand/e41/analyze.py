"""E41 once-only CPU analysis after complete integrator-sealed E36 output."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import freeze as F

A, P, HERE = F.A, F.P, F.HERE
FROZEN = HERE / 'freeze_2026-10-26'
CLASSIFIER_SEAL = 'cf063f3523f4d9672e68fa721cf50122711614d132d14bff0c30d377af1f50e3'
CANDIDATE_SHA = '8b61f9ac7216f37cc1ae8dd422a8ab0f21c7520e5851a24c8893492f263ef273'

def decision(rows):
    eligible = [r for r in rows if r['evaluable']]
    remote = sum(r['remote_state'] for r in eligible)
    local = sum(r['local_cue'] for r in eligible)
    return {'status': 'NOT_EVALUABLE' if len(eligible) < 3 else ('R' if remote > len(eligible)/2 and local == 0 else 'NOT_R'),
            'judged_rows': len(eligible), 'evaluable_rows': len(eligible), 'remote_state_rows': remote, 'local_cue_rows': local,
            'prediction': 'R', 'rule': '§147 clarification 1 (b0cdff60)'}

def summarize(feature, records, rng):
    strata = {}
    for name in ('informative', 'uninformative'):
        part = [r for r in records if r['stratum'] == name]
        y, s = [r['label'] for r in part], [r['score'] for r in part]
        value = A.auc(s, y)
        if value is not None:
            ix = rng.integers(0, len(y), size=(2000, len(y)))
            ci = A.interval(A.bootstrap_auc(s, y, ix))
        else:
            ci = A.interval([])
        strata[name] = {'n': len(y), 'n_A': sum(y), 'n_B': len(y)-sum(y), 'auroc': value, **ci}
    return {'feature': feature, 'strata': strata, **judge_strata(strata)}

def judge_strata(strata):
    """§147 clarification 1; no fallback when informative n >= 10."""
    i, u = (strata[s] for s in ('informative', 'uninformative'))
    if all(s['n'] >= 10 and s['auroc'] is not None for s in (i, u)):
        mode = 'both_strata'
        remote = i['auroc'] >= .70 and u['auroc'] >= .70
        local = i['auroc'] >= .75 and u['auroc'] <= .60
    elif i['n'] < 10 and u['n'] >= 10 and u['auroc'] is not None and u['ci95'] is not None:
        mode = 'uninformative_only'
        remote = u['auroc'] >= .70 and u['ci95'][0] > .50
        local = u['auroc'] <= .60
    else:
        return {'evaluable': False, 'judged': False, 'criterion': None,
                'reason': 'INSUFFICIENT_ITEMS_OR_UNDEFINED_AUROC_CI',
                'remote_state': None, 'local_cue': None}
    return {'evaluable': True, 'judged': True, 'criterion': mode, 'reason': None,
            'remote_state': bool(remote), 'local_cue': bool(local)}

def verify_output(out, expected):
    seal = A.verify_seal(out / 'OUTPUT_SEAL.json', expected)
    required = {'scores.jsonl', 'plan.json', 'runtime.json', 'PARITY_RESULT.json'}
    if seal.get('experiment') != 'E36' or not required <= set(seal['files']):
        raise ValueError('complete E36 custody required')
    runtime, plan = P.read(out / 'runtime.json'), P.read(out / 'plan.json')
    payload = {k: v for k, v in plan.items() if k != 'plan_sha256'}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    if not digest == seal['plan_sha256'] == plan['plan_sha256'] == runtime['plan_sha256']:
        raise ValueError('output plan identity mismatch')
    if runtime['status'] != 'COMPLETE' or P.read(out / 'PARITY_RESULT.json')['status'] != 'PASS':
        raise ValueError('incomplete production or parity failure')
    for key, digest in [('bank', F.INPUTS[str(F.BANK / 'items.input.jsonl')]), ('candidates', CANDIDATE_SHA),
                        ('freeze', 'e6c1a2349f9dca7faead507bfc521fce8e4e47dd1bba8b317bae4c9f1c38c184')]:
        if plan[key]['sha256'] != digest:
            raise ValueError('wrong E36 input binding: ' + key)
    if plan['channels']['continuation'] != {'block': 44, 'candidate_key': 'continuation', 'prefix': '- ', 'split': 'test'}:
        raise ValueError('wrong continuation channel')
    return seal

def main(args):
    F.verify_inputs()
    A.verify_seal(FROZEN / 'CLASSIFIER_SEAL.json', CLASSIFIER_SEAL)
    code = A.verify_seal(HERE / 'ANALYSIS_CODE_SEAL.json')
    if not {'analyze.py', 'freeze.py', 'PROTOCOL.json'} <= set(code['files']):
        raise ValueError('missing frozen analysis code')
    output = Path(args.e36_output)
    verify_output(output, args.output_seal_sha256)
    out = HERE / 'analysis_2026-10-26'
    A.exclusive_start(out, {'started_at': datetime.now(timezone.utc).isoformat(), 'e36_output_seal': args.output_seal_sha256,
                            'classifier_seal': CLASSIFIER_SEAL, 'analysis_code_seal': P.sha(HERE / 'ANALYSIS_CODE_SEAL.json')})
    # Only now may test predictions and sealed continuation scores be joined.
    test, tok = F.items('test'), F.decoder()
    models = P.read(FROZEN / 'cache/models.json')
    cutoffs = {r['feature']: r for r in P.read(FROZEN / 'DEV_CUTOFFS.json')['rows']}
    scoremap = {}
    for r in P.read_jsonl(output / 'scores.jsonl'):
        if r['channel'] != 'continuation' or r['feature'] not in P.ROWS:
            continue
        if r['id'] in scoremap or r['split'] != 'test' or r['block'] != 44 or r['status'] != 'COMPLETE':
            raise ValueError('invalid or duplicate continuation record')
        if len(r['scores']) != 2 or not np.isfinite(r['scores']).all():
            raise ValueError('both frozen continuation pairs required')
        scoremap[r['id']] = r
    if set(scoremap) != {r['id'] for r in test}:
        raise ValueError('E36 H4 test grid incomplete')
    rng, rows, ledger = np.random.default_rng(20261025), [], []
    for feature in P.ROWS:
        selected = [r for r in test if r['feature'] == feature]
        cutoff = cutoffs[feature]
        probabilities = P.restored_probabilities(models[feature], F.texts(selected, tok))
        strata = P.assign_strata(probabilities, cutoff['cutoff'])
        records = []
        for item, stratum in zip(selected, strata):
            s = scoremap[item['id']]
            if s['feature'] != feature or item['value'] not in cutoff['values']:
                raise ValueError('test label identity mismatch')
            records.append({'id': item['id'], 'feature': feature, 'stratum': stratum,
                'label': int(item['value'] == cutoff['values'][0]), 'score': float(np.mean(s['scores']))})
        rows.append(summarize(feature, records, rng))
        ledger.extend(records)
    metrics = {'experiment': 'E41', 'rows': rows, 'rule': decision(rows), 'bootstrap': 2000,
               'classifier_seal': CLASSIFIER_SEAL, 'e36_output_seal': args.output_seal_sha256}
    (out / 'cache').mkdir()
    A.dump(out / 'cache/item_ledger.json', ledger)
    A.dump(out / 'METRICS.json', metrics)
    lines = ['# E41 — E31(i) protocol on E36 v2', '', 'Registered decision: **' + metrics['rule']['status'] + '**.', '',
             '| Row | Informative n / AUROC (95% CI) | Uninformative n / AUROC (95% CI) | Judged criterion |', '|---|---|---|---|']
    for r in rows:
        cells = []
        for s in r['strata'].values():
            cells.append(str(s['n']) + ' / ' + ('undefined' if s['auroc'] is None else f"{s['auroc']:.4f} ({s['ci95'][0]:.4f}, {s['ci95'][1]:.4f})"))
        lines.append('| ' + ' | '.join([r['feature'], *cells, str(r['criterion'])]) + ' |')
    lines += ['', 'Strict dev-median split; ties uninformative. 2,000 IID item resamples per stratum; finite-draw percentile intervals. Undefined AUROC cannot satisfy a point threshold. No model refit or cutoff adjustment.', '',
              '§147 clarification 1: rows with both strata ≥10 retain the original point rules. If informative n<10 and uninformative n≥10, remote-state requires uninformative AUROC≥0.70 and CI lower bound>0.50; local-cue requires uninformative AUROC≤0.60. R requires a strict majority remote-state and no local-cue rows among judged rows. Fewer than three judged rows means NOT_EVALUABLE.']
    (out / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    A.dump(out / 'ANALYSIS_SEAL.json', {'complete': True, 'files': {n: P.sha(out / n) for n in ['STARTED.json', 'METRICS.json', 'RESULTS.md', 'cache/item_ledger.json']}})
    print(json.dumps({'status': metrics['rule'], 'seal': P.sha(out / 'ANALYSIS_SEAL.json')}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--e36-output', required=True)
    parser.add_argument('--output-seal-sha256', required=True, help='Integrator-published complete E36 seal')
    main(parser.parse_args())
