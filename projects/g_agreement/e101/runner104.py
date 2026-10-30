"""§213 acquisition using E101's runtime, native Oracle and E79 measured Clock."""
from pathlib import Path
import numpy as np
from .contract104 import read,write,sha,validate,SEED
from .intervention104 import behaviour104
from .timing import profile_receipt


def load(root):
    seal=read(root/'INPUT_SEAL.json');m=read(root/'MANIFEST.json')
    expected={'MANIFEST.json','SCORER.json','items.json','deltas.npy'}
    if (seal['experiment']!='E104' or seal['labels_on_pod'] is not False or set(seal['files'])!=expected
        or {p.name for p in root.iterdir()}!=expected|{'INPUT_SEAL.json'}):raise ValueError('only sealed public E104 members')
    if m['behaviour_scorer_sha256']!=sha(root/'SCORER.json'):raise ValueError('frozen scorer identity')
    scorer=read(root/'SCORER.json');implementation=scorer['implementation']
    from .runner import ROOT
    if (scorer['score_field']!='pair_logits' or scorer['aggregation']!='mean(A-B)' or scorer['candidate_requirement']!='all_single_token'
        or implementation['path']!='projects/g_agreement/e101/acquisition.py'
        or sha(ROOT/implementation['path'])!=implementation['sha256']):raise ValueError('actual E101 frozen scorer source')
    if m['read_block']!=44 or m['status']!='FROZEN_READY':raise ValueError('registered read site/input state')
    if m['stage']=='test' and (not m['dose_commit'] or not m['dose_sha256']):raise ValueError('committed arm/row doses required')
    xs=read(root/'items.json');deltas=np.load(root/'deltas.npy',allow_pickle=False);validate(xs,deltas,m)
    return xs,dict(deltas=deltas,manifest=m)


def groups(items,size=8):
    buckets={}
    for i,x in enumerate(items):
        key=(x['arm'],x['row'],x['alpha'],x['condition'],len(x['ids']),tuple(tuple(len(c) for c in p) for p in x['candidate_ids']))
        buckets.setdefault(key,[]).append(i)
    return [v[k:k+size] for _,v in sorted(buckets.items()) for k in range(0,len(v),size)]


def jobs(items,stage):
    jj=[]
    for indices in groups(items):
        x=items[indices[0]]
        jj.append(dict(kind='logits',indices=indices,arm=x['arm'],row=x['row'],alpha=x['alpha'],condition=x['condition']))
    if stage=='test':jj.extend(dict(j,kind='oracle',source_job=i) for i,j in enumerate(list(jj)))
    return jj


