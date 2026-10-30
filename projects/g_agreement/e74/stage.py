"""Anonymous immutable HF staging; no provisioning, credentials or automatic retry.

The parent enforces the original 3600-second process-group deadline, including
hashing, filesystem sync and receipt creation. Nothing executes on import.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
from . import ops, smoke as core, hardware

ASSET_SHA = 'a793ad221f2bb368029b3373b78964458ffd923e7bc63d84c1fdfa2ecd8127ec'
TRANSFER_SHA = 'fb5261b6c72498ba6a9cf4a41dfd34985b5264c64588d762e076b6f69f1da19e'


def selected(manifest):
    result = []
    for repo in manifest['repos']:
        if repo['repo_id'] not in (core.BASE_REPO, core.LENS_REPO):
            continue
        revision = core.BASE_REVISION if repo['repo_id'] == core.BASE_REPO else core.LENS_REVISION
        ops.require(repo['revision'] == revision, 'asset revision differs')
        area = 'base' if repo['repo_id'] == core.BASE_REPO else 'lens'
        for entry in repo['files']:
            if entry['required']:
                expected = f"https://huggingface.co/{repo['repo_id']}/resolve/{revision}/{entry['path']}"
                ops.require(entry['resolve_url'] == expected, 'noncanonical download URL')
                result.append(dict(entry, area=area))
    ops.require(len(result) == 65 and sum(x['size_bytes'] for x in result) == 466355755887,
                'complete exact asset selection required')
    return result


def transfer(entry, root, end, opener=None):
    """Bounded streaming hash, followed by fsync and atomic no-overwrite link."""
    dest = ops.safe(root, entry['area'] + '/' + entry['path'])
    dest.parent.mkdir(parents=True, exist_ok=True)
    ops.require(not dest.exists(), 'destination already exists; no implicit resume')
    temp = dest.with_name(dest.name + '.partial')
    algorithm = entry['identity']['algorithm']
    ops.require(algorithm in ('sha256', 'git_blob_sha1'), 'unsupported HF identity')
    h = hashlib.sha256() if algorithm == 'sha256' else hashlib.sha1()
    if algorithm == 'git_blob_sha1':
        h.update(b'blob ' + str(entry['size_bytes']).encode() + b'\0')
    sha = hashlib.sha256(); count = 0
    # A fresh urllib opener has no netrc, HF token, cookies, or auth handlers.
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ops.deadline(end)
    request = urllib.request.Request(entry['resolve_url'], headers={'Accept-Encoding': 'identity'})
    with opener.open(request, timeout=min(30, max(.01, end - time.time()))) as response, temp.open('xb') as f:
        ops.require(response.status == 200, 'anonymous download did not return 200')
        while True:
            ops.deadline(end)
            block = response.read(4 * 1024 * 1024)
            if not block:
                break
            count += len(block)
            ops.require(count <= entry['size_bytes'], 'oversized download')
            f.write(block); h.update(block); sha.update(block)
        ops.require(count == entry['size_bytes'] and h.hexdigest() == entry['identity']['value'],
                    'download checksum or size mismatch')
        f.flush(); os.fsync(f.fileno())
    ops.deadline(end)
    # Receipt describes the completed destination, not only network buffers.
    # This full reread is inside the same original3600-second supervisor window.
    ops.require(ops.sha(temp) == sha.hexdigest(), 'destination SHA256 differs after fsync')
    ops.deadline(end)
    temp.chmod(0o400)
    os.link(temp, dest); temp.unlink()
    fd = os.open(dest.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {'sha256': sha.hexdigest(), **core.stat_identity(dest)}


def nvme_evidence(path):
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', str(path), '-o', 'SOURCE,TARGET,FSTYPE']))
    source = mount['filesystems'][0]['source'].split('[')[0]
    ops.require(source.startswith('/dev/'), 'staging volume is not a verifiable block mount')
    devices = json.loads(subprocess.check_output(['lsblk', '-s', '-J', '-o', 'NAME,TYPE,TRAN,PATH', source]))
    def leaves(node):
        return [x for c in node['children'] for x in leaves(c)] if node.get('children') else [node]
    disks = [leaf for node in devices['blockdevices'] for leaf in leaves(node)]
    ops.require(disks and all(d['tran'] == 'nvme' for d in disks), 'all staging backing disks must be local NVMe')
    return {'findmnt': mount, 'lsblk': devices}


def versions():
    import torch
    v = {name: importlib.metadata.version(name) for name in ('vllm', 'vllm-lens', 'torch', 'transformers', 'peft')}
    return dict(v, python='.'.join(map(str, sys.version_info[:3])), torch_cuda=torch.version.cuda)


def overlay(root, manifest, verified):
    model = root / 'runtime/base'; adapter = root / 'runtime/adapter'
    receipt = {}
    for area, target, prefix in [('base', model, 'base/'), ('lens', adapter, 'lens/' + core.LENS_PATH + '/')]:
        for name, expected in manifest[area]['files'].items():
            source_key = prefix + name
            info = verified[source_key]
            ops.require(info['sha256'] == expected['sha256'] and info['bytes'] == expected['bytes'],
                        'verified object does not match runtime manifest')
            dest = ops.safe(target, name); dest.parent.mkdir(parents=True, exist_ok=True)
            source = ops.safe(root / 'objects', source_key)
            if area == 'base' and name == 'hf_quant_config.json':
                with source.open('rb') as inp, dest.open('xb') as out:
                    shutil.copyfileobj(inp, out); out.flush(); os.fsync(out.fileno())
                dest.chmod(0o600); core.require_private_quant_copy(dest)
            else:
                os.link(source, dest)
            receipt[('base/' if area == 'base' else 'adapter/') + name] = {
                'sha256': info['sha256'], **core.stat_identity(dest)}
    return model, adapter, receipt


def worker(req, out):
    admission = ops.admission(req['admission'], req['admission_sha256'], 'weight_staging')
    end = req['stage_start_epoch'] + 3600
    ops.require(admission['allocation_start_epoch'] <= req['stage_start_epoch'] <= time.time(), 'invalid stage clock')
    ops.deadline(end)
    archive = ops.bound(req['archive_receipt'], req['archive_receipt_sha256'])
    ops.require(archive['status'] == 'VERIFIED' and archive['source_seal_sha256'] == admission['source_seal_sha256']
                and admission['allocation_start_epoch'] <= archive['started_epoch'] <= archive['finished_epoch'] <= req['stage_start_epoch']
                and archive['finished_epoch'] - archive['started_epoch'] <= 900, 'complete bounded archive stage required before weights')
    transfer_manifest = ops.bound(req['transfer_manifest'], TRANSFER_SHA)
    ops.require(transfer_manifest['source_asset_manifest_sha256'] == ASSET_SHA, 'transfer source pin differs')
    entries = transfer_manifest['files']
    manifest = ops.bound(req['weight_manifest'], core.WEIGHT_MANIFEST_SHA256)
    # Fail before the first large transfer if the runtime or fork is unavailable.
    v = versions(); core.check_dependencies(v); core.verify_fork(Path(req['fork_archive']))
    disk = nvme_evidence(out)
    free = shutil.disk_usage(out).free
    reserve = req['additional_disk_reserve_bytes']
    ops.require(type(reserve) is int and reserve >= 2_000_000_000, 'reserve for input/output/temp files required')
    needed = sum(x['size_bytes'] for x in entries) + 11506 + 348585984 + reserve
    ops.require(free >= needed, 'insufficient free staging space')
    ops.write(out / 'DISK_BEFORE.json', dict(disk, free_bytes=free, required_bytes=needed,
              checked_at=ops.utc(), no_second_full_cache=True))
    ops.budget(admission, 3600 + sum(hardware.phase_forecast(admission).values()) + 600 + 120)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [(e, pool.submit(transfer, e, out / 'objects', end)) for e in entries]
        verified = {e['area'] + '/' + e['path']: future.result() for e, future in futures}
    model, adapter, files = overlay(out, manifest, verified)
    ops.deadline(end)
    receipt = dict(schema_version=1, experiment='E74', base_repo=core.BASE_REPO, base_revision=core.BASE_REVISION,
        lens_repo=core.LENS_REPO, lens_revision=core.LENS_REVISION, adapter_path=core.LENS_PATH,
        model_dir=str(model.resolve()), adapter_dir=str(adapter.resolve()), completed_epoch=time.time(),
        storage='local_nvme', full_weight_sha256_verified=True, canonical_cache_unchanged=True,
        weight_manifest_sha256=core.WEIGHT_MANIFEST_SHA256, fork_archive_sha256=core.FORK_SHA256,
        files=files, runtime_versions=v)
    core.check_staging_receipt(receipt, manifest, model, adapter, admission['allocation_start_epoch'], 4500)
    ops.write(out / 'STAGING_RECEIPT.json', receipt)
    ops.write(out / 'TRANSFER_RECEIPT.json', dict(started_epoch=req['stage_start_epoch'], finished_epoch=time.time(),
        files=verified, bytes=sum(e['size_bytes'] for e in entries), free_bytes_after=shutil.disk_usage(out).free,
        anonymous=True, canonical_objects_sha256_verified=True, provider_release_verified=False))
    ops.seal(out, ['STAGING_RECEIPT.json', 'TRANSFER_RECEIPT.json', 'DISK_BEFORE.json'], status='STAGED', track='G')
    ops.deadline(end)


def supervise(req, out):
    try:
        ops.admission(req['admission'], req['admission_sha256'], 'weight_staging')
    except ops.NoFit as error:
        return ops.rejected_admission(out, req, error, 'staging_admission')
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    req = dict(req, stage_start_epoch=time.time())
    ops.write(out / 'REQUEST.json', req)
    with (out / 'worker.log').open('x') as log:
        proc = subprocess.Popen([sys.executable, '-m', 'projects.g_agreement.e74.stage', '--worker', str(out / 'REQUEST.json'), '--out', str(out)],
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=max(.01, req['stage_start_epoch'] + 3600 - time.time()))
        except subprocess.TimeoutExpired:
            code = 124
        finally:
            core.kill_group(proc.pid)
    if time.time() > req['stage_start_epoch'] + 3600:
        code = 124
    rejected = json.loads((out/'NO_FIT.json').read_bytes()) if (out/'NO_FIT.json').exists() else None
    if rejected is not None: code = ops.NO_FIT_EXIT
    report = dict(status='NO_FIT' if rejected else 'STAGED' if code == 0 else 'STOP_STAGING', exit_code=code,
                  provider_release_verified=False, no_automatic_retry=True)
    if rejected: report['rejected_forecast'] = rejected
    ops.write(out/'SUPERVISOR.json', report)
    if rejected:
        names = [str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'worker.log']
        ops.seal(out, names, track='G', **report)
        print(json.dumps(report))
    return code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request', type=Path); p.add_argument('--worker', type=Path); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); source = a.worker or a.request
    if source is None: p.error('--request required')
    req = json.loads(source.read_bytes())
    if a.worker:
        try:
            worker(req, a.out.resolve()); return 0
        except ops.NoFit as error:
            ops.record_no_fit(a.out.resolve(), error, 'staging_worker')
            return ops.NO_FIT_EXIT
    return supervise(req, a.out.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
