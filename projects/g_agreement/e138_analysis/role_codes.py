"""Lossless original E104/E127 category-to-role transport, never a text parser."""
from projects.g_agreement.e127_analysis.common import require
ROLES=('recipient-old','donor-old','other')
CATEGORIES=('states_value','names_property_without_value','exhibits','silent')
def normalize(code,status,judgment_id,value_roles):
    require(type(judgment_id)is str and bool(judgment_id),'original judgment identity')
    require(type(value_roles)is dict and set(value_roles) in ({'A','B'},{'A','B','OTHER'}),'explicit original alphabet mapping')
    require(all(v in ROLES for v in value_roles.values()),'explicit source-bound role values')
    if 'OTHER'in value_roles:require(value_roles['OTHER']=='other','OTHER remains other')
    require(status in ('KEPT','UNPARSEABLE'),'original terminal disposition')
    if status=='UNPARSEABLE':
        require(code is None or (type(code)is dict and code.get('id')==judgment_id and code.get('category')=='UNPARSEABLE' and not code.get('values')),'recorded missing only')
        return None
    require(type(code)is dict and code.get('id')==judgment_id,'exact original code identity')
    require(code.get('category')in CATEGORIES and type(code.get('values'))is list,'original E104 category and values')
    vals=code['values'];require(len(vals)==len(set(vals)) and all(v in value_roles for v in vals),'all original values mapped exactly once')
    require(bool(vals)==(code['category']=='states_value'),'stating versus nonstating convention')
    mapped=[value_roles[v]for v in vals]
    require(len(mapped)==len(set(mapped)),'ambiguous many-to-one mapping cannot erase original multiple values')
    return sorted(mapped,key=ROLES.index)
