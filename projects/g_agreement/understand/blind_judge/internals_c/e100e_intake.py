"""Full attempt2 E100e reads to E82 candidate judgments; private donor joins CPU."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from ..privacy79 import redact
from ..rubric202 import amended,BASE,original_ids
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

ROWS={'container_after_move','holder_after_handovers'}


def make_units(records,labels):
    by={x['id']:x for x in labels}
    require(len(by)==len(labels)==168 and {x['row']for x in labels}==ROWS,'original168 two-row pairing roster')
    require(all(sum(x['row']==r for x in labels)==84 for r in ROWS),'84 original test items each row')
    for x in labels:
        require(x['split']=='test' and x['donor_id']in by and by[x['donor_id']]['row']==x['row'] and
            x['donor_value']==by[x['donor_id']]['source_value'] and x['source_value']!=x['donor_value'],
            'original same-row different-value donor; no new selection')
    data=[];joins=[];seen=set()
    for ref,x in records:
        key=(x['item_id'],x['reader'])
        require(key not in seen and key[0]in by and key[1]in ('oracle','nla') and x['row']==by[key[0]]['row'] and
            x['repeat']==0 and x['condition']=='transplant' and type(x['text'])is str,'new attempt2 single original readout per item/reader')
        seen.add(key);label=by[key[0]];ident=opaque('E100e','native',x['id'])
        data.append(dict(id=ident,property=label['row'],values=dict(A=label['source_value'],B=label['donor_value']),readout=x['text']))
        joins.append(dict(id=ident,item_id=key[0],row=label['row'],reader=key[1],source_ref=ref,
            target_letter='B',original_letter='A',target_value=label['donor_value'],original_value=label['source_value'],donor_id=label['donor_id']))
    require(seen=={(i,r)for i in by for r in ('oracle','nla')} and len(data)==336,'full336 native pair grid')
    copied,audit=redact(data,'E100e',addresses=True);raw={x['id']:x['readout']for x in data}
    original={x['id']:raw[x['id']]for x in audit['affected']}
    units=[dict(id=x['id'],kind='value',data=x,rubric=amended().decode())for x in copied]
    selected=set(original_ids([x['id']for x in units],'E100e'))
    units += [dict(x,kind='old_value',rubric=BASE.read_text())for x in units if x['id']in selected]
    return units,joins,audit,original


def prepare(root,expected):
    for name,digest in read(HERE/'E100e_RUNTIME_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==digest,'E100e source pin')
    root=Path(root).resolve();native=root/'OUTPUT_SEAL.json';s=verify(native,expected)
    require(s['experiment']=='E100e' and s['status']=='COMPLETE' and
        s['input_sha256']=='9b944aedc44534b58b8e6fc4a319f00bf391423f0498dfcfcc6481c41d9c5bc5' and
        s['source_sha256']=='286a907f7b70f4223ab71922c7078f11ffe5a86ea5b519fc68968ae6b3395060',
        'actual complete attempt2, unchanged original inputs, no partial stitching')
    labels=ROOT.parent/'outputs/e100e-inputs-v1/cpu_only/LABEL_SEAL.json'
    verify(labels,'24b4bb2a9082269d75c57c1e14c5e91616d03c77429c9a3b78ba72702186f2a7')
    old=ROOT.parent/'wt-i2/cache/g_agreement/i2/e82_judge_cpu_v1/runtime/results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt'
    require(sha(old)==sha(ROOT/'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt'), 'exact original E82 rubric')
    records=[]
    for member in sorted(s['files']):
        if member.startswith('jobs/')and member.endswith('.json')and not member.endswith('STAGE_SEAL.json'):
            rows=read(root/member);require(type(rows)is list,'original readout batch')
            records.extend((dict(member=member,keys=[i,'text']),x)for i,x in enumerate(rows))
    units,joins,audit,original=make_units(records,read(labels.parent/'LABELS.json'))
    dest=CACHE/'E100e/attempt2_value_units';dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'));require(read(dest/'UNITS.json')==units,'immutable E100e unit grid');return dest
    for name,value in [('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',original)]:write(dest/name,value)
    write(dest/'CUSTODY.json',dict(issuer='W-internals-C',original_source_owner='Track Q',experiment='E100e',verified=True,
        complete_eligible_native_grid=True,labels_cpu_only=True,source_pairing_seed=20261029,
        candidate_order='A=original recipient value;B=actual sealed donor value, same for both readers; source-independent of outputs',
        original_E82_rubric_sha256=sha(old),source_seals=[dict(seal=str(native),sha256=expected),dict(seal=str(labels),sha256=sha(labels))]))
    write(dest/'UNIT_SEAL.json',dict(experiment='E100e',n_primary=336,n_original=84,files={p.name:sha(p)for p in dest.iterdir()if p.is_file()}))
    write(dest/'PREPARE_SPEC.json',dict(bank='E100e',unit_seal=str(dest/'UNIT_SEAL.json'),unit_sha256=sha(dest/'UNIT_SEAL.json'),phase_name='attempt2_value'))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-root',type=Path,required=True);p.add_argument('--native-sha256',required=True);a=p.parse_args()
    d=prepare(a.native_root,a.native_sha256);print('E100e complete336+84 unit seal '+sha(d/'UNIT_SEAL.json'))
