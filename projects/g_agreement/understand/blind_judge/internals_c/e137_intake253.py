"""Literal E137 custody and original E133 alphabet; no selection or analysis."""
from pathlib import Path
from .transport import ROOT
from .runner import CACHE
from .banks import opaque
from .e133_packet_intake import templates,OTHER
from .e133_judge import naming_call,RUBRIC_SHA
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

INVENTORY=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e137/binding_v1/inventory/INVENTORY_SEAL.json')
INV_SHA='eae949987189d1567060d78bb73c58349fa85c0232b03d1a04f58b9d4ed1f676'
NATIVE=ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E137/measured_a2/out/OUTPUT_SEAL.json'
NATIVE_SHA='b03e95749a767dd6bc58635bbd36b68f3d1bc0b42f1d2691763b9d661826b54c'

def confirm_map(rows,pairs,selected):
    by={r['item_id']:r for r in rows};seen=set()
    for p in pairs:
        require(p['pair_count']==1 and len(p['members'])==2,'both frozen pair members')
        for m in p['members']:
            require(m['item_id'] in by and m['item_id'] not in seen,'explicit original item ID once');seen.add(m['item_id']);r=by[m['item_id']]
            require(r['pair_id']==p['pair_id'] and r['member']==m['member'] and r['current']==m['current'] and r['previous']==m['previous'],'original CPU roles unchanged')
            require(r['value_map']==p['value_map'] and p['value_map'].get('OTHER')==OTHER,'Q alphabet exactly original template alphabet')
    require(seen==set(selected) and len(seen)==len(selected),'whole explicit selected roster')
    return by

def intake():
    inv=verify(INVENTORY,INV_SHA);ns=verify(NATIVE,NATIVE_SHA)
    require(inv['experiment']=='E137' and inv['status']=='SCREENED_COHORT_FROZEN' and inv['labels_cpu_only'] is True and ns['experiment']=='E137' and ns['status']=='COMPLETE' and ns['stages']['main_synthetic']=='COMPLETE','actual full registered E137 source, no relabelled old acquisition')
    binding=ROOT/'results/g_agreement/understand/e137/RUNNER_INPUT_BINDING.json';b=read(binding);ip=Path(b['public_root'])/'INPUT_SEAL.json';cp=Path(b['CPU_only_root'])/'CPU_SEAL.json';verify(ip,b['input_sha256']);verify(cp,b['CPU_only_seal_sha256'])
    original=Path(b['original_CPU_pair_path']);require(sha(original)==b['original_CPU_pair_sha256'],'original frozen 360 pair bank')
    manifest=ROOT/'results/g_agreement/understand/e137/BANK_MANIFEST.json';man=read(manifest)
    rows=templates('synthetic',read(ip.parent/'items.json'),read(cp.parent/'ROLES.PRIVATE.json'),read(original)['pairs'],man['names'],man['places'])
    selected=read(INVENTORY.parent/'SELECTED_ITEM_IDS.PRIVATE.json');pairs=read(INVENTORY.parent/'PAIRS.PRIVATE.json');by=confirm_map(rows,pairs,selected)
    require(len(selected)==154 and len(pairs)==77,'literal 154 members / 77 pairs, no fill to 600')
    inner=NATIVE.parent/'main_synthetic/OUTPUT_SEAL.json';ins=verify(inner,sha(inner));require(ins['experiment']=='E133' and ins['arm']=='synthetic' and ins['stage']=='main' and ins['status']=='COMPLETE','preserve original inner E133 runner envelope under actual E137 outer seal')
    index=read(inner.parent/'INDEX.json');units=[];joins=[];seen=set()
    for x in index:
        if x.get('kind')!='oracle':continue
        key=x['id'],x['block'];require(x['id'] in selected and x['block'] in (44,52,60) and key not in seen and x['member'].startswith('oracle/'),'explicit complete native INDEX identity');seen.add(key)
        member='main_synthetic/'+x['member'];require(member in ns['files'],'outer original seal binds readout member');record=read(NATIVE.parent/member)[x['record']];require(type(record['text']) is str,'empty retained, absent never synthesized')
        r=by[x['id']];uid=opaque('E137',x['id'],str(x['block']));u=dict(id=uid,property=r['property'],values=r['values'],readout=record['text']);naming_call(u);units.append(u)
        joins.append(dict(id=uid,native_id=x['id']+':oracle:'+str(x['block']),item_id=x['id'],pair_id=r['pair_id'],member=r['member'],block=x['block'],value_map=r['value_map'],current=r['current'],previous=r['previous'],source_ref=dict(seal=str(NATIVE),sha256=NATIVE_SHA,member=member,keys=[x['record'],'text'])))
    require(seen=={(i,l)for i in selected for l in(44,52,60)} and len(units)==462,'whole actual 462 grid, no selection/refill')
    sources=[dict(seal=str(p),sha256=sha(p))for p in(INVENTORY,NATIVE,inner,ip,cp)];d=CACHE/'E137/native_units253';d.mkdir(parents=True,exist_ok=True)
    payloads={'UNITS.json':units,'SOURCE_POINTERS.PRIVATE.json':joins,'MAP_CONFIRMATION.PRIVATE.json':dict(inventory_sha256=INV_SHA,original_pair_sha256=sha(original),pairs=77,members=154,readouts=462,all_maps_identical=True,rubric_sha256=RUBRIC_SHA)}
    if(d/'UNIT_SEAL.json').exists():
        verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(all(read(d/k)==v for k,v in payloads.items()),'immutable exact intake')
    else:
        for k,v in payloads.items():write(d/k,v);(d/k).chmod(0o600)
        write(d/'UNIT_SEAL.json',dict(experiment='E137',n=462,labels_cpu_only=True,source_seals=sources,files={k:sha(d/k)for k in payloads}))
    return d/'UNIT_SEAL.json'
