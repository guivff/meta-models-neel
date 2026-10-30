import hashlib,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from projects.g_agreement.r_bench import section49 as S


def test_hash_shards_exhaustive_disjoint_and_donors_preserved():
 bank=S.read(S.REG/'plan.json');seen=[]
 for k in range(4):
  p=S.shard_plan(k);ids=p['recipient_ids'];seen+=ids
  assert len(ids)==49 and len(p['records'])==196
  assert p['records']==bank['records']
  assert len(S.chosen_records(p,True))==4
  assert len(S.chosen_records(p,False))==45
  assert set(ids)=={r['id'] for r in S.chosen_records(p,True)+S.chosen_records(p,False)}
 assert len(set(seen))==len(seen)==196
 assert set(seen)=={r['id'] for r in bank['records']}
 with pytest.raises(ValueError):S.shard_plan(True)
 with pytest.raises(ValueError):S.shard_plan(4)


def test_registered_short_forms_and_no_substitution_for_other_readers():
 bank={r['id']:r for r in S.read(S.REG/'plan.json')['records']}
 r=bank['re-re_khop2_bridge-test-0004'];d=bank[r['donor']]
 for name in ('jlens','rlens','jpp'):assert S.reader_candidates(name,r,d)==('Croatia','Netherlands')
 for name in ('olens','nla','skip_a'):assert S.reader_candidates(name,r,d)==('Croatia','the Netherlands')


def test_projection_uses_45_remaining_and_measured_reserve(tmp_path,monkeypatch):
 p=S.shard_plan(0);(tmp_path/'smoke').mkdir()
 for name in ('model',)+S.READERS:
  for i in p['smoke_ids']:
   for arm,a in S.CELLS:S.append(tmp_path/'smoke'/f'{name}.jsonl',{'item':i,'arm':arm,'alpha':a,'status':'OK'})
 S.save(tmp_path/'smoke/target_timing.json',{'capture_s':40,'reader_s':{'x':40},'setup_s':100})
 S.save(tmp_path/'smoke/nla_timing.json',{'score_s':40,'setup_s':20})
 monkeypatch.setattr(S,'Guard',lambda run:SimpleNamespace(plan=p,booking={'deadline':10000},reserve=600))
 monkeypatch.setattr(S.time,'time',lambda:1000)
 result=S.projection(tmp_path)
 assert result['remaining_items']==45
 assert result['projected_science_s']==1.25*(45*30+120)
 assert result['remaining_science_s']==8400 and result['admitted']
 monkeypatch.setattr(S.time,'time',lambda:9000)
 with pytest.raises(RuntimeError,match='Timing'):S.projection(tmp_path)


def fake_shard(root,k):
 p=S.shard_plan(k);root.mkdir(parents=True)
 S.save(root/'booking.json',{'shard_id':k,'shards_sha256':S.sha(S.REG/'shards.json'),'source_commit':'synthetic-source','pod_id':f'fake-{k}'})
 for phase,smoke in [('smoke',True),('full',False)]:
  (root/phase).mkdir()
  for r in S.chosen_records(p,smoke):
   for arm,a in S.CELLS:
    S.append(root/phase/'model.jsonl',{'item':r['id'],'arm':arm,'alpha':a,'flip':False})
    for name in S.READERS:S.append(root/phase/f'{name}.jsonl',{'item':r['id'],'arm':arm,'alpha':a,'status':'OK','lo_original_minus_donor':-1. if arm in ('J','perp') else 0.})
 S.analyze_shard(root);S.save(root/'chain_result.json',{'status':'COMPLETE'})
 S.package(root);S.mac_receipt(root);S.release(root,root/'mac_receipt.json')
 S.save(root.parent/'stop.json',{'status':'EXITED','pod':f'fake-{k}'})
 return root


def test_four_verified_shards_merge_once_at_n196(tmp_path,monkeypatch):
 import numpy as np
 monkeypatch.setattr(S,'paired_ci',lambda x,groups=None:[float(np.mean(x))]*2)
 inputs=[fake_shard(tmp_path/str(k)/'final',k) for k in range(4)]
 before=[S.sha(p/'SHARD_RESULTS.json') for p in inputs]
 result=S.merge_shards(inputs,tmp_path/'merged')
 assert result['n']==196 and result['flips']['J/1.0']['n']==196
 assert result['readers']['olens']['1.0']['verdict']=='SENSITIVITY WITHOUT USE'
 assert before==[S.sha(p/'SHARD_RESULTS.json') for p in inputs]
 with pytest.raises(ValueError,match='Duplicate'):S.merge_shards([inputs[0]]*4,tmp_path/'bad')
 with pytest.raises(ValueError,match='four'):S.merge_shards(inputs[:3],tmp_path/'partial')
 (inputs[0]/'full/model.jsonl').write_text('corrupt')
 with pytest.raises(ValueError,match='hash mismatch'):S.merge_shards(inputs,tmp_path/'corrupt')


def test_shard_never_reports_confirmatory_verdict(tmp_path):
 p=fake_shard(tmp_path/'one',0)
 result=S.analyze(p)
 assert result['status']=='SHARD_COMPLETE_NO_CONFIRMATORY_VERDICT'
 assert 'readers' not in result
 S.append(p/'full/model.jsonl',S.rows(p/'full/model.jsonl')[0])
 with pytest.raises(ValueError,match='coverage'):S.analyze(p)
