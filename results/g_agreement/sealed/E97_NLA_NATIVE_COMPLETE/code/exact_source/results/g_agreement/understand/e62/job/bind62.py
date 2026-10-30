"""Bind a frozen bank; fail on missing token boundaries instead of inferring them."""
import argparse,shutil,tarfile
from pathlib import Path
from runtime62 import *

def validate_full_grid(items):
 validate_items(items)
 require(len(items)==4620 and all(x["split"]=="test" for x in items if x["state"]=="S6"),"registered full grid, no extra eval dev items")
 for state in ('S1','S2','S3','S4','S5','S6'):
  splits=('test',) if state=='S6' else ('dev','test')
  for split in splits:
   groups=[]
   for rung in range(5):
    xs=[x for x in items if x['state']==state and x['split']==split and x['rung']==('C' if state=='S6' else 'L')+str(rung)]
    require(len(xs)==84 and len({x['base_item_id'] for x in xs})==84,'84 unique base items per cell/split');groups.append({x['base_item_id'] for x in xs})
   require(all(g==groups[0] for g in groups),'same base items across ladder')

def main():
 p=argparse.ArgumentParser()
 for k in ('bank','out','parity'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--bank-seal-sha256',required=True);a=p.parse_args();verify(a.bank,'BANK_SEAL.json',a.bank_seal_sha256)
 # W-text must provide these exact frozen token/boundary fields in its freeze; schema mismatches hold binding.
 src=a.bank/'items.PRIVATE.json';items=read(src)
 public=[{k:v for k,v in x.items() if k not in ('label','value')} for x in items];validate_full_grid(public)
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'items.json',public);shutil.copytree(a.parity,a.out/'parity')
 seal(a.out,'INPUT_SEAL.json',{'experiment':'E62','bank_seal_sha256':a.bank_seal_sha256,'private_items_sha256':sha(src),'first_content_and_read_indices':'frozen bank fields','readouts_per_test_item':1})
 archive=a.out.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as t:t.add(a.out,arcname='inputs')
 dump(a.out.parent/'INPUT_BINDING.json',{'inputs':str(a.out),'input_seal_sha256':sha(a.out/'INPUT_SEAL.json'),'input_archive':{'path':str(archive),'sha256':sha(archive)},'private_items':str(src),'private_items_sha256':sha(src),'bank_seal_sha256':a.bank_seal_sha256})
if __name__=='__main__':main()
