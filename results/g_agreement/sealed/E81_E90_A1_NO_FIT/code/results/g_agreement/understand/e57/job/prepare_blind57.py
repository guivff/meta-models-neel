"""Same rubric as E56, opaque shuffled IDs, no reader/arm/truth to judge."""
import argparse
from pathlib import Path
import numpy as np
from runtime57 import HERE,E56
from contract56 import read,dump,sha,require,SEED
from analysis_io import collect

def prepare(spec):
    data=collect(spec,'E57');records=list(data['native']);rng=np.random.default_rng(SEED);rng.shuffle(records);public=[];key=[]
    for x in records:
        k=x['unit_id'];opaque=rng.bytes(16).hex();values=data['plan']['judge_values'][k]
        require(isinstance(values,list) and len(values)==2,'judge A/B value definition')
        public.append({'id':opaque,'property':data['plan']['rows'][x['feature']]['canonical_row'],'values':{'A':values[0],'B':values[1]},'readout':x['text']})
        key.append({'opaque_id':opaque,'source_id':x['id'],'unit_id':k})
    out=Path(spec['blind_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'JUDGE_PACKET.json',public);dump(Path(spec['private_key']),key)
    dump(out/'BLIND_SEAL.json',{'experiment':'E57','rubric_sha256':sha(E56/'JUDGE_RUBRIC.md'),'input_seal_sha256':spec['input_seal_sha256'],'source_seal_sha256':spec['source_seal_sha256'],'receipt_sha256':sha(spec['receipt']),'private_key_sha256':sha(spec['private_key']),'files':{'JUDGE_PACKET.json':sha(out/'JUDGE_PACKET.json')}})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();prepare(read(a.spec))
