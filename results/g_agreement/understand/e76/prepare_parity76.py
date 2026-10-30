"""CPU-only split of the original parity packet; labels/reference never enter pod data."""
import os,shutil
import numpy as np
from common76 import *
from parity76 import ORIGINAL_SEAL,ROWS,load_parity


def prepare(source):
    source=Path(source);require(sha(source/'INPUT_SEAL.json')==ORIGINAL_SEAL,'Exact original W1 parity packet required')
    seal=read(source/'INPUT_SEAL.json');verify(source,seal)
    require(set(seal['files'])=={'items.jsonl','acts44.npy','templates.json','labels.json','REFERENCE.json'},'Exact original parity manifest')
    pod=CACHE/'parity_inputs';cpu=CACHE/'parity_cpu';pod.mkdir();cpu.mkdir(mode=0o700)
    for name in ('items.jsonl','acts44.npy'):shutil.copyfile(source/name,pod/name)
    original=read(source/'templates.json');dump(pod/'templates.json',{row:{'olens':original[row]['olens']} for row in ROWS})
    dump(pod/'INPUT_SEAL.json',{'experiment':'E76_PARITY','original_input_seal_sha256':ORIGINAL_SEAL,
        'files':{n:sha(pod/n) for n in ('items.jsonl','acts44.npy','templates.json')}})
    load_parity(pod,sha(pod/'INPUT_SEAL.json'))
    key={'experiment':'E76_PARITY','CPU_only':True,'pod_staging_forbidden':True,'original_input_seal_sha256':ORIGINAL_SEAL,
        'original_files_sha256':seal['files'],'labels':read(source/'labels.json'),'reference':read(source/'REFERENCE.json'),
        'parity_input_seal_sha256':sha(pod/'INPUT_SEAL.json'),'items':[json.loads(x) for x in (pod/'items.jsonl').read_text().splitlines()]}
    fd=os.open(cpu/'KEY.PRIVATE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(json.dumps(key,sort_keys=True,indent=2)+'\n')
    dump(HERE/'PARITY_BINDING.20261027.json',{'experiment':'E76_PARITY','original_input_seal_sha256':ORIGINAL_SEAL,
        'original_source':str(source),'blind_input_seal_sha256':sha(pod/'INPUT_SEAL.json'),
        'CPU_only_key':str((cpu/'KEY.PRIVATE.json').relative_to(ROOT)),'CPU_only_key_sha256':sha(cpu/'KEY.PRIVATE.json'),
        'pod_files':['items.jsonl','acts44.npy','templates.json','INPUT_SEAL.json'],'labels_or_reference_in_pod_export':False})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args();prepare(a.source)
