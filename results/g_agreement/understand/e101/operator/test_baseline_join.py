import hashlib
import importlib.util
from pathlib import Path
import pytest
from projects.g_agreement.e101.contract import write, sha, read

spec = importlib.util.spec_from_file_location('complete_baselines', Path(__file__).with_name('complete_baselines.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def seal(root, name, **meta):
    write(root / name, dict(files={str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}, **meta))
    return sha(root / name)


def test_complete_exact_text_sources_and_incomplete_rejection(tmp_path):
    targets, native, text, inputs = [tmp_path / n for n in ('targets', 'native', 'text', 'inputs')]
    for p in (targets, native, text, inputs): p.mkdir()
    original = {str(i): dict(bank='E56', source_id=str(i)) for i in range(588)}
    write(targets / 'ORIGINAL_IDS.json', original)
    target_sha = seal(targets, 'TARGET_SEAL.json')
    rows = [dict(item_id=str(i), reader=r, condition='unsteered', text='synthetic') for i in range(588) for r in ('oracle', 'nla')]
    write(native / 'NATIVE_BASELINES.json', rows)
    native_sha = seal(native, 'NATIVE_BASELINE_SEAL.json', target_seal_sha256=target_sha, existing_outputs_only=True, source_seals=[])
    items = [dict(id=hashlib.sha256(f'E101_TEXT:E56:{i}'.encode()).hexdigest()) for i in range(336)]
    write(inputs / 'items.json', items)
    write(inputs / 'MANIFEST.json', dict(generic_arm='E81', batch_size=1, max_new_tokens=128))
    input_sha = seal(inputs, 'INPUT_SEAL.json')
    write(text / 'JOB_GRID.json', [dict(kind='text', indices=[i]) for i in range(336)])
    write(text / 'COMPLETED.json', list(range(336)))
    (text / 'jobs').mkdir()
    for i, item in enumerate(items): write(text / f'jobs/{i:06d}.json', [dict(id=item['id'], raw=f'synthetic-{i}')])
    text_sha = seal(text, 'OUTPUT_SEAL.json', experiment='E101_TEXT', status='COMPLETE', input_sha256=input_sha)
    args = (native, native_sha, targets, target_sha, text, text_sha, inputs, input_sha)
    module.complete(*args, tmp_path / 'joined')
    result = read(tmp_path / 'joined/BASELINES.json')
    assert len(result) == 1512 and result[-1]['source_ref']['keys'] == [0, 'raw']
    (text / 'jobs/000335.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        module.complete(*args, tmp_path / 'invalid')
