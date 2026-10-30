"""Original134 E104/E109 items, unhooked44/52 -> frozen original value judge."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from .e123_channel import RUBRIC_SHA
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records,original,pointers,items,rubric):
    old={x['item_id']:(i,x) for i,x in enumerate(original) if x['arm']=='U' and x['row'] in ('fact_recall','language_plan') and x['reader']=='oracle' and x['condition']=='steered' and x['flipped'] is True}
    require(len(old)==134 and sum(o['row']=='fact_recall' for i,o in old.values())==84,'original84/50 E104 flipped cohort unchanged')
    src={x['id']:x for x in pointers};pub={x['id']:x for x in items}
    require(len(src)==len(pub)==134 and {x['base_id'] for x in pointers}==set(old) and set(src)==set(pub),'exact original input/cohort crosswalk')
    require(len(records)==len({r['id'] for _,r in records})==268,'full268 unique unhooked readouts')
    units=[];joins=[];seen=set()
    for ref,r in records:
        require(r['item_id'] in src and r['reader']=='oracle' and r['condition']=='unhooked' and r['source_layer'] in (44,52),'registered unhooked Oracle cells only')
        meta=src[r['item_id']];i,o=old[meta['base_id']]
        require(meta['condition']=='unhooked' and meta['split']=='test' and meta['row']==o['row'] and r['source_vector_index']==pub[r['item_id']]['vector_index'],'exact original capture-vector and source-item identity')
        key=meta['base_id'],r['source_layer'];require(key not in seen,'one original item/block');seen.add(key)
        uid=opaque('E123',r['id']);units.append(dict(id=uid,kind='original104',rubric=rubric,data=dict(id=uid,property=o['property'],values=o['values'],readout=r['text'])))
        joins.append(dict(id=uid,readout_id=r['id'],item_id=meta['base_id'],condition='unhooked',row=o['row'],layer=r['source_layer'],original_private_index=i,source_ref=ref,old_letter='B' if o['target']=='A' else 'A',new_letter=o['target'],public_vector_index=r['source_vector_index'],original_row_vector_index=meta['original_vector_index']))
    require(seen=={(i,b) for i in old for b in (44,52)},'complete original134 x44/52')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def prepare():
    for n,h in read(HERE/'E123_INTAKE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published original source/tested adapter')
    native=ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E123/measured_a2/out/OUTPUT_SEAL.json';ns=verify(native,'bbb1a5727e8abcea8c75b7fd01329e6185960770f22c704e6f234a8a997faa1a');require(ns['status']=='COMPLETE' and ns['experiment']=='E123','complete measured_a2 only, no NOFIT prod')
    inp=ROOT.parent/'outputs/e123-inputs-v1/inputs/INPUT_SEAL.json';verify(inp,ns['input_sha256'])
    ptr=ROOT.parent/'outputs/e123-inputs-v1/cpu_only/ORIGINAL_POINTERS.PRIVATE.json';require(sha(ptr)=='99472971752d1b508afc2102b6e1cce6ead712c830eff64a6f9eccd1595491b0','original pre-output CPU pointer bytes')
    old=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E104';ps=old/'PRIVATE_SEAL.json';verify(ps,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6')
    blind=old/'blind/BLIND_SEAL.json';verify(blind,'1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d');rubric=old/'blind/RUBRIC.md';require(sha(rubric)==RUBRIC_SHA,'originalE104/E109 rubric03d')
    config=read(ROOT/'projects/g_agreement/e123/unhooked.json');original_capture=Path(config['source_output']['seal']);verify(original_capture,config['source_output']['sha256'])
    order=read(original_capture.parent/'ARRAY_ORDER.json');require(sha(original_capture.parent/'ARRAY_ORDER.json')==config['source_output']['order_sha256'],'original row array order')
    require(all(x['base_id']==order[x['row']]['test'][x['original_vector_index']] for x in read(ptr)),'original per-row vector identity distinct from compact public indices')
    proof=CACHE/'E123/VECTOR_SOURCE_CHECK.PRIVATE.json';check=read(proof);require(check['exact_vector_bytes_verified'] is True and check['input_sha256']==sha(inp) and check['original_output_sha256']==sha(original_capture),'exact compact-to-original vector copy proof')
    records=[]
    for m in ns['files']:
        if m.startswith('jobs/') and m.endswith('.json'):
            records.extend((dict(seal=str(native),sha256=sha(native),member=m,keys=[i,'text']),r) for i,r in enumerate(read(native.parent/m)) if r.get('reader')=='oracle')
    units,joins=make_units(records,read(old/'PRIVATE.json'),read(ptr),read(inp.parent/'items.json'),rubric.read_text())
    copies,audit=redact([u['data'] for u in units],'E123',addresses=True);by={x['id']:x for x in copies};affected={x['id'] for x in audit['affected']};evidence={u['id']:u['data']['readout'] for u in units if u['id'] in affected};units=[dict(u,data=by[u['id']]) for u in units]
    d=CACHE/'E123/original104_units';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'UNIT_SEAL.json').exists():verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable268 source');return d
    for n,v in [('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',evidence),('ORIGINAL_POINTERS.PRIVATE.json',read(ptr)),('VECTOR_SOURCE_CHECK.PRIVATE.json',check)]:write(d/n,v)
    write(d/'CUSTODY.json',dict(issuer='W-internals-C',experiment='E123',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_candidates_unchanged=True,original_E104_rubric_sha256=RUBRIC_SHA,native_unhooked_oracle44_52_only=True,source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (native,inp,ps,blind,original_capture)]))
    write(d/'UNIT_SEAL.json',dict(experiment='E123',n=268,files={n:sha(d/n) for n in ('UNITS.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json','ORIGINAL_EVIDENCE.PRIVATE.json','ORIGINAL_POINTERS.PRIVATE.json','VECTOR_SOURCE_CHECK.PRIVATE.json','CUSTODY.json')}))
    write(d/'PREPARE_SPEC.json',dict(bank='E123',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name='original104'))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E123 full268 unitseal '+sha(prepare()/'UNIT_SEAL.json'))
