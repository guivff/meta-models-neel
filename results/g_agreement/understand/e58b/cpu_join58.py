"""CPU-custody input validation and label join. Never stage this module or its data to a pod."""
import copy
import hashlib
import numpy as np
from common58 import *


def pca_population(rows):
    return 'pooled_dev_read_points' if sum(len(r['dev']) for r in rows) >= 768 else 'pooled_dev_prompt_positions'


def validate_labeled_bank(bank):
    require(bank.get('experiment') == 'E58b' and bank.get('complete_registered_scope') is True,
            'Complete registered scope binding required')
    require(bank.get('definition_holds_resolved') is True, 'Scientific definition holds unresolved')
    expected_pca = pca_population(bank['rows'])
    require(bank.get('pca_population') == expected_pca, 'Exact pooled-PCA fallback rule required')
    require(bank.get('definition_authority_commit'), 'Committed definition authority required')
    rows = bank['rows']
    require(rows and len({r['key'] for r in rows}) == len(rows), 'Unique nonempty row catalog required')
    require({r['feature'] for r in rows if r['control']} == set(CONTROLS)
            and sum(bool(r['control']) for r in rows) == 3, 'All three clarified sanity rows required')
    require(all(r['feature'] != 'reasoning_bridge' for r in rows), 'Shared-answer bridge is excluded by clarification 1(a)')
    require({r['feature'] for r in rows if r['feature'] in SHALLOW} == set(SHALLOW),
            'Both clarification-2 shallow-content rows required')
    require({r['bank'] for r in rows} >= {'W1', 'E36', 'E56', 'E57'}, 'Registered bank omitted')
    for row in rows:
        require(row['category'] in ('bookkeeping', 'delimiter', 'syntactic', 'format', 'content'), 'Frozen category required')
        for split in ('dev', 'test'):
            items = row[split]
            require(len(items) == 84 and len({x['id'] for x in items}) == 84, 'Full frozen 84-item split required')
            require(all(x['split'] == split and x['ids'] and all(type(t) is int and t >= 0 for t in x['ids'])
                        for x in items), 'Exact untruncated token IDs required')
        require(not ({x['id'] for x in row['dev']} & {x['id'] for x in row['test']}), 'Dev/test overlap')
        require(sum(x['label'] == 1 for x in row['test']) == 42
                and all(type(x['label']) is int and x['label'] in (0, 1) for x in row['test']), 'Frozen A-positive test labels required')
        for item in row['test']:
            require(item.get('pairs'), 'No silently skipped test pair')
            for pair in item['pairs']:
                require(set(pair) >= {'A_ids', 'B_ids', 'source_sha256'}, 'Frozen pair lineage required')
                require(pair['A_ids'] and pair['B_ids'] and pair['A_ids'] != pair['B_ids'],
                        'Distinct frozen correct/wrong pair required; no shared-answer invention')
                require(all(type(t) is int and t >= 0 for t in pair['A_ids'] + pair['B_ids']), 'Frozen pair token IDs required')
        if row['bank'] == 'E57':
            lookup = {x['id']: x for x in row['test']}
            for item in row['test']:
                donor = lookup.get(item.get('swap_donor_id'))
                require(donor is not None and donor['label'] == 1 - item['label'], 'Frozen opposite-state E57 donor required')
                require([(p['A_ids'], p['B_ids']) for p in item['pairs']]
                        == [(p['A_ids'], p['B_ids']) for p in donor['pairs']], 'Swap candidate pairs differ')
    require(bank.get('source_seals') and bank.get('pair_inventory') and bank.get('category_seal_sha256'),
            'Upstream bank/pair/category seals and complete applicability inventory required')
    return rows


