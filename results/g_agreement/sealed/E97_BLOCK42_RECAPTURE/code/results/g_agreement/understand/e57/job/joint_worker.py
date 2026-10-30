"""Sequential E56/E57 custody on the same three pods, with separate sealed outputs."""
import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
from runtime57 import HERE, E56, ExtensionBudget, acquire57, validate_plan
from worker56 import Backend, Budget, acquire
from contract56 import ROOT, read, dump, verify, require, sha


def main():
    p = argparse.ArgumentParser()
    for key in ('assignment', 'e56-inputs', 'e57-inputs', 'assets', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--e61-inputs',type=Path)
    x = p.parse_args()
    status = read(HERE / 'READINESS.json')
    require(status['launch_allowed'] is True, 'E57 input freeze/rule bindings pending; see HANDOFF.md')
    require(read(E56 / 'RULE_STATUS.json')['status'] == 'RESOLVED', 'E56 verdict-definition hold remains')
    a = read(x.assignment)
    with61=x.e61_inputs is not None and a['slot']==0
    total=6600 if with61 else 4800
    require(a['joint_cap_seconds'] == total and a['e57_cap_seconds'] == 1800, 'shared custody caps')
    if with61:
        require(a['e61_cap_seconds']==1800,'E61 cap')
        e61=HERE.parents[1]/'e61/job'
        verify(e61,'SOURCE_SEAL.json',a['e61_source_seal_sha256'])
        verify(x.e61_inputs,'INPUT_SEAL.json',a['e61_input_seal_sha256'])
    require(time.time() < a['pod_created_epoch'] + total - 60, 'joint deadline')
    verify(HERE, 'SOURCE_SEAL.json', a['e57_source_seal_sha256'])
    verify(E56, 'SOURCE_SEAL.json', a['source_seal_sha256'])
    verify(x.e56_inputs, 'INPUT_SEAL.json', a['input_seal_sha256'])
    verify(x.e57_inputs, 'INPUT_SEAL.json', a['e57_input_seal_sha256'])
    for n, h in read(HERE / 'DEPENDENCIES.json').items():
        require(sha(ROOT / n) == h, 'dependency ' + n)
    plan = read(x.e57_inputs / 'RUN_PLAN.json')
    items = read(x.e57_inputs / 'items.json')
    labels = None
    validate_plan(plan, items, labels)
    x.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(max(0, a['pod_created_epoch'] + total - time.time()), lambda: os.kill(os.getpid(), signal.SIGKILL))
    timer.daemon = True
    timer.start()
    stage_timer = None
    try:
        out56 = x.out / 'e56'
        out56.mkdir()
        dump(out56 / 'ASSIGNMENT.json', a)
        backend = Backend(ROOT, x.assets, {'gpu_type': 'H200'})
        b56 = Budget(a)
        stage_timer = threading.Timer(max(0, b56.end - time.time()), lambda: os.kill(os.getpid(), signal.SIGKILL))
        stage_timer.daemon = True
        stage_timer.start()
        acquire(read(x.e56_inputs / 'items.json'), None, x.e56_inputs, backend, b56, out56, a)
        stage_timer.cancel()
        # E56 completed its original parity on this pod. Preserve it as E57's gate receipt.
        parity = read(out56 / 'parity/PARITY_RESULT.json')
        require(parity['status'] == 'PASS', 'same-pod E36 parity')
        started = time.time()
        b57 = ExtensionBudget(started, a['pod_created_epoch'])
        stage_timer = threading.Timer(max(0, b57.end - time.time()), lambda: os.kill(os.getpid(), signal.SIGKILL))
        stage_timer.daemon = True
        stage_timer.start()
        out57 = x.out / 'e57'
        out57.mkdir()
        dump(out57 / 'ASSIGNMENT.json', dict(a, e57_started_epoch=started))
        dump(out57 / 'PARITY_REUSE.json', {'pod_id': a['pod_id'], 'e56_output_seal_sha256': sha(out56 / 'OUTPUT_SEAL.json'), 'parity_result_sha256': sha(out56 / 'parity/PARITY_RESULT.json'), 'status': 'PASS'})
        # E56 leaves NLA resident; free it before loading the Oracle reader again.
        backend.nla = None
        import gc
        import torch
        gc.collect()
        torch.cuda.empty_cache()
        acquire57(items, labels, plan, backend, b57, out57, a)
        if with61:
            stage_timer.cancel()
            sys.path.insert(0,str(e61))
            from runtime61 import acquire61,StageBudget,verify_dependencies
            verify_dependencies()
            start61=time.time();b61=StageBudget(start61,a['pod_created_epoch'])
            stage_timer=threading.Timer(max(0,b61.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));stage_timer.daemon=True;stage_timer.start()
            out61=x.out/'e61';out61.mkdir()
            dump(out61/'ASSIGNMENT.json',dict(a,e61_started_epoch=start61))
            dump(out61/'PARITY_REUSE.json',{'pod_id':a['pod_id'],'e56_output_seal_sha256':sha(out56/'OUTPUT_SEAL.json'),'parity_result_sha256':sha(out56/'parity/PARITY_RESULT.json'),'status':'PASS'})
            backend.nla=None;gc.collect();torch.cuda.empty_cache()
            acquire61(read(x.e61_inputs/'items.json'),backend,b61,out61,{'pod_id':a['pod_id'],'input_seal_sha256':a['e61_input_seal_sha256'],'source_seal_sha256':a['e61_source_seal_sha256']})
    except BaseException as error:
        dump(x.out / 'FAILURE.json', {'type': type(error).__name__, 'error': str(error)})
        raise
    finally:
        if stage_timer:
            stage_timer.cancel()
        timer.cancel()


if __name__ == '__main__':
    main()
