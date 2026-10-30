"""E108 complete native custody → blind continuation extraction, CPU only."""
import argparse
from collections import Counter
from pathlib import Path

from .transport import ROOT
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def index_jobs(root,seal):
    indexed={};counts=Counter()
    for member in sorted(seal['files']):
        if not member.startswith('jobs/') or not member.endswith('.json') or member.endswith('JOBS_SEAL.json'):continue
        rows=read(root/member)
        require(type(rows) is list,'original native job array')
        for i,x in enumerate(rows):
            kind='base' if 'channel' in x else x['reader']+'_'+x['kind']
            key=(kind,x['id'])
            require(key not in indexed,'no repeated pilot/production item')
            if kind=='base':require(x['max_new_tokens']==64 and type(x['raw']) is str and type(x['token_ids']) is list,'original greedy64 source')
            else:require(x['reader'] in ('oracle','nla') and x['repeat']==0 and type(x['text']) is str,'one native greedy readout, malformed retained')
            indexed[key]=dict(record=x,member=member,index=i)
            counts[kind]+=1
    require(dict(counts)==dict(base=1008,oracle_native=1008,nla_native=1008,oracle_placebo=84,nla_placebo=84),'complete original1008/2184 grid')
    return indexed


def extraction_units(inventory,indexed):
    native=[x for x in inventory if x['kind']=='native']
    require(len(native)==1008 and len({x['id'] for x in native})==1008,'complete frozen native inventory')
    require({x['id'] for x in native}=={i for kind,i in indexed if kind=='base'},'exact native item IDs')
    return [dict(id=x['id'],kind='choice_extract',rubric=None,
                 data=dict(id=x['id'],category=x['category'],continuation=indexed['base',x['id']]['record']['raw'])) for x in native]


def prepare(root,expected):
    root=Path(root);native_seal=root/'OUTPUT_SEAL.json'
    seal=verify(native_seal,expected)
    require(seal['experiment']=='E108' and seal['status']=='COMPLETE','eligible complete native source')
    base=ROOT/'results/g_agreement/understand/e108'
    verify(base/'BANK_SEAL.json',sha(base/'BANK_SEAL.json'))
    inventory=read(base/'INVENTORY.json')
    indexed=index_jobs(root,seal)
    units=extraction_units(inventory,indexed)
    placebo_ids={x['id'] for x in inventory if x['kind']=='placebo'}
    for reader in ('oracle','nla'):
        require({i for kind,i in indexed if kind==reader+'_placebo'}==placebo_ids,'complete frozen placebo IDs')
    dest=CACHE/'E108/native_extraction_units';dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json')==units,'immutable native extraction packet')
        return dest
    write(dest/'UNITS.json',units)
    write(dest/'SOURCE_POINTERS.PRIVATE.json',[dict(kind=k,item_id=i,member=v['member'],index=v['index']) for (k,i),v in indexed.items()])
    write(dest/'CUSTODY.json',dict(issuer='W-internals-C',original_source_owner='Track Q',experiment='E108',verified=True,
        complete_eligible_native_grid=True,labels_cpu_only=True,ground_truth_blind=True,
        no_reader_text_in_extraction=True,no_source_choice_labels_supplied=True,
        native_source_root=str(root),source_seals=[dict(seal=str(native_seal),sha256=expected),
        dict(seal=str(base/'BANK_SEAL.json'),sha256=sha(base/'BANK_SEAL.json'))]))
    write(dest/'UNIT_SEAL.json',dict(experiment='E108',n=1008,phase='extraction',files={n:sha(dest/n) for n in ('UNITS.json','CUSTODY.json','SOURCE_POINTERS.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json',dict(bank='E108',unit_seal=str(dest/'UNIT_SEAL.json'),unit_sha256=sha(dest/'UNIT_SEAL.json'),phase_name='native_choice'))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-root',type=Path,required=True);p.add_argument('--native-sha256',required=True);a=p.parse_args()
    d=prepare(a.native_root,a.native_sha256)
    print('E108 blind1008 extraction unit seal SHA256 '+sha(d/'UNIT_SEAL.json'))
