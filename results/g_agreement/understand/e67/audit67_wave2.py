"""Read-only deterministic wave2 delivery/source audit. No judging or scientific analysis."""
from build67_wave2 import PRIVATE, JUDGE, PUBLIC
from audit67 import verify_directory
from sources67_wave2 import HERE, Ledger, load_wave2
from packet67 import *


def audit():
    verify_directory(JUDGE, 'JUDGE_PACKET_SEAL.json', {'CLAIMS_RUBRIC.txt', 'CLAIMS_OUTPUT_SCHEMA.json',
        'packet_01.jsonl', 'packet_02.jsonl', 'JUDGE_PACKET_SEAL.json'})
    verify_directory(PRIVATE, 'INTEGRATOR_SEAL.json', {'PAIRING_CONDITION_MAP.PRIVATE.json',
        'SAMPLE_INVENTORY.PRIVATE.json', 'SOURCE_BINDING.PRIVATE.json', 'INTEGRATOR_SEAL.json'})
    require(sha(PRIVATE/'INTEGRATOR_SEAL.json') == sha(PUBLIC/'INTEGRATOR_SEAL.json'), 'Public private seal linkage')
    for name in ('CLAIMS_RUBRIC.txt', 'CLAIMS_OUTPUT_SCHEMA.json'):
        require(sha(JUDGE/name) == sha(HERE/'judge_wave1'/name), 'Frozen wave1 rubric/schema changed')
    pairing = read(PRIVATE/'PAIRING_CONDITION_MAP.PRIVATE.json')
    require(pairing['wave'] == 2 and pairing['integrator_only'] is True and pairing['judge_or_pod_access_forbidden'] is True
            and pairing['packet_seal_sha256'] == sha(JUDGE/'JUDGE_PACKET_SEAL.json'), 'Private wave custody')
    packets = [[json.loads(line) for line in (JUDGE/f'packet_{i:02d}.jsonl').read_text().splitlines()] for i in (1, 2)]
    validate_packets(packets, pairing['pairs'])
    source = read(PRIVATE/'SOURCE_BINDING.PRIVATE.json')
    for path, digest in source['files_sha256'].items(): require(sha(path) == digest, 'Source changed')
    ledger = Ledger(); pools = load_wave2(ledger)
    require(ledger.files == source['files_sha256'] and ledger.analyses == source['eligible_once_analysis_seals'], 'Source lineage mismatch')
    expected_packets, expected_map, inventory = build_packets(pools)
    require(packets == expected_packets and pairing['pairs'] == expected_map, 'Seed/donor/assignment/opaque-ID/shuffle/verbatim mismatch')
    require(inventory == read(PRIVATE/'SAMPLE_INVENTORY.PRIVATE.json')['strata'], 'Private inventory mismatch')
    # Independently check seeded sample and donors against the entire original native population.
    from collections import defaultdict
    groups = defaultdict(list)
    for pair in pairing['pairs']: groups[pair['bank'], pair['reader']].append(pair)
    for key, pool in pools.items():
        ordered = sorted(pool, key=lambda x: x['item_id'])
        chosen = sorted(ordered[int(i)]['item_id'] for i in np.random.default_rng(20261027).choice(len(ordered), 100, replace=False))
        require(chosen == [x['item_id'] for x in groups[key]], 'Independent sample audit')
        rng = np.random.default_rng(20261028)
        for pair in groups[key]:
            candidates = [x for x in ordered if x['row'] == pair['row'] and x['item_id'] != pair['item_id']]
            donor = candidates[int(rng.integers(len(candidates)))]['item_id']
            require(pair['records'][1]['condition'] == 'mismatched' and pair['records'][1]['prompt_item_id'] == donor, 'Independent donor audit')
    manifest = read(HERE/'WAVE2_MANIFEST.json')
    require(manifest['sampled_readouts'] == 400 and manifest['judge_records'] == 800
            and manifest['judge_packet_seal_sha256'] == sha(JUDGE/'JUDGE_PACKET_SEAL.json'), 'Manifest mismatch')
    return {'experiment': 'E67', 'wave': 2, 'status': 'PASS', 'CPU_only': True, 'sampled_readouts': 400,
        'judge_records': 800, 'records_per_packet': [400, 400], 'source_seals_verified': True,
        'deterministic_reproduction_and_independent_sample_donor_audit': True,
        'verbatim_prompts_readouts_and_rubric': True, 'private_files_only_in_ignored_cache': True,
        'equal_prompt_mismatches': sum(x['mismatched_equal_prompt_text_count'] for x in inventory),
        'judge_calls': 0, 'scientific_analysis_invocations': 0,
        'judge_packet_seal_sha256': sha(JUDGE/'JUDGE_PACKET_SEAL.json'),
        'integrator_seal_sha256': sha(PUBLIC/'INTEGRATOR_SEAL.json')}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path); args = p.parse_args()
    result = audit()
    if args.out: dump(args.out, result)
    print(json.dumps(result))
