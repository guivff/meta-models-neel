"""Freeze exact clarified E96 inventory into label-free row shards."""
import argparse
import json
from pathlib import Path
import numpy as np
from .reconstructor_check import digest, write
from .prepare_smoke_inputs import verify


def prepare(inventory, capture_audit, out, receipt):
    inv=json.loads(inventory.read_text()); audit=json.loads(capture_audit.read_text())
    if audit['inventory_sha256'] != digest(inventory):raise ValueError('capture audit binding')
    selected=[r for r in inv['rows'] if not r['registered_no_AB_or_no_S']]
    excluded=[dict(bank=r['bank'],row=r['row'],status='NOT EVALUABLE',reason='no statement score') for r in inv['rows'] if r['registered_no_AB_or_no_S']]
    if len(selected)!=54 or len(excluded)!=8:raise ValueError('clarification1 row inventory')
    out.mkdir(parents=True,exist_ok=False)
    lookup={}; arrays={}; captures=[]
    for source in audit['sources']:
        root=Path(source['path']);verify(root,'CAPTURE_SEAL.json')
        if digest(root/'CAPTURE_SEAL.json')!=source['capture_seal_sha256']:raise ValueError('capture changed')
        ids=json.loads((root/'items.order.json').read_text())
        for layer in (42,44):arrays[str(root),layer]=np.load(root/f'acts{layer}.npy',mmap_mode='r',allow_pickle=False)
        for i,key in enumerate(ids):
            k=(source['bank'],key)
            if k in lookup:raise ValueError('duplicate capture ID')
            lookup[k]=(str(root),i)
        captures.append({k:v for k,v in source.items() if k!='path'})
    plan=[];loads=[0,0,0]
    for n,row in enumerate(selected):
        readers=['oracle'] if row['bank']=='E62' else ['oracle','nla']
        slot=min(range(3),key=lambda i:loads[i]);loads[slot]+=len(readers)*640
        key=f'{n:03d}';dest=out/key;dest.mkdir()
        ids=row['selected_ids'];write(dest/'ids.json',ids)
        for reader in readers:
            layer=44 if reader=='oracle' else 42
            h=np.stack([arrays[lookup[row['bank'],key][0],layer][lookup[row['bank'],key][1]] for key in ids])
            if h.shape!=(40,5120) or not np.isfinite(h).all():raise ValueError('activation contract')
            np.save(dest/f'acts{layer}.npy',h,allow_pickle=False)
        write(dest/'INPUT_SEAL.json',{'status':'FROZEN_LABEL_FREE_ROW','files':{p.name:digest(p) for p in sorted(dest.iterdir()) if p.is_file()}})
        plan.append({'key':key,'bank':row['bank'],'row':row['row'],'slot':slot,'readers':readers,'items':40,'samples_per_item':16,'input_seal_sha256':digest(dest/'INPUT_SEAL.json'),'batch_seed_offset':n*40*16})
    write(out/'PLAN.json',{'experiment':'E96','authority':'BRIEF §204 E96 clarification1,5902d5df','rows':plan,'seed':20261028,'temperature':1.0,'top_p':.95,'top_k':0,'batch':32,'seed_derivation':'20261028 + canonical row index*640 + zero-based flat sample batch start; identical across sharding/resume','oracle_max_new_tokens':128,'nla_max_new_tokens':512,'nla_stop':'</explanation>','greedy_regenerated':False,'excluded_controls':excluded,'not_evaluable_cells':[{'bank':'E62','row':r['row'],'reader':'nla','status':'NOT EVALUABLE','reason':'no sealed greedy baseline; not sampled'} for r in selected if r['bank']=='E62'],'total_samples':sum(loads),'shard_samples':loads,'aggregator_sha256':digest('projects/g_agreement/e96/aggregate.py')})
    write(out/'INPUT_SEAL.json',{'status':'E96_SAMPLING_INPUTS_FROZEN','files':{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'INPUT_SEAL.json'}})
    write(receipt,{'status':'INPUTS_FROZEN_NO_SAMPLES','authority_commit':'5902d5df','rows':54,'oracle_cells':54,'nla_cells':29,'items':2160,'samples':53120,'shard_samples':loads,'input_seal_sha256':digest(out/'INPUT_SEAL.json'),'inventory_sha256':digest(inventory),'capture_audit_sha256':digest(capture_audit),'capture_seals':captures,'excluded_controls':excluded,'nla_e62_status':'NOT EVALUABLE; no sampling; no greedy baseline generated','readout_count':0,'first_output_utc':'unknown','first_output_note':'Input preparation only; no sampling output exists.'})
    return plan


def main():
    p=argparse.ArgumentParser()
    for k in ('inventory','capture-audit','out','receipt'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prepare(a.inventory,a.capture_audit,a.out,a.receipt)
    print('Frozen:54 rows,83 reader cells,53120 samples,3 row shards; generated0')

if __name__=='__main__':main()
