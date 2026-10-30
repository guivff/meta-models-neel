"""Frozen §208 estimands; pure CPU functions, including withdrawn c/d rules."""
import numpy as np
REPORTED = ('format_plan','language_plan','tense_implicit','language_continuation','fact_recall')
MISSED = ('nesting_depth','indent_level','page_range_digit')
ROWS = REPORTED + MISSED
CONDITIONS = ('transplant','J_swap','perp_J_swap','R_swap','perp_R_swap')
DRAWS, SEED = 2000, 20261027

class Bootstrap:
    """One joint item draw per row, reused across all readers/conditions.

    Missing scores retain their own denominators; undefined draws invalidate CI.
    Independent rows use independent streams from the one registered RNG.
    """
    def __init__(self, cells):
        self.cells, self.indices = cells, {}
        rng = np.random.default_rng(SEED)
        for row in ROWS:
            selected = [v for (r,_,_),v in cells.items() if r == row]
            if not selected:
                continue
            ids = sorted(selected[0])
            if not ids or any(set(v) != set(ids) for v in selected):
                raise ValueError('unequal within-row item grid')
            self.indices[row] = (ids, rng.integers(0,len(ids),(DRAWS,len(ids))))
    def sample(self, key):
        if key not in self.cells:
            return None, np.full(DRAWS,np.nan), 0, 0
        ids, ix = self.indices[key[0]]
        a = np.array([np.nan if self.cells[key][i] is None else self.cells[key][i] for i in ids])
        if not np.isin(a[np.isfinite(a)],[-1,0,1]).all():
            raise ValueError('invalid signed score')
        x = a[ix]; n = np.isfinite(x).sum(axis=1)
        draws = np.divide(np.nansum(x,axis=1),n,out=np.full(DRAWS,np.nan),where=n>0)
        kept = int(np.isfinite(a).sum())
        return (float(np.nanmean(a)) if kept else None),draws,len(ids),kept
    def stat(self, row, condition, other=None, reader='oracle'):
        point, draws, total, kept = self.sample((row,reader,condition))
        result = dict(total=total,kept=kept,missing=total-kept,over_5_percent=(total-kept)*20>total)
        if other is not None:
            p,d,n,k = self.sample((row,reader,other))
            result['other_kept'] = k
            point = None if point is None or p is None else point-p
            draws = draws-d
        return dict(result,estimate=point,CI95=np.quantile(draws,[.025,.975]).tolist() if np.isfinite(draws).all() else None)
    def group_difference(self, condition):
        groups=[]
        for group in (REPORTED,MISSED):
            ss=[self.sample((r,'oracle',condition)) for r in group]
            if any(s[0] is None for s in ss):
                return dict(estimate=None,CI95=None)
            groups.append((float(np.mean([s[0] for s in ss])),np.mean([s[1] for s in ss],axis=0)))
        draws=groups[0][1]-groups[1][1]
        return dict(estimate=groups[0][0]-groups[1][0],CI95=np.quantile(draws,[.025,.975]).tolist() if np.isfinite(draws).all() else None)

def ge(s, value):
    return None if s['estimate'] is None else round(s['estimate'],12) >= value

def lower(s, value):
    return None if s['CI95'] is None else s['CI95'][0] > value

def conjunction(*tests):
    return False if False in tests else None if None in tests else True

def count_rule(tests, n):
    passed=sum(t is True for t in tests); unknown=sum(t is None for t in tests)
    return dict(status='MET' if passed>=n else 'NOT EVALUABLE' if passed+unknown>=n else 'NOT MET',passing=passed,unknown=unknown,required=n)

