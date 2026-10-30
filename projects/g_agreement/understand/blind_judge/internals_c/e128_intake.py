"""TrackQ all672 sealed lower-dose Oracle IDs, unchanged original E104 rubric."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from .e128_channel import RUBRIC_SHA
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records,identities,original,pointers,items,labels,rubric):
    old={x['item_id']:(i,x) for i,x in enumerate(original) if x['arm']=='U' and x['row']=='fact_recall' and x['reader']=='oracle' and x['condition']=='steered' and x['flipped'] is True}
    ids={x['readout_id']:x for x in identities if x.get('reader')=='oracle'};ptr={x['id']:x for x in pointers};pub={x['id']:x for x in items};lab={x['original_base_id']:x for x in labels}
    require(len(old)==len(lab)==84 and len(ptr)==len(pub)==336 and set(ptr)==set(pub),'same sealed84 originals/full336 input cells')
    require(len(ids)==len(records)==672 and len({r['id'] for _,r in records})==672,'all672 including registered random controls')
    units=[];joins=[];seen=set()
    for ref,r in records:
        require(r['id'] in ids and r['item_id'] in ptr,'explicit sealed native/TrackQ/input identity')
        q=ids[r['id']];p=ptr[r['item_id']];x=pub[r['item_id']];i,o=old[p['original_base_id']];l=lab[p['original_base_id']]
        require(q['item_id']==p['original_base_id'] and q['condition']==r['condition']==x['condition'] and q['dose']==r['alpha']==x['alpha'] and q['layer']==r['source_layer'] and r['base_id']==x['base_id'] and r['reader']=='oracle' and x['row']=='fact_recall','original IDs, dose, condition and layer; no order-derived joins')
        require(r['alpha'] in (2,4) and r['condition'] in ('steered','random') and r['source_layer'] in (44,52),'lower doses and registered layers only')
        require(p['scale']==(.25 if r['alpha']==2 else .5),'literal sealed lower-dose source scale')
        target=o['target'];other='B' if target=='A' else 'A'
        require(l['new_value'] in o['values'][target] and l['old_value'] in o['values'][other],'original candidate orientation unchanged')
        key=q['item_id'],r['alpha'],r['condition'],r['source_layer'];require(key not in seen,'unique original cell');seen.add(key)
        uid=opaque('E128',r['id']);units.append(dict(id=uid,kind='original104',rubric=rubric,data=dict(id=uid,property=o['property'],values=o['values'],readout=r['text'])))
        joins.append(dict(id=uid,readout_id=r['id'],item_id=q['item_id'],condition=q['condition'],dose=q['dose'],layer=q['layer'],original_private_index=i,source_ref=ref,old_letter=other,new_letter=target))
    require(seen=={(i,a,c,b) for i in old for a in (2,4) for c in ('steered','random') for b in (44,52)},'complete approved paired control grid, no alpha8 calls')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def prepare():
    for n,h in read(HERE/'E128_INTAKE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published E128 intake/owner source')
    qroot=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e128/binding_v1');qp=qroot/'READOUTS_TO_JUDGE.json';require(sha(qp)=='b98bfc360a189844fe993cc474601052e15a368c6065f9dd628a3f53179dd922','actual TrackQ672 readout list')
    q=read(qp);native=Path(q['source_output_seal']);ns=verify(native,'1c1618581235c5db5bcacbec1bcf408e44ebcb805d567a3aebb88406454e34a4');require(ns['status']=='COMPLETE' and ns['experiment']=='E128' and q['n']==672 and q['n_steered']==q['n_random']==336 and q['rubric_sha256']==RUBRIC_SHA,'whole measured source/approved full672 roster')
    ident=qroot/'identity/IDENTITIES.PRIVATE.json';require(sha(ident)=='99f2ed20425c31b1811de2038eb6eb7df51f8aa15b1b56391677da97a30b5102','sealed TrackQ original identities')
    inv=qroot/'inventory/INVENTORY_SEAL.json';verify(inv,'9e8ef8d9e8ef36ff8d6d7da9cc1d2f9cb4e245341a0829ae6d6269345126884d')
    pointer=ROOT.parent/'outputs/e128-inputs-v1/cpu_only/POINTER_SEAL.json';verify(pointer,'b580ae5a0acf1a96733d8b489b20b1bf3fbae19d926381cad28443687d975f99')
    inp=ROOT.parent/'outputs/e128-inputs-v1/inputs/INPUT_SEAL.json';verify(inp,'7e911f6591fb229474b132361b6e67f1696634d0001a3dd4e57823e87194b224');require(ns['input_sha256']==sha(inp),'same original lower-dose input')
    label=ROOT.parent/'outputs/e127-inputs-v2/cpu_only/LABEL_SEAL.json';verify(label,'549fa110f6f0f0276dda18b428b26de9c921e9fd97bced195f754a017ebe99c0')
    old=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E104';ps=old/'PRIVATE_SEAL.json';verify(ps,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6')
    blind=old/'blind/BLIND_SEAL.json';verify(blind,'1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d');rubric=old/'blind/RUBRIC.md';require(sha(rubric)==RUBRIC_SHA,'unchanged original E104/E109 rubric')
    records=[];cache={}
    for ref in q['readouts']:
        m=ref['member'];require(m in ns['files'],'whole sealed native member')
        if m not in cache:cache[m]=read(native.parent/m)
        r=cache[m][ref['index']];require(r['id']==ref['readout_id'] and r['alpha']==ref['dose'] and r['condition']==ref['condition'],'explicit source index and ID/condition/dose')
        records.append((dict(seal=str(native),sha256=sha(native),member=m,keys=[ref['index'],'text']),r))
    all_native=[r for m in ns['files'] if m.startswith('jobs/') and m.endswith('.json') for r in read(native.parent/m) if r.get('reader')=='oracle'];require(len(all_native)==672 and {r['id'] for r in all_native}=={r['id'] for _,r in records},'entire original native grid, no partial stitching')
    units,joins=make_units(records,read(ident),read(old/'PRIVATE.json'),read(pointer.parent/'ORIGINAL_POINTERS.PRIVATE.json'),read(inp.parent/'items.json'),read(label.parent/'LABELS.PRIVATE.json'),rubric.read_text())
    copies,audit=redact([u['data'] for u in units],'E128',addresses=True);by={x['id']:x for x in copies};affected={x['id'] for x in audit['affected']};evidence={u['id']:u['data']['readout'] for u in units if u['id'] in affected};units=[dict(u,data=by[u['id']]) for u in units]
    d=CACHE/'E128/original104_units';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'UNIT_SEAL.json').exists():verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable672 units');return d
    members=[('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',evidence),('TRACKQ_READOUT_LIST.PRIVATE.json',q),('TRACKQ_IDENTITIES.PRIVATE.json',read(ident))]
    for n,v in members:write(d/n,v)
    write(d/'CUSTODY.json',dict(issuer='W-internals-C',experiment='E128',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_candidates_unchanged=True,original_E104_rubric_sha256=RUBRIC_SHA,native_oracle44_52_only=True,only_lower_doses_2_4=True,approved_all672_random_controls=True,alpha8_rejudged=False,source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (native,inp,pointer,label,ps,blind,inv)]))
    write(d/'UNIT_SEAL.json',dict(experiment='E128',n=672,files={n:sha(d/n) for n in [x[0] for x in members]+['CUSTODY.json']}))
    write(d/'PREPARE_SPEC.json',dict(bank='E128',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name='original104'))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E128672 unitseal '+sha(prepare()/'UNIT_SEAL.json'))
