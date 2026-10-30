"""E95 measured phase/width transfer, ordered reductions and HOLD-only multi-row inputs.

Native reader and capture implementations are reused unchanged. This is a forecast,
not a guarantee about row-dependent generation time or permission to allocate.
"""
import argparse
import ast
import copy
import hashlib
import json
import math
import tarfile
from collections import Counter
from pathlib import Path
import worker87 as W
import timing95 as T
import package95 as P

METHOD = 'REPRESENTATIVE_PHASE_WIDTH_V2_SECTION217'
CEILING = 144000
ELIGIBILITY_PATH = 'results/g_agreement/understand/e95/STATEMENT_SCORE_ELIGIBILITY.json'
# §220's actual shared REOPEN proof; an arbitrary CLI ceiling is never accepted.
REOPEN_GATE_SEAL_SHA = '40755189c07ed814972574bd1454a046b0f55fd12731902696e403927e18f7df'
REOPEN_GATE_DECISION_SHA = '3161726c3a3149decc4612e39c00d3b0cefc67104433612f93d662b68f92c5c8'
STEP3_ROSTER_SHA = 'affa8fbcf37cc62ceadeaa0751312f24579ac1c884d2e757fc2256e457884703'
REOPEN_BINDING = dict(authority='§220 / 9c56f1a5',deviation=2,ceiling_seconds=169200,
    gate_seal_sha256=REOPEN_GATE_SEAL_SHA,gate_decision_sha256=REOPEN_GATE_DECISION_SHA,
    gate_status='REOPEN_E95_DEVIATION_2',step3_roster_sha256=STEP3_ROSTER_SHA)


def registered_ceiling(binding=None):
    if binding is None:return CEILING
    W.require(binding==REOPEN_BINDING,'registered sealed §220 ceiling binding')
    return 169200


def reopen_binding(path,expected_sha):
    W.require(expected_sha==REOPEN_GATE_SEAL_SHA,'registered §220 gate seal')
    seal=W.verify(path.parent,path.name,expected_sha)
    W.require(seal['experiment']=='E95' and seal['files']['GATE_DECISION.json']==REOPEN_GATE_DECISION_SHA,
              'registered §220 gate decision')
    gate=W.read(path.parent/'GATE_DECISION.json')
    W.require(gate['status']=='REOPEN_E95_DEVIATION_2' and gate['conditional_ceiling_gpu_hours']==47,
              'E95 gate must be REOPEN')
    return copy.deepcopy(REOPEN_BINDING)


def roster_digest(inv):
    return digest([{k:r[k] for k in ('row_index','item_ids','oracle_layers','nla_position_counts','reuse_e87')}
                   for r in inv['rows']])



def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def measurement_ast(source):
    tree=ast.parse(source)
    tree.body=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name!='validate_production']
    return hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()


def verify_row_sources(scope):
    request=W.read(scope/'REQUEST.json');W.verify(scope,'SCOPE_SEAL.json',request['scope_seal_sha256'])
    bound={r['row']:r for r in W.read(scope/'PLAN_BINDINGS.json')}
    declared={r['row']:r for r in request['shards']}
    inventory=W.read(scope/'ROW_INVENTORY.json')
    W.require(set(bound)==set(declared)=={r['row_index'] for r in inventory['rows']},'complete frozen row sources')
    for ri,entry in bound.items():
        inp=scope/f'row{ri}'/'inputs';W.verify(inp,'INPUT_SEAL.json',declared[ri]['input_seal_sha256'])
        W.require(W.sha(inp/'PLAN.json')==entry['plan_sha256'] and
            W.sha(inp/'items.json')==entry['items_sha256'],'unmeasured row source changed')


def dependency_extension(old,current):
    W.require(set(old)<=set(current) and all(current[n]==h for n,h in old.items()),
              'measured dependency pins changed')
    added=set(current)-set(old)
    W.require(added<={ELIGIBILITY_PATH},'unreviewed extra runtime dependency')
    return {n:current[n] for n in sorted(added)}


