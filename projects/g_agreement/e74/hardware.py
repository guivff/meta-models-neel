"""E74 hardware configuration only; no provisioning, imports or GPU calls at import."""
import datetime as dt
import math
import re
import time

HOPPER_AUTHORITY = 'bd43a46af5eb2ea84e8524fdc1ab6f5262acd729'
HOPPER_NOT_BEFORE = dt.datetime(2026, 10, 28, 5, tzinfo=dt.timezone.utc).timestamp()
TP8_LIMIT_AUTHORITY = 'f5720c36529f52bf506924fa73825df8b4c95d9e'
DEFAULT_PHASES = {'boot':660, 'smoke':120, 'capture':1633, 'readouts':840}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def limits(admission):
    kind, count = admission['gpu_type'], admission['gpu_count']
    require(type(count) is int and (kind, count) in [('B200',4), ('H200',8)],
            'unsupported hardware for limit selection')
    if count == 8:
        require(admission.get('limit_authority') == TP8_LIMIT_AUTHORITY,
                'TP8 clarification7 limit binding required')
        return {'boot_smoke_seconds':3000, 'cap_usd':120}
    return {'boot_smoke_seconds':1200, 'cap_usd':100}


def phase_forecast(admission):
    if admission['gpu_type'] == 'B200':
        return dict(DEFAULT_PHASES)
    phases = admission.get('phase_forecast_seconds')
    require(isinstance(phases, dict) and set(phases) == set(DEFAULT_PHASES),
            'H200 requires an I-2 hardware-specific phase forecast')
    require(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in phases.values()),
            'invalid H200 phase forecast')
    require(phases['boot'] + phases['smoke'] <= limits(admission)['boot_smoke_seconds'],
            'boot plus smoke exceeds hardware-specific cap')
    digest = admission.get('hardware_forecast_sha256')
    require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}', digest) is not None,
            'H200 forecast evidence hash required')
    return dict(phases)


def profile(admission, now=None):
    now = time.time() if now is None else now
    kind, count = admission['gpu_type'], admission['gpu_count']
    require(type(count) is int and (kind, count) in [('B200',4), ('H200',8)],
            'implemented hardware is4B200 or registered single-node8H200 only')
    if kind == 'H200':
        gate = admission.get('hopper_fallback', {})
        require(isinstance(gate,dict), 'Hopper fallback attestation required')
        require(gate.get('authority') == HOPPER_AUTHORITY and gate.get('not_before_epoch') == HOPPER_NOT_BEFORE,
                'Hopper clarification6 binding required')
        checked = gate.get('checked_epoch')
        allocated = admission.get('allocation_start_epoch')
        require(type(checked) in (int,float) and math.isfinite(checked)
                and type(allocated) in (int,float) and math.isfinite(allocated)
                and HOPPER_NOT_BEFORE <= checked <= now
                and HOPPER_NOT_BEFORE <= allocated <= now,
                'Hopper unavailable before Wed28Oct06:00CET')
        require(gate.get('no_b200_claim_by_deadline') is True and gate.get('single_node') is True,
                'I-2 must attest no4/8B200 claim by cutoff and single-node8H200')
        phase_forecast(admission)
    return {'gpu_type':kind, 'gpu_count':count, 'tensor_parallel_size':count,
            'hardware_authority':HOPPER_AUTHORITY if kind == 'H200' else 'b90325cb',
            'undocumented_hardware_path':kind == 'H200',
            'limits':limits(admission),
            'limit_authority':TP8_LIMIT_AUTHORITY if count == 8 else 'ac641dbf'}


def engine_kwargs(config):
    return dict(tp=config['tensor_parallel_size'], gpu_mem=.88, moe_backend='marlin',
                kv_cache_dtype='fp8', max_model_len=1152, max_num_seqs=512,
                max_num_batched_tokens=32768, w4a16=True, seed=0)


def construct(runtime, torch, model_dir, config):
    count = config['gpu_count']
    require(torch.cuda.device_count() == count, 'visible GPU count differs from admitted hardware')
    require(all(re.search(r'\b'+config['gpu_type']+r'\b', torch.cuda.get_device_name(i)) for i in range(count)),
            'visible GPU type differs from admitted hardware')
    if config['gpu_type'] == 'H200':
        require(all(tuple(torch.cuda.get_device_capability(i)) == (9,0) for i in range(count)),
                'H200 requires SM90 on every visible device')
    engine = runtime.GlmOlensEngine(model_dir, **engine_kwargs(config))
    require(engine.n_workers == count, 'author runtime worker count differs from admitted TP')
    # Read counters without resetting them; verify actual RPC worker coverage,
    # rather than trusting only the author's n_workers=tp assignment.
    require(len(engine._stats(reset=False)) == count, 'author RPC worker coverage differs from admitted TP')
    return engine
