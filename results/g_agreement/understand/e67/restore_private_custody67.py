"""Restore ignored CPU-only links for the unchanged frozen E67 verifier. No git mutation."""
import hashlib,json,os
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CACHE=ROOT/'cache/g_agreement/understand/e67/wave1/integrator_wave1'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    seal=json.loads((HERE/'integrator_wave1/INTEGRATOR_SEAL.json').read_text())
    if set(seal['files'])!={'PAIRING_CONDITION_MAP.PRIVATE.json','SAMPLE_INVENTORY.PRIVATE.json','SOURCE_BINDING.PRIVATE.json'}:
        raise ValueError('Unexpected frozen private-file inventory')
    if '*.PRIVATE.json' not in (ROOT/'.gitignore').read_text().splitlines():
        raise ValueError('Install private filename ignore rule before restoring local links')
    for name,expected in seal['files'].items():
        target=CACHE/name
        if not target.is_file() or digest(target)!=expected:raise ValueError('Cached private custody file missing or checksum mismatch')
    for name,expected in seal['files'].items():
        link=HERE/'integrator_wave1'/name;target=CACHE/name
        if link.exists() or link.is_symlink():
            if not link.is_file() or digest(link)!=expected:raise ValueError('Existing local custody alias differs; preserve and inspect')
            if link.is_symlink() and link.resolve()==target.resolve():continue
            link.unlink()
        link.symlink_to(os.path.relpath(target,link.parent))
    print('Three private files verified in ignored cache; ignored CPU-only links restored. No git files staged.')


if __name__=='__main__':main()
