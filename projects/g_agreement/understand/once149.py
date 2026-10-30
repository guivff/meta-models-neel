"""Pinned CPU-only dispatch. A started invocation is never automatically retried."""
import argparse, json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
from projects.g_agreement.blindspot import protocol as P


def execute(manifest):
    m=json.loads(manifest.read_text());root=P.ROOT
    lock=Path(m['lock']);lock.parent.mkdir(parents=True,exist_ok=True)
    # Claim before validation: failed validation also consumes the once-only attempt.
    with lock.open('x') as f:
        json.dump({'manifest_sha256':P.sha(manifest),'started_utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid()},f)
    receipt=lock.with_suffix('.receipt.json')
    try:
        if Path(m['out']).exists():raise ValueError('output already exists')
        for path,digest in m['pins'].items():
            if P.sha(Path(path))!=digest:raise ValueError('pin changed: '+path)
        for entry in m.get('seals',[]):P.verify(Path(entry['directory']),entry['name'])
        for entry in m.get('pulls',[]):
            pull=Path(entry)
            for line in (pull/'PULL_SUMS').read_text().splitlines():
                digest,name=line.split(None,1);file=(pull/name.lstrip('*')).resolve()
                if not file.is_relative_to(pull.resolve()) or P.sha(file)!=digest:raise ValueError('pull checksum: '+name)
        os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        if m['task']=='w12':
            from projects.g_agreement.blindspot.w12_analysis149 import analyse
            analyse(*(Path(m[k]) for k in ('bank','source','freeze','plan','out')))
        elif m['task']=='audit':
            from projects.g_agreement.understand.e24e_audit146 import audit
            audit(*(Path(m[k]) for k in ('bank','source','out')))
        elif m['task']=='e24':
            from projects.g_agreement.understand.e24_relaunch_analysis import analyse
            analyse(argparse.Namespace(bank=Path(m['bank']),plan=Path(m['plan']),labels=Path(m['labels']),out=Path(m['out']),outputs=[Path(x) for x in m['outputs']],c6_capture=None))
        else:raise ValueError('unknown task')
        P.dump(receipt,{'status':'COMPLETE','label':'§149 RUN-BY-INTEGRATOR','manifest_sha256':P.sha(manifest)})
    except BaseException as exc:
        P.dump(receipt,{'status':'STOP_OWNER_REQUIRED','error':str(exc),'retry_authorized':False,'manifest_sha256':P.sha(manifest)})
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();execute(a.manifest)
