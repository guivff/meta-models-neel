"""§149 E24 dispatch from fixed, integrator-verified complete shard deliveries."""
import argparse,json,os
from pathlib import Path
from datetime import datetime,timezone
from projects.g_agreement.blindspot import protocol as P


def verified_outputs(spec):
    receipt=json.loads(Path(spec['verified_receipt']).read_text())
    if receipt.get('issuer')!='integrator' or receipt.get('verified') is not True or receipt.get('experiment')!='E24' or receipt.get('plan_sha256')!=P.sha(spec['plan']):raise ValueError('integrator receipt identity')
    entries=receipt['shards'];n=len(entries)
    if not 1<=n<=8 or [e['slot'] for e in entries]!=list(range(n)):raise ValueError('all contiguous admitted slots required')
    outputs=[];admission=None
    for e in entries:
        out=Path(spec['delivery_paths'][e['slot']])
        if e['path']!=str(out) or P.sha(out/'SCORE_SEAL.json')!=e['score_seal_sha256']:raise ValueError('shard path/seal binding')
        P.verify(out,'SCORE_SEAL.json')
        adm=json.loads((out/'ADMISSION.json').read_text())
        if admission is not None and adm!=admission:raise ValueError('inconsistent admission')
        if len(adm['pods'])!=n:raise ValueError('missing admitted shard')
        admission=adm
        if json.loads((out/'FORECAST.json').read_text())['slot']!=e['slot']:raise ValueError('slot identity')
        outputs.append(out)
    return outputs


def run(spec_path,expected):
    if P.sha(spec_path)!=expected:raise ValueError('spec hash mismatch')
    spec=json.loads(spec_path.read_text());lock=Path(spec['lock']);lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'spec_sha256':expected,'label':'§149 RUN-BY-INTEGRATOR','started_utc':datetime.now(timezone.utc).isoformat()},f)
    try:
        if Path(spec['out']).exists():raise ValueError('existing analysis output')
        for n,h in spec['pins'].items():
            if P.sha(n)!=h:raise ValueError('code/input pin changed: '+n)
        outputs=verified_outputs(spec)
        os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        from .e24_relaunch_analysis import analyse
        analyse(argparse.Namespace(bank=Path(spec['bank']),plan=Path(spec['plan']),labels=Path(spec['labels']),out=Path(spec['out']),outputs=outputs,c6_capture=None))
        P.verify(Path(spec['out']),'ANALYSIS_SEAL.json')
        P.dump(lock.with_suffix('.receipt.json'),{'status':'COMPLETE','label':'§149 RUN-BY-INTEGRATOR','retry_authorized':False})
    except BaseException as exc:
        P.dump(lock.with_suffix('.receipt.json'),{'status':'STOP_OWNER_REQUIRED','reason':str(exc),'retry_authorized':False});raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--spec-sha256',required=True)
    a=p.parse_args();run(a.spec,a.spec_sha256)
