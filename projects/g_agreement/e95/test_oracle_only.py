import pytest
from projects.g_agreement.e95.oracle_only import stage,summarize


def fixture():
    cells=[dict(id=f'{arm}{i}',arm=arm,layer=44,positions=[0,1]) for arm in ('real','placebo') for i in range(3)]
    join=[dict(id=x['id'],row='row',reader='oracle',arm=x['arm'],layer=44,public_item_id=x['id'],target='A') for x in cells]
    codes=[dict(id=x['id'],category='states_value',values=['A'] if x['arm']=='real' else ['B'],first_position=0) for x in cells]
    plan=dict(rows=[dict(key='row',bank='synthetic',row='row',stage='s',status='COMPLETE',statement_score_registered=True,layers=[44],items={a:[x['id'] for x in cells if x['arm']==a] for a in ('real','placebo')},J_fraction=.5,single_site_verdict='REPORTED')],verdict_rule=dict(operator='>=',threshold=.3,authority='synthetic only'),E62_median=.4)
    return cells,join,codes,plan


def test_oracle_only_full_stage_and_map():
    cells,join,codes,plan=fixture();stage(dict(reader='oracle',status='COMPLETE',cells=cells),cells)
    r=summarize(plan,codes,join)
    assert r['NLA']['status']=='NOT RUN (operational)'
    assert r['rows'][0]['statistics']['D']==2
    assert r['H_M1']['status']=='MET'

@pytest.mark.parametrize('fault',['partial','no_placebo','nla','positions'])
def test_reject_incomplete_or_wrong_stage(fault):
    cells,_,_,_=fixture();m=dict(reader='oracle',status='COMPLETE',cells=[dict(x) for x in cells])
    if fault=='partial':m['cells'].pop()
    if fault=='no_placebo':m['cells']=m['cells'][:3]
    if fault=='nla':m['reader']='nla'
    if fault=='positions':m['cells'][0]['positions']=[0]
    with pytest.raises(ValueError):stage(m,cells)


def test_missing_placebo_group_cannot_pass_row():
    _,join,codes,plan=fixture()
    with pytest.raises(ValueError):summarize(plan,codes[:-1],join[:-1])


def test_nla_real_not_consumed():
    _,join,codes,plan=fixture();join[0]['reader']='nla'
    with pytest.raises(ValueError):summarize(plan,codes,join)


def test_unscorable_retained_and_notrun_retained():
    _,join,codes,plan=fixture();plan['rows'][0]['statement_score_registered']=False
    plan['rows'].append(dict(key='absent',bank='s',row='absent',status='NOT RUN',reason='incomplete stage'))
    r=summarize(plan,codes,join)
    assert len(r['rows'])==2 and r['H_M1']['eligible_rows']==0


def test_complete_nla_uses_identical_rules_and_reports_coverage():
    import copy
    cells,join,codes,plan=fixture();baseline=summarize(plan,codes,join)
    nc=copy.deepcopy(cells);nj=copy.deepcopy(join);njd=copy.deepcopy(codes)
    for x in nc+nj+njd:x['id']='nla-'+x['id']
    for x in nj:x['reader']='nla'
    nr=copy.deepcopy(plan['rows'][0]);nr.update(reader='nla',stage='nla-complete')
    plan['rows'].append(nr)
    stage(dict(reader='nla',status='COMPLETE',cells=nc),nc,'nla')
    z=summarize(plan,codes+njd,join+nj)
    assert z['rows']==baseline['rows'] and z['H_M1']==baseline['H_M1']
    assert z['NLA']['rows']==baseline['rows'] and z['NLA']['H_M1']==baseline['H_M1']
    assert z['coverage']['nla']==[dict(shard='nla-complete',row='row',status='COMPLETE',reason=None)]


def test_nla_missing_stage_explicit_and_no_partial_placebo():
    import copy
    cells,join,codes,plan=fixture()
    nr=copy.deepcopy(plan['rows'][0]);nr.update(reader='nla',status='NOT RUN',stage='nla-incomplete',reason='whole real/placebo stage incomplete')
    plan['rows'].append(nr)
    z=summarize(plan,codes,join)
    assert z['NLA']['rows'][0]['status']=='NOT RUN (operational)'
    assert z['coverage']['nla'][0]['shard']=='nla-incomplete'
    with pytest.raises(ValueError):stage(dict(reader='nla',status='COMPLETE',cells=cells[:3]),cells,'nla')
    with pytest.raises(ValueError):stage(dict(reader='nla',status='PARTIAL',cells=cells),cells,'nla')
