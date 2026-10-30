"""Bind the integrator's local asset inventory and forecasts to a frozen E36 request.

CPU-only. This writes a plan and command; it never loads a model or starts a pod.
The source-ready request and its scientific inputs must already be committed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import channel_contract as C
import parity_gate as G
from worker import verify_assets_binding, verify_source_bindings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def validate_ready_request(request):
    payload = {k: v for k, v in request.items() if k != 'request_sha256'}
    C.require(C.canonical_hash(payload) == request.get('request_sha256'), 'ready request digest mismatch')
    C.require(request.get('schema') == 'e36.source-ready.v1', 'wrong ready request schema')
    C.require(request.get('status') == 'READY_FOR_INTEGRATOR_BINDING', 'request is held or incomplete')
    C.require(request.get('bank_frozen') is True and request.get('model_calls') == 0, 'bank must be frozen before acquisition')
    C.require(request.get('operator') == 'integrator', 'integrator-only handoff required')
    bindings = request['bindings']
    for key in ('bank', 'freeze', 'candidates'):
        C.check_hash(bindings[key]['sha256'])
    C.require(request['scope_id'] in ('original8', 'expanded25'), 'unknown scope')
    G.validate_binding(request.get('parity_inputs'))
    return bindings


def prepare(args):
    os.chdir(ROOT)  # All portable relative paths resolve inside this checkout.
    request = json.loads(Path(args.request).read_text())
    bindings = validate_ready_request(request)
    G.load_inputs(request['parity_inputs'])
    scope = (C.scope_from_definition_packet(request['definition_packet'])
             if request['scope_id'] == 'expanded25' else None)
    rules = (C.expanded_rule_binding(request['rule_authority'])
             if request['scope_id'] == 'expanded25' else None)
    freeze = C.read_bound(bindings['freeze'])
    C.validate_freeze_receipt(freeze, bindings['bank'], scope)
    bank = C.read_bound(bindings['bank'], jsonl=True)
    candidates = C.read_bound(bindings['candidates'])
    C.validate_items(bank, scope)
    C.validate_candidates(candidates, scope)
    for row, spec in candidates['rows'].items():
        C.require(spec['values'] == freeze['rows'][row]['values'], 'candidate value orientation differs from frozen bank')
    assets = Path(args.assets).resolve()
    assets_binding = {'path': str(assets), 'sha256': C.file_hash(assets)}
    plan = C.make_plan(bindings['bank'], bindings['freeze'], bindings['candidates'],
                       assets_binding=assets_binding, candidate_bound_at=request['candidate_bound_at'],
                       frozen_at=freeze['frozen_at'], source_bindings=request['source_bindings'],
                       scope=scope, rule_binding=rules, parity_binding=request['parity_inputs'])
    verify_source_bindings(plan, ROOT)
    verify_assets_binding(plan, assets, ROOT)
    forecast = json.loads(Path(args.phase_forecast).read_text())
    out = Path(args.out).resolve()
    C.require(out.is_relative_to((HERE / 'cache').resolve()), 'bound operational files must remain in E36 cache')
    C.require(not out.exists(), 'bound output exists; do not overwrite an attempt')
    bound = C.make_launch_request(plan, plan_path=out / 'RUN_PLAN.json',
              assignment_path=out / 'ASSIGNMENT.json', assets_path=assets,
              repository_root=ROOT, output_path=out / 'run',
              prior_gpu_seconds=args.prior_gpu_seconds, phase_estimates_seconds=forecast)
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / 'RUN_PLAN.json', plan)
    write_new(out / 'LAUNCH_REQUEST_BOUND.json', bound)
    write_new(out / 'ASSIGNMENT_TEMPLATE.json', {
        'experiment': 'E36', 'operator': 'integrator', 'plan_sha256': plan['plan_sha256'],
        'gpu_count': 1, 'gpu_type': 'H200', 'pod_id': None,
        'allocation_started_at': None, 'hard_deadline': None,
        'prior_gpu_seconds': args.prior_gpu_seconds, 'phase_estimates_seconds': forecast,
        'warmed_forecast_seconds': bound['warmed_forecast_seconds'],
        'maximum_current_allocation_seconds': bound['maximum_current_allocation_seconds'],
        'setup_allowance_seconds': bound['setup_allowance_seconds'],
        'science_cap_seconds': bound['science_cap_seconds'],
        'warmed_forecast_verified': False, 'warmed_forecast_receipt': None,
        'external_stop': {'confirmed': False, 'deadline': None, 'receipt': None},
        'note': 'Integrator fills actual allocation times and verified external-stop receipt, then saves ASSIGNMENT.json.'})
    write_new(out / 'BINDING_SEAL.json', {'experiment': 'E36', 'request_sha256': request['request_sha256'],
        'model_calls': 0, 'files': {name: C.file_hash(out / name) for name in
                                 ('RUN_PLAN.json', 'LAUNCH_REQUEST_BOUND.json', 'ASSIGNMENT_TEMPLATE.json')}})
    return {'status': bound['status'], 'scope': request['scope_id'], 'model_calls': 0,
            'plan_sha256': plan['plan_sha256'], 'bound_request_sha256': bound['request_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', default=str(HERE / 'LAUNCH_REQUEST.json'))
    parser.add_argument('--assets', required=True)
    parser.add_argument('--phase-forecast', required=True)
    parser.add_argument('--prior-gpu-seconds', type=float, required=True)
    parser.add_argument('--out', required=True)
    print(json.dumps(prepare(parser.parse_args()), sort_keys=True))
