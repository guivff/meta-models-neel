"""E81 §198/§204cl2 CPU analysis. No model, network, rubric or row selection.

Invalid judgments are missing (§judging interface), not zero. S uses kept
readouts; all-missing-correct/wrong bounds retain the full planned denominator.
Oracle baseline rates are frozen source analyses, with explicitly identified E49
probe-only supplements scored by the unchanged, source-sealed E49 regex.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import numpy as np

ARMS = ('generic', 'oracle_wording')
SEED, DRAWS = 20261027, 2000

def normalize_source_polarity(joins, e73_source_keys):
    """Map local labels to the exact packet A/B letters, without editing source.

    E73 labels are 0→A, 1→B; E49/E57/E59 labels are 1→A, 0→B.
    Every E73 assignment must agree with its original sealed private key.
    """
    normalized=[]
    for j in joins:
        x=dict(j)
        if j['bank']=='e73':
            key=e73_source_keys[j['source_id']]
            assert key['label']==j['label'] and key['state']==j['row']
            assert key['value']==('B' if j['label']==1 else 'A')
            x['label']=1 if key['value']=='A' else 0
        else:
            assert j['bank'] in ('e49','e57','e59')
        normalized.append(x)
    return normalized

def signed(code, label):
    assert label in (0, 1)
    assert code['category'] in ('states_value', 'names_property_without_value', 'exhibits', 'silent')
    values = code['values']
    assert isinstance(values, list) and len(values) == len(set(values)) and set(values) <= {'A', 'B'}
    if code['category'] != 'states_value':
        assert not values
        return 0
    assert values
    if len(values) == 2:
        return 0
    return 1 if values[0] == ('A' if label == 1 else 'B') else -1

def rate(values):
    n = len(values)
    kept = np.array([v for v in values if v is not None], dtype=float)
    m = n - len(kept)
    assert n > 0
    total = int(kept.sum())
    if len(kept):
        rng = np.random.default_rng(SEED)
        samples = kept[rng.integers(0, len(kept), size=(DRAWS, len(kept)))].mean(axis=1)
        ci = [float(x) for x in np.quantile(samples, [.025, .975])]
        s = total / len(kept)
    else:
        s, ci = None, None
    return dict(N_planned=n, kept=len(kept), missing=m, missing_fraction=m/n,
                flag_missing_over_5pct=m/n > .05, signed_sum=total,
                correct_only=sum(v == 1 for v in values), wrong_only=sum(v == -1 for v in values),
                S=s, CI95=ci, S_missing_bounds=[(total-m)/n, (total+m)/n],
                bootstrap_unit='item', bootstrap_seed=SEED, bootstrap_draws=DRAWS)

def le(x, y):
    return x is not None and x <= y + 1e-12

def ge(x, y):
    return x is not None and x >= y - 1e-12

def rule(rows, field='S'):
    """Fixed row denominators; missing-only rows cannot silently disappear."""
    missed = [r for r in rows if le(r['oracle_S'], .10)]
    reported = [r for r in rows if ge(r['oracle_S'], .20)]
    def value(r):
        return r[field] if field == 'S' else r['S_missing_bounds'][0 if field == 'lower' else 1]
    a = sum(le(value(r), .10) for r in missed)
    b = sum(ge(value(r), .20) for r in reported)
    f = sum(le(value(r), .10) for r in rows)
    evaluable = bool(missed and reported) and all(value(r) is not None for r in missed+reported)
    passed = evaluable and Fraction(a, len(missed)) >= Fraction(4, 5) and Fraction(b, len(reported)) >= Fraction(1, 2)
    falsified = bool(rows) and Fraction(f, len(rows)) >= Fraction(9, 10)
    return dict(status='NOT_EVALUABLE_CHANNEL_INSENSITIVE' if falsified else ('MET' if passed else 'NOT_MET' if evaluable else 'NOT_EVALUABLE_MISSING_OR_EMPTY_STRATUM'),
                R_T1_conditions_met=bool(passed), channel_insensitive_falsifier=falsified,
                oracle_missed_rows=len(missed), text_misses_in_oracle_missed=a,
                missed_fraction=a/len(missed) if missed else None,
                oracle_reported_rows=len(reported), text_reports_in_oracle_reported=b,
                reported_fraction=b/len(reported) if reported else None,
                all_rows=len(rows), text_missed_all_rows=f, text_missed_all_fraction=f/len(rows) if rows else None,
                text_reports_reader_misses=[r['key'] for r in rows if le(r['oracle_S'], .10) and ge(value(r), .20)],
                reader_reports_text_misses=[r['key'] for r in rows if ge(r['oracle_S'], .20) and le(value(r), .10)])

def bound_rule(rows):
    """Joint worst/best assignments, choosing each row's endpoint per criterion.

    A single lower/upper assignment alone is not the worst case of the conjunction:
    the missed stratum needs low S, while the reported stratum needs high S.
    """
    lo, hi = rule(rows, 'lower'), rule(rows, 'upper')
    nm, nr = lo['oracle_missed_rows'], lo['oracle_reported_rows']
    definite = bool(nm and nr) and Fraction(hi['text_misses_in_oracle_missed'], nm) >= Fraction(4, 5) and Fraction(lo['text_reports_in_oracle_reported'], nr) >= Fraction(1, 2)
    possible = bool(nm and nr) and Fraction(lo['text_misses_in_oracle_missed'], nm) >= Fraction(4, 5) and Fraction(hi['text_reports_in_oracle_reported'], nr) >= Fraction(1, 2)
    return dict(R_T1_conditions_definite=definite, R_T1_conditions_possible=possible,
                falsifier_definite=hi['channel_insensitive_falsifier'], falsifier_possible=lo['channel_insensitive_falsifier'],
                all_missing_wrong=lo, all_missing_correct=hi)

def analyze(joins, judgments, original, baselines):
    byid = {x['id']: x for x in joins}
    assert len(byid) == len(joins)
    assert all(x['arm'] in ARMS for x in joins)
    expected = defaultdict(set)
    for x in joins:
        expected[(x['bank'], x['row'], x['arm'])].add(x['source_id'])
    cohort = {(b,r) for b,r,a in expected}
    assert set(baselines) == {b+'/'+r for b,r in cohort}
    for b,r in cohort:
        assert expected[(b,r,'generic')] == expected[(b,r,'oracle_wording')]
    def score(records, full):
        assert len({x['id'] for x in records}) == len(records)
        assert set(x['id'] for x in records) == set(byid) if full else set(x['id'] for x in records) <= set(byid)
        groups = defaultdict(list)
        for x in records:
            j = byid[x['id']]
            assert x['status'] in ('KEPT', 'UNPARSEABLE')
            if x['status'] == 'UNPARSEABLE':
                assert x['code'] is None
                v = None
            else:
                assert x['code']['id'] == x['id']
                v = signed(x['code'], j['label'])
            groups[(j['bank'],j['row'],j['arm'])].append((j['source_id'],v))
        out = {}
        for arm in ARMS:
            rows=[]
            for b,r in sorted(cohort):
                xs=sorted(groups[(b,r,arm)])
                if not xs:
                    continue
                assert len({x[0] for x in xs}) == len(xs)
                key=b+'/'+r; baseline=baselines[key]
                rows.append(dict(key=key, bank=b, row=r, arm=arm, oracle_S=baseline['S'],
                    oracle_missing=baseline.get('missing'), oracle_baseline_source=baseline['source_kind'],
                    **rate([x[1] for x in xs])))
            out[arm]=dict(role='PRIMARY' if arm=='generic' else 'SECONDARY_CANNOT_CHANGE_PRIMARY',
                rows=rows, rule=rule(rows), missingness_sensitivity=bound_rule(rows))
        return out
    primary=score(judgments, True)
    old_ids={x['id'] for x in original}
    matched=score([x for x in judgments if x['id'] in old_ids], False)
    legacy=score(original, False)
    agreement=Counter()
    main={x['id']:x for x in judgments}
    for x in original:
        a=main[x['id']]
        agreement['pairs']+=1
        if x['status']=='KEPT' and a['status']=='KEPT':
            agreement['common_kept']+=1
            agreement['category_equal']+=x['code']['category']==a['code']['category']
            agreement['value_set_equal']+=set(x['code']['values'])==set(a['code']['values'])
            agreement['signed_equal']+=signed(x['code'],byid[x['id']]['label'])==signed(a['code'],byid[x['id']]['label'])
    return dict(experiment='E81', rule='R-T1', registration='§198 E81; §204 clarification2; §172 signed item rate',
                primary_arm='generic', arms=primary, original_rubric_sensitivity=dict(
                scope='SEEDED_25PCT_MATCHED_SUBSAMPLE_ONLY_NOT_FULL_GRID', amended_matched=matched,
                original_matched=legacy, agreement=dict(agreement)),
                judgments=len(judgments), original_rubric_judgments=len(original),
                primary_verdict=primary['generic']['rule']['status'], review_status='R-2_REVIEW_PENDING')
