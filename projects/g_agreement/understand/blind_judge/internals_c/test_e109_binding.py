import hashlib
from copy import deepcopy
import pytest
from .e109_binding import code_refs, resolve_redaction


def test_kept_codes_direct_and_missing_original_null_unchanged():
    judgments = [dict(id='a', kind='value', status='KEPT', code=dict(id='a', category='silent', values=[], evidence='')),
                 dict(id='b', kind='value', status='UNPARSEABLE', code=None)]
    before = deepcopy(judgments)
    sentinels = []
    refs = code_refs(judgments, ['a', 'b'], 1, 'primary', sentinels)
    assert judgments == before
    assert refs['a'] == dict(seal_index=1, member='JUDGMENTS.json', keys=[0, 'code'])
    assert sentinels[0]['original_code']['keys'] == [1, 'code']
    assert sentinels[0]['code'] == dict(id='b', category='UNPARSEABLE', values=[], evidence='')
    assert refs['b']['keys'] == [0, 'code']
    from projects.g_agreement.understand.wmech2.core import score
    assert score(sentinels[0]['code'], 'A', 'Original text.') is None


def test_incomplete_duplicate_or_wrong_identity_fails_closed():
    good = dict(id='a', kind='value', status='KEPT', code=dict(id='a'))
    for rows in ([], [good, good], [dict(good, code=dict(id='b'))]):
        with pytest.raises(ValueError):
            code_refs(rows, ['a'], 1, 'primary', [])


def test_no_missing_as_silent_or_failed_code_reinterpretation():
    with pytest.raises(ValueError):
        code_refs([dict(id='a', kind='value', status='UNPARSEABLE', code=dict(id='a'))], ['a'], 1, 'primary', [])


def test_redaction_maps_only_exact_opaque_source_and_original_text_hash():
    text = 'A saved original readout.'
    audit = dict(authority='79f63fe0', redacted_records=1,
                 affected=[dict(id='opaque', original_readout_sha256=hashlib.sha256(text.encode()).hexdigest())])
    joins = [dict(id='opaque', row='fact_recall', layer=44, condition='steered', item_id='original')]
    result = resolve_redaction(audit, joins, lambda join: text)
    assert result['affected_readouts'] == [dict(row='fact_recall', layer=44, condition='steered', item_id='original')]
    with pytest.raises(ValueError):
        resolve_redaction(audit, joins, lambda join: text+' changed')
    with pytest.raises(ValueError):
        resolve_redaction(audit, [], lambda join: text)
