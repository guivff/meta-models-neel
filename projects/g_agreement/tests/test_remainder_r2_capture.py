import copy
import json
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2_capture as R


def test_model_keys_cannot_fall_back_to_provisional():
    it={'dataset':'rb_internal_self_choice','item_id':'i','label':1,'primary':{'label_source':'model','candidates':['a','b']}}
    with pytest.raises(ValueError,match='Missing model-derived'):R.resolve_label(it,{})
    resolved,info=R.resolve_label(it,{(it['dataset'],'i'):{'label':None,'source_key':'ml|i'}})
    assert resolved['label'] is None and info['kind']=='model' and it['label']==1
    resolved,_=R.resolve_label(it,{(it['dataset'],'i'):{'label':0,'source_key':'ml|i'}})
    assert resolved['label']==0 and resolved['primary']['answer']=='b'


def test_conflicting_model_key_files_fail(tmp_path):
    for i,y in enumerate((0,1)):
        (tmp_path/f'model_labels.{i}.jsonl').write_text(json.dumps({'dataset':'d','item_id':'i','key':'k','model_label':y})+'\n')
    with pytest.raises(ValueError,match='Conflicting'):R.label_rows(tmp_path)


def test_derangement_has_no_self_and_is_reproducible():
    ids=list('abcdef'); a=R.derangement(ids,'f|pool')
    assert set(a)==set(a.values())==set(ids) and all(k!=v for k,v in a.items())
    assert a==R.derangement(ids,'f|pool')
    with pytest.raises(ValueError):R.derangement(['one'],'f')


def test_guard_cannot_be_renewed_or_cross_pod():
    rec={'pod':'p','experiment':'r2','started_epoch':100,'deadline_epoch':1300}
    R.validate_guard(rec,'p',1300,200)
    for record,pod,deadline,now in [(rec,'q',1300,200),(rec,'p',1301,200),(rec,'p',1300,1001),({**rec,'started_epoch':99},'p',1300,200)]:
        with pytest.raises(ValueError):R.validate_guard(record,pod,deadline,now)


def test_arrays_require_all_blocks_and_finite_primary(monkeypatch):
    monkeypatch.setattr(R.C,'D_MODEL',4)
    arrays={k:np.ones((2,4),np.float16) for k in R.TAPS}
    R.validate_arrays(arrays,2)
    with pytest.raises(ValueError,match='missing'):R.validate_arrays({20:arrays[20]},2)
    arrays[20][1,0]=np.nan
    with pytest.raises(ValueError,match='Nonfinite'):R.validate_arrays(arrays,2)


def manifest():
    return {'facts':[{'bank':bank,'dataset':bank,'items':[{'item_id':f'{bank}-{split}-{i}','split':split} for split in ('pool','test') for i in range(3)]} for bank in R.A.BANKS]}


def test_smoke_covers_both_readers_banks_splits_controls():
    m=manifest();k=R.expected_keys(m,True)
    assert len(k)==48 and len(R.expected_keys(m))==72
    assert {x[0] for x in k}=={'olens','nla'}
    assert {x[2] for x in k}=={'pool','test'}
    assert {x[3] for x in k}=={'natural','shuf'}


def test_mock_cannot_unlock_live_and_budget_fails():
    m=manifest();meta={'pod':'p','git_sha':'g','code_sha':'c'};g={'guard_dir':'x','guard_sha256':'z','deadline_epoch':1300}
    cert={'manifest_sha256':R.digest(m),**meta,**g,'batch':32,'kind':'live','coverage':{'arm_cells':72},'projected_full_seconds':300,'projected_tap_bytes':100,'measured_pull_bytes_per_second':100}
    R.throughput_gate(cert,m,meta,g,32,now=100)
    for change in ({'kind':'mock'},{'manifest_sha256':'bad'},{'code_sha':'changed'},{'guard_sha256':'new'},{'projected_full_seconds':1000}):
        with pytest.raises(ValueError):R.throughput_gate({**cert,**change},m,meta,g,32,now=100)


def test_one_sided_native_uses_positive_score():
    score={'lo':-20,'lp_A':-2}
    assert R.native_value(score,{'primary':{'sided':'one'}})==-2
    assert R.native_value(score,{'primary':{'sided':'two'}})==-20


def test_hook_score_and_assembly_use_exact_same_call(monkeypatch):
    from projects.g_agreement.r_bench import collect as K
    monkeypatch.setattr(R.C,'D_MODEL',2)
    events=[]
    class Reader:name='olens'
    class Hook:
        def __init__(self,reader,taps,layer):assert taps==R.TAPS and layer==44
        def __enter__(self):events.append('enter');return self
        def __exit__(self,*args):events.append('exit')
        def assemble(self,pairs,batch,groups):
            assert pairs==[('a','b'),('c','d')] and batch==32 and groups==[('family',[1,0])]
            events.append('assemble')
            return {k:np.ones((2,2),np.float16) for k in R.TAPS},[[1],[2]],{'T':1}
    def score(reader,H,items,layer,batch,return_groups):
        assert events==['enter'] and return_groups and layer==44 and batch==32
        return [{'lo':1},{'lo':2}],[('family',[1,0])]
    monkeypatch.setattr(R,'ReadPositionHook',Hook);monkeypatch.setattr(K,'score_items',score)
    monkeypatch.setattr(K,'item_pair',lambda reader,p:tuple(p['candidates']))
    items=[{'primary':{'candidates':['a','b']}},{'primary':{'candidates':['c','d']}}]
    rows,arrays,meta=R.score_chunk(Reader(),np.ones((2,2)),items,44,32)
    assert events==['enter','exit','assemble'] and len(rows)==2 and meta['T']==1


