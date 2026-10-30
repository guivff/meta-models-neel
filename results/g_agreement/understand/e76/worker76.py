"""E76 single shared norm-matched pool: capture -> calibration seal -> native readouts."""
import argparse,json,os,signal,time
from pathlib import Path
import numpy as np
from common76 import *


class NoFit(TimeoutError):pass
PHASES=('oracle_setup','capture','oracle_readout','nla_setup','nla_readout')
BATCH_PHASES=frozenset(('capture','oracle_readout','nla_readout','parity'))


class Clock:
    def __init__(self,assignment,out,clock=time.time):
        self.a=assignment;self.out=Path(out);self.now=clock;self.end=assignment['absolute_deadline_epoch']-RESERVE
        self.remaining=dict(assignment['phase_forecasts_seconds']);self.observed={};self.events=[];self.warmed=set();self.batch_totals={};self.batch_counts={}
    def check(self):
        remaining=sum(self.remaining.values());now=self.now();fits=now+1.25*remaining+360<self.end
        data={'experiment':'E76','status':'ADMIT' if fits else 'NO_FIT','epoch':now,'remaining_forecast_seconds':remaining,
            'forecast_by_phase':self.remaining,'observed_max_seconds':self.observed,
            'real_batch_count_by_phase':self.batch_counts,'real_batch_total_seconds_by_phase':self.batch_totals,
            'forecast_method':'running mean of real batches per phase; warm-ups excluded','reforecast_margin':1.25,'production_deadline_epoch':self.end,
            'registered_stage_cap_seconds':CAP,'retrieval_reserve_seconds':RESERVE,'scope_reduced':False}
        tmp=self.out/'ADMISSION.latest.tmp.json';tmp.write_text(json.dumps(data,sort_keys=True,allow_nan=False)+'\n');tmp.replace(self.out/'ADMISSION.latest.json')
        if not fits:raise NoFit(f'Full E76 scope does not fit authorised{CAP}s stage cap')
    def call(self,phase,fn,left=0):
        self.check();start=self.now();value=fn();elapsed=max(0.,self.now()-start)
        self.observed[phase]=max(elapsed,self.observed.get(phase,0.))
        if phase in BATCH_PHASES:
            self.batch_totals[phase]=self.batch_totals.get(phase,0.)+elapsed
            self.batch_counts[phase]=self.batch_counts.get(phase,0)+1
            self.remaining[phase]=self.batch_totals[phase]/self.batch_counts[phase]*left
        else:self.remaining[phase]=0.
        self.events.append({'phase':phase,'elapsed_seconds':elapsed,'remaining_units':left});self.check();return value


    def warmup(self,phase,fn):
        require(phase not in self.warmed,'Exactly one synthetic warm-up per resident path')
        self.check();self.warmed.add(phase);start=self.now();complete=False
        try:
            fn()  # Discard the returned dummy output; do not feed Clock.call or any readout writer.
            complete=True
        finally:
            self.events.append({'phase':phase+'_warmup','elapsed_seconds':max(0.,self.now()-start),
                'synthetic_only':True,'output_discarded':True,'excluded_from_forecast':True,'completed':complete})
            tmp=self.out/'WARMUP_TIMING.tmp.json'
            tmp.write_text(json.dumps([x for x in self.events if x.get('synthetic_only')],sort_keys=True,allow_nan=False)+'\n')
            tmp.replace(self.out/'WARMUP_TIMING.json')
        self.check()  # Same absolute stage clock: cold compilation time is fully charged.


def native_warmup(backend,reader,clock):
    # The only input is fresh seeded noise; no real item, vector, median or readout is consulted.
    dummy=np.random.default_rng(20261028).standard_normal((32,DIM)).astype(np.float32)
    clock.warmup(reader+'_readout',lambda:backend.native(reader,dummy,batch=32))


