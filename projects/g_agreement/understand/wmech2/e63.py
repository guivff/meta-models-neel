"""Reuse W-mechanism's committed follow19 adapter; never reset its once guard."""
import argparse
import subprocess
from .core import *

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['blind','analyze']);a=p.parse_args()
    committed();s=read(HERE/'E63.json')
    for path,digest in s['source_files'].items():
        require(sha(path)==digest,'existing adapter dependency changed')
    spec=read(s['spec'])
    if a.mode=='blind' and Path(spec['blind_out']).exists():
        # Reuse the existing packet rather than reshuffling or issuing new IDs.
        z=verify(Path(spec['blind_out'])/'RESULT_SEAL.json',s['existing_blind_sha256'])
        require(z['output_seal_sha256']==s['output_sha256'],'existing E63 packet binds assigned seal')
        require(z['private_key_sha256']==sha(spec['private_key']),'existing private key binding')
        return
    subprocess.run([s['python'],s['adapter'],'--spec',s['spec'],'--mode',a.mode],check=True)

if __name__=='__main__': main()
