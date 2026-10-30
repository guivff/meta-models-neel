from pathlib import Path
from copy import deepcopy
import pytest
from . import e124_channel as c
from .test_e124_amendment1_judge import units
from projects.g_agreement.readerbench.io import read, write, sha, verify


def test_report_source_pending_blocks_prepare_before_any_owner_or_api_access(tmp_path, monkeypatch):
    source = tmp_path/'SOURCE.json'
    write(source, dict(report_adapter_pinned=False))
    monkeypatch.setattr(c, 'SOURCE', source)
    monkeypatch.setattr(c, 'source_gate', lambda: None)
    with pytest.raises(ValueError, match='owner report source must be frozen'):
        c.prepare(None, None)


def test_literal_registered_behavior_source_reference_required(tmp_path):
    rows = units()
    write(tmp_path/'RAW.json', rows)
    write(tmp_path/'SEAL.json', dict(files={'RAW.json': sha(tmp_path/'RAW.json')}))
    sources = [dict(seal=str(tmp_path/'SEAL.json'), sha256=sha(tmp_path/'SEAL.json'))]
    custody = dict(registered_behavior_references_verified=True, complete_eligible_grid=True, units=[
        dict(id=u['id'], model_reference_ref=dict(seal_index=0, member='RAW.json', keys=[i, 'model_reference']),
            readout_ref=dict(seal_index=0, member='RAW.json', keys=[i, 'readout'])) for i, u in enumerate(rows)])
    c.verify_unit_refs(rows, custody, sources)
    changed = deepcopy(rows); changed[0]['model_reference'] = 'an unbound replacement'
    with pytest.raises(ValueError): c.verify_unit_refs(changed, custody, sources)
    changed = deepcopy(custody); changed['registered_behavior_references_verified'] = False
    with pytest.raises(ValueError): c.verify_unit_refs(rows, changed, sources)


@pytest.mark.parametrize('failure', [False, True])
def test_complete_physical_phase_binding_or_stop_without_retry(tmp_path, monkeypatch, failure):
    dest = tmp_path/'model_reference_consistency_judging'; dest.mkdir()
    write(dest/'CALLS.json', c.calls_for(units()))
    write(dest/'INPUT_SEAL.json', dict(files={'CALLS.json': sha(dest/'CALLS.json')}))
    write(dest/'ADMISSION.json', dict(bank='E124'))
    source = tmp_path/'SOURCE.json'; write(source, {'synthetic': True})
    monkeypatch.setattr(c, 'SOURCE', source)
    class Fake:
        invoked = []
        def __init__(self, *args):
            self.root = tmp_path/'physical'; self.calls = read(dest/'CALLS.json'); self.routes = {'verified': True}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def summary(self): return dict(actual_usd='.001', unresolved_upper_usd='0')
        def call(self, ident, validator):
            self.invoked.append(ident)
            if failure: raise ValueError('unknown finish stops bank')
            p = self.root/'ledger/E124_judging'/(ident+'.response.json'); p.parent.mkdir(parents=True, exist_ok=True)
            write(p, dict(saved=True))
            # Charged length remains terminal missing; acquire never retries it.
            return dict(id=ident, status='UNPARSEABLE', result=None, request_id=ident, response_sha256=sha(p)), {}
    if failure:
        with pytest.raises(ValueError): c.acquire(dest, {}, Fake, 'synthetic')
        assert len(Fake.invoked) == 1 and not (dest/'outputs/JUDGMENT_SEAL.json').exists()
        assert read(dest/'outputs/STATUS.json')['status'] == 'STOPPED'
    else:
        seal = c.acquire(dest, {}, Fake, 'synthetic'); verify(seal, sha(seal))
        assert read(dest/'outputs/COUNTS.json')['status_counts'] == {'UNPARSEABLE': 2}
        assert all('/E124_judging/' in x['path'] for x in read(dest/'outputs/RAW_RESPONSE_BINDINGS.json'))
        c.acquire(dest, {}, Fake, 'synthetic')
        assert len(Fake.invoked) == 2


def test_separate_cap_cannot_be_borrowed_or_reset():
    for bank, cap in [('E118', '3'), ('E124', '4')]:
        with pytest.raises(ValueError): c.E124Transport(None, None, dict(bank=bank, allocation_usd=cap), 'synthetic')
