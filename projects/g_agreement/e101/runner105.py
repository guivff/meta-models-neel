"""§214 supplied-vector logits entry point on E101/E79 runtime and custody."""
from collections import Counter
import numpy as np
from .contract import read,write,sha
from .timing import profile_receipt
from projects.g_agreement.e105 import inputs as owner,scoring


def load(root):
    items,vectors,manifest=owner.load(root,sha(root/'INPUT_SEAL.json'))
    return items,dict(vectors=vectors,manifest=manifest)


def jobs(items):
    result=[]
    for condition in ('T','S','0'):
        ix=[i for i,x in enumerate(items) if x['condition']==condition]
        for group in scoring.batches([items[i] for i in ix]):
            result.append(dict(kind='logits_'+condition,indices=[ix[i] for i in group]))
    return result


def stratum(job,items):
    return (job['kind'],len(job['indices']),tuple((items[i]['row'],len(items[i]['ids']),
            tuple(tuple(len(c) for c in pair) for pair in items[i]['candidate_ids'])) for i in job['indices']))


def acquire(items,data,runtime,clock,out,timing=False):
    planned=jobs(items);vectors=data['vectors'];manifest=data['manifest'];done=[];profiles=[];pointers={}
    write(out/'RUN.json',dict(experiment='E105',stage='test',timing_only=timing,seed=owner.SEED,
          block=44,conditions=['T','S','0'],supplied_vector_mode=True,baseline_mode='unpatched',
          behaviour_mode='frozen_continuation',frozen_scorer_sha256=owner.frozen()['scorer_sha256'],
          manifest=manifest,reader_calls=0))
    write(out/'JOB_GRID.json',planned);(out/'jobs').mkdir()
    clock.call('base_setup',runtime.load_base)
    for condition in ('T','S','0'):
        phase='logits_'+condition;indices=[i for i,j in enumerate(planned) if j['kind']==phase]
        if not indices:raise ValueError('all T/S/0 conditions required')
        first=items[planned[indices[0]]['indices'][0]]
        dummy=dict(first,id='SYNTHETIC_DISCARDED',ids=[1]*len(first['ids']),
                   candidate_ids=[[[1]*len(c) for c in pair] for pair in first['candidate_ids']],
                   vector_index=None if condition=='0' else 0)
        dim=vectors.shape[1];warm_vectors=np.zeros((1,dim),dtype=np.float32)
        def warm():
            model,_,cm=runtime.subject()
            with cm:return scoring.score_batch(model,[dummy],warm_vectors)
        clock.call(phase+'_warmup_discarded',warm);clock.cost={phase:[]}
        counts=Counter(stratum(planned[i],items) for i in indices);seconds={};phase_done=set()
        for n,i in enumerate(indices):
            job=planned[i];key=stratum(job,items)
            if timing and key in seconds:continue
            xs=[items[k] for k in job['indices']]
            def call():
                model,_,cm=runtime.subject()
                with cm:return scoring.score_batch(model,xs,vectors)
            rr=clock.call(phase,call)
            if [r['id'] for r in rr]!=[x['id'] for x in xs]:raise ValueError('exact E105 output alignment')
            member=f'jobs/{i:06d}.json'
            write(out/member,[dict(r,channel='logits',gpu_type=runtime.hardware_assignment['gpu_type']) for r in rr])
            seconds.setdefault(key,[]).append(clock.events[-1]['seconds']);done.append(i);phase_done.add(n)
            for k,r in enumerate(rr):
                conditions=pointers.setdefault(r['inventory_id'],{})
                if condition in conditions:raise ValueError('duplicate condition source')
                conditions[condition]=dict(member=member,keys=[k,'pair_logprobs'])
            from admission import atomic
            atomic(out/'COMPLETED.json',done)
            if not timing and not clock.forecast([dict(kind=phase) for _ in indices],phase_done):return 'NO_FIT'
        profiles.append(dict(phase=phase,jobs=len(indices),sample_seconds=list(clock.cost[phase]),
              mean_job_seconds=sum(counts[k]*float(np.mean(v)) for k,v in seconds.items())/len(indices)))
    if timing:
        write(out/'SMOKE_COVERAGE.json',dict(status='PASS',conditions=['T','S','0'],strata=sum(len(set(stratum(j,items) for j in planned if j['kind']==p['phase'])) for p in profiles)))
        write(out/'MEASURED_PROFILE.json',profile_receipt(clock.events,profiles))
        return 'TIMING_ONLY'
    expected={x['inventory_id'] for x in items}
    if set(pointers)!=expected or any(set(v)!={'T','S','0'} for v in pointers.values()):raise ValueError('complete original condition grid')
    write(out/'MEASUREMENT_INDEX.json',[dict(id=k,conditions=v) for k,v in sorted(pointers.items())])
    return 'COMPLETE'


def main():
    import sys
    if sys.argv[1:]==['--cpu-import-preflight']:
        from .preflight105 import runtime_import
        from .runner import ROOT
        print(runtime_import(ROOT));return
    from .operational import run
    run('E105',load,acquire,['text'],seed=owner.SEED)

if __name__=='__main__':main()
