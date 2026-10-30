"""Verify original Git object identities and every commit-to-source-path binding."""
import base64
import hashlib
import json
from pathlib import Path


def verify(proof, *, external_bytes=False):
    objects = {}
    for oid, obj in proof['objects'].items():
        kind = obj['type']
        raw = base64.b64decode(obj['base64'], validate=True)
        if hashlib.sha1(f'{kind} {len(raw)}\0'.encode() + raw).hexdigest() != oid:
            raise ValueError('Git object hash mismatch')
        objects[oid] = (kind, raw)
    for row in proof['bindings']:
        kind, commit = objects[row['commit']]
        if kind != 'commit':
            raise ValueError('commit required')
        oid = next(x.split()[1].decode() for x in commit.splitlines() if x.startswith(b'tree '))
        trees = []
        for component in row['path'].split('/'):
            kind, raw = objects[oid]
            if kind != 'tree':
                raise ValueError('directory tree required')
            trees.append(oid)
            entries = {}
            while raw:
                header, tail = raw.split(b'\0', 1)
                _, name = header.split(b' ', 1)
                entries[name.decode()] = tail[:20].hex()
                raw = tail[20:]
            if component not in entries:
                raise ValueError('path component absent from original tree')
            oid = entries[component]
        if trees != row['tree_path'] or oid != row['blob_sha1']:
            raise ValueError('original tree/path/blob mismatch')
        if row['blob_in_proof']:
            kind, blob = objects[oid]
            if kind != 'blob':
                raise ValueError('source blob required')
        elif external_bytes:
            blob = Path(row['canonical_readonly_source']).read_bytes()
            if hashlib.sha1(f'blob {len(blob)}\0'.encode() + blob).hexdigest() != oid:
                raise ValueError('external original worker Git hash mismatch')
        else:
            continue
        if hashlib.sha256(blob).hexdigest() != row['sha256']:
            raise ValueError('source byte SHA256 mismatch')
    return len(objects), len(proof['bindings'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('proof', type=Path)
    parser.add_argument('--external-bytes', action='store_true')
    args = parser.parse_args()
    print(verify(json.loads(args.proof.read_text()), external_bytes=args.external_bytes))
