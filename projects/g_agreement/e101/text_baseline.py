"""E81 generic-arm frozen prompts: base Qwen, serial greedy, 128 tokens."""
import numpy as np
from .contract import read,write
from .timing import profile_receipt
CONTENT={'language_plan','format_plan','fact_recall','language_continuation'}


def load(root):
    s=read(root/'INPUT_SEAL.json');m=read(root/'MANIFEST.json');xs=read(root/'items.json')
    if set(s['files'])!={'MANIFEST.json','items.json'} or s['labels_on_pod'] is not False:raise ValueError('public baseline members only')
    if m['experiment']!='E101_TEXT' or m['generic_arm']!='E81' or not m['owner_source_sha256']:raise ValueError('frozen E81 generic source')
    if len(xs)!=336 or len({x['id'] for x in xs})!=336 or {x['row'] for x in xs}!=CONTENT:raise ValueError('four content rows')
    for row in CONTENT:
        if sum(x['row']==row for x in xs)!=84:raise ValueError('84 baseline items per row')
    for x in xs:
        if set(x)!={'id','row','input_ids','prompt'} or not x['input_ids'] or any(type(t)!=int or t<0 for t in x['input_ids']):raise ValueError('baseline public schema')
    return xs,None


def acquire(items,h,runtime,clock,out,timing=False):
    clock.call('text_setup',runtime.load_base)
    runtime.check_tokens([dict(text=x['prompt'],ids=x['input_ids']) for x in items])
    clock.call('text_warmup_discarded',lambda:runtime.text([runtime.synthetic()[0]],max_new_tokens=128))
    ordered=sorted(range(len(items)),key=lambda i:len(items[i]['input_ids']))
    indices=[ordered[k] for k in sorted({0,len(items)//2,len(items)-1})] if timing else list(range(len(items)))
    jobs=[dict(kind='text',indices=[i]) for i in range(len(items))];write(out/'JOB_GRID.json',jobs);(out/'jobs').mkdir()
    clock.cost={'text':[]};done=set()
    for i in indices:
        x=items[i];rr=clock.call('text',lambda:runtime.text([x['input_ids']],max_new_tokens=128))
        if len(rr)!=1:raise ValueError('exactly one serial greedy result')
        write(out/'jobs'/f'{i:06d}.json',[dict(id=x['id'],row=x['row'],gpu_type=runtime.hardware_assignment['gpu_type'],**rr[0])])
        done.add(i)
        from admission import atomic
        atomic(out/'COMPLETED.json',sorted(done))
        if not timing and not clock.forecast(jobs,done):return 'NO_FIT'
    if timing:write(out/'MEASURED_PROFILE.json',profile_receipt(clock.events,[dict(phase='text',jobs=len(items),sample_seconds=clock.cost['text'],mean_job_seconds=float(np.mean(clock.cost['text'])))]))
    return 'TIMING_ONLY' if timing else 'COMPLETE'

if __name__=='__main__':
    from .operational import run
    run('E101_TEXT',load,acquire,['text'])
