"""One admitted E106 Arm P or disposable NLA gate; all outputs retained once."""
import argparse,json,time,gc,hashlib,datetime
from pathlib import Path
from projects.g_agreement.e96.reconstructor_check import digest,write
from projects.g_agreement.e96.prepare_smoke_inputs import verify
from . import runtime


def utc(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()


class Clock:
    def __init__(self,out,end):self.out=out;self.end=end;self.first=None;self.generated=None
    def check(self):
        if time.time()>=self.end-120:raise TimeoutError('original-creation retrieval reserve')
    def save(self,name,data,generated=False):
        path=self.out/name
        if path.exists():raise FileExistsError(path)
        write(path,data)
        if self.first is None:self.first=utc(path.stat().st_mtime)
        if generated and self.generated is None:self.generated=utc(path.stat().st_mtime)
        write(self.out/'FIRST_OUTPUT.json',{'first_output_utc':self.first,'first_generated_readout_utc':self.generated})


def admission(path,inputs,mode):
    a=json.loads(path.read_text())
    if a['experiment']!='E106' or a['phase']!=mode or a['gpu_count']!=1 or not a['external_guard_armed'] or not a['incremental_backup_armed']:
        raise ValueError('guarded one-GPU admission')
    if a['input_seal_sha256']!=digest(inputs/'INPUT_SEAL.json'):raise ValueError('input binding')
    if a['planning_envelope_usd']>2500:raise ValueError('shared planning ceiling')
    if not a.get('analysis_adapter_cpu_tests_passed') or len(a.get('analysis_adapter_commit',''))!=40 or len(a.get('analysis_adapter_seal_sha256',''))!=64:
        raise ValueError('committed sole analysis adapter and synthetic tests required before output')
    if a['deadline_epoch']-a['created_epoch']>1800:raise ValueError('phase cap including staging')
    if mode=='gate':
        if time.time()>=datetime.datetime(2026,10,29,13,tzinfo=datetime.timezone.utc).timestamp():raise ValueError('14CET gate deadline passed')
    return a


def full_forecast(created,end,now,setups,work,remaining,reloads):
    """Whole allocation: elapsed staging/setup/work + worst own setup + both readers."""
    import math
    readers=('oracle','nla')
    if any(not setups.get(r) or not work.get(r) for r in readers):
        return {'status':'TIMING_REQUIRED','fits':False,'unknown':[r for r in readers if not setups.get(r) or not work.get(r)]}
    values=[v for group in (setups,work) for r in readers for v in group[r]]
    if any(not math.isfinite(v) or v<=0 for v in values):raise ValueError('finite positive measured timings')
    maximum_setup=max(v for r in readers for v in setups[r])
    remaining_work=sum(max(work[r])*remaining[r] for r in readers)
    future=maximum_setup*reloads+1.25*remaining_work+120
    elapsed=now-created
    return {'status':'ADMIT' if now+future<end else 'NO_FIT','fits':now+future<end,
            'elapsed_creation_seconds':elapsed,'max_measured_setup_seconds':maximum_setup,
            'future_reloads':reloads,'remaining_batches':dict(remaining),
            'max_batch_seconds':{r:max(work[r]) for r in readers},
            'remaining_work_seconds':remaining_work,'work_multiplier':1.25,
            'retrieval_reserve_seconds':120,'future_upper_seconds':future,
            'complete_custody_upper_seconds':elapsed+future,'creation_cap_seconds':end-created}


def setup_binding(a):
    """§217 clarification1: normalize own setup profiles to include staging."""
    import math
    staging=list(a.get('measured_e106_staging_seconds',[]))
    if any(not math.isfinite(x) or x<=0 for x in staging):raise ValueError('finite positive own staging')
    allowance=max(staging) if staging else 150.
    setups={r:[] for r in ('oracle','nla')}
    for reader in setups:
        # Legacy scalar profiles did not attest staging; conservatively add it.
        profiles=[{'seconds':x,'includes_staging':False} for x in a.get('prior_e106_setup_seconds',{}).get(reader,[])]
        profiles+=list(a.get('prior_e106_setup_profiles',{}).get(reader,[]))
        for p in profiles:
            if not math.isfinite(p['seconds']) or p['seconds']<=0:raise ValueError('finite positive own setup')
            if type(p['includes_staging']) is not bool:raise ValueError('explicit staging inclusion')
            setups[reader].append(p['seconds']+(0 if p['includes_staging'] else allowance))
    return setups,allowance,'own measured maximum' if staging else 'registered150s fallback'


def arm_p(a,inputs,assets,c):
    import numpy as np,torch
    items=json.loads((inputs/'ITEMS.json').read_text());prompt=json.loads((inputs/'PROMPT.json').read_text())
    if len(items)!=672 or any(x['split']!='test' for x in items):raise ValueError('Arm P test grid')
    count=0;remaining={'oracle':21,'nla':21};work={'oracle':[],'nla':[]}
    setups,staging_allowance,staging_source=setup_binding(a)
    arrays={r:np.load(inputs/f'acts{l}.npy',allow_pickle=False) for r,l in [('oracle',44),('nla',42)]}
    if any(h.shape!=(672,5120) or not np.isfinite(h).all() for h in arrays.values()):raise ValueError('Arm P vectors')
    def load_reader(reader,verify=True):
        c.check();t=time.monotonic()
        if verify:runtime.verify_assets(assets,reader,c.check)
        lens=runtime.load(assets,reader)
        if reader=='oracle':lens.prompt=prompt['prefix']+lens.prompt;lens._slots.clear()
        else:runtime.prefix_nla(lens,prompt['prefix'])
        measured=time.monotonic()-t
        setups[reader].append(measured+staging_allowance)
        name=reader+'_PROMPT.json' if verify else reader+'_RELOAD_PROMPT.json'
        c.save(name,{'reader':reader,'prefix':prompt['prefix'],'token_ids':lens.carrier(44)[0] if reader=='oracle' else lens.prompt_ids,'marker':lens.carrier(44)[1] if reader=='oracle' else lens.marker,'verify_and_load_seconds':measured,'staging_seconds':staging_allowance,'staging_source':staging_source,'setup_including_staging_seconds':setups[reader][-1]})
        return lens
    def run_batch(reader,lens,start):
        nonlocal count
        c.check();t=time.monotonic();raw=runtime.generate(reader,lens,arrays[reader][start:start+32])
        if len(raw)!=32:raise ValueError('output batch')
        layer=44 if reader=='oracle' else 42
        records=[dict(item_key=x['key'],id=x['id'],row=x['row'],source_row=x['source_row'],bank=x['bank'],split='test',reader=reader,phase='arm_p',block=layer,**r) for x,r in zip(items[start:start+32],raw)]
        c.save(f'{reader}_{start:04d}.json',records,generated=True);count+=len(records)
        work[reader].append(time.monotonic()-t);remaining[reader]-=1
    serial=0
    def require_fit(reloads):
        nonlocal serial
        f=full_forecast(a['created_epoch'],c.end,time.time(),setups,work,remaining,reloads)
        c.save(f'FULL_FORECAST_{serial:03d}.json',f);serial+=1
        if not f['fits']:raise TimeoutError('complete two-reader Arm P custody forecast does not fit')
    # Two retained pilots on the production pod; no throughput invented before both exist.
    c.save('TIMING_PLAN.json',{'status':'OWN_TIMINGS_UNKNOWN_UNTIL_BOTH_PILOTS','retained_batches_per_reader':1,'batch':32,'original_created_epoch':a['created_epoch'],'original_deadline_epoch':c.end,'cap_seconds':c.end-a['created_epoch'],'staging_seconds':staging_allowance,'staging_source':staging_source})
    lens=load_reader('oracle');run_batch('oracle',lens,0)
    del lens;gc.collect();torch.cuda.empty_cache()
    lens=load_reader('nla');run_batch('nla',lens,0)
    require_fit(1)  # NLA resident; one future Oracle reload is charged at worst own setup.
    for start in range(32,672,32):
        require_fit(1);run_batch('nla',lens,start)
    del lens;gc.collect();torch.cuda.empty_cache()
    require_fit(1)
    lens=load_reader('oracle',verify=False)
    for start in range(32,672,32):
        require_fit(0);run_batch('oracle',lens,start)
    del lens;gc.collect();torch.cuda.empty_cache()
    c.save('REPORT.json',{'status':'COMPLETE','phase':'arm_p','outputs':count,'items_per_reader':672,'readers':['oracle','nla'],'first_output_utc':c.first,'first_generated_readout_utc':c.generated})


def frozen_hash(model,trainable):
    import torch
    h=hashlib.sha256()
    for n,p in model.named_parameters():
        if n not in trainable:h.update(n.encode());h.update(p.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def gate_work_forecast(created,end,now,setup_seconds,prior_setups,step_times,remaining,hash_seconds):
    """Operational-only retained-step forecast; never invent missing GPU work."""
    import math
    if not step_times:return {'status':'TIMING_REQUIRED','fits':False,'step_work_seconds':None}
    samples=[setup_seconds,hash_seconds]+list(prior_setups)+list(step_times)
    if any(not math.isfinite(x) or x<=0 for x in samples):raise ValueError('finite positive gate timings')
    worst_setup=max([setup_seconds]+list(prior_setups))
    future=max(0,worst_setup-setup_seconds)+1.25*(max(step_times)*remaining+hash_seconds)+60+120
    return {'status':'ADMIT' if now+future<end else 'NO_FIT','fits':now+future<end,'elapsed_creation_seconds':now-created,
            'max_own_setup_including_staging_seconds':worst_setup,'max_step_seconds':max(step_times),
            'remaining_steps':remaining,'work_multiplier':1.25,'measured_frozen_hash_seconds':hash_seconds,
            'checkpoint_reserve_seconds':60,'retrieval_reserve_seconds':120,'future_upper_seconds':future,
            'complete_custody_upper_seconds':now-created+future,'creation_cap_seconds':end-created}


def gate(a,inputs,assets,c):
    import numpy as np,torch
    runtime.verify_assets(assets,'nla',c.check)
    nla=runtime.load(assets,'nla');trainable=runtime.attach_rank16(nla)
    setup_seconds=time.time()-a['created_epoch']
    c.save('PARAMETERS.json',{'original_adapter_rank':64,'new_adapter_rank':16,'trainable_names':list(trainable),'trainable_parameters':sum(p.numel() for p in trainable.values()),'base_and_original_adapter_frozen':True,'merge_used':False,'gpu':torch.cuda.get_device_name(0)})
    parity=json.loads((inputs/'NLA_PARITY.json').read_text());v=np.load(inputs/'nla_parity42.npy',allow_pickle=False)
    b200_smoke=None
    c.check()
    if 'B200' in torch.cuda.get_device_name(0):
        from .hardware_smoke import FiniteLogits
        with FiniteLogits(nla.av) as monitor:raw=runtime.generate('nla',nla,v)
        b200_smoke=monitor.receipt()
    else:raw=runtime.generate('nla',nla,v)
    comparisons=[]
    for i in parity['compare_indices']:
        expected=parity['records'][i]['raw'].encode('utf-8');actual=raw[i]['raw'].encode('utf-8')
        divergence=next((j for j,(x,y) in enumerate(zip(expected,actual)) if x!=y),None)
        if divergence is None and len(expected)!=len(actual):divergence=min(len(expected),len(actual))
        comparisons.append({'id':parity['records'][i]['id'],'byte_equal':actual==expected,'first_divergence_utf8_byte':divergence,'expected_sha256':hashlib.sha256(expected).hexdigest(),'actual_sha256':hashlib.sha256(actual).hexdigest()})
    c.save('PARITY_RAW.json',raw,generated=True);c.save('PARITY.json',comparisons)
    if b200_smoke is not None:
        c.save('B200_THREE_SEALED_ITEM_SMOKE.json',dict(b200_smoke,gpu=torch.cuda.get_device_name(0),sealed_items=3,comparisons=comparisons,original_eight_item_batch_context_preserved=True,optimizer_constructed=False))
    if len(comparisons)!=3 or not all(x['byte_equal'] for x in comparisons):raise RuntimeError('3sealed greedy raw readouts did not reproduce byte-for-byte; optimizer never constructed')
    # Frozen CPU-authored dev template targets; no parity vector or text reaches the optimizer.
    dev=np.load(inputs/'gate_dev42.npy',allow_pickle=False);ids=json.loads((inputs/'GATE_DEV_IDS.json').read_text())
    if dev.shape!=(16,5120) or set(ids)&{x['id'] for x in parity['records']}:raise ValueError('disjoint gate dev inputs')
    teachers=json.loads((inputs/'GATE_TARGETS.json').read_text())
    if len(teachers)!=16 or [x['id'] for x in teachers]!=ids or any(x['split']!='dev' for x in teachers):raise ValueError('frozen gate targets')
    c.save('TRAINING_INPUT_BINDING.json',{'vectors_sha256':digest(inputs/'gate_dev42.npy'),'targets_sha256':digest(inputs/'GATE_TARGETS.json'),'sealed_before_optimizer_utc':utc(time.time())})
    c.check();hash_started=time.monotonic();before=frozen_hash(nla.av,trainable);hash_seconds=time.monotonic()-hash_started
    old={n:p.detach().cpu().clone() for n,p in trainable.items()}
    nla.av.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});nla.av.enable_input_require_grads();nla.av.config.use_cache=False;nla.av.train()
    optimizer=torch.optim.AdamW(list(trainable.values()),lr=1e-4,weight_decay=0.)
    step_times=[]
    c.save('GATE_TIMING_PLAN.json',{'step_work_seconds':'UNKNOWN until first retained optimizer step','setup_including_staging_seconds':setup_seconds,'measured_frozen_hash_seconds':hash_seconds,'prior_own_setup_seconds':a.get('prior_e106_gate_setup_seconds',[]),'checkpoint_reserve_seconds':60,'retrieval_seconds':120})
    for step in range(10):
        step_started=time.monotonic()
        c.check();optimizer.zero_grad(set_to_none=True);total=0.
        for i in torch.randperm(16).tolist():
            c.check();answer=nla.tok.encode(teachers[i]['text'],add_special_tokens=False)+[nla.tok.eos_token_id]
            seq=torch.tensor([nla.prompt_ids+answer],device=nla.device);labels=seq.clone();labels[:,:len(nla.prompt_ids)]=-100
            # Keep injection active through checkpoint recomputation during backward.
            with nla._inject(torch.as_tensor(dev[i:i+1],device=nla.device).float()):
                loss=nla.av(input_ids=seq,attention_mask=torch.ones_like(seq),labels=labels,use_cache=False).loss
                if not torch.isfinite(loss):raise ValueError('nonfinite loss')
                (loss/16).backward();total+=float(loss.detach())/16
        if any(p.grad is not None for n,p in nla.av.named_parameters() if n not in trainable):raise ValueError('frozen parameter gradient')
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in trainable.values()):raise ValueError('nonfinite gradient')
        optimizer.step();step_times.append(time.monotonic()-step_started)
        c.save(f'STEP_{step+1:02d}.json',{'step':step+1,'loss':total,'completed_utc':utc(time.time()),'seconds':step_times[-1]})
        forecast=gate_work_forecast(a['created_epoch'],c.end,time.time(),setup_seconds,a.get('prior_e106_gate_setup_seconds',[]),step_times,9-step,hash_seconds)
        c.save(f'GATE_FORECAST_{step+1:02d}.json',forecast)
        if not forecast['fits']:raise TimeoutError('remaining ten-step gate custody forecast exceeds original cap')
    c.check();after=frozen_hash(nla.av,trainable);changed=sum(not torch.equal(old[n],p.detach().cpu()) for n,p in trainable.items())
    if before!=after or changed==0:raise RuntimeError('base freeze or rank16 update failed')
    nla.av.save_pretrained(c.out/'disposable_adapter',selected_adapters=['e106_repair'])
    c.check()
    c.save('REPORT.json',{'status':'PASS','phase':'gate','steps':10,'parity_byte_equal':3,'frozen_before_sha256':before,'frozen_after_sha256':after,'adapter_tensors_changed':changed,'first_output_utc':c.first,'first_generated_readout_utc':c.generated,'production_initialization':'pinned NLA original plus fresh zero rank16 adapter; never disposable gate weights'})


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['arm_p','gate'],required=True)
    for k in ('inputs','assets','admission','out'):p.add_argument('--'+k,type=Path,required=True)
    x=p.parse_args()
    if x.out.exists():raise FileExistsError('refuse prior output replacement')
    a=admission(x.admission,x.inputs,x.phase);verify(x.inputs,'INPUT_SEAL.json')
    assets=json.loads(x.assets.read_text());x.out.mkdir(parents=True)
    end=a['deadline_epoch']
    if x.phase=='gate':end=min(end,datetime.datetime(2026,10,29,13,tzinfo=datetime.timezone.utc).timestamp())
    c=Clock(x.out,end)
    try:
        import torch
        if torch.cuda.device_count()!=1:raise ValueError('one visible GPU')
        torch.set_num_threads(8);torch.manual_seed(20261029);torch.cuda.manual_seed_all(20261029)
        (arm_p if x.phase=='arm_p' else gate)(a,x.inputs,assets,c)
    except Exception as e:
        c.save('FAILURE.json',{'status':'arm T not run (feasibility)' if x.phase=='gate' else 'ARM_P_INCOMPLETE','reason':str(e),'type':type(e).__name__,'first_output_utc':c.first});raise
    finally:
        write(x.out/'OUTPUT_SEAL.json',{'phase':x.phase,'first_output_utc':c.first,'first_generated_readout_utc':c.generated,'input_seal_sha256':digest(x.inputs/'INPUT_SEAL.json'),'files':{str(f.relative_to(x.out)):digest(f) for f in sorted(x.out.rglob('*')) if f.is_file() and f.name!='OUTPUT_SEAL.json'}})

if __name__=='__main__':main()
