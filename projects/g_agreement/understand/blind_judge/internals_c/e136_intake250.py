"""CPU-only exact E136 deviation2 intake; no judging or scientific selection."""
import json
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
CUES={'sycophancy_pressure','misuse_intent'}


def units_for(records,items,pointers,labels,n=400):
    public={x['id']:x for x in items};ptr={x['id']:x for x in pointers};lab={x['id']:x for x in labels}
    require(len(public)==len(ptr)==n and set(public)==set(ptr) and set(public)<=set(lab),'exact frozen eligible input IDs')
    require({x['cue']for x in pointers}==CUES,'only registered two cue families')
    units=[];joins=[];seen=set()
    for ref,r in records:
        require(r['item_id']in public and r['item_id']not in seen and r['reader']=='oracle'and r['source_layer']==44 and r['id']==r['item_id']+':oracle:44','literal unique Oracle44 cell')
        require(type(r['text'])is str,'preserve empty/degenerate text verbatim');seen.add(r['item_id']);p=ptr[r['item_id']];l=lab[r['item_id']]
        require(l['cue']==p['cue'] and l['split']==p['split'] and l['pair_id']==p['source_pair_id'],'original CPU source-role identity')
        require([m['role']for m in l['messages']]==['system','user'],'original full source chat')
        uid=opaque('E136',r['id']);units.append(dict(id=uid,readout=r['text'],source_text=json.dumps(l['messages'],ensure_ascii=False)))
        joins.append(dict(id=uid,native_id=r['id'],item_id=r['item_id'],layer=44,source_ref=ref,original_source_index=p['source_index'],cue=p['cue'],pair_id=p['source_pair_id'],split=p['split']))
    require(seen==set(public),'all actual400; no partial stitching/refill')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def prepare():
    source=HERE/'E136_INTAKE250_SOURCE_SEAL.json'
    for name,h in read(source)['files'].items():require(sha(ROOT/name)==h,'published CPU intake source')
    rec=read(ROOT/'results/g_agreement/i2/E136_DEV2_COMPLETE247.json');native=Path(rec['raw_directory']);ns=verify(native/'OUTPUT_SEAL.json','25b38da7c35387315a54d0c42f85ecba83fd10347a20cf40a5bb418bf9713f58')
    require(ns['experiment']=='E136'and ns['status']=='COMPLETE'and ns['input_sha256']=='435c5c729e8eac765f51b92e5d7ee63d9183c26ec6beeaaab6056b2d095af629','complete original dev2 acquisition')
    inputs=ROOT.parent/'outputs/e136-dev2-inputs-v1';ip=inputs/'inputs/INPUT_SEAL.json';verify(ip,ns['input_sha256']);sp=inputs/'cpu_only/SUBSET_SEAL.json';verify(sp,sha(sp))
    old=ROOT.parent/'outputs/e136-bank-v2';lp=old/'cpu_only/LABEL_SEAL.json';verify(lp,'2549533aa0c02a8a65d2f55a645a28f96e1a0b8a72de47b9493f419c201021e1')
    original=old/'inputs/INPUT_SEAL.json';verify(original,'8333875388b59cd90eb2e0f9bcd6a226234022f38fd1e415424c884d447f4e50')
    full=read(original.parent/'items.json');ptr=read(sp.parent/'SUBSET_POINTERS.PRIVATE.json');items=read(ip.parent/'items.json')
    require(all(full[p['source_index']]==i for p,i in zip(ptr,items))and len(ptr)==len(items)==400,'literal original full-source subset records/order')
    records=[]
    for m in ns['files']:
        if m.startswith('jobs/')and m.endswith('.json'):
            records.extend((dict(seal=str(native/'OUTPUT_SEAL.json'),sha256=sha(native/'OUTPUT_SEAL.json'),member=m,keys=[i,'text']),r)for i,r in enumerate(read(native/m)))
    units,joins=units_for(records,items,ptr,read(lp.parent/'LABELS.PRIVATE.json'))
    d=CACHE/'E136/native_units250';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700);final=d/'UNIT_SEAL.json'
    if final.exists():verify(final,sha(final));require(read(d/'UNITS.json')==units,'immutable original units');return d
    write(d/'UNITS.json',units);write(d/'SOURCE_POINTERS.PRIVATE.json',joins)
    write(d/'CUSTODY.json',dict(experiment='E136',deviation=2,n=400,readouts_complete=True,no_condition_labels_in_units=True,empty_readouts_preserved=True,raw_native_git_export=False,question_contract_pending=True,paid_calls=False,analysis_run=False))
    write(final,dict(experiment='E136',n=400,source_sha256=sha(source),source_seals=[dict(seal=str(p),sha256=sha(p))for p in(native/'OUTPUT_SEAL.json',ip,sp,lp,original)],files={n:sha(d/n)for n in['UNITS.json','SOURCE_POINTERS.PRIVATE.json','CUSTODY.json']}))
    return d
