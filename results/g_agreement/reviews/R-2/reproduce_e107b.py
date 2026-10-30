"""Independent E107b statistical core; author-schema binding PENDING.

No author imports, file reads, guards, paid calls, or execution entrypoint.
Input is CPU-local reviewer-normalized rows. Real use requires independently
verified original-source joins and the published W-mech2 adapter contract.
"""
import math
import numpy as np
from common.stats import bootstrap_ci


def compare(rows, *, draws=5000, seed=0):
    """Original E107 naming-conditioned rates, joint source-item bootstrap.

    Each row has row/item_id and oracle/forecast dicts with belief (0/1/None)
    and named (bool/None). System naming/missing masks remain independent.
    All planned identities must be supplied; absent cells use explicit nulls.
    These conventions are provisional inheritance from E107, to be checked
    against the new committed author adapter before any real-result review.
    """
    rows = sorted(rows, key=lambda x: (x['row'], x['item_id']))
    keys = [(x['row'], x['item_id']) for x in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate original source-item identity')
    values, counts = {}, {}
    for arm in ('oracle', 'forecast'):
        vals = []
        n = dict(planned=len(rows), kept=0, missing=0, not_stating_value=0)
        for row in rows:
            cell = row[arm]  # Missing system keys are a binding failure.
            b, named = cell['belief'], cell['named']
            if b is not None and (type(b) not in (int, bool) or b not in (0, 1)):
                raise ValueError('belief must be a validated binary code or null')
            if named is not None and type(named) is not bool:
                raise ValueError('named must be boolean or null')
            if b is None or named is None:
                n['missing'] += 1; vals.append(np.nan)
            elif not named:
                n['not_stating_value'] += 1; vals.append(np.nan)
            else:
                n['kept'] += 1; vals.append(float(b))
        values[arm], counts[arm] = np.array(vals), n

    def rate(a):
        return float(np.mean(a[np.isfinite(a)])) if np.isfinite(a).any() else np.nan

    def summarize(fn):
        if not rows:
            return dict(estimate=None, CI95=None, undefined_draws=draws)
        draws_seen = []
        def metric(ix):
            value = fn(ix)
            draws_seen.append(value)
            return value
        p, lo, hi = bootstrap_ci(np.arange(len(rows)), fn=metric,
                                n_boot=draws, seed=seed)
        return dict(estimate=p if math.isfinite(p) else None,
                    CI95=[lo, hi] if math.isfinite(lo) and math.isfinite(hi) else None,
                    undefined_draws=sum(not math.isfinite(x) for x in draws_seen[:draws]))

    result = dict(counts=counts, draws=draws, seed=seed,
                  unit='original (row,item_id), paired; separate naming denominators')
    for arm in values:
        result[arm] = summarize(lambda ix, arm=arm: rate(values[arm][ix]))
    result['difference'] = summarize(lambda ix: rate(values['oracle'][ix]) - rate(values['forecast'][ix]))
    p, ci = result['difference']['estimate'], result['difference']['CI95']
    result['descriptive_R_OL1'] = ('NOT EVALUABLE' if p is None or ci is None else
                                  'MET' if round(p, 12) >= .20 and ci[0] > 0 else 'NOT MET')
    return result


def reproduce_normalized(items):
    """Bind independently verified CPU-normalized E107b items, not raw codes.

    Source contract55a20526b uses systems.outside for the new forecast. Raw
    source references/letters/evidence and both-target missingness must first
    be independently validated; this function does not replace that audit.
    """
    if len(items) != 199:
        raise ValueError('exact original 199-item cohort required')
    rows = []
    for x in items:
        if x['bank'] != 'E82' or x['cohort'] != 'belief_wrong':
            raise ValueError('wrong source cohort')
        rows.append(dict(row=x['row'],item_id=x['item_id'],
                         oracle=x['systems']['oracle'], forecast=x['systems']['outside']))
    return compare(rows)


def check_worker(reviewer, worker):
    """Compare every reported pooled estimate/CI/count; no author invocation."""
    pooled = worker['pooled']
    for arm, w in [('oracle','oracle'),('forecast','outside')]:
        c = reviewer['counts'][arm]
        if any(pooled['counts'][w][k] != v for k, v in c.items()):
            raise ValueError('worker denominator mismatch')
        if pooled['counts'][w]['unavailable'] != 0:
            raise ValueError('unavailable planned system')
    if pooled['unmatched_source_items'] != 0:
        raise ValueError('unmatched original source items')
    for arm, w in [('oracle','oracle'),('forecast','outside'),('difference','difference')]:
        for k in ('estimate','CI95'):
            a,b=reviewer[arm][k],pooled[w][k]
            if (a is None) != (b is None) or (a is not None and not np.allclose(a,b,rtol=0,atol=2e-15)):
                raise ValueError('worker statistic mismatch: '+arm+'/'+k)
    if reviewer['descriptive_R_OL1'] != worker['forecast_survival']:
        raise ValueError('worker reading mismatch')
    return True
