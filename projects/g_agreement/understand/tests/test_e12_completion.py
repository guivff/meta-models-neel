import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e12_completion as C
from projects.g_agreement.understand.cpu import read,rows,dump,sha,seal,verify


def test_forecast_excludes_only_first_warmed_unit_and_preserves_bulk_max():
    warm=[7.678468123980565,.3225018900120631,.33032356298645027]
    f=C.forecast(157,.73,warm)
    assert f['selected_rate_seconds_per_unit']==.73
    assert f['F_seconds']==pytest.approx(114.61) and f['science_cap_seconds']==pytest.approx(531.915)
    assert f['fits_with_retrieval'] and f['excluded_first_warmed_unit_seconds']==warm[0]
    assert f['eligible_warmed_timings_seconds']==warm[1:] and not f['forecast_is_upper_bound']
    # The original pull has no exact bulk duration; the sealed whole-clock bound
    # proves fit conservatively without inventing that missing measurement.
    f=C.forecast(157,None,warm,.8767604323759178)
    assert f['F_seconds']==pytest.approx(137.6513878830191)
    assert f['science_cap_seconds']==pytest.approx(566.4770818245286)
    assert f['forecast_is_upper_bound'] and f['observed_bulk_mean_seconds'] is None
    assert f['fits_with_retrieval'] and f['hard_stop_seconds']==1200
    f=C.forecast(157,.1,warm);assert f['selected_rate_seconds_per_unit']==warm[2]
    # A slow remaining warmed unit is still mandatory; no arbitrary outlier drop.
    f=C.forecast(157,.73,[.1,7.678468123980565,.33])
    assert f['F_seconds']==pytest.approx(1205.5194954649487) and f['science_cap_seconds']==1200
    assert not f['fits_even_without_retrieval'] and not f['fits_with_retrieval']
    for invalid in [[],[1.],[1.,2.],[1.,float('nan'),2.],[1.,0.,2.]]:
        with pytest.raises(ValueError):C.forecast(157,.73,invalid)
    with pytest.raises(ValueError,match='upper bound'):C.forecast(157,None,warm)


