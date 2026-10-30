"""Track-Q full756 original E127 readout list -> exact E104 blind judge units."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from .e127_channel import RUBRIC_SHA
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records,identities,original,labels,rubric):
    old={x['item_id']:(i,x) for i,x in enumerate(original) if x['arm']=='U' and x['row']=='fact_recall' and x['reader']=='oracle' and x['condition']=='steered' and x['flipped'] is True}
    lab={x['base_id']:x for x in labels};ids={x['readout_id']:x for x in identities if x.get('reader')=='oracle'}
    require(len(old)==len(lab)==84 and len(ids)==len(records)==756 and len({r['id'] for _,r in records})==756,'full original84/3conditions/3blocks')
    units=[];joins=[];seen=set()
    for ref,r in records:
        require(r['id'] in ids and r['base_id'] in lab,'explicit original native/readout identity')
        q=ids[r['id']];l=lab[r['base_id']];i,o=old[l['original_base_id']]
        condition='no_prefix' if r['condition']=='none' else r['condition']
        require(q['item_id']==l['original_base_id'] and q['condition']==condition and q['layer']==r['source_layer'] and r['reader']=='oracle' and r['item_id']==l['condition_ids'][r['condition']],'native/input/TrackQ exact ID identity, no order join')
        require(q['layer'] in (44,52,60) and condition in ('context_update','neutral_prefix','no_prefix'),'registered conditions/blocks')
        key=q['item_id'],condition,q['layer'];require(key not in seen,'one original cell');seen.add(key)
        target=o['target'];other='B' if target=='A' else 'A'
        require(l['new_value'] in o['values'][target] and l['old_value'] in o['values'][other],'unchanged original old/new candidates/letters')
        uid=opaque('E127',r['id']);units.append(dict(id=uid,kind='original104',rubric=rubric,data=dict(id=uid,property=o['property'],values=o['values'],readout=r['text'])))
        joins.append(dict(id=uid,readout_id=r['id'],item_id=q['item_id'],condition=condition,layer=q['layer'],original_private_index=i,source_ref=ref,old_letter=other,new_letter=target))
    require(seen=={(i,c,b) for i in old for c in ('context_update','neutral_prefix','no_prefix') for b in (44,52,60)},'complete registered cartesian scope')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def prepare():
    for n,h in read(HERE/'E127_INTAKE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published tested intake/owner scientific source')
    qroot=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e127/binding_v1');qp=qroot/'READOUTS_TO_JUDGE.json';require(sha(qp)=='f1c1bd70abbcdc5301e6ff391770c99bd239f20787f4413d98ee7c50b19716a1','TrackQ193676c32 exact756list')
    q=read(qp);native=Path(q['source_output_seal']);ns=verify(native,'a30e638090bbd6b8a90f98153c5a153363f05b06d62672c4a42304a13f914d78');require(ns['status']=='COMPLETE' and ns['experiment']=='E127' and q['n']==756 and q['rubric_sha256']==RUBRIC_SHA,'whole final native+originalrubric')
    ident=qroot/'identity/IDENTITIES.PRIVATE.json';require(sha(ident)=='68672a77904d8b742833a045ddd414f2748b7704577aa5abeb2e50d498755b09','TrackQ explicit identities frozen')
    inv=qroot/'inventory/INVENTORY_SEAL.json';verify(inv,'8a5b9aafff24ccb7ad1f019d81ff2de73798983f7ef341855b5dac5bdf4f8b74')
    label=ROOT.parent/'outputs/e127-inputs-v2/cpu_only/LABEL_SEAL.json';verify(label,'549fa110f6f0f0276dda18b428b26de9c921e9fd97bced195f754a017ebe99c0')
    inp=ROOT.parent/'outputs/e127-inputs-v2/inputs/INPUT_SEAL.json';verify(inp,ns['input_sha256'])
    old=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E104';ps=old/'PRIVATE_SEAL.json';verify(ps,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6')
    blind=old/'blind/BLIND_SEAL.json';verify(blind,'1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d');rubric=old/'blind/RUBRIC.md';require(sha(rubric)==RUBRIC_SHA,'exact E104/E109 rubric03d')
    records=[];cache={}
    for x in q['readouts']:
        m=x['member'];require(m in ns['files'],'original sealed native member')
        if m not in cache:cache[m]=read(native.parent/m)
        r=cache[m][x['index']];require(r['id']==x['readout_id'],'explicit source index and ID agreement')
        records.append((dict(seal=str(native),sha256=sha(native),member=m,keys=[x['index'],'text']),r))
    all_native=[r for m in ns['files'] if m.startswith('jobs/') and m.endswith('.json') for r in read(native.parent/m) if r.get('reader')=='oracle']
    require(len(all_native)==756 and {r['id'] for r in all_native}=={r['id'] for _,r in records},'entire sealed Oracle grid, not a partial-source subset')
    units,joins=make_units(records,read(ident),read(old/'PRIVATE.json'),read(label.parent/'LABELS.PRIVATE.json'),rubric.read_text())
    copies,audit=redact([u['data'] for u in units],'E127',addresses=True);by={x['id']:x for x in copies};affected={x['id'] for x in audit['affected']};evidence={u['id']:u['data']['readout'] for u in units if u['id'] in affected};units=[dict(u,data=by[u['id']]) for u in units]
    d=CACHE/'E127/original104_units';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'UNIT_SEAL.json').exists():verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable full756');return d
    for n,v in [('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',evidence),('TRACKQ_READOUT_LIST.PRIVATE.json',q),('TRACKQ_IDENTITIES.PRIVATE.json',read(ident))]:write(d/n,v)
    write(d/'CUSTODY.json',dict(issuer='W-internals-C',experiment='E127',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_candidates_unchanged=True,original_E104_rubric_sha256=RUBRIC_SHA,native_oracle44_52_60_only=True,source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (native,inp,label,ps,blind,inv)]))
    write(d/'UNIT_SEAL.json',dict(experiment='E127',n=756,files={n:sha(d/n) for n in ('UNITS.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json','ORIGINAL_EVIDENCE.PRIVATE.json','TRACKQ_READOUT_LIST.PRIVATE.json','TRACKQ_IDENTITIES.PRIVATE.json','CUSTODY.json')}))
    write(d/'PREPARE_SPEC.json',dict(bank='E127',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name='original104'))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E127 full756 unitseal '+sha(prepare()/'UNIT_SEAL.json'))
