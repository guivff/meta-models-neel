"""CPU-only E95 timing scope, sequential reductions and final measured binding."""
import argparse
import copy
import hashlib
import math
from pathlib import Path
import sys
import tarfile
import worker87 as W
import timing95 as T
from contract import digest
sys.path.insert(0,str(W.ROOT))
from projects.g_agreement.e95.prepare_inventory import sample_strata


def index_for(inventory,template):
    strata={}
    for row in inventory['rows']:
        ri=row['row_index'];pseudos=[hashlib.sha256(f'E95:placebo:{ri}:{i}'.encode()).hexdigest()[:32] for i in range(15)]
        for reader in ('oracle','nla'):
            layers=row['oracle_layers'] if reader=='oracle' else [42]
            for arm in ('real','placebo'):
                ids=row['item_ids'] if arm=='real' or (reader=='oracle' and row['reuse_e87']) else pseudos
                strata[f'{ri}:{arm}:{reader}']=[f'{i}:{l}' for i in ids for l in layers]
    chosen=sample_strata(strata,.30,20261028);old=sample_strata(chosen,.25,20261028)
    return dict(template,reduction_step=inventory['reduction_step'],total_universe=sum(map(len,strata.values())),
        total_selected=sum(map(len,chosen.values())),total_old_rubric=sum(map(len,old.values())),
        strata_sizes={k:len(v) for k,v in strata.items()},selected=chosen,old_rubric_selected=old)


def source_archive(path):
    source=W.verify(W.HERE,'SOURCE_SEAL.json',W.sha(W.HERE/'SOURCE_SEAL.json'))
    deps=W.read(W.HERE/'DEPENDENCIES.json')
    for n,h in deps.items():W.require(W.sha(W.ROOT/n)==h,'dependency '+n)
    names=set(deps)|{str((W.HERE/n).relative_to(W.ROOT)) for n in source['files']}|{str((W.HERE/'SOURCE_SEAL.json').relative_to(W.ROOT))}
    with tarfile.open(path,'w:gz') as t:
        for n in sorted(names):t.add(W.ROOT/n,arcname=n,recursive=False)
    W.require(path.stat().st_size<=20*1024*1024,'source archive limit')


