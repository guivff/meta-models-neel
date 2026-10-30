"""CPU-only E107 target/render plan; never read new outside output at freeze time."""
import argparse
import hashlib
from pathlib import Path

from .transport import ROOT
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def outside_values(lineage, letters):
    belief=list(dict.fromkeys(lineage['source_belief']+lineage['source_belief_aliases']))
    truth=list(dict.fromkeys((lineage['source_truth'] or [])+lineage['source_truth_aliases']))
    require(bool(belief),'original nonempty belief candidates')
    if not truth:
        require(letters=={'belief':'A'},'no invented truth contrast')
        return {'A':belief,'B':[]}
    require(set(letters)=={'belief','truth'} and set(letters.values())=={'A','B'},'opposing frozen outside target letters')
    return {letters['belief']:belief,letters['truth']:truth}


def plan_for(meta, roster, maps, joins, packets):
    bank=meta['bank'];source=[joins[bank][ident] for ident in roster['source_records']]
    require(meta['id']==roster['id']==maps['id'],'source/metadata identity')
    outside=meta['target_letters_by_system']['outside']
    if bank=='E81':
        origin=next(x for x in source if x['arm']=='generic')
        native=packets[bank][origin['id']]
        prop,values=native['property'],native['values']
    elif bank=='E82':
        require(len(source)==2 and {x['reader'] for x in source}=={'oracle','nla'},'original E82 pair')
        require(source[0]['source_public_id']==source[1]['source_public_id'],'same original item')
        prop=source[0]['target_kind']
        values=outside_values(maps['source_lineage'],outside)
    else:
        require(bank=='E86' and len(source)==2 and {x['reader'] for x in source}=={'oracle','nla'},'original E86 pair')
        native=packets[bank][source[0]['id']]
        prop,values=native['property'],native['values']
        require(outside=={'truth':'A'},'original E86 truth-A order')
    return [dict(inventory_id=meta['id'],bank=bank,target=target,property=prop,values=values)
            for target in outside]


def freeze():
    owner=ROOT.parent/'wt-i2'
    home=owner/'cache/g_agreement/i2/e107_cpu_inventory_v1'
    inv=owner/'results/g_agreement/i2/e107_inventory_v1'
    seal=verify(inv/'INVENTORY_SEAL.json',sha(inv/'INVENTORY_SEAL.json'))
    inventory=read(inv/'INVENTORY.json')
    roster={x['id']:x for x in read(home/'CANDIDATE_ROSTER.PRIVATE.json')}
    target_maps={x['id']:x for x in read(inv/'TARGET_MAPS.PRIVATE.json')}
    joins={};packets={};bindings={str(inv/'INVENTORY_SEAL.json'):sha(inv/'INVENTORY_SEAL.json')}
    for bank,version in [('E81','3'),('E82','1'),('E86','1')]:
        base=owner/f'cache/g_agreement/i2/{bank.lower()}_judge_cpu_v{version}'
        path=base/'JOIN_MAP.PRIVATE.json'
        joins[bank]={x['id']:x for x in read(path)}
        bindings[str(path)]=sha(path)
        if bank!='E82':
            path=base/'JUDGE_PACKET.json'
            packets[bank]={x['id']:x for x in read(path)}
            bindings[str(path)]=sha(path)
    plans=[p for meta in inventory for p in plan_for(meta,roster[meta['id']],target_maps[meta['id']],joins,packets)]
    require(len(inventory)==4297 and len(plans)==4496 and len({(x['inventory_id'],x['target']) for x in plans})==4496,'complete original outside target scope')
    require(sum(x['bank']=='E82' and x['target']=='truth' for x in plans)==199,'ten no-truth sources retained without invented target')
    dest=CACHE/'E107/frozen_judge_plan'
    dest.mkdir(parents=True,exist_ok=True)
    dest.chmod(0o700)
    if (dest/'PLAN_SEAL.json').exists():
        verify(dest/'PLAN_SEAL.json',sha(dest/'PLAN_SEAL.json'))
        require(read(dest/'PLANS.PRIVATE.json')==plans,'unchanged frozen judge plan')
        return dest
    write(dest/'PLANS.PRIVATE.json',plans)
    (dest/'PLANS.PRIVATE.json').chmod(0o600)
    write(dest/'ORIGINAL_SOURCE_BINDINGS.PRIVATE.json',bindings)
    write(dest/'PLAN_SEAL.json',dict(experiment='E107',frozen_before_judging=True,source_inventory_sha256=sha(inv/'INVENTORY_SEAL.json'),
        n_items=4297,n_target_records=4496,missing_truth_items=10,native_rejudged=False,
        files={n:sha(dest/n) for n in ('PLANS.PRIVATE.json','ORIGINAL_SOURCE_BINDINGS.PRIVATE.json')}))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.parse_args()
    dest=freeze()
    print('E107 full source-target/rubric plan frozen CPU-only; seal SHA256 '+sha(dest/'PLAN_SEAL.json'))
