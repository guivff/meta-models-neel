"""Operational §94 solo retry. Original E7 scientific collectors are unchanged."""
import argparse
import gc
import os
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from . import worker as W
from .packed import Residents,phase_args,experiment_seal
from .runtime import Gate
from .cpu import read,dump,sha,verify,seal


class SoloResidents(Residents):
    def __init__(self,a,gates):
        # Deliberately do not call packed Residents.__init__: it requires target/AR assets.
        self.a=a;self.gates=gates;self.objects={};self.loads={};self.active=None
        self.derived_inputs={};self.events=[];self.assets_sha=sha(a.assets)
        from projects.g_agreement.blindspot.run import _assets
        self.assets=_assets(a.assets,('nla',))
        self.current=None;self.completed_science=0.

    def get(self,name):
        if name not in ('decoder','nla'):raise ValueError('E7 solo may load only native42 decoder and NLA verbalizer')
        return super().get(name)


def execute(a,resident):
    W.RESIDENT=resident;g=resident.gates['E7'];resident.current=None
    root=a.out/'e7';root.mkdir(exist_ok=False);probe=a.out/'decoder-preflight';probe.mkdir(exist_ok=False)
    phases=[];status='COMPLETE';error=None
    try:
        # Decoder load/preflight and AV load finish before E7 first science, in this same process.
        decoder=resident.get('decoder')
        test=decoder.reconstruct(['The unfinished prefix (','The current position is outside parentheses.'],batch=2).numpy()
        if test.shape!=(2,5120) or not np.isfinite(test).all():raise ValueError('native42 decoder preflight failed')
        dump(probe/'report.json',{'status':'LOADED_NATIVE42','assets_sha256':sha(a.assets),'AV_loaded':False,'same_process':True,'PID':os.getpid(),'loads':resident.loads['decoder']})
        seal(probe,['report.json'],'EXPLORATORY_DECODER_LOAD_VERIFIED')
        resident.current='E7';resident.get('nla')
        # Same calls, ordering, frozen items, phrasings and six arms as packed E7.
        p=root/'readouts';phases.append(p);W.nla_readouts(phase_args(a,'E7',decoder_probe=probe,out=p))
        decode_inputs=root/'decode-inputs';W.prepare_e7_decode(SimpleNamespace(inputs=a.inputs/'e7',readouts=p,out=decode_inputs))
        if read(decode_inputs/'provenance.json')['input_seal_sha256']!=sha(a.inputs/'e7/INPUT_SEAL.json'):raise ValueError('derived E7 decoder lineage mismatch')
        resident.derived_inputs.setdefault('E7',set()).add(sha(decode_inputs/'INPUT_SEAL.json'))
        p=root/'decoder';phases.append(p);args=phase_args(a,'E7',experiment='E7',reader='nla',records='decode.input.jsonl',decoder_probe=probe,out=p);args.inputs=decode_inputs;W.reconstruct(args);resident.release('decoder')
        p=root/'scores';phases.append(p);W.score_e7(phase_args(a,'E7',decoder_probe=probe,decode_inputs=decode_inputs,reconstruction=root/'decoder',out=p));resident.release('nla')
        g.guard()
    except Exception as exc:
        status='INCOMPLETE';error=type(exc).__name__+': '+str(exc)
        if not (probe/'SCORE_SEAL.json').exists():
            dump(probe/'report.json',{'status':'DECODER_LOAD_FAILED','error_type':type(exc).__name__,'error':str(exc),'PID':os.getpid()})
            seal(probe,['report.json'],'EXPLORATORY_DECODER_LOAD_FAILED')
        gc.collect()
    finally:
        experiment_seal(root,'E7',g,status,phases,resident.events,error)
        resident.completed_science+=time.monotonic()-g.started if g.started is not None else 0
        W.RESIDENT=None
    dump(a.out/'solo.json',{'PID':os.getpid(),'order':['E7'],'checkpoint_load_counts':resident.loads,'events':resident.events,'same_process':True,'E1_E2_executed':False,'retry_authority_commit':'5eef938b6e1f29e86a60affbb4f5f237ee7eeaa8','scientific_collectors_changed':False,'status':status})
    seal(a.out,['solo.json','e7/SCORE_SEAL.json','decoder-preflight/SCORE_SEAL.json'],'EXPLORATORY_E7_SOLO_RETRY_RECEIPT')
    print('HANDOFF E7 SOLO',status,root/'SCORE_SEAL.json',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','assets','assignments','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.official=None;a.whitener=None
    gates={'E7':Gate(a.assignments/'e7.json','E7')}
    verify(a.inputs/'e7','INPUT_SEAL.json')
    if gates['E7'].assignment['input_seal_sha256']!=sha(a.inputs/'e7/INPUT_SEAL.json'):raise ValueError('solo input binding mismatch')
    a.out.mkdir(exist_ok=False,parents=True);resident=SoloResidents(a,gates)
    gates['E7'].setup_callback=resident.setup_guard
    execute(a,resident)


if __name__=='__main__':main()
