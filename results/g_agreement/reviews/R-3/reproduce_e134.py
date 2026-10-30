#!/usr/bin/env python3
"""R-3 independent E134 reproduction. Read-only: never imports/calls run_once.

Synthetic preparation:
  python results/g_agreement/reviews/R-3/reproduce_e134.py --self-test
Sealed-input review (after shared publication):
  python results/g_agreement/reviews/R-3/reproduce_e134.py --plan PUBLIC_PLAN.json \
      --author-results RESULTS.json --author-seal ANALYSIS_SEAL.json

All real inputs must be committed in this checkout; no worker checkout/private
binding access. Input normalization, T4 matcher/gate and T6 population provenance
are audited prerequisites, never inferred from hit/miss codes. JSON goes to stdout;
this script writes no scientific output, selection, lock or once guard.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from common.stats import bootstrap_ci, wilson

LAYERS = (44, 52, 60)
FIXED = ('P44', 'P52', 'P60')
ADAPTIVE = ('PALL', 'PLATE', 'PSTAB', 'PAGREE')
RULES = FIXED + ADAPTIVE
DRAWS, SEED = 2000, 20261030
PREPARATION_SOURCE_SHA256 = {'projects/g_agreement/e134/policy.py': '94fa08386df43ce9baefadaac9299ffe4c9cb2eede5c0afe921df298808e51cb', 'projects/g_agreement/e134/run_once.py': '83abcbe85ffd237ed7b586c32d078463b41bdfdb6cb0b9e990ea2f4d3ebd3b78', 'projects/g_agreement/e134/test_policy.py': 'cfa7d6c3a0ebe5f1474c651057d4d1387453a29855f442287e71c653c95edc48', 'projects/g_agreement/e134/test_once.py': '0911a6f804dc053d068d02f278bdfe638def2f228f4dd4032d3516dd03d3f19a', 'projects/g_agreement/e134/matcher.py': '152c8313ebbbe9a77225550318b4ad49c449a4be538bdc0929ec6754245f0098', 'projects/g_agreement/e134/normalize.py': '904edc2eed0b569cba86bf855f8ea0bca22b72c8fd4fff9cf5abfdcc7dc5ab5f', 'projects/g_agreement/e134/test_matcher.py': 'b0aaf352c0c64ebe43b381112582b02190e61b98acd1697684ff75b56446b446', 'projects/g_agreement/e134/sources.py': '5f7a98e98cfc82280d664f203783cbd9e6a3cfc5257a0f8930579baff47c0ade', 'projects/g_agreement/e134/truth.py': '636202589ed00646fd3fbacce86639ae4f22754ca01db19e15b2f805704925ba', 'projects/g_agreement/e134/test_sources.py': 'a2cbe1d9e7dfdb6a92cff344de0fa247a633be1b73ec26f28f4773843f98a7b6', 'projects/g_agreement/e134/test_truth.py': '986b305497b3f0f5c8bd1cb1db28caaa3eee5a8184545804af2799cc096e5c9f'}


def predict(rule, readings):
    if rule not in RULES or any(k not in LAYERS for k in readings):
        raise ValueError('unknown rule/layer')
    if any(v is not None and not isinstance(v, str) for v in readings.values()):
        raise ValueError('normalized scalar string or null required; dual values must be abstentions')
    if rule in FIXED:
        return readings.get(int(rule[1:]))
    available = [readings[k] for k in LAYERS if k in readings]
    stated = [v for v in available if v is not None]
    if not stated:
        return None
    if rule == 'PLATE':
        return stated[-1]
    if rule == 'PAGREE':
        return stated[0] if len(set(stated)) == 1 else None
    if rule == 'PALL':
        counts = Counter(stated)
        return max(enumerate(stated), key=lambda x: (counts[x[1]], x[0]))[1]
    for index in range(len(available) - 1):
        if available[index] is not None and available[index] == available[index + 1]:
            return available[index]
    return stated[-1]


def score(rows, rule, draws=DRAWS, include_truth_strata=True):
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate item-condition ID')
    eligible = [r for r in rows if rule not in FIXED or int(rule[1:]) in r['readings']]
    if not eligible:
        return dict(total=len(rows), eligible=0, unavailable=len(rows), metrics=None)
    clusters = {}
    events, accuracy_mask = [], []
    for index, row in enumerate(eligible):
        if not isinstance(row['truth'], str) or type(row.get('accuracy_eligible', True)) is not bool:
            raise ValueError('scalar truth and boolean accuracy mask required')
        value = predict(rule, row['readings'])
        events.append([value == row['truth'], value is not None and value != row['truth'], value is not None])
        accuracy_mask.append(row.get('accuracy_eligible', True))
        clusters.setdefault(row.get('item_id', row['id']), []).append(index)
    matrix = np.asarray(events, float)
    accuracy_mask = np.asarray(accuracy_mask, bool)
    units = list(clusters.values())
    def statistic(sample):
        indices = np.asarray([i for u in sample for i in units[int(u)]], int)
        result = matrix[indices].mean(axis=0)
        ai = indices[accuracy_mask[indices]]
        result[0] = matrix[ai, 0].mean() if len(ai) else np.nan
        return result
    rng = np.random.default_rng(SEED)
    boot = np.asarray([statistic(rng.integers(len(units), size=len(units))) for _ in range(draws)])
    metrics = {}
    for j, name in enumerate(('accuracy', 'false_claim_rate', 'coverage')):
        values = matrix[accuracy_mask, j] if j == 0 else matrix[:, j]
        count, denominator = int(values.sum()), len(values)
        point, low, high = wilson(count, denominator) if denominator else (None, None, None)
        valid = boot[:, j][np.isfinite(boot[:, j])]
        interval = np.quantile(valid, [.025, .975]).tolist() if len(valid) else None
        # common.stats independently reproduces draws where every sample is defined.
        # Its ordinary quantile intentionally propagates NaN for undefined samples;
        # the published kernel reports conditional finite-draw intervals and counts.
        _, blo, bhi = bootstrap_ci(np.arange(len(units)),
            lambda ix: statistic(ix)[j], n_boot=draws, seed=SEED)
        if len(valid) == draws:
            assert np.allclose(interval, [blo, bhi], rtol=0, atol=1e-12)
        else:
            assert np.isnan(blo) and np.isnan(bhi)
        metrics[name] = dict(count=count, denominator=denominator, estimate=point,
            Wilson95=[low, high] if denominator else None, item_bootstrap95=interval,
            defined_bootstrap_draws=len(valid), undefined_bootstrap_draws=draws-len(valid))
    result = dict(total=len(rows), eligible=len(eligible), unavailable=len(rows)-len(eligible), metrics=metrics)
    if include_truth_strata:
        bases = sorted({row.get('truth_basis', 'behaviour-verified') for row in rows})
        result['truth_basis_scores'] = {basis: score([row for row in rows if row.get('truth_basis', 'behaviour-verified') == basis], rule, draws, False) for basis in bases}
        result['truth_basis_scope'] = 'MIXED; see separate strata' if len(bases) > 1 else bases[0]
    return result


def match_candidates(text, candidates):
    if not isinstance(text, str) or not isinstance(candidates, dict) or not candidates:
        raise ValueError('original text/candidate-name-alias roster required')
    result = []
    for name, aliases in candidates.items():
        if not isinstance(name, str) or not name or not isinstance(aliases, (list, tuple)):
            raise ValueError('invalid original candidate roster')
        terms = [name, *aliases]
        if any(not isinstance(v, str) or not v or v.strip() != v for v in terms):
            raise ValueError('invalid original alias')
        if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I) for term in terms):
            result.append(name)
    return sorted(result)


def coverage_gate(rows):
    blocks = {}
    for layer in LAYERS:
        available = [r for r in rows if layer in r['readings']]
        if not available:
            continue
        counts = dict(no_value=0, single=0, dual=0)
        for row in available:
            matches = row['matcher_matches'][layer]
            if any(not isinstance(v, str) for v in matches) or len(set(matches)) != len(matches):
                raise ValueError('invalid matcher identities')
            value = matches[0] if len(matches) == 1 else None
            if row['readings'][layer] != value:
                raise ValueError('matcher/scalar mismatch')
            counts['no_value' if not matches else 'single' if len(matches) == 1 else 'dual'] += 1
        n = len(available)
        blocks[str(layer)] = dict(total=n, unavailable=len(rows)-n, **counts,
            exact_one_coverage=counts['single']/n, passes=10*counts['single'] >= 7*n)
    return dict(blocks=blocks, passes=bool(blocks) and all(v['passes'] for v in blocks.values()), threshold=.70)


def choose(scores, rules, types):
    valid = [r for r in rules if all(scores[t][r]['metrics'] is not None
             and scores[t][r]['metrics']['accuracy']['estimate'] is not None for t in types)]
    if not valid:
        raise ValueError('no candidate evaluable on every training type')
    means = {r: float(np.mean([scores[t][r]['metrics']['accuracy']['estimate'] for t in types])) if r in valid else None for r in rules}
    return max(valid, key=lambda r: means[r]), means


def evaluate(data, draws=DRAWS):
    if set(data) != {f'T{i}' for i in range(1, 7)}:
        raise ValueError('exact T1–T6 required; T7 must not enter selection')
    gate = coverage_gate(data['T4'])
    types = tuple(t for t in sorted(data) if t != 'T4' or gate['passes'])
    scores = {t: {rule: score(data[t], rule, draws) for rule in RULES} for t in sorted(data)}
    if not gate['passes']:
        for rule in ('PAGREE', 'PSTAB'):
            scores['T4'][rule] = dict(total=len(data['T4']), eligible=0, unavailable=0,
                metrics=None, status='NOT_EVALUABLE', reason='T4 exact-one matcher coverage below 70% at a compared block')
    loo = {}
    for held in types:
        train = [t for t in types if t != held]
        adaptive, am = choose(scores, ADAPTIVE, train)
        fixed, fm = choose(scores, FIXED, train)
        aa, ff = scores[held][adaptive]['metrics'], scores[held][fixed]['metrics']
        delta = aa['accuracy']['estimate']-ff['accuracy']['estimate'] if aa is not None and ff is not None and aa['accuracy']['estimate'] is not None and ff['accuracy']['estimate'] is not None else None
        loo[held] = dict(training_types=train, adaptive=adaptive, fixed=fixed,
            adaptive_training_mean=am, fixed_training_mean=fm,
            heldout_adaptive=scores[held][adaptive], heldout_fixed=scores[held][fixed], accuracy_difference=delta)
    adaptive, am = choose(scores, ADAPTIVE, types)
    fixed, fm = choose(scores, FIXED, types)
    return dict(T4_matcher=gate, selection_types=list(types), excluded_selection_types=[] if gate['passes'] else ['T4'],
        scores=scores, leave_one_type_out=loo,
        selection=dict(adaptive=adaptive, fixed=fixed, adaptive_type_means=am, fixed_type_means=fm),
        reading=dict(improvements_at_least_point10=sum(v['accuracy_difference'] is not None and v['accuracy_difference'] >= .10-1e-12 for v in loo.values()),
                     nonpositive=sum(v['accuracy_difference'] is not None and v['accuracy_difference'] <= 0 for v in loo.values()),
                     not_evaluable=sum(v['accuracy_difference'] is None for v in loo.values())),
        bootstrap=dict(draws=draws, seed=SEED, unit='original item within state type, conditions clustered', selection_refit=False), exploratory=True)


def committed_file(path, digest=None, commit='HEAD'):
    p = Path(path).resolve()
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        raise ValueError('real evidence must be committed in the reviewer shared checkout') from None
    raw = p.read_bytes()
    saved = subprocess.check_output(['git', 'show', commit + ':' + rel.as_posix()], cwd=ROOT)
    if raw != saved or (digest and hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError('uncommitted/changed/hash-mismatched evidence: ' + str(rel))
    return raw


def read_pin(pin):
    return json.loads(committed_file(pin['path'], pin.get('sha256'), pin.get('commit', 'HEAD')))


def compare(own, author, path=''):
    differences = []
    if isinstance(own, dict):
        if not isinstance(author, dict):
            return [dict(path=path, own=own, worker=author)]
        for key, value in own.items():
            if key not in author:
                differences.append(dict(path=path+'/'+key, note='worker field absent'))
            else:
                differences += compare(value, author[key], path+'/'+key)
    elif isinstance(own, list):
        if not isinstance(author, list) or len(own) != len(author):
            differences.append(dict(path=path, own=own, worker=author))
        else:
            for i, value in enumerate(own):
                differences += compare(value, author[i], path+'/'+str(i))
    elif isinstance(own, (int, float)) and not isinstance(own, bool):
        # common.stats uses z=1.96; author uses exact normal quantile1.95996398.
        tolerance = 1e-5 if '/Wilson95/' in path else 1e-12
        if not isinstance(author, (int, float)) or abs(own-author) > tolerance:
            differences.append(dict(path=path, own=own, worker=author))
    elif own != author:
        differences.append(dict(path=path, own=own, worker=author))
    return differences


def reproduce(args):
    plan = json.loads(committed_file(args.plan))
    if plan['experiment'] != 'E134' or plan['normalization_status'] != 'AUTHORIZED_FROZEN':
        raise ValueError('authorized frozen normalization required')
    for pin in plan['pins']:
        committed_file(pin['path'], pin['sha256'])
    selection = None
    if plan['phase'] == 'T7':
        # Must verify frozen selection and opening custody before reading T7 rows.
        selection = read_pin(plan['selection'])
        custody = plan['E133_custody']
        if not custody['selected_rule_committed_before_any_output_opened']:
            raise ValueError('prospective custody not established')
        committed_file(custody['receipt'], custody['receipt_sha256'])
    data = read_pin(plan['rows'])
    for rows in data.values():
        for row in rows:
            row['readings'] = {int(k): v for k, v in row['readings'].items()}
            if 'matcher_matches' in row:
                row['matcher_matches'] = {int(k): v for k, v in row['matcher_matches'].items()}
            if not row.get('source_refs') or not row.get('truth_ref'):
                raise ValueError('per-item original source lineage absent')
    if plan['phase'] == 'T1_T6':
        if any('accuracy_eligible' not in row for row in data.get('T6', [])):
            raise ValueError('T6 told-only accuracy mask must be explicitly source-bound')
        own = evaluate(data)
    elif plan['phase'] == 'T7' and set(data) == {'T7'}:
        rules = tuple(dict.fromkeys((selection['adaptive_rule'], 'P44', 'P52', 'P60')))
        own = dict(experiment='E134', prospective=True, selection=plan['selection'],
            scores={r: score(data['T7'], r) for r in rules},
            bootstrap=dict(draws=DRAWS, seed=SEED, unit='original E133 item'))
    else:
        raise ValueError('unexpected phase/population')
    differences = []
    if args.author_results:
        author = json.loads(committed_file(args.author_results))
        if args.author_seal:
            seal = json.loads(committed_file(args.author_seal))
            if seal['files']['RESULTS.json'] != hashlib.sha256(committed_file(args.author_results)).hexdigest():
                raise ValueError('author sealed result hash mismatch')
        differences = compare(own, author)
    return dict(experiment='E134', reviewer='R-3', phase=plan['phase'], independent=own,
        discrepancies=differences, scientific_guard_invoked=False,
        normalization_custody='Must separately verify T4 matcher coverage/gate, T6 told-only accuracy, raw source joins, and actual first-opening timestamps. A boolean receipt is not independent timing proof.',
        Wilson_convention='common.stats z1.96; author exact normal quantile; tolerance1e-5 reported')


def operating_points(rows, draws=DRAWS):
    rules = ('PALL', 'P44', 'P52', 'P60')
    order = ('correct', 'false', 'abstain')
    states = {}
    precision = {}
    for rule in rules:
        outcomes = []
        for row in rows:
            value = predict(rule, row['readings'])
            outcomes.append('abstain' if value is None else 'correct' if value == row['truth'] else 'false')
        states[rule] = outcomes
        k, f = outcomes.count('correct'), outcomes.count('false')
        n = k + f
        _, lo, hi = wilson(k, n) if n else (None, None, None)
        precision[rule] = dict(correct=k, false=f, claims=n, total=len(rows), coverage=n/len(rows),
            estimate=k/n if n else None, Wilson95=[lo,hi] if n else None)
    table = [[sum(a == x and b == y for a,b in zip(states['PALL'], states['P60'])) for y in order] for x in order]
    diffs = {}
    for state, name in [('correct','accuracy_PALL_minus_P60'), ('false','false_claim_PALL_minus_P60')]:
        values = np.asarray([int(a == state)-int(b == state) for a,b in zip(states['PALL'],states['P60'])])
        point, lo, hi = bootstrap_ci(values, n_boot=draws, seed=SEED)
        diffs[name] = dict(estimate=point, item_bootstrap95=[lo,hi], defined_draws=draws, undefined_draws=0)
    conservative = score(rows,'PAGREE',draws)
    k = conservative['metrics']['accuracy']['count']
    n = conservative['metrics']['coverage']['count']
    _, lo, hi = wilson(k,n) if n else (None,None,None)
    conservative['precision_given_claim'] = dict(correct=k,claims=n,estimate=k/n if n else None,Wilson95=[lo,hi] if n else None)
    return dict(experiment='E134',supplement='§248 B',exploratory_post_hoc=True,n_prompts=len(rows),
        paired_differences=diffs,outcome_table=dict(rows='PALL',columns='P60',order=list(order),counts=table),
        precision_given_claim=precision,PAGREE=conservative,
        bootstrap=dict(draws=draws,seed=SEED,unit='original E133 prompt/item',paired=True),no_policy_selection=True)


def local_review(bundle):
    # Explicit later committed ruling overrides shared-input-only restriction for
    # this sealed opaque delivery, on this machine only. Never export these rows.
    authority = subprocess.check_output(['git','show','c0c66589b:projects/g_agreement/BRIEF_UNDERSTAND.md'],cwd=ROOT,text=True)
    if 'T1–T7 opaque per-item evidence locally' not in authority:
        raise ValueError('specific local evidence authority absent')
    base = Path(bundle).resolve()
    expected = ROOT/'cache/g_agreement/understand/e134/wlens_local_review248'
    if base != expected.resolve():
        raise ValueError('only explicitly authorized local delivery directory accepted')
    seal = json.loads((base/'LOCAL_DELIVERY_SEAL.json').read_text())
    if seal.get('local_only') is not True or seal.get('never_push') is not True:
        raise ValueError('local-only delivery disposition absent')
    for name, digest in seal['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or hashlib.sha256((base/relative).read_bytes()).hexdigest() != digest:
            raise ValueError('local delivered member hash mismatch')
    train = json.loads((base/'T1_T6_OPAQUE_ROWS.json').read_text())
    test = json.loads((base/'T7_OPAQUE_ROWS.json').read_text())
    for data in (train,test):
        for rows in data.values():
            for row in rows:
                row['readings'] = {int(k):v for k,v in row['readings'].items()}
                if 'matcher_matches' in row:
                    row['matcher_matches'] = {int(k):v for k,v in row['matcher_matches'].items()}
                if not row.get('source_pointer_sha256') or not row.get('truth_pointer_sha256'):
                    raise ValueError('opaque source/truth hash linkage absent')
    train_result = evaluate(train)
    original = ROOT/'results/g_agreement/understand/e134'
    author_train = json.loads(committed_file(original/'analysis_once/RESULTS.json'))
    author_test = json.loads(committed_file(original/'t7_once/RESULTS.json'))
    author_companion = json.loads(committed_file(original/'companion248/RESULTS.json'))
    test_result = dict(experiment='E134',prospective=True,selection=author_test['selection'],
        scores={rule:score(test['T7'],rule) for rule in ('PALL','P44','P52','P60')},
        bootstrap=dict(draws=DRAWS,seed=SEED,unit='original E133 item'))
    companion = operating_points(test['T7'])
    return dict(experiment='E134',local_evidence_authority='c0c66589b item2',never_publish_per_item=True,
        delivered_members_verified=len(seal['files']),train=train_result,T7=test_result,companion248=companion,
        discrepancies=dict(T1_T6=compare(train_result,author_train),T7=compare(test_result,author_test),
                           companion248=compare(companion,author_companion)),
        scope='Independent equality/policy/clustered bootstrap reproduction; private raw-semantic source normalization is not reconstructed; opaque evidence stays local.')


def self_test():
    # Same synthetic scenarios as committed tests; independent implementation.
    r = {44:'a', 52:'b', 60:'a'}
    assert [predict(p, r) for p in RULES] == ['a','b','a','a','a','a',None]
    assert predict('PALL', {44:'a',52:'b'}) == 'b'
    assert predict('PSTAB', {44:'a',52:None,60:'b'}) == 'b'
    assert predict('PSTAB', {44:'a',52:'a',60:'b'}) == 'a'
    assert predict('PAGREE', {44:None,52:'a',60:'a'}) == 'a'
    assert score([dict(id='one',truth='a',readings={44:'a'})], 'P60', 8)['metrics'] is None
    rows = [dict(id=str(i),truth='a',readings={44:v}) for i,v in enumerate(['a','b',None])]
    assert [score(rows,'P44',8)['metrics'][m]['estimate'] for m in ['accuracy','false_claim_rate','coverage']] == [1/3,1/3,2/3]
    clustered = [dict(id=str(i),item_id='same',truth='a',readings={44:v}) for i,v in enumerate(['a','b'])]
    assert score(clustered,'P44',8)['metrics']['accuracy']['item_bootstrap95'] == [.5,.5]
    data = {f'T{i}':[dict(id=str(j),truth='a',readings={44:'a',52:'a',60:'a'}) for j in range(3)] for i in range(1,7)}
    for row in data['T4']:
        row['matcher_matches'] = {k: [v] for k,v in row['readings'].items()}
    result = evaluate(data,8)
    assert result['selection']['adaptive']=='PALL' and result['selection']['fixed']=='P44'
    assert all(k not in v['training_types'] for k,v in result['leave_one_type_out'].items())
    assert match_candidates('ANN annie Robert', {'Ann':['Annie'], 'Bob':['Robert']}) == ['Ann','Bob']
    assert match_candidates('Joanne Ann2 _Ann Anné', {'Ann':[]}) == []
    for row in data['T4']:
        row['readings'][44] = None
        row['matcher_matches'][44] = []
    excluded = evaluate(data,8)
    assert excluded['excluded_selection_types'] == ['T4']
    assert excluded['scores']['T4']['PSTAB']['metrics'] is None
    masked = [dict(id='told',truth='told',accuracy_eligible=True,readings={44:'told'}), dict(id='untold',truth='not_told',accuracy_eligible=False,readings={44:'told'})]
    assert score(masked,'P44',8)['metrics']['accuracy']['denominator'] == 1
    assert score(masked,'P44',8)['metrics']['coverage']['denominator'] == 2
    data['T7'] = []
    try:
        evaluate(data,8)
    except ValueError:
        pass
    else:
        raise AssertionError('T7 must not enter training')
    operating_rows = [dict(id=str(i), item_id=str(i), truth='a', readings=v) for i,v in enumerate([
        {44:'a',52:'a',60:'a'}, {44:'a',52:'a',60:None}, {44:'b',52:'b',60:None}])]
    op = operating_points(operating_rows, 8)
    assert op['outcome_table']['counts'] == [[1,0,1],[0,0,1],[0,0,0]]
    assert op['no_policy_selection'] is True
    print(json.dumps(dict(status='SYNTHETIC_PASS', real_rows_read=0, author_guard_invoked=False)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--plan')
    p.add_argument('--local-bundle', help='c0c66589b-authorized local-only opaque evidence; never push rows')
    p.add_argument('--author-results')
    p.add_argument('--author-seal')
    args = p.parse_args()
    if args.self_test:
        self_test()
    elif args.local_bundle:
        print(json.dumps(local_review(args.local_bundle), indent=2, sort_keys=True, allow_nan=False))
    elif args.plan:
        print(json.dumps(reproduce(args), indent=2, sort_keys=True, allow_nan=False))
    else:
        p.error('--self-test or --plan required')
