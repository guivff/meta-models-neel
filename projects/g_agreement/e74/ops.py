"""Small fail-closed IO and budget primitives shared by the E74 operator tools."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import time
from . import hardware


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def write(path, obj):
    """Exclusive, durable publication; a failed claim is never automatically reset."""
    path = Path(path)
    with path.open('xb') as f:
        f.write(encoded(obj)); f.flush(); os.fsync(f.fileno())
    path.chmod(0o600)


def bound(path, digest):
    require(sha(path) == digest, 'bound file hash mismatch')
    return json.loads(Path(path).read_bytes())


def safe(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts and str(p) != '.', 'unsafe relative path')
    result = Path(root) / p
    require(result.resolve().is_relative_to(Path(root).resolve()), 'path escapes root')
    return result


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def seal(directory, names, **metadata):
    obj = dict(metadata, sealed_at=utc(), files={n: sha(safe(directory, n)) for n in names})
    write(Path(directory) / 'SEAL.json', obj)
    return obj


def verify_seal(path, expected=None):
    path = Path(path)
    obj = bound(path, expected) if expected else json.loads(path.read_bytes())
    require(bool(obj['files']), 'empty seal')
    for name, digest in obj['files'].items():
        require(sha(safe(path.parent, name)) == digest, 'sealed member hash mismatch')
    return obj


def deadline(end):
    require(math.isfinite(end) and time.time() < end, 'deadline exceeded')


NO_FIT_EXIT = 4


class NoFit(ValueError):
    """A valid whole-E74 forecast exceeds the hardware-specific admission cap."""
    def __init__(self, evidence):
        super().__init__(f"whole E74 padded forecast exceeds USD{evidence['cap_usd']}")
        self.evidence = evidence


def record_no_fit(out, error, origin):
    evidence = dict(error.evidence, status='NO_FIT', reason='PADDED_FORECAST_EXCEEDS_CAP', origin=origin)
    target = Path(out)/'NO_FIT.json'
    temp = Path(out)/('.NO_FIT.' + origin + '.json')
    write(temp, evidence)
    try:
        os.link(temp, target)  # publish complete bytes; first rejection wins
    except FileExistsError:
        pass
    finally:
        temp.unlink()
    return json.loads(target.read_bytes())


def rejected_admission(out, request, error, origin):
    """Seal a pre-worker rejection too; never launch a child or reset a claim."""
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    write(out/'REQUEST.json', request)
    evidence = record_no_fit(out, error, origin)
    report = dict(status='NO_FIT', exit_code=NO_FIT_EXIT, rejected_forecast=evidence,
                  provider_release_verified=False, no_automatic_retry=True)
    write(out/'SUPERVISOR.json', report)
    seal(out, ['REQUEST.json', 'NO_FIT.json', 'SUPERVISOR.json'], track='G', **report)
    print(json.dumps(report))
    return NO_FIT_EXIT


def budget(admission, remaining_seconds, now=None):
    """Count ALL elapsed allocation time plus remaining work, paid wait and release.

    Extra charges are an operator-supplied upper bound, never treated as a quote.
    This is a forecasting gate, not proof of provider release.
    """
    now = time.time() if now is None else now
    vals = [now, admission['allocation_start_epoch'], admission['replica_hourly_usd'],
            admission['other_cost_upper_bound_usd'], remaining_seconds]
    require(all(type(x) in (int, float) and math.isfinite(x) for x in vals), 'invalid cost inputs')
    require(now >= vals[1] > 0 and vals[2] > 0 and vals[3] >= 0 and remaining_seconds >= 0,
            'invalid cost domain')
    forecast = ((now - vals[1] + remaining_seconds) * vals[2] / 3600 + vals[3]) * 1.25
    cap = hardware.limits(admission)['cap_usd']
    require(admission['cap_usd'] == cap and math.isfinite(forecast), 'invalid cap or nonfinite forecast')
    evidence = {'at_epoch': now, 'allocation_start_epoch': vals[1], 'elapsed_seconds': now - vals[1],
                'remaining_seconds': remaining_seconds, 'replica_hourly_usd': vals[2],
                'other_cost_upper_bound_usd': vals[3], 'multiplier': 1.25,
                'forecast_usd': forecast/1.25, 'forecast_times_1_25_usd': forecast, 'cap_usd': cap}
    if forecast > cap:
        raise NoFit(evidence)
    require(now + remaining_seconds <= admission['provider_stop_epoch'], 'provider deadline cannot cover remaining work')
    return {'at_epoch': now, 'elapsed_seconds': now - vals[1], 'remaining_seconds': remaining_seconds,
            'forecast_times_1_25_usd': forecast, 'cap_usd': cap}


def admission(path, digest, phase):
    obj = bound(path, digest)
    require(obj['issuer'] == 'I-2' and obj['experiment'] == 'E74' and obj['admitted'] is True,
            'actual I-2 admission required')
    require(phase in obj['authorized_phases'], 'phase not admitted')
    hardware.profile(obj)
    require(obj['provider_stop_verified'] is True and obj['environment_lock_verified'] is True,
            'operator hard stop and environment lock required')
    require(isinstance(obj['environment_lock_sha256'], str) and len(obj['environment_lock_sha256']) == 64,
            'environment lock digest required')
    budget(obj, 0)
    return obj
