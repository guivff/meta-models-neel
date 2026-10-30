"""E67 wave2: sealed native test jobs only, including retained pilots exactly once."""
from sources67 import HERE, ROOT, MECH, Ledger, normalized
from packet67 import *

COHORT = 'joint-a7fea77c-7279007d'


def validate_native(job, rows, items):
    require(job['kind'] == 'native' and job['reader'] in ('oracle', 'nla'), 'Original native job required')
    require(len(rows) == len(job['units']), 'Native job cardinality')
    for row, unit in zip(rows, job['units']):
        require(unit['id'] in items and unit['split'] == 'test', 'Original test item required')
        item = items[unit['id']]
        require(row['unit_id'] == unit['id'] and row['id'] == unit['id'] + ':' + job['reader'] + ':0'
                and row['reader'] == job['reader'] and row['repeat'] == 0, 'Single native identity')
        require(row['feature'] == item['feature'] == unit['feature']
                and row['reader_native_layer'] == (44 if job['reader'] == 'oracle' else 42), 'Native row/layer identity')
        require(unit['text'] == item['text'] and isinstance(row['text'], str), 'Exact native prompt/text required')


def load_wave2(ledger):
    # Authorise both banks before opening any shared retained-pilot text.
    specs = {}
    manifests = {}
    for bank in ('E56', 'E57'):
        spec_path = MECH / f'results/g_agreement/understand/analysis402/{bank}_SPEC.json'
        ledger.bind(spec_path); spec = read(spec_path); specs[bank] = spec
        analysis_dir = MECH / f'results/g_agreement/understand/{bank.lower()}/analysis402_once_2026-10-27'
        analysis = ledger.verify(analysis_dir, 'ANALYSIS_SEAL.json')
        require(analysis['status'] == 'COMPLETE' and analysis['experiment'] == bank
                and analysis['cohort_id'] == COHORT and 'ONCE.json' in analysis['files'], 'Completed once-only analysis required')
        ledger.analyses[bank] = {'path': str(analysis_dir/'ANALYSIS_SEAL.json'),
                               'sha256': sha(analysis_dir/'ANALYSIS_SEAL.json')}
        ledger.bind(spec['receipt'], analysis['manifest_sha256']); manifest = read(spec['receipt'])
        require(manifest['verified'] is True and manifest['issuer'] == 'integrator'
                and manifest['experiment'] == bank and manifest['cohort_id'] == COHORT, 'Verified original manifest')
        manifests[bank] = manifest
    joint_path = MECH/'results/g_agreement/understand/joint9/INPUT_BINDING.json'
    ledger.bind(joint_path); joint = read(joint_path); joint_inputs = Path(joint['inputs'])
    ledger.bind(joint_inputs/'INPUT_SEAL.json', joint['input_seal_sha256'])
    ledger.bind(joint_inputs/'PLAN.json', read(joint_inputs/'INPUT_SEAL.json')['files']['PLAN.json'])
    original = read(joint_inputs/'PLAN.json')
    require(original['identity'] == joint['plan_sha256'], 'Original plan identity')
    pools = {}
    for bank in ('E56', 'E57'):
        spec = specs[bank]; manifest = manifests[bank]; inp = Path(spec['inputs'])
        ledger.bind(inp/'INPUT_SEAL.json', spec['input_seal_sha256']); input_seal = read(inp/'INPUT_SEAL.json')
        for name in ('items.json', 'SAMPLING.json' if bank == 'E56' else 'RUN_PLAN.json'):
            ledger.bind(inp/name, input_seal['files'][name])
        plan = read(inp/('SAMPLING.json' if bank == 'E56' else 'RUN_PLAN.json'))
        native_ids = {i for ids in plan['native_ids'].values() for i in ids}
        all_items = read(inp/'items.json'); items = {x['id']: x for x in all_items if x['id'] in native_ids}
        require(len(items) == len(native_ids) == (1092 if bank == 'E56' else 1680)
                and all(x['split'] == 'test' for x in items.values()), 'Complete registered native test population')
        jobs = {j['key']: j for j in original['jobs'] if j['exp'] == bank and j['kind'] == 'native'}
        found = {}
        def retain(key, rows, path, payload_key=None):
            require(key in jobs and key not in found, 'Duplicate or out-of-bank native job')
            job = jobs[key]; validate_native(job, rows, items)
            found[key] = (job, rows, path, payload_key)
        shards = set()
        for entry in manifest['shards']:
            shard = entry['shard']; require(shard not in shards, 'Duplicate shard'); shards.add(shard)
            root = Path(entry['root']); outer = ledger.verify(root, 'OUTPUT_SEAL.json', entry['output_seal_sha256'])
            require(outer['experiment'] == bank and outer['shard'] == shard and outer['status'] == 'COMPLETE', 'Completed native shard')
            if entry['layout'] == 'joint9':
                require(bank == 'E56' and shard in (0, 1) and outer['plan_sha256'] == joint['plan_sha256'], 'Legacy shard identity')
                for key, job in jobs.items():
                    if not job['retained_pilot'] and job['shard'] == shard:
                        path = root/'jobs'/f'{job["resume_number"]:06d}.json'
                        require(str(path.relative_to(root)) in outer['files'], 'Unsealed legacy job')
                        retain(key, read(path), path)
            else:
                require(entry['layout'] == 'replan402' and outer['cohort_id'] == COHORT, 'Replan cohort')
                binding_path = MECH/f'results/g_agreement/understand/replan402/{bank}_{shard}_BINDING.json'
                ledger.bind(binding_path); binding = read(binding_path); staged = Path(binding['inputs'])
                ledger.bind(staged/'INPUT_SEAL.json', binding['input_seal_sha256'])
                ledger.bind(staged/'PLAN.json', read(staged/'INPUT_SEAL.json')['files']['PLAN.json'])
                shard_plan = read(staged/'PLAN.json')
                require(shard_plan['parent_plan_sha256'] == joint['plan_sha256'], 'Original parent plan')
                stage = root/bank; seal = ledger.verify(stage, 'STAGE_SEAL.json')
                require(seal['status'] == 'COMPLETE' and seal['stage'] == bank
                        and seal['plan_sha256'] == binding['plan_sha256'] == sha(staged/'PLAN.json'), 'Sealed replan identity')
                require(outer['files'][bank+'/STAGE_SEAL.json'] == sha(stage/'STAGE_SEAL.json'), 'Outer stage seal linkage')
                for job in shard_plan['jobs']:
                    if job['kind'] != 'native': continue
                    key = job['original_key']; require(key in jobs and job['units'] == jobs[key]['units'], 'Original native units unchanged')
                    path = stage/'jobs'/f'{job["number"]:06d}.json'
                    require(str(path.relative_to(stage)) in seal['files'], 'Unsealed native job')
                    retain(key, read(path), path)
        require(shards == {0, 1, 2}, 'Three completed shards required')
        pilots = {}
        for entry in manifest['retained_pilot_pulls']:
            root = Path(entry['root']); seal = ledger.verify(root, entry['seal_file'], entry['seal_sha256'])
            require(entry['pilot_file'] in seal['files'] and entry['slot'] not in pilots, 'Unique sealed pilot custody')
            pilots[entry['slot']] = root/entry['pilot_file']
        for key, job in jobs.items():
            if not job['retained_pilot']: continue
            prefix, index = key.split(':'); slot = 'second' if prefix == 'second' else int(prefix)
            path = pilots[slot]
            retain(key, read(path)[index], path, index)
        require(set(found) == set(jobs), 'Exact original native job union, pilots included once')
        for reader in ('oracle', 'nla'):
            pool = []
            for key, (job, rows, path, payload_key) in sorted(found.items()):
                if job['reader'] != reader: continue
                for index, row in enumerate(rows):
                    x = normalized(bank, reader, items[row['unit_id']], row, path, index)
                    x['source'].update(original_job_key=key, payload_key=payload_key)
                    pool.append(x)
            require(len(pool) == len(items) and {x['item_id'] for x in pool} == native_ids, 'Complete unique native test grid')
            pools[bank, reader] = pool
    return pools
