"""Offline E95 admission around the existing E87 grouped judge primitives.

No inference or credential access. E87's bank-specific admission stays intact.
"""
import hashlib
from decimal import Decimal
from pathlib import Path

from projects.g_agreement.readerbench.io import read, sha, verify
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge import e87


def group_id(stratum, unit_layer):
    return hashlib.sha256(f'E95:group:{stratum}:{unit_layer}'.encode()).hexdigest()[:32]


def universe(rows):
    result = {}
    for row in rows:
        ri = row['row_index']
        for reader in ('oracle', 'nla'):
            layers = row['oracle_layers'] if reader == 'oracle' else [42]
            for condition in ('real', 'placebo'):
                if condition == 'real' or (reader == 'oracle' and row['reuse_e87']):
                    ids = row['item_ids']
                else:
                    ids = [hashlib.sha256(f'E95:placebo:{ri}:{i}'.encode()).hexdigest()[:32]
                           for i in range(15)]
                stratum = f'{ri}:{condition}:{reader}'
                for unit in ids:
                    for layer in layers:
                        key = f'{unit}:{layer}'
                        gid = group_id(stratum, key)
                        require(gid not in result, 'unique E95 call identity')
                        result[gid] = (stratum, key)
    return result


def budget_gate(receipt, worst_case):
    reserved = Decimal(str(receipt['E95_allocation_usd']))
    total = Decimal(str(receipt['global_judging_committed_including_reservation_usd']))
    bound = Decimal(str(worst_case))
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified') is True
            and receipt.get('reservation_included') is True,
            'integrator reservation and reconciled global ledger required')
    require(all(x.is_finite() for x in (reserved, total, bound))
            and 0 <= bound <= reserved <= 60 and 0 < reserved <= total <= 1000,
            'E95 USD60 cap and global USD1000 envelope')


def unresolved_statement_ids(records, expected, eligibility):
    by_row = {x['row_index']: x['statement_score_registered'] for x in eligibility['rows']}
    require(len(records) == len(expected) and {x['id'] for x in records} == set(expected),
            'regex/disposition coverage over entire bank')
    unresolved = set()
    for record in records:
        row = int(expected[record['id']][0].split(':', 1)[0])
        require(row in by_row and type(by_row[row]) is bool, 'explicit statement-score eligibility')
        if not by_row[row]:
            require(record['status'] == 'NOT_EVALUABLE_NO_STATEMENT_SCORE',
                    'no value judgment invented for an unscorable row')
            continue
        require(record['status'] in ('RESOLVED', 'UNRESOLVED', 'NO_REGEX'),
                'explicit regex resolution state')
        if record['status'] != 'NO_REGEX':
            require(record.get('regex_sha256'), 'frozen regex provenance')
        if record['status'] != 'RESOLVED':
            unresolved.add(record['id'])
    return unresolved


