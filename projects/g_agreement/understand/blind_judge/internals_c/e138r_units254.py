"""E138 deviation2 correction: same168 source readouts, whole literal values."""
from .phases253 import v_units
from .whole_values254 import encode,assert_encoded
from .banks import opaque
from projects.g_agreement.readerbench.scoring import require

def assert_all(units,joins):
    by={j['id']:j for j in joins};require(len(units)==len(by)==168,'same original168 identities')
    for u in units:
        j=by[u['id']];assert_encoded(u['values'],{j['recipient_letter']:j['recipient_old'],j['donor_letter']:j['donor_old']})

def build():
    old,joins,sources=v_units();by={j['id']:j for j in joins};units=[];pointers=[]
    for u in old:
        j=by[u['id']];uid=opaque('E138R',j['native_id']);raw={j['recipient_letter']:j['recipient_old'],j['donor_letter']:j['donor_old']}
        units.append(dict(id=uid,property=u['property'],values=encode(raw),readout=u['readout']))
        pointers.append(dict(j,id=uid,defective_E138_unit_id=u['id']))
    assert_all(units,pointers)
    require([u['readout']for u in units]==[u['readout']for u in old],'all same168 original readout strings unchanged')
    return units,pointers,sources
