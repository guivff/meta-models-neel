"""One E74 engine: fixed smoke -> sealed capture -> external CPU/GO -> readers.

No labels, category names, probe fits, credentials or provider operations belong
in this process. An I-2 GO attests to the CPU-verified committed forecast using
hashes only. The provider hard stop remains an independent operator obligation.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import numpy as np
from . import ops, smoke as core, smoke50, hardware

PORT_SHA = 'd2a84037e6b20b4aeae309fbc2bd7fdfb26ffaa7b7d2be81b01fbd30d5a281b8'
ITEM_SHA = 'c3f5c82f989c642cc25f6e4dc5787eb1d215ec7c4b18430652e9905d36925f95'
N = 14184
READERS = 6804
WIDTH = 6144
BATCH = 512
LIMIT = 20_000_000


class RealBatchMean:
    """Unpadded throughput from completed production batches only.

    Equal-sized batches give the arithmetic batch mean per item. Weight by
    actual item count for a partial batch. The planning proxy is used only
    before any real batch; it is not a floor or a synthetic observation.
    """
    def __init__(self, prior_rate):
        self.rate = prior_rate
        self.seconds = 0.0
        self.items = 0
        self.batches = 0

    def observe(self, seconds, items):
        ops.require(type(items) is int and items > 0 and
                    type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
                    'invalid real batch timing')
        self.seconds += seconds
        self.items += items
        self.batches += 1
        self.rate = self.seconds / self.items

    def evidence(self):
        return dict(rule='running_mean_real_batches', authority='a6d0e06ee85e700ae12c425acc62a7471cb52f97',
                    seconds=self.seconds, items=self.items, batches=self.batches,
                    seconds_per_item=self.rate, padding_applied_here=False)


def phase(out, name, end):
    ops.deadline(end)
    # Only this small supervisor pointer is replaceable; scientific outputs are exclusive.
    temp = out / ('PHASE.' + name + '.json')
    ops.write(temp, {'phase': name, 'deadline_epoch': end, 'started_epoch': time.time()})
    os.replace(temp, out / 'PHASE.json')


def pack(path, members):
    with Path(path).open('xb') as f, tarfile.open(fileobj=f, mode='w') as tar:
        for name, raw in sorted(members.items()):
            ops.safe(Path('/archive'), name)
            m = tarfile.TarInfo(name); m.size = len(raw); m.mode = 0o600
            tar.addfile(m, io.BytesIO(raw))
    ops.require(Path(path).stat().st_size <= LIMIT, 'shard archive exceeds20MB')
    with Path(path).open('rb') as f: os.fsync(f.fileno())


def unpack(path, allowed):
    ops.require(Path(path).stat().st_size <= LIMIT, 'archive too large')
    with tarfile.open(path) as tar:
        entries = tar.getmembers()
        ops.require(len(entries) == len(allowed) and {m.name for m in entries} == set(allowed), 'archive member mismatch')
        ops.require(all(m.isfile() and m.size <= LIMIT for m in entries) and sum(m.size for m in entries) <= LIMIT,
                    'archive contains unsafe/oversized members')
        return {m.name: tar.extractfile(m).read() for m in entries}


def load_items(path):
    ops.require(ops.sha(path) == ITEM_SHA, 'frozen capture inputs differ')
    rows = [json.loads(s) for s in Path(path).read_text().splitlines()]
    validate_items(rows, N)
    return rows


def validate_items(rows, count):
    ops.require(len(rows) == count and len({r['id'] for r in rows}) == count, 'incomplete/duplicate capture input')
    for r in rows:
        ops.require(set(r) == {'id', 'ids', 'read_position'} and core.SHA_RE.fullmatch(r['id']), 'non-allowlisted input field')
        ops.require(0 < len(r['ids']) <= 550 and all(type(i) is int and 0 <= i < 154856 for i in r['ids']), 'invalid prefix')
        ops.require(type(r['read_position']) is int and r['read_position'] == len(r['ids']) - 1, 'read point is not final prefix token')


def read_plan(path, digest, items):
    obj = ops.bound(path, digest)
    ops.require(set(obj) == {'schema_version', 'experiment', 'port_seal_sha256', 'item_input_sha256', 'ids'}, 'reader plan fields differ')
    ops.require(obj['experiment'] == 'E74' and obj['schema_version'] == 1 and obj['port_seal_sha256'] == PORT_SHA
                and obj['item_input_sha256'] == ITEM_SHA, 'reader plan provenance differs')
    ids = obj['ids']
    ops.require(len(ids) == READERS and len(set(ids)) == READERS and set(ids) <= {r['id'] for r in items}, 'reader coverage differs')
    return ids


def write_capture(path, ids, tensors):
    import torch
    ops.require(len(tensors) == len(ids) and all(tuple(t.shape) == (1, WIDTH) for t in tensors), 'capture shape differs')
    a = torch.cat(tensors).detach().to(device='cpu', dtype=torch.float32).numpy()
    ops.require(np.isfinite(a).all() and np.all(np.linalg.norm(a, axis=1) > 0), 'nonfinite/zero capture')
    buf = io.BytesIO(); np.save(buf, a, allow_pickle=False)
    pack(path, {'h51.npy': buf.getvalue(), 'ids.json': ops.encoded(ids)})


def read_capture(path):
    data = unpack(path, {'h51.npy', 'ids.json'})
    ids = json.loads(data['ids.json']); a = np.load(io.BytesIO(data['h51.npy']), allow_pickle=False)
    ops.require(a.shape == (len(ids), WIDTH) and a.dtype == np.float32 and np.isfinite(a).all(), 'invalid capture payload')
    ops.require(len(ids) == len(set(ids)) and all(core.SHA_RE.fullmatch(i) for i in ids), 'invalid capture identities')
    return ids, a


GO_FIELDS = {'issuer', 'experiment', 'decision', 'checked_epoch', 'capture_seal_sha256', 'port_seal_sha256',
             'reader_plan_sha256', 'cpu_probe_seal_sha256', 'forecast_record_sha256', 'forecast_commit',
             'category_binding_sha256', 'asset_card_sha256', 'cpu_intake_seal_sha256', 'rg2_not_evaluable_permanent',
             'forecast_commit_verified', 'capture_pull_verified', 'cpu_probes_verified', 'reader_outputs_accessed',
             'source_seal_sha256', 'provider_stop_epoch'}


def check_go(go, req, capture_digest, captured_epoch, now):
    ops.require(set(go) == GO_FIELDS and go['issuer'] == 'I-2' and go['experiment'] == 'E74' and go['decision'] == 'GO', 'invalid I-2 GO envelope')
    for key in ('cpu_probe_seal_sha256', 'forecast_record_sha256', 'category_binding_sha256', 'cpu_intake_seal_sha256'):
        ops.require(isinstance(go[key], str) and core.SHA_RE.fullmatch(go[key]), 'missing CPU/forecast hash')
    ops.require(len(go['forecast_commit']) == 40 and all(x in '0123456789abcdef' for x in go['forecast_commit']), 'full forecast commit required')
    ops.require(captured_epoch <= go['checked_epoch'] <= now, 'GO chronology differs')
    for key, value in {'capture_seal_sha256': capture_digest, 'port_seal_sha256': PORT_SHA,
                       'reader_plan_sha256': req['reader_plan_sha256'], 'source_seal_sha256': req['source_seal_sha256'],
                       'asset_card_sha256': 'dcb6d67bebaf06ab5312e2d30201e88d805d406bbc9bdfdc1502f3745ec748e5'}.items():
        ops.require(go[key] == value, 'GO provenance differs: ' + key)
    ops.require(go['rg2_not_evaluable_permanent'] is True and go['forecast_commit_verified'] is True
                and go['capture_pull_verified'] is True and go['cpu_probes_verified'] is True
                and go['reader_outputs_accessed'] is False, 'pre-GO CPU/forecast custody incomplete')
    ops.require(go['provider_stop_epoch'] == req['admission_obj']['provider_stop_epoch'], 'GO changes provider cap')


def await_go(req, out, capture_digest, captured_epoch):
    end = min(captured_epoch + 600, req['admission_obj']['provider_stop_epoch'])
    phase(out, 'CPU_FORECAST_GO_WAIT', end)
    path = Path(req['go_file'])
    while True:
        ops.deadline(end)
        ops.budget(req['admission_obj'], hardware.phase_forecast(req['admission_obj'])['readouts'] + 120)
        if path.exists():
            # I-2 must atomically publish this file on its controlled local channel.
            go = json.loads(path.read_bytes())
            check_go(go, req, capture_digest, captured_epoch, time.time())
            ops.write(out / 'ACCEPTED_GO.json', go)
            return
        time.sleep(.25)


def run_resident(req, out, engine, runtime, fixtures, items, reader_ids):
    """Engine is constructed exactly once by worker; CPU tests inject a fake engine."""
    admission = req['admission_obj']
    forecast = hardware.phase_forecast(admission)
    config = hardware.profile(admission)
    ops.write(out/'SCIENCE_ONCE.json', {'claimed_epoch': time.time(), 'fixture_sha256': smoke50.FIXTURE_SHA})
    result = smoke50.run50(fixtures, runtime, engine, req['adapter_dir'], expected_workers=config['gpu_count'])
    ops.deadline(req['deadline_epoch'])
    sm = out / 'smoke'; sm.mkdir()
    ops.write(sm / 'STATISTICS.json', dict(result, boot_seconds=req['boot_seconds'], fixture_sha256=smoke50.FIXTURE_SHA, hardware=config))
    ops.seal(sm, ['STATISTICS.json'], status='SMOKE50_STATISTICS_SEALED', track='G')
    ops.require(result['passed'], 'STOP_SMOKE_CRITERION_FAILED; no retuning')
    ops.deadline(req['deadline_epoch'])
    phase(out, 'CAPTURE', admission['provider_stop_epoch'])
    engine.set_lens(None)
    ops.require(engine.merged is None, 'capture requires unmerged base')
    cap = out / 'capture'; cap.mkdir(); names = []; timing = RealBatchMean(forecast['capture'] / N)
    for start in range(0, len(items), BATCH):
        batch = items[start:start + BATCH]
        gate = ops.budget(admission, (len(items)-start)*timing.rate + 600 + forecast['readouts'] + 120)
        prefix = f'{start//BATCH:04d}'
        ops.write(cap / (prefix + '.CLAIM.json'), {'ids_sha256': hashlib.sha256(ops.encoded([x['id'] for x in batch])).hexdigest(), 'gate': gate})
        t = time.monotonic()
        acts = engine.capture_h51([x['ids'] for x in batch], [[x['read_position']] for x in batch])
        name = prefix + '.tar'; write_capture(cap / name, [x['id'] for x in batch], acts)
        elapsed = time.monotonic() - t; timing.observe(elapsed, len(batch))
        receipt = prefix + '.json'
        ops.write(cap / receipt, {'archive_sha256': ops.sha(cap/name), 'n': len(batch), 'seconds': elapsed,
                                'block': 51, 'dtype': 'float32', 'width': WIDTH, 'reforecast': timing.evidence()})
        names.extend([name, receipt, prefix + '.CLAIM.json'])
        ops.budget(admission, (len(items)-start-len(batch))*timing.rate + 600 + forecast['readouts'] + 120)
    ops.seal(cap, names, status='CAPTURE_COMPLETE', track='G', input_seal_sha256=PORT_SHA,
             item_input_sha256=ITEM_SHA, n=len(items), block=51, width=WIDTH, source_seal_sha256=req['source_seal_sha256'])
    captured_epoch = time.time(); cap_digest = ops.sha(cap/'SEAL.json')
    await_go(req, out, cap_digest, captured_epoch)
    phase(out, 'READERS', admission['provider_stop_epoch'])
    # Recheck sealed capture before consuming; no second model forward or recapture.
    ops.verify_seal(cap/'SEAL.json', cap_digest)
    vectors = {}
    wanted = set(reader_ids)
    for name in names:
        if name.endswith('.tar'):
            ids, a = read_capture(cap/name)
            for i, x in enumerate(ids):
                if x in wanted: vectors[x] = a[i].copy()
    ops.require(set(vectors) == wanted, 'test capture coverage incomplete')
    engine.set_lens(req['adapter_dir'], keep_base='gpu')
    readers = out/'readers'; readers.mkdir(); names = []; timing = RealBatchMean(forecast['readouts'] / READERS)
    import torch
    for start in range(0, len(reader_ids), BATCH):
        ids = reader_ids[start:start+BATCH]; prefix = f'{start//BATCH:04d}'
        gate = ops.budget(admission, (len(reader_ids)-start)*timing.rate + 120)
        ops.write(readers/(prefix+'.CLAIM.json'), {'ids_sha256': hashlib.sha256(ops.encoded(ids)).hexdigest(), 'gate': gate})
        t = time.monotonic()
        outputs = engine.verbalize(torch.from_numpy(np.stack([vectors[x] for x in ids])), n=1, temperature=0.0, cap=16, seed=0, alpha=54.1)
        ops.require(len(outputs) == len(ids) and all(isinstance(x, list) and len(x) == 1 and isinstance(x[0], str) for x in outputs), 'one output per test item required')
        name = prefix+'.tar'
        raw = b''.join((json.dumps({'id': i, 'readout': x[0]}, ensure_ascii=False) + '\n').encode() for i, x in zip(ids, outputs))
        pack(readers/name, {'readouts.jsonl': raw})
        elapsed = time.monotonic()-t; timing.observe(elapsed, len(ids))
        receipt = prefix+'.json'
        ops.write(readers/receipt, {'archive_sha256': ops.sha(readers/name), 'n': len(ids), 'seconds': elapsed, 'reforecast': timing.evidence()})
        names.extend([name, receipt, prefix+'.CLAIM.json'])
        ops.budget(admission, (len(reader_ids)-start-len(ids))*timing.rate + 120)
    ops.seal(readers, names, status='READERS_COMPLETE_UNOPENED', track='G', n=len(reader_ids),
             capture_seal_sha256=cap_digest, go_sha256=ops.sha(out/'ACCEPTED_GO.json'),
             readouts_human_inspected=False, judging_authorized_by_this_runner=False)
    phase(out, 'COMPLETE', admission['provider_stop_epoch'])


def worker(req, out):
    ops.require(not sys.flags.optimize, 'author assertions must remain enabled')
    admission = ops.admission(req['admission'], req['admission_sha256'], 'resident_smoke_capture')
    config = hardware.profile(admission)
    req = dict(req, admission_obj=admission)
    ops.require(admission['source_seal_sha256'] == req['source_seal_sha256'], 'admission source pin differs')
    ops.verify_seal(req['source_seal'], req['source_seal_sha256'])
    ops.write(out/'ENGINE_ONCE.json', {'claimed_epoch': time.time(), 'source_seal_sha256': req['source_seal_sha256']})
    smoke50.validate_clocks(req, time.time(), admission)
    ops.require(req['allocation_start_epoch'] == admission['allocation_start_epoch'], 'allocation clock differs')
    ops.require(0 < req['archive_staging_started_epoch'] <= req['archive_staging_finished_epoch'] <= req['science_start_epoch'], 'archive stage clocks missing')
    archive = ops.bound(req['archive_receipt'], req['archive_receipt_sha256'])
    ops.require(archive['status'] == 'VERIFIED' and archive['started_epoch'] == req['archive_staging_started_epoch']
                and archive['finished_epoch'] == req['archive_staging_finished_epoch'], 'actual archive receipt required')
    ops.require(archive['source_seal_sha256'] == req['source_seal_sha256'], 'archive source pin differs')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      VLLM_LENS_CUDA_GRAPHS='1', VLLM_ALLOW_INSECURE_SERIALIZATION='1', VLLM_LENS_MERGE_ALLOW_TP='1')
    items = load_items(Path(req['items']))
    reader_ids = read_plan(req['reader_plan'], req['reader_plan_sha256'], items)
    fixtures = smoke50.load_inputs(Path(req['fixtures']), Path(req['input_seal']))
    manifest = core.load_bound_json(Path(req['weight_manifest']), core.WEIGHT_MANIFEST_SHA256)
    staging = core.load_bound_json(Path(req['staging_receipt']), req['staging_receipt_sha256'])
    ops.require(staging['completed_epoch'] <= req['science_start_epoch'], 'weight receipt not complete before boot')
    core.check_staging_receipt(staging, manifest, Path(req['model_dir']), Path(req['adapter_dir']), req['allocation_start_epoch'], 4500)
    core.verify_fork(Path(req['fork_archive'])); core.check_dependencies(staging['runtime_versions'])
    runtime = core.import_author_runtime(Path(req['runtime']))
    import torch
    ops.budget(admission, sum(hardware.phase_forecast(admission).values()) + 600 + 120)
    phase(out, 'BOOT_SMOKE', req['deadline_epoch']); t = time.monotonic()
    engine = hardware.construct(runtime, torch, req['model_dir'], config)
    req['boot_seconds'] = time.monotonic() - t
    ops.require(core.sha256(Path(req['model_dir'])/'hf_quant_config.json') == manifest['author_quant_override']['derived_hf_quant_config_sha256'], 'derived quant config differs')
    run_resident(req, out, engine, runtime, fixtures, items, reader_ids)


def supervise(req, out):
    try:
        a = ops.admission(req['admission'], req['admission_sha256'], 'resident_smoke_capture')
    except ops.NoFit as error:
        return ops.rejected_admission(out, req, error, 'resident_admission')
    smoke50.validate_clocks(req, time.time(), a)
    out.mkdir(parents=True, exist_ok=False, mode=0o700); ops.write(out/'REQUEST.json', req)
    # At most the admitted hardware-specific affordable lifetime; reserve the complete quoted extras.
    cost_end = a['allocation_start_epoch'] + (hardware.limits(a)['cap_usd']/1.25-a['other_cost_upper_bound_usd'])*3600/a['replica_hourly_usd']
    hard_end = min(cost_end, a['provider_stop_epoch']) - 120
    with (out/'worker.log').open('x') as log:
        proc = subprocess.Popen([sys.executable, '-m', 'projects.g_agreement.e74.resident', '--worker', str(out/'REQUEST.json'), '--out', str(out)],
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        code = 124
        try:
            while proc.poll() is None:
                current = json.loads((out/'PHASE.json').read_bytes()) if (out/'PHASE.json').exists() else {'deadline_epoch': req['deadline_epoch']}
                if time.time() > cost_end - 120:
                    try:
                        ops.budget(a, 120)
                    except ops.NoFit as error:
                        if not (out/'NO_FIT.json').exists():
                            ops.record_no_fit(out, error, 'resident_cost_watchdog')
                        code = ops.NO_FIT_EXIT
                        break
                if time.time() >= min(current['deadline_epoch'], hard_end): break
                time.sleep(.1)
            else:
                code = proc.returncode
        finally:
            core.kill_group(proc.pid)
    names = [str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'worker.log']
    rejected = json.loads((out/'NO_FIT.json').read_bytes()) if (out/'NO_FIT.json').exists() else None
    if rejected is not None: code = ops.NO_FIT_EXIT
    status = 'NO_FIT' if rejected else 'COMPLETE' if code == 0 else 'STOP_INCOMPLETE'
    # STOP seals retain all once-only partial batches and claims; never replay them.
    report = dict(status=status, exit_code=code, provider_release_verified=False)
    if rejected: report['rejected_forecast'] = rejected
    ops.seal(out, names, track='G', no_automatic_retry=True, reader_text_displayed=False, **report)
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
            ops.record_no_fit(a.out.resolve(), error, 'resident_worker')
            return ops.NO_FIT_EXIT
    return supervise(req, a.out.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
