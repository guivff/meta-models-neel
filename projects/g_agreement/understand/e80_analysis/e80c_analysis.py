"""E80c once-only analysis: R-X3 (confirmatory, Oracle, pooled) and R-X4 (descriptive), BRIEF_UNDERSTAND §197 E80c
(registered 11:10 CET) + clarification 1 (11:20 CET, PCA condition). Integrator-authored per Guiv 2026-10-28.

Frozen choices (committed before any judged E80/E80c output is opened):
- pass per readout: score80.passed (family headline scorer); UNPARSEABLE/missing = missing, never fail.
- S = items whose Oracle readout passes under none (E80 judgments). Falls are computed on the complete-case subset of S
  with a non-missing verdict under all three ablations; n excluded is reported.
- fall_c = 1 - pass rate under condition c on that subset. Item bootstrap: 2000 draws, seed 20261028, percentile 95% CI.
- R-X3 MET iff fall_J >= 0.30, fall_J - fall_random >= 0.20 with bootstrap lower bound > 0, and
  fall_J - fall_PCA >= 0.10 with bootstrap lower bound > 0. FALSIFIED iff fall_J <= fall_random + 0.05 (point estimates).
  If the random part is met but not the PCA part: NOT MET, labelled 'readers depend on high-variance directions, not
  specifically the J-space'.
- R-X4 (descriptive): the same per family and for the NLA (exploratory block-44 basis at block 42); J-fraction against
  pass under none (AUROC, means); norm ratios per condition from the sealed NORM_RATIOS (flag > 1.5).
- Sensitivity: the same R-X3 numbers excluding path/address-redacted readouts.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
from .score80 import passed

HERE = Path(__file__).resolve().parent
CONDITIONS = ('J_ablated', 'random_ablated', 'PCA_ablated')
DRAWS, SEED = 2000, 20261028


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def require(ok, msg):
    if not ok:raise ValueError(msg)


def verdicts(judgments, readouts, join, packets, bank_conditions):
    """{(reader, condition): {unit_id: pass or None}} from one bank's terminal grid and its CPU-only join."""
    text = {x['id']: x['readout'] for x in readouts};out = {}
    require({r['id'] for r in judgments} == set(text) == set(join), 'complete opaque grid and join')
    for r in judgments:
        j = join[r['id']];cond = j['condition']
        require(cond in bank_conditions, 'condition in bank')
        cell = out.setdefault((j['reader'], cond), {})
        require(j['unit_id'] not in cell, 'one readout per item per reader per condition')
        cell[j['unit_id']] = passed(r, packets[j['unit_id']], text[r['id']])
    return out


def falls(none, cond, items):
    """Complete-case falls on S = items passing under none."""
    S = [i for i in items if none.get(i) is True]
    keep = [i for i in S if all(cond[c].get(i) is not None for c in CONDITIONS)]
    fall = {c: (1 - sum(cond[c][i] for i in keep)/len(keep)) if keep else None for c in CONDITIONS}
    return S, keep, fall


def bootstrap(keep, cond):
    rng = random.Random(SEED);dr, dp = [], []
    for _ in range(DRAWS):
        b = [keep[rng.randrange(len(keep))] for _ in keep]
        f = {c: 1 - sum(cond[c][i] for i in b)/len(b) for c in CONDITIONS}
        dr.append(f['J_ablated']-f['random_ablated']);dp.append(f['J_ablated']-f['PCA_ablated'])
    q = lambda xs: [sorted(xs)[int(0.025*DRAWS)], sorted(xs)[int(0.975*DRAWS)-1]]
    return q(dr), q(dp)


def rule(none, cond, items):
    S, keep, fall = falls(none, cond, items)
    if len(keep) < 2:return dict(status='NOT EVALUABLE', n_pass_none=len(S), n_complete=len(keep))
    ci_r, ci_p = bootstrap(keep, cond)
    dr = fall['J_ablated']-fall['random_ablated'];dp = fall['J_ablated']-fall['PCA_ablated']
    rand_ok = fall['J_ablated'] >= 0.30 and dr >= 0.20 and ci_r[0] > 0
    pca_ok = dp >= 0.10 and ci_p[0] > 0
    if fall['J_ablated'] <= fall['random_ablated']+0.05:status = 'FALSIFIED (readers read outside the J-space)'
    elif rand_ok and pca_ok:status = 'MET'
    elif rand_ok:status = 'NOT MET: readers depend on high-variance directions, not specifically the J-space'
    else:status = 'NOT MET'
    return dict(status=status, n_pass_none=len(S), n_complete=len(keep), n_excluded_missing=len(S)-len(keep), falls=fall,
                J_minus_random=dict(estimate=dr, ci95=ci_r), J_minus_PCA=dict(estimate=dp, ci95=ci_p))


