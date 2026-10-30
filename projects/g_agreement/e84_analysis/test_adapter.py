import copy
import pytest
from .adapter import analyze,gate,inventory,STATES,SYSTEMS,GUARD,NOT_BUILT_REASON
from projects.g_agreement.understand.wmech2 import core

def gates():return {s:dict(probe_fit_split='dev',test_used_for_fit=False,probe_metric='test_AUROC',probe_blocks=dict(oracle=44,nla=42),dev_n=100,test_n=200,bow_window_tokens=512,probe_test=dict(oracle=.9,nla=.9),bow_test=.65) for s in STATES}
def rows():return [dict(state=s,item_id=str(i),system=r,score=1 if i<150 else -1) for s in STATES for i in range(200) for r in SYSTEMS]
def test_signed_rate_exact_and_reproducible():
    a=analyze(rows(),gates());assert a==analyze(rows(),gates())
    for x in a['states'].values():
        for r in x['systems'].values():assert r['S']==.5 and r['N_planned']==200 and r['bootstrap_seed']==20261027 and r['bootstrap_draws']==2000

def test_gate_boundaries_and_drop():
    g=gates();assert gate(g[STATES[0]])=='PASS'
    g[STATES[0]]['probe_test']['oracle']=.8999
    x=analyze([x for x in rows() if not(x['state']==STATES[0] and x['system']=='oracle')],g)
    assert x['states'][STATES[0]]['reader_dispositions']['oracle']=='DROPPED_GATE'
    assert 'nla' in x['states'][STATES[0]]['systems']
    with pytest.raises(ValueError):analyze(rows(),g)
    g=gates();g[STATES[0]]['bow_test']=.65001
    z=analyze(rows(),g)['states'][STATES[0]]
    assert z['disposition']=='TEXT_READABLE' and len(z['systems'])==3

def test_missing_not_zero_and_allmissing():
    xs=rows()
    for x in xs:
        if x['system']=='oracle':x['score']=None
    r=analyze(xs,gates())['states'][STATES[0]]['systems']['oracle']
    assert r['S'] is None and r['missing']==200 and r['S_missing_bounds']==[-1,1]

def test_grid_pairing_duplicate_and_drop():
    xs=rows()
    with pytest.raises(ValueError):analyze(xs[:-1],gates())
    with pytest.raises(ValueError):analyze(xs+[xs[0]],gates())
    xs[0]['item_id']='other'
    with pytest.raises(ValueError):analyze(xs,gates())

def test_no_test_fit_or_nan():
    g=gates()[STATES[0]];g['test_used_for_fit']=True
    with pytest.raises(ValueError):gate(g)
    g['test_used_for_fit']=False;g['probe_test']['oracle']=float('nan')
    with pytest.raises(ValueError):gate(g)

def fixture():
    inv=dict(experiment='E84',authority='revived deviation1',seed=20261029,dataset=dict(family='SWE-Zero OpenHands',repository='synthetic/repo',revision='synthetic',license='CC BY 4.0',anonymous_download=True,terms_acceptance_required=False,original_release_check_sha256='a'),parser_source_sha256='b',probe_recipe_sha256='c',read_point='start_of_next_assistant_turn',window_policy='complete_rendered_prefix',absence_window_tokens=512,cropped=False,reader_blocks=dict(oracle=44,nla=42),ambiguity_counts={s:2 for s in STATES})
    items={s+str(i):dict(state=s,item_id=str(i),split='test',state_absent_from_last512=True,unambiguous_cpu_parse=True,source_transcript_sha256='a',window_sha256='b',parser_record_sha256='c',targets={r:'A' for r in SYSTEMS}) for s in STATES for i in range(200)}
    inv.update(state_dispositions={'file_being_edited':'BUILT','last_test_passed':'NOT BUILT','failed_attempts':'NOT BUILT'},confirmation_shards=shards(),additional_shard_confirmed=True,e110_finished_before_e84_freeze=True)
    items={k:x for k,x in items.items() if x['state']=='file_being_edited'}
    return inv,items

def test_inventory_access_and_hidden_state():
    inv,items=fixture();inventory(inv,items)
    inv['dataset']['terms_acceptance_required']=True
    with pytest.raises(ValueError):inventory(inv,items)
    inv['dataset']['terms_acceptance_required']=False
    next(iter(items.values()))['state_absent_from_last512']=False
    with pytest.raises(ValueError):inventory(inv,items)

def test_inventory_exact_state_denominators():
    inv,items=fixture();items.pop(next(iter(items)))
    with pytest.raises(ValueError):inventory(inv,items)

def test_score_both_neither_and_evidence():
    code=dict(id='x',category='states_value',values=['A','B'],evidence='both')
    assert core.score(code,'A','both')==0
    code.update(category='silent',values=[],evidence='');assert core.score(code,'A','anything')==0
    code.update(category='states_value',values=['B'],evidence='B');assert core.score(code,'A','B')==-1
    with pytest.raises(ValueError):core.score(code,'A','unrelated')

def test_fixed_exclusive_guard(tmp_path):
    assert str(GUARD).endswith('/e84/deviation1/ANALYSIS_ONCE.json')
    spec=dict(analysis=str(tmp_path/'out'),guard=str(tmp_path/'guard'),output_sha256='synthetic')
    core.claim(spec,'synthetic')
    spec['analysis']=str(tmp_path/'other')
    with pytest.raises(FileExistsError):core.claim(spec,'synthetic')


def shards():return [dict(shard=str(i),seed=20261029,sha256='synthetic',trajectories=100,state_candidates=0) for i in range(2)]

def test_source_limited_rows_retained():
    g=gates()
    for state in ('last_test_passed','failed_attempts'):g[state]=dict(disposition='NOT BUILT',reason=NOT_BUILT_REASON,shard_counts=shards())
    a=analyze([x for x in rows() if x['state']=='file_being_edited'],g)
    assert a['states']['last_test_passed']['disposition']=='NOT BUILT'
    assert len(a['states']['failed_attempts']['gates']['shard_counts'])==2
    assert a['states']['file_being_edited']['systems']['oracle']['N_planned']==200
    g['failed_attempts']['reason']='unavailable'
    with pytest.raises(ValueError):analyze([],g)

def test_confirmation_and_e110_order_required():
    inv,items=fixture();inv['e110_finished_before_e84_freeze']=False
    with pytest.raises(ValueError):inventory(inv,items)
    inv['e110_finished_before_e84_freeze']=True;inv['confirmation_shards']=shards()[:1]
    with pytest.raises(ValueError):inventory(inv,items)


def test_full_prefix_and_single_frozen_baseline():
    assert SYSTEMS==('oracle','nla','text_generic')
    inv,items=fixture();inventory(inv,items)
    inv['cropped']=True
    with pytest.raises(ValueError):inventory(inv,items)
    inv['cropped']=False;inv['window_policy']='last512'
    with pytest.raises(ValueError):inventory(inv,items)


def test_dev_score_not_gate_and_both_readers_fail():
    g=gates();g[STATES[0]]['probe_dev']=0
    assert gate(g[STATES[0]])=='PASS'
    g[STATES[0]]['probe_test']=dict(oracle=.1,nla=.2)
    xs=[x for x in rows() if x['state']!=STATES[0] or x['system']=='text_generic']
    assert set(analyze(xs,g)['states'][STATES[0]]['systems'])=={'text_generic'}
