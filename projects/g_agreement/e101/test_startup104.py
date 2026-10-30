import contextlib,shutil,time,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101 import capture104
from projects.g_agreement.e101.contract import read,write,sha
from projects.g_agreement.e101.package104 import ROOT,source_paths
from projects.g_agreement.e101.preflight104 import runtime_import


def test_real_runtime_import_from_fresh_source_and_missing_common_decoy(tmp_path):
    paths=source_paths()
    assert {str(p.relative_to(ROOT)) for p in (ROOT/'common').glob('*.py')}<=paths
    for name in paths:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    result=runtime_import(tmp_path)
    assert result['status']=='PASS' and result['model_loaded'] is False and result['GPU_calls']==0
    assert result['runtime_imports']['common']=='common/__init__.py'
    shutil.rmtree(tmp_path/'common')
    with pytest.raises(RuntimeError,match='common'):runtime_import(tmp_path)


def packet(tmp_path,monkeypatch):
    public=tmp_path/'inputs';public.mkdir()
    xs=[dict(id=f'dev-{i}',ids=[1]*9+[3+i%4],read_index=9) for i in range(168)]
    write(public/'items.json',xs)
    write(public/'INPUT_SEAL.json',dict(experiment='E104',stage='dev_direction40',block=40,position='read_token',labels_on_pod=False,records=168,files={'items.json':sha(public/'items.json')}))
    digest=sha(public/'INPUT_SEAL.json');request=tmp_path/'REQUEST.json'
    write(request,dict(public_input_sha256=digest,records=168,rows=['fact_recall','language_plan']))
    monkeypatch.setattr(capture104,'REQUEST',request)
    return public,digest


class CaptureRuntime:
    def __init__(self):self.loads=0;self.hardware_assignment={'gpu_type':'CPU_SYNTHETIC'}
    def load_base(self):self.loads+=1
    def subject(self):
        return object(),SimpleNamespace(pad_token_id=0,encode=lambda *args,**kwargs:[2]),contextlib.nullcontext()


def test_capture_entry_calls_owner_once_after_discarded_warmup_and_refuses_replay(tmp_path,monkeypatch):
    from projects.g_agreement.e101.runner import dependencies
    old,_,_,_,_=dependencies()
    from projects.g_agreement.e104_vectors import build as owner
    import mats.capture as mats_capture
    inputs,digest=packet(tmp_path,monkeypatch);calls=[];invocations=[]
    def capture(model,sequences,layers,positions,**kwargs):
        calls.append((sequences,layers,positions));return {40:torch.full((1,1,5120),float(len(calls)))}
    monkeypatch.setattr(mats_capture,'capture',capture)
    original=owner.capture_once
    def once(*args,**kwargs):invocations.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(owner,'capture_once',once)
    runtime=CaptureRuntime();out=tmp_path/'out';out.mkdir()
    clock=old.Clock(out,time.time()+1800)
    assert capture104.acquire_capture(inputs,digest,runtime,clock,out)=='COMPLETE'
    assert runtime.loads==1 and len(invocations)==1 and len(calls)==169
    assert calls[0]==([[2]*32],[40],[[31]])
    assert [x['phase'] for x in clock.events[:2]]==['capture40_setup','capture40_warmup_discarded']
    assert all(c[1]==[40] and c[2]==[[9]] for c in calls[1:])
    assert np.load(out/'capture40/acts40.npy').shape==(168,5120)
    assert read(out/'capture40/CAPTURE_SEAL.json')['status']=='COMPLETE'
    assert (inputs/'CAPTURE_ONCE.json').exists() and (out/'capture40/START.json').exists()
    other=tmp_path/'different-output';other.mkdir()
    with pytest.raises(FileExistsError,match='CAPTURE_ONCE'):capture104.acquire_capture(inputs,digest,runtime,clock,other)
    assert runtime.loads==1 and len(calls)==169


def test_capture_failure_keeps_start_and_once_markers_no_implicit_retry(tmp_path,monkeypatch):
    from projects.g_agreement.e101.runner import dependencies
    old,_,_,_,_=dependencies()
    import mats.capture as mats_capture
    inputs,digest=packet(tmp_path,monkeypatch);n=[]
    def fail(model,sequences,layers,positions,**kwargs):
        n.append(1)
        if len(n)>1:raise RuntimeError('synthetic first real capture failure')
        return {40:torch.ones((1,1,5120))}
    monkeypatch.setattr(mats_capture,'capture',fail)
    out=tmp_path/'out';out.mkdir();runtime=CaptureRuntime()
    with pytest.raises(RuntimeError,match='first real'):capture104.acquire_capture(inputs,digest,runtime,old.Clock(out,time.time()+1800),out)
    assert len(n)==2 and (inputs/'CAPTURE_ONCE.json').exists() and (out/'capture40/START.json').exists()
    with pytest.raises(FileExistsError):capture104.acquire_capture(inputs,digest,runtime,old.Clock(out,time.time()+1800),out)
    assert len(n)==2