def admission(spec):
    require(spec['bank'] == 'E95' and spec['channel'] == 'grouped_positions', 'E95 only')
    require(sha(Path(e87.__file__)) == spec['e87_primitives_sha256'], 'owner judge primitives pinned')
    for key in ('inventory', 'index', 'eligibility', 'regex_audit', 'custody_receipt', 'budget_receipt'):
        require(sha(spec[key]) == spec[key+'_sha256'], key+' identity')
    inventory = read(spec['inventory'])
    index = read(spec['index'])
    eligibility = read(spec['eligibility'])
    root=Path(__file__).resolve().parents[3]
    if eligibility['inventory_sha256'] != spec['inventory_sha256']:
        # Step3 removes rows/items; the pre-output eligibility ruling remains original.
        original=root/'results/g_agreement/understand/e95/ROW_INVENTORY.json'
        frozen=root/'results/g_agreement/understand/e95/STATEMENT_SCORE_ELIGIBILITY.json'
        require(sha(spec['eligibility'])==sha(frozen) and eligibility['inventory_sha256']==sha(original),
                'unchanged original statement-score ruling, no new post-output eligibility')
        previous={r['row_index']:(r['bank'],r['row'])for r in read(original)['rows']}
        require(all(previous[r['row_index']]==(r['bank'],r['row'])for r in inventory['rows']),
                'same original row identity after frozen reduction')
    require(inventory['experiment'] == index['experiment'] == 'E95'
            and inventory['reduction_step'] == index['reduction_step']
            and index['seed'] == 20261028, 'frozen matching scope and subsample')
    expected = universe(inventory['rows'])
    from .stage_complete import admission as stage_admission
    stage_eligible = stage_admission(spec,expected)
    require(len(expected) == index['total_universe'], 'complete per-row cell universe')
    require(index['total_selected'] == round(.30*len(expected))
            and index['total_old_rubric'] == round(.25*index['total_selected']),
            '30% fixed judge sample and 25% original-rubric sample')
    selected, original = set(), set()
    for stratum, units in index['selected'].items():
        require(len(units) == len(set(units)), 'unique selected units')
        selected.update(group_id(stratum, unit) for unit in units)
        old = index['old_rubric_selected'][stratum]
        require(set(old) <= set(units), 'old-rubric sample nested in judge sample')
        original.update(group_id(stratum, unit) for unit in old)
    require(selected <= set(expected) and len(selected) == index['total_selected']
            and len(original) == index['total_old_rubric'], 'fixed sampled identities')
    audit = read(spec['regex_audit'])
    require(audit['inventory_sha256'] == spec['inventory_sha256']
            and audit['index_sha256'] == spec['index_sha256'], 'regex binds frozen bank/index')
    codes = audit['records']
    unresolved = unresolved_statement_ids(codes, expected, eligibility)
    wanted = selected & unresolved & stage_eligible
    if 'judging_stage' in spec:
        from .judging_stages import partition
        wanted = partition(wanted, expected, spec['judging_stage'])
    packet = Path(spec['packet'])
    seal = verify(packet/'PACKET_SEAL.json', spec['packet_seal_sha256'])
    require(seal['experiment'] == 'E95' and seal['inventory_sha256'] == spec['inventory_sha256']
            and seal['index_sha256'] == spec['index_sha256']
            and seal['regex_audit_sha256'] == spec['regex_audit_sha256'], 'complete packet binding')
    require(seal['stage_inventory_sha256']==spec['stage_inventory_sha256'],'packet closed-stage coverage binding')
    if 'judging_stage' in spec:
        require(seal.get('judging_stage') == spec['judging_stage'], 'exact staged packet binding')
    groups = read(packet/'GROUPED_PACKET.json')
    if groups:
        e87.validate_source(groups)
    require({x['id'] for x in groups} == wanted and len(groups) == len(wanted),
            'judge exactly the preselected regex-unresolved records')
    old_ids = read(packet/'ORIGINAL_IDS.json')
    require(len(old_ids) == len(set(old_ids)) and set(old_ids) == original & wanted,
            'unchanged fixed original-rubric comparison IDs')
    require((packet/'RUBRIC.txt').read_bytes() == e87.RUBRIC.read_bytes()
            and seal['rubric_sha256'] == sha(e87.RUBRIC), 'existing §202 rubric unchanged')
    receipt = read(spec['custody_receipt'])
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified') is True
            and receipt.get('experiment') == 'E95'
            and receipt['packet_seal_sha256'] == spec['packet_seal_sha256']
            and receipt['inventory_sha256'] == spec['inventory_sha256']
            and receipt['index_sha256'] == spec['index_sha256']
            and receipt.get('row_and_index_commit_before_first_call_verified') is True
            and receipt.get('source_seals'), 'verified output custody and before-call commitments')
    for entry in receipt['source_seals']:
        verify(entry['path'], entry['sha256'])
    budget_gate(read(spec['budget_receipt']), spec['first_pass_worst_case_usd'])
    # Preserve E87's renderer, wire, classification and schema; only admission is E95-specific.
    rendered = [dict(id=x['id'], rubric=e87.render_record(
        dict(id=x['id'], property=x['property'], values=x['values'], readout=''),
        e87.RUBRIC.read_text())['rubric'], positions=x['positions']) for x in groups]
    return rendered, old_ids
