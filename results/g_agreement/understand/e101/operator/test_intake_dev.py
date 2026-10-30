import importlib.util
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e101.contract import write, sha

spec = importlib.util.spec_from_file_location('intake_dev', Path(__file__).with_name('intake_dev.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_row_doses_use84_and_independent_blocks(tmp_path):
    inp, out = tmp_path / 'inputs', tmp_path / 'out'
    inp.mkdir(); out.mkdir(); (out / 'jobs').mkdir()
    xs, records = [], []
    key = {str(i): dict(split='dev', row='format_plan', contrast_target_sign=1) for i in range(84)}
    for block, threshold in ((42, 2), (44, 1)):
        for alpha in (.5, 1., 2., 4.):
            for i in range(84):
                identity = f'{block}:{alpha}:{i}'
                xs.append(dict(id=identity, base_id=str(i), row='format_plan', block=block,
                               alpha=alpha, condition='steered', vector_index=len(xs), ids=[1],
                               read_index=0, candidate_ids=[[[1], [2]]], norm_ratio=1.))
                score = 1. if i < (59 if alpha >= threshold else 58) else -1.
                records.append(dict(id=identity, pair_logprobs=[[score, 0.]]))
    write(inp / 'items.json', xs)
    np.save(inp / 'vectors.npy', np.ones((672, 5120), dtype=np.float32))
    write(inp / 'MANIFEST.json', dict(stage='dev', dev_count=84, dose_policy='independent_blocks',
                                    scoring_mode='continuation', ruling_commit='synthetic'))
    write(inp / 'INPUT_SEAL.json', dict(files={p.name: sha(p) for p in inp.iterdir()}))
    write(out / 'JOB_GRID.json', [dict(kind='logits', indices=list(range(672)))])
    write(out / 'COMPLETED.json', [0]); write(out / 'jobs/000000.json', records)
    write(out / 'OUTPUT_SEAL.json', dict(status='COMPLETE', stage='dev', input_sha256=sha(inp / 'INPUT_SEAL.json'),
          files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}))
    shard = dict(input_root=str(inp), output_root=str(out), input_sha256=sha(inp / 'INPUT_SEAL.json'), output_sha256=sha(out / 'OUTPUT_SEAL.json'))
    doses = module.select_row(shard, key)['selected_doses']
    assert doses['format_plan:42']['alpha'] == 2 and doses['format_plan:44']['alpha'] == 1
    (out / 'jobs/000000.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        module.select_row(shard, key)


def test_completed_row_cannot_be_replaced(tmp_path):
    from projects.g_agreement.e101.contract import ROWS
    binding = tmp_path / 'binding.json'
    write(binding, dict(stage='dev', packages=[dict(row=r) for r in sorted(ROWS)]))
    original = tmp_path / 'dev/format_plan/out'
    original.mkdir(parents=True)
    write(original / 'OUTPUT_SEAL.json', dict(status='COMPLETE'))
    with pytest.raises(ValueError, match='cannot replace'):
        module.inspect(binding, tmp_path / 'dev', 'source', {'format_plan': tmp_path / 'replacement'})
