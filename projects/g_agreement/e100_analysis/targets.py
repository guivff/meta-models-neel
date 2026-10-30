"""Build sealed CPU donor targets from input metadata only; no reader outputs."""
import argparse
from pathlib import Path
from adapter import core, read, write, sha, require
from rules import ROWS
VECTOR_HASH='dd1ff8dc2ec742e001d8d0e59b700b33fa904680d420d9fb9350088f752317b0'
PLAN_HASH='7945c9d58f5d67ed12954e8a7f52c8f06b61cabe06b5697bf62e42af37eef0fb'

def mapped(join,banks,plan):
    out=[]; identities=core.unique(join)
    for x in join:
        require(x['row'] in ROWS,'registered row')
        bank=banks[x['bank']]; donor=bank[x['donor_source_item_id']]; source=bank[x['source_item_id']]
        require(source['split']==donor['split']=='test','sealed test items only')
        require(source['row_id']==donor['row_id']==x['row'],'same row')
        require(source['label']==x['true_label'] and donor['label']==x['donor_label'] and source['label']!=donor['label'],'opposite registered labels')
        require(identities[x['donor_id']]['source_item_id']==donor['id'],'opaque donor join')
        if x['bank']=='E57':
            pair=plan[donor['id']]
            require(len(pair)==2,'frozen donor-family judge values')
            values=dict(A=pair[0],B=pair[1])
        else:
            groups={label:{d['value'] for d in bank.values() if d['row_id']==x['row'] and d['label']==label} for label in (1,0)}
            require(all(len(v)==1 for v in groups.values()),'unambiguous registered binary values')
            values=dict(A=next(iter(groups[1])),B=next(iter(groups[0])))
        out.append(dict(id=x['id'],row=x['row'],source_item_id=source['id'],donor_id=x['donor_id'],donor_source_item_id=donor['id'],property=x['row'],values=values,target='A' if donor['label']==1 else 'B'))
    require(len(out)==672 and all(sum(t['row']==r for t in out)==84 for r in ROWS),'full all84 grid')
    return out

def build(vector,plan,out):
    vector,plan,out=Path(vector),Path(plan),Path(out)
    core.verify(vector/'VECTOR_SEAL.json',VECTOR_HASH)
    require(sha(plan)==PLAN_HASH,'original E57 judge plan')
    sources=read(vector/'cpu_only/SOURCES.json');banks={};hashes={}
    for bank,s in sources['banks'].items():
        p=Path(s['metadata_path']);require(sha(p)==s['metadata_sha256'],'sealed bank metadata')
        banks[bank]=core.unique(read(p));hashes[str(p)]=sha(p)
    join=read(vector/'cpu_only/JOIN.DO_NOT_STAGE.json')
    targets=mapped(join,banks,read(plan)['judge_values'])
    out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    write(out/'TARGETS.json',targets);(out/'TARGETS.json').chmod(0o600)
    write(out/'PROVENANCE.json',dict(vector_seal=str(vector/'VECTOR_SEAL.json'),vector_sha256=VECTOR_HASH,source_metadata=hashes,e57_plan=str(plan),e57_plan_sha256=PLAN_HASH,donor_pair_policy='Use donor source item family, A=label1 and B=label0, exact frozen E57 judge_values; E56/E59 unique sealed metadata values per label.',E100_readouts_opened=False))
    core.seal(out,'TARGET_SEAL.json',experiment='E100',labels_cpu_only=True,mapping='donor_family_registered_values',records=len(targets),vector_sha256=VECTOR_HASH)
    return sha(out/'TARGET_SEAL.json')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--vectors',required=True);p.add_argument('--e57-plan',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    print(build(a.vectors,a.e57_plan,a.out))
