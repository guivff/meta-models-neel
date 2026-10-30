"""Narrowed R2-B capture -> pool fit -> ablation scoring pipeline.

External booking/guard bootstrap and verified Mac release remain mandatory.
This module never creates, stops, or terminates a pod.
"""
from __future__ import annotations
import time
from pathlib import Path
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_runner as R,remainder_r2b_fit as F,remainder_r2b_slice as S


def run_slice(plan,root,process,engine,guard,fit_jobs=F.fit_jobs,clock=time.monotonic):
    cells=plan['cells'];jobs=plan['probe_jobs'];transfers=plan['transfer_jobs']
    if not cells or any(c['reader']!='olens' or c['arm']!='natural' or c.get('generate') for c in cells):
        raise ValueError(f'Slice capture contains an unsupported reader/arm/generation cell: {cells}')
    root=Path(root);outputs=[]
    def write_phase(name,phase_cells,run):
        writer=R.RunWriter(root/name,dict(cells=phase_cells),process)
        for c in phase_cells:
            guard();payload,arrays=run(c);writer.append(c,payload,arrays)
        writer.finish();outputs.append(str(writer.root));return writer
    def smoke_row(writer,cell):
        try:
            guard();payload,arrays=engine.execute(cell);writer.append(cell,payload,arrays)
            return payload
        except Exception as error:
            raise ValueError(f'SMOKE FAILED: {cell.get("cohort",cell.get("dataset"))} {cell["arm"]}: {error}') from error
    def finish_smoke(writer):
        try:writer.finish()
        except Exception as error:raise ValueError(f'SMOKE FAILED: {error}') from error
    try:
        # Warm-up load is timed inside the booking, before measured per-item smoke.
        guard()
        if hasattr(engine,'load'):engine.load()
        smoke_by_group={}
        for c in cells:smoke_by_group.setdefault((c['dataset'],c['split']),c)
        initial=list(smoke_by_group.values())
        stamp=dict(process,run_kind='smoke')
        initial_writer=R.RunWriter(root/'capture_smoke',dict(cells=initial),stamp)
        began=clock()
        for c in initial:
            smoke_row(initial_writer,c)
        finish_smoke(initial_writer);outputs.append(str(initial_writer.root))
        per_item=(clock()-began)/len(initial)
        # Reserve a disclosed fitting allowance until the real fit timing is known.
        estimated_forwards=len(cells)+len(S.ARMS)*sum(c['split']=='test' for c in cells)
        projected=1.5*per_item*estimated_forwards+plan.get('fit_reserve_seconds',1800)
        guard()
        if hasattr(guard,'booking'):
            b=guard.booking
            if projected>=b['segment_deadline']-time.time()-guard.pull_reserve:
                raise ValueError(f'Full slice projection does not fit: {projected:.1f}s; retain smoke and wait')
        # One process stamp is shared by its own phase writers, never by a child.
        capture=write_phase('capture',cells,engine.execute)
        # Source probes use the exact bound source44 vectors without a second model load.
        source_cells=[dict(c,reader='source',tap_blocks=[44]) for c in cells]
        source_keys={R.cell_key(c):R.cell_key(sc) for c,sc in zip(cells,source_cells)}
        source=write_phase('source',source_cells,engine.source)
        source_records=F.read_process(source.root,process['run_kind'])
        source_jobs=[];source_cohorts=set()
        for job in jobs:
            if job['cohort'] in source_cohorts:continue
            source_cohorts.add(job['cohort'])
            source_jobs.append(dict(job_id=job['cohort']+':source44',cohort=job['cohort'],block=44,
                train=[source_keys[k] for k in job['train']],evaluate=[source_keys[k] for k in job['evaluate']]))
        for job in transfers:
            source_jobs.append(dict(job_id=job['cohort']+':source44-transfer',cohort=job['cohort'],block=44,
                selection='forward-block transfer',train=[source_keys[k] for k in job['train']],
                evaluate=[source_keys[k] for k in job['evaluate']]))
        source_fits,source_predictions=fit_jobs(source_jobs,source_records,guard)
        source_lookup={f['job_id']:f for f in source_fits}
        write_phase('source_fits',source_jobs,lambda j:({'fit':source_lookup[j['job_id']],
            'predictions':[p for p in source_predictions if p['job_id']==j['job_id']]},{}))
        records=F.read_process(capture.root,process['run_kind'])
        started=clock();fits,predictions=fit_jobs(jobs,records,guard)
        selected=S.select_fits(fits,jobs)
        derived=S.transfer_jobs(transfers,selected,cells[0]['tap_blocks'])
        if derived:
            extra,extra_predictions=fit_jobs(derived,records,guard)
            fits+=extra;predictions+=extra_predictions
            for fit in extra:
                if not next(j['selected_for_causal'] for j in derived if j['job_id']==fit['job_id']):continue
                cohort=next(j['cohort'] for j in derived if j['job_id']==fit['job_id'])
                if cohort in selected:raise ValueError(f'Duplicate transfer cohort: {cohort}')
                selected[cohort]=fit
        all_jobs=jobs+derived
        fit_by_id={f['job_id']:f for f in fits}
        fit_writer=write_phase('fits',all_jobs,lambda j:({'fit':fit_by_id[j['job_id']],
            'predictions':[p for p in predictions if p['job_id']==j['job_id']]},{}))
        # Stored fits precede any held-out causal model forward.
        causal=S.causal_cells(selected,cells)
        if {c['arm'] for c in causal}!=set(S.ARMS):raise ValueError('Incomplete derived causal arms')
        # Smoke has its own run_kind and path; the per-process run_id is unchanged.
        first={}
        for c in causal:first.setdefault((c['cohort'],c['arm']),c)
        smoke_cells=list(first.values())
        smoke_stamp=dict(process,run_kind='smoke')
        smoke=R.RunWriter(root/'causal_smoke',dict(cells=smoke_cells),smoke_stamp)
        start=clock();smoke_payloads={}
        for c in smoke_cells:
            payload=smoke_row(smoke,c)
            smoke_payloads[(c['cohort'],c['arm'])]=payload
        finish_smoke(smoke);elapsed=clock()-start;outputs.append(str(smoke.root))
        import math
        for cohort in selected:
            a=smoke_payloads[(cohort,'mean_ablation')].get('displacement')
            b=smoke_payloads[(cohort,'random_ablation')].get('displacement')
            if a is None or b is None or not math.isclose(a['intended_l2'],b['intended_l2'],rel_tol=1e-5,abs_tol=1e-6):
                raise ValueError(f'SMOKE FAILED: equal-norm control {cohort}')
        # Conservative measured causal projection; budget check includes pull reserve.
        projection=1.5*elapsed*len(causal)/len(smoke_cells)
        guard()
        if hasattr(guard,'booking'):
            b=guard.booking
            if projection>=b['segment_deadline']-time.time()-guard.pull_reserve:
                raise ValueError(f'Causal projection does not fit: {projection:.1f}s; retain capture/fits/smoke')
        scored=write_phase('causal',causal,engine.execute)
        from projects.g_agreement.r_bench import remainder_r2b_analysis as A
        from projects.g_agreement.r_bench.remainder_r2b_prepare import lines
        pairs=A.paired_items(list(lines(scored.root/'rows.jsonl')))
        cohorts={}
        for row in pairs:
            key=(row['population'],row['recipe'],row['selection'])
            cohorts.setdefault(key,[]).append(row)
        analysis_cells=[dict(population=k[0],recipe=k[1],selection=k[2]) for k in sorted(cohorts)]
        write_phase('analysis',analysis_cells,lambda c:({'contrasts':A.summarize(cohorts[(c['population'],c['recipe'],c['selection'])])},{}))
        return dict(process_dirs=outputs,selected_fit_sha256={k:D.digest(v) for k,v in selected.items()},
                    fit_wall_s=clock()-started,causal_projection_s=projection,
                    causal_dir=str(scored.root),fit_dir=str(fit_writer.root))
    finally:engine.close()
