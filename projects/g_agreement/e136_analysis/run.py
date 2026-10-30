"""Sole CPU invocation after owner-verified normalization; no automatic retry."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from .analysis import CUES, analyze, validate

ROOT = Path(__file__).resolve().parents[3]
GUARD = ROOT.parent / 'wt-wmech/cache/g_agreement/understand/e136/PROBES_BEHAVIOUR_ONCE.json'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def checked(ref):
    p = Path(ref['path'])
    if sha(p) != ref['sha256']:
        raise ValueError('binding hash mismatch')
    return p

def validate_scope(spec):
    if spec.get('deviation') != 2 or spec.get('cues') != list(CUES):
        raise ValueError('explicit deviation 2 and original two-cue scope required')

def main(spec_path):
    receipt = json.loads(Path(__file__).with_name('SOURCE_RECEIPT.json').read_text())
    for name, digest in receipt['files'].items():
        path = 'projects/g_agreement/e136_analysis/' + name
        committed = subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != digest or sha(ROOT / path) != digest:
            raise ValueError('committed tested source mismatch')
    spec = json.loads(Path(spec_path).read_text())
    validate_scope(spec)
    for flag in ('complete_inventory', 'original_source_verified', 'source_order_verified',
                 'privacy_verified', 'route_verified', 'normalization_verified_by_owner', 'terminal_capture'):
        if spec.get(flag) is not True:
            raise ValueError('owner custody required: ' + flag)
    required = ('bank', 'cpu_labels', 'public_inputs', 'capture_seal', 'normalization_receipt', 'measurements')
    for key in required:
        checked(spec[key])
    if spec['bank']['sha256'] != '1083d2e91fbcb9e897727231fcc786b8feef40c94225c2c07452a8fb6f1c4cf9':
        raise ValueError('original frozen bank only')
    if spec['cpu_labels']['sha256'] != '2549533aa0c02a8a65d2f55a645a28f96e1a0b8a72de47b9493f419c201021e1':
        raise ValueError('original CPU label seal only')
    if GUARD.exists():
        raise FileExistsError('consumed guard; NEVER REPLAY')
    rows = json.loads(checked(spec['measurements']).read_text())
    validate(rows)
    out = Path(spec['output_dir'])
    if out.exists():
        raise FileExistsError('fresh output directory required')
    GUARD.parent.mkdir(parents=True, exist_ok=True)
    with GUARD.open('x') as f:
        json.dump({'spec_sha256':sha(spec_path), 'source_receipt_sha256':sha(Path(__file__).with_name('SOURCE_RECEIPT.json'))}, f)
    out.mkdir(parents=True)
    result = analyze(rows)
    # Fitted coefficients stay private. Publish aggregates only after scan/review.
    private = {c: {k: result['cues'][c]['probe'].pop(k) for k in ('coefficients','intercept') if k in result['cues'][c]['probe']} for c in result['cues']}
    for name, obj in [('RESULTS.json', result), ('PROBES.PRIVATE.json', private), ('BINDING.PRIVATE.json', spec)]:
        (out/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')
    (out/'ANALYSIS_SEAL.json').write_text(json.dumps({'members':{p.name:sha(p) for p in sorted(out.iterdir())}}, indent=2)+'\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    main(parser.parse_args().spec)
