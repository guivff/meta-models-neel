"""Bind E50 to E36's sealed v2 bank and verified block-44 captures; CPU only."""
from pathlib import Path
import argparse
import json
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C

BANK_SEAL = '381fad8114a3dcd4a1142f9b776840d611db6c0ca10fad054a807a81c46e0b37'
BANK_HASH = '2d3b14226b76fb51b7afe83190b34fd03a2c9cb3ded6f3f867ac35cb3de10690'
CANDIDATES_HASH = '8b61f9ac7216f37cc1ae8dd422a8ab0f21c7520e5851a24c8893492f263ef273'
FREEZE_HASH = 'e6c1a2349f9dca7faead507bfc521fce8e4e47dd1bba8b317bae4c9f1c38c184'


def stage(bank, candidates, out):
    bank, candidates = Path(bank), Path(candidates)
    if C.sha(bank/'PREPARED_SEAL.json') != BANK_SEAL or C.sha(candidates) != CANDIDATES_HASH:
        raise ValueError('registered E36 frozen bank/candidates differ')
    C.verify(bank, 'PREPARED_SEAL.json')
    if C.sha(bank/'items.input.jsonl') != BANK_HASH or C.sha(bank/'FREEZE_RECEIPT.json') != FREEZE_HASH:
        raise ValueError('registered E36 item source differs')
    full = C.rows(bank/'items.input.jsonl')
    labels = C.rows(bank/'labels.DO_NOT_STAGE.jsonl')
    lookup = {r['id']: r for r in labels}
    if len(lookup) != len(labels) or set(lookup) != {r['id'] for r in full}:
        raise ValueError('E36 private labels must match exact source population')
    defs = C.read(C.HERE/'ROW_DEFINITIONS.json')['rows']
    specs = C.read(candidates)['rows']
    templates = {}
    selected = [r for r in full if r['feature'] in C.ROWS]
    for row in C.ROWS:
        spec = specs[row]
        if spec['values'] != defs[row]['values'] or len(spec['olens_descriptive']) != 2:
            raise ValueError('frozen descriptive pairs/orientation mismatch')
        if any(len(pair) != 2 or any(not isinstance(s, str) or not s for s in pair) for pair in spec['olens_descriptive']):
            raise ValueError('two nonempty ordered candidate pairs required')
        templates[row] = {'values': spec['values'], 'olens': spec['olens_descriptive']}
        clusters = {}
        for split in ('dev', 'test'):
            group = [r for r in selected if r['feature']==row and r['split']==split]
            if len(group)!=84 or len({r['id'] for r in group})!=84:
                raise ValueError('84 unique items per row/split required')
            for r in group:
                lab=lookup[r['id']]
                if any(lab[k]!=r[k] for k in ('feature','split','cluster')) or lab['value'] not in spec['values']:
                    raise ValueError('label metadata/orientation mismatch')
            if sum(lookup[r['id']]['value']==spec['values'][0] for r in group)!=42:
                raise ValueError('balanced source row required')
            clusters[split]={r['cluster'] for r in group}
        if clusters['dev'] & clusters['test']:
            raise ValueError('development and test template families overlap')
    out=C.cache_output(out)
    for split in ('dev','test'):
        part=sorted((r for r in selected if r['split']==split and (split=='test' or r['feature'] in C.STRUCTURE)), key=lambda r:(C.ROWS.index(r['feature']),r['id']))
        lab=[{'id':r['id'],'feature':r['feature'],'y':int(lookup[r['id']]['value']==templates[r['feature']]['values'][0]),'cluster':r['cluster']} for r in part]
        C.jsonl(out/(split+'.jsonl'),lab if split=='dev' else [{'id':r['id'],'feature':r['feature']} for r in part])
        if split=='test':C.jsonl(out/'test.labels.DO_NOT_STAGE.jsonl',lab)
    C.dump(out/'templates.json',templates)
    C.jsonl(out/'source.items.audit.jsonl',[{'id':r['id'],'feature':r['feature'],'split':r['split'],'source_length':len(r['ids'])} for r in selected if r['split']=='test' or r['feature'] in C.STRUCTURE])
    C.dump(out/'provenance.json',{'source_bank_seal':BANK_SEAL,'source_bank_sha256':BANK_HASH,'source_freeze_sha256':FREEZE_HASH,'source_candidates_sha256':CANDIDATES_HASH,'source_private_sha256':C.sha(bank/'labels.DO_NOT_STAGE.jsonl'),'plan_sha256':C.sha(C.HERE/'PLAN.json'),'activation_layer':44,'split':'E36 frozen v2 dev and test','test_labels_for_cpu_analysis_only':True})
    names=['dev.jsonl','test.jsonl','templates.json','source.items.audit.jsonl','provenance.json']
    C.seal(out,'STAGE_SEAL.json',names)
    C.dump(out/'PREPARATION.json',{'status':'AWAITING_VERIFIED_E36_CAPTURE','stage_seal_sha256':C.sha(out/'STAGE_SEAL.json'),'private_test_labels_sha256':C.sha(out/'test.labels.DO_NOT_STAGE.jsonl'),'items':3444,'dev':1344,'test':2100,'gpu_hours':0})
    return C.read(out/'PREPARATION.json')


