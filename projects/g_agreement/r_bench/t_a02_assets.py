"""Hash existing pinned A02 assets. Never download or substitute missing weights."""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from projects.g_agreement.core import config as C

TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
ADAPTER_SHAS = {'sft': '572bab4c8edcfeff21603e5a02c3e9d18772dffa97b0f3fd40cd34fd729a44fb',
                'sft_dpo': '19bbf00f5a9ed387bb80ff15fcb9704fad17f2d03621d0998f4524579622c7ee'}


def cached(repo: str, revision: str, filename: str) -> Path:
    from huggingface_hub import try_to_load_from_cache
    p = try_to_load_from_cache(repo, filename, revision=revision)
    if not isinstance(p, str) or not Path(p).is_file():
        raise FileNotFoundError(f'missing pinned asset: {repo}@{revision}/{filename}')
    return Path(p)


def check_file(spec: tuple[Path, str]) -> dict:
    p, expected = spec
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    actual = h.hexdigest()
    return {'path': str(p.resolve()), 'sha256': actual, 'expected_sha256': expected,
            'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns, 'passed': actual == expected}


def build_manifest() -> dict:
    started = time.time()
    manifest = json.loads((C.RESULTS_DIR / 'r/t_a02/target_shards.json').read_text())
    if manifest['revision'] != C.TARGET_MODEL_SHA:
        raise ValueError('checkpoint manifest revision mismatch')
    specs = [(cached(C.TARGET_MODEL_ID, C.TARGET_MODEL_SHA, s['path']), s['sha256'])
             for s in manifest['shards']]
    tok = cached(C.TARGET_MODEL_ID, C.TARGET_MODEL_SHA, 'tokenizer.json')
    oracle = cached(C.OLENS_REPO, C.OLENS_SHA, C.OLENS_SUBFOLDER + '/adapter_model.safetensors')
    jlens = cached(C.JLENS_REPO, C.JLENS_SHA, C.JLENS_FILE)
    specs.extend([(tok, TOKENIZER_SHA), (oracle, C.OLENS_ADAPTER_SHA256), (jlens, C.JLENS_FILE_SHA256)])
    specs.extend((C.CACHE_DIR / 'r/planted_facts' / recipe / 'adapter/adapter_model.safetensors', sha)
                 for recipe, sha in ADAPTER_SHAS.items())
    # Two readers keep hashing bounded on a shared network volume.
    with ThreadPoolExecutor(max_workers=2) as executor:
        files = list(executor.map(check_file, specs))
    result = {'passed': all(f['passed'] for f in files), 'target_revision': C.TARGET_MODEL_SHA,
              'target_id': C.TARGET_MODEL_ID, 'files': files, 'verified_at_unix': time.time(),
              'verification_seconds': time.time() - started,
              'oracle_adapter_dir': str(oracle.parent), 'jlens_path': str(jlens),
              'tokenizer_dir': str(tok.parent), 'target_snapshot_dir': str(specs[0][0].parent)}
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=C.CACHE_DIR / 'r/t_a02/assets_verification.json')
    args = ap.parse_args()
    try:
        result = build_manifest()
    except (FileNotFoundError, ValueError, OSError) as exc:
        result = {'passed': False, 'status': 'NOT RUN', 'reason': str(exc), 'target_revision': C.TARGET_MODEL_SHA}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'out': str(args.out),
                      'files': len(result.get('files', [])), 'reason': result.get('reason')}))
    return 0 if result['passed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
