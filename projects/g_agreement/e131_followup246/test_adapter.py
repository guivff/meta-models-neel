from copy import deepcopy
import pytest
from . import adapter as a
from projects.g_agreement.e127_analysis.test_rules import code

def rows():
    out=[]
    for i in range(84):
        old=code('A');new=code('B')
        out.append(dict(item_id=str(i),old_value='A',new_value='B',text_class='new' if i<43 else 'neither',alpha4_cohort=i<42,
          e104_original44={'steered':old,'random':old},e109_reference44={'steered':old,'random':new},e109_52={'steered':new,'random':old},
          e121={c:['wrong','wrong'] for c in ('steered','random')},e123={c:[old,new] for c in ('steered','random','unhooked')}))
    return out

def test_full_counts_wilson_overlap_and_banks():
    r=a.analyze(rows());g=r['groups']['new']
    assert g['reader_banks']['e104_original44']['steered']['old']['k']==43
    assert g['reader_banks']['e109_reference44']['random']['new']['k']==43
    assert g['block52_new']['steered']['Wilson95'][1]==1
    assert g['e121_agreements']['steered']['k']==43
    assert g['e123_disagreement_flags']['steered']['k']==43
    assert r['text_by_alpha4_cohort']=={'new':{'in':42,'out':1},'neither':{'in':0,'out':41}}
    assert r['old44_difference']['e104_original44']['CI95']==[0.,0.]

def test_missing_and_neither_dual_stay_distinct():
    xs=rows();xs[0]['e104_original44']['steered']=code(None,'UNPARSEABLE');xs[1]['e104_original44']['steered']=code(None)
    xs[2]['e104_original44']['steered']=dict(category='states_value',values=['A','B'],evidence='A B')
    xs[0]['e121']['steered']=[None,'wrong'];xs[1]['e121']['steered']=['no mention','no mention']
    xs[0]['e123']['steered']=[code(None,'UNPARSEABLE'),code('B')]
    r=a.analyze(xs,50)['groups']['new'];z=r['reader_banks']['e104_original44']['steered']
    assert z['old']['k']==40 and z['old']['n']==42 and z['old']['missing_n']==1
    assert z['neither']['k']==1 and z['dual']['k']==1
    assert r['e121_agreements']['steered']['k']==41 and r['e121_agreements']['steered']['n']==42
    assert r['e123_disagreement_flags']['steered']['missing_n']==1

def test_bootstrap_difference_sign_and_order_invariance():
    xs=rows()
    for x in xs:
        if x['text_class']=='neither':x['e104_original44']['steered']=code(None)
    r=a.difference(xs,'e104_original44')
    assert r['estimate']==1 and r['CI95']==[1.,1.] and r['valid_draws']==5000
    assert r==a.difference(list(reversed(xs)),'e104_original44')

def test_all_missing_group_reports_undefined_not_zero():
    xs=rows()
    for x in xs:
        if x['text_class']=='new':x['e104_original44']['steered']=None
    r=a.difference(xs,'e104_original44',100)
    assert r['estimate'] is None and r['CI95'] is None and r['undefined_draws']==100

@pytest.mark.parametrize('mutation',[lambda x:x.pop(),lambda x:x[0].update(text_class='old'),lambda x:x[0].update(alpha4_cohort=False),lambda x:x[0].update(item_id='1')])
def test_invalid_census_fails(mutation):
    xs=rows();mutation(xs)
    with pytest.raises(ValueError):a.analyze(xs,10)

def test_guard_refusal_before_any_load(tmp_path,monkeypatch):
    monkeypatch.setattr(a,'CUSTODY',tmp_path);(tmp_path/'ANALYSIS_ONCE.json').write_text('{}')
    monkeypatch.setattr(a,'load',lambda s:pytest.fail('opened outputs'))
    with pytest.raises(ValueError,match='consumed'):a.run({},'test')

def test_commit_gate_precedes_open(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['adapter','--spec','never'])
    def fail(*args):raise ValueError('uncommitted')
    monkeypatch.setattr(a.t,'committed',fail);monkeypatch.setattr(a.t.core,'read',lambda p:pytest.fail('read before commit'))
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_exact_owner_packet_rejected_before_classifications(tmp_path):
    p=tmp_path/'packet.json';p.write_text('{}')
    with pytest.raises(ValueError,match='exact W-text'):
        a.load(dict(join_packet=str(p),join_sha256=a.t.core.sha(p)))

def test_full_literal_join_loader_without_real_inputs(monkeypatch):
    core=a.t.core;ids=[str(i) for i in range(84)]
    items=[dict(item_id=i,old_value='A',new_value='B') for i in ids]
    classes=[dict(id='c'+i,base_id='b'+i,condition='e104_steered_8',text_value='new' if int(i)<43 else 'neither') for i in ids]
    joins=[dict(e104_item_id=i,e127_original_base_id=i,e104_source_record_id='s'+i,e131_id='c'+i,e131_base_id='b'+i,text_class=classes[int(i)]['text_value']) for i in ids]
    labels=[dict(item_id=i,condition=k,row='fact_recall',arm='U',id='s'+i,opaque_id=i+k,text='A B') for i in ids for k in ('steered','random')]
    codes=[dict(code('A'),id=i+k,evidence='A') for i in ids for k in ('steered','random')]
    mapping={'packet':{'records':joins},'text/CLASSIFICATIONS.PRIVATE.json':classes,'128spec':{'e104_private':'labels'},'labels':labels,'104/JUDGMENTS.json':codes,'121/BINDING.json':{},'123/BINDING.json':{}}
    monkeypatch.setattr(core,'read',lambda p:deepcopy(mapping[str(p)]));monkeypatch.setattr(core,'sha',lambda p:'f03acd297f0cca855167fea022a118199791062b8632afad7f0333d996e3f1f6')
    monkeypatch.setattr(core,'verify',lambda *x:{'files':{'CLASSIFICATIONS.PRIVATE.json':'synthetic'}})
    monkeypatch.setattr(a.t,'cohort',lambda *x:(items,{},{}));monkeypatch.setattr(a,'fixed_cohort',lambda *x:set(ids[:42]))
    monkeypatch.setattr(a.e121,'inputs',lambda s:[dict(item_id=i,condition=k,reader=r,**{'class':'wrong'}) for i in ids for k in ('steered','random') for r in ('oracle','nla')])
    monkeypatch.setattr(a.e123,'metadata',lambda s:{})
    monkeypatch.setattr(a.e123,'inputs',lambda *s:{'fact_recall':[dict(item_id=i,conditions={k:{'44':code('A'),'52':code('B')} for k in ('steered','random','unhooked')}) for i in ids]})
    spec=dict(join_packet='packet',join_sha256=core.sha('packet'),e131_analysis_seal='text/seal',e128_spec='128spec',e104_judgment_seal='104/seal',e121_analysis_seal='121/seal',e123_analysis_seal='123/seal')
    xs=a.load(spec);assert len(xs)==84 and a.analyze(xs,10)['groups']['new']['n']==43
    joins[0]['e104_source_record_id']='wrong-source'
    with pytest.raises(ValueError,match='source identity'):a.load(spec)
