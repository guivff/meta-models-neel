"""E35 conditional SAE training and one unchanged gate, frozen 2026-10-25.

Integrator-only offline execution. No activation corpus is written to disk.
All pilots use training positions; retained training begins after admission.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import signal
import time

from fallback_sae import FIXED_CONFIG, NORMALIZATION_MANIFEST, SAETrainer
from gate_inputs import dump_new, sha, verify_sample
from gate_math import GateAccumulator
from gate_worker import capture44, decoder_blocks, TARGET_REPO, TARGET_REVISION
from training_clock import TrainingClock, NoFit, RETRIEVAL_RESERVE
from training_stream import verify_training_cache, iter_training_chunks


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REQUEST_FILENAME = 'LAUNCH_REQUEST.training.json'
PLAN_FILENAME = 'FALLBACK_TRAINING_PLAN.20261025.json'
NORMALIZATION_FILENAME = 'FALLBACK_NORMALIZATION.20261025.json'
OUTPUT_PATH = 'cache/g_agreement/understand/e35/training-20261025/out'
CACHE_PATH = 'cache/g_agreement/understand/e35/training-tokens-20261025'
SAMPLE_SHA = 'dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593'
PRIOR_RESULT_SHA = '9eeb3122927af350408f84ddf631c12fb2329ddc2c276de7db3ccada57d284c3'
PRIOR_SEAL_SHA = '0e374e11fc7d7bda66a3b920ae54f4f24be1313f5fe303760a5b1a843b61893c'
CAPTURE_TOKENS = 512


def read(path):
    return json.loads(Path(path).read_text())


def verify_sources(request, root=ROOT):
    required = {'training_worker.py', 'training_stream.py', 'training_clock.py',
                'fallback_sae.py', 'FALLBACK_TRAINING_CHOICES.20261025.md',
                PLAN_FILENAME, NORMALIZATION_FILENAME, 'FALLBACK_CORPUS_PIN.20261025.json',
                'gate_worker.py', 'gate_inputs.py', 'gate_math.py', 'sae.py',
                'GATE_SAMPLE.json', 'LAUNCH_REQUEST.gate-rerun1.json'}
    if (request.get('experiment') != 'E35' or request.get('stage') != 'training'
            or request.get('output_path') != OUTPUT_PATH
            or not required <= set(request.get('source_files', {}))):
        raise ValueError('complete fixed training request required')
    base = root / 'results/g_agreement/understand/e35'
    for name, expected in request['source_files'].items():
        path = (base / name).resolve()
        if not path.is_relative_to(base.resolve()) or sha(path) != expected:
            raise ValueError('training source checksum mismatch')
    plan = read(base / PLAN_FILENAME)
    if plan['training'] != asdict(FIXED_CONFIG) or read(base / NORMALIZATION_FILENAME) != NORMALIZATION_MANIFEST:
        raise ValueError('fixed training configuration or normalization mismatch')
    if plan['normalization_manifest_sha256'] != sha(base / NORMALIZATION_FILENAME):
        raise ValueError('normalization byte pin mismatch')


def verify_prior_gate(request, root=ROOT):
    folder = (root / request['prior_gate_dir']).resolve()
    if not folder.is_relative_to((root / 'cache/g_agreement/understand/e35').resolve()):
        raise ValueError('prior gate evidence must stay in E35 cache')
    pins = request['prior_gate_files']
    required = {'GATE_RESULT.json', 'OUTPUT_SEAL.json', 'CLOCK.json', 'assignment.json'}
    if not required <= set(pins) or pins['GATE_RESULT.json'] != PRIOR_RESULT_SHA or pins['OUTPUT_SEAL.json'] != PRIOR_SEAL_SHA:
        raise ValueError('exact delivered transfer failure evidence required')
    for name, digest in pins.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or sha(path) != digest:
            raise ValueError('prior gate evidence checksum mismatch')
    gate, seal = read(folder / 'GATE_RESULT.json'), read(folder / 'OUTPUT_SEAL.json')
    metrics = gate.get('metrics') or {}
    if (gate.get('experiment') != 'E35' or gate.get('stage') != 'gate'
            or gate.get('status') != 'FAIL' or seal.get('status') != 'FAIL'
            or metrics.get('passed') is not False or metrics.get('n_tokens') != 50000
            or metrics.get('d_model') != 5120 or metrics.get('d_sae') != 81920
            or gate.get('sample_sha256') != SAMPLE_SHA
            or gate.get('request_sha256') != sha(root / 'results/g_agreement/understand/e35/LAUNCH_REQUEST.gate-rerun1.json')
            or gate.get('assignment_sha256') != pins['assignment.json']
            or seal.get('files', {}).get('GATE_RESULT.json') != pins['GATE_RESULT.json']
            or seal.get('files', {}).get('CLOCK.json') != pins['CLOCK.json']):
        raise ValueError('complete sealed scientific transfer FAIL required')
    fvu, dead = metrics.get('fvu'), metrics.get('dead_fraction')
    if (type(fvu) not in (float, int) or type(dead) not in (float, int)
            or not math.isfinite(fvu) or not math.isfinite(dead)
            or fvu < 0 or not 0 <= dead <= 1 or not (fvu > .25 or dead >= .1)):
        raise ValueError('transfer failure thresholds inconsistent')
    return {'result_sha256': pins['GATE_RESULT.json'], 'seal_sha256': pins['OUTPUT_SEAL.json'],
            'large_arrays_retrieved_for_this_worker': False,
            'large_array_seal_pins': {name: seal.get('files', {}).get(name)
                                      for name in ('h.npy', 'reconstruction.npy')},
            'large_arrays_used_for_fallback': False, 'fallback_uses_new_capture': True}


def verify_accounting(path, assignment):
    expected = assignment['prior_accounting']
    if sha(path) != expected['receipt_sha256']:
        raise ValueError('prior accounting receipt checksum mismatch')
    receipt = read(path)
    pods = receipt.get('pod_ids', [])
    if (receipt.get('status') != 'FINAL_OR_CONSERVATIVE'
            or receipt.get('previous_gpu_seconds') != assignment['previous_gpu_seconds']
            or receipt.get('mode') != expected['rerun_mode']
            or not isinstance(pods, list)
            or not all(pod in pods for pod in ('5wu4ujkbiotxom', '21wel7nawi51j3', '833ksjl7c6sxie'))):
        raise ValueError('complete matching prior-pod accounting required')
    return receipt


def claim_run(out, assignment_sha, request_sha, root=ROOT):
    out = Path(out)
    expected = (root / OUTPUT_PATH).resolve()
    if out.resolve() != expected:
        raise ValueError('exact once-only training output location required')
    guard = root / 'cache/g_agreement/understand/e35/training.RUN_ONCE.json'
    guard.parent.mkdir(parents=True, exist_ok=True)
    dump_new(guard, {'assignment_sha256': assignment_sha, 'request_sha256': request_sha,
                     'epoch': time.time()})
    out.mkdir(parents=True, exist_ok=False)


def write_clock(out, clock, progress):
    record = dict(clock.record(), worker_progress=dict(progress))
    temporary = out / 'CLOCK.tmp'
    temporary.write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    temporary.replace(out / 'CLOCK.json')


def verify_device_memory(total_bytes, free_bytes):
    if (type(total_bytes) is not int or type(free_bytes) is not int
            or total_bytes < 80_000_000_000 or free_bytes < 20_000_000_000
            or free_bytes > total_bytes):
        raise NoFit('single-device memory admission failed')
    return {'passed': True, 'total_bytes': total_bytes, 'free_after_target_bytes': free_bytes,
            'minimum_total_bytes': 80_000_000_000, 'minimum_free_after_target_bytes': 20_000_000_000}


def hardware_record():
    import importlib.metadata
    import torch
    free, total = torch.cuda.mem_get_info()
    return {'torch': str(torch.__version__), 'transformers': importlib.metadata.version('transformers'),
            'cuda_runtime': torch.version.cuda, 'cudnn': torch.backends.cudnn.version(),
            'device_name': torch.cuda.get_device_name(), 'total_bytes': total, 'free_bytes': free,
            'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
            'peak_reserved_bytes': torch.cuda.max_memory_reserved(),
            'capture_path': 'gate_worker.capture44 full target forward; no target backward',
            'sae_dtype': 'float32', 'target_dtype': 'bfloat16',
            'tf32': False, 'cublas_workspace_config': ':4096:8'}


def rearm_science_alarm(clock):
    deadline = min(clock.a['deadline_epoch'] - RETRIEVAL_RESERVE,
                   clock.science_start + clock.science_limit)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.time()))


def load_target(clock):
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM
    clock.check()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError('exactly one visible CUDA GPU required')
    if torch.cuda.get_device_properties(0).total_memory < 80_000_000_000:
        raise NoFit('target and SAE require an admitted 80GB device')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(20261025)
    target = Path(snapshot_download(TARGET_REPO, revision=TARGET_REVISION, local_files_only=True))
    model = AutoModelForCausalLM.from_pretrained(target, dtype=torch.bfloat16,
                                                device_map='cuda', local_files_only=True)
    model.eval()
    model.requires_grad_(False)
    decoder_blocks(model)
    free, total = torch.cuda.mem_get_info()
    memory = verify_device_memory(int(total), int(free))
    clock.check()
    return model, target / 'tokenizer.json', memory


def training_tensor(h):
    """Leave inference mode before cloning; autograd may save this normal tensor."""
    import torch
    with torch.inference_mode(False):
        x = h.detach().float().clone()
    if torch.is_inference(x) or x.ndim != 2 or not torch.isfinite(x).all():
        raise ValueError('finite normal tensor required for SAE autograd')
    return x


def activation_batches(model, chunks, clock, progress, *, capture=capture44,
                       config=FIXED_CONFIG, device='cuda'):
    """Bounded 4096-position buffer; retain every document tail without padding."""
    import torch
    buffer = torch.empty((config.batch_size, config.d_model), dtype=torch.float32, device=device)
    used = 0
    for chunk in chunks:
        clock.check()
        ids = chunk['ids']
        if not 0 < len(ids) <= CAPTURE_TOKENS or chunk['token_end'] - chunk['token_start'] != len(ids):
            raise ValueError('complete document-local cache chunk required')
        h = training_tensor(capture(model, ids, list(range(len(ids))), device=device))
        if h.shape != (len(ids), config.d_model):
            raise ValueError('training capture residual shape mismatch')
        progress['training_chunks_captured'] += 1
        offset = 0
        while offset < len(h):
            take = min(config.batch_size - used, len(h) - offset)
            buffer[used:used + take].copy_(h[offset:offset + take])
            used, offset = used + take, offset + take
            if used == config.batch_size:
                yield buffer
                used = 0
    if used:
        yield buffer[:used]


def gate_process(model, sae, ids, positions, *, capture=capture44, device='cuda'):
    import numpy as np
    import torch
    h = capture(model, ids, positions, device=device)
    if h.shape != (len(positions), sae.d_model):
        raise ValueError('gate residual shape mismatch')
    reconstruction = []
    active = np.zeros(sae.d_sae, dtype=bool)
    with torch.inference_mode():
        for start in range(0, len(h), 256):
            z = sae.encode(h[start:start + 256])
            if not torch.isfinite(z).all():
                raise ValueError('nonfinite gate SAE code')
            r = sae.decode(z)
            if not torch.isfinite(r).all():
                raise ValueError('nonfinite gate reconstruction')
            reconstruction.append(r.cpu().numpy())
            active |= z.gt(0).any(dim=0).cpu().numpy()
    return h.cpu().numpy(), np.concatenate(reconstruction), active


def run_pilots(model, chunks_factory, sample, ids_by_document, clock, heartbeat, *,
               capture=capture44, trainer_factory=SAETrainer, synchronize=None,
               config=FIXED_CONFIG, device='cuda'):
    """Three timings of each kind, all train-only; discard the scratch model."""
    import torch
    synchronize = synchronize or torch.cuda.synchronize
    count = max(3, math.ceil(config.batch_size / CAPTURE_TOKENS))
    full = []
    for chunk in chunks_factory():
        if len(chunk['ids']) == CAPTURE_TOKENS:
            full.append(chunk)
            if len(full) == count:
                break
    if len(full) != count or len(sample['pilot_document_ids']) != 3:
        raise ValueError('complete training-only pilot material required')
    scratch = trainer_factory(device=device, config=config, synthetic=True, timing_force_auxiliary=True)
    clock.begin_science()
    # Warm-up is training-only and inside the non-resetting science clock.
    warm = training_tensor(capture(model, full[0]['ids'], list(range(CAPTURE_TOKENS)), device=device))
    with torch.inference_mode():
        scratch.model.decode(scratch.model.encode(warm))
    synchronize()
    del warm
    buffer = torch.empty((config.batch_size, config.d_model), dtype=torch.float32, device=device)
    filled = 0
    for i, chunk in enumerate(full):
        clock.check()
        synchronize()
        started = time.monotonic()
        h = training_tensor(capture(model, chunk['ids'], list(range(CAPTURE_TOKENS)), device=device))
        synchronize()
        elapsed = time.monotonic() - started
        if i < 3:
            clock.record_pilot('capture512', elapsed)
            heartbeat()
        take = min(len(h), config.batch_size - filled)
        if take:
            buffer[filled:filled + take].copy_(h[:take])
            filled += take
    if filled != config.batch_size:
        raise ValueError('full scratch training batch required')
    for _ in range(3):
        clock.check()
        synchronize()
        started = time.monotonic()
        scratch.step(buffer, first_position=scratch.tokens_seen, split='train')
        synchronize()
        clock.record_pilot('train4096', time.monotonic() - started)
        heartbeat()
    for key in sample['pilot_document_ids']:
        clock.check()
        if len(ids_by_document[key]) != CAPTURE_TOKENS:
            raise ValueError('exact 512-token training gate pilot required')
        synchronize()
        started = time.monotonic()
        gate_process(model, scratch.model, ids_by_document[key], list(range(CAPTURE_TOKENS)),
                     capture=capture, device=device)
        synchronize()
        clock.record_pilot('gate512', time.monotonic() - started)
        heartbeat()
    del scratch, buffer


def run_science(model, chunks_factory, manifest, sample, ids_by_document, clock, out, heartbeat,
                progress, *, capture=capture44, trainer_factory=SAETrainer, synchronize=None,
                metric_factory=GateAccumulator, config=FIXED_CONFIG, device='cuda',
                runtime_record=hardware_record, arm_alarm=rearm_science_alarm):
    import torch
    from sae import QwenScopeSAE
    run_pilots(model, chunks_factory, sample, ids_by_document, clock, heartbeat,
               capture=capture, trainer_factory=trainer_factory, synchronize=synchronize,
               config=config, device=device)
    dump_new(out / 'PILOT_HARDWARE.json', runtime_record())
    clock.admit(manifest['n_chunks'], optimizer_steps=math.ceil(config.target_tokens / config.batch_size),
                gate_documents=len(sample['documents']))
    arm_alarm(clock)
    heartbeat()
    # Fresh seeded parameters; none of the scratch pilot updates are retained.
    trainer = trainer_factory(device=device, config=config, synthetic=False)
    for x in activation_batches(model, chunks_factory(), clock, progress,
                                capture=capture, config=config, device=device):
        clock.check()
        report = trainer.step(x, first_position=trainer.tokens_seen, split='train')
        progress.update(training_tokens=trainer.tokens_seen, optimizer_steps=trainer.steps,
                        last_training_loss=report['loss'])
        heartbeat()
    if trainer.tokens_seen != config.target_tokens or progress['training_chunks_captured'] != manifest['n_chunks']:
        raise ValueError('complete unique token stream required before final checkpoint')
    clock.check()
    params = trainer.checkpoint_tensors()
    checkpoint = out / 'layer44.fallback.sae.pt'
    with checkpoint.open('xb') as stream:
        torch.save(params, stream)
    checkpoint_sha = sha(checkpoint)
    normalization = out / 'NORMALIZATION.json'
    with normalization.open('xb') as stream:
        stream.write((HERE / NORMALIZATION_FILENAME).read_bytes())
    training_result = trainer.completed_manifest()
    training_result.update(sae_checkpoint_sha256=checkpoint_sha,
                           normalization_manifest_sha256=sha(normalization),
                           scratch_pilot_updates_discarded=3,
                           token_cache_seal_sha256=manifest['_verified_seal_sha256'])
    dump_new(out / 'TRAINING_RESULT.json', training_result)
    del trainer
    sae = QwenScopeSAE(params, k=config.k).to(device)
    del params
    clock.check()
    # Gate is once-only and begins only after the final checkpoint is sealed by hash.
    dump_new(out / 'fallback-gate.RUN_ONCE.json', {'sae_checkpoint_sha256': checkpoint_sha,
                                                'sample_sha256': SAMPLE_SHA})
    metric = metric_factory(config.d_model, config.d_sae)
    for record in sample['documents']:
        clock.check()
        h, r, active = gate_process(model, sae, ids_by_document[record['id']], record['positions'],
                                    capture=capture, device=device)
        metric.update(h, r, active_latents=active)
        progress['gate_documents'] += 1
        progress['gate_tokens'] += len(h)
        heartbeat()
    clock.check()
    return metric.result(), checkpoint_sha, sha(normalization)


def execute(args, clock, request, assignment, custody):
    import torch
    progress = {'training_chunks_captured': 0, 'training_tokens': 0,
                'optimizer_steps': 0, 'gate_documents': 0, 'gate_tokens': 0}
    heartbeat = lambda: write_clock(args.out, clock, progress)
    status, error_type, metrics = 'INCOMPLETE', None, None
    failure_category, retry_eligible = None, False
    checkpoint_sha = normalization_sha = None
    model = None
    started = time.time()
    try:
        seal_sha = assignment['training_cache_seal_sha256']
        manifest = verify_training_cache(args.training_cache, expected_seal_sha256=seal_sha)
        bindings = manifest['bindings']
        if (manifest['n_tokens'] != FIXED_CONFIG.target_tokens
                or bindings['source_commit'] != assignment['source_commit']
                or bindings['training_plan_sha256'] != sha(HERE / PLAN_FILENAME)
                or bindings['fineweb_pin_sha256'] != sha(HERE / 'FALLBACK_CORPUS_PIN.20261025.json')):
            raise ValueError('prepared training cache differs from committed source plan')
        manifest['_verified_seal_sha256'] = seal_sha
        model, tokenizer, memory = load_target(clock)
        dump_new(args.out / 'MEMORY_ADMISSION.json', memory)
        torch.cuda.reset_peak_memory_stats()
        sample = read(HERE / 'GATE_SAMPLE.json')
        if sha(HERE / 'GATE_SAMPLE.json') != SAMPLE_SHA or len(sample['documents']) != 487:
            raise ValueError('unchanged held-out gate sample required')
        ids = verify_sample(args.corpus, args.manifest, tokenizer, sample)
        chunks_factory = lambda: iter_training_chunks(args.training_cache, expected_seal_sha256=seal_sha)
        metrics, checkpoint_sha, normalization_sha = run_science(
            model, chunks_factory, manifest, sample, ids, clock, args.out, heartbeat, progress)
        status = 'PASS' if metrics['passed'] else 'FAIL'
    except Exception as exc:
        status = 'NO_FIT' if isinstance(exc, NoFit) else 'INCOMPLETE'
        error_type = type(exc).__name__
        operational = isinstance(exc, (NoFit, OSError, torch.cuda.OutOfMemoryError))
        failure_category = 'OPERATIONAL' if operational else 'VALIDITY_OR_UNCLASSIFIED'
        retry_eligible = operational
    finally:
        model = None
        if torch.cuda.is_initialized():
            torch.cuda.empty_cache()
    clock.status = status
    heartbeat()
    report = {'experiment': 'E35', 'stage': 'gate', 'status': status, 'metrics': metrics,
              'error_type': error_type, 'worker_started_epoch': started, 'worker_finished_epoch': time.time(),
              'failure_category': failure_category, 'operational_rebuild_eligible': retry_eligible,
              'request_sha256': sha(HERE / REQUEST_FILENAME), 'assignment_sha256': sha(args.assignment),
              'sample_sha256': SAMPLE_SHA, 'sae_checkpoint_sha256': checkpoint_sha,
              'normalization_manifest_sha256': normalization_sha, 'sae_k': 64,
              'accounting_receipt_sha256': sha(args.accounting_receipt),
              'transfer_gate_custody': custody, 'clock': clock.record(), 'progress': progress,
              'next_stage': 'frozen_blind_labelling_then_decomposition' if status == 'PASS' else
                            ('report_no_adequate_SAE_and_stop' if status == 'FAIL' else
                             ('report_operational_stop' if retry_eligible else 'report_validity_stop_no_retry')),
              'decomposition_calls': 0, 'heldout_gate_runs': int(progress['gate_documents'] > 0)}
    dump_new(args.out / 'GATE_RESULT.json', report)
    files = {p.name: sha(p) for p in args.out.iterdir() if p.is_file()}
    dump_new(args.out / 'OUTPUT_SEAL.json', {'status': status, 'files': files})
    print('E35 training', status, error_type or '')
    return 0 if status in ('PASS', 'FAIL') else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assignment', 'accounting-receipt', 'training-cache', 'corpus', 'manifest', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        request = read(HERE / REQUEST_FILENAME)
        verify_sources(request)
        assignment = read(args.assignment)
        verify_accounting(args.accounting_receipt, assignment)
        custody = verify_prior_gate(request)
        clock = TrainingClock(assignment, sha(HERE / REQUEST_FILENAME))
        if args.training_cache.resolve() != (ROOT / CACHE_PATH).resolve():
            raise ValueError('exact sealed training token cache location required')
        claim_run(args.out, sha(args.assignment), sha(HERE / REQUEST_FILENAME))
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', WANDB_MODE='disabled',
                          CUBLAS_WORKSPACE_CONFIG=':4096:8')

        def stop(signum, frame):
            raise NoFit('absolute stage deadline')

        signal.signal(signal.SIGALRM, stop)
        signal.setitimer(signal.ITIMER_REAL, max(.001, clock.a['deadline_epoch'] - RETRIEVAL_RESERVE - time.time()))
        try:
            return execute(args, clock, request, assignment, custody)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    except Exception as exc:
        print('E35 training INCOMPLETE', type(exc).__name__)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
