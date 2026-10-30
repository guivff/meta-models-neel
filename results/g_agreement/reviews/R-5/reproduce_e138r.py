"""Independent E138R final-seal intake; never runs owner correction/guard.

The original reviewer statistical/role kernels are reused unchanged. All real
sources are opened only after a pinned COMPLETE_ONCE correction seal validates.
"""
import argparse
import json
from pathlib import Path
from reproduce_e118b import check, compare, read, sealed, sha
from reproduce_e138 import ROOT, expand_roles, reproduce_owner_rows

AUTHORITY = '250_deviation2_37d27a217'
DEFECTIVE = '1f10da833fa1ada3faa54d53236385ec2958f60221be4fa2f1a1bdc0029beaf8'
INPUT = 'a9b55f3b72f257cb4b86aec5441f3be18f5cc57b51a92fe1ee717ab71c467f39'


def correction_contract(final, packet, terminal):
    check(final.get('experiment') == 'E138R' and final.get('status') == 'COMPLETE_ONCE', 'final corrected scientific seal required')
    check(final.get('authority') == AUTHORITY and final.get('defective_analysis_sha256') == DEFECTIVE, 'final correction disclosure')
    check(packet.get('experiment') == 'E138R' and packet.get('status') == 'COMPLETE', 'complete corrected binding')
    check(packet.get('correction_authority') == AUTHORITY and packet.get('defective_analysis_sha256') == DEFECTIVE, 'bound correction authority/defective history')
    check(packet.get('corrected_input_sha256') == INPUT, 'reviewed whole-value input')
    flags = ('whole_values_verified', 'same168_native_readouts_verified', 'R5_actual_sample_pass', 'post_output_correction_disclosed',
             'original84_verified', 'donor_pairing_E100_verified', 'random_E76_verified', 'clean_E127_no_prefix_verified',
             'literal_value_code_mapping_verified', 'route_verified', 'privacy_verified', 'terminal_dispositions_verified')
    check(all(packet.get(k) is True for k in flags), 'complete original and correction custody flags')
    check(packet['unknown_cost_requests'] == 0 and 0 <= packet['booked_usd'] <= packet['cap_usd'] == 1, 'corrected original bank1')
    check(terminal.get('experiment') == 'E138R' and terminal.get('status') == 'COMPLETE', 'corrected terminal judgments')
    check(terminal.get('input_seal_sha256') == INPUT, 'terminal reviewed whole-value input')


def check_new_pointers(rows, index):
    check(len(rows) == 84, 'original full84')
    for row in rows:
        for arm in ('donor', 'random'):
            cell = row['arms'][arm]
            check(type(cell) is dict and set(cell) == {'e104_role_code'}, 'lossless corrected categorical transport')
            for field in ('code', 'status', 'judgment_id'):
                p = cell['e104_role_code'][field]
                check(type(p) is dict and set(p) == {'ref'} and p['ref']['seal_index'] == index, 'no defective new-arm code/status/identity references')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis-seal', type=Path, required=True)
    p.add_argument('--seal-sha256', required=True)
    a = p.parse_args()
    pins = read(Path(__file__).with_name('E138R_REPRODUCTION_SOURCE.json'))
    check(all(sha(ROOT/f) == h for f, h in pins['files'].items()), 'prepared correction source changed')
    final = sealed(a.analysis_seal, a.seal_sha256)
    check(final.get('experiment') == 'E138R' and final.get('status') == 'COMPLETE_ONCE', 'correction seal before real source opening')
    check({'RESULTS.json', 'BINDING.PRIVATE.json', 'CORRECTION.json'} <= set(final['files']), 'complete original correction packet')
    spec = read(a.analysis_seal.parent/'BINDING.PRIVATE.json')
    check(spec['correction_authority'] == AUTHORITY, 'corrected SPEC authority')
    sealed(spec['defective_analysis_seal'], DEFECTIVE)
    packet = sealed(spec['binding_seal'], spec['binding_sha256'])
    sources = packet['source_seals']
    check(packet['corrected_judgments'] in sources, 'explicit corrected source')
    index = sources.index(packet['corrected_judgments'])
    seals = [sealed(s['seal'], s['sha256']) for s in sources]
    correction_contract(final, packet, seals[index])
    disclosure = read(a.analysis_seal.parent/'CORRECTION.json')
    check(disclosure.get('experiment') == 'E138R' and disclosure.get('authority') == AUTHORITY and
          disclosure.get('defective_analysis_sha256') == DEFECTIVE and disclosure.get('corrected_input_sha256') == INPUT,
          'published post-output correction disclosure')
    for name in ('E104_inventory', 'E127_clean', 'E100_pairing', 'E76_random'):
        s = packet['original_sources'][name]
        sealed(s['seal'], s['sha256'])
    review = packet['R5_sample_review_source']
    check(sha(review['path']) == review['sha256'], 'frozen published R5 sample review')
    pointers = read(Path(spec['binding_seal']).parent/'RECORD_POINTERS.json')
    check_new_pointers(pointers, index)
    cache = {}
    def resolve(ref):
        i = ref['seal_index']
        check(type(i) is int and 0 <= i < len(sources), 'source index')
        check(ref['member'] in seals[i]['files'], 'sealed member reference')
        key = (i, ref['member'])
        if key not in cache:
            cache[key] = read(Path(sources[i]['seal']).parent/ref['member'])
        result = cache[key]
        for k in ref['keys']:
            result = result[k]
        return result
    actual = reproduce_owner_rows(expand_roles(pointers, resolve))
    n = compare(actual, read(a.analysis_seal.parent/'RESULTS.json'))
    print(json.dumps(dict(status='VERIFIED', compared_leaves=n, analysis_sha256=a.seal_sha256,
                         donor_primary=actual['donor_primary'], random_withdrawal=actual['random_withdrawal'],
                         bootstrap=actual['bootstrap'], correction_after_output=True,
                         physical_and_chronology_custody='separate review required'), indent=2))


if __name__ == '__main__':
    main()
