import copy
import pytest
from . import e101 as e

def fixture():
    targets={};rows=[];doses={}
    for row in e.ROWS:
        for b in (42,44):doses[f'{row}:{b}']={'alpha':1}
        for i in range(84):
            item=row+str(i);targets[item]=dict(row=row,J_fraction={'42':.3,'44':.4})
            for reader in e.READERS:
                for c in ('steered','random','unsteered'):
                    rows.append(dict(id=item+reader+c,item_id=item,row=row,reader=reader,condition=c,score=(1 if row in e.CONTENT and c=='steered' else 0),flipped=c=='steered',norm_ratio=1.2,norm_over_1_5=False))
            if row in e.CONTENT:rows.append(dict(id=item+'text',item_id=item,row=row,reader='text',condition='text',score=-1,stated_value=1))
    return rows,doses,targets

def test_full_rules_and_baselines():
    r,d,t=fixture();x=e.analyze(r,d,t,'steered_flipped')
    for reader in e.READERS:
        assert all(x['rules'][reader][k]['status']=='MET' for k in ('R-F1','R-F2','R-F3'))
    z=x['rows']['format_plan'];assert z['text_stated_rate']['estimate']==1
    assert z['oracle']['B_random']['estimate']==0
    assert z['oracle']['S_all_steered']['estimate']==1

def test_paired_steered_cohort_even_when_random_does_not_flip():
    r,d,t=fixture()
    for x in r:
        if x['row']=='format_plan' and x['condition'] in ('steered','random'):
            i=int(x['item_id'].replace('format_plan',''))
            x['flipped']=i<42 if x['condition']=='steered' else i>=42
            x['score']=1 if i<42 else -1
    z=e.analyze(r,d,t,'steered_flipped')['rows']['format_plan']['oracle']
    assert z['S_target']['estimate']==z['S_random']['estimate']==1
    assert z['difference']['CI95']==[0,0] and z['B_random']['estimate']==.5
    assert z['S_all_steered']['estimate']==z['S_all_random']['estimate']==0
    with pytest.raises(ValueError):e.analyze(r,d,t,'condition_flipped')

def test_no_dose_and_insufficient_flips_do_not_count_as_null():
    r,d,t=fixture()
    for row in e.BOOK:d[f'{row}:44']['alpha']=None
    x=e.analyze(r,d,t,'steered_flipped')
    assert x['rules']['oracle']['R-F2']['status']=='NOT EVALUABLE'
    assert x['rules']['nla']['R-F2']['status']=='MET'
    for row in e.BOOK:d[f'{row}:44']['alpha']=1
    for z in r:
        if z['row'] in e.BOOK and z['condition']=='steered':z['flipped']=False
    assert e.analyze(r,d,t,'steered_flipped')['rules']['oracle']['R-F2']['status']=='NOT EVALUABLE'

def test_falsifiers_and_missing_scores():
    r,d,t=fixture()
    for x in r:
        if x['condition']=='steered':x['score']=0 if x['row'] in e.CONTENT else 1
    a=e.analyze(r,d,t,'steered_flipped')
    assert a['rules']['oracle']['R-F1_falsifier']['status']=='MET'
    assert a['rules']['oracle']['R-F2_falsifier']['status']=='MET'
    for x in r:
        if x['condition']=='steered':x['score']=None
    assert e.analyze(r,d,t,'steered_flipped')['rules']['oracle']['R-F1']['status']=='NOT EVALUABLE'

def test_stat_paired_and_repeatable():
    x={str(i):i%2 for i in range(84)}
    assert e.stat(x,x)['CI95']==[0.,0.]
    assert e.stat(x)==e.stat(x)

