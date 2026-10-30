"""CPU-only per-phase native-ID binding; original codes/nulls never rewritten."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def project(joins,rows,source,n):
    by={r['id']:(i,r) for i,r in enumerate(rows)}
    require(len(joins)==len(rows)==len(by)==n and len({j['native_id'] for j in joins})==n and {j['id'] for j in joins}==set(by),'full original ID join, never file order')
    out={};missing=[]
    for j in joins:
        i,r=by[j['id']]
        require(r['kind']=='original57' and r['status'] in ('KEPT','UNPARSEABLE','REFUSED') and (r['code'] is None)==(r['status']!='KEPT'),'literal terminal code/null')
        if r['code'] is not None:require(r['code']['id']==j['id'],'exact original blind code ID')
        ref=dict(**source,member='JUDGMENTS.json',keys=[i,'code'])
        x=dict(j,judgment_id=j['id'],status=r['status'],code_source=ref,judgment_row_source=dict(**source,member='JUDGMENTS.json',keys=[i]),request_id=r['request_id'],response_sha256=r['response_sha256'])
        if r['code'] is None:
            x['missing_sentinel_index']=len(missing)
            missing.append(dict(id=r['id'],original_code=ref,terminal_status=r['status'],code=dict(id=r['id'],category='UNPARSEABLE',values=[],evidence='')))
        out[j['native_id']]=x
    return out,missing


def build(part):
    for n,h in read(HERE/'E117_ADMIN_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published CPU-only source pointer formatter')
    phase='targeted_sham' if part=='c' else 'native';n=672 if part=='c' else 3024
    p=CACHE/'E117'/(phase+'_judging')/'outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));require(s['status']=='COMPLETE' and s['experiment']=='E117' and s['route_verified'] is True,'complete original phase before handoff')
    u=CACHE/'E117'/(phase+'_units')/'UNIT_SEAL.json';verify(u,sha(u))
    refs,missing=project(read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(p.parent/'JUDGMENTS.json'),dict(seal=str(p),sha256=sha(p)),n)
    d=CACHE/'E117'/(phase+'_code_binding');d.mkdir(exist_ok=True);d.chmod(0o700)
    final=d/'HANDOFF_SEAL.json'
    if final.exists():verify(final,sha(final));require(read(d/'READOUT_CODE_BINDINGS.PRIVATE.json')==refs,'immutable per-phase original code references');return d
    write(d/'READOUT_CODE_BINDINGS.PRIVATE.json',refs);write(d/'MISSING_SENTINELS.PRIVATE.json',missing)
    write(final,dict(experiment='E117',part=part,status='COMPLETE_JUDGING_POINTERS_FOR_OWNER_SPEC',n=n,analysis_run=False,route_verified=True,labels_cpu_only=True,source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (p,u)],files={n:sha(d/n) for n in ['READOUT_CODE_BINDINGS.PRIVATE.json','MISSING_SENTINELS.PRIVATE.json']}))
    return d


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--part',choices=['c','main'],required=True);a=p.parse_args();print('E117 source-only handoff '+sha(build(a.part)/'HANDOFF_SEAL.json'))
