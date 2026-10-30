"""E21 integrator worker: only AR, loaded once with warm-up in the same process."""
import argparse
import os
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .e21 import PATHS, PLAN, BATCH, unit_plan
from .e21_runtime import Gate, NoFit
from projects.g_agreement.w_claims.ar import OFFICIAL_SHA, WHITENER_SHA


def export_whitener(ruler, out):
    """Export the verified official raw->white map for optional post-pull CPU use.

    The primary AR outputs are never transformed here. No dimension inference,
    alternative whitener, or substitute checkpoint is allowed.
    """
    import torch
    report={'status':'UNAVAILABLE', 'official_source':OFFICIAL_SHA,
            'moments_sha256':WHITENER_SHA,'ridge_c':.1,
            'formula':'(x.float32 - mu) @ w.T; official Whitener.whiten'}
    try:
        mu=ruler.mu.detach().float().cpu(); w=ruler.w.detach().float().cpu()
        if mu.shape != (5120,) or w.shape != (5120,5120) or ruler.ridge_c != .1:
            raise ValueError('official native44 transform shape/ridge mismatch')
        if not torch.isfinite(mu).all() or not torch.isfinite(w).all():
            raise ValueError('nonfinite verified transform')
        x=torch.stack([mu,mu+torch.linspace(-1,1,5120)])
        expected=(x-mu)@w.T
        if not torch.allclose(ruler.whiten(x).cpu(),expected,atol=1e-6,rtol=1e-6):
            raise ValueError('official method differs from exported transform')
        np.savez(out/'whitener.npz',mu=mu.numpy(),w=w.numpy())
        report.update(status='VERIFIED_APPLIES_CLEANLY',export_sha256=sha(out/'whitener.npz'))
    except (AttributeError,TypeError,ValueError,RuntimeError) as exc:
        report['reason']=type(exc).__name__+': '+str(exc)
    dump(out/'WHITENER.json',report)


def load(a,g):
    from projects.g_agreement.blindspot.ar_tests import _assets
    from projects.g_agreement.blindspot.run import _assets as model_assets
    from projects.g_agreement.w_claims.ar import load_reconstructor
    g.setup_guard()
    assets=model_assets(a.assets,('model',)); _assets(a.assets,('ar',))
    ar,tok,ruler=load_reconstructor(a.official,a.whitener,assets['ar'],assets['model'])
    ar.eval()
    export_whitener(ruler,a.out)
    g.setup_guard()
    return ar,tok


class Collection:
    def __init__(self,a,g,ar,tok,reconstruct=None):
        if reconstruct is None:
            from projects.g_agreement.w_claims.ar import reconstruct
        self.a,self.g,self.ar,self.tok,self.fn=a,g,ar,tok,reconstruct
        self.records=rows(a.inputs/'texts.input.jsonl')
        self.pilot=rows(a.inputs/'pilot.input.jsonl')
        self.units=read(a.inputs/'units.json'); self.pilot_units=read(a.inputs/'pilot_units.json')
        self.received={}

    def call(self,records):
        value=self.fn(self.ar,self.tok,[r['text'] for r in records])
        if hasattr(value,'numpy'): value=value.numpy()
        x=np.asarray(value,dtype=np.float32)
        if x.shape != (len(records),5120) or not np.isfinite(x).all():
            raise ValueError('finite raw block44 reconstructions required')
        return x

    def setup(self):
        for path in PATHS:
            self.g.setup_guard(); t=time.monotonic()
            self.call([self.pilot[i] for i in self.pilot_units[path][0]])
            self.g.warm(path,time.monotonic()-t)

    def run(self):
        self.g.start()
        for path in PATHS:
            for unit in self.pilot_units[path]:
                self.g.guard(); t=time.monotonic()
                self.call([self.pilot[i] for i in unit])
                self.g.record(path,time.monotonic()-t,retained=False)
        self.g.admit()
        for path in PATHS:
            folder=self.a.out/path; folder.mkdir()
            for j,unit in enumerate(self.units[path]):
                self.g.guard(); t=time.monotonic()
                x=self.call([self.records[i] for i in unit])
                np.save(folder/f'unit-{j:05d}.npy',x,allow_pickle=False)
                self.received.update(zip(unit,x))
                self.g.record(path,time.monotonic()-t,retained=True)
        if set(self.received) != set(range(len(self.records))):
            raise ValueError('incomplete reconstruction grid')
        self.g.guard()
        np.save(self.a.out/'recon.npy',np.stack([self.received[i] for i in range(len(self.records))]),allow_pickle=False)
        dump(self.a.out/'ids.json',[r['id'] for r in self.records])
        self.g.guard()


def execute(a,g,loaded=None,reconstruct=None):
    status,error,loads='COMPLETE',None,0
    try:
        if loaded is None:
            loaded=load(a,g); loads=1
        collector=Collection(a,g,*loaded,reconstruct=reconstruct)
        collector.setup(); collector.run()
    except Exception as exc:
        status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE'
        error=type(exc).__name__+': '+str(exc)
    g.status=status; g.write_state()
    dump(a.out/'run.json',{'status':status,'error':error,'experiment':'E21','PID':os.getpid(),
        'source_commit':g.assignment.get('source_commit'),'checkpoint_load_counts':{'AR':loads},
        'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'assignment_sha256':g.assignment_sha256,
        'first_science_epoch':g.first_science_epoch,'science_seconds':g.elapsed(),
        'raw_space':'block44; no whitening applied','generation_calls':0,'probe_fits_on_pod':0,
        'science_clock_resets':0})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E21_'+status)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','assets','assignment','official','whitener','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); verify(a.inputs,'INPUT_SEAL.json')
    records=rows(a.inputs/'texts.input.jsonl'); plans=read(a.inputs/'units.json')
    plan=read(ROOT/PLAN)
    if plans != unit_plan(records) or len({r['id'] for r in records}) != len(records):
        raise ValueError('frozen canonical once-only unit grid required')
    if len(read(a.inputs/'test_ids.json')) != 2100 or len(read(a.inputs/'dev_ids.json')) != 2100:
        raise ValueError('all25 rows/2100 dev/2100 test required')
    if sha(a.inputs/'INPUT_SEAL.json') != plan['input_seal_sha256']:
        raise ValueError('plan input seal mismatch')
    g=Gate(a.assignment,{p:len(plans[p]) for p in PATHS})
    if g.assignment.get('assets_sha256') != sha(a.assets) or g.assignment.get('input_seal_sha256') != sha(a.inputs/'INPUT_SEAL.json'):
        raise ValueError('assignment assets/input mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):
        raise ValueError('private label bank cannot be staged on worker')
    a.out.mkdir(parents=True,exist_ok=False); g.out=a.out; g.write_state()
    status=execute(a,g); print('HANDOFF E21',status,a.out/'SCORE_SEAL.json')
    if status != 'COMPLETE': raise SystemExit(2)


if __name__ == '__main__': main()
