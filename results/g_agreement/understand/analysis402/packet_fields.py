"""94a770cc(a): lossless public-field adapter; renderer belongs to W-internals."""
import argparse,json
from pathlib import Path
from custody import read,dump,verify,sha,seal,require

def fields(record):
 require(set(record)=={'id','property','values','readout'},'frozen value-packet schema')
 require(set(record['values'])=={'A','B'},'both frozen values required')
 require(all(isinstance(v,str) for v in (record['id'],record['property'],record['readout'],record['values']['A'],record['values']['B'])),'verbatim string fields')
 return {'id':record['id'],'property':record['property'],'value_A':record['values']['A'],'value_B':record['values']['B'],'readout':record['readout']}

def convert(blind,out):
 s=verify(blind,'BLIND_SEAL.json');require('JUDGE_PACKET.json' in s['files'],'sealed value packet');records=[fields(x) for x in read(blind/'JUDGE_PACKET.json')];require(len({x['id'] for x in records})==len(records),'unique opaque IDs');out.mkdir(parents=True,exist_ok=False);dump(out/'RUBRIC_FIELDS.json',records)
 seal(out,'RUBRIC_FIELDS_SEAL.json',{'authority':'94a770cc(a)','blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),'source_packet_sha256':sha(blind/'JUDGE_PACKET.json'),'field_order':['property','value_A','value_B'],'rendering':'frozen E56 rubric; property then value_A then value_B, verbatim, always A before B','records':len(records),'S6':'EVAL_PACKET remains separate; not converted to value rubric'})
 return records
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--blind',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();convert(a.blind,a.out)
