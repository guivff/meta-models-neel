"""Tiny-model runner integration and operational entry wiring, CPU only."""
import contextlib,time,sys
import numpy as np
import pytest
from projects.g_agreement.e101 import runner105 as R
from projects.g_agreement.e101.contract import read,write,sha
from projects.g_agreement.e101.runner import dependencies
from projects.g_agreement.e101.test_e101 import Tiny


class Runtime:
    def __init__(self,*args):
        self.base=Tiny();self.hardware_assignment={'gpu_type':'CPU_SYNTHETIC'};self.loaded=[]
    def load_base(self):self.loaded.append('base')
    def subject(self):return self.base,None,contextlib.nullcontext()
    def load_oracle(self):pytest.fail('reader requested')
    def load_nla(self):pytest.fail('reader requested')


def packet():
    items=[]
    for i in range(3):
        for cond in ('T','S','0'):
            items.append(dict(id=f'{i}:{cond}',inventory_id=f'inv{i}',base_id=str(i),row='nesting_depth',
              condition=cond,block=44,ids=[1,2],read_index=1,candidate_ids=[[[3],[3,4]]],
              vector_index=None if cond=='0' else i*2+(cond=='S'),donor_id=None if cond=='0' else 'donor'))
    vectors=np.arange(24,dtype=np.float32).reshape(6,4)
    return items,dict(vectors=vectors,manifest={'experiment':'E105','row':'nesting_depth'})


def test_tiny_production_complete_raw_source_pointers_and_no_readers(tmp_path):
    xs,data=packet();before=data['vectors'].tobytes();rt=Runtime();old,*_=dependencies()
    assert R.acquire(xs,data,rt,old.Clock(tmp_path,time.time()+3600),tmp_path)=='COMPLETE'
    assert rt.loaded==['base'] and data['vectors'].tobytes()==before
    assert len(read(tmp_path/'COMPLETED.json'))==3
    index=read(tmp_path/'MEASUREMENT_INDEX.json');assert len(index)==3
    for item in index:
        assert set(item['conditions'])=={'T','S','0'}
        for cond,ref in item['conditions'].items():
            raw=read(tmp_path/ref['member']);record=raw[ref['keys'][0]]
            assert record['inventory_id']==item['id'] and record['condition']==cond
            assert np.isfinite(record[ref['keys'][1]]).all()
    assert not any(layer._forward_hooks for layer in rt.base.layers)
    phases=[x['phase'] for x in read(tmp_path/'PHASE_TIMINGS.json')]
    assert phases.count('base_setup')==1 and phases.count('logits_0_warmup_discarded')==1


def test_timing_covers_each_condition_without_complete_index(tmp_path):
    xs,data=packet();old,*_=dependencies()
    assert R.acquire(xs,data,Runtime(),old.Clock(tmp_path,time.time()+3600),tmp_path,True)=='TIMING_ONLY'
    assert not (tmp_path/'MEASUREMENT_INDEX.json').exists()
    profile=read(tmp_path/'MEASURED_PROFILE.json')
    assert {p['phase'] for p in profile['phases']}=={'logits_T','logits_S','logits_0'}
    assert profile['profile_outputs_discarded'] and profile['setup_warmup_seconds']>0
    assert read(tmp_path/'SMOKE_COVERAGE.json')['conditions']==['T','S','0']


def test_failure_removes_intervention_hooks(tmp_path):
    xs,data=packet();data['vectors'][0,0]=np.nan;rt=Runtime();old,*_=dependencies()
    with pytest.raises(ValueError):R.acquire(xs,data,rt,old.Clock(tmp_path,time.time()+3600),tmp_path)
    assert not any(layer._forward_hooks for layer in rt.base.layers)
    assert not (tmp_path/'MEASUREMENT_INDEX.json').exists()


def test_entry_point_uses_e101_wrapper_and_base_text_capability(monkeypatch):
    from projects.g_agreement.e101 import operational
    calls=[]
    monkeypatch.setattr(operational,'run',lambda *a,**k:calls.append((a,k)))
    monkeypatch.setattr(sys,'argv',['runner105'])
    R.main()
    assert calls==[(('E105',R.load,R.acquire,['text']),dict(seed=20261030))]


def test_operational_timing_seals_real_tiny_jobs(tmp_path,monkeypatch):
    from projects.g_agreement.e101 import operational as op
    from projects.g_agreement.e101 import runner
    xs,data=packet();assets=tmp_path/'assets.json';write(assets,{})
    source=tmp_path/'source.json';write(source,{})
    assignment=tmp_path/'assignment.json';created=time.time()
    ass=dict(experiment='E105',input_sha256='input',source_sha256='source',assets_sha256=sha(assets),
      gpu_count=1,daily_budget_verified=True,pod_id='own',cap_seconds=3600,pod_created_epoch=created,
      absolute_deadline_epoch=created+3600,gpu_type='H200')
    write(assignment,ass);out=tmp_path/'out'
    monkeypatch.setenv('RUNPOD_POD_ID','own');monkeypatch.setattr(op,'ROOT',tmp_path)
    monkeypatch.setattr(op,'verify',lambda *a:None)
    monkeypatch.setattr(R,'load',lambda root:(xs,data))
    old,*_=dependencies();capabilities=[]
    def gate(ass,receipt,assets,caps):
        capabilities.extend(caps);return dict(gpu_type='H200',actual_gpu_name='CPU_SYNTHETIC')
    monkeypatch.setattr(op,'dependencies',lambda:(old,Runtime,gate,lambda *a:None,lambda x:True))
    monkeypatch.setattr(sys,'argv',['runner105','--inputs',str(tmp_path),'--assets',str(assets),
      '--assignment',str(assignment),'--source-seal',str(source),'--source-sha','source',
      '--input-sha','input','--out',str(out),'--timing'])
    R.main();seal=read(out/'OUTPUT_SEAL.json')
    assert seal['experiment']=='E105' and seal['status']=='TIMING_ONLY' and capabilities==['text']
    assert 'jobs/000000.json' in seal['files'] and seal['first_output_evidence']
    assert read(out/'MEASURED_PROFILE.json')['experiment']=='E105'