def active(b):
    pc=[b.stat(r,'transplant') for r in REPORTED]
    falsifier=count_rule([None if s['estimate'] is None else round(s['estimate'],12)<.20 for s in pc],3)
    gate=falsifier['status']!='NOT MET'
    c3=[]; dominance=[]; complement=[]
    for r in REPORTED:
        j=b.stat(r,'J_swap'); delta=b.stat(r,'J_swap','R_swap')
        c3.append(conjunction(ge(j,.30),ge(delta,.20),lower(delta,0)))
        dominance.append(ge(b.stat(r,'J_swap','perp_J_swap'),.20))
        complement.append(ge(b.stat(r,'perp_J_swap'),.30))
    suff=count_rule(c3,3)
    both=count_rule(complement,3)
    hc=dict(status='DESCRIPTIVE',on_R_C3_rows={r:dominance[i] for i,r in enumerate(REPORTED) if c3[i] is True},complement=both,
            interpretation='both components carry it' if both['status']=='MET' else 'see row contrasts')
    if gate:
        suff=dict(status='NOT EVALUABLE',reason='R-PC falsifier met or unresolved')
        hc=dict(status='NOT EVALUABLE',reason='R-PC falsifier met or unresolved')
    return {'R-PC':count_rule([conjunction(ge(s,.50),lower(s,.30)) for s in pc],4),
            'R-PC_falsifier':falsifier,'R-C3':suff,'H-C3b':hc}

def original_withdrawn(b, probe_shifts):
    """Audit-only original c/d: never invoked on production a/b data.

    Condition names d:2, d_J:0.5, d_perp:1, u_tok:2, d@36:1.
    Manipulation shifts are row-level signed target-direction dev-probe shifts.
    H-T/H-U lack a registered dose pooling rule: report each dose separately.
    """
    c4=[]
    for r in REPORTED:
        tests=[]
        for a in ('0.5','1','2'):
            d=b.stat(r,'d_J:'+a,'d_perp:'+a)
            tests.append(conjunction(ge(b.stat(r,'d_J:'+a),.30),ge(d,.30),lower(d,0)))
        c4.append(True if True in tests else None if None in tests else False)
    delta=b.group_difference('d:2')
    ratio=None
    if all(r in probe_shifts and np.isfinite(probe_shifts[r]) for r in ROWS):
        missed=float(np.mean([probe_shifts[r] for r in MISSED]))
        if missed != 0:
            ratio=float(np.mean([probe_shifts[r] for r in REPORTED]))/missed
    check=None if ratio is None else .5<=ratio<=2
    missed_tests=[ge(b.stat(r,'d:'+a),.30) for r in MISSED for a in ('0.5','1','2')]
    falsifier_tests=[None if delta['estimate'] is None else round(delta['estimate'],12)<=.10]+missed_tests
    rd=count_rule([conjunction(ge(delta,.30),lower(delta,0),check)],1)
    rd.update(difference=delta,manipulation_ratio=ratio,manipulation_check=check,falsifier=count_rule(falsifier_tests,1))
    ht={}
    for a in ('0.5','1','2','4'):
        differences=[b.stat(r,'u_tok:'+a,'d_J:'+a) for r in REPORTED]
        ht[a]=dict(token_not_excluded=count_rule([ge(d,-.10) for d in differences],3),
                   J_beats_token=count_rule([None if d['estimate'] is None else round(d['estimate'],12)<=-.20 for d in differences],3),rule_bearing=a!='4')
    hu={a:dict(contrast=b.stat('nesting_depth','d@36:'+a,'d:'+a),processed_reportable=ge(b.stat('nesting_depth','d@36:'+a,'d:'+a),.20)) for a in ('1','2')}
    result={'R-C4':count_rule(c4,3),'R-D1':rd,'H-T':ht,'H-U':hu}
    if active(b)['R-PC_falsifier']['status']!='NOT MET':
        return {k:dict(status='NOT EVALUABLE',reason='R-PC falsifier met or unresolved',audit=v) for k,v in result.items()}
    return result

def production(cells):
    b=Bootstrap(cells)
    return dict(prior='E79 Arm A R-C1 NOT MET (0/3), sealed 23ed827a; reported first.',
                bootstrap=dict(draws=DRAWS,seed=SEED,unit='item',joint_within_row=True),
                rules=dict(active(b),**{k:dict(status='WITHDRAWN',authority='69f8c08e4') for k in ('R-C4','R-D1','H-T','H-U')}),
                rows={r:{reader:{c:b.stat(r,c,reader=reader) for c in CONDITIONS} for reader in ('oracle','nla')} for r in ROWS},
                contrasts={r:{reader:{c:b.stat(r,'J_swap',c,reader=reader) for c in ('R_swap','perp_J_swap')} for reader in ('oracle','nla')} for r in ROWS},
                readers=dict(oracle='confirmatory',nla='exploratory; block 42, block-44 basis'))
