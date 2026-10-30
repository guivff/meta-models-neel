import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_engine as E,remainder_r2b as D,remainder_r2b_runner as R


class FakeEngine:
    def __init__(self):self.closed=False
    def execute(self,cell):return {'lo':.25},{k:np.ones(4,dtype=np.float16) for k in cell['tap_blocks']}
    def close(self):self.closed=True


def test_collection_to_verified_output_same_orchestration(tmp_path):
    cells=[dict(reader='olens',arm=a,item_id='synthetic',tap_blocks=[2,4,6]) for a in D.ARMS]
    m={'cells':cells};p=D.stamp('fake','sha','a'*64,'test');writer=R.RunWriter(tmp_path,m,p);engine=FakeEngine();checks=[]
    files=E.execute_manifest(m,'olens',writer,engine,lambda:checks.append(1))
    assert len(checks)==len(cells) and engine.closed
    assert len(writer.seen)==len(cells) and 'rows.jsonl' in files


def test_phase_and_array_decoys(tmp_path):
    cell=dict(reader='olens',arm='natural',item_id='decoy',tap_blocks=[2]);m={'cells':[cell]}
    writer=R.RunWriter(tmp_path,m,D.stamp('fake','sha','a'*64,'test'));engine=FakeEngine()
    with pytest.raises(ValueError,match='nla'):E.execute_manifest(m,'nla',writer,engine,lambda:None)
    class Bad(FakeEngine):
        def execute(self,c):return {},{4:np.ones(4,dtype=np.float16)}
    engine=Bad()
    with pytest.raises(ValueError,match='decoy'):E.execute_manifest(m,'olens',writer,engine,lambda:None)
    assert engine.closed


def test_guard_denies_before_engine_and_closes(tmp_path):
    cell=dict(reader='olens',arm='natural',item_id='decoy',tap_blocks=[]);m={'cells':[cell]}
    w=R.RunWriter(tmp_path,m,D.stamp('fake','sha','a'*64,'test'));e=FakeEngine()
    def guard():raise ValueError('decoy deadline')
    with pytest.raises(ValueError,match='decoy deadline'):E.execute_manifest(m,'olens',w,e,guard)
    assert e.closed and not w.seen


def test_unpinned_oracle_asset_decoy():
    from projects.g_agreement.r_bench.remainder_r2b_engine import validate_oracle_assets
    with pytest.raises(ValueError,match='decoy'):
        validate_oracle_assets(dict(target_revision='decoy-revision'))
