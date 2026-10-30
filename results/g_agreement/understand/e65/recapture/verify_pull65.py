"""Once-only CPU integrity verification; downstream C/probe analysis belongs to W-lens."""
import time
import numpy as np
from common65 import *


def validate_capture(final, bank, positions):
    offsets = read(final / 'OFFSETS.json')
    require(offsets['experiment'] == 'E65' and offsets['schema'] == 'E65_CAPTURE_OFFSETS_V1'
            and offsets['dtype'] == 'float16' and offsets['shape'] == [positions, DIM]
            and offsets['block'] == BLOCK, 'Capture format/block mismatch')
    expected = [{'key': row['key'], 'items': [{'id': x['id'], 'prompt_tokens': len(x['ids']), 'start': x['start'],
                 'stop': x['stop'], 'offset': x['offset'], 'count': x['stop']-x['start']} for x in row['items']]}
                 for row in bank['rows']]
    require(offsets['rows'] == expected, 'Capture item order/token offsets differ from sealed selection')
    array = np.load(final / 'ACTIVATIONS.fp16.npy', mmap_mode='r', allow_pickle=False)
    require(array.dtype == np.float16 and array.shape == (positions, DIM), 'Raw fp16 array shape mismatch')
    for start in range(0, positions, 8192):
        require(np.isfinite(array[start:start+8192]).all(), 'Nonfinite capture')
    return offsets


def main():
    cpu_seal = read(HERE / 'CPU_SOURCE_SEAL.json'); verify_files(ROOT, cpu_seal)
    request = read(HERE / 'LAUNCH_REQUEST.json')
    require(request['status'] == 'READY' and request['CPU_source_seal_sha256'] == sha(HERE / 'CPU_SOURCE_SEAL.json'), 'Exact READY CPU source required')
    verify_files(ROOT, read(HERE / 'COMMAND_SEAL.json'))
    dump(HERE / 'VERIFY.RUN_ONCE.json', {'started_epoch': time.time(), 'experiment': 'E65', 'request_sha256': sha(HERE / 'LAUNCH_REQUEST.json')})
    bank, items, positions = load_inputs()
    pull = CACHE / 'verified-pull'; final = pull / 'final'; receipt = read(pull / 'VERIFIED_PULL.json')
    require(receipt.get('issuer') == 'integrator' and receipt.get('experiment') == 'E65'
            and receipt.get('verified_complete') is True and receipt['output_seal_sha256'] == sha(final / 'OUTPUT_SEAL.json'),
            'Integrator verified complete pull required')
    output = read(final / 'OUTPUT_SEAL.json'); verify_files(final, output)
    require(output.get('status') == 'COMPLETE' and output.get('experiment') == 'E65', 'Incomplete capture')
    custody = read(final / 'CUSTODY.json'); a = custody['assignment']; stopped = receipt['provider_stopped_epoch']
    require(custody['request_sha256'] == a['request_sha256'] == sha(HERE / 'LAUNCH_REQUEST.json')
            and custody['source_seal_sha256'] == a['source_seal_sha256'] == request['source_seal_sha256']
            and custody['input_seal_sha256'] == a['input_seal_sha256'] == request['input_seal_sha256'], 'Custody pin mismatch')
    require(a.get('issuer') == 'integrator' and a.get('experiment') == 'E65' and a.get('gpu_count') == 1
            and a.get('pod_id') == receipt.get('pod_id') and a.get('previous_gpu_seconds') == 0
            and all(a.get(k) is True for k in ('source_pushed', 'external_hardstop_verified', 'hold_renewer_verified', 'separate_pod_verified')),
            'Own-pod custody mismatch')
    require(0 < a['allocated_gpu_seconds'] <= CAP
            and a['provider_created_epoch'] <= custody['completed_epoch'] <= stopped <= a['deadline_epoch']
            <= min(a['provider_created_epoch']+a['allocated_gpu_seconds'], STOP), 'Provider cap/programme violation')
    forecast = read(final / 'FORECAST.json')
    require(forecast['status'] == 'FIT' and forecast['all_items'] == len(items) and forecast['all_positions'] == positions
            and forecast['admitted_epoch'] + 1.5*forecast['remaining_forecast_seconds'] + 360 < forecast['production_deadline_epoch']
            and forecast['production_deadline_epoch'] == a['deadline_epoch']-RESERVE, 'Full-scope admission missing')
    validate_capture(final, bank, positions)
    identity = read(HERE / 'CPU_IDENTITY_ARCHIVE.json')
    folder = CACHE / 'cpu_only'; require(sha(folder / 'CPU_MAP_SEAL.json') == identity['cpu_map_seal_sha256'], 'CPU map seal mismatch')
    verify_files(folder, read(folder / 'CPU_MAP_SEAL.json'))
    require(sha(folder / 'IDENTITY_MAP.json') == identity['identity_map_sha256'], 'CPU identity map mismatch')
    mapping = read(folder / 'IDENTITY_MAP.json')
    require(mapping['pod_input_seal_sha256'] == request['input_seal_sha256'], 'CPU map targets another pod input')
    require([x['pod_row'] for x in mapping['rows']] == [x['key'] for x in bank['rows']]
            and [[x['pod_id'] for x in row['items']] for row in mapping['rows']]
            == [[x['id'] for x in row['items']] for row in bank['rows']], 'CPU map item order mismatch')
    dump(HERE / 'VERIFIED_CAPTURE.json', {'experiment': 'E65', 'status': 'COMPLETE_INTEGRITY_VERIFIED', 'CPU_only': True,
        'rows': len(bank['rows']), 'items': len(items), 'positions': positions, 'dtype': 'float16', 'block': BLOCK,
        'output_seal_sha256': sha(final / 'OUTPUT_SEAL.json'), 'request_sha256': sha(HERE / 'LAUNCH_REQUEST.json'),
        'provider_seconds': stopped-a['provider_created_epoch'], 'CPU_identity_map_sha256': sha(folder / 'IDENTITY_MAP.json'),
        'downstream_owner': 'W-lens', 'probe_or_reader_analysis_run': False})
    print('E65 capture integrity verified; downstream C remains with W-lens.')


if __name__ == '__main__': main()
