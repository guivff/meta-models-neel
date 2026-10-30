"""Independent §248 guards; never calls an original author analysis/entrypoint."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e107b_analysis.adapter import inputs as original_inputs, resolver
from . import coverage,predictors
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
E107B='f62ef3aaf4d51cba3f2319bff90a78a1179a3c086e95bae598c4a692496bae28'

def source_check():
    for name,h in core.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        if core.sha(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('committed source receipt mismatch')

def expand(value,ref):
    if isinstance(value,dict):
        if set(value)=={'ref'}:return ref(value['ref'])
        return {k:expand(v,ref) for k,v in value.items()}
    if isinstance(value,list):return [expand(v,ref) for v in value]
    return value

def main(specfile):
    source_check();s=core.read(specfile);phase=s['phase']
    if ROOT.name!='wt-wmech2' or phase not in ('A','C'):raise ValueError('canonical checkout and registered phase required')
    if s.get('owner_verified_original_joins') is not True or s.get('reviewer_source_delivered') is not True:raise ValueError('original bindings/reviewer source delivery required')
    # Dependencies are original verified seals, not merely boolean completion assertions.
    required=['E117'] if phase=='A' else ['E117','E133','E135','RQ_item_join_verification','B_probe_margin_delivery']
    for key in required:
        r=s['dependencies'][key];core.verify(r['seal'],r['sha256'])
    if phase=='A':
        base=Path(s['e107b_seal']);seal=core.verify(base,E107B)
        if 'BINDING.json' not in seal['files']:raise ValueError('original private E107b binding required')
        ceiling_packet=core.verify(s['e82_ceiling_binding_seal'],s['e82_ceiling_binding_sha256'])
        if ceiling_packet.get('experiment')!='E82' or ceiling_packet.get('status')!='COMPLETE' or ceiling_packet.get('original_199_answer_label_join_verified') is not True:
            raise ValueError('sealed original E82 ceiling custody required')
        if 'CEILING_POINTERS.json' not in ceiling_packet['files']:raise ValueError('literal original E82 pointers required')
    else:
        if s['alpha8_judgment_bank']!='E109_reference':raise ValueError('do not mix original E104 and E109-reference judgments')
        packet=core.verify(s['table_binding_seal'],s['table_binding_sha256'])
        if packet['status']!='COMPLETE' or not packet['original_84_verified']:raise ValueError('full original table binding')
    guard=ROOT.parent/f'wt-wmech/cache/g_agreement/understand/companions248/{phase}_ONCE.json'
    if guard.exists():raise FileExistsError('consumed §248 guard; no replay')
    out=Path(s['analysis'])
    if out.exists():raise FileExistsError('fresh output directory required')
    guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:json.dump({'spec_sha256':core.sha(specfile),'source_receipt':core.sha(HERE/'SOURCE_RECEIPT.json')},f)
    out.mkdir(parents=True)
    if phase=='A':
        # Reuse source decoding only, never original analyze/main/guard.
        ceiling=expand(core.read(Path(s['e82_ceiling_binding_seal']).parent/'CEILING_POINTERS.json'),resolver(ceiling_packet['source_seals']))
        result=coverage.analyze(original_inputs(core.read(base.parent/'BINDING.json')),ceiling)
    else:
        ref=resolver(packet['source_seals'])
        indexed=core.read(Path(s['table_binding_seal']).parent/'TABLE_POINTERS.json')
        result=predictors.analyze(expand(indexed,ref))
        core.write(out/'TABLE.PRIVATE.json',result.pop('PRIVATE_TABLE'))
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.PRIVATE.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',section='248 '+phase,status='COMPLETE_ONCE',source_receipt=core.sha(HERE/'SOURCE_RECEIPT.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);main(p.parse_args().spec)
