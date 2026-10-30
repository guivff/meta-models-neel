"""CPU join of sealed native baselines and the completed exact E101_TEXT run."""
import argparse
import hashlib
from pathlib import Path
from projects.g_agreement.e101.contract import read, sha, verify, write


def complete(native, native_sha, targets, target_sha, text, text_sha, inputs, input_sha, out):
    ns = verify(native, 'NATIVE_BASELINE_SEAL.json', native_sha)
    verify(targets, 'TARGET_SEAL.json', target_sha)
    ts = verify(text, 'OUTPUT_SEAL.json', text_sha)
    verify(inputs, 'INPUT_SEAL.json', input_sha)
    if (ns['target_seal_sha256'] != target_sha or not ns['existing_outputs_only']
            or ts['experiment'] != 'E101_TEXT' or ts['status'] != 'COMPLETE'
            or ts['input_sha256'] != input_sha):
        raise ValueError('matching completed text and native seals required')
    manifest = read(inputs / 'MANIFEST.json')
    if manifest['generic_arm'] != 'E81' or manifest['batch_size'] != 1 or manifest['max_new_tokens'] != 128:
        raise ValueError('frozen generic serial128 baseline')
    items = read(inputs / 'items.json')
    original = read(targets / 'ORIGINAL_IDS.json')
    mapping = {hashlib.sha256(f'E101_TEXT:{v["bank"]}:{v["source_id"]}'.encode()).hexdigest(): k
               for k, v in original.items()}
    if len(items) != 336 or any(x['id'] not in mapping for x in items):
        raise ValueError('exact original text item mapping')
    jobs = read(text / 'JOB_GRID.json')
    if len(jobs) != 336 or sorted(read(text / 'COMPLETED.json')) != list(range(336)):
        raise ValueError('all text jobs complete')
    rows = read(native / 'NATIVE_BASELINES.json')
    sources = list(ns['source_seals'])
    for entry in sources:
        p = Path(entry['seal']); verify(p.parent, p.name, entry['sha256'])
    index = len(sources)
    sources.append(dict(seal=str((text / 'OUTPUT_SEAL.json').resolve()), sha256=text_sha))
    seen = set()
    for i, job in enumerate(jobs):
        if job != dict(kind='text', indices=[i]):
            raise ValueError('serial original text order')
        member = f'jobs/{i:06d}.json'
        if member not in ts['files']:
            raise ValueError('unsealed text record')
        record = read(text / member)
        if len(record) != 1 or record[0]['id'] != items[i]['id'] or record[0]['id'] in seen:
            raise ValueError('unique original text record')
        seen.add(record[0]['id'])
        rows.append(dict(item_id=mapping[record[0]['id']], reader='text', condition='text',
                         text=record[0]['raw'], source_ref=dict(seal_index=index, member=member, keys=[0, 'raw'])))
    if len(rows) != 1512 or len({(x['item_id'], x['reader']) for x in rows}) != 1512:
        raise ValueError('complete unique baseline grid')
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'BASELINES.json', rows)
    write(out / 'BASELINE_SEAL.json', dict(experiment='E101', existing_outputs_only=True,
          source_seals=sources, files={'BASELINES.json': sha(out / 'BASELINES.json')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('native', 'targets', 'text', 'inputs', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('native-sha', 'target-sha', 'text-sha', 'input-sha'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    complete(a.native, a.native_sha, a.targets, a.target_sha, a.text, a.text_sha, a.inputs, a.input_sha, a.out)
