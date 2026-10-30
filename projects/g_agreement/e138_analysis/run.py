"""New fixed E138 guard; original E100/E127 author entrypoints never called."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e107b_analysis.adapter import resolver
from .analysis import analyze
from .role_codes import normalize
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e138/ANALYSIS_ONCE.json'

def expand(value,ref):
    if isinstance(value,dict):
        if set(value)=={'ref'}:return ref(value['ref'])
        if set(value)=={'e104_role_code'}:
            cell=value['e104_role_code']
            core.require(set(cell)=={'code','status','judgment_id','value_roles'} and all(type(v)is dict and set(v)=={'ref'} for v in cell.values()),'all role transport fields must be sealed original refs')
            return normalize(**{k:expand(v,ref)for k,v in cell.items()})
        return {k:expand(v,ref) for k,v in value.items()}
    if isinstance(value,list):return [expand(v,ref) for v in value]
    return value

def admission(packet):
    core.require(packet.get('experiment')=='E138' and packet.get('status')=='COMPLETE','terminal E138 source binding')
    for flag in ('original84_verified','donor_pairing_E100_verified','random_E76_verified','clean_E127_no_prefix_verified','literal_value_code_mapping_verified','route_verified','privacy_verified','terminal_dispositions_verified'):
        core.require(packet.get(flag) is True,'owner binding: '+flag)
    core.require('RECORD_POINTERS.json' in packet['files'],'sealed literal source pointer table')
    core.require(packet.get('unknown_cost_requests')==0 and 0<=packet['booked_usd']<=packet['cap_usd']==1,'terminal original USD1 bank')
    for name in ('E104_inventory','E127_clean','E100_pairing','E76_random'):
        r=packet['original_sources'][name];core.verify(r['seal'],r['sha256'])

def main(specfile):
    core.require(ROOT.name=='wt-wmech2','canonical source checkout required')
    for name,digest in core.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        core.require(core.sha(ROOT/name)==digest and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()==digest,'committed tested source required')
    s=core.read(specfile)
    core.require(s.get('reviewer_source_delivered') is True,'R5 prospective source delivery')
    packet=core.verify(s['binding_seal'],s['binding_sha256']);admission(packet)
    if GUARD.exists():raise FileExistsError('E138 consumed; NEVER REPLAY')
    out=Path(s['analysis'])
    core.require(not out.exists(),'fresh output directory')
    GUARD.parent.mkdir(parents=True,exist_ok=True)
    with GUARD.open('x') as f:json.dump(dict(spec_sha256=core.sha(specfile),source_receipt=core.sha(HERE/'SOURCE_RECEIPT.json')),f)
    out.mkdir(parents=True)
    refs=resolver(packet['source_seals'])
    rows=expand(core.read(Path(s['binding_seal']).parent/'RECORD_POINTERS.json'),refs)
    result=analyze(rows)
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.PRIVATE.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E138',status='COMPLETE_ONCE',source_receipt=core.sha(HERE/'SOURCE_RECEIPT.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);main(p.parse_args().spec)
