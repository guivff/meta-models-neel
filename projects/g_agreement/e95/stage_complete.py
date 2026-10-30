"""E95 note5: admit whole reader stages from the closed Track Q inventory only."""
from pathlib import Path
from projects.g_agreement.readerbench.io import read,sha,verify
from projects.g_agreement.readerbench.scoring import require

INVENTORY_SHA='95c3e0f1d8e0cc1492b4f19a534daca49274fcb14bb11217ceb9b9d079d14a68'


def stage_rows(inventory):
    require(inventory['kind']=='E95_STAGE_ROW_INVENTORY_NOTE4' and inventory['pending']==[],'closed stage inventory only')
    allowed={'oracle':set(),'nla':set()};seen=set()
    for shard in inventory['shards']:
        rows=set(shard['row_indices']);require(len(rows)==len(shard['row_indices']) and not seen&rows,'unique frozen shard rows');seen|=rows
        for reader in allowed:
            complete=shard[reader+'_stage_complete'];require(type(complete)is bool,'explicit whole reader stage disposition')
            if complete:
                for arm in ('real','placebo'):
                    require(shard['stages'][reader+'_'+arm]['status']=='complete','both arms complete; no partial reader reuse')
                allowed[reader]|=rows
    require(len(allowed['oracle'])==62 and len(allowed['nla'])==44,'final registered coverage62 Oracle/44 NLA')
    return allowed


def eligible_ids(expected,allowed):
    result=set()
    for gid,(stratum,unit)in expected.items():
        row,arm,reader=stratum.split(':')
        require(reader in allowed and arm in ('real','placebo'),'original item/layer/reader/arm identity')
        if int(row)in allowed[reader]:result.add(gid)
    return result


def admission(spec,expected):
    require(spec['stage_inventory_sha256']==INVENTORY_SHA==sha(spec['stage_inventory']),'exact closed inventory be185a543')
    root=Path(__file__).resolve().parents[3]
    base=root/'results/g_agreement/understand/e95/deviation2'
    require(sha(spec['inventory'])==sha(base/'ROW_INVENTORY.json') and sha(spec['index'])==sha(base/'JUDGE_INDEX.json'),
            'frozen step3 rows/item-layer sample, no outcome-based reselection')
    inventory=read(spec['stage_inventory']);allowed=stage_rows(inventory)
    needed={x['shard']:x for x in inventory['shards']if x['oracle_stage_complete']or x['nla_stage_complete']}
    require(set(spec['stage_sources'])==set(needed),'all and only stage-complete source shards')
    for name,original in needed.items():
        source=spec['stage_sources'][name];manifest=Path(source['manifest'])
        require(sha(manifest)==original['stage_manifest_sha256'],'original TrackQ stage manifest')
        m=read(manifest)
        require(m['shard']==name and m['output_seal_sha256']==original['output_seal_sha256']
                and all(m[r+'_stage_complete']==original[r+'_stage_complete']for r in allowed),'original reader disposition/output identity')
        verify(source['stage_seal'],original['stage_seal_sha256'])
        require(sha(source['output_seal'])==original['output_seal_sha256'],'original archived output identity')
    return eligible_ids(expected,allowed)
