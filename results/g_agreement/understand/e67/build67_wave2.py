"""Build E67 wave2 once. Private artifacts are written directly to ignored cache."""
import os
import shutil
import subprocess
from datetime import datetime, timezone
from packet67 import *
from sources67_wave2 import HERE, ROOT, Ledger, load_wave2

PRIVATE = ROOT/'cache/g_agreement/understand/e67/wave2/integrator_wave2'
JUDGE = HERE/'judge_wave2'
PUBLIC = HERE/'integrator_wave2'


def main():
    guard = HERE/'BUILD.wave2.RUN_ONCE.json'
    require(not guard.exists() and not JUDGE.exists() and not PRIVATE.exists(), 'Preserve once-only frozen wave2')
    require(subprocess.run(['git', 'check-ignore', '-q', str(PRIVATE/'PAIRING_CONDITION_MAP.PRIVATE.json')], cwd=ROOT).returncode == 0,
            'Private cache must be git-ignored')
    dump(guard, {'experiment': 'E67', 'wave': 2, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'sample_seed': SAMPLE_SEED, 'donor_seed': DONOR_SEED,
        'code_seal_sha256': sha(HERE/'CODE_SEAL.wave2.20261027.json'),
        'rubric_sha256': sha(HERE/'judge_wave1/CLAIMS_RUBRIC.txt'),
        'schema_sha256': sha(HERE/'judge_wave1/CLAIMS_OUTPUT_SCHEMA.json')})
    ledger = Ledger(); pools = load_wave2(ledger)
    packets, mapping, inventory = build_packets(pools)
    JUDGE.mkdir(); PUBLIC.mkdir(); PRIVATE.mkdir(parents=True, mode=0o700)
    os.chmod(PRIVATE, 0o700)
    for name in ('CLAIMS_RUBRIC.txt', 'CLAIMS_OUTPUT_SCHEMA.json'):
        shutil.copyfile(HERE/'judge_wave1'/name, JUDGE/name)
    for i, packet in enumerate(packets, 1):
        with (JUDGE/f'packet_{i:02d}.jsonl').open('x') as f:
            for row in packet: f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    dump(JUDGE/'JUDGE_PACKET_SEAL.json', {'files': {p.name: sha(p) for p in sorted(JUDGE.iterdir())},
        'record_fields': ['id', 'prompt_text', 'readout'], 'independent_packet_contexts_required': True})
    private_objects = {
        'PAIRING_CONDITION_MAP.PRIVATE.json': {'experiment': 'E67', 'wave': 2, 'integrator_only': True,
            'judge_or_pod_access_forbidden': True, 'pairs': mapping,
            'packet_seal_sha256': sha(JUDGE/'JUDGE_PACKET_SEAL.json')},
        'SAMPLE_INVENTORY.PRIVATE.json': {'experiment': 'E67', 'wave': 2, 'strata': inventory,
            'sample_seed': SAMPLE_SEED, 'donor_seed': DONOR_SEED, 'numpy_version': np.__version__,
            'shuffle_streams': 'SeedSequence([20261028,3]) and SeedSequence([20261028,4])',
            'assignment_stream': 'SeedSequence([20261028,1])', 'opaque_id_stream': 'SeedSequence([20261028,2])',
            'no_readout_content_filtering': True, 'opaque_ID_namespace': 'wave2 (never pooled with wave1)'},
        'SOURCE_BINDING.PRIVATE.json': {'experiment': 'E67', 'wave': 2,
            'eligible_once_analysis_seals': ledger.analyses, 'files_sha256': ledger.files,
            'sealed_retained_native_pilots_included_once': True, 'original_analysis_or_model_rerun': False}}
    for name, value in private_objects.items():
        # Restrictive mode at creation; no private data is written to a public path.
        fd = os.open(PRIVATE/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f: f.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n')
    seal = {'experiment': 'E67', 'wave': 2, 'integrator_only': True, 'judge_or_pod_access_forbidden': True,
            'files': {p.name: sha(p) for p in sorted(PRIVATE.iterdir())}}
    dump(PRIVATE/'INTEGRATOR_SEAL.json', seal); dump(PUBLIC/'INTEGRATOR_SEAL.json', seal)
    dump(HERE/'WAVE2_MANIFEST.json', {'experiment': 'E67', 'wave': 2, 'status': 'READY',
        'authority': 'BRIEF_UNDERSTAND section184 and clarification2; user wave2 instruction',
        'CPU_only': True, 'judge_calls': 0, 'registered_analysis_runs': 0, 'sampled_readouts': len(mapping),
        'judge_records': sum(map(len, packets)), 'records_per_packet': list(map(len, packets)),
        'strata': [{k: x[k] for k in ('bank', 'reader', 'eligible_items', 'sampled_items', 'truncation_cohort', 'native_max_new_tokens')} for x in inventory],
        'judge_directory': str(JUDGE.relative_to(ROOT)), 'judge_packet_seal_sha256': sha(JUDGE/'JUDGE_PACKET_SEAL.json'),
        'integrator_only_directory': str(PRIVATE.relative_to(ROOT)), 'integrator_seal_sha256': sha(PUBLIC/'INTEGRATOR_SEAL.json'),
        'opaque_ID_namespace': 'wave2; separate from wave1', 'reporting': 'separate wave2; never pool with wave1'})
    print(json.dumps({'status': 'FROZEN', 'wave': 2, 'sampled_readouts': len(mapping),
        'judge_records': sum(map(len, packets)), 'per_stratum': [(x['bank'], x['reader'], x['sampled_items']) for x in inventory]}))


if __name__ == '__main__': main()
