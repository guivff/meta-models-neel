"""§222 E104 U hook, five downstream read sites, E87 greedy layer sweep."""
import importlib.util,sys
from collections import Counter
from pathlib import Path
import numpy as np
from .contract109 import load,CAPTURE,READ,SEED,write,read,sha
from .runner import ROOT
from .intervention104 import intervene_forward
from .timing import profile_receipt


def backend87():
    path=ROOT/'results/g_agreement/understand/e87/worker87.py'
    spec=importlib.util.spec_from_file_location('_e109_e87',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module.Backend87


def natural_capture(model,items):
    import torch
    from mats.capture import decoder_blocks
    blocks=decoder_blocks(model);values={l:[] for l in CAPTURE};handles=[]
    if not items or len({len(x['ids']) for x in items})!=1:raise ValueError('equal unpadded prompts')
    def hook(layer):
        def observe(module,args,output):
            z=output[0] if isinstance(output,tuple) else output
            values[layer].append(torch.stack([z[i,x['read_index']].float() for i,x in enumerate(items)]).detach().cpu().numpy())
        return observe
    try:
        for layer in CAPTURE:handles.append(blocks[layer].register_forward_hook(hook(layer)))
        ids=torch.tensor([x['ids'] for x in items],device=model.get_input_embeddings().weight.device)
        with torch.inference_mode():model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=1)
    finally:
        for h in handles:h.remove()
    if any(len(v)!=1 or not np.isfinite(v[0]).all() for v in values.values()):raise ValueError('one finite natural capture per layer')
    return {l:v[0] for l,v in values.items()}


def capture_batch(model,items,deltas):
    """One natural pass, then two E104 U passes, sharing natural44 for norms."""
    groups={c:[x for x in items if x['condition']==c] for c in ('unhooked','steered','random')}
    baseline=groups['unhooked'];keys=[x['base_id'] for x in baseline]
    if any([x['base_id'] for x in xs]!=keys for xs in groups.values()):raise ValueError('aligned three-condition batch')
    natural=natural_capture(model,baseline);values={'unhooked':natural};metrics={'unhooked':[dict(injection_sites=[],hook_installed=False) for _ in baseline]}
    for condition in ('steered','random'):
        xs=groups[condition];d=deltas[[x['delta_index'] for x in xs]].copy();before=d.tobytes()
        captures={l:[] for l in CAPTURE}
        _,mm,_=intervene_forward(model,[x['ids'] for x in xs],[x['read_index'] for x in xs],d,'U',1,
                  captures=captures,natural_read=natural[44])
        if d.tobytes()!=before or any(len(v)!=1 or not np.isfinite(v[0]).all() for v in captures.values()):raise ValueError('unchanged signed deltas and complete captures')
        values[condition]={l:v[0] for l,v in captures.items()};metrics[condition]=[dict(m,hook_installed=True) for m in mm]
    arrays={l:np.concatenate([values[c][l] for c in groups],axis=0) for l in CAPTURE};records=[]
    for condition,xs in groups.items():
        for k,x in enumerate(xs):
            norms={}
            for layer in CAPTURE:
                before=float(np.linalg.norm(natural[layer][k].astype(np.float64)));after=float(np.linalg.norm(values[condition][layer][k].astype(np.float64)))
                if min(before,after)<=0 or not np.isfinite([before,after]).all():raise ValueError('finite observed read norms')
                norms[str(layer)]=dict(before_norm=before,after_norm=after,norm_ratio=after/before)
            records.append(dict(x,read_norms=norms,**metrics[condition][k]))
    return records,arrays


