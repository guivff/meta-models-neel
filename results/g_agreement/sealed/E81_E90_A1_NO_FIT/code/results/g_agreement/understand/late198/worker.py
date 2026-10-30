"""Sections 198/199: public acquisition, CPU gates, capture seal, CPU probes, readers."""
import argparse
import os
import signal
import threading
import time
from pathlib import Path
import numpy as np
from contract import *

class NoFit(RuntimeError):
    pass

def batches(items, size=8, equal_length=False):
    if not equal_length:
        return [items[i:i+size] for i in range(0, len(items), size)]
    groups = {}
    for item in items:
        groups.setdefault(len(item['ids']), []).append(item)
    return [xs[i:i+size] for _, xs in sorted(groups.items()) for i in range(0, len(xs), size)]

class Clock:
    def __init__(self, out, end, seeds, backend):
        self.out, self.end, self.seeds, self.backend = out, end, seeds, backend
        self.events, self.observed, self.remaining = [], {}, {}

    def check(self):
        if time.time() >= self.end - 60:
            raise NoFit('absolute deadline / retrieval reserve')

    def call(self, phase, fn, real=False):
        self.check()
        self.backend.sync()
        started = time.monotonic()
        try:
            result = fn()
            self.backend.sync()
        except BaseException:
            self.events.append(dict(phase=phase, seconds=time.monotonic()-started, status='FAILED', real=real))
            write(self.out/'PHASE_TIMINGS.json', self.events, replace=True)
            raise
        elapsed = time.monotonic()-started
        self.events.append(dict(phase=phase, seconds=elapsed, status='COMPLETE', real=real))
        write(self.out/'PHASE_TIMINGS.json', self.events, replace=True)
        if real:
            self.observed.setdefault(phase, []).append(elapsed)
        return result

    def admit(self):
        self.check()
        means = {p: float(np.mean(self.observed[p])) if self.observed.get(p) else self.seeds[p]
                 for p, n in self.remaining.items() if n}
        estimate = 1.25 * sum(n * means[p] for p, n in self.remaining.items() if n)
        fits = time.time() + estimate < self.end - 60
        write(self.out/'FORECAST.json', dict(status='ADMIT' if fits else 'NO_FIT',
            estimator='running mean of real batches; initial seeds for unobserved phases',
            remaining=self.remaining, seconds_per_batch=means, remaining_forecast_seconds=estimate,
            margin=1.25, deadline_epoch=self.end, warmups_excluded=True), replace=True)
        if not fits:
            raise NoFit('remaining running-mean forecast does not fit')

def ready_stage(out, stage, binding):
    digest_value = seal(out/stage, 'STAGE_SEAL.json', **binding, stage=stage, status='COMPLETE')
    ready = dict(binding, stage_seal_sha256=digest_value, ready_epoch=time.time())
    write(out/(stage.upper()+'_READY.json'), ready)
    return ready

def await_release(path, ready, allowed, clock, forecast=False, probe=False):
    while not path.exists():
        clock.check()
        time.sleep(1)
    release = read(path)
    ids = check_release(release, ready, allowed, time.time(), forecast, probe)
    write(clock.out/(path.stem+'_RECEIPT.json'), release)
    return ids