def split_bank(bank):
    """Deterministic blind export; labels cannot affect pod bytes or ID order."""
    rows = validate_labeled_bank(bank)
    pod = {'experiment': 'E58b', 'schema': 'E58B_POD_BLIND_V2',
           'pca_population': bank['pca_population'], 'rows': []}
    join = {'experiment': 'E58b', 'schema': 'E58B_CPU_JOIN_V2',
            'original_bank': copy.deepcopy(bank), 'row_map': {}, 'item_map': {}}
    rng = np.random.default_rng(20261027)
    for ri, row in enumerate(rows):
        opaque_row = hashlib.sha256(f'E58b row {ri}'.encode()).hexdigest()[:32]
        join['row_map'][opaque_row] = row['key']
        public_row = {'key': opaque_row, 'dev': [], 'test': []}
        for split in ('dev', 'test'):
            for j, item in enumerate(row[split]):
                opaque = hashlib.sha256(f'E58b item {ri} {split} {j}'.encode()).hexdigest()[:32]
                join['item_map'][opaque] = {'row': row['key'], 'id': item['id'], 'split': split}
                public = {'id': opaque, 'split': split, 'ids': list(item['ids'])}
                if split == 'test':
                    public['pairs'] = [{'A_ids': list(p['A_ids']), 'B_ids': list(p['B_ids'])} for p in item['pairs']]
                public_row[split].append(public)
            order = rng.permutation(len(public_row[split]))
            public_row[split] = [public_row[split][int(i)] for i in order]
        pod['rows'].append(public_row)
    return pod, join


def join_records(pod, join, records):
    """CPU only: validate the blind export, then orient candidate likelihoods."""
    require(join.get('schema') == 'E58B_CPU_JOIN_V2' and join.get('experiment') == 'E58b', 'CPU join schema mismatch')
    expected_pod, expected_join = split_bank(join['original_bank'])
    require(pod == expected_pod and join['row_map'] == expected_join['row_map']
            and join['item_map'] == expected_join['item_map'], 'CPU/pod item or pair alignment mismatch')
    converted = []
    for record in records:
        require(set(record) == {'row', 'id', 'pair_index', 'arm', 'seed', 'logp_A', 'logp_B'},
                'Only separate raw A/B likelihood records are accepted')
        arm = record['arm']
        require(arm in ARMS, 'Unknown arm')
        expected_seed = SEEDS[int(arm[-1])] if arm.startswith('random') else None
        require(record['seed'] == expected_seed and (expected_seed is None or type(record['seed']) is int), 'Random seed mismatch')
        require(type(record['pair_index']) is int and record['pair_index'] >= 0, 'Pair index mismatch')
        require(all(finite_number(record[k]) and record[k] <= 0 for k in ('logp_A', 'logp_B')),
                'Finite nonpositive candidate log probabilities required')
        require(record['row'] in join['row_map'] and record['id'] in join['item_map'], 'Unknown blind identity')
        item = join['item_map'][record['id']]
        original_row = join['row_map'][record['row']]
        require(item['row'] == original_row and item['split'] == 'test', 'Wrong row/split identity')
        converted.append({'row': original_row, 'id': item['id'], 'pair_index': record['pair_index'], 'arm': arm,
                          'logodds_A_minus_B': record['logp_A'] - record['logp_B']})
    rows = validate_labeled_bank(join['original_bank'])
    return rows, converted


def load_custodied_join(request, pod, input_seal_sha256):
    binding_path = HERE / 'CPU_CUSTODY_BINDING.20261027.json'
    require(sha(binding_path) == request['cpu_custody_binding_sha256'], 'CPU custody binding mismatch')
    binding = read(binding_path)
    folder = (ROOT / binding['directory']).resolve()
    require(folder.is_relative_to(CACHE.resolve()), 'CPU custody path outside owner cache')
    require(sha(folder / 'CPU_SEAL.json') == binding['cpu_seal_sha256'], 'CPU seal mismatch')
    verify(folder, 'CPU_SEAL.json')
    receipt = read(folder / 'INTEGRATOR_CUSTODY.json')
    require(receipt.get('issuer') == 'integrator' and receipt.get('experiment') == 'E58b'
            and receipt.get('verified_cpu_only') is True and receipt.get('labels_stayed_off_pod') is True,
            'Integrator CPU-only custody receipt required')
    require(receipt.get('cpu_seal_sha256') == binding['cpu_seal_sha256']
            and receipt.get('cpu_join_sha256') == binding['cpu_join_sha256']
            and receipt.get('pod_input_seal_sha256') == input_seal_sha256, 'CPU custody receipt linkage mismatch')
    require(sha(folder / 'CPU_JOIN.json') == binding['cpu_join_sha256'], 'CPU label file mismatch')
    join = read(folder / 'CPU_JOIN.json')
    require(join['pod_input_seal_sha256'] == input_seal_sha256, 'CPU join points to another pod population')
    # Validate complete item/candidate identity before any label orientation.
    expected_pod, expected_join = split_bank(join['original_bank'])
    require(expected_pod == pod and expected_join['row_map'] == join['row_map']
            and expected_join['item_map'] == join['item_map'], 'Sealed CPU join differs from the pod population')
    return join