def jobs(items,size=8):
    groups={}
    for i,x in enumerate(items):
        if x['condition']=='unhooked':groups.setdefault((x['row'],x['split'],len(x['ids'])),[]).append(i)
    index={(x['row'],x['split'],x['base_id'],x['condition']):i for i,x in enumerate(items)};jj=[]
    for _,indices in sorted(groups.items()):
        for start in range(0,len(indices),size):
            base=[items[i] for i in indices[start:start+size]]
            ix=[index[(x['row'],x['split'],x['base_id'],c)] for c in ('unhooked','steered','random') for x in base]
            jj.append(dict(kind='capture',indices=ix))
    for layer in READ:
        for source,j in enumerate(list(jj)):
            if j['kind']!='capture':continue
            ix=[k for k,i in enumerate(j['indices']) if items[i]['split']=='test' and items[i]['condition']!='unhooked']
            if ix:jj.append(dict(kind=f'oracle_{layer}',layer=layer,source_job=source,vector_indices=ix,indices=[j['indices'][k] for k in ix]))
    return jj


def export_arrays(items,index,out):
    """Lossless raw capture copies in original item order for frozen CPU probes."""
    by_id={x['id']:x for x in index};cache={};arrays={};order={}
    (out/'arrays').mkdir()
    for row in sorted({x['row'] for x in items}):
        arrays[row]={};order[row]={}
        for split in ('dev','test'):
            arrays[row][split]={}
            natural=[x for x in items if x['row']==row and x['split']==split and x['condition']=='unhooked']
            order[row][split]=[x['base_id'] for x in natural]
            for condition in ('unhooked','steered','random'):
                xs=[x for x in items if x['row']==row and x['split']==split and x['condition']==condition]
                if [x['base_id'] for x in xs]!=order[row][split]:raise ValueError('original array condition order')
                arrays[row][split][condition]={}
                for layer in CAPTURE:
                    values=[]
                    for x in xs:
                        ref=by_id[x['id']]['layers'][str(layer)];member=ref['member']
                        if member not in cache:cache[member]=np.load(out/member,allow_pickle=False,mmap_mode='r')
                        values.append(cache[member][ref['vector_index']])
                    member=f'arrays/{row}_{split}_{condition}_{layer}.npy'
                    np.save(out/member,np.stack(values),allow_pickle=False)
                    arrays[row][split][condition][str(layer)]=dict(member=member,keys=[])
    write(out/'CAPTURE_ARRAYS.json',arrays);write(out/'ARRAY_ORDER.json',order)