def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y];neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:return None
    return sum((p > n)+0.5*(p == n) for p in pos for n in neg)/(len(pos)*len(neg))


def analyze(spec):
    for path, digest in spec['pins'].items():require(sha(path) == digest, 'input pin: '+path)
    packets = {x['id']: x for x in read(spec['judge_packets'])};plan = read(spec['plan']);items = plan['item_ids']
    require(len(packets) == len(items) == 518, 'frozen 518-item grid')
    none = verdicts(read(spec['e80_judgments']), read(spec['e80_readouts']), read(spec['e80_join']), packets, ('none',))
    abl = verdicts(read(spec['e80c_judgments']), read(spec['e80c_readouts']), read(spec['e80c_join']), packets, CONDITIONS)
    redacted = {read(spec['e80c_join']).get(x['id'], read(spec['e80_join']).get(x['id'], {})).get('unit_id') for x in
                read(spec['e80c_redaction'])['affected']+read(spec['e80_redaction'])['affected']}
    fam = {i: packets[i]['family'] for i in items};out = dict(experiment='E80c', registration='§197 E80c 11:10 CET + clarification 1 11:20 CET')
    for reader in ('oracle', 'nla'):
        n = none[(reader, 'none')];c = {k: abl[(reader, k)] for k in CONDITIONS}
        pooled = rule(n, c, items)
        out[reader] = dict(pooled=pooled, per_family={f: rule(n, c, [i for i in items if fam[i] == f]) for f in sorted(set(fam.values()))},
                           redaction_excluded=rule(n, c, [i for i in items if i not in redacted]),
                           pass_rate_none={k: (sum(n[i] for i in items if n.get(i) is not None)/max(1, sum(n.get(i) is not None for i in items))) for k in ['all']},
                           missing={k: sum(v.get(i) is None for i in items) for k, v in [('none', n)]+list(c.items())})
    out['R_X3'] = out['oracle']['pooled']['status']
    norms = read(spec['norm_ratios']);jf = norms['j_fraction_by_block']
    for reader, block in (('oracle', '44'), ('nla', '42')):
        n = none[(reader, 'none')];xs = [(jf[block][k], n[i]) for k, i in enumerate(items) if n.get(i) is not None]
        out[reader]['j_fraction_vs_pass_none'] = dict(block=block, auroc=auroc([x for x, _ in xs], [y for _, y in xs]),
            mean_pass=sum(x for x, y in xs if y)/max(1, sum(1 for _, y in xs if y)), mean_fail=sum(x for x, y in xs if not y)/max(1, sum(1 for _, y in xs if not y)))
    out['norm_ratios'] = {k: {m: v[m] for m in ('mean', 'minimum', 'maximum', 'above_1_5', 'n')} for k, v in norms['per_cell'].items()}
    out['R_X4'] = 'DESCRIPTIVE'
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, default=HERE/'SPEC_E80c.json');a = p.parse_args()
    spec = read(a.spec);guard = Path(spec['guard']);out = Path(spec['out'])
    require(not guard.exists() and not out.exists(), 'once only: guard or output exists')
    result = analyze(spec)  # all input pins verified before the guard is consumed
    guard.parent.mkdir(parents=True, exist_ok=True);guard.write_text(json.dumps(dict(spec_sha256=sha(a.spec)))+'\n')
    out.mkdir(parents=True);(out/'RESULTS.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    files = {f.name: sha(f) for f in out.iterdir()}
    (out/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(experiment='E80c', status='COMPLETE_ONCE', spec_sha256=sha(a.spec), files=files), indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(R_X3=result['R_X3'], oracle=result['oracle']['pooled']), sort_keys=True))


if __name__ == '__main__':main()
