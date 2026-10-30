"""Prepare one shared judge packet from integrator-verified outputs; never judge here."""
import argparse,json
from pathlib import Path
import numpy as np
from contract56 import *

def expected_native_grid(inp,slot,reader):
 plan=read(inp/'SHARDS.json');sample=read(inp/'SAMPLING.json')['native_ids'];inj=read(inp/'injection/ITEMS.json')['items']
 text={k for row in plan['rows'][str(slot)] for k in sample[row]};injection={x['id']:x for x in inj if x['row'] in plan['injection_rows'][str(slot)]}
 return {k+':'+reader+':'+str(r) for k in text|set(injection) for r in range(1)},injection

def prepare(spec):
 inp=Path(spec['inputs']);verify(inp,'INPUT_SEAL.json',spec['input_seal_sha256']);receipt=read(spec['receipt'])
 require(receipt['verified'] is True and receipt['experiment']=='E56' and set(receipt['slots'])=={'0','1','2'},'integrator receipt')
 from analysis_io import collect
 data=collect(spec,'E56')
 defs=read(inp/'ROW_DEFINITIONS.json')['rows'];injvalues=read(inp/'injection/PLAN.json')['rows'];records=[]
 for x in data['native']:
  values=defs[x['feature']]['values'] if x['kind']=='text' else injvalues[x['feature']]
  records.append((x,values))
 out=Path(spec['blind_out']);out.mkdir(parents=True,exist_ok=False);rng=np.random.default_rng(SEED);rng.shuffle(records);public=[];key=[]
 for i,(x,values) in enumerate(records):
  opaque=rng.bytes(16).hex();public.append({'id':opaque,'property':x['feature'],'values':{'A':values[0],'B':values[1]},'readout':x['text']})
  key.append({'opaque_id':opaque,'source_id':x['id'],'unit_id':x['unit_id'],'reader':x['reader'],'feature':x['feature'],'kind':x['kind'],'repeat':x['repeat'],'direction_id':x.get('direction_id'),'arm':x.get('arm')})
 dump(out/'JUDGE_PACKET.json',public);dump(Path(spec['private_key']),key)
 dump(out/'BLIND_SEAL.json',{'experiment':'E56','rubric_sha256':sha(HERE/'JUDGE_RUBRIC.md'),'input_seal_sha256':spec['input_seal_sha256'],'source_seal_sha256':spec['source_seal_sha256'],'receipt_sha256':sha(spec['receipt']),'private_key_sha256':sha(spec['private_key']),'files':{'JUDGE_PACKET.json':sha(out/'JUDGE_PACKET.json')}})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True,type=Path);a=p.parse_args();prepare(read(a.spec))
