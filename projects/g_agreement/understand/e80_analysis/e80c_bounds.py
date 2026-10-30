"""E80c missingness bounds and truncation count (§212, 6e182a1b). Descriptive companion to e80c_analysis (7b8433cc),
which stays the registered R-X3/R-X4 analysis. Committed before the E80c grid exists.

For each reader, on S = items passing under none: falls per ablation with every missing verdict set to pass (lowest
fall) and to fail (highest fall), and the J-minus-random / J-minus-PCA differences at the two extremes.
Truncations = E80c records that the integrator resume recorded UNPARSEABLE after a charged finish_reason 'length'.
"""
import argparse
import json
from pathlib import Path
from .e80c_analysis import CONDITIONS, verdicts, read, sha, require


def bounds(none, cond, items):
    S = [i for i in items if none.get(i) is True];out = {}
    for fill, name in ((True, 'missing_as_pass'), (False, 'missing_as_fail')):
        fall = {c: (1 - sum((cond[c].get(i) if cond[c].get(i) is not None else fill) for i in S)/len(S)) if S else None for c in CONDITIONS}
        out[name] = dict(falls=fall, J_minus_random=None if not S else fall['J_ablated']-fall['random_ablated'],
                         J_minus_PCA=None if not S else fall['J_ablated']-fall['PCA_ablated'])
    out['n_pass_none'] = len(S);out['missing_by_condition'] = {c: sum(cond[c].get(i) is None for i in S) for c in CONDITIONS}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--truncations', type=int, required=True);p.add_argument('--out', type=Path, required=True);a = p.parse_args()
    spec = read(a.spec)
    for path, digest in spec['pins'].items():require(sha(path) == digest, 'input pin: '+path)
    require(not a.out.exists(), 'once only')
    packets = {x['id']: x for x in read(spec['judge_packets'])};items = read(spec['plan'])['item_ids']
    none = verdicts(read(spec['e80_judgments']), read(spec['e80_readouts']), read(spec['e80_join']), packets, ('none',))
    abl = verdicts(read(spec['e80c_judgments']), read(spec['e80c_readouts']), read(spec['e80c_join']), packets, CONDITIONS)
    res = dict(experiment='E80c', kind='DESCRIPTIVE missingness bounds (§212)', charged_length_truncations=a.truncations,
               **{r: bounds(none[(r, 'none')], {c: abl[(r, c)] for c in CONDITIONS}, items) for r in ('oracle', 'nla')})
    a.out.write_text(json.dumps(res, indent=2, sort_keys=True)+'\n');print(json.dumps(res['oracle'], sort_keys=True)[:600])


if __name__ == '__main__':main()
