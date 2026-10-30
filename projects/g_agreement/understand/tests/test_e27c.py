import copy
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
import torch
from projects.g_agreement.understand import e27c as E
from projects.g_agreement.understand import e27c_runtime as R
from projects.g_agreement.understand.e27c_worker import counts,Collection
from projects.g_agreement.understand.e27c_analyse import summarize,decision
from projects.g_agreement.understand.cpu import ROOT,read,dump,sha


def spec():
    return {f:{'indices':list(range(i*84,(i+1)*84)),'partners':list(range(42,84))+list(range(42)),
               'pairs':[[str(k),'A','B'] for k in range(4 if i<3 else 2)]} for i,f in enumerate(E.FEATURES)}


def test_s16_partner_rule_seed_and_cluster():
    y=np.tile([0,1],42);cl=np.repeat(np.arange(21),4)
    j=E.s16().partners(y,cl,16)
    assert np.array_equal(j,E.s16().partners(y,cl,16))
    assert np.all(y[j]!=y) and np.all(cl[j]!=cl)
    with pytest.raises(ValueError):E.s16().partners(y,['one']*84,16)


def test_two_swaps_are_distinct_and_raw():
    h=torch.tensor([[7.,2.],[2.,9.]])
    ol=torch.tensor([[1.,0.],[0.,3.]])
    nla=torch.tensor([[4.,1.],[1.,5.]])
    a=E.s16().construct(h,ol,nla,np.array([1,0]))
    assert torch.equal(a['swap_res'],ol+(h-ol)[[1,0]])
    assert torch.equal(a['swap_resn'],ol+(nla-ol)[[1,0]])
    assert not torch.equal(a['swap_res'],a['swap_resn'])


def test_counts_cover_partial_batches():
    assert counts(spec())=={'ol_generation':42,'nla_generation':21,'reconstruction':154,'asked':60}


def test_bootstrap_donor_follow_not_recipient():
    y=np.tile([0,1],42);j=np.arange(84)^1
    m=summarize(np.stack([1-y,1-y]),y,j)
    assert m['mean']['follows_j']['auroc']==1
    assert m['mean']['follows_i']['auroc']==0
    assert m['fixed']['follows_j']['ci95']==[1.,1.]
    ties=summarize(np.zeros((2,84)),y,j)
    assert ties['mean']['follows_j']['auroc']==.5


def test_decisions_do_not_pool_arms_or_rows():
    m={f:{arm:{'mean':{'follows_j':{'auroc':.8 if arm=='swap_res' else .6}}} for arm in E.ARMS} for f in E.FEATURES}
    assert decision(m)=={'swap_res':'DESIGN_POWER','swap_resn':'BANK_OR_LABELS'}
    m['list_index']['swap_res']['mean']['follows_j']['auroc']=.79
    assert decision(m)['swap_res']=='MIXED_OR_INTERMEDIATE'


def assignment(tmp_path):
    now=time.time();required={'projects/g_agreement/understand/'+n+'.py' for n in ('e27c','e27c_runtime','e27c_worker','e27c_analyse','cpu')}
    a={'issuer':'integrator','experiment':'E27C','gpu_count':1,'pod_id':'synthetic-test',
       'attempt':2,'authority_commit':'17472735','head_warning_reviewed':True,
       'head_review_sha256':sha(R.REQUEST/'HEAD_REVIEW.json'),
       'brief_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,
       'E23_analysis_posted':True,'E26_analysis_posted':True,'provider_created_epoch':now-1,
       'setup_deadline_epoch':now+100,'deadline_epoch':now+2000,
       'plan_sha256':sha(R.REQUEST/'PLAN.json'),'brief_sha256':sha(R.REQUEST/'BRIEF_UNDERSTAND.authority.md'),
       'source_files':{n:sha(ROOT/n) for n in required}}
    p=tmp_path/'assignment.json';dump(p,a);return p,a


def test_total_budget_includes_setup(tmp_path):
    p,a=assignment(tmp_path);a['deadline_epoch']=a['provider_created_epoch']+7201;dump(p,a)
    with pytest.raises(ValueError,match='total setup'):R.Gate(p,counts(spec()))


