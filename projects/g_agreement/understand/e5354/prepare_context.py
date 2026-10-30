"""Integrator-only private join; no scientific analysis or guard consumption."""
import argparse
import shutil
from pathlib import Path
from .contract import ROOT, HERE, read, sha, require, dump, seal, verify, sources
from .judgment_adapter import adapt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args();sources()
    b = read(HERE/'CONTEXT_BINDING.json')
    require(sha(a.key) == b['private_key_sha256'], 'integrator private key hash')
    require(sha(b['map_path']) == b['map_sha256'], 'exact map hash')
    d = Path(b['judgment_delivery_path']);verify(d, 'RESULT_SEAL.json', b['judgment_delivery_seal_sha256'])
    keys = read(a.key);codes = read(d/'JUDGMENTS.json')
    km = {x['blind_id']: x for x in keys}
    require(len(keys) == len(km) == len(codes) == 336 and set(km) == {x['id'] for x in codes}, 'full E54 join')
    joined = []
    for code in codes:
        adapt(code)  # validate without changing delivered fields
        k = km[code['id']]
        joined.append(dict(code, blind_id=code['id'], id=k['id'], reader=k['reader'],
                           raw_sha256=k['raw_sha256'], blinded=True))
    a.out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(b['map_path'], a.out/'MAP.json')
    dump(a.out/'JUDGMENTS.json', joined)
    seal(a.out, 'INPUT_SEAL.json', {'issuer': 'integrator',
        'judgment_delivery_seal_sha256': b['judgment_delivery_seal_sha256'],
        'private_key_sha256': b['private_key_sha256'], 'map_sha256': b['map_sha256']})
    print(sha(a.out/'INPUT_SEAL.json'))


if __name__ == '__main__':
    main()
