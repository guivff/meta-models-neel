"""CPU-only E108 scalar/pointer binding; no analysis, calls or new scoring.

Ground truth, offsets and unavailable J fractions point at the frozen measurement
plan. Hit booleans/nulls are copied exactly from JUDGMENTS[index].code, with an
independent pointer for every eligible cell. Ineligible cells retain plan nulls.
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

from .transport import ROOT, HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def bind_hits(plans, judgments):
    by = {x['id']: (i, x) for i, x in enumerate(judgments)}
    require(len(by) == len(judgments), 'unique terminal hit IDs')
    expected = [v for p in plans for v in p['hit_unit_ids'].values() if v is not None]
    require(len(expected) == len(set(expected)) and set(expected) == set(by),
            'exact complete eligible hit census; no partial or extra judgments')
    require(len({p['id'] for p in plans}) == len(plans), 'unique full plan inventory')
    values, pointers = [], []
    for pi, plan in enumerate(plans):
        systems = {'oracle', 'nla', 'outside'} if plan['kind'] == 'native' else {'oracle', 'nla'}
        require(plan['kind'] in ('native', 'placebo') and set(plan['hit_unit_ids']) == systems,
                'original complete system census')
        hits, refs = {}, {}
        for system, ident in plan['hit_unit_ids'].items():
            if ident is None:
                require(bool(plan['missing_reasons'].get(system)), 'source-bound ineligibility reason')
                hits[system] = None
                refs[system] = dict(source='frozen_plan', plan_index=pi,
                                    reason=plan['missing_reasons'][system])
                continue
            ji, terminal = by[ident]
            require(terminal['kind'] == 'choice_hit' and terminal['status'] in
                    ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'known terminal hit status')
            code = terminal['code']
            require(type(code) is bool if terminal['status'] == 'KEPT' else code is None,
                    'exact original bool or terminal null; no coercion')
            hits[system] = code
            refs[system] = dict(source='terminal_code', member='JUDGMENTS.json',
                                keys=[ji, 'code'], unit_id=ident, status=terminal['status'])
        values.append(dict(id=plan['id'], hits=hits))
        pointers.append(dict(id=plan['id'], systems=refs))
    return values, pointers


def prepare():
    manifest = HERE/'E108_BINDING_SOURCE_SEAL.json'
    for name, digest in read(manifest)['files'].items():
        require(sha(ROOT/name) == digest, 'published CPU binding source pin')
    home = CACHE/'E108'
    unit_path = home/'chosen_member_hit_units/UNIT_SEAL.json'
    verify(unit_path, sha(unit_path))
    hit_path = home/'chosen_member_hit_judging/outputs/JUDGMENT_SEAL.json'
    hit = verify(hit_path, sha(hit_path))
    require(hit['experiment'] == 'E108' and hit['status'] == 'COMPLETE' and
            hit['route_verified'] is True, 'complete route-verified hit phase')
    input_seal = verify(hit_path.parent.parent/'INPUT_SEAL.json', hit['input_sha256'])
    require(any(Path(x['seal']).resolve() == unit_path.resolve() and x['sha256'] == sha(unit_path)
                for x in input_seal['source_seals']), 'same frozen hit units and result input')
    plans = read(unit_path.parent/'MEASUREMENT_PLAN.PRIVATE.json')
    judgments = read(hit_path.parent/'JUDGMENTS.json')
    inventory = ROOT/'results/g_agreement/understand/e108/BANK_SEAL.json'
    verify(inventory, sha(inventory))
    metadata = read(inventory.parent/'INVENTORY.json')
    require(len(plans) == 1092 and {p['id'] for p in plans} == {x['id'] for x in metadata},
            'all original1008 native and84 placebo IDs')
    require(sum(p['kind'] == 'native' for p in plans) == 1008 and
            sum(p['kind'] == 'placebo' for p in plans) == 84, 'full original inventory kinds')
    require({p['id']: p['kind'] for p in plans} == {x['id']: x['kind'] for x in metadata},
            'each original item kind unchanged')
    values, pointers = bind_hits(plans, judgments)
    dest = home/'normalized'
    dest.mkdir(exist_ok=True)
    dest.chmod(0o700)
    if (dest/'JUDGMENT_SEAL.json').exists():
        prior = verify(dest/'JUDGMENT_SEAL.json', sha(dest/'JUDGMENT_SEAL.json'))
        require(prior['source_seals'][1]['sha256'] == sha(unit_path) and
                prior['source_seals'][2]['sha256'] == sha(hit_path), 'immutable normalization sources')
        return dest
    write(dest/'HIT_VALUES.json', values)
    write(dest/'HIT_CODE_POINTERS.PRIVATE.json', pointers)
    write(dest/'VALUE_SEAL.json', dict(experiment='E108', status='EXACT_CODE_COPY',
        source_seals=[dict(seal=str(unit_path), sha256=sha(unit_path)),
                      dict(seal=str(hit_path), sha256=sha(hit_path))],
        files={n: sha(dest/n) for n in ('HIT_VALUES.json', 'HIT_CODE_POINTERS.PRIVATE.json')}))
    sources = [dict(seal=str(dest/'VALUE_SEAL.json'), sha256=sha(dest/'VALUE_SEAL.json')),
               dict(seal=str(unit_path), sha256=sha(unit_path)),
               dict(seal=str(hit_path), sha256=sha(hit_path))]
    for source in read(unit_path.parent/'CUSTODY.json')['source_seals']:
        verify(source['seal'], source['sha256'])
        if source not in sources:
            sources.append(source)
    measurements = []
    for i, plan in enumerate(plans):
        fields = dict(hits=dict(seal_index=0, member='HIT_VALUES.json', keys=[i, 'hits']))
        if plan['kind'] == 'native':
            fields.update({k: dict(seal_index=1, member='MEASUREMENT_PLAN.PRIVATE.json', keys=[i, k])
                           for k in ('ground_truth', 'J_fraction', 'choice_token_offset')})
        measurements.append(dict(id=plan['id'], fields=fields))
    write(dest/'MEASUREMENTS.json', measurements)
    write(dest/'NORMALIZATION_RECEIPT.json', dict(source_manifest_sha256=sha(manifest),
        policy='Exact JUDGMENTS.json[index].code bool/null copy; plan eligibility/ground truth/offset unchanged',
        inventory_items=1092, hit_units=len(judgments), aliases_added=0, early_choices_excluded=0,
        J_fraction_disposition='Frozen source-plan nulls retained; owner source requested, no recipe inferred',
        private_joins_cpu_only=True, scientific_analysis_run=False))
    write(dest/'JUDGMENT_SEAL.json', dict(experiment='E108', status='COMPLETE',
        inventory_sha256=sha(inventory), route_verified=True, redaction_audit_complete=True,
        ground_truth_blind=True, labels_cpu_only=True, source_seals=sources,
        first_output_utc=hit['first_output_utc'],
        outside_generation=dict(model='google/gemini-3.1-flash-lite', provider='google-vertex/global',
                                temperature=0, max_tokens=256, ZDR=True, data_collection='deny', fallbacks=False),
        files={n: sha(dest/n) for n in ('MEASUREMENTS.json', 'NORMALIZATION_RECEIPT.json')}))
    commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--',
                                     str(inventory.relative_to(ROOT))], cwd=ROOT, text=True).strip()
    blob = subprocess.check_output(['git', 'show', commit+':'+str(inventory.relative_to(ROOT))], cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest() == sha(inventory), 'original committed inventory')
    write(dest/'ADAPTER_SPEC.PRIVATE.json', dict(inventory_seal=str(inventory), inventory_sha256=sha(inventory),
        inventory_commit=commit, output_seal=str(dest/'JUDGMENT_SEAL.json'),
        output_sha256=sha(dest/'JUDGMENT_SEAL.json'), analysis=str(home/'analysis_once')))
    verify(dest/'JUDGMENT_SEAL.json', sha(dest/'JUDGMENT_SEAL.json'))
    return dest


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    dest = prepare()
    print('E108 complete CPU normalization '+sha(dest/'JUDGMENT_SEAL.json'))
