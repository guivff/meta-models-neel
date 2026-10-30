"""Copy-only E112 inventory construction under ba760009e; no outcome access."""
from copy import deepcopy

def copy_fields(sources, fields):
    values={}; provenance={}
    for name, ref in fields.items():
        if ref is None:
            values[name]='MISSING';provenance[name]={'status':'MISSING','reason':'No literal pre-output source supplied'};continue
        source,keys=ref
        record=sources[source]
        if not record['pre_output_verified']:raise ValueError('source is not verified pre-output')
        v=record['data']
        try:
            for k in keys:v=v[k]
        except (KeyError,IndexError,TypeError):
            values[name]='MISSING';provenance[name]={'status':'MISSING','source':source,'keys':keys};continue
        values[name]=deepcopy(v)
        provenance[name]={'status':'COPIED','source':source,'keys':keys,'custody':deepcopy(record['custody'])}
    return dict(values=values,provenance=provenance,construction='POST_OUTPUT_COPY_ONLY',authority='ba760009e',outcomes_used=False)
