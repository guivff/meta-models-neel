"""E80 once-only analysis: R-X1, R-X2 (BRIEF_UNDERSTAND E80, 06:35 CET; §197 E80b, 07:50 CET; E80 note 07:05 CET).
Integrator-authored per Guiv 2026-10-28. Exploratory side analysis since §198 (stated in the output).

Frozen choices (committed before any judged E80 output is opened):
- pass per readout: score80.passed; UNPARSEABLE/missing are excluded and counted.
- Forecast of record: E80b (21151275 / seal bc056368): J-visible = visible_top10; rank = best_target_rank1.
  The original 189c1161 forecast (J and logit lens) is reported beside it as a measurement-error comparison.
  The logit-lens control rank comes from 189c1161 (E80b recomputed J only); this is stated in the output.
- R-X1 (Oracle confirmatory; NLA reported): family-stratified Mantel-Haenszel OR of pass on J-visible, Robins-Breslow-
  Greenland 95% CI; if the MH OR is undefined (zero margin), +0.5 is added to every cell (Haldane-Anscombe) and
  flagged. MET iff OR >= 2 and CI lower bound > 1. FALSIFIED iff OR <= 1.2. Otherwise NOT MET, labelled
  underpowered when the CI includes 1 (E80 note).
- R-X2 (Oracle confirmatory; NLA reported): stratified AUROC of lower J rank predicting pass, counting within-family
  pairs only; one-sided stratified permutation p (pass permuted within family, 10,000 permutations, seed 20261028,
  p = (k+1)/(n+1)). LR test in a within-family logistic model: pass ~ family + log(logit rank1) vs + log(J rank1),
  chi-square(1). MET iff AUROC >= 0.65 and permutation p < 0.01 and LR p < 0.01.
- Reported: per-family pass rates; top-50 visibility and its rate; WorkspaceBench published floors are not in the
  packaged export and are marked NOT PACKAGED rather than invented.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import numpy as np
from .score80 import passed
from .e80c_analysis import verdicts, sha, read, require

HERE = Path(__file__).resolve().parent
PERMS, SEED = 10000, 20261028


def mantel_haenszel(strata, correct=False):
    """strata: list of (a, b, c, d) = (visible pass, visible fail, invisible pass, invisible fail). RBG CI."""
    R = S = P_R = PS_QR = Q_S = 0.0
    for a, b, c, d in strata:
        n = a+b+c+d
        if n == 0:continue
        r, s = a*d/n, b*c/n;p, q = (a+d)/n, (b+c)/n
        R += r;S += s;P_R += p*r;PS_QR += p*s+q*r;Q_S += q*s
    if R == 0 or S == 0:
        if correct:return dict(OR=None, ci95=None, note='undefined even after Haldane-Anscombe correction')
        out = mantel_haenszel([tuple(x+0.5 for x in s) for s in strata if sum(s)], correct=True)
        return dict(out, haldane_anscombe=True, note='uncorrected MH OR undefined (zero margin); +0.5 added to every cell')
    OR = R/S;var = P_R/(2*R*R)+PS_QR/(2*R*S)+Q_S/(2*S*S);se = math.sqrt(var)
    return dict(OR=OR, ci95=[math.exp(math.log(OR)-1.96*se), math.exp(math.log(OR)+1.96*se)])


def strat_auroc(score, y, fam):
    """Within-family pairs only; higher score should mean pass."""
    num = den = 0.0
    for f in set(fam):
        pos = [s for s, t, g in zip(score, y, fam) if g == f and t];neg = [s for s, t, g in zip(score, y, fam) if g == f and not t]
        for p in pos:
            for q in neg:num += (p > q)+0.5*(p == q)
        den += len(pos)*len(neg)
    return num/den if den else None


def perm_p(score, y, fam):
    obs = strat_auroc(score, y, fam)
    if obs is None:return None, None  # no within-family pass/fail pairs
    rng = random.Random(SEED);idx = {}
    for k, f in enumerate(fam):idx.setdefault(f, []).append(k)
    k_ge = 0;yy = list(y)
    for _ in range(PERMS):
        for f, ks in idx.items():
            vals = [yy[k] for k in ks];rng.shuffle(vals)
            for k, v in zip(ks, vals):yy[k] = v
        k_ge += strat_auroc(score, yy, fam) >= obs
    return obs, (k_ge+1)/(PERMS+1)


def logit_ll(X, y):
    """Maximum log-likelihood of a logistic regression by Newton-Raphson (ridge 1e-8 for separation stability)."""
    X = np.asarray(X, float);y = np.asarray(y, float);b = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1/(1+np.exp(-X@b));W = p*(1-p)
        H = X.T@(X*W[:, None])+1e-8*np.eye(X.shape[1]);g = X.T@(y-p)
        step = np.linalg.solve(H, g);b += step
        if np.max(np.abs(step)) < 1e-10:break
    p = np.clip(1/(1+np.exp(-X@b)), 1e-12, 1-1e-12)
    return float(np.sum(y*np.log(p)+(1-y)*np.log(1-p)))


def lr_test(y, fam, logit_rank, j_rank):
    fams = sorted(set(fam));base = [[1.0 if f == g else 0.0 for g in fams] for f in fam]
    X0 = [row+[math.log(lr)] for row, lr in zip(base, logit_rank)];X1 = [row+[math.log(jr)] for row, jr in zip(X0, j_rank)]
    stat = max(0.0, 2*(logit_ll(X1, y)-logit_ll(X0, y)))
    return dict(chi2=stat, p=math.erfc(math.sqrt(stat/2)))  # chi-square(1) survival


def reader_rules(pass_by_item, rows, orig):
    items = [i for i in rows if pass_by_item.get(i) is not None]
    fam = [rows[i]['family'] for i in items];y = [bool(pass_by_item[i]) for i in items]
    strata = []
    for f in sorted(set(fam)):
        sub = [i for i in items if rows[i]['family'] == f];vis = lambda i: rows[i]['J']['visible_top10']
        strata.append((sum(1 for i in sub if vis(i) and pass_by_item[i]), sum(1 for i in sub if vis(i) and not pass_by_item[i]),
                       sum(1 for i in sub if not vis(i) and pass_by_item[i]), sum(1 for i in sub if not vis(i) and not pass_by_item[i])))
    mh = mantel_haenszel(strata)
    if mh['OR'] is None:x1 = 'NOT EVALUABLE'
    elif mh['OR'] <= 1.2:x1 = 'FALSIFIED'
    elif mh['OR'] >= 2 and mh['ci95'][0] > 1:x1 = 'MET'
    else:x1 = 'NOT MET (underpowered)' if mh['ci95'][0] <= 1 else 'NOT MET'
    jr = [rows[i]['J']['best_target_rank1'] for i in items];lr = [orig[i]['logit']['best_target_rank1'] for i in items]
    au, p = perm_p([-r for r in jr], y, fam);lrt = lr_test(y, fam, lr, jr)
    x2 = 'NOT EVALUABLE' if au is None else ('MET' if au >= 0.65 and p < 0.01 and lrt['p'] < 0.01 else 'NOT MET')
    oj = [orig[i]['J']['best_target_rank1'] for i in items]
    return dict(n=len(items), n_missing=len(rows)-len(items), R_X1=dict(status=x1, strata=dict(zip(sorted(set(fam)), strata)), **mh),
                R_X2=dict(status=x2, auroc=au, perm_p=p, lr=lrt),
                original_forecast_comparison=dict(auroc_J_189c1161=strat_auroc([-r for r in oj], y, fam), auroc_logit_189c1161=strat_auroc([-r for r in lr], y, fam),
                    n_visible_189c1161=sum(orig[i]['J']['visible_top10'] for i in items)),
                descriptive=dict(n_visible_top10=sum(rows[i]['J']['visible_top10'] for i in items), n_top50=sum(r <= 50 for r in jr),
                    pass_rate_top50=(sum(yy for yy, r in zip(y, jr) if r <= 50)/max(1, sum(r <= 50 for r in jr))),
                    pass_rate_by_family={f: sum(yy for yy, g in zip(y, fam) if g == f)/fam.count(f) for f in sorted(set(fam))},
                    floors='NOT PACKAGED (WorkspaceBench published floors are not in the frozen export)'))


def analyze(spec):
    for path, digest in spec['pins'].items():require(sha(path) == digest, 'input pin: '+path)
    packets = {x['id']: x for x in read(spec['judge_packets'])}
    rows = {r['id']: r for r in read(spec['e80b_forecast'])['rows']};orig = {r['id']: r for r in read(spec['original_forecast'])['rows']}
    require(len(rows) == len(orig) == len(packets) == 518 and set(rows) == set(orig) == set(packets), 'frozen 518 items in both forecasts')
    none = verdicts(read(spec['e80_judgments']), read(spec['e80_readouts']), read(spec['e80_join']), packets, ('none',))
    out = dict(experiment='E80', forecast_of_record='E80b 21151275 (seal bc056368)', status_note='exploratory side analysis since §198 reframing')
    for reader in ('oracle', 'nla'):out[reader] = reader_rules(none[(reader, 'none')], rows, orig)
    out['R_X1'] = out['oracle']['R_X1']['status'];out['R_X2'] = out['oracle']['R_X2']['status']
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, default=HERE/'SPEC_E80.json');a = p.parse_args()
    spec = read(a.spec);guard = Path(spec['guard']);out = Path(spec['out'])
    require(not guard.exists() and not out.exists(), 'once only: guard or output exists')
    result = analyze(spec)
    guard.parent.mkdir(parents=True, exist_ok=True);guard.write_text(json.dumps(dict(spec_sha256=sha(a.spec)))+'\n')
    out.mkdir(parents=True);(out/'RESULTS.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    (out/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(experiment='E80', status='COMPLETE_ONCE', spec_sha256=sha(a.spec),
        files={f.name: sha(f) for f in out.iterdir()}), indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(R_X1=result['R_X1'], R_X2=result['R_X2']), sort_keys=True))


if __name__ == '__main__':main()
