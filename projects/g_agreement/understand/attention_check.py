"""§91 operational checks only; no model loading, allocation or science retry."""
from __future__ import annotations

import math
import json
from pathlib import Path
import shutil

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from projects.g_agreement.blindspot import protocol as P
from .budget import CAP_SECONDS, forecast


READER_PHASES = ('olens', 'nla', 'jlens')


def sealed_calibrations(previous, input_seals):
    """Read verified sealed timing bytes, never remeasure or rescale them."""
    previous = Path(previous)
    seal = P.verify(previous, 'SCORE_SEAL.json')
    required = {'provenance.json', 'RUN_STATUS.json'} | {
        f'calibration/{phase}.json' for phase in READER_PHASES}
    if seal['status'] != 'SCORES_SEALED_EXPLORATORY_E4' or not required <= set(seal['files']):
        raise ValueError('previous E4 seal lacks the three reader calibrations')
    provenance = json.loads((previous/'provenance.json').read_text())
    if provenance['experiment'] != 'E4' or provenance['input_seals'] != input_seals:
        raise ValueError('sealed E4 input population mismatch')
    receipts = {}
    for phase in READER_PHASES:
        receipt = json.loads((previous/f'calibration/{phase}.json').read_text())
        if (receipt['batch'] != 1 or receipt['units'] != 2100 or receipt['warmups'] != 1
                or not math.isclose(forecast(receipt['timings_seconds'], receipt['units']),
                                    receipt['forecast_seconds'], abs_tol=1e-7)):
            raise ValueError('sealed reader calibration differs from frozen E4 scope')
        receipts[phase] = receipt
    return receipts


def retain_calibrations(previous, destination, input_seals):
    """Copy original bytes and their aggregate seal for incremental retrieval."""
    receipts = sealed_calibrations(previous, input_seals)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('SCORE_SEAL.json', 'RUN_STATUS.json', 'provenance.json',
                 *(f'calibration/{phase}.json' for phase in READER_PHASES)):
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(previous)/name, target)
    P.verify(destination, 'SCORE_SEAL.json')
    return receipts


def forecast_lower_bound(receipts):
    """A missing target forecast/transfer/elapsed time cannot lower this bound."""
    if set(receipts) != set(READER_PHASES):
        raise ValueError('all three sealed reader calibrations required')
    lower = sum(forecast(receipts[p]['timings_seconds'], receipts[p]['units'])
                for p in READER_PHASES)
    return {'reader_forecast_seconds': lower, 'science_cap_seconds': CAP_SECONDS,
            'excess_seconds_at_least': max(0., lower-CAP_SECONDS),
            'status': 'NO_FIT_DO_NOT_LAUNCH' if lower > CAP_SECONDS else 'TARGET_GATE_PENDING',
            'target_transfer_elapsed_seconds_lower_bound': 0.}


def equivalence_items(data):
    """Four test IDs in lexical order, chosen without scores or labels."""
    indices = sorted((i for i, item in enumerate(data['items']) if item['split'] == 'test'),
                     key=lambda i: data['items'][i]['id'])[:4]
    if len(indices) != 4 or len({data['items'][i]['id'] for i in indices}) != 4:
        raise ValueError('exactly four distinct test items required')
    return indices


def check_equivalence(runtime, data, receipt_path):
    """Before science: native Oracle asked LO, forced SDPA flash versus math.

    The Oracle/target share weights. This is a setup-only numerical check;
    no gradients, calibration, labels, seed change or production scores. Both
    contexts restore backend flags. Write PASS/FAIL/ERROR before raising.
    The caller must stop E4 on failure, without any retry or fallback.
    """
    path = Path(receipt_path)
    if path.exists():
        raise ValueError('equivalence receipt already exists; no implicit retry')
    receipt = {'status': 'ERROR', 'stage': 'pre-science setup', 'absolute_tolerance': 1e-2,
               'relative_tolerance': 0., 'comparison': 'SDPA FLASH_ATTENTION versus MATH',
               'score': 'native Oracle asked A-minus-B, mean of two frozen phrasing pairs',
               'selection': 'first four lexical test IDs in sealed E4 input', 'items': []}
    try:
        if runtime.name not in {'olens', 'target'} or runtime.device.type != 'cuda':
            raise ValueError('real flash/math equivalence requires the Oracle/target on CUDA')
        configs = [getattr(module, 'config', None) for module in runtime.model.modules()]
        implementations = {getattr(config, '_attn_implementation', None) for config in configs}
        if 'sdpa' not in implementations or implementations - {None, 'sdpa'}:
            raise ValueError('equivalence requires SDPA dispatch; no eager/flash2 substitution')
        indices = equivalence_items(data)
        for index in indices:
            item = data['items'][index]
            acts = np.array(data['activations'][44][index:index+1], copy=True)
            pairs = data['templates'][item['feature']]['olens']
            values = []
            for backend in (SDPBackend.FLASH_ATTENTION, SDPBackend.MATH):
                with torch.no_grad(), sdpa_kernel(backend):
                    values.append(float(runtime.asked(acts, pairs, batch=2).item()))
            if not all(math.isfinite(v) for v in values):
                raise ValueError('nonfinite flash/math asked log-odds')
            delta = abs(values[1]-values[0])
            receipt['items'].append({'id': item['id'], 'feature': item['feature'],
                'flash_asked_logodds': values[0], 'math_asked_logodds': values[1],
                'absolute_difference': delta,
                'passed': delta <= 1e-2})
        receipt['max_absolute_difference'] = max(i['absolute_difference'] for i in receipt['items'])
        receipt['status'] = 'PASS' if all(i['passed'] for i in receipt['items']) else 'FAIL'
        P.dump(path, receipt)
        if receipt['status'] != 'PASS':
            raise ValueError('E4 INCOMPLETE: flash/math asked log-odds equivalence failed')
        return receipt
    except Exception as exc:
        receipt['error'] = type(exc).__name__+': '+str(exc)
        P.dump(path, receipt)
        raise
