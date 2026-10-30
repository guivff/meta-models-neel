"""E35 transfer gate only. Offline, assigned by Integrator, once, with a hard clock."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time

from gate_inputs import dump_new, sha, verify_sample
from gate_math import GateAccumulator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STOP = datetime(2026, 10, 28, 22, 59, tzinfo=timezone.utc).timestamp()
TARGET_REPO = 'Qwen/Qwen3.6-27B'
TARGET_REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
RESERVE = 180
# 2026-10-25: §133 item 7 authorizes this single operational rerun only.
REQUEST_FILENAME = 'LAUNCH_REQUEST.gate-rerun1.json'
RERUN_AUTHORITY = '01c5775ecdb57525e42ab7a831b8928ddbb25944'
UNACCOUNTED_POD = '5wu4ujkbiotxom'


def read(path):
    return json.loads(Path(path).read_text())


class NoFit(TimeoutError):
    pass


def verify_sources(request, root=ROOT):
    required = {'gate_worker.py', 'gate_inputs.py', 'gate_math.py', 'sae.py',
                'GATE_SAMPLE.json', 'GATE_PLAN.20261025.json', 'REGISTRATION.5731e92e.md'}
    pins = request['source_files']
    if not required <= set(pins):
        raise ValueError('complete gate source/input pins required')
    base = root / 'results/g_agreement/understand/e35'
    for filename, expected in pins.items():
        path = (base / filename).resolve()
        if not path.is_relative_to(base.resolve()) or sha(path) != expected:
            raise ValueError('gate source/input checksum mismatch')


def verify_rerun_assignment(assignment, root=ROOT):
    """§133/7 bookkeeping is a launch prerequisite, not a new scientific gate."""
    if (type(assignment.get('gate_attempt')) is not int or assignment['gate_attempt'] != 2
            or assignment.get('rerun_authority_commit') != RERUN_AUTHORITY):
        raise ValueError('only the section-133 authorized second gate attempt is permitted')
    previous = assignment.get('previous_gpu_seconds')
    if type(previous) not in (float, int) or not math.isfinite(previous) or previous < 180:
        raise ValueError('at least 180 prior E35 GPU seconds must be carried forward')
    record = assignment.get('prior_pod_accounting', {})
    if (not isinstance(record, dict) or record.get('pod_id') != UNACCOUNTED_POD
            or record.get('resolved') is not True):
        raise ValueError('Integrator must resolve the section-133 pod accounting first')
    handoff = root / 'results/g_agreement/blindspot/HANDOFF.md'
    if not handoff.is_file() or sha(handoff) != record.get('handoff_sha256'):
        raise ValueError('pinned Integrator HANDOFF accounting evidence required')
    if UNACCOUNTED_POD not in handoff.read_text():
        raise ValueError('Integrator HANDOFF must identify the accounted pod')


class Clock:
    def __init__(self, assignment, request_sha, now=None):
        now = time.time() if now is None else now
        self.a = assignment
        self.science_start = None
        self.science_limit = None
        self.forecast = None
        self.pilot_seconds = []
        self.documents_done = 0
        self.tokens_done = 0
        self.status = 'SETUP'
        if (assignment.get('issuer') != 'integrator' or assignment.get('experiment') != 'E35'
                or assignment.get('stage') != 'gate' or assignment.get('gpu_count') != 1
                or not assignment.get('pod_id') or assignment.get('request_sha256') != request_sha):
            raise ValueError('exact single-GPU Integrator gate assignment required')
        if os.environ.get('RUNPOD_POD_ID') != assignment['pod_id']:
            raise ValueError('assignment does not belong to this RunPod pod')
        commit = assignment.get('source_commit')
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
            raise ValueError('exact pushed source commit required')
        for key in ('source_pushed', 'external_hardstop_verified', 'hold_renewer_verified'):
            if assignment.get(key) is not True:
                raise ValueError('Integrator push/hardstop/hold evidence required')
        for key in ('previous_gpu_seconds', 'allocated_gpu_seconds', 'provider_created_epoch',
                    'deadline_epoch', 'setup_deadline_epoch'):
            value = assignment.get(key)
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError('finite assignment timing fields required')
        start, allocation = assignment['provider_created_epoch'], assignment['allocated_gpu_seconds']
        if not (0 <= assignment['previous_gpu_seconds'] and RESERVE < allocation <= 3600
                and assignment['previous_gpu_seconds'] + allocation <= 21600):
            raise ValueError('E35 total/stage GPU allocation exceeded')
        if not start <= now < assignment['setup_deadline_epoch'] <= min(start + 1500, assignment['deadline_epoch'] - RESERVE):
            raise ValueError('setup assignment expired or invalid')
        if not assignment['setup_deadline_epoch'] < assignment['deadline_epoch'] <= min(STOP, start + allocation):
            raise ValueError('absolute/provider/programme deadline invalid')

    def check(self):
        now = time.time()
        limit = self.a['deadline_epoch'] - RESERVE
        if self.science_start is None:
            limit = min(limit, self.a['setup_deadline_epoch'])
        elif self.science_limit is not None:
            limit = min(limit, self.science_start + self.science_limit)
        if now >= limit:
            raise NoFit('gate clock exhausted')

    def begin_science(self):
        self.check()
        if self.science_start is not None:
            raise ValueError('science clock cannot reset')
        self.science_start = time.time()
        self.status = 'PILOT'

    def admit(self, documents):
        self.check()
        if len(self.pilot_seconds) != 3 or any(x <= 0 or not math.isfinite(x) for x in self.pilot_seconds):
            raise ValueError('three complete warmed pilot timings required')
        # Each pilot processes all 512 positions; retained docs process <=512.
        self.forecast = sum(self.pilot_seconds) + statistics.median(self.pilot_seconds) * documents
        self.science_limit = min(1.5 * self.forecast + 360,
                                 self.a['deadline_epoch'] - RESERVE - self.science_start)
        if self.forecast + 180 > self.science_limit:
            raise NoFit('full frozen sample does not fit; no subset or second request')
        self.status = 'RUNNING'

    def record(self):
        return {'status': self.status, 'first_science_epoch': self.science_start,
                'science_cap_seconds': self.science_limit, 'forecast_seconds': self.forecast,
                'pilot_seconds': self.pilot_seconds, 'documents_done': self.documents_done,
                'tokens_done': self.tokens_done, 'provider_elapsed_seconds': max(0, time.time() - self.a['provider_created_epoch']),
                'science_clock_resets': 0, 'retrieval_reserve_seconds': RESERVE}


def decoder_blocks(model):
    for path in ('model.layers', 'model.language_model.layers'):
        current = model
        try:
            for part in path.split('.'):
                current = getattr(current, part)
            if len(current) == 64:
                return current
        except AttributeError:
            pass
    raise ValueError('expected 64-block Qwen target')


def capture44(model, ids, positions, device='cuda'):
    import torch
    if not ids or not positions or len(set(positions)) != len(positions) or any(p < 0 or p >= len(ids) for p in positions):
        raise ValueError('valid unique prefix positions required')
    captured = {}

    def hook(module, inputs, output):
        h = output[0] if isinstance(output, tuple) else output
        if h.ndim != 3 or h.shape[0] != 1 or h.shape[1] != len(ids):
            raise ValueError('unexpected block44 output shape')
        captured['h'] = h[0, positions, :].detach().float()

    handle = decoder_blocks(model)[44].register_forward_hook(hook)
    try:
        with torch.inference_mode():
            model(input_ids=torch.tensor([ids], dtype=torch.long, device=device),
                  use_cache=False, logits_to_keep=1)
    finally:
        handle.remove()
    if 'h' not in captured or not torch.isfinite(captured['h']).all():
        raise ValueError('finite raw block44 output required')
    return captured['h']


def load_assets(clock):
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    from transformers import AutoModelForCausalLM
    from sae import QwenScopeSAE, PINNED_REPOSITORY, PINNED_REVISION, PINNED_FILENAME
    clock.check()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError('exactly one visible CUDA GPU required')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(20261025)
    target_path = Path(snapshot_download(TARGET_REPO, revision=TARGET_REVISION, local_files_only=True))
    # A deliberately partial SAE snapshot contains only these two staged files.
    # Do not require whole-repository snapshot completeness or reach the network.
    config_path = Path(hf_hub_download(repo_id=PINNED_REPOSITORY, filename='config.json',
                                      revision=PINNED_REVISION, local_files_only=True))
    weight_path = Path(hf_hub_download(repo_id=PINNED_REPOSITORY, filename=PINNED_FILENAME,
                                      revision=PINNED_REVISION, local_files_only=True))
    config = read(config_path)
    if sha(config_path) != read(HERE / 'GATE_PLAN.20261025.json')['sae']['config_sha256']:
        raise ValueError('pinned SAE config checksum mismatch')
    if (config.get('base_model') != 'Qwen/Qwen3.5-27B' or config.get('d_model') != 5120
            or config.get('d_sae') != 81920 or config.get('k') != 50
            or config.get('hook_point') != 'resid_post' or 44 not in config.get('layers', [])):
        raise ValueError('pinned layer44 SAE config contract mismatch')
    model = AutoModelForCausalLM.from_pretrained(target_path, dtype=torch.bfloat16,
                                                device_map='cuda', local_files_only=True)
    model.eval()
    model.requires_grad_(False)
    decoder_blocks(model)
    sae = QwenScopeSAE.from_checkpoint(weight_path, device='cuda')
    clock.check()
    return model, sae, target_path / 'tokenizer.json'


def process(model, sae, ids, positions):
    import numpy as np
    import torch
    h = capture44(model, ids, positions)
    if h.shape != (len(positions), 5120):
        raise ValueError('target residual width mismatch')
    recon, fired = [], np.zeros(81920, dtype=bool)
    with torch.inference_mode():
        for start in range(0, len(positions), 256):
            xhat, active = sae.reconstruct_and_fired(h[start:start + 256])
            recon.append(xhat.cpu().numpy())
            fired |= active.cpu().numpy()
    return h.cpu().numpy(), np.concatenate(recon), fired


def write_clock(out, clock):
    # A mutable runtime heartbeat is separate from immutable dated registrations.
    temporary = out / 'CLOCK.tmp'
    temporary.write_text(json.dumps(clock.record(), sort_keys=True, indent=2) + '\n')
    temporary.replace(out / 'CLOCK.json')


def claim_run(out, assignment_sha, request_sha):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # A changed output basename must not bypass the one-request guard.
    dump_new(out.parent / 'gate.RUN_ONCE.json', {'assignment_sha256': assignment_sha,
                                              'request_sha256': request_sha, 'epoch': time.time()})
    out.mkdir(exist_ok=False)


def execute(a, clock):
    import numpy as np
    import torch
    status, error_type, result = 'INCOMPLETE', None, None
    model = sae = None
    started = time.time()
    try:
        model, sae, tokenizer_path = load_assets(clock)
        sample = read(HERE / 'GATE_SAMPLE.json')
        ids = verify_sample(a.corpus, a.manifest, tokenizer_path, sample)
        clock.check()
        pilot_ids = sample['pilot_document_ids']
        # One unscored warm-up, on a training document, before the science clock.
        process(model, sae, ids[pilot_ids[0]], list(range(512)))
        torch.cuda.synchronize()
        clock.begin_science()
        for key in pilot_ids:
            clock.check()
            t = time.monotonic()
            process(model, sae, ids[key], list(range(512)))
            torch.cuda.synchronize()
            clock.pilot_seconds.append(time.monotonic() - t)
            write_clock(a.out, clock)
        clock.admit(len(sample['documents']))
        write_clock(a.out, clock)
        metric = GateAccumulator(5120, 81920)
        h_file = np.lib.format.open_memmap(a.out / 'h.npy', mode='w+', dtype='float32', shape=(50000, 5120))
        r_file = np.lib.format.open_memmap(a.out / 'reconstruction.npy', mode='w+', dtype='float32', shape=(50000, 5120))
        for record in sample['documents']:
            clock.check()
            h, r, active = process(model, sae, ids[record['id']], record['positions'])
            metric.update(h, r, active_latents=active)
            start, end = clock.tokens_done, clock.tokens_done + len(h)
            h_file[start:end], r_file[start:end] = h, r
            clock.tokens_done = end
            clock.documents_done += 1
            write_clock(a.out, clock)
        h_file.flush()
        r_file.flush()
        clock.check()
        result = metric.result()
        status = 'PASS' if result['passed'] else 'FAIL'
    except Exception as exc:
        status = 'NO_FIT' if isinstance(exc, NoFit) else 'INCOMPLETE'
        error_type = type(exc).__name__  # Avoid dumping arbitrary paths or exception payloads.
    finally:
        model = sae = None
        torch.cuda.empty_cache()
    clock.status = status
    write_clock(a.out, clock)
    report = {'experiment': 'E35', 'stage': 'gate', 'status': status,
              'error_type': error_type, 'metrics': result,
              'worker_started_epoch': started, 'worker_finished_epoch': time.time(),
              'clock': clock.record(), 'assignment_sha256': sha(a.assignment),
              'request_sha256': sha(HERE / REQUEST_FILENAME),
              'sample_sha256': sha(HERE / 'GATE_SAMPLE.json'),
              'next_stage': 'freeze_latent_rubric' if status == 'PASS' else
                            ('prepare_registered_TopK_training' if status == 'FAIL' else 'report_operational_stop'),
              'decomposition_calls': 0, 'training_steps': 0}
    dump_new(a.out / 'GATE_RESULT.json', report)
    # Preserve the evidence; a failure or partial collection is never a gate failure score.
    files = {p.name: sha(p) for p in a.out.iterdir() if p.is_file()}
    dump_new(a.out / 'OUTPUT_SEAL.json', {'status': status, 'files': files})
    print('E35 gate', status)
    return 0 if status in ('PASS', 'FAIL') else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assignment', 'corpus', 'manifest', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    request_path = HERE / REQUEST_FILENAME
    request = read(request_path)
    verify_sources(request)
    assignment = read(a.assignment)
    verify_rerun_assignment(assignment)
    clock = Clock(assignment, sha(request_path))
    if a.out.resolve() != (ROOT / request['output_path']).resolve():
        raise ValueError('exact once-only gate output location required')
    # Successful preflight or not, a launch consumes this stage's one request.
    claim_run(a.out, sha(a.assignment), sha(request_path))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', WANDB_MODE='disabled')
    write_clock(a.out, clock)

    def stop(signum, frame):
        raise NoFit('external process deadline')

    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, clock.a['deadline_epoch'] - RESERVE - time.time()))
    code = execute(a, clock)
    signal.setitimer(signal.ITIMER_REAL, 0)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
