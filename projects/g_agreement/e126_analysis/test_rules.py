from copy import deepcopy
import pytest
import numpy as np
from . import rules as r


def item(i='x',row='fact_recall',gap=2.,R=.6,I=.7,control=.1):
    clean=-1.;steered=clean+gap
    patches={b:{d:{p:(steered-(R if p=='read_token' else control)*gap if d=='restore' else clean+(I if p=='read_token' else control)*gap)for p in r.PATCHES}for d in r.DIRECTIONS}for b in r.BLOCKS}
    return dict(item_id=i,row=row,clean=clean,steered=steered,patches=patches)


def blocks(main=.6,early=.1,control=.1,insert_control=.9,lower=.3):
    return {b:{d:{p:dict(estimate=(early if b==44 else main) if p=='read_token' else (control if d=='restore' else insert_control),CI95=[lower,.9])for p in r.PATCHES}for d in r.DIRECTIONS}for b in r.BLOCKS}


def test_original_E105_pair_orientation_and_average():
    pairs=[[-3,-5],[-4,-10]]
    assert r.log_odds(pairs,'A','A',2)==4
    assert r.log_odds(pairs,'B','A',2)==-4
    assert r.log_odds(pairs,'B','B',2)==4
    for bad in ([],[[-3,float('nan')]],[[True,-2]],[[1,-2]]):
        with pytest.raises(ValueError):r.log_odds(bad,'A','A',1)


def test_restoration_insertion_symmetry_with_two_controls():
    x=r.item_ratios(item())
    for b in r.BLOCKS:
        assert x['ratios'][b]['restore']['read_token']==pytest.approx(.6)
        assert x['ratios'][b]['insert']['read_token']==pytest.approx(.7)
        assert x['ratios'][b]['restore']['earlier_token']==pytest.approx(.1)
        assert x['ratios'][b]['insert']['random_norm_matched']==pytest.approx(.1)


def test_ratio_per_item_before_median_not_ratio_of_means():
    xs=[item('a',gap=1.,R=0),item('b',gap=1.,R=0),item('c',gap=100.,R=1.)]
    values=[r.item_ratios(x)['ratios'][52]['restore']['read_token']for x in xs]
    assert r.median_stat(values,draws=50)['estimate']==0
    assert sum(x['steered']-x['patches'][52]['restore']['read_token']for x in xs)/sum(x['steered']-x['clean']for x in xs)>.9


def test_no_clipping_negative_gap_and_overshoot():
    x=r.item_ratios(item(gap=-2.,R=1.7,I=-.4))
    assert x['ratios'][60]['restore']['read_token']==pytest.approx(1.7)
    assert x['ratios'][60]['insert']['read_token']==pytest.approx(-.4)


def test_zero_denominator_retained_not_epsilon_or_cohort_shrink():
    x=r.item_ratios(item(gap=0))
    assert x['zero_native_gap'] is True and x['ratios'][44]['restore']['read_token'] is None
    stat=r.median_stat([None,.8],draws=10)
    assert stat['estimate'] is None and stat['n']==2 and stat['n_defined']==1


def test_RMED1_registered_boundaries_and_only_restore_controls():
    z=blocks(main=.5,early=.15,control=.15,insert_control=.99,lower=.25001)
    assert r.classify(z)['R_MED1']=='MET'
    for b in (52,56):z[b]['restore']['read_token']['CI95'][0]=.25
    assert r.classify(z)['R_MED1']=='NOT MET'
    assert r.classify(z)['control_scope']==['restore']


def test_every_control_block_both_types_required():
    z=blocks();z[60]['restore']['random_norm_matched']['estimate']=.15001
    assert r.classify(z)['R_MED1']=='NOT MET'
    z=blocks();z[48]['restore']['earlier_token']['estimate']=.15001
    assert r.classify(z)['R_MED1']=='NOT MET'


def test_later_existential_and_R44_condition():
    z=blocks(main=.1);z[56]['restore']['read_token']=dict(estimate=.7,CI95=[.4,.9])
    assert r.classify(z)['R_MED1']=='MET'
    z[44]['restore']['read_token']['estimate']=.15001
    assert r.classify(z)['R_MED1']=='NOT MET'


def test_falsifier_all_five_blocks_controls_and_missing():
    z=blocks(main=.15,early=.15,control=.15)
    assert r.classify(z)['falsifier']=='MET'
    z[48]['restore']['read_token']['estimate']=.15001
    assert r.classify(z)['falsifier']=='NOT MET'
    z=blocks(main=.1);z[52]['restore']['read_token']['estimate']=None
    assert r.classify(z)['falsifier']=='NOT EVALUABLE'


def test_full_original_rows_and_raw_odds_retained():
    records=[item(str(i),row=row)for row,n in r.ROWS.items()for i in range(n)]
    result,private=r.analyze(records,draws=10)
    assert result['rows']['fact_recall']['n_items']==84 and result['rows']['language_plan']['n_items']==50
    assert len(private)==134 and private[0]['raw_log_odds']['clean']==-1
    assert result['bootstrap']['statistic']=='median'
    with pytest.raises(ValueError):r.analyze(records[:-1],draws=10)
    with pytest.raises(ValueError):r.analyze(records+[records[0]],draws=10)


def test_missing_patch_or_nonfinite_fails_without_dropping():
    x=item();del x['patches'][60]['insert']['earlier_token']
    with pytest.raises(ValueError):r.item_ratios(x)
    x=item();x['patches'][48]['restore']['read_token']=float('inf')
    with pytest.raises(ValueError):r.item_ratios(x)


def test_median_bootstrap_reuses_common_stats_exactly():
    from common.stats import bootstrap_ci
    values=[-.3,.2,.7,2.4];point,lo,hi=bootstrap_ci(values,fn=np.median,n_boot=25,seed=r.SEED)
    actual=r.median_stat(values,draws=25)
    assert actual['estimate']==point and actual['CI95']==[lo,hi]


def test_language_cannot_promote_fact_confirmatory_rule():
    records=[]
    for row,n in r.ROWS.items():
        for i in range(n):
            x=item(str(i),row=row,R=.1 if row=='fact_recall' else .8)
            x['patches'][44]['restore']['read_token']=x['steered']-.1*(x['steered']-x['clean'])
            records.append(x)
    result,_=r.analyze(records,draws=10)
    assert result['R_MED1']=='NOT MET' and result['falsifier']=='MET'
    assert result['rows']['language_plan']['descriptive_rules']['R_MED1']=='MET'
