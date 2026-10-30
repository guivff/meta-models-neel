import copy
import pytest
from . import adapter as a

def fixture(n=60):
    return [dict(row='wrong_bridge',item_id=str(i),cohort='belief_wrong',systems={s:dict(belief=int(s!='outside'),truth=int(s=='outside'),named=True) for s in ('oracle','nla','outside')}) for i in range(n)]

def test_exact_reuse_and_pooled_not_two_row_gate():
    xs=fixture();r=a.analyze(xs);assert r['rules']['oracle']['R_B2_prime']=='MET' and r['rules']['oracle']['R_OL1_prime']=='MET'
    assert r['cohorts']['belief_wrong']['oracle']['R_B2_statistic']==a.row_summary([dict(belief=1,truth=0,any_named=True)]*60)
    assert r['cohorts']['belief_wrong']['oracle']['reader_vs_outside']==a.compare(xs,'oracle','outside','belief',True)

def test_minimum60_not150():
    assert a.analyze(fixture(59))['status']=='NOT RUN'
    assert a.analyze(fixture(60))['status']=='COMPLETE'
    assert a.analyze(fixture(60))['target150_met'] is False

def test_missing_both_and_non_naming():
    xs=fixture()
    for x in xs:x['systems']['oracle']=dict(belief=None,truth=None,named=None)
    r=a.analyze(xs);assert r['rules']['oracle']['R_B2_prime']=='NOT EVALUABLE'
    for x in xs:x['systems']['oracle']=dict(belief=1,truth=1,named=True)
    assert a.analyze(xs)['cohorts']['belief_wrong']['oracle']['R_B2_statistic']['delta']==0
    for x in xs:x['systems']['oracle']=dict(belief=0,truth=0,named=False)
    assert a.analyze(xs)['rules']['oracle']['R_B2_prime']=='NOT EVALUABLE'

def test_item_weights_and_baseline_own_naming_denominator():
    xs=fixture(80)
    for i,x in enumerate(xs):
        x['row']='small' if i<10 else 'large'
        x['systems']['outside']=dict(belief=int(i<10),truth=0,named=i<10)
    z=a.analyze(xs)['cohorts']['belief_wrong']['oracle']['reader_vs_outside']
    assert z['outside']['estimate']==1 and z['difference']['estimate']==0
    assert z['counts']['outside']['not_stating_value']==70

def test_wrong_vs_matched_right_not_pooled_together():
    xs=fixture();right=copy.deepcopy(xs)
    for x in right:x['item_id']='right'+x['item_id'];x['cohort']='belief_right'
    assert a.analyze(xs+right)['belief_wrong']==60
    with pytest.raises(ValueError):a.analyze(xs+xs)

def test_original_letter_mapping_and_missing_pair():
    meta=dict(id='i',bank='E82',cohort='belief_wrong',systems=['oracle'],target_letters_by_system={'oracle':dict(belief='B',truth='A')})
    code=dict(id='j',category='states_value',values=['B'],evidence='value')
    data={'oracle':{t:dict(text='value',code=code,target_letter=l) for t,l in [('belief','B'),('truth','A')]}}
    z=a.evaluate(meta,data)['systems']['oracle'];assert z==dict(belief=1,truth=0,named=True)
    data['oracle']['truth']['code']=None
    assert a.evaluate(meta,data)['systems']['oracle']['named'] is None

def test_tamper_and_once(tmp_path):
    a.core.write(tmp_path/'raw.json',{});a.core.seal(tmp_path,'SEAL.json');h=a.core.sha(tmp_path/'SEAL.json')
    (tmp_path/'raw.json').write_text('tampered')
    with pytest.raises(ValueError):a.core.verify(tmp_path/'SEAL.json',h)
    s=dict(analysis=str(tmp_path/'out'),guard=str(tmp_path/'guard'),output_sha256='synthetic');a.core.claim(s,'synthetic');s['analysis']=str(tmp_path/'again')
    with pytest.raises(FileExistsError):a.core.claim(s,'synthetic')


def test_twohop_frozen_fallback_and_native_prompt():
    inv=dict(experiment='E110',seed=20261029,item_source='TwoHopFact',dataset_revision='59a84cd883f71641a03fb6fa50da92a9603e7845',dataset_repository='soheeyang/TwoHopFact',license='CC BY 4.0',anonymous_download=True,candidate_count=3000,composition_types=52,filter_counts=dict(stable_belief_wrong=59,native_belief_wrong=120),selection_mode='no paraphrase gate',survivor_counts=dict(belief_wrong=120))
    m={'x':dict(split='test',read_token='end_of_native_two_hop_prompt',cohort='belief_wrong',one_hop_correct=False,two_hop_correct=False,stable_one_hop_paraphrases=1)}
    assert a.filter_contract(inv,m)=='no paraphrase gate'
    inv['filter_counts']['stable_belief_wrong']=60
    with pytest.raises(ValueError):a.filter_contract(inv,m)
    inv['selection_mode']='stable belief';inv['survivor_counts']['belief_wrong']=60
    with pytest.raises(ValueError):a.filter_contract(inv,m)
    m['x']['stable_one_hop_paraphrases']=3;assert a.filter_contract(inv,m)=='stable belief'
    m['x']['two_hop_correct']=True
    with pytest.raises(ValueError):a.filter_contract(inv,m)


