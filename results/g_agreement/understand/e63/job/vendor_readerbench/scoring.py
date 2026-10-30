"""Shared E63 / ReaderBench statistics. No readers, judge calls, or data loading."""
import re
from collections import defaultdict
import numpy as np

D5 = ('topic_content', 'register_genre', 'format_without_value',
      'structural_value', 'generic_other')
E56 = ('states_value', 'names_property_without_value', 'exhibits', 'silent')
RUBRIC_HASHES = {
    'E56': '03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613',
    'D5': 'eb2fa79c52c12e52db83e4ada809f6b5a7f69777c79266cb5d84dbfc65743113',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def regex_values(text, patterns):
    require(isinstance(text, str), 'text must be a string; preserve empty readouts')
    require(set(patterns) == {'A', 'B'}, 'two frozen regex patterns required')
    # Flags are explicit in the frozen expression, e.g. (?i); no word-list rewriting.
    return {v for v, pattern in patterns.items() if re.search(pattern, text)}


def value_score(values, truth):
    require(truth in ('A', 'B') and set(values) <= {'A', 'B'}, 'invalid values')
    if len(values) != 1:
        return 0
    return 1 if truth in values else -1


def cluster_draws(records, scores, draws=2000, seed=20261027):
    """Resample items and retain their full repeat counts; readout-weighted estimand."""
    require(len(records) == len(scores) > 0, 'empty or mismatched score grid')
    groups = defaultdict(list)
    for record, score in zip(records, scores):
        groups[record['item_id']].append(score)
    groups = [groups[k] for k in sorted(groups)]
    sums = np.array([sum(g) for g in groups], dtype=float)
    counts = np.array([len(g) for g in groups])
    rng = np.random.default_rng(seed)
    # Bounded memory for large banks.
    result = np.empty(draws)
    for start in range(0, draws, 100):
        ix = rng.integers(len(groups), size=(min(100, draws-start), len(groups)))
        result[start:start+len(ix)] = sums[ix].sum(1) / counts[ix].sum(1)
    return result


def ci(draws):
    return np.quantile(draws, [.025, .975]).tolist()


def coded(records, patterns, judgments=None):
    ids = [r['id'] for r in records]
    require(len(ids) == len(set(ids)) and ids, 'nonempty unique readout IDs required')
    if judgments is not None:
        require(set(judgments) == set(ids), 'complete judgment grid required; no fallback')
    scores, naming = [], []
    for r in records:
        values = regex_values(r['text'], patterns) if judgments is None else judgments[r['id']]
        scores.append(value_score(values, r['label']))
        naming.append(int(bool(values)))
    return scores, naming


def summarize(records, patterns, judgments=None, draws=2000, seed=20261027):
    scores, naming = coded(records, patterns, judgments)
    return {'n_readouts': len(records), 'n_items': len({r['item_id'] for r in records}),
            'S': float(np.mean(scores)), 'S_ci': ci(cluster_draws(records, scores, draws, seed)),
            'N': float(np.mean(naming)), 'N_ci': ci(cluster_draws(records, naming, draws, seed)),
            'coding': 'blind_judge' if judgments is not None else 'regex'}


def placebo_labels(records, seed=20261029):
    """One random A/B truth per placebo vector, shared by its repeats."""
    rng = np.random.default_rng(seed)
    labels = {k: ('A', 'B')[int(rng.integers(2))]
              for k in sorted({r['item_id'] for r in records})}
    return [dict(r, label=labels[r['item_id']]) for r in records]


def contrast(real, placebo, patterns, reported, draws=2000, seed=20261027):
    placebo = placebo_labels(placebo)
    rs, _ = coded(real, patterns)
    ps, _ = coded(placebo, patterns)
    delta = float(np.mean(rs) - np.mean(ps))
    interval = ci(cluster_draws(real, rs, draws, seed) -
                  cluster_draws(placebo, ps, draws, seed+1))
    return {'real': summarize(real, patterns, draws=draws, seed=seed),
            'placebo': summarize(placebo, patterns, draws=draws, seed=seed),
            'delta_S_regex': delta, 'delta_ci': interval,
            'R_P1': ('PASS' if delta >= .20 and interval[0] > 0 else 'FAIL')
                    if reported else 'NOT_APPLICABLE'}


def validate_judgments(packet, judgments, taxonomy):
    """Validate before joining private truth. Never infer or repair a judge code."""
    p = {x['id']: x for x in packet}
    j = {x['id']: x for x in judgments}
    require(len(p) == len(packet) and len(j) == len(judgments) and set(j) == set(p),
            'judgment grid must match packet exactly')
    categories = D5 if taxonomy == 'D5' else E56
    require(taxonomy in ('D5', 'E56'), 'unknown taxonomy')
    for ident, row in j.items():
        require(row['category'] in categories, 'wrong taxonomy')
        evidence = row.get('evidence')
        require(isinstance(evidence, str) and evidence in p[ident]['readout'], 'nonverbatim evidence')
        empty_ok = row['category'] in ('generic_other', 'silent')
        require(bool(evidence) or empty_ok, 'missing evidence')
        if taxonomy == 'E56':
            values = row.get('values')
            require(isinstance(values, list) and len(values) == len(set(values)) and
                    set(values) <= {'A', 'B'}, 'invalid judge values')
            require(bool(values) == (row['category'] == 'states_value'), 'category/value mismatch')
    return j


def category_shares(records):
    require(bool(records), 'no coded records')
    require(all(r['category'] in D5 for r in records), 'D5 categories required')
    grouped = defaultdict(list)
    for r in records:
        grouped[(r['bank'], r['row'])].append(r)
    def shares(xs):
        return {k: sum(x['category'] == k for x in xs)/len(xs) for k in D5}
    rows = [{'bank': k[0], 'row': k[1], 'n': len(v), 'shares': shares(v)}
            for k, v in sorted(grouped.items())]
    return {'rows': rows, 'n': len(records), 'readout_weighted': shares(records),
            'equal_row': {k: float(np.mean([r['shares'][k] for r in rows])) for k in D5}}


def placebo_tvd(placebo_categories, missed_categories):
    require(len(placebo_categories) == 200, 'R-P2 requires 200 readouts per reader')
    require(bool(missed_categories), 'matching-reader MISSED judgments unavailable')
    require(set(placebo_categories + missed_categories) <= set(D5), 'wrong taxonomy')
    p = {k: placebo_categories.count(k)/len(placebo_categories) for k in D5}
    q = {k: missed_categories.count(k)/len(missed_categories) for k in D5}
    tvd = sum(abs(p[k]-q[k]) for k in D5)/2
    label = ('misses resemble placebo output' if tvd <= .15 else
             'misses are input-specific' if tvd >= .40 else 'intermediate')
    return {'TVD': tvd, 'description': label, 'placebo': p, 'missed': q}
