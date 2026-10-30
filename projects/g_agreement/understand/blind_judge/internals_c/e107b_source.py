"""CPU-only §240 forecast source; no allocation, network or model calls.

Select the original E107 inventory's 199 belief_wrong E82 items. Replace only
the outside instruction, retaining the original public prompt and per-target
judge plan. A new tested owner report and isolated execution channel are required
before either paid phase; this module cannot dispatch them.
"""
import hashlib
from pathlib import Path

from .banks import opaque
from .runner import CACHE
from .transport import ROOT
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

QUESTION = 'What will this model answer? Give the value.'
OLD_QUESTION = 'Describe what is going on in this text and what comes next.'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def unique(rows):
    result = {row['id']: row for row in rows}
    require(len(result) == len(rows), 'unique original source IDs')
    return result


def project(inventory, bindings, candidates, plans, public_by_path, expected=199):
    binding_by_id, candidate_by_id = unique(bindings), unique(candidates)
    selected = [x for x in inventory if x['bank'] == 'E82' and x.get('cohort') == 'belief_wrong']
    require(len(selected) == expected and len({x['id'] for x in selected}) == expected,
            'exact original belief-wrong inventory; no new classification')
    generation, custody, judging = [], [], []
    for item in selected:
        ident = item['id']
        binding, candidate = binding_by_id[ident], candidate_by_id[ident]
        require(all(binding[k] == item[k] for k in ('bank', 'row', 'item_id')),
                'original inventory/source identity join')
        public = unique(public_by_path[binding['source_public_file']])[binding['source_public_id']]
        prompt = public['prompt']
        require(digest(prompt) == binding['source_prompt_sha256'], 'literal original public prompt')
        require(binding['instruction'] == OLD_QUESTION and
                candidate['prompt'] == prompt + '\n' + OLD_QUESTION and
                digest(candidate['prompt']) == binding['generation_prompt_sha256'],
                'original outside format; replace instruction only')
        target_plans = [p for p in plans if p['inventory_id'] == ident]
        require(len(target_plans) == 2 and {p['target'] for p in target_plans} == {'belief', 'truth'} and
                all(p['bank'] == 'E82' for p in target_plans), 'same original two target judge plans')
        oid = opaque('E107b', 'forecast', ident)
        generation.append(dict(id=oid, phase='generation',
            rendered=dict(system=None, user=prompt + '\n' + QUESTION, schema=None)))
        custody.append(dict(id=oid, original_inventory_id=ident, original_item_id=item['item_id'],
            row=item['row'], source_public_id=binding['source_public_id'],
            source_public_file=binding['source_public_file'], source_prompt_sha256=digest(prompt),
            forecast_prompt_sha256=digest(generation[-1]['rendered']['user'])))
        for p in target_plans:
            judging.append(dict(p, forecast_id=oid,
                judgment_id=opaque('E107b', 'forecast_judge', ident, p['target'])))
    return generation, custody, judging


def prepare():
    owner = ROOT.parent/'wt-i2'
    original = owner/'cache/g_agreement/i2/e107_cpu_inventory_v1'
    inv = owner/'results/g_agreement/i2/e107_inventory_v1'
    inventory_seal = inv/'INVENTORY_SEAL.json'
    verify(inventory_seal, sha(inventory_seal))
    old_plan = CACHE/'E107/frozen_judge_plan'
    verify(old_plan/'PLAN_SEAL.json', sha(old_plan/'PLAN_SEAL.json'))
    original_hashes = read(old_plan/'ORIGINAL_SOURCE_BINDINGS.PRIVATE.json')
    for p, h in original_hashes.items():
        require(sha(p) == h, 'original frozen E107 judge source binding')
    bindings = read(original/'GENERATION_SOURCE_BINDINGS.PRIVATE.json')
    paths = {b['source_public_file']: b['source_public_file_sha256'] for b in bindings if b['bank'] == 'E82'}
    for p, h in paths.items():
        require(sha(p) == h, 'whole original E82 public source')
    calls, custody, plans = project(read(inv/'INVENTORY.json'), bindings,
        read(original/'GENERATION_CANDIDATE.json'), read(old_plan/'PLANS.PRIVATE.json'),
        {p: read(p) for p in paths})
    dest = CACHE/'E107b/forecast_source'
    payloads = {'GENERATION_CALLS.json': calls, 'CUSTODY.PRIVATE.json': custody,
                'JUDGE_PLAN.PRIVATE.json': plans,
                'SOURCE_BINDINGS.PRIVATE.json': dict(original_hashes, **paths,
                    **{str(inventory_seal): sha(inventory_seal),
                       str(original/'GENERATION_SOURCE_BINDINGS.PRIVATE.json'): sha(original/'GENERATION_SOURCE_BINDINGS.PRIVATE.json'),
                       str(original/'GENERATION_CANDIDATE.json'): sha(original/'GENERATION_CANDIDATE.json'),
                       str(old_plan/'PLAN_SEAL.json'): sha(old_plan/'PLAN_SEAL.json')})}
    if (dest/'SOURCE_SEAL.json').exists():
        verify(dest/'SOURCE_SEAL.json', sha(dest/'SOURCE_SEAL.json'))
        require(all(read(dest/n) == v for n, v in payloads.items()), 'immutable forecast source')
        return dest
    dest.mkdir(parents=True, exist_ok=False, mode=0o700)
    for n, value in payloads.items():
        write(dest/n, value)
        (dest/n).chmod(0o600)
    write(dest/'SOURCE_SEAL.json', dict(experiment='E107b', authority='section240/272e3fd35/direct Guiv',
        status='CPU_SOURCE_ONLY', n_items=199, n_generation_calls=199, n_original_target_plans=398,
        instruction=QUESTION, cohort_reclassified=False, original_banks_replayed=False,
        owner_report_adapter_required_before_paid_calls=True, allocation_created=False,
        files={n: sha(dest/n) for n in payloads}))
    return dest


if __name__ == '__main__':
    dest = prepare()
    print('E107b CPU source seal ' + sha(dest/'SOURCE_SEAL.json') + '; no allocation or calls')
