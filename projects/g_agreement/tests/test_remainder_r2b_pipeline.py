import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_pipeline as P,remainder_r2b_runner as R,remainder_r2b as D,remainder_r2b_slice as S


def test_slice_end_to_end_fake_model_isolated(tmp_path,monkeypatch):
    from projects.g_agreement.r_bench import remainder_r2b_analysis as A
    monkeypatch.setattr(A,'summarize',lambda rows:[{'n':len(rows)}])
    cells=[dict(item_id=s,split=s,label=1,population='main',recipe='base',probe_group=s,cohort='family',dataset='d',item={},reader='olens',arm='natural',tap_blocks=[2,4,6],generate=False) for s in ('pool','test')]
    keys={c['split']:R.cell_key(c) for c in cells}
    jobs=[dict(job_id=f'j{b}',cohort='family',block=b,train=[keys['pool']],evaluate=[keys['test']]) for b in cells[0]['tap_blocks']]
    def fit(jobs,records,guard):
        return [dict(job_id=j['job_id'],block=j['block'],pool_validation_accuracy=.9,mean=[0.,0.,0.],raw_normal=[1.,0.,0.],train_cells=j['train'],evaluation_cells=j['evaluate']) for j in jobs],[]
    class Engine:
        closed=False
        def execute(self,c):return dict(lo=1.,displacement=dict(intended_l2=1.,realized_l2=1.)),{b:np.ones(3,dtype=np.float16) for b in c['tap_blocks']}
        source=execute
        def close(self):self.closed=True
    engine=Engine();process=D.stamp('fake','a','a'*64,'test')
    result=P.run_slice(dict(cells=cells,probe_jobs=jobs,transfer_jobs=[]),tmp_path,process,engine,lambda:None,fit_jobs=fit)
    assert engine.closed
    import json
    rows=[json.loads(l) for l in ( __import__('pathlib').Path(result['causal_dir'])/'rows.jsonl').read_text().splitlines()]
    assert {r['cell']['arm'] for r in rows}==set(S.ARMS)
    assert all(r['run_kind']=='test' for r in rows)
    assert all(p.is_relative_to(tmp_path) for p in tmp_path.rglob('*'))


def test_pipeline_unsupported_arm_decoy(tmp_path):
    with pytest.raises(ValueError,match='decoy'):
        P.run_slice(dict(cells=[dict(reader='nla',arm='decoy')],probe_jobs=[],transfer_jobs=[]),tmp_path,{},None,lambda:None)


def test_smoke_failure_decoy_prevents_full_capture(tmp_path):
    class Engine:
        calls=0;closed=False
        def execute(self,cell):
            self.calls+=1
            raise ValueError('decoy-missing-state')
        def close(self):self.closed=True
    engine=Engine();cell=dict(reader='olens',arm='natural',dataset='d',split='pool',tap_blocks=[2])
    with pytest.raises(ValueError,match='SMOKE FAILED:.*decoy-missing-state'):
        P.run_slice(dict(cells=[cell],probe_jobs=[],transfer_jobs=[]),tmp_path,D.stamp('fake','a','a'*64,'test'),engine,lambda:None)
    assert engine.calls==1 and engine.closed
