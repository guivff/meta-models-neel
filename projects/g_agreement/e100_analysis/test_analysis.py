import copy
import numpy as np
import pytest
from rules import *

def fixture():
    return {(r,reader,c):{str(i):1 for i in range(84)} for r in ROWS for reader in ('oracle','nla') for c in CONDITIONS}

def setcell(cells,row,c,value):
    cells[(row,'oracle',c)]={str(i):value for i in range(84)}

def test_joint_paired_and_reproducibility():
    cells=fixture(); values={str(i):(-1 if i%3==0 else 1) for i in range(84)}
    cells[(ROWS[0],'oracle','J_swap')]=values
    cells[(ROWS[0],'oracle','R_swap')]=dict(values)
    b=Bootstrap(cells)
    assert b.stat(ROWS[0],'J_swap','R_swap')['CI95']==[0.,0.]
    assert b.stat(ROWS[0],'J_swap')==Bootstrap(cells).stat(ROWS[0],'J_swap')
    assert not np.array_equal(b.indices[ROWS[0]][1],b.indices[ROWS[1]][1])

def test_masks_not_complete_case_and_undefined_ci():
    cells=fixture(); r=ROWS[0]
    cells[(r,'oracle','J_swap')]={str(i):(1 if i==0 else None) for i in range(84)}
    cells[(r,'oracle','R_swap')]={str(i):(-1 if i==1 else None) for i in range(84)}
    d=Bootstrap(cells).stat(r,'J_swap','R_swap')
    assert d['estimate']==2 and d['CI95'] is None and d['over_5_percent']

def test_active_gating_is_falsifier_not_pc_failure():
    cells=fixture()
    for r in REPORTED:
        setcell(cells,r,'transplant',0.0 if r==REPORTED[0] else 1)
        setcell(cells,r,'R_swap',0);setcell(cells,r,'perp_J_swap',0)
    result=active(Bootstrap(cells)); assert result['R-PC']['status']=='MET' and result['R-C3']['status']=='MET'
    setcell(cells,REPORTED[1],'transplant',0)
    result=active(Bootstrap(cells)); assert result['R-PC']['status']=='NOT MET' and result['R-C3']['status']=='MET'
    setcell(cells,REPORTED[2],'transplant',0)
    result=active(Bootstrap(cells)); assert result['R-PC_falsifier']['status']=='MET' and result['R-C3']['status']=='NOT EVALUABLE'

def test_both_components_and_native_nla_not_confirmatory():
    cells=fixture()
    for r in REPORTED:setcell(cells,r,'R_swap',0)
    result=production(cells)
    assert result['rules']['H-C3b']['interpretation']=='both components carry it'
    assert all(result['rules'][r]['status']=='WITHDRAWN' for r in ('R-C4','R-D1','H-T','H-U'))
    for r in REPORTED:setcell(cells,r,'J_swap',0)
    assert production(cells)['rules']['R-C3']['status']=='NOT MET'

def original_fixture():
    cells=fixture()
    for r in ROWS:
        for a in ('0.5','1','2','4'):
            for c,value in [('d',1 if r in REPORTED else 0),('d_J',1),('d_perp',0),('u_tok',1)]:setcell(cells,r,c+':'+a,value)
        for a in ('1','2'):setcell(cells,r,'d@36:'+a,1)
    return cells

def test_original_rules_and_probe_ratio_condition():
    cells=original_fixture(); shifts={r:1 for r in ROWS}
    result=original_withdrawn(Bootstrap(cells),shifts)
    assert result['R-C4']['status']=='MET'
    assert result['R-D1']['status']=='MET'
    assert result['H-U']['1']['processed_reportable'] is True
    assert result['H-T']['2']['token_not_excluded']['status']=='MET'
    assert result['H-T']['4']['rule_bearing'] is False
    for r in MISSED:shifts[r]=.1
    assert original_withdrawn(Bootstrap(cells),shifts)['R-D1']['status']=='NOT MET'
    assert original_withdrawn(Bootstrap(cells),{})['R-D1']['status']=='NOT EVALUABLE'
    for r in MISSED:shifts[r]=2
    assert original_withdrawn(Bootstrap(cells),shifts)['R-D1']['status']=='MET'
    for r in MISSED:shifts[r]=.5
    assert original_withdrawn(Bootstrap(cells),shifts)['R-D1']['status']=='MET'

def test_alpha4_cannot_rescue_and_decoder_falsifier():
    cells=original_fixture()
    for r in REPORTED:
        for a in ('0.5','1','2'):setcell(cells,r,'d_J:'+a,0)
    assert original_withdrawn(Bootstrap(cells),{r:1 for r in ROWS})['R-C4']['status']=='NOT MET'
    setcell(cells,MISSED[0],'d:1',1)
    assert original_withdrawn(Bootstrap(cells),{r:1 for r in ROWS})['R-D1']['falsifier']['status']=='MET'

def test_incomplete_grid_rejected():
    cells=fixture();del cells[(ROWS[0],'oracle','J_swap')]['0']
    with pytest.raises(ValueError,match='grid'):Bootstrap(cells)

def test_fixed_guard_is_once_only(tmp_path):
    import adapter
    s=dict(guard=str(tmp_path/'once'),analysis=str(tmp_path/'result'),output_sha256='synthetic')
    adapter.core.claim(s,'synthetic')
    s['analysis']=str(tmp_path/'other')
    with pytest.raises(FileExistsError):adapter.core.claim(s,'synthetic')

