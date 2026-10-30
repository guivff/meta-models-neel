"""Registered E140 E104 value-code adaptation; four blind fields only."""
import json,hashlib,re
from .transport import SHARED
from .banks import object_schema,rendered,validate_schema,opaque
from projects.g_agreement.readerbench.io import sha
from projects.g_agreement.readerbench.scoring import require
BASE=SHARED/'E104/blind/RUBRIC.md'
BASE_SHA='03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'
CATEGORIES=['states_value','names_property_without_value','exhibits','silent']


def rubric():
    require(sha(BASE)==BASE_SHA,'original frozen E104 rubric')
    old=BASE.read_text();needle='`values` is `["A"]`, `["B"]`, or `["A","B"]`.'
    require(old.count(needle)==1,'literal original E104 stating rule')
    old=old.replace('frozen A/B order','frozen X/Y order').replace('A negated assertion of A is not an assertion of A; credit B only if it explicitly entails B','A negated assertion of X is not an assertion of X; credit Y only if it explicitly entails Y')
    return old.replace(needle,'`values` is a nonempty subset of ["X","Y","OTHER"]. X and Y are the two supplied value descriptions. OTHER means an explicitly asserted different value of this same property; use OTHER only with verbatim evidence naming that other value. Keep every asserted value, including multiple incompatible values.')


def value_call140(unit,protocol=None):
    require(set(unit)=={'id','property','values','readout'},'E104 only opaque ID/property/value descriptions/readout; no prompt or roles')
    require(re.fullmatch('[0-9a-f]{32,64}',unit['id'])is not None and type(unit['property'])is str and type(unit['readout'])is str,'literal blind descriptor')
    require(set(unit['values'])=={'X','Y'}and all(type(v)is list and v and all(type(x)is str and x for x in v)for v in unit['values'].values()),'exact two approved literal value descriptions')
    record=dict(type='object',additionalProperties=False,required=['id','category','values','evidence'],properties=dict(id=dict(type='string'),category=dict(type='string',enum=CATEGORIES),values=dict(type='array',items=dict(type='string',enum=['X','Y','OTHER'])),evidence=dict(type='string')))
    schema=object_schema('e140_blind_values',dict(records=dict(type='array',items=record)))
    canonical={k:unit[k]for k in ['id','property','values','readout']};canonical['values']={k:unit['values'][k]for k in('X','Y')}
    call=dict(id=opaque('E140','judging',unit['id']),phase='judging',rendered=dict(system=rubric(),user=json.dumps([canonical],ensure_ascii=False),schema=schema))
    def validate(value):
        validate_schema(value,schema['schema']);require(len(value['records'])==1,'one original record');r=value['records'][0]
        require(r['id']==unit['id']and len(r['values'])==len(set(r['values'])),'exact opaque ID/unique set')
        require(bool(r['values'])if r['category']=='states_value'else not r['values'],'original E104 stating/nonstating categories')
        require((r['evidence']==''if r['category']=='silent'else bool(r['evidence']))and r['evidence']in unit['readout'],'verbatim E104 evidence')
    return call,validate

