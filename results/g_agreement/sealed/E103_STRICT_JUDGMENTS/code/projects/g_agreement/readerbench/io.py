"""Fail-closed, relative-path content seals for the W-core scoring boundary."""
import hashlib
import json
from pathlib import Path
from .scoring import require


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def verify(path, expected):
    path = Path(path)
    require(sha(path) == expected, 'seal hash mismatch')
    seal = read(path)
    require(bool(seal.get('files')), 'empty seal')
    for name, digest in seal['files'].items():
        member = (path.parent/name).resolve()
        require(member.is_relative_to(path.parent.resolve()), 'seal path escapes root')
        require(sha(member) == digest, 'sealed member mismatch: '+name)
    return seal


def load_bundle(path, expected):
    """Payload files are not opened until their hashes and authority receipt verify."""
    path = Path(path)
    seal = verify(path, expected)
    require({'RECEIPT.json', 'DATA.json'} <= set(seal['files']), 'bundle missing sealed inputs')
    receipt = read(path.parent/'RECEIPT.json')
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified') is True,
            'integrator-verified receipt required')
    require(receipt.get('source_seals'), 'source seal lineage required')
    # Local source seals must verify as well: no trust in a progress/status string.
    sources = {}
    for source in receipt['source_seals']:
        sources[source['sha256']] = verify(source['path'], source['sha256'])
    data = read(path.parent/'DATA.json')
    for row in data.get('rows', []):
        source = sources.get(row.get('analysis_seal_sha256'))
        require(source and source.get('status') == 'COMPLETE_ONCE',
                'row must bind a verified complete once-only bank analysis seal')
        for name in ('judge_route_seal_sha256', 'judgment_seal_sha256'):
            if row.get(name):
                require(row[name] in sources, 'judge metadata must bind verified source seals')
    return data, receipt


def seal_output(root, metadata):
    root = Path(root)
    write(root/'RESULT_SEAL.json', dict(metadata, files={
        p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file() and p.name != 'RESULT_SEAL.json'}))


def verify_sources():
    root = Path(__file__).resolve().parents[3]
    manifest = read(root/'results/g_agreement/understand/e64/SCORER_SOURCE_SEAL.json')
    for name, digest in manifest['files'].items():
        member = (root/name).resolve()
        require(member.is_relative_to(root), 'source path escapes root')
        require(sha(member) == digest, 'registered scorer source changed: '+name)