def prepare(inventory_path,index_path,input_dirs,out,cap_seconds=3600,previous=None):
    inventory=copy.deepcopy(W.read(inventory_path));index=W.read(index_path)
    W.require(inventory['experiment']==index['experiment']=='E95' and inventory['reduction_step']==index['reduction_step'],'matching scope')
    W.require(index_for(inventory,index)==index,'exact frozen seeded judge index')
    prior=None
    if previous:
        prior=W.read(previous)
        W.require(prior['status']=='REDUCTION_REQUIRED' and prior['forecast_cap_seconds']>144000 and
            prior['inventory_sha256']==W.sha(inventory_path) and prior['index_sha256']==W.sha(index_path) and
            prior['reduction_step']==inventory['reduction_step']<3,'only next registered reduction after measured excess')
        oldscope=previous.parent
        W.verify(oldscope,'SCOPE_SEAL.json',prior['scope_seal_sha256'])
        # Recheck the measured evidence instead of trusting an editable decision file.
        verified=evaluate(oldscope,[Path(p) for p in prior['profile_paths']],prior['prior_custody_seconds'])
        W.require(verified==prior,'verified reduction decision')
        step=inventory['reduction_step']+1;inventory['reduction_step']=step
        for row in inventory['rows']:
            if row['reuse_e87']:continue
            row['oracle_layers']=[36,44,56]
            if step>=2:
                row['item_ids']=row['item_ids'][:20];row['nla_position_counts']=row['nla_position_counts'][:20]
        if step==3:
            W.require(all(isinstance(r['probe_auroc'],(int,float)) and math.isfinite(r['probe_auroc'])
                for r in inventory['rows'] if not r['reuse_e87']),'step3 requires verified dev probe evidence; unknown is not eligible/ineligible')
            inventory['rows']=[r for r in inventory['rows'] if r['reuse_e87'] or r['probe_auroc']>=.90]
        index=index_for(inventory,index)
    else:W.require(inventory['reduction_step']==0,'start from full registered scope')
    W.require(type(cap_seconds)is int and 60<cap_seconds<=144000,'bounded operator timing cap')
    selected={r['row_index']:r for r in inventory['rows']};sources={}
    for d in input_dirs:
        d=Path(d);W.verify(d,'INPUT_SEAL.json',W.sha(d/'INPUT_SEAL.json'))
        p=W.read(d/'PLAN.json');xs=W.validate(W.read(d/'items.json'),p)
        W.require(len(p['row_indices'])==1,'one whole row per source package')
        r=p['row_indices'][0];W.require(r not in sources,'no duplicate row packages');sources[r]=(d,p,xs)
    W.require(set(selected)<=set(sources),'every final row supplied')
    out.mkdir(parents=True,exist_ok=False);records=[]
    for r,row in selected.items():
        d,p,xs=sources[r];p=copy.deepcopy(p)
        W.require(row['item_ids']==p['item_ids'][:len(row['item_ids'])],'only frozen first-item prefix')
        p['reduction_step']=inventory['reduction_step'];p['layers']=[20,36,44,56] if not p['reduction_step'] else [36,44,56]
        if p['reduction_step']>=2:
            for rr in p['row_roster']:
                if not rr['reuse_e87']:rr['item_ids']=rr['item_ids'][:20]
        xs=xs[:len(row['item_ids'])];p['item_ids']=row['item_ids'];W.validate(xs,p)
        W.require(p['row_roster'][r]['reuse_e87']==row['reuse_e87'] and p['row_roster'][r]['placebo_positions']==[row['nla_position_counts'][0]]*15,
            'inventory matches registered row/placebo structure')
        inp=out/f'row{r}'/'inputs';inp.mkdir(parents=True)
        W.write(inp/'PLAN.json',p);W.write(inp/'items.json',xs)
        records.append(dict(row=r,plan_sha256=W.sha(inp/'PLAN.json'),items_sha256=W.sha(inp/'items.json'),workload=T.workload(xs,p)))
    W.write(out/'ROW_INVENTORY.json',inventory);W.write(out/'JUDGE_INDEX.json',index)
    W.write(out/'PLAN_BINDINGS.json',records)
    W.write(out/'SCOPE_SEAL.json',dict(experiment='E95',reduction_step=inventory['reduction_step'],
        previous_decision_sha256=W.sha(previous) if previous else None,
        files={n:W.sha(out/n) for n in ['ROW_INVENTORY.json','JUDGE_INDEX.json','PLAN_BINDINGS.json']}))
    scope=W.sha(out/'SCOPE_SEAL.json');source_archive(out/'source.tar.gz');shards=[]
    for record in records:
        inp=out/f"row{record['row']}"/'inputs'
        W.write(inp/'STAGE_REQUEST.json',dict(experiment='E95',status='READY_E95_TIMING_ONLY',cap_seconds=cap_seconds,
            cumulative_cap_seconds=144000,account_gate_USD=1500,seed_seconds_per_batch={},scope_seal_sha256=scope,
            inventory_sha256=W.sha(out/'ROW_INVENTORY.json'),index_sha256=W.sha(out/'JUDGE_INDEX.json')))
        ih=W.seal(inp,'INPUT_SEAL.json',experiment='E95',timing_only=True)
        archive=inp.parent/'inputs.tar.gz'
        with tarfile.open(archive,'w:gz') as t:t.add(inp,arcname='inputs')
        W.require(archive.stat().st_size<=20*1024*1024,'input archive limit')
        shards.append(dict(record,input_archive=str(archive.resolve()),input_archive_sha256=W.sha(archive),input_seal_sha256=ih))
    request=dict(status='TIMING_ONLY_REQUIRES_I3_ADMISSION',source_archive=str((out/'source.tar.gz').resolve()),
        source_archive_sha256=W.sha(out/'source.tar.gz'),source_seal_sha256=W.sha(W.HERE/'SOURCE_SEAL.json'),
        scope_seal_sha256=scope,inventory_sha256=W.sha(out/'ROW_INVENTORY.json'),index_sha256=W.sha(out/'JUDGE_INDEX.json'),
        reduction_step=inventory['reduction_step'],shards=shards,full_launch_allowed=False,labels_on_pod=False)
    W.write(out/'REQUEST.json',request);return request