def assignment_check(a,request,now=None,pod_id=None):
    now=time.time() if now is None else now;pod_id=os.environ.get('RUNPOD_POD_ID') if pod_id is None else pod_id
    require(a.get('issuer')=='integrator' and a.get('track')=='Q' and a.get('experiment')=='E76' and a.get('gpu_count')==1
        and bool(pod_id) and a.get('pod_id')==pod_id,'Main Integrator single-pod TrackQ admission required')
    require(all(a.get(k) is True for k in ('main_integrator_admitted','daily_budget_verified','source_pushed','external_hardstop_verified','hold_renewer_verified')),'Main admission and external custody guards required')
    require(a.get('request_sha256')==sha(HERE/'LAUNCH_REQUEST.json') and a.get('source_seal_sha256')==request['source_seal_sha256']==sha(HERE/'POD_SOURCE_SEAL.json')
        and a.get('input_seal_sha256')==request['input_seal_sha256']==sha(CACHE/'pod_inputs/INPUT_SEAL.json'),'Exact request/code/input pins required')
    require(isinstance(a.get('source_commit'),str) and len(a['source_commit'])==40 and all(c in '0123456789abcdef' for c in a['source_commit']),'Published full commit required')
    for k in ('stage_started_epoch','absolute_deadline_epoch','allocated_stage_seconds','provider_lease_deadline_epoch'):
        require(type(a.get(k)) in (int,float) and math.isfinite(a[k]),'Finite stage custody clocks required')
    require(RESERVE<a['allocated_stage_seconds']<=CAP and a['stage_started_epoch']<=now<a['absolute_deadline_epoch']
        <=min(a['stage_started_epoch']+a['allocated_stage_seconds'],a['provider_lease_deadline_epoch'],STOP),'E76 stage/provider/programme cap violation')
    f=a.get('phase_forecasts_seconds',{});require(set(f)==set(PHASES) and all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in f.values()) and sum(f.values())>0,'Complete conservative phase forecasts required')
    return a['absolute_deadline_epoch']-RESERVE


def parity_release(a):
    release=read(CACHE/'PARITY_RELEASE.json')
    require(release.get('issuer')=='integrator' and release.get('pod_id')==a['pod_id'] and release.get('status')=='PASS'
        and release.get('same_pod_verified') is True and release.get('native_backend_unchanged') is True,'Same-pod native parity release required')
    require(isinstance(release.get('parity_result_sha256'),str) and len(release['parity_result_sha256'])==64
        and all(c in '0123456789abcdef' for c in release['parity_result_sha256']),'Exact verified parity result pin required')
    expected={str(p.relative_to(HERE)):sha(p) for p in (HERE/'vendor/mats/readers/olens.py',HERE/'vendor/mats/readers/nla.py',HERE/'native_nla512.py')}
    require(release.get('native_code_sha256')==expected,'Parity native-code correspondence must be verified on CPU')
    require(release.get('assets_manifest_sha256')==a['assets_manifest_sha256'],'Parity assets must match stage assets')
    if (CACHE/'PARITY_GENERATE.RUN_ONCE.json').exists():
        out=CACHE/'parity-generated-20261027'
        require(release.get('parity_generation_output_seal_sha256')==sha(out/'OUTPUT_SEAL.json')
            and release.get('raw_scores_sha256')==sha(out/'PARITY_SCORES.jsonl')
            and release.get('parity_input_seal_sha256')==read(HERE/'LAUNCH_REQUEST.json')['parity_input_seal_sha256'],
            'CPU parity release must bind this exact split generation')
    return release


def acquire_calibration(backend,bank,items,selected,z,clock,out):
    # No E76 reader generation occurs until all bank medians and input pools seal.
    raw={l:np.empty((N,DIM),np.float32) for l in (42,44)};norms={l:np.empty(len(items),np.float64) for l in (42,44)}
    target={item_index:pool_index for pool_index,item_index in enumerate(selected)}
    order=sorted(range(len(items)),key=lambda i:(len(items[i]['ids']),items[i]['id']));jobs=[order[i:i+64] for i in range(0,len(order),64)]
    seen=set()
    for j,ix in enumerate(jobs):
        values=clock.call('capture',lambda:backend.capture([items[i] for i in ix],batch=64),len(jobs)-j-1)
        require(set(values)=={42,44},'Both native-layer captures required')
        for l in (42,44):
            require(values[l].shape==(len(ix),DIM) and np.isfinite(values[l]).all(),'Capture geometry failure')
            norms[l][ix]=np.linalg.norm(values[l].astype(np.float64),axis=1)
            for k,index in enumerate(ix):
                if index in target:raw[l][target[index]]=values[l][k]
        require(not seen.intersection(ix),'Duplicate calibration item');seen.update(ix)
    require(seen==set(range(len(items))),'Complete all-test median reference required')
    pools,calibration=make_pools(bank,norms,raw,z)
    for l in (42,44):np.save(out/f'REFERENCE_NORMS{l}.npy',norms[l],allow_pickle=False)
    for l in (42,44):np.save(out/f'SELECTED_RAW{l}.npy',raw[l],allow_pickle=False)
    for (l,arm),h in pools.items():np.save(out/f'pool_{l}_{arm}.npy',h,allow_pickle=False)
    dump(out/'CALIBRATION.json',{**calibration,'experiment':'E76','sealed_before_any_native_readout':True,
        'reference_items':len(items),'items_per_source_bank':{str(b):sum(x['bank']==b for x in items) for b in range(5)},
        'input_seal_sha256':sha(CACHE/'pod_inputs/INPUT_SEAL.json')})
    names=['CALIBRATION.json']+[f'REFERENCE_NORMS{l}.npy' for l in (42,44)]+[f'SELECTED_RAW{l}.npy' for l in (42,44)]+[f'pool_{l}_{arm}.npy' for l in (42,44) for arm in ARMS]
    dump(out/'CALIBRATION_SEAL.json',{'experiment':'E76','files':{n:sha(out/n) for n in names}})
    return pools,calibration


