"""CPU-only E98 port: preserve frozen strings, splits and targets off pod."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import os


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def convert(bank, records, tokenizer):
    """Drop a complete row if any frozen endpoint fails the token-boundary rule."""
    converted, failures = [], []
    for record in records:
        text = record['text']
        enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = enc['input_ids'], enc['offset_mapping']
        valid = bool(ids) and len(ids) == len(offsets) and offsets[-1][1] == len(text)
        valid = valid and tokenizer.decode(ids, skip_special_tokens=False,
                                           clean_up_tokenization_spaces=False) == text
        if not valid:
            failures.append({'bank': bank, 'row': record['feature'],
                             'source_id': record['id'], 'reason': 'prefix_endpoint_not_exact_token_boundary'})
        opaque = hashlib.sha256(('E98\0' + bank + '\0' + record['id']).encode()).hexdigest()[:32]
        public = {'id': opaque, 'ids': ids, 'read_index': len(ids) - 1}
        private = dict(record, id=opaque, source_id=record['id'], source_bank=bank,
                       source_text_sha256=hashlib.sha256(text.encode()).hexdigest(), ids=ids)
        converted.append((public, private))
    dropped = {x['row'] for x in failures}
    kept = [(p, k) for p, k in converted if k['feature'] not in dropped]
    return kept, failures, sorted(dropped)


def run(root, tokenizer_path, out):
    from transformers import AutoTokenizer
    cardpath = root / 'results/g_agreement/understand/e98/ASSET_CARD.json'
    card = json.loads(cardpath.read_text())
    if card['verdict'] != 'PASS':
        raise ValueError('E98 not run (assets)')
    tok = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    public, private, failures, sources, summaries = [], [], [], {}, {}
    for bank in ('E57', 'E59'):
        manifestpath = root / 'results/g_agreement/understand' / bank.lower() / 'FREEZE_MANIFEST.json'
        manifest = json.loads(manifestpath.read_text())
        source = Path(manifest['bank_directory'])
        if sha(source / 'BANK_SEAL.json') != manifest['bank_seal_sha256']:
            raise ValueError('Source bank seal changed')
        seal = json.loads((source / 'BANK_SEAL.json').read_text())
        if sha(source / 'items.PRIVATE.json') != seal['files']['items.PRIVATE.json']:
            raise ValueError('Source items changed')
        records = json.loads((source / 'items.PRIVATE.json').read_text())
        if len(records) != manifest['items']:
            raise ValueError('Source item count mismatch')
        kept, failed, dropped = convert(bank, records, tok)
        public.extend(x[0] for x in kept)
        private.extend(x[1] for x in kept)
        failures.extend(failed)
        sources[bank] = {'manifest_sha256': sha(manifestpath),
                         'bank_seal_sha256': manifest['bank_seal_sha256'],
                         'items_sha256': seal['files']['items.PRIVATE.json']}
        summaries[bank] = {'source_items': len(records), 'kept_items': len(kept), 'dropped_rows': dropped,
                           'rows': dict(Counter(x[1]['feature'] for x in kept)),
                           'splits': dict(Counter(x[1]['split'] for x in kept))}
    if len({r['id'] for r in public}) != len(public):
        raise ValueError('Opaque ID collision')
    if any(set(r) != {'id', 'ids', 'read_index'} for r in public):
        raise ValueError('Public allowlist failure')
    # All labels, values, feature names, original IDs and prompts remain CPU-only.
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    pod = out / 'pod_inputs'
    pod.mkdir()
    write(pod / 'items.json', public)
    write(pod / 'reader_ids.json', [r['id'] for r in private if r['split'] == 'test'])
    write(out / 'KEY.PRIVATE.json', private)
    (out / 'KEY.PRIVATE.json').chmod(0o600)
    write(out / 'DROPPED.PRIVATE.json', failures)
    (out / 'DROPPED.PRIVATE.json').chmod(0o600)
    write(pod / 'INPUT_SEAL.json', {'experiment': 'E98', 'first_output_utc': 'unknown',
           'first_output_evidence': 'Input preparation only; no readout, judgment or analysis output',
           'stage': 'LABEL_FREE_CAPTURE_INPUTS',
          'layer': card['oracle']['layer'], 'hidden_size': card['model']['hidden_size'],
          'model': card['model']['repo'], 'revision': card['model']['revision'],
          'files': {p.name: sha(p) for p in pod.iterdir() if p.is_file()}})
    receipt = {'experiment': 'E98', 'status': 'PORTED_UNCHANGED_FROZEN_TEXT',
               'asset_card_sha256': sha(cardpath), 'source_banks': sources, 'counts': summaries,
               'private_key_sha256': sha(out / 'KEY.PRIVATE.json'),
               'pod_seal_sha256': sha(pod / 'INPUT_SEAL.json'), 'pod_directory': str(pod.resolve()),
               'tokenizer_files': {p.name: sha(p) for p in tokenizer_path.iterdir() if p.is_file()},
               'drop_rule': 'Any invalid endpoint drops the entire row; labels/splits/text never changed.',
               'cpu_only': True, 'gpu_hours': 0}
    write(out / 'PORT_RECEIPT.json', receipt)
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    run(a.root.resolve(), a.tokenizer.resolve(), a.out.resolve())
