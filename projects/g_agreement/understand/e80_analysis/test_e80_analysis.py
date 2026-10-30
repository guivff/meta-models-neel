"""Synthetic tests for the E80 R-X1/R-X2 analysis (no real data)."""
import random
from . import e80_analysis as A


def test_mantel_haenszel_known_value():
    r = A.mantel_haenszel([(10, 5, 5, 10)])  # single 2x2: OR = (10*10)/(5*5) = 4
    assert abs(r['OR']-4) < 1e-12 and r['ci95'][0] < 4 < r['ci95'][1]
    h = A.mantel_haenszel([(10, 0, 5, 10)])  # no visible failures: corrected, flagged
    assert h['haldane_anscombe'] and abs(h['OR']-(10.5*10.5)/(0.5*5.5)) < 1e-9


def test_stratified_auroc_ignores_cross_family_pairs():
    score = [3, 1, 30, 10];y = [True, False, True, False];fam = ['a', 'a', 'b', 'b']
    assert A.strat_auroc(score, y, fam) == 1.0
    assert A.strat_auroc([1, 3, 10, 30], y, fam) == 0.0


def rows_for(n, vis, jrank, lrank, fams=('multihop', 'poetry')):
    rows, orig = {}, {}
    for k in range(n):
        i = f'E80:x:{k:03d}';f = fams[k % len(fams)]
        rows[i] = {'family': f, 'J': {'visible_top10': vis(k), 'best_target_rank1': jrank(k)}}
        orig[i] = {'J': {'visible_top10': False, 'best_target_rank1': jrank(k)*3}, 'logit': {'best_target_rank1': lrank(k)}}
    return rows, orig


def test_rules_met_and_falsified():
    rng = random.Random(1);n = 200
    rows, orig = rows_for(n, lambda k: k < 60, lambda k: 1+k, lambda k: 1+rng.randrange(1000))
    passes = {i: (k < 55 or 60 <= k < 75) for k, i in enumerate(rows)}  # pass tracks low J rank, independent of logit rank
    A.PERMS = 199
    r = A.reader_rules(passes, rows, orig)
    assert r['R_X1']['status'] == 'MET' and r['R_X2']['status'] == 'MET' and r['R_X2']['lr']['p'] < 0.01
    passes = {i: (k % 3 == 0) for k, i in enumerate(rows)}  # unrelated to visibility
    r = A.reader_rules(passes, rows, orig)
    assert r['R_X1']['status'] in ('FALSIFIED', 'NOT MET (underpowered)') and r['R_X2']['status'] == 'NOT MET'


def test_missing_excluded_and_counted():
    rows, orig = rows_for(20, lambda k: k < 5, lambda k: 1+k, lambda k: 1+k)
    passes = {i: (None if k == 0 else k < 8) for k, i in enumerate(rows)}
    A.PERMS = 19
    r = A.reader_rules(passes, rows, orig)
    assert r['n'] == 19 and r['n_missing'] == 1


def test_lr_adds_information_only_when_j_rank_matters():
    rng = random.Random(2);n = 300;fam = ['a']*n
    j = [1+rng.randrange(500) for _ in range(n)];lr = [1+rng.randrange(500) for _ in range(n)]
    y = [jj < 100 for jj in j]
    assert A.lr_test(y, fam, lr, j)['p'] < 1e-6
    y2 = [ll < 100 for ll in lr]
    assert A.lr_test(y2, fam, lr, j)['p'] > 0.01


def test_no_within_family_pairs_is_not_evaluable():
    rows, orig = rows_for(20, lambda k: k < 5, lambda k: 1+k, lambda k: 1+k)
    A.PERMS = 19
    r = A.reader_rules({i: (k % 2 == 0) for k, i in enumerate(rows)}, rows, orig)  # one family all pass, other all fail
    assert r['R_X2']['status'] == 'NOT EVALUABLE'