def test_capture_rejects_private_extra_wrong_packet_and_wrong_custody(tmp_path,monkeypatch):
    inputs,digest=packet(tmp_path,monkeypatch)
    with pytest.raises(ValueError):capture104.load_capture(inputs,'0'*64)
    (inputs/'PRIVATE.json').write_text('{}')
    with pytest.raises(ValueError,match='public'):capture104.load_capture(inputs,digest)
    monkeypatch.setenv('RUNPOD_POD_ID','own')
    a=dict(experiment='E104',stage='dev_direction40',capture_once=True,input_sha256='i',source_sha256='s',assets_sha256='a',gpu_count=1,daily_budget_verified=True,
        cap_seconds=1800,pod_id='own',custody_start_epoch=1,pod_created_epoch=1,absolute_deadline_epoch=1801)
    capture104.validate_assignment(a,'i','s','a')
    for change in (dict(cap_seconds=1801),dict(capture_once=False),dict(stage='dev'),dict(custody_start_epoch=2)):
        with pytest.raises(ValueError):capture104.validate_assignment(dict(a,**change),'i','s','a')


def test_runner_cli_dispatches_capture_and_capture_parser_rejects_timing(monkeypatch):
    from projects.g_agreement.e101 import runner104
    original=capture104.main
    with pytest.raises(SystemExit) as error:
        original(['--capture-dev40','packet','--capture-sha','s','--capture-out','out','--assets','a','--assignment','ass','--source-seal','ss','--source-sha','h','--timing'])
    assert error.value.code==2
    seen=[];monkeypatch.setattr(capture104,'main',lambda:seen.append('capture'))
    monkeypatch.setattr('sys.argv',['runner104','--capture-dev40=/frozen/public'])
    runner104.main();assert seen==['capture']


def test_capture_CLI_runs_source_custody_hardware_gates_and_seals_once_step(tmp_path,monkeypatch):
    from projects.g_agreement.e101.runner import dependencies
    old,_,_,_,_=dependencies()
    import mats.capture as mats_capture
    inputs,digest=packet(tmp_path,monkeypatch);events=[];instances=[]
    monkeypatch.setattr(capture104,'ROOT',tmp_path)
    (tmp_path/'source.py').write_text('# synthetic source fixture\n')
    write(tmp_path/'SOURCE.json',dict(files={'source.py':sha(tmp_path/'source.py')}))
    write(tmp_path/'assets.json',dict(synthetic=True))
    created=time.time();source_sha=sha(tmp_path/'SOURCE.json');asset_sha=sha(tmp_path/'assets.json')
    ass=dict(experiment='E104',stage='dev_direction40',capture_once=True,input_sha256=digest,source_sha256=source_sha,assets_sha256=asset_sha,
        gpu_count=1,daily_budget_verified=True,cap_seconds=1800,pod_id='own',custody_start_epoch=created,pod_created_epoch=created,absolute_deadline_epoch=created+1800)
    write(tmp_path/'assignment.json',ass);monkeypatch.setenv('RUNPOD_POD_ID','own')
    class Runtime(CaptureRuntime):
        def __init__(self,assets):super().__init__();instances.append(self)
        def load_base(self):
            assert self.hardware_assignment==ass;events.append('base_setup');super().load_base()
    def bind(assignment,rows):assert rows=={'fact_recall','language_plan'};events.append('row_hardware_binding')
    def gate(assignment,receipt,assets,capabilities):
        assert capabilities==['text'];events.append('hardware_gate')
        return dict(gpu_type='H200',actual_gpu_name='CPU_SYNTHETIC')
    monkeypatch.setattr(capture104,'dependencies',lambda:(old,Runtime,gate,bind,lambda x:bool(np.isfinite(x).all())))
    monkeypatch.setattr(mats_capture,'capture',lambda *args,**kwargs:{40:torch.ones((1,1,5120))})
    out=tmp_path/'capture-output'
    capture104.main(['--capture-dev40',str(inputs),'--capture-sha',digest,'--capture-out',str(out),'--assets',str(tmp_path/'assets.json'),
        '--assignment',str(tmp_path/'assignment.json'),'--source-seal',str(tmp_path/'SOURCE.json'),'--source-sha',source_sha])
    result=read(out/'OUTPUT_SEAL.json')
    assert result['status']=='COMPLETE' and result['stage']=='dev_direction40' and result['capture_once'] is True and result['profiling'] is False
    assert events==['row_hardware_binding','hardware_gate','base_setup'] and instances[0].loads==1
    assert {'capture40/CAPTURE_SEAL.json','CAPTURE_ONCE.json'}<=set(result['files'])
    assert (out/'CAPTURE_ONCE.json').read_bytes()==(inputs/'CAPTURE_ONCE.json').read_bytes()
