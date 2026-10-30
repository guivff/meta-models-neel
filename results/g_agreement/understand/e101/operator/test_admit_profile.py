import importlib.util
from pathlib import Path
import pytest
from projects.g_agreement.e101.contract import write, sha

spec = importlib.util.spec_from_file_location('admit_profile', Path(__file__).with_name('admit_profile.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    inp, out = tmp_path / 'inputs', tmp_path / 'outputs'
    inp.mkdir(); out.mkdir()
    write(inp / 'MANIFEST.json', {'stage': 'dev'})
    write(inp / 'INPUT_SEAL.json', {'files': {'MANIFEST.json': sha(inp / 'MANIFEST.json')}})
    digest = sha(inp / 'INPUT_SEAL.json')
    write(out / 'MEASURED_PROFILE.json', dict(status='TIMING_ONLY_NOT_SCIENCE',
          input_sha256=digest, source_sha256='source', gpu_type='H200', margin=1.25,
          setup_warmup_seconds=10, measured_work_seconds=20, staging_seconds=5,
          total_seconds_with_margin=118.75))
    write(out / 'SMOKE_COVERAGE.json', dict(status='PASS', expected_cells=8, covered_cells=8))
    write(out / 'OUTPUT_SEAL.json', dict(experiment='E101', status='TIMING_ONLY', stage='dev',
          input_sha256=digest, source_sha256='source', gpu_type='H200',
          files={p.name: sha(p) for p in out.iterdir()}))
    return inp, out, digest, sha(out / 'OUTPUT_SEAL.json'), 'source'


def test_cap_and_profile_binding(tmp_path):
    packet = module.prepare(*fixture(tmp_path))
    assert packet['assignment_fields']['cap_seconds'] == 119
    assert packet['required_argv'][0] == '--profile'
    assert packet['provider_mutations'] == 0


def test_wrong_source_and_corrupt_profile_rejected(tmp_path):
    args = fixture(tmp_path)
    with pytest.raises(ValueError):
        module.prepare(*args[:-1], 'different-source')
    (args[1] / 'MEASURED_PROFILE.json').write_text('{}')
    with pytest.raises(ValueError):
        module.prepare(*args)
