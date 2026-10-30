"""E109 full original readout grid → opaque E56 units; cohort stays CPU-side."""
import argparse
from pathlib import Path
from collections import Counter

from .transport import ROOT,SHARED
from .runner import CACHE
from .banks import opaque
from ..rubric202 import original_ids,amended,BASE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

PRIVATE_SHA='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4'


def make_units(records,original):
    mapping={}
    for x in original:
        key=(x['row'],x['item_id'])
        definition=dict(property=x['property'],values=x['values'])
        require(key not in mapping or mapping[key]==definition,'same original item/candidate orientation across conditions')
        mapping[key]=definition
    require(len(mapping)==168,'original E104 full test bank')
    counts=Counter();seen=set();units=[];joins=[]
    for ref,x in records:
        require(x['split']=='test' and x['reader']=='oracle' and x['layer'] in (44,52,60) and
                x['condition'] in ('steered','random') and type(x['text']) is str,'registered E109 test readout; malformed retained')
        key=(x['row'],x['base_id'])
        require(key in mapping,'original item identity, no inferred cohort')
        cell=(x['row'],x['base_id'],x['condition'],x['layer'])
        require(cell not in seen,'no duplicated pilot or readout')
        seen.add(cell);counts[x['row'],x['condition'],x['layer']]+=1
        ident=opaque('E109','native',x['id'])
        data=dict(id=ident,readout=x['text'],**mapping[key])
        units.append(dict(id=ident,kind='value',data=data,rubric=amended().decode()))
        joins.append(dict(id=ident,row=x['row'],item_id=x['base_id'],condition=x['condition'],layer=x['layer'],source_id=x['id'],source_ref=ref))
    require(len(units)==1008 and len({x['id']for x in units})==1008 and len(counts)==12 and all(n==84 for n in counts.values()),'all1008/12x84 cells, no cohort filtering')
    selected=set(original_ids([x['id'] for x in units],'E109'))
    return units+[dict(x,kind='old_value',rubric=BASE.read_text()) for x in units if x['id'] in selected],joins


def prepare(root,expected):
    root=Path(root);native=root/'OUTPUT_SEAL.json';seal=verify(native,expected)
    require(seal['experiment']=='E109' and seal['status']=='COMPLETE','complete native acquisition')
    old=SHARED/'E104';require(sha(old/'PRIVATE.json')==PRIVATE_SHA,'unchanged original E104 CPU join')
    original=read(old/'PRIVATE.json');packets={x['id']:x for x in read(old/'blind/JUDGE_PACKET.json')}
    for x in original:
        p=packets[x['opaque_id']]
        require(x['property']==p['property'] and x['values']==p['values'],'original blind definitions match original private source')
    records=[]
    for entry in read(root/'READOUT_INDEX.json'):
        require(set(entry)=={'job','member'} and entry['member'] in seal['files'],'original readout member pin')
        for i,x in enumerate(read(root/entry['member'])):records.append((dict(member=entry['member'],index=i),x))
    units,joins=make_units(records,original)
    dest=CACHE/'E109/oracle_arrival_units';dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'));require(read(dest/'UNITS.json')==units,'immutable E109 units')
        return dest
    write(dest/'UNITS.json',units);write(dest/'SOURCE_POINTERS.PRIVATE.json',joins)
    write(dest/'CUSTODY.json',dict(issuer='W-internals-C',original_source_owner='Track Q',experiment='E109',verified=True,
        complete_eligible_native_grid=True,labels_cpu_only=True,cohort_filter_applied=False,original_private_sha256=PRIVATE_SHA,
        native_source_root=str(root),source_seals=[dict(seal=str(native),sha256=expected),dict(seal=str(old/'blind/BLIND_SEAL.json'),sha256=sha(old/'blind/BLIND_SEAL.json'))]))
    write(dest/'UNIT_SEAL.json',dict(experiment='E109',n_primary=1008,n_original=252,files={n:sha(dest/n) for n in ('UNITS.json','CUSTODY.json','SOURCE_POINTERS.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json',dict(bank='E109',unit_seal=str(dest/'UNIT_SEAL.json'),unit_sha256=sha(dest/'UNIT_SEAL.json'),phase_name='oracle_arrival'))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-root',type=Path,required=True);p.add_argument('--native-sha256',required=True);a=p.parse_args();d=prepare(a.native_root,a.native_sha256)
    print('E109 full1008 primary+252old unit seal SHA256 '+sha(d/'UNIT_SEAL.json'))
