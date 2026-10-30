from pathlib import Path
import pytest
from projects.g_agreement.blindspot import w10_cpu as W
from projects.g_agreement.blindspot import protocol as P


def row(name,oracle=True,nla=True,gap=.3,delta=.2,lo=.01,kind='mode'):
    return {'feature':name,'class':kind,'probes':{'44':{'auroc':1}},
        'readers':{'olens':{'evaluable':oracle,'true':{'auroc':1-gap}},'nla':{'evaluable':nla}},
        'nla_minus_oracle':{'difference':delta,'ci95':[lo,.5]}}


def test_registered_denominators_and_surprisal_exclusion():
    data=[row('a'),row('b',nla=False),row('c',oracle=False),row('surprise',kind='surprisal')]
    result=W.adjudicate(data)
    assert result['H1']['n']==2 and result['H2']['n']==1
    assert result['H1']['k']==2 and result['H2']['k']==1
    assert W.adjudicate([])['H1']['status']=='NOT EVALUABLE'


def test_H1_inclusive_threshold_and_H2_strict_positive_lower_ci():
    result=W.adjudicate([row('a',gap=.25,delta=.10,lo=0)])
    assert result['H1']['status']=='CONFIRMED'
    assert result['H2']['status']=='NOT MET'


def test_judge_budget_rejects_full_pass_before_any_post(tmp_path,monkeypatch):
    import requests
    P.jsonl(tmp_path/'judge_packet.jsonl',[{'id':str(i),'prompt':'frozen'} for i in range(200)])
    P.dump(tmp_path/'MODE_PACKET_SEAL.json',{'files':{'judge_packet.jsonl':P.sha(tmp_path/'judge_packet.jsonl')}})
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only-not-a-real-key')
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'data':[{'id':'openai/gpt-5-mini','pricing':{'prompt':'1','completion':'1'}}]}
    monkeypatch.setattr(requests,'get',lambda *a,**k:Response())
    def must_not_send(*a,**k):raise AssertionError('budget guard allowed an API request')
    monkeypatch.setattr(requests,'post',must_not_send)
    with pytest.raises(ValueError,match='price bound exceeds cap'):
        W.judge(tmp_path,tmp_path/'judged')
    assert not (tmp_path/'judged').exists()
