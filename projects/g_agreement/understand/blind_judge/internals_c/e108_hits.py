"""Full-seal E108 extraction → original native/outside/placebo hit units.

Only registered NONE/multiple/failed-extraction eligibility is applied. Every
original inventory item stays in the CPU measurement plan, including null cells.
No aliases or early-choice exclusion are introduced.
"""
import argparse
import re
from pathlib import Path
from collections import Counter

from .transport import ROOT,HERE
from .runner import CACHE
from .banks import opaque
from .e108_intake import index_jobs
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def choice_offset(raw,ids,member,tokenizer):
    """Report only offsets proven by the exact original token sequence."""
    if tokenizer.decode(ids,skip_special_tokens=True)!=raw:return None,'DECODE_MISMATCH'
    encoded=tokenizer.encode(raw,add_special_tokens=False)
    if list(encoded.ids)!=ids:return None,'TOKEN_SEQUENCE_NOT_REPRODUCED'
    folded=raw.casefold()
    if len(folded)!=len(raw):return None,'CASEFOLD_POSITION_AMBIGUOUS'
    matches=list(re.finditer(r'(?<!\w)'+re.escape(member.casefold())+r'(?!\w)',folded))
    if len(matches)!=1:return None,'NO_UNIQUE_LITERAL_MEMBER_SPAN'
    start=matches[0].start();end=matches[0].end()
    indices=[i for i,(a,b) in enumerate(encoded.offsets) if a<end and b>start]
    if not indices:return None,'NO_SOURCE_TOKEN_OVERLAP'
    return min(indices),'EXACT_NATIVE_TOKEN_IDS_AND_UNIQUE_LITERAL_SPAN'


def build_units(inventory,indexed,extractions,outside,placebo_specs,tokenizer=None):
    gt={x['id']:x for x in extractions};native=[x for x in inventory if x['kind']=='native'];placebo=[x for x in inventory if x['kind']=='placebo']
    require(len(gt)==len(extractions) and set(gt)=={x['id'] for x in native},'full original extraction IDs')
    out={x['id']:x for x in outside}
    require(len(out)==len(outside) and set(out)=={opaque('E108','outside',x['id']) for x in native},'full original outside generation IDs')
    specs={x['id']:x for x in placebo_specs}
    require(len(specs)==len(placebo_specs) and set(specs)=={x['id'] for x in placebo},'all original placebo references')
    units=[];plans=[];by_gt={};counts=Counter()
    for meta in native:
        ident=meta['id'];terminal=gt[ident]
        require(terminal['kind']=='choice_extract','original blind extraction kind')
        code=terminal['code'] if terminal['status']=='KEPT' else dict(status='UNPARSEABLE',canonical_member=None)
        require(code['status'] in ('ONE','NONE','MULTIPLE','UNPARSEABLE'),'ground-truth disposition')
        require(bool(code['canonical_member']) if code['status']=='ONE' else code['canonical_member'] is None,'original canonical member, no alias invention')
        by_gt[ident]=code;counts[code['status']]+=1
        fields={};missing={}
        if code['status']=='ONE':
            for system in ('oracle','nla','outside'):
                if system=='outside':
                    source=out[opaque('E108','outside',ident)]
                    require(source['phase']=='generation' and source['status']=='GENERATED' and source['finish_reason'] in ('stop','length'),'original outside text/length retained')
                    if source.get('refusal') is not None:
                        fields[system]=None;missing[system]='OUTSIDE_REFUSED';continue
                    text=source['text']
                else:text=indexed[system+'_native',ident]['record']['text']
                uid=opaque('E108','hit',ident,system)
                units.append(dict(id=uid,kind='choice_hit',rubric=None,data=dict(id=uid,chosen_member=code['canonical_member'],readout=text)))
                fields[system]=uid
        else:
            fields={s:None for s in ('oracle','nla','outside')};missing={s:'GROUND_TRUTH_'+code['status'] for s in fields}
        offset=None;offset_reason='GROUND_TRUTH_NOT_ONE'
        if code['status']=='ONE' and tokenizer is not None:
            source=indexed['base',ident]['record'];offset,offset_reason=choice_offset(source['raw'],source['token_ids'],code['canonical_member'],tokenizer)
        elif code['status']=='ONE':offset_reason='TOKENIZER_UNAVAILABLE'
        plans.append(dict(id=ident,kind='native',ground_truth=code,hit_unit_ids=fields,missing_reasons=missing,
                          choice_token_offset=offset,choice_token_offset_source=offset_reason,J_fraction=None,J_fraction_disposition='await owner source; no value inferred'))
    for meta in placebo:
        ident=meta['id'];reference=specs[ident]['reference_id'];require(reference in by_gt,'original placebo reference')
        choice=by_gt[reference];fields={};missing={}
        for system in ('oracle','nla'):
            if choice['status']!='ONE':fields[system]=None;missing[system]='REFERENCE_GROUND_TRUTH_'+choice['status'];continue
            uid=opaque('E108','placebo_hit',ident,system);text=indexed[system+'_placebo',ident]['record']['text']
            units.append(dict(id=uid,kind='choice_hit',rubric=None,data=dict(id=uid,chosen_member=choice['canonical_member'],readout=text)))
            fields[system]=uid
        plans.append(dict(id=ident,kind='placebo',reference_id=reference,hit_unit_ids=fields,missing_reasons=missing))
    require(len({x['id'] for x in units})==len(units) and len(plans)==len(inventory),'complete unique units and unchanged full measurement inventory')
    return units,plans,dict(counts)


