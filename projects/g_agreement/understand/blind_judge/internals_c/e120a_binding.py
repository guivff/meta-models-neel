"""CPU-only original readout/row.id/seven-field-code sibling pointers for I2/WM2."""
from .transport import ROOT,HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def assemble(joins,judgments,native_ref,n=800):
    by={r['id']:(i,r) for i,r in enumerate(judgments)}
    require(len(joins)==len(judgments)==len(by)==n and {j['id'] for j in joins}==set(by), 'full original ID census, never order join')
    out=[]
    def ref(s,m,k):return dict(seal_index=s,member=m,keys=k)
    for j in joins:
        i,r=by[j['id']]
        require(r['kind']=='eval85' and r['status'] in ('KEPT','UNPARSEABLE','REFUSED') and (r['code'] is None)==(r['status']!='KEPT'), 'literal original code/null')
        p=j['source_ref'];require(p['seal']==native_ref['seal'] and p['sha256']==native_ref['sha256'] and p['keys'][-1]=='text', 'exact original whole native source')
        keys=p['keys'][:-1]
        out.append(dict(id=j['id'],item_id=j['item_id'],block=j['block'],judgment_id=j['id'],fields=dict(
            item_id=ref(2,p['member'],keys+['item_id']),block=ref(2,p['member'],keys+['source_layer']),text=ref(2,p['member'],p['keys']),
            code=ref(0,'JUDGMENTS.json',[i,'code']),judgment_id=ref(0,'JUDGMENTS.json',[i,'id']))))
    return out


def build():
    for n,h in read(HERE/'E120a_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published original pointer binding source')
    p=CACHE/'E120/late_layers_judging/outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));require(s['experiment']=='E120' and s['status']=='COMPLETE' and s['route_verified'] is True,'complete new a phase')
    u=CACHE/'E120/late_layers_units/UNIT_SEAL.json';verify(u,sha(u));native=read(u.parent/'CUSTODY.json')['source_seals'][0];verify(native['seal'],native['sha256'])
    rows=assemble(read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(p.parent/'JUDGMENTS.json'),native)
    d=CACHE/'E120/part_a_analysis_handoff';d.mkdir(exist_ok=True);sources=[dict(seal=str(p),sha256=sha(p)),dict(seal=str(u),sha256=sha(u)),native]
    if(d/'HANDOFF_SEAL.json').exists():
        verify(d/'HANDOFF_SEAL.json',sha(d/'HANDOFF_SEAL.json'));require(read(d/'MEASUREMENTS.PRIVATE.json')==rows,'same immutable owner handoff');return d
    write(d/'MEASUREMENTS.PRIVATE.json',rows);write(d/'SOURCE_SEALS.PRIVATE.json',sources)
    write(d/'HANDOFF_SEAL.json',dict(experiment='E120',part='a',status='COMPLETE_JUDGING_POINTERS_FOR_OWNER_SPEC',n=800,analysis_run=False,owner_final_plan_and_custody_spec_required=True,files={n:sha(d/n) for n in ('MEASUREMENTS.PRIVATE.json','SOURCE_SEALS.PRIVATE.json')}))
    return d


if __name__=='__main__':print('E120a owner pointer handoff '+sha(build()/'HANDOFF_SEAL.json'))