def test_score_sentinel_and_evidence():
    import adapter
    assert adapter.core.score(dict(id='x',category='UNPARSEABLE',values=[],evidence=''),'A','') is None
    assert adapter.core.score(dict(id='x',category='states_value',values=['A','B'],evidence='either'),'A','either')==0
    with pytest.raises(ValueError):adapter.core.score(dict(id='x',category='states_value',values=['A'],evidence='absent'),'A','different')

def test_complete_synthetic_sealed_acquisition_and_tamper(tmp_path):
    import adapter as a
    targets=[]
    for row in ROWS:
        for i in range(84):
            targets.append(dict(id=row+str(i),row=row,property=row,values={'A':'synthetic A','B':'synthetic B'},target='A',donor_id=row+str((i+1)%84),source_item_id='s'+str(i),donor_source_item_id='s'+str((i+1)%84)))
    td=tmp_path/'targets';td.mkdir();a.write(td/'TARGETS.json',targets)
    a.core.seal(td,'TARGET_SEAL.json',experiment='E100',labels_cpu_only=True,mapping='donor_family_registered_values')
    cfg=dict(targets_seal=str(td/'TARGET_SEAL.json'),targets_sha256=a.sha(td/'TARGET_SEAL.json'),runner_source_sha256='synthetic_source',shards={})
    for shard,group in [('reported',REPORTED),('missed',MISSED)]:
        out=tmp_path/shard;out.mkdir();(out/'jobs').mkdir();grid=[]
        for row in group:
            for reader in ('oracle','nla'):
                for condition in CONDITIONS:
                    for start in range(0,84,8):
                        number=len(grid);indices=list(range(start,min(start+8,84)))
                        grid.append(dict(number=number,indices=indices,row=row,reader=reader,condition=condition))
                        records=[dict(id=row+str(i)+':'+reader+':'+condition,item_id=row+str(i),row=row,reader=reader,condition=condition,repeat=0,basis_block=44,read_block=44 if reader=='oracle' else 42,norm_ratio=1.0,norm_over_1_5=False,gpu_type='H200',text='synthetic A') for i in indices]
                        a.write(out/'jobs'/('%06d.json'%number),records)
        a.write(out/'JOB_GRID.json',grid);a.write(out/'COMPLETED.json',list(range(len(grid))));a.write(out/'NOT_RUN.json',[])
        a.core.seal(out,'OUTPUT_SEAL.json',experiment='E100',stage='ab',status='COMPLETE',shard=shard,labels_cpu_only=True,source_seal_sha256='synthetic_source',input_seal_sha256='synthetic_input',gpu_type='H200',actual_gpu_name='synthetic H200')
        cfg['shards'][shard]=dict(seal=str(out/'OUTPUT_SEAL.json'),sha256=a.sha(out/'OUTPUT_SEAL.json'),input_sha256='synthetic_input')
    rows,digest=a.inputs(cfg)
    assert len(rows)==6720 and len(digest)==64
    bad=tmp_path/'reported'/'jobs'/'000000.json';bad.write_text('[]')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(cfg)

def test_historical_figure_uses_saved_cells(tmp_path):
    import adapter
    pytest.importorskip('matplotlib')
    e79={'states':{r:{'rates':{'J:4':{'estimate':.1,'CI95':[0,.2]},'none':{'estimate':None,'CI95':None}}} for r in MISSED}}
    adapter.figure(production(fixture()),e79,tmp_path/'figure.png')
    assert (tmp_path/'figure.png').stat().st_size>1000

def test_target_mapping_uses_donor_family_and_rejects_wrong_label(monkeypatch):
    import targets
    monkeypatch.setattr(targets,'ROWS',('page_range_digit',))
    # Function's all-672 guard remains production-fixed; test the target lookup
    # with a synthetic full cardinality and eight synthetic row identifiers.
    rownames=tuple('synthetic'+str(i) for i in range(8));monkeypatch.setattr(targets,'ROWS',rownames)
    bank={};join=[];plan={}
    for row in rownames:
        for i in range(84):
            ident=row+':'+str(i);donor=row+':'+str((i+1)%84)
            bank[ident]=dict(id=ident,row_id=row,split='test',label=i%2,value='A' if i%2 else 'B')
            plan[ident]=['positive-family-'+str(i),'negative-family-'+str(i)]
            join.append(dict(id=ident,row=row,bank='E57',source_item_id=ident,donor_id=donor,donor_source_item_id=donor,true_label=i%2,donor_label=(i+1)%2))
    result=targets.mapped(join,{'E57':bank},plan)
    assert result[0]['values']['A']=='positive-family-1' and result[0]['target']=='A'
    join[0]['donor_label']=0
    with pytest.raises(ValueError,match='opposite registered'):targets.mapped(join,{'E57':bank},plan)

def test_production_refuses_before_any_readout_if_uncommitted(monkeypatch):
    import adapter
    monkeypatch.setattr('sys.argv',['adapter.py','export','--spec','synthetic-not-opened.json'])
    def reject(): raise ValueError('uncommitted analysis source')
    monkeypatch.setattr(adapter,'committed',reject)
    monkeypatch.setattr(adapter,'config',lambda _:pytest.fail('spec opened before source gate'))
    monkeypatch.setattr(adapter,'inputs',lambda _:pytest.fail('readouts opened before source gate'))
    with pytest.raises(ValueError,match='uncommitted'):adapter.main()
