import json
import numpy as np
import pytest
from projects.g_agreement.r_bench import section49 as S

def test_split_exact_norms_and_components():
 q=np.eye(4)[:,:2];d=np.array([[3.,4.,0.,12.],[1.,2.,3.,4.]])
 a=S.split_edit(d,q,41)
 for v in a.values():np.testing.assert_allclose(np.linalg.norm(v,axis=1),np.linalg.norm(d,axis=1),rtol=1e-6)
 np.testing.assert_allclose(a['J'][:,2:],0);np.testing.assert_allclose(a['perp'][:,:2],0)
 for k in a:np.testing.assert_array_equal(a[k],S.split_edit(d,q,41)[k])
 assert not np.allclose(a['random0'],a['random1'])

def test_degenerate_not_silently_replaced():
 with pytest.raises(ValueError,match='Degenerate'):S.split_edit(np.array([1.,0.,0.,0.]),np.eye(4)[:,:2],0)
 for v in S.split_edit(np.zeros(4),np.eye(4)[:,:2],0).values():assert not v.any()

def test_wilson_cutoff():
 assert S.wilson(0)[1]==pytest.approx(.019222531917868147)
 assert S.wilson(3)[1]<.05<S.wilson(4)[1]

def test_plan_all196_donors_same_template():
 plan=S.read(S.REG/'plan.json');bank={r['id']:r for r in plan['records']}
 assert set(bank)==set(S.read(S.REG/'bank_inventory.json')['item_ids']);assert len(bank)==196
 for r in bank.values():
  donor=bank[r['donor']];assert r['template']==donor['template'];assert r['bridge']!=donor['bridge'];assert r['answer']!=donor['answer']
 assert len(plan['smoke_ids'])==4 and set(plan['smoke_ids'])<set(bank)

def test_no_partial_verdict(tmp_path):
 with pytest.raises(ValueError,match='coverage'):S.analyze(tmp_path)

def test_release_detects_changed_file(tmp_path):
 remote=tmp_path/'remote';local=tmp_path/'local';remote.mkdir();local.mkdir()
 (remote/'x').write_text('ok');S.package(remote)
 for p in remote.iterdir():(local/p.name).write_bytes(p.read_bytes())
 S.mac_receipt(local)
 assert S.release(remote,local/'mac_receipt.json')['status']=='VERIFIED_READY_TO_STOP'
 (local/'x').write_text('corrupt')
 with pytest.raises(ValueError):S.mac_receipt(local)

def test_paired_ci_control():
 assert S.paired_ci(np.zeros(196))==[0.,0.]
 assert S.paired_ci(np.ones(196),['a']*98+['b']*98)==[1.,1.]


def test_answer_parse_not_punctuation_flip():
 assert S.answer_label('Spanish.', ['Spanish','Portuguese'])=='Spanish'
 assert S.answer_label('Spanish or Portuguese', ['Spanish','Portuguese'])=='Spanish'
 assert S.answer_label('unknown', ['Spanish','Portuguese']) is None

def test_analysis_three_conditions_and_separate_circular(tmp_path,monkeypatch):
 # Complete frozen-sized synthetic table: J follows, random does not, perp follows,
 # zero J flips. Exercises actual coverage and verdict rather than an isolated formula.
 plan=S.read(S.REG/'plan.json');ids=[r['id'] for r in plan['records']]
 monkeypatch.setattr(S,'paired_ci',lambda x,groups=None:[float(np.mean(x)),float(np.mean(x))])
 (tmp_path/'smoke').mkdir();(tmp_path/'full').mkdir()
 for iid in ids:
  for arm,alpha in S.CELLS:
   S.append(tmp_path/'full/model.jsonl',{'item':iid,'arm':arm,'alpha':alpha,'flip':False})
   for reader in S.READERS:
    S.append(tmp_path/'full'/f'{reader}.jsonl',{'item':iid,'arm':arm,'alpha':alpha,'lo_original_minus_donor':-1. if arm in ('J','perp','full') else 0.})
 result=S.analyze(tmp_path)
 assert result['readers']['olens']['1.0']['verdict']=='SENSITIVITY WITHOUT USE'
 assert result['readers']['jlens']['1.0']['verdict']=='CIRCULAR_DESCRIPTIVE'
 assert result['readers']['olens']['1.5']['verdict']=='DESCRIPTIVE'
 # Duplicates must never be accepted as complete coverage.
 S.append(tmp_path/'full/model.jsonl',{'item':ids[0],'arm':'J','alpha':1.,'flip':False})
 with pytest.raises(ValueError,match='coverage'):S.analyze(tmp_path)

