"""CPU-only §220 amendment1 reprice. Read operational metadata, never job values."""
import argparse,copy,json,math,shutil,tarfile
from pathlib import Path
import numpy as np
import worker87 as W
import representative95 as R
import package95 as P
import admission95 as A

PRIOR=9924.6
OUTPUTS={1:'be5535aa423ed8b5cb5d1ebcc14b9c6e589ea81e5a605e1a0a2426c4e809472b',
2:'fc006d68347ad27259fc323ca163efa77b8132b4dd198c2243b94ad54aa6811f',
3:'5c80ccad5373cca5b30a5612a09e7ae8bbd728d0ada0f4e21759bf67e07d15eb',
4:'9e6b4850069d9663894d3a384e18606aa4329b16f99de44711ea532eefa48494',
5:'571c37ccbba627b0c942e217a30d37932faabeabb143137301beeed41129375e',
6:'59f7eceb5cf61d3a18f31dce749dedd054e947928697809365393d509ef28c62',
7:'97fbcbb2647ce0406c7f4ca82078a2548e22675a43a24de73080601a8e84e351'}
REUSE_SHA='9393a5aae4cd1bad2bd3433660e8c09a85acde6721ccbde659898f5f23395a09'


def observations(root,hardware):
    records=[]
    for i,expected in OUTPUTS.items():
        d=root/f's{i}'/'out';W.require(W.sha(d/'OUTPUT_SEAL.json')==expected,'verified original NO_FIT seal')
        seal=W.read(d/'OUTPUT_SEAL.json');data={}
        for n in ['PHASE_TIMINGS.json','FORECAST.json','ASSIGNMENT.json']:
            W.require(W.sha(d/n)==seal['files'][n],'sealed operational metadata '+n);data[n]=W.read(d/n)
        ass=data['ASSIGNMENT.json']
        W.require(all(ass[k]==v for k,v in hardware.items()),'same measured GPU/image/stack/assets')
        ev=data['PHASE_TIMINGS.json'];W.require(all(x['status']=='COMPLETE' for x in ev),'completed timing events')
        oracle=[x['seconds'] for x in ev if x['phase']=='oracle_native' and x['real']]
        mean=float(np.mean(oracle)) if oracle else None
        if oracle:W.require(math.isclose(mean,data['FORECAST.json']['seconds_per_batch']['oracle_native'],rel_tol=1e-12),'actual Oracle running mean')
        loads=[x['seconds'] for x in ev if x['phase']=='oracle_setup'];W.require(len(loads)==1,'one original model setup')
        records.append(dict(shard=i,profile_sha256=W.sha(d/'FORECAST.json'),output_seal_sha256=expected,
            phase_timings_sha256=W.sha(d/'PHASE_TIMINGS.json'),path=str((d/'FORECAST.json').resolve()),
            oracle_measured_batches=len(oracle),oracle_mean_seconds=mean,oracle_setup_seconds=loads[0]))
    return records


def price_book(original,records):
    b=copy.deepcopy(original);means=[r['oracle_mean_seconds'] for r in records if r['oracle_measured_batches']]
    W.require(means and all(math.isfinite(v) and v>0 for v in means),'actual post-load Oracle rates')
    maximum=max(means)
    for k in b['native']:
        if k.startswith('oracle:'):b['native'][k]=max(b['native'][k],maximum)
    # No complete production staging receipt exists: preserve the larger known own
    # timing staging and §217 clarification1's150s fallback, never infer it from job mtimes.
    staging=max(b['other']['staging'],150.)
    b['other']['staging']=staging
    b['other']['oracle_setup']=max(b['other']['oracle_setup'],max(r['oracle_setup_seconds'] for r in records))
    warm=['capture_warmup_discarded','nla_42_warmup_discarded']+[f'oracle_{l}_warmup_discarded' for l in (36,44,56)]
    tail=b['other']['nla_setup']+b['other']['measured_other']+sum(b['other'][k] for k in warm)
    for r in records:
        b['evidence'].append(copy.deepcopy(r))
        b['setup_profiles'].append(dict(profile_sha256=r['profile_sha256'],seconds=r['oracle_setup_seconds']+tail+staging,
            includes_staging=True,kind='observed Oracle head + frozen measured NLA/warmup tail + staging allowance'))
    b['maximum_measured_setup_seconds']=max(x['seconds'] for x in b['setup_profiles'])
    b['profile_set_sha256']=R.digest(sorted(b['evidence'],key=lambda x:x['profile_sha256']))
    b['amendment1_pricing']=dict(authority=A.AUTHORITY,oracle_rate_rule='maximum actual per-shard running mean; floor each original stratum at this value',
        maximum_observed_oracle_mean_seconds=maximum,setup_envelope_rule='max observed Oracle setup + own measured frozen NLA/warmup/overhead tail + staging',
        staging_seconds=staging,staging_policy='max known own timing staging and registered150s fallback; no mtime-derived staging',work_margin=A.MARGIN)
    return b