def test_source_gate_before_test_read(monkeypatch):
    monkeypatch.setattr(e,'committed',lambda: (_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(e,'read',lambda _:pytest.fail('opened input before source gate'))
    monkeypatch.setattr('sys.argv',['e101','analyze','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):e.main()

def test_plot(tmp_path):
    pytest.importorskip('matplotlib')
    r,d,t=fixture();e.figure(e.analyze(r,d,t,'steered_flipped'),tmp_path/'figure.png')
    assert (tmp_path/'figure.png').stat().st_size>1000

def test_complete_synthetic_runner_custody(tmp_path,monkeypatch):
    targets=[];baseline=[];items=[];selected={f'{r}:{b}':{'alpha':1} for r in e.ROWS for b in (42,44)}
    def bundle(name,files,**meta):
        folder=tmp_path/name;folder.mkdir()
        for n,value in files.items():
            (folder/n).parent.mkdir(parents=True,exist_ok=True);e.write(folder/n,value)
        e.core.seal(folder,'SEAL.json',**meta)
        return dict(seal=str(folder/'SEAL.json'),sha256=e.sha(folder/'SEAL.json'))
    source=bundle('historic',{'texts.json':['synthetic exact baseline']},experiment='historical')
    for row in e.ROWS:
        for i in range(84):
            item=row+str(i)
            targets.append(dict(id=item,row=row,split='test',property=row,values={'A':'a','B':'b'},target='B',contrast_target_sign=-1,J_fraction={'42':.3,'44':.4}))
            for reader,block in e.READERS.items():
                baseline.append(dict(item_id=item,reader=reader,condition='unsteered',text='synthetic exact baseline',source_ref=dict(seal_index=0,member='texts.json',keys=[0])))
                for c in ('steered','random'):items.append(dict(id=item+reader+c,base_id=item,row=row,block=block,condition=c,alpha=1,candidate_ids=[[[1],[2]]],norm_ratio=1))
            if row in e.CONTENT:baseline.append(dict(item_id=item,reader='text',condition='text',text='synthetic exact baseline',source_ref=dict(seal_index=0,member='texts.json',keys=[0])))
    ts=bundle('targets',{'TARGETS.json':targets},experiment='E101',labels_cpu_only=True)
    bs=bundle('baseline',{'BASELINES.json':baseline},experiment='E101',existing_outputs_only=True,source_seals=[source])
    ins=bundle('inputs',{'items.json':items,'MANIFEST.json':dict(stage='test',dose_sha256='dosehash',dose_commit='commit',scoring_mode='continuation')},labels_on_pod=False)
    grid=[];files={}
    for phase in ('logits','oracle','nla'):
        ix=[i for i,x in enumerate(items) if phase=='logits' or x['block']==e.READERS[phase]]
        grid.append(dict(kind=phase,indices=ix))
        files[f'jobs/{len(grid)-1:06d}.json']=[dict(id=items[i]['id'],**({'pair_logprobs':[[-2.,-1.]]} if phase=='logits' else {'text':'synthetic readout'})) for i in ix]
    files.update({'JOB_GRID.json':grid,'COMPLETED.json':[0,1,2]})
    outs=bundle('outputs',files,experiment='E101',stage='test',status='COMPLETE',input_sha256=ins['sha256'],dose_sha256='dosehash',source_sha256='runner')
    monkeypatch.setattr(e,'committed_dose',lambda *a:dict(scoring_mode='continuation',dev_count=84,dose_policy='independent_blocks',selected_doses=selected))
    s=dict(dose_path='unused',dose_commit='commit',dose_sha256='dosehash',runner_source_sha256='runner',targets=ts,baselines=bs,shards=[dict(input=ins,output=outs)])
    rows,_,_=e.acquire(s)
    assert len(rows)==3864 and sum(x.get('flipped',False) for x in rows)==2352
    (tmp_path/'outputs/jobs/000000.json').write_text('[]')
    with pytest.raises(ValueError,match='member mismatch'):e.acquire(s)

def test_212_descriptive_two_cells_without_baseline_dependency():
    rows,doses,targets=fixture()
    for key in doses:doses[key]['alpha']=4 if key in ('fact_recall:44','language_plan:44') else None
    rows=[x for x in rows if x['row'] in ('fact_recall','language_plan') and x['reader']=='oracle' and x['condition'] in ('steered','random')]
    result=e.analyze(rows,doses,targets,'steered_flipped',descriptive=True)
    assert result['scope']=='descriptive_two_cell'
    assert all(v['status']=='NOT EVALUABLE' for rr in result['rules'].values() for v in rr.values())
    assert result['rows']['fact_recall']['oracle']['S_all_steered']['estimate']==1
    assert result['rows']['language_plan']['oracle']['B_random']['estimate']==0
    assert result['baselines_status'].startswith('NOT PROVIDED')
    assert '12 of 14' in result['null_wording']

def test_212_operational_language_plan_is_not_a_zero():
    rows,doses,targets=fixture()
    for key in doses:doses[key]['alpha']=4 if key in ('fact_recall:44','language_plan:44') else None
    rows=[x for x in rows if x['row']=='fact_recall' and x['reader']=='oracle' and x['condition'] in ('steered','random')]
    result=e.analyze(rows,doses,targets,'steered_flipped',descriptive=True,operational_not_run=['language_plan:44'])
    assert result['rows']['language_plan']['oracle']['status']=='NOT RUN (operational)'
    assert 'B' not in result['rows']['language_plan']['oracle']