def test_mock_roundtrip_all_cells_and_misjoined_rows_fail(tmp_path,monkeypatch):
    monkeypatch.setattr(R,'ROOT',tmp_path);monkeypatch.setattr(R.C,'D_MODEL',4)
    facts=[];banks={}
    for b in R.A.BANKS:
        source=tmp_path/b;source.mkdir();x=np.arange(16,dtype=np.float16).reshape(4,4)
        states={}
        for layer in R.READERS.values():
            path=source/f'L{layer}.npy';np.save(path,x);states[str(layer)]={'path':str(path.relative_to(tmp_path)),'sha256':R.sha(path)}
        items=[]
        for j,(split,y) in enumerate([('pool',0),('pool',1),('test',0),('test',1)]):
            iid=f'{b}-{split}-{y}';it={'dataset':b,'item_id':iid,'split':split,'label':y,'primary':{'sided':'two','candidates':['a','b']}}
            items.append({'item_id':iid,'split':split,'label':y,'state_row':j,'donor_item_id':f'{b}-{split}-{1-y}',
                          'donor_state_row':j^1,'label_info':{'kind':'construction'},'item':it})
        facts.append({'bank':b,'dataset':b,'tag':'TEST','states':states,'items':items});banks[b]={'sha256':'bank'}
    m={'facts':facts,'banks':banks,'items':12};meta={'pod':'mock','git_sha':'g','code_sha':'c'}
    root=tmp_path/'capture';result=R.capture(m,root,meta,True,32,None,mock=True)
    assert result['coverage']['arm_cells']==72 and result['coverage']['score_rows']==48
    idxpath=next(root.rglob('index.json'));idx=json.loads(idxpath.read_text());scorepath=idxpath.parent/'scores.jsonl'
    rows=R.read_jsonl(scorepath);rows[0]['source_item_id']='wrong'
    scorepath.write_text(''.join(json.dumps(r)+'\n' for r in rows));idx['scores_sha256']=R.sha(scorepath);R.save(idxpath,idx)
    with pytest.raises(ValueError,match='mapping mismatch'):R.audit(root,m,True)
    with pytest.raises(ValueError,match='Refuse existing'):R.capture(m,root,meta,True,32,None,mock=True)


def test_live_capture_checks_pull_window_before_any_model_load(tmp_path,monkeypatch):
    from projects.g_agreement.core import model as M
    def forbidden():raise AssertionError('Model load started inside pull reserve')
    monkeypatch.setattr(M,'load_target',forbidden);monkeypatch.setattr(R.time,'time',lambda:100)
    with pytest.raises(RuntimeError,match='before model load'):
        R.capture({'facts':[],'items':0},tmp_path/'out',{'pod':'p'},False,32,500,pull_reserve=450)


def test_measured_large_transfer_reserve_is_returned_to_live_runner():
    m=manifest();meta={'pod':'p','git_sha':'g','code_sha':'c'};guard={'guard_dir':'x','guard_sha256':'z','deadline_epoch':1300}
    cert={'manifest_sha256':R.digest(m),**meta,**guard,'batch':32,'kind':'live','coverage':{'arm_cells':72},
          'projected_full_seconds':100,'projected_tap_bytes':40000,'measured_pull_bytes_per_second':100,'load_seconds':{'olens':10,'nla':20}}
    gate=R.throughput_gate(cert,m,meta,guard,32,now=100)
    assert gate['pull_reserve_seconds']==600 and gate['model_load_seconds']==cert['load_seconds']


def test_kway_is_unavailable_not_a_first_two_candidate_binary_score():
    rows=[{'split':split,'primary':{'sided':'kway'}} for split in ('pool','test') for i in range(2)]
    assert 'K-way' in R.eligibility_problem(rows)
    with pytest.raises(ValueError,match='K-way'):R.native_value({'lo':1},{'primary':{'sided':'kway'}})
    assert R.eligibility_problem([{'split':split,'primary':{'sided':'two'}} for split in ('pool','test') for i in range(2)]) is None


def test_read_position_hook_keeps_no_sequence_and_rejoins_groups(monkeypatch):
    import torch
    from projects.g_agreement.r_bench import collect as K
    from projects.g_agreement.core import model as M
    monkeypatch.setattr(R.C,'D_MODEL',4)
    blocks=torch.nn.ModuleList([torch.nn.Identity() for _ in range(41)])
    class Base:
        def __init__(self,*args):self.model=object();self.head_len=3
        def templates_for(self,fam):return ['{X}']
    monkeypatch.setattr(K,'ReaderStateHook',Base);monkeypatch.setattr(M,'blocks',lambda model:blocks)
    with R.ReadPositionHook(object(),R.TAPS,44) as hook:
        h=torch.randn(4,128,4);h[0:2,2]=3;h[2:4,2]=7
        for layer in R.TAPS:blocks[layer](h)
    assert all(v[0].shape==(4,4) and v[0].dtype==torch.float16 for v in hook.forwards.values())
    arrays,indices,meta=hook.assemble([('a','b'),('c','d')],32,[('family',[1,0])])
    assert indices==[] and meta['position']=='pre_answer'
    assert all(x.shape==(2,4) and (x[0]==7).all() and (x[1]==3).all() for x in arrays.values())
    hook.base.templates_for=lambda fam:['{X}','second {X}']
    with pytest.raises(ValueError,match='one frozen template'):hook.assemble([('a','b'),('c','d')],32,[('family',[1,0])])