def evaluate(scope,profile_paths,prior_seconds=0,allow_representative=False):
    request=W.read(scope/'REQUEST.json');W.verify(scope,'SCOPE_SEAL.json',request['scope_seal_sha256'])
    W.require(isinstance(prior_seconds,(int,float)) and math.isfinite(prior_seconds) and prior_seconds>=0,'actual prior custody')
    rows={x['row']:x for x in request['shards']};measured={};caps=[]
    for path in profile_paths:
        path=Path(path);report=W.read(path);terminal=W.verify(path.parent,'OUTPUT_SEAL.json',W.sha(path.parent/'OUTPUT_SEAL.json'))
        W.require(terminal['status']=='PROFILE_ONLY' and terminal['synthetic'] is False and terminal['files'][path.name]==W.sha(path),'sealed actual timing, not synthetic')
        W.require(report['status']=='E95_TIMING_ONLY_NOT_SCIENCE' and len(report['row_indices'])==1,'one measured row')
        r=report['row_indices'][0];W.require(r in rows and r not in measured,'one profile per retained row');row=rows[r]
        for k in ['source_seal_sha256','scope_seal_sha256','inventory_sha256','index_sha256','reduction_step']:
            W.require(report[k]==terminal[k]==request[k],'exact source/final scope identity: '+k)
        W.require(report['input_seal_sha256']==row['input_seal_sha256'] and report['plan_sha256']==row['plan_sha256'] and
            report['items_sha256']==row['items_sha256'] and report['workload']==row['workload'],'exact whole-row workload')
        hardware=report['hardware'];W.require(report['gpu_type'] in ('H200','B200') and hardware['gpu_type']==report['gpu_type'] and
            report['gpu_type'] in hardware['actual_gpu_name'] and digest(report['assets_sha256']) and digest(hardware['stack_sha256']) and
            hardware['image_digest'].startswith('sha256:') and digest(hardware['image_digest'][7:]),'actual hardware/image/stack/assets identity')
        events=W.read(path.parent/'PHASE_TIMINGS.json')
        W.require(W.sha(path.parent/'PHASE_TIMINGS.json')==report['phase_timings_sha256'],'phase timing binding')
        native=report['native_phases'];W.require(set(native)==set(row['workload']),'complete phase coverage')
        for k,n in row['workload'].items():
            samples=[e['seconds'] for e in events if e['phase']==k and e['real'] and e['status']=='COMPLETE']
            W.require(samples and all(math.isfinite(v) and v>=0 for v in samples),'finite actual timings')
            v=native[k];W.require(v['full_batches']==n and v['measured_batches']==len(samples) and
                math.isclose(v['mean_seconds'],sum(samples)/len(samples),rel_tol=1e-12),'measured phase mean')
            W.require(len(samples)==(n if k.startswith('nla:placebo:') else min(3,n)),'fixed timing sample; all NLA placebo')
        stage=W.read(path.parent/'STAGING_RECEIPT.json');ass=W.read(path.parent/'ASSIGNMENT.json')
        W.require(W.sha(path.parent/'STAGING_RECEIPT.json')==report['staging_receipt_sha256'] and
            stage['assignment_sha256']==W.sha(path.parent/'ASSIGNMENT.json') and
            stage['pod_created_epoch']==ass['pod_created_epoch']==ass['custody_start_epoch'] and
            report['staging_seconds']==stage['worker_ready_epoch']-stage['pod_created_epoch']>=0,'creation-through-staging included')
        W.require(ass['gpu_type']==report['gpu_type'] and ass['image_digest']==hardware['image_digest'] and
            ass['stack_sha256']==hardware['stack_sha256'] and ass['assets_sha256']==report['assets_sha256'],'same assigned hardware/image/stack/assets')
        non_native=sum(e['seconds'] for e in events if e['phase'] not in native)
        W.require(math.isclose(non_native,report['non_native_seconds'],rel_tol=1e-12) and
            math.isfinite(report['measured_other_seconds']) and report['measured_other_seconds']>=0,'measured setup/capture/other')
        cap=math.ceil(1.25*(report['staging_seconds']+non_native+report['measured_other_seconds']+
            sum(v['full_batches']*v['mean_seconds'] for v in native.values())+60))
        W.require(cap==report['forecast_seconds'] and report['margin']==1.25,'padded forecast formula')
        measured[r]=path;caps.append(dict(row=r,cap_seconds=cap,profile_sha256=W.sha(path),output_seal_sha256=W.sha(path.parent/'OUTPUT_SEAL.json'),
            input_seal_sha256=row['input_seal_sha256'],plan_sha256=row['plan_sha256'],items_sha256=row['items_sha256'],
            gpu_type=report['gpu_type'],image_digest=hardware['image_digest'],stack_sha256=hardware['stack_sha256'],assets_sha256=report['assets_sha256']))
    W.require(set(measured)==set(rows) or (allow_representative and measured),
        'all retained rows, including reused-row NLA placebo, measured')
    total=sum(x['cap_seconds'] for x in caps)
    return dict(status=('VERIFIED_PROFILE_SUBSET_NOT_ADMISSION' if set(measured)!=set(rows) else
        'WITHIN_40H_REQUIRES_I3_GO' if total<=144000 else 'REDUCTION_REQUIRED'),
        reduction_step=request['reduction_step'],scope_seal_sha256=request['scope_seal_sha256'],inventory_sha256=request['inventory_sha256'],
        index_sha256=request['index_sha256'],source_seal_sha256=request['source_seal_sha256'],forecast_cap_seconds=total,projected_custody_seconds=total+prior_seconds,
        production_cap_seconds=total,prior_custody_seconds=prior_seconds,ceiling_seconds=144000,margin=1.25,
        profile_paths=[str(Path(p).resolve()) for p in profile_paths],shards=caps,production_admitted=False,
        next_reduction_step=request['reduction_step']+1 if total>144000 and request['reduction_step']<3 else None)


