"""Join original unsteered readouts by sealed original item IDs, CPU only."""
import argparse
from pathlib import Path
from projects.g_agreement.e101.contract import read, sha, verify, write


def bind(targets, target_sha, roots, out):
    target_seal = verify(targets, 'TARGET_SEAL.json', target_sha)
    if 'ORIGINAL_IDS.json' not in target_seal['files']:
        raise ValueError('original IDs must be owner-sealed')
    originals = read(targets / 'ORIGINAL_IDS.json')
    wanted = {(v['bank'], v['source_id']): k for k, v in originals.items()}
    if len(wanted) != 588 or len(originals) != 588:
        raise ValueError('588 unique original test items')
    found, sources = {}, []
    for bank in ('E56', 'E57', 'E59'):
        for path in sorted((roots / bank).glob('shard_*/out/OUTPUT_SEAL.json')):
            digest = sha(path)
            seal = verify(path.parent, path.name, digest)
            if seal['status'] != 'COMPLETE':
                raise ValueError('complete original output required')
            index = len(sources)
            sources.append(dict(seal=str(path.resolve()), sha256=digest))
            for member in sorted(seal['files']):
                if '/jobs/' not in '/' + member or not member.endswith('.json'):
                    continue
                records = read(path.parent / member)
                if not isinstance(records, list):
                    continue
                for n, record in enumerate(records):
                    if not isinstance(record, dict):
                        continue
                    item = wanted.get((bank, record.get('unit_id')))
                    if not item or record.get('kind') != 'text' or 'arm' in record:
                        continue
                    reader = record['reader']
                    if reader not in ('oracle', 'nla'):
                        continue
                    if record['repeat'] != 0 or record['reader_native_layer'] != {'oracle': 44, 'nla': 42}[reader]:
                        raise ValueError('original native single-readout binding')
                    key = item, reader
                    if key in found or not isinstance(record['text'], str):
                        raise ValueError('duplicate or invalid original readout')
                    found[key] = dict(item_id=item, reader=reader, condition='unsteered', text=record['text'],
                                      source_ref=dict(seal_index=index, member=member, keys=[n, 'text']))
    if set(found) != {(item, reader) for item in originals for reader in ('oracle', 'nla')}:
        raise ValueError('1176 original native readouts required')
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'NATIVE_BASELINES.json', [found[k] for k in sorted(found)])
    write(out / 'NATIVE_BASELINE_SEAL.json', dict(experiment='E101', status='NATIVE_COMPLETE_TEXT_PENDING',
          existing_outputs_only=True, source_seals=sources, target_seal_sha256=target_sha,
          files={'NATIVE_BASELINES.json': sha(out / 'NATIVE_BASELINES.json')}))


def main():
    parser = argparse.ArgumentParser()
    for name in ('targets', 'roots', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--target-sha', required=True)
    args = parser.parse_args()
    bind(args.targets, args.target_sha, args.roots, args.out)


if __name__ == '__main__':
    main()