def same_runner(scope):
    """Prove original measured scientific code equals the new admission-only package."""
    request=W.read(scope/'REQUEST.json');archive=Path(request['source_archive'])
    W.require(W.sha(archive)==request['source_archive_sha256'],'original timing source archive')
    prefix=str(W.HERE.relative_to(W.ROOT))+'/'
    with tarfile.open(archive) as tar:
        def data(name):return tar.extractfile(name).read()
        seal_bytes=data(prefix+'SOURCE_SEAL.json')
        W.require(hashlib.sha256(seal_bytes).hexdigest()==request['source_seal_sha256'],'measured source seal')
        old=json.loads(seal_bytes)
        for name,h in old['files'].items():
            W.require(hashlib.sha256(data(prefix+name)).hexdigest()==h,'original source member')
            if name=='timing95.py':
                W.require(measurement_ast(data(prefix+name).decode())==measurement_ast((W.HERE/name).read_text()),
                          'measured timing/capture path changed')
            elif name not in ('package95.py','representative95.py','DEPENDENCIES.json') and not name.startswith('test_'):
                W.require(W.sha(W.HERE/name)==h,'measured scientific source changed: '+name)
        deps=json.loads(data(prefix+'DEPENDENCIES.json'))
        current=W.read(W.HERE/'DEPENDENCIES.json');added=dependency_extension(deps,current)
        for name,h in current.items():W.require(W.sha(W.ROOT/name)==h,'measured dependency changed: '+name)
    return dict(measured_source_sha256=request['source_seal_sha256'],
                runtime_source_sha256=W.sha(W.HERE/'SOURCE_SEAL.json'),
                measurement_ast_sha256=measurement_ast((W.HERE/'timing95.py').read_text()),
                allowed_changes=['package95 CPU admission','timing95.validate_production','tests/new admission module'],
                added_pinned_cpu_metadata=added,
                scientific_code_unchanged=True)


def rates(scope,paths):
    P.evaluate(scope,paths,0,allow_representative=True) # Original full validation, except row coverage.
    native={};other={};evidence=[];hardware=None;lengths=[];setups=[]
    for path in map(Path,paths):
        r=W.read(path);identity=dict(gpu_type=r['gpu_type'],image_digest=r['hardware']['image_digest'],
            stack_sha256=r['hardware']['stack_sha256'],assets_sha256=r['assets_sha256'])
        W.require(hardware is None or identity==hardware,'representative profiles must share actual runtime')
        hardware=identity
        for ri in r['row_indices']:
            lengths.extend(len(x['ids']) for x in W.read(scope/f'row{ri}'/'inputs/items.json'))
        for phase,v in r['native_phases'].items():native[phase]=max(native.get(phase,0),v['mean_seconds'])
        events=W.read(path.parent/'PHASE_TIMINGS.json');phase={}
        for e in events:
            W.require(e['status']=='COMPLETE','completed timing events')
            if e['phase'] not in r['native_phases']:phase.setdefault(e['phase'],[]).append(e['seconds'])
        for key,values in phase.items():
            # Capture per item; RNG construction per global row traversed. Other phases once per pod.
            value=max(values) if key=='capture' else sum(values)
            if key=='placebo_build':value/=max(r['row_indices'])+1
            other[key]=max(other.get(key,0),value)
        setups.append(dict(profile_sha256=W.sha(path),seconds=r['staging_seconds']+r['measured_other_seconds']+
            sum(sum(v) for k,v in phase.items() if k not in ('capture','placebo_build'))))
        other['staging']=max(other.get('staging',0),r['staging_seconds'])
        other['measured_other']=max(other.get('measured_other',0),r['measured_other_seconds'])
        evidence.append(dict(path=str(path.resolve()),profile_sha256=W.sha(path),
            output_seal_sha256=W.sha(path.parent/'OUTPUT_SEAL.json'),row_indices=r['row_indices']))
    return dict(native=native,other=other,hardware=hardware,evidence=evidence,setup_profiles=setups,
                maximum_measured_setup_seconds=max(x['seconds'] for x in setups),
                measured_capture_prompt_tokens=dict(min=min(lengths),max=max(lengths),items=len(lengths)),
                profile_set_sha256=digest(sorted(evidence,key=lambda x:x['profile_sha256'])))


