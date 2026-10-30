"""E127 Wilson reporting re-pointed to paired paraphrase codes; no fitting."""
from projects.g_agreement.e127_analysis.common import rate, require, criterion

BLOCKS = (44, 52, 60)
CODES = ('X', 'Y', 'other', 'none', 'multiple')

def code(cell):
    if cell is None:
        return None
    values = cell['values']
    require(type(values) is list and all(type(v) is str and v in ('X','Y','OTHER') for v in values), 'literal asserted set')
    require(len(values) == len(set(values)), 'unique asserted set')
    if len(values) > 1:
        return 'multiple'
    return {'X':'X','Y':'Y','OTHER':'other'}[values[0]] if values else 'none'



def analyze(rows, other_policy='xy_only'):
    require(other_policy == 'xy_only', 'explicit frozen other-value policy required')
    require(40 <= len(rows) <= 84, '40..84 selected pairs; smaller screens are screen-only')
    require(len({r['pair_id'] for r in rows}) == len(rows), 'unique pairs')
    reports = {}
    for block in BLOCKS:
        cells = []
        paired = []
        tracking = []
        prior = []
        unknown_pairs = 0
        multiple_pairs = 0
        for row in rows:
            require(set(row['blocks']) == {str(b) for b in BLOCKS}, 'exact three blocks')
            arms = row['blocks'][str(block)]
            require(set(arms) == {'A', 'B'}, 'exact paraphrase pair')
            values = []
            for arm in ('A', 'B'):
                cell = arms[arm]
                label = code(cell)
                cells.append(label)
                if cell is None:
                    values.append(None)
                elif label in ('X', 'Y'):
                    values.append(label)
                else:
                    values.append('')
            # Clarification 2 says EVERY pair with a multiple readout, even
            # when its partner is missing/non-value, enters sensitivity as zero.
            if any(code(arms[a]) == 'multiple' for a in ('A','B')):
                multiple_pairs += 1
            if any(arms[a] is None for a in ('A','B')):
                unknown_pairs += 1
                paired.append(None)
            else:
                both = all(values)
                paired.append(int(both))
                if both:
                    tracking.append(int(values == ['X','Y']))
                    prior.append(int(values[0] == values[1]))
        coverage = rate([None if c is None else int(c in ('X','Y','other','multiple')) for c in cells])
        tr, pr = rate(tracking), rate(prior)
        sensitivity = dict(tracking=rate(tracking+[0]*multiple_pairs), prior=rate(prior+[0]*multiple_pairs), added_multiple_pairs=multiple_pairs, eligible_pairs=len(tracking)+multiple_pairs, used_for_verdict=False)
        reports[str(block)] = dict(tracking=tr, prior=pr, coverage=coverage, xy_coverage=rate([None if c is None else int(c in ('X','Y')) for c in cells]), both_value_pair_coverage=rate(paired),
            planned_pairs=len(rows), eligible_pairs=len(tracking), unknown_pairs=unknown_pairs,
            multiple_readouts=sum(c=='multiple' for c in cells), multiple_pairs=multiple_pairs, sensitivity=sensitivity,
            categories={code:rate([None if c is None else int(c==code) for c in cells]) for code in CODES},
            tracking_reading=criterion(tr,.60,.45), prior_reading=criterion(pr,.50))
    return dict(experiment='E140',descriptive=True,blocks=reports,other_policy=other_policy,
        block60_readings={'follows_forward_pass':reports['60']['tracking_reading'],'prior_or_resolving_dominates':reports['60']['prior_reading']},
        ceiling={'value':1.0,'construction_only':True,'new_run':False},
        multiple_value_authority='252_clarification2_d1d15ccf2',
        missing_policy='Sensitivity adds every pair with a multiple readout as neither tracking nor prior, including missing partners. Terminal missing excluded from observed rates, with explicit coverage; none is observed non-value. No cross-block complete-case restriction.',new_calls=0)