def prepare():
    from .registered import source_gate
    source_gate(HERE/'E108_HIT_SOURCE_SEAL.json')
    home=CACHE/'E108';native_custody=read(home/'native_extraction_units/CUSTODY.json');native_ref=native_custody['source_seals'][0]
    ns=verify(native_ref['seal'],native_ref['sha256']);native_root=Path(native_ref['seal']).parent;indexed=index_jobs(native_root,ns)
    extraction=home/'native_choice_extraction/outputs/JUDGMENT_SEAL.json';es=verify(extraction,sha(extraction))
    require(es['experiment']=='E108' and es['status']=='COMPLETE' and es['route_verified'] is True,'complete blind extraction seal')
    generation=home/'generation/outputs/GENERATION_SEAL.json';gs=verify(generation,sha(generation));require(gs['status']=='COMPLETE' and gs['route_verified'] is True,'complete outside seal')
    base=ROOT/'results/g_agreement/understand/e108';verify(base/'BANK_SEAL.json',sha(base/'BANK_SEAL.json'));inventory=read(base/'INVENTORY.json')
    receipt=read(base/'INPUT_RECEIPT.json');spec=Path(receipt['public_directory'])/'PLACEBO_SPECS.json';require(sha(spec)==receipt['files']['PLACEBO_SPECS.json'],'original reference-vector specifications')
    require(sha(TOKENIZER)==TOKENIZER_SHA,'pinned tokenizer bytes')
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(TOKENIZER))
    units,plans,counts=build_units(inventory,indexed,read(extraction.parent/'JUDGMENTS.json'),read(generation.parent/'RESPONSES.json'),read(spec),tok)
    require(len(plans)==1092 and sum(counts.values())==1008,'full1008/84 before any hits')
    dest=home/'chosen_member_hit_units';dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'));require(read(dest/'UNITS.json')==units,'immutable hit phase')
        return dest
    write(dest/'UNITS.json',units);write(dest/'MEASUREMENT_PLAN.PRIVATE.json',plans)
    write(dest/'ELIGIBILITY_COUNTS.json',dict(ground_truth=counts,all_inventory_items=1092,hit_requests=len(units),early_choices_excluded=0,aliases_added=0,tokenizer_sha256=TOKENIZER_SHA))
    write(dest/'CUSTODY.json',dict(issuer='W-internals-C',original_source_owner='Track Q',experiment='E108',verified=True,
        complete_eligible_native_grid=True,labels_cpu_only=True,extraction_complete=True,outside_complete=True,registered_none_multiple_exclusions_only=True,
        source_seals=[dict(seal=str(extraction),sha256=sha(extraction)),dict(seal=str(generation),sha256=sha(generation)),native_ref,
            dict(seal=str(base/'BANK_SEAL.json'),sha256=sha(base/'BANK_SEAL.json'))]))
    write(dest/'UNIT_SEAL.json',dict(experiment='E108',files={n:sha(dest/n)for n in ('UNITS.json','CUSTODY.json','MEASUREMENT_PLAN.PRIVATE.json','ELIGIBILITY_COUNTS.json')}))
    write(dest/'PREPARE_SPEC.json',dict(bank='E108',unit_seal=str(dest/'UNIT_SEAL.json'),unit_sha256=sha(dest/'UNIT_SEAL.json'),phase_name='chosen_member_hit'))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.parse_args();d=prepare();print('E108 complete-source hit unit seal '+sha(d/'UNIT_SEAL.json'))
