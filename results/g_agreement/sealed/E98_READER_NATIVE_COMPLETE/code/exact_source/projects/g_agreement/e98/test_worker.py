import json
import numpy as np
import pytest
from projects.g_agreement.e98.worker import validate, Clock, capture_one, verify, sha


def test_no_labels_or_nonterminal_capture():
    item = {'id':'a'*32, 'ids':[3,4], 'read_index':1}
    validate([item], [item['id']])
    for bad in [dict(item,label=1),dict(item,read_index=0),dict(item,id='state_A')]:
        with pytest.raises(ValueError): validate([bad],[bad['id']])


def test_running_clock_retains_pilot_and_refuses_overrun(tmp_path):
    import time
    clock=Clock(tmp_path,time.time()+61)
    clock.samples=[10.0]
    assert not clock.fits(2)
    assert json.loads((tmp_path/'FORECAST.json').read_text())['forecast_seconds']==25
    assert clock.samples==[10.0]


def test_capture_last_position_and_hook_cleanup():
    import torch
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__();self.model=type('Blocks',(),{})()
            self.model.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(19)])
            self.device='cpu'
        def forward(self,input_ids,**kw):
            x=torch.arange(input_ids.shape[1]*2560).reshape(1,input_ids.shape[1],2560).float()
            for block in self.model.layers:x=block(x)
            return x
    model=Model()
    out=capture_one(model,[1,2,3],18)
    assert np.array_equal(out,np.arange(5120,7680))
    assert not model.model.layers[18]._forward_hooks


def test_seal_rejects_mutation(tmp_path):
    (tmp_path/'items.json').write_text('[]')
    (tmp_path/'seal.json').write_text(json.dumps({'files':{'items.json':sha(tmp_path/'items.json')}}))
    digest=sha(tmp_path/'seal.json')
    verify(tmp_path,'seal.json',digest)
    (tmp_path/'items.json').write_text('[1]')
    with pytest.raises(ValueError):verify(tmp_path,'seal.json',digest)


@pytest.mark.parametrize('failure_after', [0, 1])
def test_acquisition_exception_seals_failed(tmp_path, failure_after):
    # Execute the worker's actual acquisition loop and exception/finally handlers,
    # replacing only model setup with CPU fixtures.
    import ast
    import inspect
    import time
    from types import SimpleNamespace
    from projects.g_agreement.e98 import worker
    tree = ast.parse(inspect.getsource(worker.main))
    main = tree.body[0]
    guarded = next(n for n in main.body if isinstance(n, ast.Try))
    start = next(i for i, n in enumerate(guarded.body)
                 if isinstance(n, ast.Expr) and 'records' in ast.unparse(n))
    guarded.body = guarded.body[start:]
    units = [{'id': str(i)*32, 'ids': [1]} for i in range(2)]
    calls = []
    def capture(*args):
        if len(calls) == failure_after:
            raise TimeoutError('Injected acquisition failure')
        calls.append(True)
        return np.ones(2560)
    env = dict(vars(worker), a=SimpleNamespace(out=tmp_path, phase='capture',
               input_sha='input', card_sha='card'), status='FAILED', units=units,
               model=None, clock=Clock(tmp_path, time.time()+3600),
               timer=SimpleNamespace(cancel=lambda: None), capture_one=capture)
    with pytest.raises(TimeoutError):
        exec(compile(ast.fix_missing_locations(ast.Module(body=[guarded], type_ignores=[])),
                     '<actual-worker-acquisition>', 'exec'), env)
    sealed = json.loads((tmp_path/'CAPTURE_SEAL.json').read_text())
    assert sealed['status'] == 'FAILED'
    assert (tmp_path/'FAILURE.json').exists()
    assert len(list((tmp_path/'records').glob('*.npy'))) == failure_after


@pytest.mark.parametrize('defect', ['missing', 'failure', 'unsealed', 'nonfinite'])
def test_reader_rejects_incomplete_capture(tmp_path, defect):
    from projects.g_agreement.e98.worker import seal, require_capture
    item = {'id':'a'*32}
    (tmp_path/'records').mkdir()
    if defect != 'missing':
        value = np.full(2560, np.nan) if defect == 'nonfinite' else np.ones(2560)
        np.save(tmp_path/'records'/(item['id']+'.npy'), value)
    if defect == 'failure': (tmp_path/'FAILURE.json').write_text('{}')
    seal(tmp_path, 'CAPTURE_SEAL.json', status='COMPLETE', input_sha256='input')
    if defect == 'unsealed':
        p = tmp_path/'CAPTURE_SEAL.json'
        data = json.loads(p.read_text()); data['files'] = {}; p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        require_capture(tmp_path, sha(tmp_path/'CAPTURE_SEAL.json'), 'input', [item])


def test_seal_first_output_uses_earliest_record_mtime(tmp_path):
    import os
    from datetime import datetime, timezone
    from projects.g_agreement.e98.worker import seal
    (tmp_path/'records').mkdir()
    for name, epoch in [('a', 1800000020), ('b', 1800000010)]:
        path = tmp_path/'records'/(name+'.json')
        path.write_text('{}'); os.utime(path, (epoch, epoch))
    seal(tmp_path, 'OUTPUT_SEAL.json', phase='reader')
    receipt = json.loads((tmp_path/'OUTPUT_SEAL.json').read_text())
    assert receipt['first_output_utc'] == datetime.fromtimestamp(1800000010, timezone.utc).isoformat()
    assert receipt['first_output_evidence']['path'] == 'records/b.json'
    seal(tmp_path, 'CAPTURE_SEAL.json', phase='capture')
    assert json.loads((tmp_path/'CAPTURE_SEAL.json').read_text())['first_output_utc'] == 'unknown'