def test_admission_requires_intact_smoke(tmp_path):
 (tmp_path/'smoke').mkdir();p=tmp_path/'smoke/x';p.write_text('ok')
 S.save(tmp_path/'projection.json',{'admitted':True,'smoke_files':{'x':S.sha(p)}});S.require_admission(tmp_path)
 p.write_text('changed')
 with pytest.raises(ValueError,match='changed'):S.require_admission(tmp_path)
 S.save(tmp_path/'projection.json',{'admitted':False})
 with pytest.raises(ValueError,match='not admitted'):S.require_admission(tmp_path)


def test_amended_parser_smoke_and_order():
 vocab=sorted({r['answer'] for r in S.read(S.REG/'plan.json')['records']})
 text='The country famous for the moai statues'
 assert S.answer_label(text,vocab) is None
 assert S.answer_measure(text,text,vocab)['flip'] is None
 assert S.answer_label('Portuguese, not Spanish.', ['Spanish','Portuguese'])=='Portuguese'
 assert S.answer_label('New York then York', ['York','New York'])=='New York'
 assert S.answer_label('Spanishish', ['Spanish']) is None
 assert S.ANSWER_TOKENS==64
 records=[{'item':str(i),'unparseable':i==0} for i in range(20)]
 assert S.smoke_parse_gate(records)['rate']==.05
 with pytest.raises(ValueError,match='5%'):S.smoke_parse_gate(records[:19])

def test_unresolved_never_counted_as_known_nonflip(tmp_path,monkeypatch):
 plan=S.read(S.REG/'plan.json');monkeypatch.setattr(S,'paired_ci',lambda x,groups=None:[1.,1.])
 (tmp_path/'full').mkdir()
 for i,r in enumerate(plan['records']):
  for arm,alpha in S.CELLS:
   unknown=i<4 and arm=='J'
   S.append(tmp_path/'full/model.jsonl',{'item':r['id'],'arm':arm,'alpha':alpha,'flip':None if unknown else False,'unparseable':unknown})
   for reader in S.READERS:S.append(tmp_path/'full'/f'{reader}.jsonl',{'item':r['id'],'arm':arm,'alpha':alpha,'lo_original_minus_donor':-1. if arm in ('J','perp') else 0.})
 result=S.analyze(tmp_path)
 assert result['flips']['J/1.0']['unresolved']==4
 assert result['flips']['J/1.0']['n']==196
 assert result['readers']['olens']['1.0']['verdict']=='CRITERION NOT MET'


def test_missing_native_payload_logged_and_next_cell_survives(tmp_path):
 bad={'unscorable':True,'lo':None,'reason':'no single-token variant for B','variants_B':{}}
 first=S.reader_cell('i','d','natural',0.,'jlens',44,bad)
 second=S.reader_cell('j','d','natural',0.,'jlens',44,{'lo':1.,'unscorable':False})
 S.append(tmp_path/'cells.jsonl',first);S.append(tmp_path/'cells.jsonl',second)
 assert first['status']=='MISSING' and first['native']==bad
 assert second['status']=='OK' and len(S.rows(tmp_path/'cells.jsonl'))==2
 row=S.reader_cell('i','d','J',1.,'rlens',44,{'lo':float('nan')})
 assert row['status']=='MISSING' and row['native']['lo']=='nan'

def test_missing_follow_bounds_keep_denominator_and_natural_dependency():
 d={('a','natural',0.):None,('a','J',1.):-1.,('b','natural',0.):0.,('b','J',1.):-1.}
 lo,hi=S.follow_bounds(d,['a','b'],'J',1.)
 assert list(lo)==[0.,1.] and list(hi)==[1.,1.]


def test_standing_missing_thresholds():
 rr=[{'arm':'J','alpha':1.,'status':'MISSING' if i<4 else 'OK'} for i in range(20)]
 x=S.missing_summary({'jlens':rr});assert x['rate']==.2;S.missing_gate(x)
 assert x['arms']['jlens/J/1.0']['format_limited']
 with pytest.raises(ValueError,match='20%'):S.missing_gate(S.missing_summary({'jlens':rr[:-1]}))
