"""CPU-only split of the frozen bank into blind pod inputs and a custody join."""
import shutil
from common58 import *
from cpu_join58 import split_bank
from worker58 import validate_bank, validate_pod_directory


def replace_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    dump(temporary, value)
    temporary.replace(path)


def main():
    source_verify()
    require(not (CACHE / 'WORKER.RUN_ONCE.json').exists()
            and not (HERE / 'ANALYSIS.RUN_ONCE.json').exists(), 'Cannot repartition after invocation')
    original = CACHE / 'inputs'
    verify(original, 'INPUT_SEAL.json')
    bank = read(original / 'BANK.json')
    pod, join = split_bank(bank)
    validate_bank(pod)
    require(sha(original / 'J384.npy') == J_SHA, 'Exact frozen J basis required')
    inp, cpu = CACHE / 'pod_inputs_v2', CACHE / 'cpu_only_v2'
    require(not inp.exists() and not cpu.exists(), 'Preserve existing partition; do not overwrite')
    inp.mkdir(); cpu.mkdir()
    dump(inp / 'BANK.json', pod)
    shutil.copyfile(original / 'J384.npy', inp / 'J384.npy')
    dump(inp / 'INPUT_SEAL.json', {'experiment': 'E58b', 'schema': 'E58B_POD_INPUT_SEAL_V2',
         'files': {name: sha(inp / name) for name in ('BANK.json', 'J384.npy')}})
    validate_pod_directory(inp)
    join.update(pod_input_seal_sha256=sha(inp / 'INPUT_SEAL.json'),
                original_input_seal_sha256=sha(original / 'INPUT_SEAL.json'))
    dump(cpu / 'CPU_JOIN.json', join)
    dump(cpu / 'CPU_SEAL.json', {'experiment': 'E58b', 'schema': 'E58B_CPU_ONLY_CUSTODY_V2',
         'cpu_only': True, 'pod_staging_forbidden': True,
         'files': {'CPU_JOIN.json': sha(cpu / 'CPU_JOIN.json')}})
    dump(HERE / 'CPU_CUSTODY_BINDING.20261027.json', {'experiment': 'E58b', 'version': 'BLIND_V2',
         'directory': str(cpu.relative_to(ROOT)), 'cpu_only': True, 'pod_staging_forbidden': True,
         'cpu_seal_sha256': sha(cpu / 'CPU_SEAL.json'), 'cpu_join_sha256': sha(cpu / 'CPU_JOIN.json'),
         'pod_input_seal_sha256': sha(inp / 'INPUT_SEAL.json'),
         'original_input_seal_sha256': sha(original / 'INPUT_SEAL.json'),
         'integrator_receipt': str((cpu / 'INTEGRATOR_CUSTODY.json').relative_to(ROOT))})
    replace_json(HERE / 'INPUT_BINDING.20261027.json', {'experiment': 'E58b', 'version': 'BLIND_V2',
         'pod_input_directory': str(inp.relative_to(ROOT)), 'input_seal_sha256': sha(inp / 'INPUT_SEAL.json'),
         'pod_row_keys': [r['key'] for r in pod['rows']], 'rows': len(pod['rows']),
         'dev_items': sum(len(r['dev']) for r in pod['rows']),
         'test_items': sum(len(r['test']) for r in pod['rows']), 'pca_population': pod['pca_population'],
         'cpu_custody_binding_sha256': sha(HERE / 'CPU_CUSTODY_BINDING.20261027.json'),
         'scoring_invocations': 0})
    with (HERE / 'HANDOFF.md').open('a') as f:
        f.write('\n- 2026-10-27 — Blind-v2 partition complete: pod has token IDs, opaque IDs and candidate tokens only; labels/original IDs/donors stay in cpu_only_v2/CPU_JOIN.json. Legacy full bank/archive retained locally as superseded history. No model or registered analysis invoked.\n')
    print('Blind pod inputs and CPU-only join sealed; request re-seal and commit remain required.')


if __name__ == '__main__':
    main()