def evidence_values(inventory,entry):
    if entry is None:return
    p=Path(entry['seal']);seal=W.verify(p.parent,p.name,entry['sha256'])
    W.require(seal['metric']=='dev_probe_auroc' and 'DEV_PROBES.json' in seal['files'],'dev-only quantitative evidence')
    sources=seal['source_seals'];verified=[W.verify(Path(x['seal']).parent,Path(x['seal']).name,x['sha256']) for x in sources]
    rows={r['row_index']:r for r in inventory['rows']};seen=set()
    for record in W.read(p.parent/'DEV_PROBES.json'):
        ri=record['row_index'];W.require(ri in rows and ri not in seen,'one dev evidence record per known row');seen.add(ri)
        row=rows[ri];W.require(record['bank']==row['bank'] and record['row']==row['row'] and record['split']=='dev','dev evidence row identity')
        ref=record['source_ref'];ix=ref['seal_index'];W.require(ref['member'] in verified[ix]['files'],'sealed dev metric member')
        value=W.read(Path(sources[ix]['seal']).parent/ref['member'])
        for key in ref['keys']:value=value[key]
        W.require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=1,'numeric dev AUROC')
        W.require(row['probe_auroc'] is None or math.isclose(row['probe_auroc'],value),'dev evidence contradicts frozen value')
        row['probe_auroc']=value


def reduce_inventory(base,step):
    inv=copy.deepcopy(base);inv['reduction_step']=step
    for row in inv['rows']:
        if row['reuse_e87']:continue
        if step:row['oracle_layers']=[36,44,56]
        if step>=2:
            row['item_ids']=row['item_ids'][:20];row['nla_position_counts']=row['nla_position_counts'][:20]
    if step==3:
        unknown=[r['row_index'] for r in inv['rows'] if not r['reuse_e87'] and
                 (type(r['probe_auroc']) not in (int,float) or not math.isfinite(r['probe_auroc']) or not 0<=r['probe_auroc']<=1)]
        if unknown:return inv,unknown
        inv['rows']=[r for r in inv['rows'] if r['reuse_e87'] or r['probe_auroc']>=.9]
    return inv,[]


def row_inputs(scope,row,step):
    old=scope/f"row{row['row_index']}"/'inputs'
    p=copy.deepcopy(W.read(old/'PLAN.json'));xs=W.read(old/'items.json')[:len(row['item_ids'])]
    p['reduction_step']=step;p['layers']=[20,36,44,56] if step==0 else [36,44,56]
    if step>=2:
        for entry in p['row_roster']:
            if not entry['reuse_e87']:entry['item_ids']=entry['item_ids'][:20]
    p['item_ids']=[x['id'] for x in xs];W.require(p['item_ids']==row['item_ids'],'frozen item prefix')
    W.validate(xs,p);return xs,p


