"""Synthetic-only regression tests for 09494e79; no outcome files or claims."""
import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import custody
import analysis56 as old56
import analysis57 as old57
import rules56_missing_g3 as new56
import rules57_missing_g3 as new57


def fixture56():
    probe={r:.95 for r in old56.IMPLICIT};j={r:{'G3_AUROC':.55} for r in probe}
    names=set(old56.IMPLICIT+old56.CONTROLS+['fact_recall']+[x for pair in old56.TWINS for x in pair])
    rates={(reader,r,'text'):{'S':.4,'CI95':[.3,.5]} for reader in ('oracle','nla') for r in names}
    return probe,j,rates


def test_56_null_is_ineligible_and_normal_rules_identical(monkeypatch):
    for m in (old56,new56):monkeypatch.setattr(m,'reported',lambda r:r['S']>=.2)
    p,j,r=fixture56();assert new56.rules(p,j,r)==old56.rules(p,j,r)
    before=copy.deepcopy(r);j['anomaly_state']['G3_AUROC']=None;result=new56.rules(p,j,r)
    assert result['R1']['anomaly_state']=={'probe':.95,'J_G3':None,'pass':False,'status':'NOT EVALUABLE','reason':'missing frozen G3 (09494e79)'}
    assert result['readers']['oracle']['R2_reporting_rows']==4
    assert r==before and r['oracle','anomaly_state','text']['S']==.4
    j['anomaly_state']['G3_AUROC']=0
    assert new56.rules(p,j,r)['R1']['anomaly_state']['pass'] is True


def synthetic57(monkeypatch):
    rows=old57.GROUP_B+['multi_token_entity','focus_think','focus_mention','focus_ignore','focus_none','category_switch','capacity_list','linewrap_implicit','linewrap_asked','count_gradient_first_letter']
    private={r:dict(id=r,feature=r,label=1,template_index=0,filler_index=0,variant=0) for r in rows}
    native=[dict(reader=reader,unit_id=r,id=reader+':'+r,repeat=0,text='birds') for reader in ('oracle','nla') for r in rows]
    private['category_stay']=dict(private['category_switch'],id='category_stay',label=0)
    native.extend(dict(reader=reader,unit_id='category_stay',id=reader+':category_stay',repeat=0,text='birds') for reader in ('oracle','nla'))
    def count(xs,meta):
        x=xs[0];return dict(reader=x['reader'],unit_id=x['unit_id'],feature=private[x['unit_id']]['feature'],any_mention_rate=.5,distinct_over_readouts=1,mean_distinct_per_readout=1)
    for m in (old57,new57):
        monkeypatch.setattr(m,'probe_aucs',lambda d:{r:.95 for r in rows})
        monkeypatch.setattr(m,'rate',lambda x:{'S':.4,'CI95':[.3,.5]})
        monkeypatch.setattr(m,'reported',lambda r:True)
        monkeypatch.setattr(m,'signed_value',lambda j,l:1)
        monkeypatch.setattr(m,'named_terms',lambda *a:{'birds'})
        monkeypatch.setattr(m,'paired_ci',lambda *a:[.1,.2])
        monkeypatch.setattr(m,'count_item',count)
    counts=[count([x],{}) for x in native if private[x['unit_id']]['feature'] in ('capacity_list','category_switch')]
    data={'private':private,'native':native,'plan':{'rows':{r:{'probe_applicable':r not in ('capacity_list','category_switch','focus_none')} for r in rows},'native_ids':{r:[r] for r in rows},'count_metadata':{r:{} for r in rows}},'counts':counts}
    data['plan']['native_ids']['category_switch'].append('category_stay');data['plan']['count_metadata']['category_stay']={}
    jj={x['id']:{} for x in native};j={r:{'J_label':'DIFFUSE','G3_AUROC':.5} for r in rows};j['capacity_list']['top50_list_nouns']={'capacity_list':['bird']};data['plan']['count_metadata']['capacity_list']={'list_nouns':['bird']}
    return data,jj,j


def test_57_normal_results_identical(monkeypatch):
    d,jj,j=synthetic57(monkeypatch)
    assert new57.compute(d,jj,j)==old57.compute(d,jj,j)


def test_57_null_ra1_keeps_native_s_and_other_rules(monkeypatch):
    d,jj,j=synthetic57(monkeypatch);normal,_=new57.compute(d,jj,j);j['multi_token_entity']['G3_AUROC']=None
    result,counts=new57.compute(d,jj,j)
    for reader in ('oracle','nla'):
        assert result['readers'][reader]['R_A1']=='NOT EVALUABLE'
        assert result['rates'][reader+'|multi_token_entity']['S']==.4
        assert {k:v for k,v in result['readers'][reader].items() if k!='R_A1'}=={k:v for k,v in normal['readers'][reader].items() if k!='R_A1'}
    assert result['R_B']==normal['R_B'] and counts==sorted(d['counts'],key=lambda x:(x['reader'],x['unit_id']))
    assert 'no single-token readout' in result['R_A1_limitation']
