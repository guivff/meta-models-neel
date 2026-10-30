"""Pre-score input binding and forced request hashes; owner commits afterwards."""
from common58 import *
from worker58 import validate_bank, validate_pod_directory


def replace_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    dump(temporary, value)
    temporary.replace(path)


def main():
    source_verify()
    require(not (CACHE / 'WORKER.rerun1.RUN_ONCE.json').exists()
            and not (HERE / 'ANALYSIS.RUN_ONCE.json').exists(), 'Cannot rebind after invocation')
    binding = read(HERE / 'INPUT_BINDING.20261027.json')
    inp = CACHE / 'pod_inputs_v2'
    require(binding['input_seal_sha256'] == sha(inp / 'INPUT_SEAL.json'), 'Binding/input seal mismatch')
    validate_pod_directory(inp)
    bank = read(inp / 'BANK.json'); rows = validate_bank(bank)
    require(binding['pod_row_keys'] == [r['key'] for r in rows], 'Binding row scope mismatch')
    cpu = read(HERE / 'CPU_CUSTODY_BINDING.20261027.json')
    require(cpu['pod_input_seal_sha256'] == binding['input_seal_sha256'], 'CPU/pod binding mismatch')
    request = read(HERE / 'LAUNCH_REQUEST.json')
    request.update(status='READY', input_seal_sha256=binding['input_seal_sha256'],
                   input_binding_sha256=sha(HERE / 'INPUT_BINDING.20261027.json'),
                   source_seal_sha256=sha(HERE / 'POD_SOURCE_SEAL.20261027.json'),
                   analysis_source_seal_sha256=sha(HERE / 'SOURCE_SEAL.20261027.json'),
                   cpu_custody_binding_sha256=sha(HERE / 'CPU_CUSTODY_BINDING.20261027.json'))
    replace_json(HERE / 'LAUNCH_REQUEST.json', request)
    command_seal = read(HERE / 'COMMAND_SEAL.20261027.json')
    command_seal['files'] = {name: sha(ROOT / name) for name in command_seal['files']}
    replace_json(HERE / 'COMMAND_SEAL.20261027.json', command_seal)
    with (HERE / 'HANDOFF.md').open('a') as f:
        f.write('\n- 2026-10-27 — Verified input binding promoted request to READY before any invocation; '
                'request SHA256 `' + sha(HERE / 'LAUNCH_REQUEST.json') + '`. '
                'Owner commit/scan and Integrator publication/launch remain required.\n')
    print('Request and forced command hashes refreshed. Commit and secret-scan before Integrator launch.')


if __name__ == '__main__':
    main()
