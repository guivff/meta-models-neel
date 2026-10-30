"""Lossless E104 producer-record validation; no scoring or denominator choice."""
from projects.g_agreement.e127_analysis.common import require

CATEGORIES = ('states_value', 'names_property_without_value', 'exhibits', 'silent')
VALUES = ('X', 'Y', 'OTHER')


def preserve_record(judgment, native_text):
    """Validate the original terminal wrapper and return all recorded values.

    Connected under §252 clarification 2; analysis uses the preserved set.
    Never reparse text or choose a tie-break.
    """
    require(type(judgment) is dict and type(native_text) is str, 'literal source records')
    require(type(judgment.get('id')) is str and bool(judgment['id']), 'original opaque identity')
    require(judgment.get('status') in ('KEPT', 'UNPARSEABLE'), 'terminal disposition')
    code = judgment.get('code')
    if judgment['status'] == 'UNPARSEABLE':
        require(code is None, 'terminal missing must remain null')
        return None
    require(type(code) is dict and set(code) == {'id', 'category', 'values', 'evidence'}, 'exact producer code fields')
    require(code['id'] == judgment['id'], 'original nested code identity')
    require(code['category'] in CATEGORIES and type(code['values']) is list, 'original category/value array')
    values = code['values']
    require(all(type(v) is str and v in VALUES for v in values), 'literal X/Y/OTHER alphabet')
    require(len(values) == len(set(values)), 'unique asserted values')
    require(bool(values) == (code['category'] == 'states_value'), 'original stating convention')
    evidence = code['evidence']
    require(type(evidence) is str and evidence in native_text, 'original verbatim evidence')
    require(evidence == '' if code['category'] == 'silent' else bool(evidence), 'original evidence convention')
    return dict(id=code['id'], category=code['category'], values=list(values), evidence=evidence)
