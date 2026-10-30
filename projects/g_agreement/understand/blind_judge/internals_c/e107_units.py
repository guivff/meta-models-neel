"""Render all new E107 outside descriptions using the pre-frozen source plan.

Only a completed, verified full generation seal can be consumed. The generated
strings remain exact; no native baseline is rescored or rejudged.
"""
import argparse
from pathlib import Path

from .transport import ROOT
from .runner import CACHE
from .banks import opaque
from ..rubric202 import original_ids,amended,BASE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def build_units(plans,generated):
    by={x['id']:x for x in generated}
    require(len(by)==len(generated) and set(by)=={x['inventory_id'] for x in plans},'complete exact generated source grid')
    units=[]
    for p in plans:
        source=by[p['inventory_id']]
        require(source['phase']=='generation' and source['status']=='GENERATED' and source['finish_reason'] in ('stop','length') and
                type(source['text']) is str and source.get('refusal') is None,'retain generation truncation; refusal requires owner diagnosis')
        ident=opaque('E107','outside_judge',p['inventory_id'],p['target'])
        data=dict(id=ident,property=p['property'],values=p['values'],readout=source['text'])
        units.append(dict(id=ident,kind='value',data=data,rubric=amended().decode()))
    require(len({x['id'] for x in units})==len(units),'opaque target IDs remain distinct')
    selected=set(original_ids([x['id'] for x in units],'E107'))
    return units+[dict(x,kind='old_value',rubric=BASE.read_text()) for x in units if x['id'] in selected]


def prepare():
    home=CACHE/'E107'
    generation=home/'generation/outputs/GENERATION_SEAL.json'
    seal=verify(generation,sha(generation))
    require(seal['experiment']=='E107' and seal['phase']=='generation' and seal['status']=='COMPLETE' and seal['route_verified'] is True,'complete route-verified E107 generation')
    plan=home/'frozen_judge_plan'
    verify(plan/'PLAN_SEAL.json',sha(plan/'PLAN_SEAL.json'))
    bindings=read(plan/'ORIGINAL_SOURCE_BINDINGS.PRIVATE.json')
    for path,digest in bindings.items():require(sha(path)==digest,'frozen original source binding')
    plans=read(plan/'PLANS.PRIVATE.json')
    units=build_units(plans,read(generation.parent/'RESPONSES.json'))
    dest=home/'outside_judge_units'
    dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json')==units,'immutable new outside unit grid')
        return dest
    write(dest/'UNITS.json',units)
    write(dest/'CUSTODY.json',dict(issuer='W-internals-C',original_source_owner='I-2',experiment='E107',verified=True,
        owner_delegation='I2-C-E107-E85-DIRECT-DISPATCH-20261029; direct Guiv W-internals-C execution assignment',
        complete_eligible_native_grid=True,labels_cpu_only=True,regex_first_unresolved_only=True,
        regex_resolved_retained=0,regex_note='source E81/E82/E86 description channels are blind E56 judging; no new native regex applied',
        source_seals=[dict(seal=str(generation),sha256=sha(generation)),dict(seal=str(plan/'PLAN_SEAL.json'),sha256=sha(plan/'PLAN_SEAL.json'))]))
    write(dest/'UNIT_SEAL.json',dict(experiment='E107',n=len(units),files={n:sha(dest/n) for n in ('UNITS.json','CUSTODY.json')}))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.parse_args();dest=prepare()
    print('Full E107 new outside unit seal SHA256 '+sha(dest/'UNIT_SEAL.json')+'; no judging calls')