def acquire(items,data,runtime,clock,out,timing=False):
    planned=jobs(items);deltas=data['deltas'];profiles=[];done=[];captured=set();index=[]
    write(out/'RUN.json',dict(experiment='E109',authority='2d470093a',seed=SEED,timing_only=timing,manifest=data['manifest'],
       capture_blocks=list(CAPTURE),oracle_blocks=list(READ),oracle_split='test',oracle_conditions=['steered','random'],native_max_new_tokens=128))
    write(out/'JOB_GRID.json',planned);(out/'jobs').mkdir();(out/'capture').mkdir()
    gpu=runtime.hardware_assignment['gpu_type'];b87=None
    for phase in ('capture',*(f'oracle_{l}' for l in READ)):
        ix=[i for i,j in enumerate(planned) if j['kind']==phase]
        if not ix:raise ValueError('all capture/read phases required')
        if phase=='capture':clock.call('base_setup',runtime.load_base)
        elif b87 is None:
            b87=backend87();clock.call('oracle_setup',runtime.load_oracle)
            trained=b87.confirm_layers(runtime)
            if not set(READ)<=set(trained):raise ValueError('trained Oracle read blocks required')
            write(out/'TRAINED_LAYERS.json',dict(requested=list(READ),trained=trained,status='PASS'))
        def warm():
            if phase=='capture':
                first=planned[ix[0]];xs=[dict(items[k],ids=[1]*len(items[k]['ids'])) for k in first['indices']]
                model,_,cm=runtime.subject()
                with cm:return capture_batch(model,xs,np.zeros_like(deltas))
            return b87.sweep(runtime,'oracle',np.random.default_rng(SEED).standard_normal((1,deltas.shape[1])).astype(np.float32),planned[ix[0]]['layer'])
        clock.call(phase+'_warmup_discarded',warm);clock.cost={phase:[]};phase_done=set();seen={}
        def stratum(j):
            x=items[j['indices'][0]]
            return (x['row'],x['split'],len(x['ids']),len(j['indices']))
        counts=Counter(stratum(planned[i]) for i in ix)
        for n,i in enumerate(ix):
            j=planned[i];key=stratum(j)
            if timing and (key in seen or phase!='capture' and j['source_job'] not in captured):continue
            xs=[items[k] for k in j['indices']]
            def call():
                if phase=='capture':
                    model,_,cm=runtime.subject()
                    with cm:return capture_batch(model,xs,deltas)
                vectors=np.load(out/'capture'/f'{j["source_job"]:06d}_{j["layer"]}.npy',allow_pickle=False)[j['vector_indices']].copy();before=vectors.tobytes()
                rr=b87.sweep(runtime,'oracle',vectors,j['layer'])
                if len(rr)!=len(xs) or vectors.tobytes()!=before:raise ValueError('one greedy unchanged Oracle input per cell')
                return [dict(id=x['id']+':oracle:'+str(j['layer']),base_id=x['base_id'],capture_id=x['id'],row=x['row'],split=x['split'],condition=x['condition'],alpha=x['alpha'],layer=j['layer'],reader='oracle',source_job=j['source_job'],source_vector=k,**r) for x,k,r in zip(xs,j['vector_indices'],rr)]
            value=clock.call(phase,call)
            if phase=='capture':
                rr,arrays=value
                if [x['id'] for x in rr]!=[x['id'] for x in xs]:raise ValueError('capture alignment')
                for layer,vectors in arrays.items():np.save(out/'capture'/f'{i:06d}_{layer}.npy',vectors,allow_pickle=False)
                captured.add(i)
                for k,r in enumerate(rr):index.append(dict(id=r['id'],base_id=r['base_id'],row=r['row'],split=r['split'],condition=r['condition'],alpha=r['alpha'],
                    layers={str(l):dict(member=f'capture/{i:06d}_{l}.npy',vector_index=k) for l in CAPTURE},metadata=dict(member=f'jobs/{i:06d}.json',record_index=k)))
            else:rr=value
            write(out/'jobs'/f'{i:06d}.json',[dict(r,gpu_type=gpu,channel=phase) for r in rr])
            done.append(i);phase_done.add(n);seen.setdefault(key,[]).append(clock.events[-1]['seconds'])
            from admission import atomic
            atomic(out/'COMPLETED.json',done)
            if not timing and not clock.forecast([dict(kind=phase) for _ in ix],phase_done):return 'NO_FIT'
        if set(seen)!=set(counts):raise ValueError('all row/split/length/batch strata measured')
        profiles.append(dict(phase=phase,jobs=len(ix),sample_seconds=list(clock.cost[phase]),mean_job_seconds=sum(counts[k]*float(np.mean(v)) for k,v in seen.items())/len(ix)))
    if timing:
        write(out/'MEASURED_PROFILE.json',profile_receipt(clock.events,profiles));return 'TIMING_ONLY'
    if len(index)!=len(items):raise ValueError('complete capture inventory')
    export_arrays(items,index,out)
    write(out/'CAPTURE_INDEX.json',index);write(out/'READOUT_INDEX.json',[dict(job=i,member=f'jobs/{i:06d}.json') for i,j in enumerate(planned) if j['kind']!='capture'])
    return 'COMPLETE'


def main():
    import sys
    if sys.argv[1:]==['--cpu-import-preflight']:
        from .preflight109 import runtime_import
        print(runtime_import(ROOT));return
    from .operational import run
    run('E109',load,acquire,['text','oracle'],seed=SEED)

if __name__=='__main__':main()
