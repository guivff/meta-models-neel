"""Literal full752 late Oracle readouts / sealed E108 ONE choices; no analysis."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from .banks import opaque
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def verify_choice_envelope(value, choice):
    require(value == dict(status='ONE', canonical_member=choice), 'literal sealed original ONE status/member equality')


def make_units(records,cohort,items):
    selected={x['id']:(i,x) for i,x in enumerate(cohort)}
    require(len(selected)==len(cohort)==376 and {x['id'] for x in items}==set(selected),'full sealed376 ONE item cohort')
    require(sum(x['arm']=='immediate' for x in cohort)==329 and sum(x['arm']=='delayed' for x in cohort)==47,'original329/47 arms')
    require(len(records)==len({r['id'] for _,r in records})==752,'complete unique752 native records')
    units=[];joins=[];seen=set()
    for source_ref,r in records:
        key=r['item_id'],r['source_layer']
        require(key not in seen and key[0] in selected and key[1] in (52,60) and r['reader']=='oracle' and type(r['text']) is str,'one original readout/item/block')
        seen.add(key);i,c=selected[key[0]];require(type(c['choice']) is str and bool(c['choice']),'literal sealed ONE choice')
        uid=opaque('E116','hit',r['id'])
        units.append(dict(id=uid,kind='choice_hit',rubric=None,data=dict(id=uid,chosen_member=c['choice'],readout=r['text'])))
        joins.append(dict(id=uid,item_id=c['id'],arm=c['arm'],block=key[1],native_id=r['id'],native_text_ref=source_ref,cohort_index=i,choice_ref=c['ground_truth_ref']))
    require(seen=={(i,b) for i in selected for b in (52,60)},'all registered item/block cells, no stitching')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def prepare():
    for n,h in read(HERE/'E116_INTAKE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published E116 intake/owner source')
    native=ROOT.parent/'wt-i2/cache/g_agreement/i2/parallel_gpu230/e116-measured-r1/terminal_pull/outputs/OUTPUT_SEAL.json'
    ns=verify(native,'c4fb717411a03145ab427f590c2f78eba2a9ced284f4653817a4a0eae4f59002')
    require(ns['status']=='COMPLETE' and ns['experiment']=='E116' and ns['input_sha256']=='e7aea4db86d8bcfc9bd4fc838b7a889acb4bb5c1c113fc307d1090bac290c395','whole original measured native attempt')
    inp=ROOT.parent/'outputs/e116-inputs-v1/inputs/INPUT_SEAL.json';verify(inp,ns['input_sha256'])
    cp=ROOT.parent/'outputs/e116-inputs-v1/cpu_only/COHORT_SEAL.json';cs=verify(cp,'16e07a9e4c9f636d66c2b14a138794158940cbc9a3ab5e19f59482cec300c8b6')
    require(sha(Path(cs['source_normalization']))==cs['source_normalization_sha256'],'original E108 normalization unchanged')
    for r in cs['ground_truth_source_seals']:verify(r['seal'],r['sha256'])
    cohort=read(cp.parent/'COHORT.PRIVATE.json')
    for c in cohort:
        ref=c['ground_truth_ref'];require('seal_index' in ref,'original explicit choice pointer')
        r=cs['ground_truth_source_seals'][ref['seal_index']];value=read(Path(r['seal']).parent/ref['member'])
        for k in ref['keys']:value=value[k]
        verify_choice_envelope(value,c['choice'])
    records=[]
    for m in ns['files']:
        if m.startswith('jobs/') and m.endswith('.json'):
            records.extend((dict(seal=str(native),sha256=sha(native),member=m,keys=[i,'text']),r) for i,r in enumerate(read(native.parent/m)))
    units,joins=make_units(records,cohort,read(inp.parent/'items.json'))
    raw=[dict(id=u['id'],readout=u['data']['readout']) for u in units];copies,audit=redact(raw,'E116',addresses=True);copies={x['id']:x['readout'] for x in copies};affected={x['id'] for x in audit['affected']}
    originals={x['id']:x['readout'] for x in raw if x['id'] in affected}
    units=[dict(u,data=dict(u['data'],readout=copies[u['id']])) for u in units]
    d=CACHE/'E116/chosen_member_hit_units';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'UNIT_SEAL.json').exists():
        verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable original752');return d
    for n,v in [('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',originals)]:write(d/n,v)
    refs=[dict(seal=str(native),sha256=sha(native)),dict(seal=str(inp),sha256=sha(inp)),dict(seal=str(cp),sha256=sha(cp))]+cs['ground_truth_source_seals']
    write(d/'CUSTODY.json',dict(experiment='E116',issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,native_oracle52_60_only=True,original_E108_choices_unchanged=True,source_seals=refs))
    write(d/'UNIT_SEAL.json',dict(experiment='E116',n=752,files={n:sha(d/n) for n in ('UNITS.json','CUSTODY.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json','ORIGINAL_EVIDENCE.PRIVATE.json')}))
    write(d/'PREPARE_SPEC.json',dict(bank='E116',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name='chosen_member_hit'))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E116 full752 units '+sha(prepare()/'UNIT_SEAL.json'))
