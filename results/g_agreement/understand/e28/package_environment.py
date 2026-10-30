"""Package the pre-authorized E28 backward environment and parity gate only."""
from __future__ import annotations
import gzip
import io
from pathlib import Path
import tarfile
import contract as C

PREFIX = 'results/g_agreement/understand/e28/'
ORIGINAL_PLAN = '73d5eddfc32692e3f6b7fc1428be681627ae0e9d9da5d8d4cf0af0f32f05c6eb'
ORIGINAL_INPUT = '13bbcc29c1ffc69e2b350bc46b05b1b9c9aeb5e5a7c47bbbd47195daba3a6c02'


def archive(path, files):
    with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as z:
        with tarfile.open(fileobj=z, mode='w') as tar:
            for name, source in sorted(files.items()):
                data = source.read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                tar.addfile(info, io.BytesIO(data))
    with tarfile.open(path) as tar:
        import hashlib
        assert set(tar.getnames()) == set(files)
        for member in tar.getmembers():
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == C.sha(files[member.name])


def main():
    cache = C.ROOT / 'cache/g_agreement/understand'
    original = C.HERE / 'cache/input-v1'
    parity = cache / 'e28-parity-v1'
    C.verify(original)
    C.verify(parity)
    assert C.sha(C.HERE / 'PLAN.json') == ORIGINAL_PLAN
    assert C.sha(original / 'INPUT_SEAL.json') == ORIGINAL_INPUT
    validation = C.read(C.HERE / 'CPU_VALIDATION_ENVIRONMENT.json')
    review = C.read(C.HERE / 'ENVIRONMENT_REVIEW_2026-10-25.json')
    assert validation['status'] == review['status'] == 'PASS'
    names = set(C.read(C.HERE / 'SOURCE_MANIFEST.json')['files'])
    names |= {str(p.relative_to(C.ROOT)) for p in C.HERE.glob('*.py')}
    names |= {PREFIX + n for n in ('OVERLAY_REQUIREMENTS.txt', 'TRAINING_ENVIRONMENT_2026-10-25.md',
               'HANDOFF_ENVIRONMENT_2026-10-25.md', 'PARITY_PREPARATION_2026-10-25.json',
               'OWNER_READING_2026-10-25.md', 'PRIOR_ATTEMPT_ACCOUNTING_2026-10-25.json')}
    pins = {n: C.sha(C.ROOT / n) for n in sorted(names)}
    C.dump(C.HERE / 'SOURCE_MANIFEST.json', {'files': pins})
    source_archive = cache / 'e28-environment-source-v2.tar.gz'
    source_files = {n: C.ROOT / n for n in names}
    source_files[PREFIX + 'SOURCE_MANIFEST.json'] = C.HERE / 'SOURCE_MANIFEST.json'
    archive(source_archive, source_files)
    parity_archive = cache / 'e28-parity-v1.tar.gz'
    archive(parity_archive, {n: parity / n for n in [*C.read(parity / 'INPUT_SEAL.json')['files'], 'INPUT_SEAL.json']})
    input_archive = C.HERE / 'cache/e28-input-v1.tar.gz'
    with tarfile.open(input_archive) as tar:
        import hashlib
        expected = C.read(original / 'INPUT_SEAL.json')['files']
        assert set(tar.getnames()) == set(expected) | {'INPUT_SEAL.json'}
        for n, h in expected.items():
            assert hashlib.sha256(tar.extractfile(n).read()).hexdigest() == h
    for slot in range(2):
        path = C.HERE / f'ASSIGNMENT_SLOT{slot}.template.json'
        a = C.read(path)
        a.update(source_manifest_sha256=C.sha(C.HERE / 'SOURCE_MANIFEST.json'),
                 parity_input_seal_sha256=C.sha(parity / 'INPUT_SEAL.json'),
                 training_environment_sha256=None, source_published=False,
                 allocated_gpu_seconds=8318.5, previous_gpu_seconds=1363,
                 source_commit='INTEGRATOR_SET_AFTER_PUBLICATION', external_hardstop_verified=False,
                 provider_created_epoch=None, deadline_epoch=None)
        assert 2 * a['allocated_gpu_seconds'] + a['previous_gpu_seconds'] == 18000
        C.dump(path, a)
    request = C.read(C.HERE / 'LAUNCH_REQUEST.json')
    request.update(schema='E28_ENVIRONMENT_LAUNCH_REQUEST_v2', date='2026-10-25',
        status='CPU_REVIEWED_OVERLAY_AND_PRETRAIN_PARITY_GATE_REQUIRED',
        environment_authority='Direct Guiv instructions 2026-10-25; pre-authorized under §136',
        environment_ready_by='2026-10-26T12:00:00+01:00',
        missing_environment_after_deadline='NOT_RUN_ENVIRONMENT',
        worker_worktree_local='.',
        source_manifest_sha256=C.sha(C.HERE / 'SOURCE_MANIFEST.json'),
        source_archive_local=str(source_archive.relative_to(C.ROOT)), source_archive_sha256=C.sha(source_archive),
        input_archive_local=str(input_archive.relative_to(C.ROOT)), input_archive_sha256=C.sha(input_archive),
        parity_archive_local=str(parity_archive.relative_to(C.ROOT)), parity_archive_sha256=C.sha(parity_archive),
        parity_input_seal_sha256=C.sha(parity / 'INPUT_SEAL.json'),
        unchanged_scientific_plan_sha256=ORIGINAL_PLAN, unchanged_scientific_input_seal_sha256=ORIGINAL_INPUT,
        environment_prepare_command='/weights/venv-kernels/bin/python results/g_agreement/understand/e28/training_environment.py prepare --base-python /weights/venv-kernels/bin/python --overlay /tmp/e28-training-POD_ID --manifest cache/g_agreement/understand/e28-POD_ID/TRAINING_ENVIRONMENT.json',
        environment='Fresh pod-local overlay on /weights/venv-kernels; only exact wheel-hashed Triton3.7.1 added; inherited package versions and bytes frozen before forwards',
        optimizer='Inherited torch.optim.AdamW, pinned by torch byte/version manifest; exact existing PLAN hyperparameters',
        pretraining_gate={'rows':['prose_sentiment','prose_paren','python_string'], 'n_per_row':84,
                         'metric':'untrained merged RL lens row AUROC vs sealed W1, both frozen paired log-odds averaged',
                         'max_abs_auroc_delta':.03, 'timing':'before ANY optimizer step including warmup',
                         'failure':'PARITY_FAILED_STOP; no retry or retuning', 'labels':'252 fixed parity labels only in separate sealed gate archive'},
        evidence=validation, environment_review=review,
        operations='Integrator publishes and launches after E33; E37 build already committed. Global12pod ceiling and180s spacing. Original14runs and<=5GPUh unchanged. All environment/parity/warmup time remains inside provider allocation.',
        readiness_limits=['CPU training test passed; CUDA backward remains unverified until first parity-gated warm training step',
                          'Each pod must freeze actual inherited environment and pass parity before any optimizer step',
                          'Real backward readiness must be recorded by Monday26Oct12:00CET',
                          'Both warmed full-grid forecasts must still fit unchanged total18000GPU-seconds'])
    request['worker_command'] = ('/tmp/e28-training-POD_ID/bin/python results/g_agreement/understand/e28/worker.py run '
        '--assignment ASSIGNMENT.json --mapping results/g_agreement/understand/e28/LORA_TARGETS.json '
        '--input INPUT_CACHE --assets VERIFIED_ASSETS.json --out NEW_OUTPUT_CACHE --admission ADMISSION.json '
        '--parity-inputs PARITY_INPUTS --environment-manifest TRAINING_ENVIRONMENT.json')
    assert request['budget']['total_provider_gpu_seconds'] == 18000
    request['budget'].update(previous_booked_gpu_seconds=1363, default_per_pod_provider_seconds=8318.5,
                             remaining_new_provider_gpu_seconds=16637,
                             prior_accounting_file=PREFIX+'PRIOR_ATTEMPT_ACCOUNTING_2026-10-25.json')
    assert request['scope']['runs'] == 14
    C.dump(C.HERE / 'LAUNCH_REQUEST.json', request)
    print('E28 environment packet sealed; original PLAN, input bank, all arms and cap unchanged')


if __name__ == '__main__':
    main()
