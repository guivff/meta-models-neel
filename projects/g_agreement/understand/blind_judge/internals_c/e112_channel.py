"""Prospective E112 family adapter; existing E80 renderer/scorer bytes unchanged.

Bank registration is process-local, in a new worker only. Executing C/B files,
their ledgers and their module dictionaries in other processes are untouched.
"""
from decimal import Decimal
from . import transport
from .banks import opaque,rendered
from ..e80_channel import wire_for,valid_response
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require

CAP=Decimal('3')


def register_process_cap():
    """Call in a new E112 worker before snapshot(new_banks=['E112'])."""
    source=transport.HERE/'E112_SOURCE_SEAL.json'
    for name,digest in read(source)['files'].items():require(sha(transport.ROOT/name)==digest,'prospective E112 source pin')
    require(transport.CAPS.get('E112',CAP)==CAP,'no E112 cap override')
    transport.CAPS['E112']=CAP


def family_call(ident,packet,sample,protocol,renderer):
    require(packet['headline_scorer']!='regex','regex family stays CPU; no API call')
    wire=wire_for(packet,sample,protocol,renderer)
    call=dict(id=opaque('E112','family',ident),phase='judging',
        rendered=rendered(wire['messages'],wire['response_format']['json_schema']))
    require(transport.frozen_wire(call,protocol)==wire,'exact original E80 family wire/settings')
    return call,lambda value:valid_response(value,packet)


def validate_grid(records,packets):
    require(len(packets)==518 and len(records)==1036 and len({x['id']for x in records})==1036,'all518x2 new readouts')
    seen=set()
    for x in records:
        require(set(x)=={'id','item_id','reader','layer','readout'} and x['item_id']in packets and
            x['reader']in ('oracle','nla') and x['layer']==(44 if x['reader']=='oracle' else 42) and
            type(x['readout'])is str,'CPU source metadata/readout grid')
        key=(x['item_id'],x['reader']);require(key not in seen,'one greedy readout per item/reader');seen.add(key)
    require(seen=={(i,r)for i in packets for r in ('oracle','nla')},'same original518 items both readers')


class E112Transport(transport.Transport):
    def __init__(self,input_seal,input_sha256,admission,key):
        source=transport.HERE/'E112_SOURCE_SEAL.json'
        register_process_cap()
        require(admission['bank']=='E112' and Decimal(str(admission['allocation_usd']))==CAP and
            admission['E112_source_seal_sha256']==sha(source),'separate registered3 and source-bound E112 admission')
        super().__init__(input_seal,input_sha256,admission,key)
