from copy import deepcopy
import pytest
from .e108_binding import bind_hits


def fixture():
    plans = [dict(id='n1', kind='native', hit_unit_ids=dict(oracle='h1', nla='h2', outside='h3'), missing_reasons={}),
             dict(id='n2', kind='native', hit_unit_ids=dict(oracle=None, nla=None, outside=None),
                  missing_reasons={s: 'GROUND_TRUTH_MULTIPLE' for s in ('oracle', 'nla', 'outside')}),
             dict(id='p', kind='placebo', hit_unit_ids=dict(oracle='h4', nla=None),
                  missing_reasons=dict(nla='REFERENCE_GROUND_TRUTH_NONE'))]
    judgments = [dict(id='h'+str(i+1), kind='choice_hit', status=status, code=code)
                 for i, (status, code) in enumerate([('KEPT', True), ('KEPT', False),
                                                   ('UNPARSEABLE', None), ('REFUSED', None)])]
    return plans, judgments


def test_exact_true_false_terminal_missing_and_ineligible_cells_with_pointers():
    plans, judgments = fixture()
    before = deepcopy((plans, judgments))
    values, pointers = bind_hits(plans, judgments)
    assert (plans, judgments) == before
    assert values == [dict(id='n1', hits=dict(oracle=True, nla=False, outside=None)),
                      dict(id='n2', hits=dict(oracle=None, nla=None, outside=None)),
                      dict(id='p', hits=dict(oracle=None, nla=None))]
    assert pointers[0]['systems']['nla']['keys'] == [1, 'code']
    assert pointers[1]['systems']['oracle']['reason'] == 'GROUND_TRUTH_MULTIPLE'
    assert pointers[2]['systems']['oracle']['status'] == 'REFUSED'


def test_partial_extra_or_duplicate_judgment_census_fails_closed():
    plans, judgments = fixture()
    for bad in (judgments[:-1], judgments+[judgments[0]],
                judgments+[dict(id='extra', kind='choice_hit', status='KEPT', code=True)]):
        with pytest.raises(ValueError):
            bind_hits(plans, bad)


def test_no_bool_coercion_or_failed_call_as_zero():
    plans, judgments = fixture()
    for index, field, value in [(0, 'code', 1), (2, 'code', False), (3, 'status', 'UNKNOWN')]:
        bad = deepcopy(judgments)
        bad[index][field] = value
        with pytest.raises(ValueError):
            bind_hits(plans, bad)


def test_missing_ineligibility_reason_cannot_be_guessed():
    plans, judgments = fixture()
    plans[1]['missing_reasons'] = {}
    with pytest.raises(ValueError):
        bind_hits(plans, judgments)


def test_full_synthetic_bank_resolves_through_original_adapter_without_analysis(tmp_path, monkeypatch):
    from . import e108_binding as binding
    from projects.g_agreement.e108_analysis import adapter
    from projects.g_agreement.e108_analysis.rules import CATEGORIES
    from projects.g_agreement.readerbench.io import write, read, sha
    root = tmp_path
    here = root/'receipts'
    cache = root/'cache'
    here.mkdir()
    home = cache/'E108'
    units = home/'chosen_member_hit_units'
    hits = home/'chosen_member_hit_judging/outputs'
    inventory = root/'results/g_agreement/understand/e108'
    for path in (units, hits, inventory):
        path.mkdir(parents=True)
    metadata = [dict(id=f'n{ci}_{arm}_{j}', kind='native', category=cat, arm=arm, prompt_id=f'{ci}_{j}')
                for ci, cat in enumerate(CATEGORIES) for arm in ('immediate', 'delayed') for j in range(42)]
    metadata += [dict(id=f'p{i}', kind='placebo') for i in range(84)]
    write(inventory/'INVENTORY.json', metadata)
    write(inventory/'BANK_SEAL.json', dict(experiment='E108', files={'INVENTORY.json': sha(inventory/'INVENTORY.json')}))
    plans = []
    for i, meta in enumerate(metadata):
        systems = ('oracle', 'nla', 'outside') if meta['kind'] == 'native' else ('oracle', 'nla')
        plan = dict(id=meta['id'], kind=meta['kind'], hit_unit_ids={s: 'h'+s if i == 0 else None for s in systems},
                    missing_reasons={} if i == 0 else {s: 'GROUND_TRUTH_NONE' for s in systems})
        if meta['kind'] == 'native':
            plan.update(ground_truth=dict(status='ONE' if i == 0 else 'NONE', canonical_member='dog' if i == 0 else None),
                        J_fraction=None, choice_token_offset=1 if i == 0 else None)
        plans.append(plan)
    write(units/'MEASUREMENT_PLAN.PRIVATE.json', plans)
    write(units/'CUSTODY.json', dict(source_seals=[]))
    write(units/'UNIT_SEAL.json', dict(experiment='E108', files={n: sha(units/n) for n in
        ('MEASUREMENT_PLAN.PRIVATE.json', 'CUSTODY.json')}))
    terminals = [dict(id='h'+s, kind='choice_hit', status='UNPARSEABLE' if code is None else 'KEPT', code=code)
                 for s, code in zip(('oracle', 'nla', 'outside'), (True, False, None))]
    write(hits.parent/'CALLS.json', [])
    write(hits.parent/'INPUT_SEAL.json', dict(files={'CALLS.json': sha(hits.parent/'CALLS.json')},
        source_seals=[dict(seal=str(units/'UNIT_SEAL.json'), sha256=sha(units/'UNIT_SEAL.json'))]))
    write(hits/'JUDGMENTS.json', terminals)
    write(hits/'JUDGMENT_SEAL.json', dict(experiment='E108', status='COMPLETE', route_verified=True,
        input_sha256=sha(hits.parent/'INPUT_SEAL.json'), first_output_utc='synthetic',
        files={'JUDGMENTS.json': sha(hits/'JUDGMENTS.json')}))
    (root/'source.py').write_text('# synthetic source pin\n')
    write(here/'E108_BINDING_SOURCE_SEAL.json', dict(files={'source.py': sha(root/'source.py')}))
    monkeypatch.setattr(binding, 'ROOT', root)
    monkeypatch.setattr(binding, 'HERE', here)
    monkeypatch.setattr(binding, 'CACHE', cache)
    monkeypatch.setattr(adapter, 'ROOT', root)
    def git(args, **kwargs):
        return 'a'*40 if args[1] == 'log' else (inventory/'BANK_SEAL.json').read_bytes()
    monkeypatch.setattr(binding.subprocess, 'check_output', git)
    dest = binding.prepare()
    native, placebo = adapter.inputs(read(dest/'ADAPTER_SPEC.PRIVATE.json'))
    assert len(native) == 1008 and len(placebo) == 84
    assert native[0]['hits'] == dict(oracle=True, nla=False, outside=None)
    assert native[0]['choice_status'] == 'ONE' and native[0]['choice_token_offset'] == 1
    assert all(x['choice_status'] == 'NONE' and all(v is None for v in x['hits'].values()) for x in native[1:])
    assert all(all(v is None for v in x['hits'].values()) for x in placebo)
    assert binding.prepare() == dest
