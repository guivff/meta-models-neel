"""CPU-side download of individually sealed <=20MB capture shards over SSH.

I-2 supplies the host/path and observed capture digest privately. This is pull
only: no labels, CPU analyses or user data are uploaded. No automatic retry.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import time
from . import ops, resident


def copy_one(host, remote_root, name, target, end):
    ops.deadline(end)
    ops.require(re.fullmatch(r'[A-Za-z0-9_@.:-]+',host) and not host.startswith('-'), 'invalid SSH host')
    ops.require(re.fullmatch(r'/[A-Za-z0-9_./-]+',remote_root) and '..' not in Path(remote_root).parts, 'unsafe remote root')
    ops.require(name == 'SEAL.json' or re.fullmatch(r'[0-9]{4}\.(tar|json|CLAIM\.json)',name), 'unexpected capture member')
    result=subprocess.run(['scp','-q','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','--',
                           host+':'+remote_root.rstrip('/')+'/'+name,str(target)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=max(.01,end-time.time()))
    ops.require(result.returncode == 0, 'capture pull failed; details stay with SSH operator')
    ops.deadline(end)
    ops.require(target.stat().st_size <= resident.LIMIT, 'capture shard exceeds20MB')


def pull(host, remote_root, digest, out, end, fetch=copy_one):
    ops.deadline(end);out.mkdir(parents=True,exist_ok=False,mode=0o700)
    fetch(host,remote_root,'SEAL.json',out/'SEAL.json',end)
    seal=ops.bound(out/'SEAL.json',digest)
    epoch=dt.datetime.fromisoformat(seal['sealed_at']).timestamp()
    ops.require(end <= epoch+600 and epoch <= time.time(), 'pull may not reset paid600second CPU/GO window')
    ops.require(seal['status']=='CAPTURE_COMPLETE' and seal['n']==resident.N
                and seal['input_seal_sha256']==resident.PORT_SHA, 'registered complete capture required')
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(fetch,host,remote_root,name,ops.safe(out,name),end) for name in seal['files']]
        for job in jobs:job.result()
    ops.verify_seal(out/'SEAL.json',digest);ops.deadline(end)
    ops.write(out/'PULL_RECEIPT.json',{'status':'VERIFIED_CPU_PULL','capture_seal_sha256':digest,
              'finished_epoch':time.time(),'deadline_epoch':end,'files':len(seal['files']),
              'bytes':sum((out/name).stat().st_size for name in seal['files']), 'labels_uploaded':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True);p.add_argument('--remote-capture',required=True)
    p.add_argument('--capture-sha256',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--deadline-epoch',type=float,required=True)
    a=p.parse_args();pull(a.host,a.remote_capture,a.capture_sha256,a.out,a.deadline_epoch)


if __name__=='__main__':main()
