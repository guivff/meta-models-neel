"""Source-pointer projection for E116/E120c owners; no scorer or analysis calls."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def assemble(bank,joins,judgments,phase_ref,unit_ref,native_ref,cohort_ref=None):
    n=752 if bank=='E116' else 800
    js={r['id']:(i,r) for i,r in enumerate(judgments)}
    require(len(joins)==len(js)==len(judgments)==n and {j['id'] for j in joins}==set(js),'complete exact source IDs before projection')
    sources=[phase_ref,unit_ref,native_ref]+([cohort_ref] if cohort_ref else [])
    def ref(s,m,k):return dict(seal_index=s,member=m,keys=k)
    out=[];items={}
    for i,j in enumerate(joins):
        q,r=js[j['id']];require(r['status'] in ('KEPT','UNPARSEABLE','REFUSED') and (r['code'] is None)==(r['status']!='KEPT'),'terminal missingness remains explicit null')
        if bank=='E116':
            require(r['kind']=='choice_hit' and (r['code'] is None or type(r['code']) is bool),'original hit bool/null')
            cell=dict(source_id=ref(1,'SOURCE_POINTERS.PRIVATE.json',[i,'item_id']),block=ref(1,'SOURCE_POINTERS.PRIVATE.json',[i,'block']),hit=ref(0,'JUDGMENTS.json',[q,'code']))
            x=items.setdefault(j['item_id'],dict(id=j['item_id'],source_id=ref(3,'COHORT.PRIVATE.json',[j['cohort_index'],'id']),choice=ref(3,'COHORT.PRIVATE.json',[j['cohort_index'],'choice']),blocks={}))
            require(str(j['block']) not in x['blocks'],'no repeated block');x['blocks'][str(j['block'])]=cell
        else:
            require(bank=='E120' and r['kind']=='eval85','only original judge205 codes')
            native=j['source_ref'];require(native['seal']==native_ref['seal'],'exact original native root')
            path=native['keys'][:-1]
            fields=dict(item_id=ref(2,native['member'],path+['item_id']),block=ref(2,native['member'],path+['source_layer']),arm=ref(2,native['member'],path+['condition']),text=ref(2,native['member'],native['keys']),code=ref(0,'JUDGMENTS.json',[q,'code']),judgment_id=ref(0,'JUDGMENTS.json',[q,'id']))
            out.append(dict(id=j['id'],item_id=j['item_id'],arm=j['arm'],judgment_id=j['id'],fields=fields))
    if bank=='E116':
        require(len(items)==376 and all(set(x['blocks'])=={'52','60'} for x in items.values()),'full376 two-block owner input')
        out=sorted(items.values(),key=lambda x:x['id'])
    return out,sources


def build(bank):
    for n,h in read(HERE/'LATE_BANK_HANDOFF_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published pointer projection source')
    phase_name='chosen_member_hit_judging' if bank=='E116' else 'targeted_sham_judging'
    unit_name='chosen_member_hit_units' if bank=='E116' else 'targeted_sham_units'
    p=CACHE/bank/phase_name/'outputs/JUDGMENT_SEAL.json';ps=verify(p,sha(p));require(ps['status']=='COMPLETE' and ps['experiment']==bank and ps['route_verified'] is True,'complete route verified phase')
    u=CACHE/bank/unit_name/'UNIT_SEAL.json';verify(u,sha(u));custody=read(u.parent/'CUSTODY.json');native=custody['source_seals'][0]
    refs=lambda x:dict(seal=str(x),sha256=sha(x))
    cohort=custody['source_seals'][2] if bank=='E116' else None
    rows,sources=assemble(bank,read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(p.parent/'JUDGMENTS.json'),refs(p),refs(u),native,cohort)
    for r in sources:verify(r['seal'],r['sha256'])
    d=CACHE/bank/'analysis_handoff';d.mkdir(exist_ok=True);d.chmod(0o700)
    if(d/'HANDOFF_SEAL.json').exists():
        verify(d/'HANDOFF_SEAL.json',sha(d/'HANDOFF_SEAL.json'));require(read(d/'MEASUREMENTS.PRIVATE.json')==rows,'immutable source handoff');return d
    write(d/'MEASUREMENTS.PRIVATE.json',rows);write(d/'SOURCE_SEALS.PRIVATE.json',sources)
    write(d/'HANDOFF_SEAL.json',dict(experiment=bank,status='COMPLETE_JUDGING_POINTERS_FOR_OWNER_SPEC',analysis_run=False,n_measurements=len(rows),files={n:sha(d/n) for n in ('MEASUREMENTS.PRIVATE.json','SOURCE_SEALS.PRIVATE.json')}))
    return d


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',choices=['E116','E120'],required=True);a=p.parse_args();print('CPU owner handoff '+sha(build(a.bank)/'HANDOFF_SEAL.json'))