def test_amended_cap_accepts_exactly_7200_but_no_old_pod_or_unreviewed_head(tmp_path):
    p,a=assignment(tmp_path);a['deadline_epoch']=a['provider_created_epoch']+7200;dump(p,a)
    assert R.Gate(p,counts(spec())).state()['total_GPU_limit_seconds']==7200
    a['pod_id']='2a3pwvf3e7vxf5';dump(p,a)
    with pytest.raises(ValueError,match='fresh'):R.Gate(p,counts(spec()))
    a['pod_id']='synthetic-test';a['head_warning_reviewed']=False;dump(p,a)
    with pytest.raises(ValueError,match='head review'):R.Gate(p,counts(spec()))


def test_reject_missing_source_and_future_provider(tmp_path):
    p,a=assignment(tmp_path);a['source_files']={};dump(p,a)
    with pytest.raises(ValueError,match='source manifest'):R.Gate(p,counts(spec()))
    p,a=assignment(tmp_path);a['provider_created_epoch']=time.time()+60;dump(p,a)
    with pytest.raises(ValueError,match='absolute'):R.Gate(p,counts(spec()))


def gate_started(tmp_path):
    p,a=assignment(tmp_path);g=R.Gate(p,counts(spec()));g.out=tmp_path
    for k in R.PATHS:g.warm(k,.01)
    g.start();return g


def test_admission_requires_all_paths_and_no_clock_reset(tmp_path):
    g=gate_started(tmp_path)
    with pytest.raises(ValueError):g.start()
    with pytest.raises(ValueError):g.admit(1.)
    with pytest.raises(ValueError):g.record('asked',.1,True)
    for k in R.PATHS:
        for _ in range(3):g.record(k,.01,False)
    g.admit(.1)
    assert g.admitted and (tmp_path/'FORECAST_SEAL.json').is_file()
    with pytest.raises(ValueError):g.admit(.1)


def test_no_fit_seals_forecast_before_production(tmp_path):
    g=gate_started(tmp_path)
    for k in R.PATHS:
        for _ in range(3):g.record(k,100.,False)
    with pytest.raises(R.NoFit):g.admit(.1)
    assert g.completed=={k:0 for k in R.PATHS}
    assert read(tmp_path/'FULL_WARMED_FORECAST.json')['fit'] is False


def test_production_grid_two_sample_averaging(tmp_path):
    # Complete synthetic seven-row pipeline; no checkpoint or model calls.
    c=Collection.__new__(Collection);c.spec=spec();c.a=SimpleNamespace(out=tmp_path)
    c.h={L:torch.zeros(588,5120) for L in (42,44)};c.lib=E.s16()
    completed={k:0 for k in R.PATHS}
    c.g=SimpleNamespace(completed=completed,counts=counts(c.spec))
    def rec(texts,batch):return torch.stack([torch.full((5120,),float(t)) for t in texts])
    decoder=SimpleNamespace(reconstruct=rec)
    c.res=SimpleNamespace(get=lambda owner:decoder)
    c.generation=lambda owner,h:[['2','4'] if owner=='ol' else ['6','8'] for _ in h]
    def score(h,pairs):
        # h=0, R_OL=3, R_NLA=7: raw residual swap=0, reconstructed residual swap=7.
        assert torch.all(h==0) or torch.all(h==7)
        return np.tile(h[:,0].numpy(),(len(pairs),1))
    c.score=score
    def timed(key,fn,retained):completed[key]+=1;return fn()
    c.timed=timed;c.production()
    assert completed==counts(c.spec)
    for f in E.FEATURES:
        assert np.all(np.load(tmp_path/f'scores-{f}-swap_res.npy')==0)
        assert np.all(np.load(tmp_path/f'scores-{f}-swap_resn.npy')==7)


def test_matched_phrasings_remain_verbatim_and_extensions_use_w1():
    p=E.pairs_for('list_index',{})
    assert len(p)==4 and p[0][1]=='This is item number two in the list'
    assert E.pairs_for('python_string',{'nla':[['a','b'],['c','d']]})==[
        ['W1:python_string:0','a','b'],['W1:python_string:1','c','d']]