def initial_work(exp, items, score_items, downstream):
    work = {}
    if exp == 'E81':
        return dict(base_setup=1, base_text=len(batches(items, equal_length=True)))
    if exp != 'E83':
        work.update(base_setup=1, capture=len(batches(items)))
    if score_items:
        work['next_token'] = len(batches(score_items, equal_length=True))
    if downstream:
        work['downstream'] = len(batches(downstream, equal_length=True))
    n = sum(x['split'] == 'test' for x in items)
    work.update(oracle_setup=1, oracle_native=n if exp == 'E83' else (n+7)//8)
    if exp != 'E83':
        work.update(nla_setup=1, nla_native=(n+7)//8)
    return work

def acquire(inp, plan, items, scores, downstream, b, c, out, binding, release_fn):
    exp = plan['experiment']
    c.remaining = initial_work(exp, items, scores, downstream)
    if exp != 'E83':
        c.call('base_setup', b.load_base)
        c.remaining['base_setup'] = 0
    if exp == 'E81':
        b.check_tokens(items)
        c.call('base_text_warmup_discarded', lambda: b.text(b.synthetic()))
        stage = out/'text'; stage.mkdir()
        for i, chunk in enumerate(batches(items, equal_length=True)):
            values = c.call('base_text', lambda: b.text([x['ids'] for x in chunk]), real=True)
            require(len(values) == len(chunk), 'text output count')
            write(stage/f'{i:06d}.json', [dict(id=x['id'], feature=x['feature'], arm=x['arm'], **v) for x,v in zip(chunk,values)])
            c.remaining['base_text'] -= 1
            c.admit()
        ready_stage(out, 'text', binding)
        return
    if scores:
        b.check_tokens(scores)
        c.call('next_token_warmup_discarded', lambda: b.next_token(b.synthetic()))
        stage = out/'behaviour'; stage.mkdir()
        for i, chunk in enumerate(batches(scores, equal_length=True)):
            values = c.call('next_token', lambda: b.next_token([x['ids'] for x in chunk]), real=True)
            require(len(values) == len(chunk), 'next-token output count')
            write(stage/f'{i:06d}.json', [dict(id=x['id'], **v) for x,v in zip(chunk,values)])
            c.remaining['next_token'] -= 1
            c.admit()
        ready = ready_stage(out, 'behaviour', binding)
        keep = release_fn('SELECTION_GO', ready, [x['id'] for x in items], False, False)
        items = [x for x in items if x['id'] in set(keep)]
        require(items, 'no eligible items; stop before capture/readers')
        c.remaining['capture'] = len(batches(items))
    if exp == 'E83':
        # Frozen owner export contains only read-position vectors and opaque item order.
        vectors = np.load(inp/'acts44.npy', allow_pickle=False)
        require(vectors.shape == (len(items),5120) and np.isfinite(vectors).all(), 'sealed E83 vector grid')
        acts = {44: vectors}
    else:
        stage = out/'capture'; stage.mkdir()
        c.call('capture_warmup_discarded', b.warm_capture)
        parts = {42: [], 44: []}
        for chunk in batches(items):
            got = c.call('capture', lambda: b.capture(chunk), real=True)
            for layer in parts:
                require(got[layer].shape == (len(chunk),5120) and np.isfinite(got[layer]).all(), 'capture dimensions')
                parts[layer].append(got[layer])
            c.remaining['capture'] -= 1
            c.admit()
        acts = {l: np.concatenate(v) for l,v in parts.items()}
        for layer,h in acts.items():
            # Seal the exact float32 values subsequently supplied to each native adapter.
            np.save(stage/f'acts{layer}.npy', h)
        write(stage/'items.order.json', [x['id'] for x in items])
        write(stage/'POSITIONS.json', [dict(id=x['id'], read_index=x['read_index']) for x in items])
        ready = ready_stage(out, 'capture', binding)
        # All dev-fit probes and truth/belief labels remain on CPU. No readout before receipt.
        allowed = [x['id'] for x in items if x['split']=='test']
        keep = release_fn('READERS_GO', ready, allowed, plan['forecast_required'], True)
        if downstream:
            b.check_tokens(downstream)
            c.call('downstream_warmup_discarded', lambda: b.text(b.synthetic()))
            stage = out/'downstream'; stage.mkdir()
            for i, chunk in enumerate(batches(downstream, equal_length=True)):
                values = c.call('downstream', lambda: b.text([x['ids'] for x in chunk]), real=True)
                require(len(values)==len(chunk), 'downstream output count')
                write(stage/f'{i:06d}.json', [dict(id=x['id'],**v) for x,v in zip(chunk,values)])
                c.remaining['downstream'] -= 1
                c.admit()
            ready_stage(out, 'downstream', binding)
        indices = [i for i,x in enumerate(items) if x['id'] in set(keep)]
        items = [items[i] for i in indices]
        acts = {l:h[indices] for l,h in acts.items()}
    selected = list(range(len(items)))
    n = len(selected) if exp=='E83' else (len(selected)+7)//8
    c.remaining['oracle_native'] = n
    if exp != 'E83':
        c.remaining['nla_native'] = n
    if not selected:
        write(out/'NOT_EVALUABLE.json', dict(reason='CPU gates released no reader items'))
        return
    for reader in (('oracle',) if exp=='E83' else ('oracle','nla')):
        c.call(reader+'_setup', b.load_oracle if reader=='oracle' else b.load_nla)
        c.remaining[reader+'_setup'] = 0
        sampled = exp=='E83'
        dummy = np.random.default_rng(plan['seed']).standard_normal((1 if sampled else 8,5120)).astype(np.float32)
        c.call(reader+'_warmup_discarded', lambda: b.native(reader,dummy,sampled))
        # Reset after synthetic sampling: warm-up never consumes the scientific random stream.
        if sampled:
            b.seed(plan['seed'])
        stage = out/reader; stage.mkdir()
        size = 1 if sampled else 8
        for i in range(0,len(items),size):
            units = items[i:i+size]
            h = acts[44 if reader=='oracle' else 42][i:i+size].copy()
            before = h.tobytes()
            groups = c.call(reader+'_native', lambda: b.native(reader,h,sampled), real=True)
            require(h.tobytes()==before and len(groups)==len(units)
                    and all(len(g)==(8 if sampled else 1) for g in groups), 'unaltered vectors/readout grid')
            records = [dict(id=x['id']+':'+reader+':'+str(k), unit_id=x['id'], feature=x['feature'],
                            arm=x['arm'], reader=reader, repeat=k, **v)
                       for x,g in zip(units,groups) for k,v in enumerate(g)]
            write(stage/f'{i//size:06d}.json',records)
            c.remaining[reader+'_native'] -= 1
            c.admit()
        ready_stage(out, reader, binding)
        if reader=='nla':
            records=[x for f in sorted(stage.glob('[0-9]*.json')) for x in read(f)]
            rows={}
            for x in records:
                r=rows.setdefault(x['feature'],dict(n=0,truncated=0))
                r['n']+=1; r['truncated']+=int('</explanation>' not in x['raw'])
            for r in rows.values():r['rate']=r['truncated']/r['n']
            write(out/'NLA_TRUNCATION.json',rows)

def preflight(a):
    verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for name,h in read(HERE/'DEPENDENCIES.json').items():
        require(sha(ROOT/name)==h,'source dependency '+name)
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    require(not s.get('synthetic',False) or a.dry_run,'synthetic fixture cannot launch production')
    plan=read(a.inputs/'PLAN.json'); items=read(a.inputs/'items.json')
    scores=read(a.inputs/'SCORE_ITEMS.json'); downstream=read(a.inputs/'DOWNSTREAM.json')
    exp=validate_plan(plan,items,scores,downstream)
    limits=read(a.inputs/'STAGE_REQUEST.json')
    require(limits['status']=='READY' and limits['experiment']==exp,'sealed READY stage request')
    expected={'PLAN.json','items.json','SCORE_ITEMS.json','DOWNSTREAM.json','STAGE_REQUEST.json'}
    if exp=='E83':expected.add('acts44.npy')
    require(set(s['files'])==expected,'pod input allowlist')
    require({str(p.relative_to(a.inputs)) for p in a.inputs.rglob('*') if p.is_file()}==expected|{'INPUT_SEAL.json'},'no extra private files')
    ass=read(a.assignment); end=deadline(ass,limits,time.time())
    read(a.assets)
    return plan,items,scores,downstream,limits,ass,end

def main():
    p=argparse.ArgumentParser()
    for key in ('inputs','assets','assignment','out','releases'):p.add_argument('--'+key,type=Path,required=True)
    for key in ('source-sha','input-sha'):p.add_argument('--'+key,required=True)
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(); plan,items,scores,downstream,limits,ass,end=preflight(a)
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
    if a.dry_run:
        from test_worker import TinyRuntime
        b=TinyRuntime()
    else:
        from runtime import Runtime
        b=Runtime(a.assets)
    c=Clock(a.out,end,limits['seed_seconds_per_batch'],b)
    binding=dict(experiment=plan['experiment'],pod_id=ass['pod_id'],source_seal_sha256=a.source_sha,
                 input_seal_sha256=a.input_sha,synthetic=a.dry_run)
    def release(name,ready,allowed,forecast,probe):
        if a.dry_run:
            v={k:ready[k] for k in ('experiment','pod_id','source_seal_sha256','input_seal_sha256','stage_seal_sha256')}
            v.update(released_ids=allowed,issued_epoch=time.time(),authorized=True,cpu_receipt_sha256='a'*64)
            if forecast:v.update(forecast_commit='b'*40,forecast_seal_sha256='c'*64)
            if probe:v['probe_seal_sha256']='d'*64
            check_release(v,ready,allowed,time.time(),forecast,probe)
            write(a.out/(name+'_RECEIPT.json'),v)
            return allowed
        return await_release(a.releases/(name+'.json'),ready,allowed,c,forecast,probe)
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    status='COMPLETE'
    try:
        acquire(a.inputs,plan,items,scores,downstream,b,c,a.out,binding,release)
    except NoFit as e:
        status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(e),retained_pilots=True))
    except BaseException as e:
        write(a.out/'FAILURE.json',dict(reason=str(e),type=type(e).__name__));raise
    finally:
        timer.cancel()
    if a.dry_run:write(a.out/'DRY_RUN.json',dict(status=status,GPU_calls=0))
    seal(a.out,'OUTPUT_SEAL.json',**binding,status=status)

if __name__=='__main__':main()