def acquire(items,data,runtime,clock,out,timing=False):
    m=data['manifest'];deltas=data['deltas'];planned=jobs(items,m['stage']);profile=[];done=[]
    write(out/'JOB_GRID.json',planned);write(out/'RUN.json',dict(experiment='E104',stage=m['stage'],seed=SEED,cells=m['cells'],
        dose_sha256=m.get('dose_sha256'),dose_commit=m.get('dose_commit'),behaviour_scorer_sha256=m['behaviour_scorer_sha256'],
        dose_score_field='pair_logits',norm_convention=m['norm_convention'],U_hook=m['U_hook'],N_hook=m['N_hook']))
    (out/'jobs').mkdir();(out/'read_vectors').mkdir()
    gpu=getattr(runtime,'hardware_assignment',{}).get('gpu_type','CPU_SYNTHETIC')
    for phase in ('logits','oracle'):
        indices=[i for i,j in enumerate(planned) if j['kind']==phase]
        if not indices:continue
        clock.call(phase+'_setup',runtime.load_base if phase=='logits' else runtime.load_oracle)
        def warm():
            if phase=='oracle':return runtime.readers.native_one('oracle',np.random.default_rng(SEED).standard_normal((1,deltas.shape[1])).astype(np.float32))
            first=items[planned[indices[0]]['indices'][0]];x=dict(first,ids=[1]*len(first['ids']))
            model,_,cm=runtime.subject()
            with cm:return behaviour104(model,[x],np.zeros((1,deltas.shape[1]),np.float32))
        clock.call(phase+'_warmup_discarded',warm)
        clock.cost={phase:[]};phase_jobs=[dict(kind=phase) for _ in indices];phase_done=set();seen=set();stratum_seconds={};counts={}
        def stratum(job):
            x=items[job['indices'][0]]
            return (job['arm'],job['row'],job['alpha'],job['condition'],len(job['indices']),len(x['ids']),tuple(tuple(len(c) for c in p) for p in x['candidate_ids']))
        for i in indices:counts[stratum(planned[i])]=counts.get(stratum(planned[i]),0)+1
        for n,i in enumerate(indices):
            j=planned[i];key=stratum(j)
            if timing and key in seen:continue
            seen.add(key);xs=[items[k] for k in j['indices']]
            def call():
                if phase=='logits':
                    d=deltas[j['indices']].copy();before=d.tobytes();model,_,cm=runtime.subject()
                    with cm:records,vectors=behaviour104(model,xs,d)
                    if d.tobytes()!=before:raise ValueError('signed deltas mutated')
                    if m['stage']=='test':np.save(out/'read_vectors'/f'{i:06d}.npy',vectors,allow_pickle=False)
                    return [dict(id=x['id'],base_id=x['base_id'],item_id=x['base_id'],row=x['row'],arm=x['arm'],split=m['stage'],reader='subject' if phase=='logits' else 'oracle',alpha=x['alpha'],condition=x['condition'],channel=phase,gpu_type=gpu,behaviour_scorer_sha256=m['behaviour_scorer_sha256'],**r) for x,r in zip(xs,records)]
                source=j['source_job'];vectors=np.load(out/'read_vectors'/f'{source:06d}.npy',allow_pickle=False);before=vectors.tobytes()
                rr=runtime.readers.native_one('oracle',vectors)
                if len(rr)!=len(xs) or any(len(v)!=1 for v in rr) or vectors.tobytes()!=before:raise ValueError('one unchanged native Oracle input per cell')
                logit_records=read(out/'jobs'/f'{source:06d}.json')
                if [r['id'] for r in logit_records]!=[x['id'] for x in xs]:raise ValueError('Oracle/capture exact cell alignment')
                return [dict(id=x['id'],base_id=x['base_id'],item_id=x['base_id'],row=x['row'],arm=x['arm'],split=m['stage'],reader='subject' if phase=='logits' else 'oracle',alpha=x['alpha'],condition=x['condition'],channel=phase,gpu_type=gpu,
                    norm_source_job=source,norm_ratio=l['norm_ratio'],read_norm_ratio=l['read_norm_ratio'],injection_sites=l['injection_sites'],read_site=l['read_site'],**r[0]) for x,r,l in zip(xs,rr,logit_records)]
            records=clock.call(phase,call)
            if len(records)!=len(xs):raise ValueError('E104 output alignment')
            write(out/'jobs'/f'{i:06d}.json',records);done.append(i);phase_done.add(n)
            stratum_seconds.setdefault(key,[]).append(clock.events[-1]['seconds'])
            from admission import atomic
            atomic(out/'COMPLETED.json',done)
            if not timing and not clock.forecast(phase_jobs,phase_done):return 'NO_FIT'
        profile.append(dict(phase=phase,jobs=len(indices),sample_seconds=list(clock.cost[phase]),
            mean_job_seconds=sum(counts[k]*float(np.mean(v)) for k,v in stratum_seconds.items())/len(indices)))
    if timing:write(out/'MEASURED_PROFILE.json',profile_receipt(clock.events,profile))
    return 'TIMING_ONLY' if timing else 'COMPLETE'


def main():
    import sys
    if sys.argv[1:]==['--cpu-import-preflight']:
        from .preflight104 import runtime_import
        from .runner import ROOT
        print(runtime_import(ROOT));return
    if any(x=='--capture-dev40' or x.startswith('--capture-dev40=') for x in sys.argv[1:]):
        from .capture104 import main as capture_main
        return capture_main()
    from .operational import run
    run('E104',load,acquire,['oracle'],seed=SEED)
if __name__=='__main__':main()
