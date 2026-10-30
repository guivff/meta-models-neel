"""CPU R-D (§42) pooled disagreement AUROC on the frozen X3 test pairs.

Positive = prefilled option differs from the target's frozen unprefilled choice.
Both prefills and all positions/arms stay together in each item/family draw.
Only position a earns the preregistered comparative claim. A missing sentence
position b is unavailable for the entire cohort, never a complete-case metric.
"""
from __future__ import annotations

import hashlib
import json
import math
from numbers import Real
from pathlib import Path

import numpy as np

from projects.g_agreement.r_bench import rd_pretext as protocol
from projects.g_agreement.r_bench.x4_cue_report import _many_aucs, interval

DRAWS = 2000
SEED = 0
REPORT_PATHS = {'analysis': 'analysis.json', 'metadata': 'metadata.json', 'report': 'REPORT.md'}


def output_paths(out):
    return {key: Path(out)/name for key, name in REPORT_PATHS.items()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def registry():
    """No duplicated arm list; a cannot acquire a fictitious prompt-only row."""
    positions = tuple(protocol.POSITIONS)
    arms = {position: tuple(protocol.ARMS_BY_POSITION[position]) for position in positions}
    if set(positions) != {'a', 'b', 'c'} or len(set(positions)) != len(positions):
        raise ValueError('invalid R-D position registry')
    for position, names in arms.items():
        required = {reader+'/'+condition for reader in protocol.READERS for condition in ('natural', 'shuffled')}
        required |= {'text_judge', 'probe/L44'}
        if position != 'a':
            required.add('prompt_only')
        if len(names) != len(set(names)) or set(names) != required:
            raise ValueError('invalid R-D arm registry at position '+position+': unexpected='+str(sorted(set(names)-required))+' missing='+str(sorted(required-set(names))))
    return positions, arms


def rule(gaps):
    """Strict intersection rule at a; no multiplicity correction was requested."""
    judge = gaps['text_judge']['95'][0]
    shuffled = gaps['shuffled']['95'][0]
    return bool(judge is not None and shuffled is not None and judge > .10 and shuffled > .05)


def paired_weights(ids, families, draws=DRAWS):
    """Exactly draws resamples; pair members get identical weights everywhere."""
    if type(draws) is not int or draws < 1:
        raise ValueError('bootstrap draws must be a positive integer')
    samples = {}
    for scheme, labels in (('item', np.repeat(ids, 2).tolist()),
                           ('family', np.repeat(families, 2).tolist())):
        groups = sorted(set(labels))
        index = {name: i for i, name in enumerate(groups)}
        inverse = np.array([index[name] for name in labels], dtype=int)
        rng = np.random.default_rng(SEED)
        weights = np.empty((draws, len(labels)), dtype=float)
        for j in range(draws):
            counts = np.bincount(rng.integers(0, len(groups), len(groups)), minlength=len(groups))
            weights[j] = counts[inverse]
        samples[scheme] = weights
    return samples


def _expected(expected_items):
    raw = expected_items['items'] if isinstance(expected_items, dict) else expected_items
    items, splits = {}, {}
    for item in raw:
        if not {'id', 'split', 'family', 'preferred'} <= item.keys():
            raise ValueError('frozen item missing identity/family/preference')
        if not isinstance(item['id'], str) or not item['id'] or not isinstance(item['family'], str) or not item['family']:
            raise ValueError('invalid frozen ID/family')
        if item['id'] in items:
            raise ValueError('duplicate frozen item ID')
        if item['split'] not in ('pool', 'test') or item['preferred'] not in ('A', 'B'):
            raise ValueError('invalid frozen split/preference')
        items[item['id']] = item
        splits.setdefault(item['family'], set()).add(item['split'])
    if any(len(values) != 1 for values in splits.values()):
        raise ValueError('pool/test family leakage')
    ids = sorted(ident for ident, item in items.items() if item['split'] == 'test')
    if not ids or len({items[ident]['family'] for ident in ids}) < 2:
        raise ValueError('need a nonempty frozen test cohort with at least two families')
    return items, ids


def _failure_map(position_failures, items):
    failed = {}
    for failure in position_failures or []:
        if failure.get('position') != 'b':
            raise ValueError('only position b may be unavailable')
        key = (failure.get('id'), failure.get('prefilled'))
        item = items.get(key[0])
        if item is None or key[1] not in ('A', 'B'):
            raise ValueError('unknown failed b prefill '+str(key))
        if not isinstance(failure.get('reason'), str) or not failure['reason'].strip():
            raise ValueError('missing b failure reason')
        if key in failed:
            raise ValueError('duplicate b failure declaration')
        if 'split' in failure and failure['split'] != item['split']:
            raise ValueError('failed b split mismatch '+str(key))
        failed[key] = dict(failure, split=item['split'])
    return failed


def analyze(rows, expected_items, draws=DRAWS, *, position_failures=None):
    """Require all frozen test cells, except explicitly unavailable whole b.

    ``position_failures`` is a list of ``{position:'b', id, prefilled, reason}``.
    A failure in pool or test suppresses ALL position-b estimates. The caller may supply
    zero b rows (whole position withheld) or complete arm sets for successful
    prefills; none are silently used for a complete-case estimate. Any missing
    a/c cell, undeclared b absence, partial arm set, or failed-prefill score fails.
    Pool smoke rows are separate and are rejected here.
    """
    positions, arms_by_position = registry()
    items, ids = _expected(expected_items)
    failed = _failure_map(position_failures, items)
    rows = list(rows)
    fields = {'id', 'prefilled', 'position', 'arm', 'score', 'split', 'family', 'dispreferred', 'outputs'}
    prov_fields = ('run_id', 'run_kind', 'code_sha256')
    have_provenance = any(any(key in row for key in prov_fields) for row in rows)
    provenance = set()
    cells = {}
    for row in rows:
        if not fields <= row.keys():
            raise ValueError('missing score row fields '+str(sorted(fields-row.keys()))+' id='+str(row.get('id')))
        item = items.get(row['id'])
        if item is None or item['split'] != 'test' or row['split'] != 'test':
            raise ValueError('unknown or non-test score row '+str((row['id'],row['prefilled'],row['position'],row['arm'])))
        if row['family'] != item['family'] or row['prefilled'] not in ('A', 'B'):
            raise ValueError('score family/prefill mismatch '+str((row['id'],row['prefilled'],row['position'],row['arm'])))
        if type(row['dispreferred']) is not bool or row['dispreferred'] != (row['prefilled'] != item['preferred']):
            raise ValueError('score disagreement label mismatch '+str((row['id'],row['prefilled'],row['position'],row['arm'])))
        position = row['position']
        if position not in positions or row['arm'] not in arms_by_position[position]:
            raise ValueError('unknown arm/position or structurally absent prompt_only '+str((row['id'],row['prefilled'],position,row['arm'])))
        if isinstance(row['score'], bool) or not isinstance(row['score'], Real) or not math.isfinite(row['score']):
            raise ValueError('nonfinite or nonnumeric score '+str((row['id'],row['prefilled'],position,row['arm'])))
        if not isinstance(row['outputs'], dict) or not row['outputs']:
            raise ValueError('missing reader output '+str((row['id'],row['prefilled'],position,row['arm'])))
        if position == 'b' and (row['id'], row['prefilled']) in failed:
            raise ValueError('score present for declared missing b prefill '+str((row['id'],row['prefilled'],position,row['arm'])))
        if have_provenance:
            if not all(isinstance(row.get(key), str) and row[key] for key in prov_fields):
                raise ValueError('missing row provenance '+str((row['id'],row['prefilled'],position,row['arm'])))
            code = row['code_sha256']
            if len(code) != 64 or any(char not in '0123456789abcdef' for char in code):
                raise ValueError('invalid row code SHA256')
            provenance.add(tuple(row[key] for key in prov_fields))
            if len(provenance) != 1:
                raise ValueError('mixed row provenance '+str((row['id'],row['prefilled'],position,row['arm'])))
        key = (row['id'], row['prefilled'], position, row['arm'])
        if key in cells:
            raise ValueError('duplicate score cell '+str(key))
        cells[key] = row
    y = np.array([int(option != items[ident]['preferred']) for ident in ids for option in ('A', 'B')])
    families = [items[ident]['family'] for ident in ids]
    weights = paired_weights(ids, families, draws)
    output = {}
    for position in positions:
        arms = arms_by_position[position]
        expected = {(ident, option, position, arm) for ident in ids for option in ('A', 'B') for arm in arms}
        actual = {key for key in cells if key[2] == position}
        present_prefills = {(key[0], key[1]) for key in actual}
        coverage = {'attempted_pairs': len(ids), 'attempted_prefills': 2*len(ids),
                    'expected_score_cells': len(expected), 'saved_score_cells': len(actual),
                    'complete_scored_prefills': len(present_prefills),
                    'declared_failed_prefills': sum(items[key[0]]['split']=='test' for key in failed) if position == 'b' else 0,
                    'declared_failed_pool_prefills': sum(items[key[0]]['split']=='pool' for key in failed) if position == 'b' else 0,
                    'attempted_pool_prefills': 2*sum(item['split']=='pool' for item in items.values()),
                    'unscored_prefills': 2*len(ids)-len(present_prefills)}
        if position == 'b' and failed:
            for ident, option in present_prefills:
                if {(ident, option, position, arm) for arm in arms} - actual:
                    raise ValueError('partial arm set in unavailable b position '+str((ident,option))+': missing='+str(sorted({(ident,option,position,arm) for arm in arms}-actual)))
            output[position] = {'status': 'MISSING_POSITION', 'coverage': coverage,
                                'failures': [failed[key] for key in sorted(failed)],
                                'arms': {arm: {'auroc': None, 'ci': {'95': [None, None], '90': [None, None]},
                                               'verdict': ['MISSING_POSITION']} for arm in arms},
                                'reason': 'At least one pool or test sentence position is missing; no whole-cohort or complete-case b estimate is reported.'}
            continue
        if actual != expected:
            raise ValueError(f'missing/extra score cells at {position}: missing={len(expected-actual)}, extra={len(actual-expected)}, first_missing={sorted(expected-actual)[:1]}, first_extra={sorted(actual-expected)[:1]}')
        matrix = np.array([[cells[(ident, option, position, arm)]['score'] for arm in arms]
                           for ident in ids for option in ('A', 'B')])
        point = _many_aucs(y, matrix, np.ones((1, len(y))))[0]
        samples = {name: _many_aucs(y, matrix, values) for name, values in weights.items()}
        if any(not np.isfinite(values).all() for values in samples.values()):
            raise ValueError('undefined paired bootstrap: each resampled pair must retain both labels')
        results = {arm: {'auroc': float(point[j]),
                         'ci': interval({name: values[:, j] for name, values in samples.items()})}
                   for j, arm in enumerate(arms)}
        for reader in protocol.READERS:
            arm = reader+'/natural'
            i = arms.index(arm)
            comparisons = {'text_judge': 'text_judge', 'shuffled': reader+'/shuffled', 'probe/L44': 'probe/L44'}
            if 'prompt_only' in arms:
                comparisons['prompt_only'] = 'prompt_only'
            gaps = {}
            for name, comparator in comparisons.items():
                j = arms.index(comparator)
                gaps[name] = dict(interval({scheme: values[:, i]-values[:, j] for scheme, values in samples.items()}),
                                  point=float(point[i]-point[j]), comparator=comparator)
            results[arm]['gaps'] = gaps
            if position == 'a':
                results[arm]['primary_rule_passed'] = rule(gaps)
                results[arm]['verdict'] = ['READERS WIN PRE-TEXT'] if rule(gaps) else ['UNDERPOWERED/MIXED']
            else:
                results[arm]['verdict'] = ['DESCRIPTIVE SECONDARY POSITION']
        output[position] = {'status': 'COMPLETE', 'coverage': coverage, 'arms': results,
                            'bootstrap_valid_draws': {name: draws for name in samples}}
    primary = {reader: output['a']['arms'][reader+'/natural']['primary_rule_passed'] for reader in protocol.READERS}
    return {'status': 'COMPLETE' if not failed else 'SECONDARY_POSITION_MISSING',
            'test_pairs': len(ids), 'test_prefills': len(y), 'families': len(set(families)),
            'draws': draws, 'seed': SEED, 'positions': output, 'primary_rule': primary,
            'expected_items_sha256': digest([items[ident] for ident in sorted(items)]),
            'scores_sha256': digest([cells[key] for key in sorted(cells)]),
            'inference': {'estimand': 'pooled tie-aware AUROC across both prefills; not within-pair concordance',
                          'positive_label': 'prefilled option differs from frozen unprefilled Qwen preference',
                          'resampling': 'paired item and family draws; both prefills and all positions/arms kept together',
                          'interval': 'conservative minimum-lower/maximum-upper envelope of percentile intervals',
                          'primary_position': 'a', 'secondary_positions': ['b', 'c'],
                          'rule': '95% lower(reader-text_judge) > 0.10 AND 95% lower(reader-shuffled) > 0.05',
                          'multiplicity': 'unadjusted per-reader tests, no BH or family-wise guarantee',
                          'probe': 'per-position L44 pool-trained fit; intervals conditional on frozen fit',
                          'missing_b': 'whole position unavailable; no imputation or complete-case AUROC'},
            'example_ids': sorted(np.random.default_rng(SEED).choice(ids, min(10, len(ids)), replace=False).tolist())}


def _ci(bounds):
    return 'unavailable' if bounds[0] is None else f'[{bounds[0]:.4f}, {bounds[1]:.4f}]'


def write_report(out, analysis, metadata):
    """Exclusive small report outputs; callers supply operational provenance."""
    paths = output_paths(out)
    if any(path.exists() for path in paths.values()):
        raise FileExistsError('report artifact already exists')
    lines = ['# R-D: readers before explanatory text (BRIEF_R §42)', '',
             f"{analysis['test_pairs']} frozen test pairs, {analysis['test_prefills']} prefills, {analysis['families']} choice families.", '',
             'The primary metric is pooled AUROC for identifying a dispreferred prefill. Intervals retain both prefills in every paired draw and quote the conservative item/family envelope.', '',
             f"{analysis['draws']:,} attempts per scheme, seed 0. Reader tests are unadjusted; there is no family-wise or false-discovery guarantee.", '',
             '| Position | Attempted prefills | Complete scored prefills | Saved/expected score cells | Declared failed test prefills | Declared failed pool prefills | Status |',
             '|---|---:|---:|---:|---:|---:|---|']
    for position, data in analysis['positions'].items():
        cov = data['coverage']
        lines.append(f"| {position} | {cov['attempted_prefills']} | {cov['complete_scored_prefills']} | {cov['saved_score_cells']}/{cov['expected_score_cells']} | {cov['declared_failed_prefills']} | {cov['declared_failed_pool_prefills']} | {data['status']} |")
    lines += ['', '| Position | Arm | AUROC | Wider 95% CI | Verdict |', '|---|---|---:|---|---|']
    for position, data in analysis['positions'].items():
        for arm, result in data['arms'].items():
            value = 'unavailable' if result['auroc'] is None else f"{result['auroc']:.4f}"
            lines.append(f"| {position} | {arm} | {value} | {_ci(result['ci']['95'])} | {', '.join(result.get('verdict', ['descriptive baseline']))} |")
    lines += ['', '| Position | Reader | Comparator | AUROC difference | Wider 95% CI | Wider 90% CI |', '|---|---|---|---:|---|---|']
    for position, data in analysis['positions'].items():
        for reader in protocol.READERS:
            for name, gap in data['arms'][reader+'/natural'].get('gaps', {}).items():
                lines.append(f"| {position} | {reader} | {name} | {gap['point']:.4f} | {_ci(gap['95'])} | {_ci(gap['90'])} |")
    lines += ['', 'Only position a earns the primary claim: reader minus text judge must have a 95% lower bound above 0.10, and reader minus shuffled state must have a 95% lower bound above 0.05. Positions b and c are descriptive; they cannot rescue a failed primary rule.', '',
              'Prompt-only is structurally absent at a; no zero score is substituted. Text judge is evaluated at a. Probe comparisons condition on the separate frozen pool fit for that position.', '']
    if analysis['positions']['b']['status'] == 'MISSING_POSITION':
        lines += ['Position b is unavailable for the full cohort. Saved successful-prefill rows are counted above but never used for a complete-case AUROC. The declared boundary failures are retained in analysis.json; positions a and c retain their complete paired cohorts.', '']
    encoded = {paths['analysis']: json.dumps(analysis, sort_keys=True, indent=2, allow_nan=False)+'\n',
               paths['metadata']: json.dumps(metadata, sort_keys=True, indent=2, allow_nan=False)+'\n',
               paths['report']: '\n'.join(lines)}
    Path(out).mkdir(parents=True, exist_ok=True)
    for path, text in encoded.items():
        with path.open('x') as handle:
            handle.write(text)
    return analysis
