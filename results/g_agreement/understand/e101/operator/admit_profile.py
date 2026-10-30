"""CPU-only production packet from a sealed E101 timing run; never opens readouts."""
import argparse
import math
from pathlib import Path

from projects.g_agreement.e101.contract import read, sha, verify, write
from projects.g_agreement.e101.timing import admit


def prepare(inputs, outputs, input_sha, output_sha, source_sha):
    verify(inputs, 'INPUT_SEAL.json', input_sha)
    seal = verify(outputs, 'OUTPUT_SEAL.json', output_sha)
    manifest = read(inputs / 'MANIFEST.json')
    if (seal['experiment'] != 'E101' or seal['status'] != 'TIMING_ONLY'
            or seal['input_sha256'] != input_sha or seal['source_sha256'] != source_sha
            or seal['stage'] != manifest['stage']):
        raise ValueError('matching completed timing seal required')
    for member in ('MEASURED_PROFILE.json', 'SMOKE_COVERAGE.json'):
        if member not in seal['files']:
            raise ValueError('timing and smoke must be sealed')
    smoke = read(outputs / 'SMOKE_COVERAGE.json')
    if smoke['status'] != 'PASS' or smoke['expected_cells'] != smoke['covered_cells']:
        raise ValueError('all registered cells must be covered')
    profile_path = outputs / 'MEASURED_PROFILE.json'
    profile = read(profile_path)
    cap = math.ceil(profile['total_seconds_with_margin'])
    assignment = dict(profile_sha256=sha(profile_path), cap_seconds=cap,
                      gpu_type=seal['gpu_type'])
    admit(profile_path, assignment, input_sha, source_sha)
    return dict(experiment='E101', status='PROFILE_VERIFIED_PENDING_FRESH_PROVIDER_ADMISSION',
                input_sha256=input_sha, source_sha256=source_sha,
                timing_output_sha256=output_sha, profile_path=str(profile_path.resolve()),
                assignment_fields=assignment,
                required_argv=['--profile', str(profile_path.resolve())],
                creation_clock_required=True, provider_mutations=0,
                note='Stage the exact profile and substitute its pod path in argv. Fresh budget, guards and custody remain required.')


def main():
    p = argparse.ArgumentParser()
    for name in ('inputs', 'outputs', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('input-sha', 'output-sha', 'source-sha'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    write(a.out, prepare(a.inputs, a.outputs, a.input_sha, a.output_sha, a.source_sha))


if __name__ == '__main__':
    main()