def test_twohop_under60_both_notrun():
    inv=dict(experiment='E110',seed=20261029,item_source='TwoHopFact',dataset_revision='59a84cd883f71641a03fb6fa50da92a9603e7845',dataset_repository='soheeyang/TwoHopFact',license='CC BY 4.0',anonymous_download=True,candidate_count=3000,composition_types=52,filter_counts=dict(stable_belief_wrong=20,native_belief_wrong=59),selection_mode='NOT RUN',survivor_counts=dict(belief_wrong=59))
    assert a.filter_contract(inv,{})=='NOT RUN'
    inv['anonymous_download']=False
    with pytest.raises(ValueError):a.filter_contract(inv,{})


def shards_fixture(n=4):
    ids=[str(i) for i in range(3000)];ordered=sorted(ids);a.random.Random(20261029).shuffle(ordered)
    r=dict(authority='aa8438c71',restart_index=1,original_candidate_ids=ids,selection_at='2026-10-29T15:00:00Z',excluded_attempt=dict(status='NO_FIT',output_count=192,excluded=True,job_ids=['old'+str(i) for i in range(192)],attempt_id='old'),shards=[])
    for q in range(4):
        r['shards'].append(dict(quarter=q,candidate_ids=ordered[q*750:(q+1)*750],status='COMPLETE' if q<n else 'NOT COMPLETE',included=q<n,completed_at='2026-10-29T14:59:00Z',attempt_id='restart1',job_ids=['q'+str(q)],prompt_bytes_unchanged=True,all_candidate_jobs_complete=True))
    return dict(candidate_count=n*750),r


def test_complete_quarters_and_zero_shards():
    for n in (0,1,3,4):
        inv,r=shards_fixture(n);z=a.shard_contract(inv,{},r)
        assert z['achieved_candidates']==750*n and z['excluded_original_outputs']==192


def test_shard_cutoff_and_no_cherry_pick():
    inv,r=shards_fixture(3);r['selection_at']='2026-10-29T14:59:30Z'
    with pytest.raises(ValueError):a.shard_contract(inv,{},r)
    r['selection_at']='2026-10-29T15:00:00Z';r['shards'][0]['included']=False
    with pytest.raises(ValueError):a.shard_contract(inv,{},r)
    inv,r=shards_fixture(3);r['shards'][0]['completed_at']='2026-10-29T15:01:00Z';r['selection_at']='2026-10-29T15:02:00Z'
    with pytest.raises(ValueError):a.shard_contract(inv,{},r)


def test_partition_old_attempt_and_survivor_custody():
    for mutation in ('partition','old_job','old_attempt','survivor','achieved'):
        inv,r=shards_fixture(3);meta={}
        if mutation=='partition':r['shards'][0]['candidate_ids'].reverse()
        if mutation=='old_job':r['shards'][0]['job_ids']=['old0']
        if mutation=='old_attempt':r['shards'][0]['attempt_id']='old'
        if mutation=='survivor':meta={'x':dict(candidate_id=r['shards'][3]['candidate_ids'][0])}
        if mutation=='achieved':inv['candidate_count']=3000
        with pytest.raises(ValueError):a.shard_contract(inv,meta,r)


def test_deviation2_reference_same_scale_and_rules_unchanged():
    xs=fixture();reference=fixture(100)
    before=a.analyze(xs);after=a.analyze(xs,reference)
    assert after['rules']==before['rules'] and after['cohorts']==before['cohorts']
    z=after['descriptive_banks']['E82_wrong_bridge']
    assert z['items']==100 and 'descriptive only' in z['role']
    assert z['statistics']['oracle']['R_B2_statistic']==a.row_summary([dict(belief=1,truth=0,any_named=True)]*100)
    assert z['statistics']['oracle']['reader_vs_outside']==a.compare(reference,'oracle','outside','belief',True)
    assert 'rules' not in z


def test_reference_cannot_rescue_new_bank_floor():
    z=a.analyze(fixture(59),fixture(100))
    assert z['status']=='NOT RUN' and z['belief_wrong']==59
    assert 'rules' not in z and 'descriptive_banks' not in z


@pytest.mark.parametrize('mutation',['count','duplicate','row','cohort','system'])
def test_reference_exact100_original_cohort(mutation):
    xs=fixture(100)
    if mutation=='count':xs.pop()
    if mutation=='duplicate':xs[-1]['item_id']=xs[0]['item_id']
    if mutation=='row':xs[0]['row']='other'
    if mutation=='cohort':xs[0]['cohort']='belief_right'
    if mutation=='system':xs[0]['systems'].pop('outside')
    with pytest.raises(ValueError):a.reference_summary(xs)


def test_reference_missing_and_both_keep_original_denominators():
    xs=fixture(100)
    for x in xs:x['systems']['oracle']=dict(belief=None,truth=None,named=None)
    z=a.reference_summary(xs)['statistics']['oracle']
    assert not z['R_B2_statistic']['evaluable']
    for x in xs:x['systems']['oracle']=dict(belief=1,truth=1,named=True)
    assert a.reference_summary(xs)['statistics']['oracle']['R_B2_statistic']['delta']==0


def test_deviation2_generated_filter_preserves_floor_and_fallback():
    inv=dict(experiment='E110',deviation=2,seed=20261029,item_source='E82_long_tail_bridge',generation_method='E82_wrong_bridge',long_tail_source_bound=True,candidate_count=3000,composition_types=52,filter_counts=dict(stable_belief_wrong=59,native_belief_wrong=60),selection_mode='no paraphrase gate',survivor_counts=dict(belief_wrong=60))
    assert a.filter_contract(inv,{})=='no paraphrase gate'
    inv['filter_counts']['native_belief_wrong']=59;inv['survivor_counts']['belief_wrong']=59;inv['selection_mode']='NOT RUN'
    assert a.filter_contract(inv,{})=='NOT RUN'
    inv['long_tail_source_bound']=False
    with pytest.raises(ValueError):a.filter_contract(inv,{})