def bind(scope,profile_paths,out,prior_seconds=0):
    """Prepare measured inputs; only I-3 may promote HOLD to READY and re-seal."""
    decision=evaluate(scope,profile_paths,prior_seconds)
    W.require(decision['status']=='WITHIN_40H_REQUIRES_I3_GO','registered reductions required before production binding')
    request=W.read(scope/'REQUEST.json');out.mkdir(parents=True,exist_ok=False)
    W.write(out/'MEASURED_DECISION.json',decision);shards=[]
    reports={W.read(p)['row_indices'][0]:Path(p) for p in profile_paths}
    for entry in decision['shards']:
        row=entry['row'];report=W.read(reports[row]);old=scope/f'row{row}'/'inputs';inp=out/f'row{row}'/'inputs';inp.mkdir(parents=True)
        for n in ['PLAN.json','items.json']:(inp/n).write_bytes((old/n).read_bytes())
        seeds={}
        events=W.read(reports[row].parent/'PHASE_TIMINGS.json')
        for phase in ['oracle_setup','nla_setup','capture','placebo_build']:
            times=[e['seconds'] for e in events if e['phase']==phase]
            seeds[phase]=sum(times)/len(times) if times else 0
        for reader in ['oracle','nla']:
            times=[e['seconds'] for e in events if e['phase'].startswith(reader+':')]
            seeds[reader+'_native']=sum(times)/len(times) if times else 0
        binding=dict(entry,source_seal_sha256=request['source_seal_sha256'],scope_seal_sha256=request['scope_seal_sha256'],
            inventory_sha256=request['inventory_sha256'],index_sha256=request['index_sha256'],reduction_step=request['reduction_step'],
            measured_decision_sha256=W.sha(out/'MEASURED_DECISION.json'))
        W.write(inp/'STAGE_REQUEST.json',dict(experiment='E95',status='HOLD_I3_GLOBAL_ADMISSION',cap_seconds=entry['cap_seconds'],
            cumulative_cap_seconds=entry['cap_seconds']+prior_seconds,account_gate_USD=1500,seed_seconds_per_batch=seeds,timing95=binding))
        ih=W.seal(inp,'INPUT_SEAL.json',experiment='E95',measured_scope_sha256=request['scope_seal_sha256'])
        archive=inp.parent/'inputs.tar.gz'
        with tarfile.open(archive,'w:gz') as t:t.add(inp,arcname='inputs')
        shards.append(dict(binding,input_archive=str(archive.resolve()),input_archive_sha256=W.sha(archive),input_seal_sha256=ih))
    W.write(out/'REQUEST.json',dict(request,status='HOLD_I3_GLOBAL_ADMISSION',shards=shards,full_launch_allowed=False,
        measured_decision_sha256=W.sha(out/'MEASURED_DECISION.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('prepare')
    for n in ['inventory','index','out']:q.add_argument('--'+n,type=Path,required=True)
    q.add_argument('--inputs',type=Path,nargs='+',required=True);q.add_argument('--cap-seconds',type=int,default=3600);q.add_argument('--previous-decision',type=Path)
    q=sub.add_parser('evaluate');q.add_argument('--scope',type=Path,required=True);q.add_argument('--profiles',type=Path,nargs='+',required=True)
    q.add_argument('--prior-seconds',type=float,required=True);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('bind');q.add_argument('--scope',type=Path,required=True);q.add_argument('--profiles',type=Path,nargs='+',required=True)
    q.add_argument('--prior-seconds',type=float,required=True);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.cmd=='prepare':prepare(a.inventory,a.index,a.inputs,a.out,a.cap_seconds,a.previous_decision)
    elif a.cmd=='bind':bind(a.scope,a.profiles,a.out,a.prior_seconds)
    else:W.write(a.out,evaluate(a.scope,a.profiles,a.prior_seconds))
