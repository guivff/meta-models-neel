"""Exact native readout-ID -> original blind judgment-ID/code pointers, CPU only."""
from .runner import CACHE
from .transport import ROOT,HERE
from .e128_channel import RUBRIC_SHA
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def project(joins,rows,phase,n=672):
    by={r['id']:(i,r) for i,r in enumerate(rows)}
    require(len(joins)==len(rows)==len(by)==n and len({j['readout_id'] for j in joins})==n and {j['id'] for j in joins}==set(by),'full unique original dispatch source IDs')
    out={}
    for j in joins:
        i,r=by[j['id']];require(r['kind']=='original104' and (r['code'] is None)==(r['status']!='KEPT'),'literal original code/null')
        if r['code'] is not None:require(r['code']['id']==j['id'],'exact original blind code identity')
        out[j['readout_id']]=dict(judgment_id=j['id'],status=r['status'],code_source=dict(seal=str(phase),sha256=sha(phase) if hasattr(phase,'exists') else 'test',member='JUDGMENTS.json',keys=[i,'code']),text_source=j['source_ref'])
    return out


def build():
    for n,h in read(HERE/'E128_BINDING_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published binding source')
    p=CACHE/'E128/original104_judging/outputs/JUDGMENT_SEAL.json';v=verify(p,sha(p));require(v['status']=='COMPLETE' and v['experiment']=='E128' and v['route_verified'] is True,'full bank before binding')
    u=CACHE/'E128/original104_units/UNIT_SEAL.json';verify(u,sha(u))
    out=project(read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(p.parent/'JUDGMENTS.json'),p)
    d=CACHE/'E128/readout_code_binding';d.mkdir(exist_ok=True);write(d/'READOUT_CODE_BINDINGS.PRIVATE.json',out)
    write(d/'JUDGMENT_SEAL.json',dict(experiment='E128',status='COMPLETE',n=672,route_verified=True,labels_cpu_only=True,rubric_sha256=RUBRIC_SHA,judging_cap_usd=3,source_seals=[dict(seal=str(p),sha256=sha(p)),dict(seal=str(u),sha256=sha(u))],files={'READOUT_CODE_BINDINGS.PRIVATE.json':sha(d/'READOUT_CODE_BINDINGS.PRIVATE.json')}))
    return d/'JUDGMENT_SEAL.json'


if __name__=='__main__':print('E128 keyed binding '+sha(build()))
