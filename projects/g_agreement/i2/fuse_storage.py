"""E74's authorised RunPod FUSE exception; CPU validation only, no allocation.

The operator must obtain the volume contract from the actual authenticated pod
response and bind it into the existing SHA-bound I-2 admission. A FUSE pool's df
total is never evidence of the pod's allocated capacity. No filesystem is
reclassified as NVMe. Existing transfer/fsync/reread and engine gates still apply.
"""
import hashlib
import json
import math
from pathlib import Path

AUTHORITY_SHA256 = 'a1680e5ba265de2fd9a4ef1f28442c21f71b627ab1b76cadf09c537a5bde6f43'
WEIGHT_BYTES = 466355755887
MIN_REQUIRED_BYTES = 468704353377
FUSE_TYPES = frozenset({'fuse', 'fuse.mfs', 'fuse3', 'fuse3.mfs'})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def number(value):
    require(type(value) in (int, float) and math.isfinite(value), 'finite number required')
    return value


def contract(admission, mount, free_bytes, required_bytes, now):
    """Validate actual FUSE observation against the allocation-bound contract.

    The contract is root/operator evidence, not a remotely self-issued waiver.
    The caller first verifies the enclosing admission SHA and provider identity.
    remaining_seconds includes all staging, idle, boot, smoke, capture, readouts
    and closeout; it uses the existing whole-endpoint clock and cost padding.
    """
    c = admission.get('storage_exception')
    require(isinstance(c, dict), 'FUSE requires allocation-bound storage exception')
    keys = {'authority_sha256', 'allocation_receipt_sha256', 'run_identity_sha256',
            'allocation_start_epoch', 'provider_stop_epoch', 'provider',
            'volume_mount_path', 'allocated_volume_bytes', 'existing_volume_bytes',
            'capacity_observed_epoch', 'remaining_seconds'}
    require(set(c) == keys, 'storage contract fields differ')
    require(c['authority_sha256'] == AUTHORITY_SHA256 and c['provider'] == 'RunPod',
            'storage exception authority/provider differs')
    for key in ('allocation_receipt_sha256', 'run_identity_sha256'):
        require(isinstance(c[key], str) and len(c[key]) == 64 and
                all(ch in '0123456789abcdef' for ch in c[key]), 'actual allocation identity required')
        require(c[key] == admission.get(key), 'storage contract belongs to another allocation')
    require(c['allocation_start_epoch'] == admission['allocation_start_epoch'] and
            c['provider_stop_epoch'] == admission['provider_stop_epoch'], 'original allocation clocks differ')
    now = number(now)
    require(0 < c['allocation_start_epoch'] <= number(c['capacity_observed_epoch']) <= now <
            c['provider_stop_epoch'], 'capacity observation outside original allocation')
    require(isinstance(mount, dict) and len(mount.get('filesystems', [])) == 1,
            'single actual filesystem observation required')
    fs = mount['filesystems'][0]
    require(fs['fstype'] in FUSE_TYPES, 'exception only admits RunPod FUSE')
    require(fs['target'] == c['volume_mount_path'] == '/workspace', 'actual RunPod workspace mount required')
    for value in (c['allocated_volume_bytes'], c['existing_volume_bytes'], free_bytes, required_bytes):
        require(type(value) is int and value >= 0, 'nonnegative capacity bytes required')
    require(required_bytes >= MIN_REQUIRED_BYTES and
            c['allocated_volume_bytes'] - c['existing_volume_bytes'] >= required_bytes and
            free_bytes >= required_bytes, 'insufficient allocated capacity or actual filesystem free space')
    remaining = number(c['remaining_seconds'])
    require(remaining > 0 and now + remaining <= c['provider_stop_epoch'], 'original full endpoint cannot fit')
    rate = number(admission['replica_hourly_usd'])
    extras = number(admission['other_cost_upper_bound_usd'])
    cap = number(admission['cap_usd'])
    require(rate > 0 and extras >= 0 and cap > 0, 'invalid forecast inputs')
    padded = ((now - c['allocation_start_epoch'] + remaining) * rate / 3600 + extras) * 1.25
    require(padded <= cap, 'full endpoint padded forecast exceeds cap')
    return {'storage': 'runpod_fuse', 'local_nvme_verified': False,
            'authority_sha256': AUTHORITY_SHA256, 'contract_sha256': digest(c),
            'allocation_receipt_sha256': c['allocation_receipt_sha256'],
            'run_identity_sha256': c['run_identity_sha256'],
            'findmnt': mount, 'free_bytes': free_bytes, 'required_bytes': required_bytes,
            'allocated_volume_bytes': c['allocated_volume_bytes'],
            'existing_volume_bytes': c['existing_volume_bytes'],
            'checked_epoch': now, 'forecast_times_1_25_usd': padded,
            'no_second_full_cache': True}


def verify_receipt(proof, admission, now):
    require(isinstance(proof, dict), 'storage proof required')
    expected = contract(admission, proof['findmnt'], proof['free_bytes'], proof['required_bytes'],
                        proof['checked_epoch'])
    require(proof == expected and proof['checked_epoch'] <= number(now), 'storage proof changed or is future dated')
    require(now < admission['provider_stop_epoch'], 'original provider endpoint expired')
    return proof


def observe(path, admission, required_bytes, now, metadata, disk_usage):
    """Read-only mount/capacity observation; no writes, transfers or GPU calls."""
    path = Path(path).resolve()
    require(path == Path('/workspace') or Path('/workspace') in path.parents,
            'FUSE exception only covers workspace descendants')
    mount = metadata(['findmnt', '-J', '-T', str(path), '-o', 'SOURCE,TARGET,FSTYPE'])
    return contract(admission, mount, disk_usage(path).free, required_bytes, now)
