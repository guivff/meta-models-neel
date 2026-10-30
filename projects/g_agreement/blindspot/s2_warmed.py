"""S2 operational timing adapter; frozen fidelity math, inputs and AR source stay unchanged."""
import argparse
import math
from pathlib import Path
import statistics
import time

from . import ar_tests as AR, protocol as P
from .s2_fidelity import check_source


def warmed_gate(load_seconds, timed_units, batches, elapsed, done, allocated, previous):
    """Actual load plus median of exactly three warmed production batches."""
    numbers = [load_seconds, elapsed, allocated, previous, *timed_units]
    if (len(timed_units) != 3 or not all(math.isfinite(x) for x in numbers)
        or load_seconds < 0 or elapsed < 0 or previous < 0 or allocated <= 0
        or any(x <= 0 for x in timed_units) or not 3 <= done <= batches):
        raise ValueError('invalid warmed timing evidence')
    median = statistics.median(timed_units)
    forecast = load_seconds + median*batches
    cap = min(1.5*forecast+360, 3600)
    available = min(allocated, cap-previous)
    if elapsed+1.5*median*(batches-done)+180 > available:
        raise TimeoutError('NO_FIT: warmed remaining forecast exceeds remaining science/retrieval budget')
    return {'load_seconds': load_seconds, 'timed_units_seconds': list(timed_units),
            'median_unit_seconds': median, 'forecast_seconds': forecast,
            'cap_seconds': cap, 'remaining_science_cap_seconds': available,
            'previous_gpu_seconds': previous, 'warmup_scored': False}


def collect(a):
    import numpy as np
    import torch
    from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
    check_source()
    assignment = AR._read(a.assignment)
    relative = 'projects/g_agreement/blindspot/s2_warmed.py'
    if (assignment.get('experiment') != 'S2'
        or assignment.get('entrypoint_files', {}).get(relative) != P.sha(__file__)):
        raise ValueError('S2 assignment must bind warmed timing entrypoint')
    AR._no_labels(a.texts)
    AR._verify(a.texts, 'INPUT_SEAL.json', ['texts.input.jsonl', 'definitions.json', 'provenance.json'])
    records = P.rows(a.texts/'texts.input.jsonl')
    expected, _ = AR.freeze_text_records(AR._read(a.texts/'definitions.json'))
    if records != expected or a.batch != 8:
        raise ValueError('frozen statement grid / production batch changed')
    assets = AR._assets(a.assets, ('model', 'ar'))
    batches = [records[i:i+a.batch] for i in range(0,len(records),a.batch)]
    if len(batches) < 3:
        raise ValueError('three timed production units required')
    with AR._compute('fidelity', a.assignment):
        # The load remains science, as in frozen collect_fidelity; never reset its clock.
        started = time.monotonic()
        a.out.mkdir(parents=True, exist_ok=False)
        ar, tok, _ = load_reconstructor(a.official,a.whitener,assets['ar'],assets['model'])
        load_seconds = time.monotonic()-started
        def guard():
            elapsed = time.monotonic()-started
            if elapsed >= float(assignment['allocated_gpu_seconds'])-180 or time.time() >= float(assignment['deadline_epoch'])-180:
                raise TimeoutError('S2 retrieval reserve / operator deadline')
        # One unscored warm-up through the same path. Pick longest padded batch deterministically.
        warm = max(batches,key=lambda b:max(len(tok(r['text'],add_special_tokens=False)['input_ids']) for r in b))
        guard()
        discarded = reconstruct(ar,tok,[r['text'] for r in warm])
        del discarded
        vectors = []; timings = []; gate = None
        for i,batch in enumerate(batches):
            guard()
            unit_started = time.monotonic()
            vectors.append(reconstruct(ar,tok,[r['text'] for r in batch]))
            unit_seconds = time.monotonic()-unit_started  # reconstruct synchronizes by copying to CPU
            if len(timings) < 3:
                timings.append(unit_seconds)
            if len(timings) == 3:
                gate = warmed_gate(load_seconds,timings,len(batches),time.monotonic()-started,i+1,
                    float(assignment['allocated_gpu_seconds']),float(assignment['previous_gpu_seconds']))
                if i == 2:
                    P.dump(a.out/'WARMED_FORECAST.json',gate)
        guard()
        np.save(a.out/'recon.npy',torch.cat(vectors).numpy(),allow_pickle=False)
        P.dump(a.out/'ids.json',[r['id'] for r in records])
        P.dump(a.out/'provenance.json',{**AR._provenance(text_seal_sha256=a.texts/'INPUT_SEAL.json',
            assets_sha256=a.assets,assignment_sha256=a.assignment,whitener_sha256=a.whitener),
            'stage':'S2','timing_entrypoint_sha256':P.sha(__file__),
            'timing_amendment':'08b24aeb','warmup_outputs_discarded':True})
        P.seal(a.out,['recon.npy','ids.json','provenance.json'],'SCORES_SEALED_FIDELITY_BEFORE_LABEL_JOIN')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('texts','assets','assignment','official','whitener','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--batch',type=int,default=8)
    collect(p.parse_args())


if __name__ == '__main__':
    main()
