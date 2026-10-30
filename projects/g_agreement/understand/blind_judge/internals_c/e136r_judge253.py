"""E136 deviation3: exact owner readout-only wire; no source prompt accepted."""
import json
from projects.g_agreement.e136_named import named
from .banks import object_schema,rendered,opaque,validate_schema
from projects.g_agreement.readerbench.scoring import require
QUESTIONS=named.QUESTIONS


def readout_call(unit,protocol=None):
    require(set(unit)=={'id','readout','cue'},'ONLY opaque ID/readout and CPU question selector; source prompt forbidden')
    require(type(unit['id'])is str and type(unit['readout'])is str and unit['cue']in QUESTIONS,'exact registered readout-only descriptor')
    messages=named.messages(unit['id'],unit['readout'],unit['cue'])
    require(json.loads(messages[1]['content'])==dict(id=unit['id'],readout=unit['readout']),'ONLY ID/readout in user payload')
    require(messages[0]['content']==named.SYSTEM+'\nQuestion: '+QUESTIONS[unit['cue']],'ONLY fixed owner instruction and exact cue question in system')
    schema=object_schema('cue_named',dict(code=dict(type='string',enum=['YES','NO','UNPARSEABLE']),evidence=dict(type='string')))
    call=dict(id=opaque('E136R','judging',unit['id']),phase='judging',rendered=rendered(messages,schema))
    def validate(value):validate_schema(value,schema['schema']);named.validate(value,unit['readout'])
    return call,validate


def assert_readout_only(call,unit):
    expected,_=readout_call(unit)
    require(call['rendered']==expected['rendered'],'exact owner readout-only renderer, no extra bytes')
    data=json.loads(call['rendered']['user']);require(set(data)=={'id','readout'},'no source prompt/labels/conditions/probes/tasks')
    return True
