"""One registered P retime: retain cold+steady batches, custody both native readers."""
import argparse,json,time
from pathlib import Path
from .worker import Clock,admission,setup_binding,full_forecast
from . import runtime
from projects.g_agreement.e96.prepare_smoke_inputs import verify
from projects.g_agreement.e96.reconstructor_check import digest,write


def steady_forecast(a,end,now,setups,current_setups,work,remaining,memory):
    """Cold retained batches are charged fully as setup; every later batch as work."""
    f=full_forecast(a['created_epoch'],end,now,setups,work,remaining,0)
    if f['status']=='TIMING_REQUIRED':return f
    deficit=sum(max(0,max(setups[r])-current_setups[r]) for r in ('oracle','nla'))
    f['own_setup_deficit_seconds']=deficit;f['future_upper_seconds']+=deficit
    f['complete_custody_upper_seconds']+=deficit
    f['fits']=now+f['future_upper_seconds']<end and memory['fits']
    f['status']='ADMIT' if f['fits'] else 'NO_FIT'
    f['memory']=memory;return f


def memory_headroom(free,peak_allocated,current_allocated):
    # Measured inference transient plus 2GiB operational reserve, no batch changes.
    reserve=max(0,peak_allocated-current_allocated)+2*1024**3
    return {'free_bytes':free,'peak_allocated_bytes':peak_allocated,'current_allocated_bytes':current_allocated,
            'required_transient_and_reserve_bytes':reserve,'fits':free>=reserve}


