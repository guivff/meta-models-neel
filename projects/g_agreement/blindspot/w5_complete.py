"""One scoring-only W5 completion; no capture and no partial-score resume."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import shutil
import signal
from statistics import median
import time
import numpy as np
from . import protocol as P
from . import run as R

TIMING_AMENDMENT = "08b24aeb898e2f087c4641cabf6757d16b030b95"


def verified_capture(bank, capture, expected_seal):
    bank, capture = Path(bank), Path(capture)
    R._labels_absent(bank)
    all_items, _, specs = R._inputs(bank)
    seal = P.verify(capture, "CAPTURE_SEAL.json")
    names = {f"acts{L}.npy" for L in R.W5_LAYERS} | {"items.order.json", "provenance.capture.json"}
    if (P.sha(capture / "CAPTURE_SEAL.json") != expected_seal or set(seal["files"]) != names
            or seal.get("status") != "CAPTURE_COMPLETE_SCORES_PENDING"):
        raise ValueError("requires exact six-layer capture seal")
    ids = json.loads((bank / "sweep.input.json").read_text())
    if not ids or len(ids) != len(set(ids)) or json.loads((capture / "items.order.json").read_text()) != ids:
        raise ValueError("capture order differs from full frozen W5 subset")
    cp = json.loads((capture / "provenance.capture.json").read_text())
    if cp["input_seal_sha256"] != P.sha(bank / "INPUT_SEAL.json"):
        raise ValueError("capture bank lineage mismatch")
    index = {it["id"]: it for it in all_items}; items = [index[key] for key in ids]
    local = {key: i for i, key in enumerate(ids)}
    donors = [local[it["donor_id"]] for it in items]
    specs = {f: specs[f] for f in sorted({it["feature"] for it in items})}
    if any(s.get("kind") != "binary" for s in specs.values()):
        raise ValueError("W5 subset must remain binary")
    arrays = {L: np.load(capture / f"acts{L}.npy", allow_pickle=False) for L in R.W5_LAYERS}
    if any(h.ndim != 2 or len(h) != len(items) or h.dtype.kind != 'f' or not np.isfinite(h).all() for h in arrays.values()):
        raise ValueError("invalid capture dimensions or values")
    if len({(h.shape, h.dtype.str) for h in arrays.values()}) != 1:
        raise ValueError("capture shapes/dtypes disagree")
    return items, donors, specs, arrays


def work_units(items, donors, specs):
    for feature, spec in specs.items():
        indices = [i for i, it in enumerate(items) if it['feature'] == feature]
        for layer in R.W5_LAYERS:
            for arm, selected in R._arms(indices, donors):
                yield spec, indices, layer, arm, selected


def score_unit(ol, h, items, unit):
    spec, indices, layer, arm, selected = unit
    v = ol.paired_logodds_templates(h[layer][selected], layer, R._pairs(spec, 'olens'))
    return R._score_rows(items, indices, v, 'olens', layer, arm, 'summed_sequence_logodds')


def forecast_budget(smoke, n_units):
    if set(smoke) != set(R.W5_LAYERS) or set(n_units) != set(R.W5_LAYERS):
        raise ValueError("timings and fresh-pass counts required for all six layer paths")
    if any(len(smoke[L]) != 3 or any(not math.isfinite(v) or v <= 0 for v in smoke[L])
           or not isinstance(n_units[L], int) or n_units[L] < 3 for L in R.W5_LAYERS):
        raise ValueError("three positive warm smoke timings required per layer path")
    medians = {L: median(smoke[L]) for L in R.W5_LAYERS}
    smoke_seconds = sum(sum(values) for values in smoke.values())
    fresh_seconds = sum(medians[L] * n_units[L] for L in R.W5_LAYERS)
    forecast = smoke_seconds + fresh_seconds
    return {'forecast_seconds': forecast, 'science_cap_seconds': min(1.5 * forecast + 360, 3600),
            'fits_one_gpu_hour': 1.5 * forecast <= 3600,
            'forecast_method': 'sum(18 timed units) + sum(per-layer median of 3 * fresh units at that layer)',
            'smoke_unit_seconds': smoke, 'smoke_seconds': smoke_seconds,
            'median_unit_seconds_by_layer': medians, 'fresh_pass_forecast_seconds': fresh_seconds,
            'fresh_units_by_layer': n_units, 'units_in_fresh_pass': sum(n_units.values()),
            'smoke_outputs_used': False, 'timing_amendment_commit': TIMING_AMENDMENT}


def collect(a):
    assignment = P.admit(a.assignment, experiment='W5', bank=a.bank,
                         execution_plan=a.execution_plan, run_kind=P.W5_COMPLETION_KIND)
    receipt = json.loads(a.receipt.read_text())
    if (assignment.get('completion_receipt_sha256') != P.sha(a.receipt)
            or receipt.get('source_files') != P.code_hashes()
            or receipt.get('budget_amendment_commit') != P.W5_COMPLETION_AMENDMENT
            or receipt.get('timing_amendment_commit') != TIMING_AMENDMENT):
        raise ValueError("receipt not bound to assignment/source/amendment")
    R._runtime(a.bank, a.batch)
    items, donors, specs, arrays = verified_capture(a.bank, a.capture, receipt['capture_seal_sha256'])
    w1 = R._require_w1_before_sweep(a, json.loads((a.bank / 'templates.json').read_text()))
    units = list(work_units(items, donors, specs))
    by_layer = {L: [unit for unit in units if unit[2] == L] for L in R.W5_LAYERS}
    if any(len(group) < 3 for group in by_layer.values()):
        raise ValueError("three production-shaped timing units required per layer path")
    if w1 != receipt['w1_analysis_seal_sha256'] or len(items) != receipt['n_items'] or len(units) != receipt['n_scoring_units']:
        raise ValueError("full W1/W5 population differs from receipt")
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('w5_scoring_completion', gpu=True, extra={'pod_id': assignment['pod_id']}), P.compute_window(assignment):
        for layer in R.W5_LAYERS:
            shutil.copyfile(a.capture / f'acts{layer}.npy', a.out / f'acts{layer}.npy')
        import torch
        h = {L: torch.from_numpy(x) for L, x in arrays.items()}
        assets = R._assets(a.assets, names=('model', 'olens')); ol = R._load_oracle(assets)
        warmup = []
        for L, group in by_layer.items():
            P.science_deadline(assignment)
            unit = group[0]
            score_unit(ol, h, items, unit)  # full production shape; discarded setup output
            warmup.append({'layer': L, 'feature': items[unit[1][0]]['feature'],
                           'arm': unit[3], 'n_items': len(unit[1]), 'n_pairs': len(R._pairs(unit[0], 'olens'))})
        torch.cuda.synchronize()
        P.dump(a.out / 'WARMUP.json', {'status': 'UNSCORED_SETUP_COMPLETE', 'layers': list(R.W5_LAYERS),
            'batch': a.batch, 'units': warmup, 'full_production_shape': True, 'warmup_outputs_used': False,
            'timing_amendment_commit': TIMING_AMENDMENT})
        P.science_checkpoint(assignment)
        clock = json.loads(Path(assignment['_science_clock_path']).read_text())
        smoke = {L: [] for L in R.W5_LAYERS}
        for L, group in by_layer.items():
            for unit in group[:3]:
                P.science_checkpoint(assignment); before = time.perf_counter()
                score_unit(ol, h, items, unit)  # outputs discarded, never in final grid
                torch.cuda.synchronize(); smoke[L].append(time.perf_counter() - before)
        budget = forecast_budget(smoke, {L: len(group) for L, group in by_layer.items()})
        budget.update(first_science_epoch=clock['first_science_epoch'],
                      absolute_science_deadline_epoch=min(clock['science_deadline_epoch'], clock['first_science_epoch'] + budget['science_cap_seconds']))
        budget['fits_assigned_cap'] = budget['science_cap_seconds'] <= P._science_budget(assignment)
        budget['fits_remaining_custody'] = time.time() + budget['fresh_pass_forecast_seconds'] < assignment['deadline_epoch'] - 180
        P.dump(a.out / 'FORECAST.json', budget)
        if not all(budget[k] for k in ('fits_one_gpu_hour', 'fits_assigned_cap', 'fits_remaining_custody')):
            P.dump(a.out / 'STATUS.json', {'status': 'NO_FIT_REPORT_TO_GUIV', 'full_scoring_started': False, 'scope_reduced': False})
            return
        deadline = budget['absolute_science_deadline_epoch']
        def check():
            if time.time() >= deadline: raise TimeoutError('forecast-bounded first-science deadline reached')
            signal.setitimer(signal.ITIMER_REAL, max(.01, deadline - time.time()))
        scores = []
        for unit in units:
            check(); rows = score_unit(ol, h, items, unit)
            scores.extend(rows); R._append_partial(a, 'sweep', rows)
        from .analysis import _grid
        _grid(scores, items, specs, [('olens', L) for L in R.W5_LAYERS]); check()
        P.jsonl(a.out / 'scores.sweep.jsonl', scores)
        P.dump(a.out / 'items.order.json', [it['id'] for it in items])
        P.dump(a.out / 'provenance.sweep.json', {'input_seal_sha256': P.sha(a.bank / 'INPUT_SEAL.json'),
            'assignment_sha256': P.sha(a.assignment), 'assets_sha256': P.sha(a.assets), 'source_files': P.code_hashes(),
            'experiment': 'W5', 'batch': a.batch, 'hook': 'zero-based decoder block output, raw last-prefix-token state',
            'sweep_input_sha256': P.sha(a.bank / 'sweep.input.json'), 'w1_analysis_seal_sha256': w1,
            'source_capture_seal_sha256': receipt['capture_seal_sha256'], 'completion_receipt_sha256': P.sha(a.receipt),
            'science_clock': clock, 'run_kind': P.W5_COMPLETION_KIND, 'recaptured': False, 'partial_rows_reused': False})
        names = ['scores.sweep.jsonl', 'items.order.json', 'provenance.sweep.json', 'FORECAST.json', 'WARMUP.json']
        names += [f'acts{L}.npy' for L in R.W5_LAYERS]
        P.seal(a.out, names, 'SCORES_SEALED_SWEEP_BEFORE_LABEL_JOIN')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for f in ('assignment', 'bank', 'assets', 'out', 'capture', 'receipt', 'execution-plan', 'w1-analysis'):
        p.add_argument('--' + f, type=Path, required=True)
    p.add_argument('--batch', type=int, default=32)
    collect(p.parse_args())


if __name__ == '__main__': main()