def build(release,observed,out):
    req=W.read(release);W.require(req['experiment']=='E95' and req['authority_commit'].startswith('aa8438c7'),'corrected-gate original release')
    book0=req['shards'][0]['timing95']['rate_book'];records=observations(observed,book0['hardware']);book=price_book(book0,records)
    reuse=W.HERE/'E87_REUSE_HARDWARE.json';W.require(W.sha(reuse)==REUSE_SHA,'I3 c113a227 reuse receipt')
    out.mkdir(parents=True,exist_ok=False);packets=[]
    for r in req['shards']:
        archive=Path(r['input_archive']);W.require(W.sha(archive)==r['input_archive_sha256'],'original READY public archive')
        folder=out/r['shard'];folder.mkdir()
        with tarfile.open(archive) as tar:tar.extractall(folder,filter='data')
        inp=folder/'inputs';W.verify(inp,'INPUT_SEAL.json',r['input_seal_sha256'])
        plan=W.read(inp/'PLAN.json');items=W.read(inp/'items.json');W.validate(items,plan)
        forecast=R.estimate(items,plan,book,margin=A.MARGIN)
        W.require(not forecast['missing_native_phases'],'full unchanged phase-width coverage')
        packets.append((r,inp,plan,items,forecast))
    total=sum(f['cap_seconds'] for r,inp,p,x,f in packets)
    W.require(total<=math.floor(A.CEILING-PRIOR),'54h cumulative budget including all original custody')
    rows=[ri for _,_,p,_,_ in packets for ri in p['row_indices']];W.require(len(rows)==len(set(rows))==72,'same72 whole rows')
    decision=dict(experiment='E95',amendment_authority=A.AUTHORITY,method=A.METHOD,ceiling_seconds=A.CEILING,prior_custody_seconds=PRIOR,
        production_cap_seconds=total,programme_projected_custody_seconds=total+PRIOR,remaining_headroom_seconds=A.CEILING-total-PRIOR,
        margin=A.MARGIN,rate_book=book,original_release_sha256=W.sha(release),corrected_gate_decision_sha256=req['corrected_gate_decision_sha256'],
        shards=[dict(shard=r['shard'],row_indices=p['row_indices'],forecast=f) for r,inp,p,x,f in packets],scientific_outputs_opened=False,GPU_calls=0)
    W.write(out/'REPRICED_DECISION.json',decision);P.source_archive(out/'source.tar.gz');source_sha=W.sha(W.HERE/'SOURCE_SEAL.json');new=[]
    scope_sha=R.digest(dict(inventory=req['inventory_sha256'],index=req['index_sha256'],decision=W.sha(out/'REPRICED_DECISION.json')))
    for r,inp,p,x,f in packets:
        limits=W.read(inp/'STAGE_REQUEST.json');m=limits['timing95']
        m.pop('ceiling_binding',None)
        m.update(scope_seal_sha256=scope_sha,amendment_binding=dict(authority=A.AUTHORITY,ceiling_seconds=A.CEILING,margin=A.MARGIN),method=A.METHOD,amendment_authority=A.AUTHORITY,margin=A.MARGIN,ceiling_seconds=A.CEILING,source_seal_sha256=source_sha,
            prior_custody_seconds=PRIOR,programme_projected_custody_seconds=total+PRIOR,forecast=f,cap_seconds=f['cap_seconds'],
            rate_book=book,profile_set_sha256=book['profile_set_sha256'],measured_decision_sha256=W.sha(out/'REPRICED_DECISION.json'))
        seeds=limits['seed_seconds_per_batch']
        for k in ('oracle_setup','nla_setup','capture'):seeds[k]=book['other'][k]
        for reader in ('oracle','nla'):
            ns={k:n for k,n in f['workload'].items() if k.startswith(reader+':')}
            seeds[reader+'_native']=sum(n*book['native'][k] for k,n in ns.items())/sum(ns.values()) if ns else 0
        limits.update(status='READY',cap_seconds=f['cap_seconds'],cumulative_cap_seconds=f['cap_seconds']+PRIOR)
        W.write(inp/'STAGE_REQUEST.json',limits,replace=True);(inp/'INPUT_SEAL.json').unlink();ih=W.seal(inp,'INPUT_SEAL.json',experiment='E95',amendment_authority=A.AUTHORITY)
        W.require(W.sha(inp/'PLAN.json')==m['plan_sha256'] and W.sha(inp/'items.json')==m['items_sha256'],'original plan/items unchanged')
        archive=inp.parent/'inputs.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:tar.add(inp,arcname='inputs')
        new.append(dict(shard=r['shard'],row_indices=p['row_indices'],mode=p['mode'],cap_seconds=f['cap_seconds'],input_archive=str(archive.resolve()),input_archive_sha256=W.sha(archive),input_seal_sha256=ih,timing95=m,
            reuse_hardware_sha256=REUSE_SHA if p['mode']=='nla_placebo_only' else None))
    result=dict(experiment='E95',authority=A.AUTHORITY,status='ALL8_READY_PENDING_I3_RE_RELEASE',full_launch_allowed=False,source_archive=str((out/'source.tar.gz').resolve()),
        source_archive_sha256=W.sha(out/'source.tar.gz'),source_seal_sha256=source_sha,entrypoint='results/g_agreement/understand/e87/admission95.py',
        ceiling_seconds=A.CEILING,prior_custody_seconds=PRIOR,production_cap_seconds=total,programme_projected_custody_seconds=total+PRIOR,work_margin=A.MARGIN,
        corrected_gate_decision_sha256=req['corrected_gate_decision_sha256'],corrected_analysis_seal_sha256=req['corrected_analysis_seal_sha256'],
        corrected_depth_seal_sha256=req['corrected_depth_seal_sha256'],scope_seal_sha256=scope_sha,inventory_sha256=req['inventory_sha256'],index_sha256=req['index_sha256'],
        launch_cutoff=req['launch_cutoff'],original_release_sha256=W.sha(release),
        reuse_hardware_relative='results/g_agreement/understand/e87/E87_REUSE_HARDWARE.json',reuse_hardware_sha256=REUSE_SHA,shards=new)
    W.write(out/'REQUEST.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('release','observed','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=build(a.release,a.observed,a.out);print(json.dumps({k:r[k] for k in ['status','production_cap_seconds','programme_projected_custody_seconds','source_archive_sha256']}))