def run(backend,bank,items,selected,z,out,clock):
    clock.call('oracle_setup',backend.load_oracle)
    pools,calibration=acquire_calibration(backend,bank,items,selected,z,clock,out)
    calls={reader:0 for reader in READERS}
    for reader in READERS:
        if reader=='nla':clock.call('nla_setup',backend.load_nla)
        native_warmup(backend,reader,clock)
        layer=44 if reader=='oracle' else 42;jobs=[(arm,s) for arm in ARMS for s in range(0,N,32)]
        originals={arm:pools[layer,arm].tobytes() for arm in ARMS}
        with (out/f'{reader}.jsonl').open('x') as stream:
            for j,(arm,s) in enumerate(jobs):
                h=pools[layer,arm][s:s+32];values=clock.call(reader+'_readout',lambda:backend.native(reader,h,batch=32),len(jobs)-j-1)
                require(len(values)==len(h),'Exactly one native readout per vector required')
                for i,value in enumerate(values):
                    require(isinstance(value['raw'],str) and isinstance(value['text'],str),'Native text schema failure')
                    index=s+i
                    record={'id':__import__('hashlib').sha256(f'E76 {reader} {arm} {index}'.encode()).hexdigest()[:32],
                        'reader':reader,'layer':layer,'arm':arm,'pool_index':index,'source_bank':calibration['source_bank_indices_by_pool_index'][index],
                        'repeat':0,**value}
                    if reader=='nla':require(record['native_max_new_tokens']==512 and record['native_stop']=='</explanation>','Frozen NLA512 stop contract required')
                    stream.write(json.dumps(record,allow_nan=False,ensure_ascii=False)+'\n');calls[reader]+=1
                stream.flush()
        require(all(pools[layer,arm].tobytes()==originals[arm] for arm in ARMS),'Native adapter mutated sealed input pool')
    require(calls=={'oracle':1000,'nla':1000},'Complete one-greedy shared pool grid required')
    from native_nla512 import truncation_summary
    dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(line) for line in (out/'nla.jsonl').read_text().splitlines()],row_key='arm'))
    dump(out/'GRID_COMPLETE.json',{'experiment':'E76','readouts':calls,'vectors_per_arm':N,'repeat':0,'source_bank_covariate':True})
    dump(out/'TIMING.json',{'completed_epoch':time.time(),'phase_events':clock.events,'phase_max_seconds':clock.observed})


def preflight():
    source_verify();bank,items,selected,z=load_inputs()
    from parity76 import load_parity
    load_parity(CACHE/'parity_inputs',sha(CACHE/'parity_inputs/INPUT_SEAL.json'))
    return {'experiment':'E76','status':'CPU_PREFLIGHT_PASS','reference_items':len(items),'selected_shuffled_vectors':len(selected),
        'random_vectors':len(z),'source_banks':5,'native_readouts_required':2000,'no_labels_or_private_files':True,
        'source_seal_sha256':sha(HERE/'POD_SOURCE_SEAL.json'),'input_seal_sha256':sha(CACHE/'pod_inputs/INPUT_SEAL.json'),'GPU_calls':0}


