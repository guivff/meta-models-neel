"""E26 integrator worker: only AR, loaded once with warm-up in the same process."""
import argparse
import os
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .e26 import PATHS, PLAN, BATCH, unit_plan, validate_inputs
from .e26_runtime import Gate, NoFit
from projects.g_agreement.w_claims.ar import OFFICIAL_SHA, WHITENER_SHA


def load(a,g):
    from projects.g_agreement.blindspot.ar_tests import _assets
    from projects.g_agreement.blindspot.run import _assets as model_assets
    from projects.g_agreement.w_claims.ar import load_reconstructor
    g.setup_guard()
    assets=model_assets(a.assets,('model',)); _assets(a.assets,('ar',))
    ar,tok,ruler=load_reconstructor(a.official,a.whitener,assets['ar'],assets['model'])
    ar.eval()
    if 44 not in ar.layers: raise ValueError('native tag44 required')
    g.setup_guard()
    return ar,tok


class Collection:
    def __init__(self,a,g,ar,tok,reconstruct=None):
        if reconstruct is None:
            from projects.g_agreement.w_claims.ar import reconstruct
        self.a,self.g,self.ar,self.tok,self.fn=a,g,ar,tok,reconstruct
        self.input_sha = sha(a.inputs/'INPUT_SEAL.json')
        self.records=validate_inputs(a.inputs, self.input_sha)
        self.pilot=rows(a.inputs/'pilot.input.jsonl')
        self.units=read(a.inputs/'units.json'); self.pilot_units=read(a.inputs/'pilot_units.json')
        self.received={}

    def call(self,records):
        validate_inputs(self.a.inputs, self.input_sha)
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
        validate_inputs(a.inputs, g.assignment['input_seal_sha256'])
        if loaded is None:
            loaded=load(a,g); loads=1
        collector=Collection(a,g,*loaded,reconstruct=reconstruct)
        collector.setup(); collector.run()
    except Exception as exc:
        status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE'
        error=type(exc).__name__+': '+str(exc)
    g.status=status; g.write_state()
    dump(a.out/'run.json',{'status':status,'error':error,'experiment':'E26','PID':os.getpid(),
        'source_commit':g.assignment.get('source_commit'),'source_files':g.assignment['source_files'],'checkpoint_load_counts':{'AR':loads},
        'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'assignment_sha256':g.assignment_sha256,
        'first_science_epoch':g.first_science_epoch,'science_seconds':g.elapsed(),
        'raw_space':'block44; no whitening applied',
        'candidate_banks_sha256':sha(a.inputs/'BANKS.json'),
        'authority_commit':'4384b1ad','generation_calls':0,'probe_fits_on_pod':0,
        'science_clock_resets':0})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E26_'+status)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','assets','assignment','official','whitener','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); verify(a.inputs,'INPUT_SEAL.json')
    plan=read(ROOT/PLAN)
    records=validate_inputs(a.inputs, plan['input_seal_sha256'])
    plans=read(a.inputs/'units.json')
    g=Gate(a.assignment,{p:len(plans[p]) for p in PATHS})
    if g.assignment.get('assets_sha256') != sha(a.assets) or g.assignment.get('input_seal_sha256') != sha(a.inputs/'INPUT_SEAL.json'):
        raise ValueError('assignment assets/input mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):
        raise ValueError('private label bank cannot be staged on worker')
    a.out.mkdir(parents=True,exist_ok=False); g.out=a.out; g.write_state()
    status=execute(a,g); print('HANDOFF E26',status,a.out/'SCORE_SEAL.json')
    if status != 'COMPLETE': raise SystemExit(2)


if __name__ == '__main__': main()