def arm_p_retime(a,inputs,assets,c):
    import numpy as np,torch
    items=json.loads((inputs/'ITEMS.json').read_text());prompt=json.loads((inputs/'PROMPT.json').read_text())
    if len(items)!=672 or any(x['split']!='test' for x in items):raise ValueError('full unchanged P grid')
    arrays={r:np.load(inputs/f'acts{b}.npy',allow_pickle=False) for r,b in [('oracle',44),('nla',42)]}
    if any(x.shape!=(672,5120) or not np.isfinite(x).all() for x in arrays.values()):raise ValueError('P vectors')
    setups,staging,staging_source=setup_binding(a);work={r:[] for r in arrays};current={};lenses={};remaining={r:21 for r in arrays};count=0;serial=0;transient=0
    c.save('TIMING_PLAN.json',{'status':'STEADY_TIMINGS_AND_DUAL_MEMORY_UNKNOWN','retained_batches_per_reader':2,'batch':32,'cold_full_batch_charged_as_setup':True,'steady_max_uses_all_batches_after_first':True,'both_readers_resident':True,'no_reload':True,'no_failed_partial_reuse':True,'original_created_epoch':a['created_epoch'],'original_deadline_epoch':c.end,'staging_seconds':staging,'staging_source':staging_source})
    def batch(reader,start):
        nonlocal count,transient
        c.check();torch.cuda.synchronize();t=time.monotonic()
        raw=runtime.generate(reader,lenses[reader],arrays[reader][start:start+32]);torch.cuda.synchronize()
        if len(raw)!=32:raise ValueError('output batch')
        records=[dict(item_key=x['key'],id=x['id'],row=x['row'],source_row=x['source_row'],bank=x['bank'],split='test',reader=reader,phase='arm_p',block=44 if reader=='oracle' else 42,**r) for x,r in zip(items[start:start+32],raw)]
        c.save(f'{reader}_{start:04d}.json',records,generated=True)
        seconds=time.monotonic()-t;remaining[reader]-=1;count+=32
        transient=max(transient,torch.cuda.max_memory_allocated()-torch.cuda.memory_allocated())
        if start:work[reader].append(seconds)
        c.save(f'{reader}_{start:04d}_TIMING.json',{'seconds':seconds,'classification':'cold_full_batch_setup' if not start else 'steady_work','all_outputs_retained':True,'cuda_allocated_bytes':torch.cuda.memory_allocated(),'cuda_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'cuda_free_bytes':torch.cuda.mem_get_info()[0]})
        return seconds
    for reader in ('oracle','nla'):
        c.check();t=time.monotonic();runtime.verify_assets(assets,reader,c.check)
        lenses[reader]=runtime.load(assets,reader)
        lens=lenses[reader]
        if reader=='oracle':lens.prompt=prompt['prefix']+lens.prompt;lens._slots.clear()
        else:runtime.prefix_nla(lens,prompt['prefix'])
        load_seconds=time.monotonic()-t
        c.save(reader+'_PROMPT.json',{'reader':reader,'prefix':prompt['prefix'],'token_ids':lens.carrier(44)[0] if reader=='oracle' else lens.prompt_ids,'marker':lens.carrier(44)[1] if reader=='oracle' else lens.marker,'verify_and_load_seconds':load_seconds})
        cold=batch(reader,0);current[reader]=load_seconds+staging+cold;setups[reader].append(current[reader])
        c.save(reader+'_SETUP.json',{'verify_and_load_seconds':load_seconds,'full_retained_cold_batch_seconds':cold,'staging_seconds':staging,'setup_including_staging_and_cold_seconds':current[reader]})
        torch.cuda.reset_peak_memory_stats();batch(reader,32)
        # Keep BOTH distinct pinned models alive; never share/merge their base weights.
    memory=memory_headroom(torch.cuda.mem_get_info()[0],torch.cuda.memory_allocated()+transient,torch.cuda.memory_allocated())
    c.save('DUAL_READER_MEMORY.json',memory)
    if not memory['fits']:raise MemoryError('dual native reader measured transient/headroom does not fit')
    def fit():
        nonlocal serial
        m=memory_headroom(torch.cuda.mem_get_info()[0],torch.cuda.memory_allocated()+transient,torch.cuda.memory_allocated())
        f=steady_forecast(a,c.end,time.time(),setups,current,work,remaining,m)
        c.save(f'FULL_FORECAST_{serial:03d}.json',f);serial+=1
        if not f['fits']:raise TimeoutError('registered P retime full remaining custody does not fit')
    fit()
    for reader in ('nla','oracle'):
        for start in range(64,672,32):fit();batch(reader,start)
    fit();c.save('REPORT.json',{'status':'COMPLETE','phase':'arm_p','outputs':count,'items_per_reader':672,'readers':['oracle','nla'],'first_output_utc':c.first,'first_generated_readout_utc':c.generated,'both_distinct_readers_retained':True,'failed_partials_reused':False})


def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','admission','out'):p.add_argument('--'+k,type=Path,required=True)
    x=p.parse_args()
    if x.out.exists():raise FileExistsError('new output only')
    a=admission(x.admission,x.inputs,'arm_p')
    if a.get('attempt')!='a2' or not a.get('single_registered_operational_restart'):raise ValueError('I-4 registered sole restart required')
    if a['deadline_epoch']-a['created_epoch']>1366.5616109371185:raise ValueError('remaining original P custody')
    verify(x.inputs,'INPUT_SEAL.json');assets=json.loads(x.assets.read_text());x.out.mkdir(parents=True);c=Clock(x.out,a['deadline_epoch'])
    try:
        import torch
        if torch.cuda.device_count()!=1:raise ValueError('one visible GPU')
        torch.set_num_threads(8);torch.manual_seed(20261029);torch.cuda.manual_seed_all(20261029)
        arm_p_retime(a,x.inputs,assets,c)
    except Exception as e:
        c.save('FAILURE.json',{'status':'arm P not run (operational)','reason':str(e),'type':type(e).__name__,'first_output_utc':c.first});raise
    finally:write(x.out/'OUTPUT_SEAL.json',{'phase':'arm_p','first_output_utc':c.first,'first_generated_readout_utc':c.generated,'input_seal_sha256':digest(x.inputs/'INPUT_SEAL.json'),'files':{str(f.relative_to(x.out)):digest(f) for f in sorted(x.out.rglob('*')) if f.is_file() and f.name!='OUTPUT_SEAL.json'}})

if __name__=='__main__':main()
