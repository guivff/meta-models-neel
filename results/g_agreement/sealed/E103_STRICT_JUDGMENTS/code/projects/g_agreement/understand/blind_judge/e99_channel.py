"""E99 transport adapter: caller must bind W-text's frozen renderer before calls.

The frozen renderer supplies system/user/schema. This module adds only the E56
transport settings and records refusals/failures; it cannot invent prompts.
"""
import argparse
from pathlib import Path
from .run import payload
from .e99_accounting import check_wire,classify_transport,summarize
from .e80_channel import valid_response
from .privacy79 import strings
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def frozen_wire(rendered,protocol):
    require(set(rendered) in ({'system','user','schema'},{'system','user','schema','response_format'}),'exact frozen renderer output')
    require((rendered['system'] is None or type(rendered['system']) is str) and type(rendered['user']) is str,'literal prompt strings')
    wire=payload([], '', 'E56',protocol)
    wire['messages']=([dict(role='system',content=rendered['system'])] if rendered['system'] is not None else [])+[dict(role='user',content=rendered['user'])]
    if rendered['schema'] is None:
        require(rendered.get('response_format') in ('text','source prompt JSON, parsed by original parse_design_score'),'frozen plain-text contract')
        wire.pop('response_format')
    else:wire['response_format']={'type':'json_schema','json_schema':rendered['schema']}
    check_wire(wire)
    return wire


def validate_wire_privacy(wire,privacy_check):
    check_wire(wire)
    for value in strings(wire['messages']):
        privacy_check('extract',[dict(id='opaque',readout=value)],wire)


def terminal_record(call_id,http_status,body,rendered,validator=None):
    """Record transport refusal separately from schema/evidence failure."""
    import json
    record=classify_transport(http_status,body)
    if record['status']!='VALIDATE':return dict(id=call_id,**record)
    try:
        content=body['choices'][0]['message']['content']
        if rendered['schema'] is None:
            require(type(content) is str,'plain text response')
            value=content
        else:
            value=json.loads(content)
            valid_response(value,{'schema':rendered['schema']})
        if validator is not None:validator(value)
    except (ValueError,KeyError,TypeError,AssertionError):
        return dict(id=call_id,status='UNPARSEABLE',reason='FROZEN_SCHEMA_OR_EVIDENCE_FAILED')
    return dict(id=call_id,status='KEPT',result=value)


def main():
    p=argparse.ArgumentParser(description='E99 offline accounting only; no API key or inference')
    p.add_argument('--grid',type=Path,required=True);p.add_argument('--grid-sha256',required=True)
    p.add_argument('--terminal',type=Path,required=True);p.add_argument('--terminal-sha256',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(sha(a.grid)==a.grid_sha256 and sha(a.terminal)==a.terminal_sha256,'sealed accounting inputs')
    grid=read(a.grid);result=summarize(grid['cells'],grid['calls'],read(a.terminal))
    require(not a.out.exists(),'never overwrite accounting receipt');write(a.out,result)

if __name__=='__main__':main()