def prepare(bank, capture, out, e39_input):
    import numpy as np
    bank=Path(bank)
    C.verify(bank,'STAGE_SEAL.json')
    prep=C.read(bank/'PREPARATION.json')
    if (prep['stage_seal_sha256']!=C.sha(bank/'STAGE_SEAL.json') or
        prep['private_test_labels_sha256']!=C.sha(bank/'test.labels.DO_NOT_STAGE.jsonl')):
        raise ValueError('prepared v2 metadata/key changed')
    prov=C.read(bank/'provenance.json')
    if (prov['source_bank_seal']!=BANK_SEAL or prov['source_candidates_sha256']!=CANDIDATES_HASH or
        prov['plan_sha256']!=C.sha(C.HERE/'PLAN.json')):
        raise ValueError('staged input is not registered E50 source')
    selected=C.rows(bank/'source.items.audit.jsonl');want={r['id']:r for r in selected}
    vectors={};audits={};sources=[]
    for root in map(Path,capture):
        seal=C.verify(root,'OUTPUT_SEAL.json')
        runtime=C.read(root/'runtime.json');plan=C.read(root/'plan.json')
        if (seal.get('experiment')!='E36' or runtime['status']!='COMPLETE' or
            seal['plan_sha256']!=runtime['plan_sha256'] or seal['plan_sha256']!=plan['plan_sha256']):
            raise ValueError('complete verified E36 pull required')
        if plan['freeze']['sha256']!=FREEZE_HASH or plan['candidates']['sha256']!=CANDIDATES_HASH:
            raise ValueError('capture does not bind the registered E36 source')
        order=C.read(root/'items.order.json');a=np.load(root/'acts44.npy',mmap_mode='r',allow_pickle=False)
        audit=C.read(root/'capture.audit.json');byid={x['id']:x for x in audit['items']}
        if len(order)!=len(set(order)) or a.shape!=(len(order),5120) or set(byid)!=set(order):
            raise ValueError('capture order/shape/audit mismatch')
        if 44 not in audit['blocks'] or audit['padding_side']!='right':
            raise ValueError('capture protocol mismatch')
        source={'output_seal_sha256':C.sha(root/'OUTPUT_SEAL.json'),'acts44_sha256':C.sha(root/'acts44.npy'),'order_sha256':C.sha(root/'items.order.json'),'capture_audit_sha256':C.sha(root/'capture.audit.json'),'environment_sha256':C.sha(root/'environment.json'),'plan_sha256':C.sha(root/'plan.json')}
        sources.append(source)
        for i,k in enumerate(order):
            if k not in want:continue
            if k in vectors or byid[k]['length']!=want[k]['source_length'] or byid[k]['feature']!=want[k]['feature']:
                raise ValueError('duplicate or mismatched selected capture')
            v=np.asarray(a[i],dtype=np.float32)
            if not np.isfinite(v).all() or np.linalg.norm(v)==0:raise ValueError('invalid activation')
            vectors[k]=v
            audits[k]={**byid[k],'environment_sha256':source['environment_sha256'],'output_seal_sha256':source['output_seal_sha256']}
    if set(vectors)!=set(want):raise ValueError('all 3444 selected v2 dev/test activations required; no partial launch')
    e39_input=Path(e39_input)
    C.verify(e39_input)
    if C.sha(e39_input/'INPUT_SEAL.json')!=C.plan()['e39_bound_input_seal_sha256']:
        raise ValueError('must reuse E39 exact bound v2 input')
    e39_prov=C.read(e39_input/'provenance.json')
    if sources!=e39_prov['source_capture_seals']:raise ValueError('same verified E36 captures as E39 required')
    for split in ('dev','test'):
        old=C.rows(e39_input/(split+'.jsonl'));acts=np.load(e39_input/(split+'.acts44.npy'),mmap_mode='r',allow_pickle=False)
        for i,item in enumerate(old):
            if item['id'] in want and not np.array_equal(acts[i],vectors[item['id']]):
                raise ValueError('shared E39 activation tensor differs')
    prov.update(e39_bound_input_seal_sha256=C.sha(e39_input/'INPUT_SEAL.json'),shared_e39_tensors_bit_exact=True)
    out=C.cache_output(out)
    for n in ['dev.jsonl','test.jsonl','templates.json','test.labels.DO_NOT_STAGE.jsonl']:
        shutil.copyfile(bank/n,out/n)
    for split in ('dev','test'):
        items=C.rows(out/(split+'.jsonl'))
        np.save(out/(split+'.acts44.npy'),np.stack([vectors[r['id']] for r in items]),allow_pickle=False)
    C.jsonl(out/'capture.audit.jsonl',[audits[k] for k in sorted(audits)])
    C.dump(out/'provenance.json',{**prov,'source_capture_seals':sources,'stage_seal_sha256':C.sha(bank/'STAGE_SEAL.json')})
    C.seal(out,names=['dev.jsonl','test.jsonl','templates.json','dev.acts44.npy','test.acts44.npy','capture.audit.jsonl','provenance.json'])
    C.dump(out/'PREPARATION.json',{'status':'COMPLETE','input_seal_sha256':C.sha(out/'INPUT_SEAL.json'),'private_test_labels_sha256':prep['private_test_labels_sha256'],'items':3444,'gpu_hours':0})
    return C.read(out/'PREPARATION.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',type=Path,required=True);p.add_argument('--candidates',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(stage(a.bank,a.candidates,a.out),sort_keys=True))