def generate_parity_only(args,assignment,request,end):
    from parity76 import load_parity,generate
    pin=request['parity_input_seal_sha256']
    require(assignment.get('parity_input_seal_sha256')==pin,'Assigned split parity input pin required')
    inputs=load_parity(CACHE/'parity_inputs',pin)
    forecasts=assignment.get('parity_phase_forecasts_seconds',{})
    require(set(forecasts)=={'parity_setup','parity'} and all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in forecasts.values()),'Conservative parity setup/score forecasts required')
    require(not (CACHE/'WORKER.RUN_ONCE.json').exists(),'Parity must precede production')
    dump(CACHE/'PARITY_GENERATE.RUN_ONCE.json',{'experiment':'E76_PARITY','started_epoch':time.time(),'assignment_sha256':sha(args.assignment)})
    out=CACHE/'parity-generated-20261027';out.mkdir(exist_ok=False)
    clock=Clock(assignment,out);clock.remaining.update(forecasts);clock.check()
    def expired(*_):raise NoFit('E76 split parity shares the original stage deadline')
    old=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    status='INCOMPLETE'
    try:
        from backend76 import Backend
        backend=Backend(args.assets);dump(out/'RUNTIME.json',backend.runtime)
        detail=generate(backend,clock,inputs,out);clock.check()
        dump(out/'GENERATION.json',detail);status='GENERATED_UNSCORED'
    except BaseException as exc:
        dump(out/'FAILURE.json',{'error_type':type(exc).__name__,'guard_preserved':True});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        dump(out/'CUSTODY.json',{'experiment':'E76_PARITY','assignment':assignment,'assignment_sha256':sha(args.assignment),
            'completed_epoch':time.time(),'assets_manifest_sha256':sha(args.assets),'request_sha256':sha(HERE/'LAUNCH_REQUEST.json'),
            'source_seal_sha256':sha(HERE/'POD_SOURCE_SEAL.json'),'parity_input_seal_sha256':pin,
            'native_code_sha256':{str(p.relative_to(HERE)):sha(p) for p in (HERE/'vendor/mats/readers/olens.py',HERE/'vendor/mats/readers/nla.py',HERE/'native_nla512.py')}})
        dump(out/'OUTPUT_SEAL.json',{'experiment':'E76_PARITY','status':status,'files':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}})


def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--parity-generate-only',action='store_true');p.add_argument('--assignment',type=Path);p.add_argument('--assets',type=Path);a=p.parse_args()
    detail=preflight()
    if a.preflight:print(json.dumps(detail));return
    require(a.assignment is not None and a.assets is not None,'Integrator assignment/assets required')
    request=read(HERE/'LAUNCH_REQUEST.json');require(request['status']=='READY','Unsealed request')
    assignment=read(a.assignment);end=assignment_check(assignment,request)
    require(sha(a.assets)==assignment['assets_manifest_sha256'],'Assigned assets manifest mismatch')
    if a.parity_generate_only:
        generate_parity_only(a,assignment,request,end);return
    release=parity_release(assignment)
    dump(CACHE/'WORKER.RUN_ONCE.json',{'experiment':'E76','started_epoch':time.time(),'assignment_sha256':sha(a.assignment)})
    out=CACHE/'out-20261027';out.mkdir(exist_ok=False);clock=Clock(assignment,out);clock.check()
    def expired(*_):raise NoFit(f'E76 absolute{CAP}s stage deadline')
    old=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    status='INCOMPLETE'
    try:
        from backend76 import Backend
        backend=Backend(a.assets);dump(out/'RUNTIME.json',backend.runtime);dump(out/'PARITY_RELEASE.json',release)
        bank,items,selected,z=load_inputs();run(backend,bank,items,selected,z,out,clock);clock.check();status='COMPLETE'
    except BaseException as exc:
        dump(out/'FAILURE.json',{'category':'OPERATIONAL_NO_FIT' if isinstance(exc,NoFit) else 'FAILURE_STOP',
            'error_type':type(exc).__name__,'scope_reduced':False,'guard_preserved':True});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        dump(out/'CUSTODY.json',{'assignment':assignment,'assignment_sha256':sha(a.assignment),'completed_epoch':time.time(),
            'request_sha256':sha(HERE/'LAUNCH_REQUEST.json'),'input_seal_sha256':detail['input_seal_sha256'],
            'source_seal_sha256':detail['source_seal_sha256']})
        dump(out/'OUTPUT_SEAL.json',{'experiment':'E76','status':status,'files':{x.name:sha(x) for x in sorted(out.iterdir()) if x.is_file()}})


if __name__=='__main__':main()
