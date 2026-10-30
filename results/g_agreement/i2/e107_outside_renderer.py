"""Prospective source-bank rubric rendering for new E107 outside descriptions only.
Draft helper: not a frozen judge plan or dispatch admission. Source bank rubric
bindings, original-rubric comparison scope and exact future wires remain pending.
No calls, sampling, source text repair, native rescoring, or scientific inference.
"""
import hashlib


def call_id(inventory_id, target):
    return hashlib.sha256(('E107|outside_judge|'+inventory_id+'|'+target).encode()).hexdigest()[:32]


def validate_plan(plan):
    assert set(plan)=={'inventory_id','bank','target','property','values'}
    assert plan['bank'] in ('E81','E82','E86')
    assert plan['target'] in ({'S'} if plan['bank']=='E81' else {'truth'} if plan['bank']=='E86' else {'belief','truth'})
    assert isinstance(plan['property'],str) and plan['property']
    assert set(plan['values'])=={'A','B'} and plan['values']['A']
    assert plan['values']['B'] or (plan['bank']=='E82' and plan['target']=='belief')


def render_outside(plans, generated, rubrics, render_record):
    """Use the entire actual outside text; never substitute a native position."""
    by={x['id']:x for x in generated}
    assert len(by)==len(generated) and set(by)=={x['inventory_id']for x in plans}
    assert len({(x['inventory_id'],x['target'])for x in plans})==len(plans)
    output=[]
    for plan in plans:
        validate_plan(plan)
        source=by[plan['inventory_id']]
        assert source['phase']=='generation' and source['status']=='GENERATED'
        assert source['finish_reason'] in ('stop','length') and isinstance(source['text'],str)
        assert source.get('refusal') is None, 'preserve refusal; coordinator diagnosis before scoring'
        item=dict(id=call_id(plan['inventory_id'],plan['target']),property=plan['property'],
                  values=plan['values'],readout=source['text'])
        rendered=render_record(item,rubrics[plan['bank']])
        assert set(rendered)=={'id','rubric','readout'} and rendered['readout']==source['text']
        output.append(dict(bank=plan['bank'],target=plan['target'],record=rendered))
    return output