@pytest.fixture
def captured(tmp_path):
    inp=tmp_path/'inputs';inp.mkdir();prior=tmp_path/'prior';prior.mkdir();items=[{'id':str(i),'feature':'f','text':'source','wrong_activation_index':5-i} for i in range(6)]
    C.jsonl(inp/'items.input.jsonl',items)
    native=[{'feature':'f','arm':'activation_only','indices':[i,i+1]} for i in range(0,6,2)]
    context=[{'feature':'f','arm':arm,'indices':[i,i+1]} for arm in ['text_activation','text_only','text_wrong_activation'] for i in range(0,6,2)]
    dump(inp/'nla_units.json',{'native':native,'context':context});dump(inp/'templates.json',{'f':{'nla':[['A','B'],['A','B']]}});np.save(inp/'acts42.npy',np.ones((6,5120),np.float32))
    nla=tmp_path/'nla';(nla/'av_base').mkdir(parents=True);(nla/'av_base/tokenizer.json').write_text('tok')
    dump(inp/'provenance.json',{'native_carriers':{'nla':{'request':'native','marker_token_id':7,'tokenizer_json_sha256':sha(nla/'av_base/tokenizer.json')}}})
    dump(inp/'INPUT_SEAL.json',{'files':{p.name:sha(p) for p in inp.iterdir()}})
    def value(unit):return [{'id':items[i]['id'],'feature':'f','reader':'nla','layer':42,'arm':unit['arm'],'scores':[1.,2.],'score':1.5} for i in unit['indices']]
    for phase,units in [('native',native),('context',context[:7])]:
        directory=prior/f'nla-{phase}-units';directory.mkdir()
        for i,u in enumerate(units):dump(directory/f'unit-{i:05d}.json',value(u))
        if phase=='native':seal(directory,[p.name for p in directory.iterdir()],'FOLLOWUP_PHASE_COMPLETE_BEFORE_LABEL_JOIN')
    dump(prior/'run.json',{'status':'INCOMPLETE','input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'elapsed_science_seconds':10.,'forecast':{'paths':{'nla_native':{'completed_units':3},'nla_context':{'completed_units':7}}}})
    dump(prior/'PREFIX_PREFLIGHT.json',{'nla':'SUPPORTED_NATIVE_PREFIX'})
    seal(prior,[str(p.relative_to(prior)) for p in prior.rglob('*') if p.is_file()],'EXPLORATORY_E12_INCOMPLETE')
    return inp,prior,nla,items,native,context,value


def test_inventory_exact_disjoint_missing_suffix_and_preserves_completed(captured):
    inp,prior,*_=captured;before=sha(prior/'SCORE_SEAL.json');inv=C.inventory(inp,prior)
    assert inv['retained_native_units']==[0,1,2] and inv['retained_context_units']==list(range(7))
    assert inv['missing_context_units']==[7,8] and sha(prior/'SCORE_SEAL.json')==before
    dump(prior/'nla-context-units/unit-00001.json',[])
    with pytest.raises(ValueError,match='seal mismatch'):C.inventory(inp,prior)


def bare_gate(plan):
    g=object.__new__(C.Gate);g.assignment={'setup_deadline_epoch':time.time()+2400,'deadline_epoch':time.time()+3600,'assets_sha256':'frozen'};g.assignment_sha256='assigned';g.plan=plan;g.started=None;g.first_science_epoch=None;g.completed=[];g.status='SETUP';g.cap=plan['forecast']['science_cap_seconds'];return g


def test_no_fit_before_any_model_load_or_science(tmp_path,monkeypatch):
    f=C.forecast(157,.73,[.1,7.678468123980565,.33]);plan={'forecast':f,'missing_context_units':list(range(1514,1671)),'input_seal_sha256':'frozen','prior_parent_seal_sha256':'prior'};g=bare_gate(plan)
    monkeypatch.setattr(C,'Residents',lambda *a:pytest.fail('NO_FIT must stop before any model load'))
    status=C.execute(SimpleNamespace(inputs=tmp_path/'unused',out=tmp_path/'out'),g)
    assert status=='NO_FIT' and g.first_science_epoch is None and g.completed==[]
    verify(tmp_path/'out');verify(tmp_path/'out','FORECAST_SEAL.json')
    run=read(tmp_path/'out/run.json');assert run['elapsed_science_seconds']==0 and run['checkpoint_load_counts']=={}


def test_fit_worker_scores_only_missing_units_and_same_original_order(captured,tmp_path,monkeypatch):
    inp,prior,nla,items,native,context,value=captured
    inv=C.inventory(inp,prior);plan={'forecast':C.forecast(2,.1,[7.68,.1,.1]),'missing_context_units':[7,8],'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'prior_parent_seal_sha256':inv['prior_parent_seal_sha256']};g=bare_gate(plan)
    reader=SimpleNamespace(tok=object(),prompt_ids=[1,7,3],marker=1)
    resident=SimpleNamespace(assets={'nla':str(nla)},get=lambda:reader,loads={'nla_verbalizer':1})
    calls=[]
    def score(r,name,u,records,h,t,s):
        assert r is reader and name=='nla'
        if records[0]['id'].startswith('WARMUP-'):return []
        calls.append(u['indices']);return value(u)
    monkeypatch.setattr(C,'score_unit',score);monkeypatch.setattr(C,'carrier',lambda *a:([1,7,3],1))
    status=C.execute(SimpleNamespace(inputs=inp,out=tmp_path/'completion'),g,resident)
    assert status=='COMPLETE' and calls==[context[7]['indices'],context[8]['indices']]
    assert sorted(p.name for p in (tmp_path/'completion/nla-context-units').iterdir())==['unit-00007.json','unit-00008.json']
    assert read(tmp_path/'completion/run.json')['Oracle_or_native_rerun'] is False


def test_cpu_join_full_four_arm_grid_no_rescoring_or_label_join(captured,tmp_path,monkeypatch):
    inp,prior,nla,items,native,context,value=captured;inv=C.inventory(inp,prior);before={f:sha(prior/f) for f in read(prior/'SCORE_SEAL.json')['files']}
    completion=tmp_path/'completion';(completion/'nla-context-units').mkdir(parents=True)
    for i in [7,8]:dump(completion/'nla-context-units'/f'unit-{i:05d}.json',value(context[i]))
    dump(completion/'run.json',{'completed_context_units':[7,8],'expected_context_units':[7,8],'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'prior_parent_seal_sha256':inv['prior_parent_seal_sha256']})
    seal(completion,[str(p.relative_to(completion)) for p in completion.rglob('*') if p.is_file()],'E12_CONTEXT_COMPLETION_COMPLETE')
    monkeypatch.setattr(C,'score_unit',lambda *a:pytest.fail('join must never rescore any unit'))
    out=tmp_path/'joined';C.join(inp,prior,completion,out);verify(out);verify(out/'nla')
    result=rows(out/'nla/scores.jsonl');assert len(result)==24 and len({(r['id'],r['arm']) for r in result})==24
    expected=[r for u in [*native,*context] for r in value(u)];assert result==expected
    assert all(sha(prior/f)==digest for f,digest in before.items())
    assert read(out/'SCORE_SEAL.json')['status']=='EXPLORATORY_E12_COMPLETE'
    # A completion containing even one previously scored unit must never join.
    dump(completion/'nla-context-units/unit-00006.json',value(context[6]))
    seal(completion,[str(p.relative_to(completion)) for p in completion.rglob('*') if p.is_file() and p.name!='SCORE_SEAL.json'],'E12_CONTEXT_COMPLETION_COMPLETE')
    with pytest.raises(ValueError,match='exactly unscored'):C.join(inp,prior,completion,tmp_path/'bad-join')


def test_preflight_no_fit_returns_nonzero_without_models(tmp_path,monkeypatch):
    import sys
    path=tmp_path/'PLAN.json';dump(path,{'status':'NO_FIT','forecast':C.forecast(157,.73,[.1,7.678468123980565,.33])})
    monkeypatch.setattr(sys,'argv',['completion','preflight','--plan',str(path)])
    with pytest.raises(SystemExit) as e:C.main()
    assert e.value.code==2


def test_gate_rejects_old_larger_cap_unpushed_source_and_mutable_source(tmp_path,monkeypatch):
    now=time.time();monkeypatch.setattr(C,'ROOT',tmp_path);monkeypatch.setattr(C,'STOP',now+10000)
    names=['projects/g_agreement/understand/'+n+'.py' for n in ['e12_completion','e12_retry','followup_packed','followup_analyse','e12','cpu']]
    for name in [C.BRIEF,*names]:p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('frozen')
    assignment={'issuer':'integrator','experiment':'E12_CONTEXT_COMPLETION','gpu_count':1,'pod_id':'fake','brief_registered':True,'brief_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,'brief_sha256':sha(tmp_path/C.BRIEF),'source_files':{n:sha(tmp_path/n) for n in names},'allocated_gpu_seconds':1200,'previous_gpu_seconds':0,'provider_created_epoch':now-10,'setup_deadline_epoch':now+2390,'deadline_epoch':now+3590,'setup_allowance_seconds':2400,'forecast_method':'observed_bulk_mean_max_remaining_warmed_units_excluding_first'}
    path=tmp_path/'assignment.json';dump(path,assignment);plan={'forecast':C.forecast(157,.73,[.1,7.678468123980565,.33])}
    g=C.Gate(path,plan);assert g.cap==1200
    with pytest.raises(C.NoFit):g.start()
    assert g.first_science_epoch is None
    for change in [{'allocated_gpu_seconds':3600},{'previous_gpu_seconds':1},{'setup_allowance_seconds':2401},{'brief_pushed':False}]:
        dump(path,{**assignment,**change})
        with pytest.raises(ValueError):C.Gate(path,plan)
    dump(path,assignment);(tmp_path/names[0]).write_text('mutated')
    with pytest.raises(ValueError,match='source pin'):C.Gate(path,plan)


def test_preflight_fit_returns_success_without_models(tmp_path,monkeypatch):
    import sys
    path=tmp_path/'PLAN.json';dump(path,{'status':'FIT','forecast':C.forecast(157,None,[7.678468,.322502,.330324],.8767604323759178)})
    monkeypatch.setattr(sys,'argv',['completion','preflight','--plan',str(path)])
    monkeypatch.setattr(C,'Residents',lambda *a:pytest.fail('CPU preflight cannot load a model'))
    C.main()


def test_cap_seals_partial_suffix_and_rejects_join(captured,tmp_path,monkeypatch):
    inp,prior,nla,items,native,context,value=captured;inv=C.inventory(inp,prior)
    plan={'forecast':C.forecast(2,.1,[7.68,.1,.1]),'missing_context_units':[7,8],'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'prior_parent_seal_sha256':inv['prior_parent_seal_sha256']};g=bare_gate(plan)
    reader=SimpleNamespace(tok=object(),prompt_ids=[1,7,3],marker=1)
    resident=SimpleNamespace(assets={'nla':str(nla)},get=lambda:reader,loads={'nla_verbalizer':1})
    calls=[]
    def score(r,name,u,records,h,t,s):
        if records[0]['id'].startswith('WARMUP-'):return []
        calls.append(u['indices']);return value(u)
    def guard():
        if g.completed:raise TimeoutError('completion science/retrieval deadline reached')
    monkeypatch.setattr(C,'score_unit',score);monkeypatch.setattr(C,'carrier',lambda *a:([1,7,3],1));monkeypatch.setattr(g,'guard',guard)
    out=tmp_path/'partial';assert C.execute(SimpleNamespace(inputs=inp,out=out),g,resident)=='INCOMPLETE'
    verify(out);run=read(out/'run.json')
    assert run['completed_context_units']==[7] and run['expected_context_units']==[7,8]
    assert len(read(out/'nla-context-units/unit-00007.json'))==2
    assert calls==[context[7]['indices']] and read(out/'CLOCK.json')['status']=='INCOMPLETE'
    assert run['science_clock_resets']==0 and g.first_science_epoch is not None
    with pytest.raises(ValueError,match='must be COMPLETE'):C.join(inp,prior,out,tmp_path/'bad-join')
    assert sha(prior/'SCORE_SEAL.json')==inv['prior_parent_seal_sha256']
