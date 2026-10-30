"""Authorized post-output E138R correction; original science and guard immutable."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from . import run as original
from .analysis import analyze, validate
from projects.g_agreement.understand.wmech2 import core

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
AUTHORITY = '250_deviation2_37d27a217'
DEFECTIVE = '1f10da833fa1ada3faa54d53236385ec2958f60221be4fa2f1a1bdc0029beaf8'
INPUT = 'a9b55f3b72f257cb4b86aec5441f3be18f5cc57b51a92fe1ee717ab71c467f39'
GUARD = ROOT.parent / 'wt-wmech/cache/g_agreement/understand/e138/correction_r/ANALYSIS_ONCE.json'
RECEIPT = HERE / 'CORRECTION_SOURCE_RECEIPT.json'


def committed():
    receipt = core.read(RECEIPT)
    for name, digest in receipt['files'].items():
        blob = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        core.require(core.sha(ROOT / name) == digest == hashlib.sha256(blob).hexdigest(), 'committed correction dependency: ' + name)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def admission(packet):
    core.require(packet.get('experiment') == 'E138R' and packet.get('correction_authority') == AUTHORITY, 'explicit corrected bank authority')
    core.require(packet.get('defective_analysis_sha256') == DEFECTIVE, 'retain defective first seal')
    core.require(packet.get('corrected_input_sha256') == INPUT, 'reviewed whole-value input')
    for flag in ('whole_values_verified', 'same168_native_readouts_verified', 'R5_actual_sample_pass', 'post_output_correction_disclosed'):
        core.require(packet.get(flag) is True, 'correction binding: ' + flag)
    original.admission(dict(packet, experiment='E138'))
    source = packet['corrected_judgments']
    core.require(source in packet['source_seals'], 'corrected judgments must be a sealed source')
    core.require(source['sha256'] != DEFECTIVE, 'not defective analysis as judgments')
    terminal = core.verify(source['seal'], source['sha256'])
    core.require(terminal.get('input_seal_sha256') == INPUT, 'terminal seal binds reviewed whole-value input')
    review = packet['R5_sample_review_source']
    core.require(core.sha(review['path']) == review['sha256'], 'exact published sample review bytes')
    return packet['source_seals'].index(source)


def check_pointers(rows, judge_index):
    core.require(len(rows) == 84, 'full original84 pointer grid')
    for row in rows:
        for arm in ('donor', 'random'):
            cell = row['arms'][arm]
            core.require(set(cell) == {'e104_role_code'}, 'new arms require lossless original category transport')
            for field in ('code', 'status', 'judgment_id'):
                pointer = cell['e104_role_code'][field]
                core.require(set(pointer) == {'ref'} and pointer['ref']['seal_index'] == judge_index, 'all new judgment fields must reference corrected terminal bank')
    return rows


def main(specfile):
    core.require(ROOT.name == 'wt-wmech2', 'canonical source checkout required')
    commit = committed()
    if GUARD.exists():
        raise FileExistsError('E138R correction consumed; NEVER REPLAY')
    s = core.read(specfile)
    core.require(s.get('reviewer_source_delivered') is True, 'R5 correction source delivery')
    core.require(s.get('correction_authority') == AUTHORITY, 'explicit correction SPEC')
    core.require(original.GUARD.exists(), 'original guard must remain preserved')
    core.verify(s['defective_analysis_seal'], DEFECTIVE)
    packet = core.verify(s['binding_seal'], s['binding_sha256'])
    judge_index = admission(packet)
    pointers = check_pointers(core.read(Path(s['binding_seal']).parent / 'RECORD_POINTERS.json'), judge_index)
    rows = validate(original.expand(pointers, original.resolver(packet['source_seals'])))
    out = Path(s['analysis'])
    core.require(not out.exists(), 'fresh correction output directory')
    GUARD.parent.mkdir(parents=True, exist_ok=True)
    with GUARD.open('x') as f:
        json.dump(dict(spec_sha256=core.sha(specfile), source_receipt=core.sha(RECEIPT), code_commit=commit, authority=AUTHORITY, defective_analysis_sha256=DEFECTIVE), f)
    out.mkdir(parents=True, mode=0o700)
    result = analyze(rows)
    core.write(out / 'RESULTS.json', result)
    core.write(out / 'CORRECTION.json', dict(experiment='E138R', authority=AUTHORITY, defective_analysis_sha256=DEFECTIVE, disclosure='Authorized correction after first result was seen; original MET withdrawn, original artifacts immutable. Numerical analysis unchanged.', corrected_input_sha256=INPUT))
    core.write(out / 'BINDING.PRIVATE.json', s)
    (out / 'BINDING.PRIVATE.json').chmod(0o600)
    core.seal(out, 'ANALYSIS_SEAL.json', experiment='E138R', status='COMPLETE_ONCE', authority=AUTHORITY, defective_analysis_sha256=DEFECTIVE, source_receipt=core.sha(RECEIPT), code_commit=commit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    main(parser.parse_args().spec)
