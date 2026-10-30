"""CPU-source to judge-wire values: strings are atomic, never iterables of aliases."""
from projects.g_agreement.readerbench.scoring import require

def encode(values):
    require(type(values)is dict and len(values)>=2,'complete literal source value map')
    require(all(type(v)is str and bool(v) for v in values.values()),'whole original source strings required')
    return {k:[values[k]]for k in sorted(values)}

def assert_encoded(actual,original):
    require(actual==encode(original),'every unit value must equal a singleton whole original source string')

def e140_unit(uid,property_text,readout,x,y):
    require(type(readout)is str,'literal native text, empty retained')
    return dict(id=uid,property=property_text,values=encode({'X':x,'Y':y}),readout=readout)
