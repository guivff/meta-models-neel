"""CPU preflight of the exact pod archive, including its extracted capture code."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from common65 import *

POD_FILES = {str((HERE / n).relative_to(ROOT)) for n in ('common65.py', 'worker65.py', 'RUNTIME_PINS.json', 'POD_SOURCE_SEAL.json')}
POD_FILES |= {str((CACHE / 'pod_inputs' / n).relative_to(ROOT)) for n in ('BANK.json', 'INPUT_SEAL.json')}


def archive_members(archive):
    with tarfile.open(archive) as t:
        names = [m.name for m in t.getmembers()]
        require(len(names) == len(set(names)) and set(names) == POD_FILES, 'Exact archive file whitelist required')
        require(all(m.isfile() and not m.issym() and not m.islnk() for m in t.getmembers()), 'Only regular archive files allowed')
        require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names), 'Unsafe archive path')
    return names


def exact_preflight(archive):
    archive = Path(archive).resolve(); names = archive_members(archive)
    with tempfile.TemporaryDirectory(prefix='e65-exact-preflight-') as tmp:
        root = Path(tmp)
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                dest = root / m.name; dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as f: f.write(t.extractfile(m).read())
                require(sha(dest) == sha(ROOT / m.name), 'Extracted archive differs from local bound file')
        worker = root / HERE.relative_to(ROOT) / 'worker65.py'
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, str(worker), '--preflight'], cwd=root, env=env,
                                check=True, capture_output=True, text=True)
        detail = json.loads(result.stdout)
        # Import the extracted module in an isolated process and exercise its real
        # capture hook on a tiny CPU decoder with tuple outputs and ragged prompts.
        test = r'''
import sys,types
sys.path.insert(0,sys.argv[1])
import numpy as np
import torch
from worker65 import capture_batch,blocks
class Block(torch.nn.Module):
 def forward(self,h):return (h+1,)
class Toy(torch.nn.Module):
 def __init__(self):
  super().__init__();self.model=torch.nn.Module();self.model.layers=torch.nn.ModuleList([Block() for _ in range(64)]);self.visited=[]
 def forward(self,input_ids,attention_mask,**kw):
  h=input_ids.float()[:,:,None].expand(-1,-1,4).clone()
  for i,layer in enumerate(self.model.layers):self.visited.append(i);h=layer(h)[0]
  return h
model=Toy();items=[{'ids':[1,2,3],'start':1,'stop':3},{'ids':[4,5],'start':0,'stop':2}]
values=capture_batch(model,blocks(model)[44],items,'cpu',dim=4)
assert model.visited==list(range(45))
assert values[0].dtype==np.float16 and values[0].shape==(2,4)
np.testing.assert_array_equal(values[0],np.array([[47]*4,[48]*4],dtype=np.float16))
np.testing.assert_array_equal(values[1],np.array([[49]*4,[50]*4],dtype=np.float16))
assert not blocks(model)[44]._forward_hooks
print('EXTRACTED_CAPTURE_CPU_PASS')
'''
        checked = subprocess.run([sys.executable, '-c', test, str(worker.parent)], cwd=root, env=env,
                                 check=True, capture_output=True, text=True)
        require(checked.stdout.strip() == 'EXTRACTED_CAPTURE_CPU_PASS', 'Extracted CPU hook check failed')
    return {'experiment': 'E65', 'status': 'EXACT_ARCHIVE_CPU_PREFLIGHT_PASS', 'archive_sha256': sha(archive),
        'members': names, 'member_checksums_verified': True, 'extracted_entrypoint_preflight': detail,
        'extracted_capture_CPU_test': 'PASS: raw block44, tuple output, ragged prompts, slice offsets, fp16, early stop and hook cleanup',
        'labels_or_private_files_in_archive': False, 'GPU_calls': 0}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--archive', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); dump(a.out, exact_preflight(a.archive)); print('Exact archive CPU preflight PASS')