def aggregate_workload(items,plan):
    counts=Counter()
    for ri in plan['row_indices']:
        p=copy.deepcopy(plan);p['row_indices']=[ri]
        xs=[x for x in items if x['global_index']//30==ri];p['item_ids']=[x['id'] for x in xs]
        counts.update(T.workload(xs,p))
    return dict(counts)


def estimate(items,plan,book,margin=1.25):
    W.require(all(type(v) in (int,float) and math.isfinite(v) and v>=0
        for v in list(book['native'].values())+list(book['other'].values())),'finite nonnegative measured rates')
    counts=aggregate_workload(items,plan);missing={k:n for k,n in counts.items() if k not in book['native']}
    native=sum(n*book['native'][k] for k,n in counts.items() if k in book['native'])
    other=book['other'];phases=['oracle_setup','nla_setup','nla_42_warmup_discarded']
    if plan['mode']=='remaining':phases+=['capture_warmup_discarded']+[f'oracle_{l}_warmup_discarded' for l in plan['layers']]
    W.require(all(k in other for k in phases) and 'placebo_build' in other and
              (plan['mode']!='remaining' or 'capture' in other),'measured non-native phase coverage')
    setups=book['setup_profiles']
    W.require(setups and all(type(x['seconds']) in (int,float) and math.isfinite(x['seconds']) and x['seconds']>=0 for x in setups),
              'finite experiment-owned measured setup profiles')
    setup=max(x['seconds'] for x in setups)
    W.require(setup==book['maximum_measured_setup_seconds'] and
              {x['profile_sha256'] for x in setups}=={x['profile_sha256'] for x in book['evidence']},'maximum own measured setup binding')
    fixed=setup+60
    capture=other.get('capture',0)*len(items) if plan['mode']=='remaining' else 0
    placebo=other['placebo_build']*(max(plan['row_indices'])+1)
    W.require(margin in (1.15,1.25),'registered work margin')
    cap=math.ceil(fixed+margin*(capture+placebo+native))
    return dict(cap_seconds=cap,cap_formula=f'max_measured_setup + {margin}*measured_work + retrieval',
                maximum_measured_setup_seconds=setup,retrieval_seconds=60,workload=counts,missing_native_phases=missing,
                measured_phase_cost_seconds=dict(fixed=fixed,capture=capture,placebo_build=placebo,native=native))


def groups_for(scope,inv,book,count):
    W.require(type(count)is int and 1<=count<=8,'one to eight proposed shards')
    rows=[]
    for row in inv['rows']:
        xs,p=row_inputs(scope,row,inv['reduction_step']);rows.append((row,xs,p,estimate(xs,p,book)))
    modes=sorted({x[2]['mode'] for x in rows});W.require(count>=len(modes),'separate remaining/reuse modes')
    groups=[]
    for mode in modes:groups.append(dict(mode=mode,rows=[],weight=0))
    while len(groups)<min(count,len(rows)):
        mode=max(modes,key=lambda m:sum(x[3]['cap_seconds'] for x in rows if x[2]['mode']==m)/(1+sum(g['mode']==m for g in groups)))
        groups.append(dict(mode=mode,rows=[],weight=0))
    for record in sorted(rows,key=lambda x:(-x[3]['cap_seconds'],x[0]['row_index'])):
        group=min((g for g in groups if g['mode']==record[2]['mode']),key=lambda g:g['weight'])
        group['rows'].append(record);group['weight']+=record[3]['cap_seconds']
    result=[]
    for group in groups:
        if not group['rows']:continue
        ordered=sorted(group['rows'],key=lambda x:x[0]['row_index']);items=[x for r,xs,p,e in ordered for x in xs]
        plan=copy.deepcopy(ordered[0][2]);plan['row_indices']=[r['row_index'] for r,xs,p,e in ordered]
        plan['item_ids']=[x['id'] for x in items];plan['shard']='e95-representative-'+str(inv['reduction_step'])+'-'+str(len(result))
        W.validate(items,plan);result.append(dict(items=items,plan=plan,forecast=estimate(items,plan,book)))
    return result


def plan(scope,profiles,prior_seconds,shards=8,dev_evidence=None,reopening=None):
    W.require(math.isfinite(prior_seconds) and prior_seconds>=0,'finite prior actual custody')
    ceiling=registered_ceiling(reopening)
    success='WITHIN_47H_REQUIRES_I3_GO' if reopening else 'WITHIN_40H_REQUIRES_I3_GO'
    verify_row_sources(scope)
    proof=same_runner(scope);book=rates(scope,profiles);base=copy.deepcopy(W.read(scope/'ROW_INVENTORY.json'))
    W.require(base['reduction_step']==0,'representative reductions start from registered full scope')
    evidence_values(base,dev_evidence);trace=[];groups=[]
    for step in ([3] if reopening else range(4)):
        inv,unknown=reduce_inventory(base,step)
        if unknown:
            trace.append(dict(reduction_step=step,status='BLOCKED_DEV_AUROC_EVIDENCE',unknown_rows=unknown));break
        if reopening:W.require(roster_digest(inv)==reopening['step3_roster_sha256'],'unchanged registered step3 roster')
        groups=groups_for(scope,inv,book,shards);production=sum(g['forecast']['cap_seconds'] for g in groups)
        missing=dict(Counter({k:sum(g['forecast']['missing_native_phases'].get(k,0) for g in groups)
                              for g in groups for k in g['forecast']['missing_native_phases']}))
        status=('REDUCTION_REQUIRED' if production+prior_seconds>ceiling else
                'BLOCKED_UNMEASURED_PHASE_WIDTH' if missing else success)
        trace.append(dict(reduction_step=step,status=status,production_cap_seconds=production,
                          projected_custody_seconds=production+prior_seconds,missing_native_phases=missing,
                          projection_is_complete=not missing,
                          covered_component_cap_seconds=production,
                          retained_rows=[r['row_index'] for r in inv['rows']]))
        if status!='REDUCTION_REQUIRED':break
    decision=dict(experiment='E95',method=METHOD,status=trace[-1]['status'],reduction_step=trace[-1]['reduction_step'],
        reductions=trace,prior_custody_seconds=prior_seconds,ceiling_seconds=ceiling,ceiling_binding=reopening,margin=1.25,
        source_compatibility=proof,rate_book=book,base_scope_seal_sha256=W.sha(scope/'SCOPE_SEAL.json'),
        dev_evidence=dev_evidence,production_admitted=False,full_launch_allowed=False,
        forecast_assumptions=['Phase/arm/layer/width mean transfer across frozen rows; no width interpolation',
        'Maximum complete own-profile measured setup/staging/warmups once per shard; capture uses maximum observed per-item time',
        'Placebo construction charged per global RNG row traversed, preserving full seed stream',
        'Section217: setup unpadded +1.25 measured work +60s retrieval per shard; original creation/prior custody and runtime NO_FIT retained'])
    decision['retained_prompt_max_tokens']=max((len(x['ids']) for g in groups for x in g['items']),default=0)
    eligibility=W.ROOT/ELIGIBILITY_PATH
    decision['unchanged_statement_eligibility']=dict(path=str(eligibility),sha256=W.sha(eligibility),
        note='Category-switch NOT EVALUABLE statements remain listed; reductions do not reinterpret them.')
    return decision,(inv,groups)


def bind(scope,profiles,out,prior_seconds,shards=8,dev_evidence=None,reopening=None):
    decision,(inv,groups)=plan(scope,profiles,prior_seconds,shards,dev_evidence,reopening)
    out.mkdir(parents=True,exist_ok=False);W.write(out/'MEASURED_DECISION.json',decision)
    if decision['status'] not in ('WITHIN_40H_REQUIRES_I3_GO','WITHIN_47H_REQUIRES_I3_GO'):return decision
    index=P.index_for(inv,W.read(scope/'JUDGE_INDEX.json'))
    W.write(out/'ROW_INVENTORY.json',inv);W.write(out/'JUDGE_INDEX.json',index)
    scope_sha=digest(dict(inventory=W.sha(out/'ROW_INVENTORY.json'),index=W.sha(out/'JUDGE_INDEX.json'),decision=W.sha(out/'MEASURED_DECISION.json')))
    P.source_archive(out/'source.tar.gz');records=[];book=decision['rate_book']
    for group in groups:
        items,p,forecast=group['items'],group['plan'],group['forecast'];inp=out/p['shard']/'inputs';inp.mkdir(parents=True)
        W.write(inp/'PLAN.json',p);W.write(inp/'items.json',items)
        m=dict(method=METHOD,ceiling_seconds=decision['ceiling_seconds'],ceiling_binding=reopening,
            programme_projected_custody_seconds=decision['reductions'][-1]['projected_custody_seconds'],
            prior_custody_seconds=prior_seconds,source_seal_sha256=W.sha(W.HERE/'SOURCE_SEAL.json'),scope_seal_sha256=scope_sha,
            inventory_sha256=W.sha(out/'ROW_INVENTORY.json'),index_sha256=W.sha(out/'JUDGE_INDEX.json'),
            plan_sha256=W.sha(inp/'PLAN.json'),items_sha256=W.sha(inp/'items.json'),row_indices=p['row_indices'],
            reduction_step=p['reduction_step'],cap_seconds=forecast['cap_seconds'],forecast=forecast,
            rate_book=book,profile_set_sha256=book['profile_set_sha256'],
            measured_decision_sha256=W.sha(out/'MEASURED_DECISION.json'),**book['hardware'])
        seeds={k:book['other'].get(k,0) for k in ['oracle_setup','nla_setup','capture','placebo_build']}
        seeds['placebo_build']*=max(p['row_indices'])+1
        for reader in ['oracle','nla']:
            counts={k:n for k,n in forecast['workload'].items() if k.startswith(reader+':')}
            seeds[reader+'_native']=sum(n*book['native'][k] for k,n in counts.items())/sum(counts.values()) if counts else 0
        W.write(inp/'STAGE_REQUEST.json',dict(experiment='E95',status='HOLD_I3_GLOBAL_ADMISSION',
            cap_seconds=m['cap_seconds'],cumulative_cap_seconds=m['cap_seconds']+prior_seconds,
            account_gate_USD=2500,seed_seconds_per_batch=seeds,timing95=m))
        ih=W.seal(inp,'INPUT_SEAL.json',experiment='E95',measured_scope_sha256=scope_sha)
        archive=inp.parent/'inputs.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:tar.add(inp,arcname='inputs')
        W.require(archive.stat().st_size<=20*1024*1024,'public input archive limit')
        records.append(dict(row_indices=p['row_indices'],shard=p['shard'],mode=p['mode'],cap_seconds=m['cap_seconds'],
            input_archive=str(archive.resolve()),input_archive_sha256=W.sha(archive),input_seal_sha256=ih,
            timing95=m))
    W.write(out/'REQUEST.json',dict(experiment='E95',status='HOLD_I3_GLOBAL_ADMISSION',full_launch_allowed=False,
        source_archive=str((out/'source.tar.gz').resolve()),source_archive_sha256=W.sha(out/'source.tar.gz'),
        source_seal_sha256=W.sha(W.HERE/'SOURCE_SEAL.json'),ceiling_binding=reopening,ceiling_seconds=decision['ceiling_seconds'],shards=records))
    return decision


def validate_production(assignment,limits,plan,inp,source_sha):
    m=limits['timing95']
    if m.get('method')=='REPRESENTATIVE_PHASE_WIDTH_V3_AMENDMENT1':
        from admission95 import validate_production as validate_amendment
        return validate_amendment(assignment,limits,plan,inp,source_sha)
    ceiling=registered_ceiling(m.get('ceiling_binding'))
    W.require(m['ceiling_seconds']==ceiling and
        0<=m['prior_custody_seconds']<=m['programme_projected_custody_seconds']<=ceiling,
        'whole programme original custody within registered ceiling')
    if m.get('ceiling_binding'):W.require(plan['reduction_step']==3,'§220 step3 only')
    W.require(m['source_seal_sha256']==source_sha and m['plan_sha256']==W.sha(inp/'PLAN.json') and
        m['items_sha256']==W.sha(inp/'items.json') and m['row_indices']==plan['row_indices'] and
        m['reduction_step']==plan['reduction_step'],'representative production source/whole-row scope')
    forecast=estimate(W.read(inp/'items.json'),plan,m['rate_book'])
    W.require(forecast==m['forecast'] and not forecast['missing_native_phases'] and
        limits['cap_seconds']==m['cap_seconds']==forecast['cap_seconds'],'measured phase/width/cap arithmetic')
    W.require(m['profile_set_sha256']==m['rate_book']['profile_set_sha256']==
        digest(sorted(m['rate_book']['evidence'],key=lambda x:x['profile_sha256'])),'measured profile set identity')
    W.require(assignment['pod_created_epoch']==assignment['custody_start_epoch'],'original creation clock required')
    for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']:
        W.require(assignment[k]==m[k],'representative assigned '+k)
        if k in m['rate_book']['hardware']:W.require(m[k]==m['rate_book']['hardware'][k],'measured runtime '+k)
    from contract import digest as valid_digest
    W.require(assignment['measured_profile_set_sha256']==m['profile_set_sha256'] and
        assignment['measured_decision_sha256']==m['measured_decision_sha256'] and
        valid_digest(assignment['e95_integrator_admission_sha256']),'independent I3 admission and measured evidence required')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['scope','out']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--profiles',type=Path,nargs='+',required=True)
    parser.add_argument('--prior-seconds',type=float,required=True);parser.add_argument('--shards',type=int,default=8)
    parser.add_argument('--dev-evidence',type=Path)
    parser.add_argument('--reopen-gate-seal',type=Path);parser.add_argument('--reopen-gate-sha')
    args=parser.parse_args()
    evidence=W.read(args.dev_evidence) if args.dev_evidence else None
    W.require(bool(args.reopen_gate_seal)==bool(args.reopen_gate_sha),'paired reopen gate seal/hash')
    reopening=reopen_binding(args.reopen_gate_seal,args.reopen_gate_sha) if args.reopen_gate_seal else None
    result=bind(args.scope,args.profiles,args.out,args.prior_seconds,args.shards,evidence,reopening)
    print(json.dumps(dict(status=result['status'],reduction_step=result['reduction_step'],production_admitted=False)))
