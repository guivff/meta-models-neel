"""§177 fixed selection and lossless readout export; no best-example selection."""
import json
import numpy as np


def select_three(ids):
    ids=sorted(ids)
    if len(ids)!=len(set(ids)) or len(ids)<3:raise ValueError('three distinct test items required')
    rng=np.random.default_rng(20261027)
    return [ids[0]]+rng.choice(ids[1:],size=2,replace=False).tolist()


def verbatim_records(records,unit_ids):
    chosen=[]
    for unit in unit_ids:
        for reader in ('oracle','nla'):
            group=[x for x in records if x['unit_id']==unit and x['reader']==reader]
            if len(group)!=1 or {x['repeat'] for x in group}!=set(range(1)):
                raise ValueError('DISPLAY_NOT_ACQUIRED: '+unit+' '+reader+'; do not substitute another item')
            for x in sorted(group,key=lambda x:x['repeat']):
                if not isinstance(x.get('raw'),str):raise ValueError('raw verbatim readout missing')
                chosen.append(dict(x))
    return chosen


def display_html(title,records):
    import html
    # HTML <pre> escapes rendering syntax while preserving every raw character.
    return '<!doctype html><meta charset="utf-8"><title>'+html.escape(title)+'</title><h1>'+html.escape(title)+'</h1>'+''.join('<h2>'+html.escape(x['unit_id']+' / '+x['reader']+' / '+str(x['repeat']))+'</h2><pre>'+html.escape(x['raw'])+'</pre>' for x in records)


def injection_display(records,items,probe_scores):
    selected=[x for x in items if x['row']=='prose_sentiment']
    if {(x['variant'],x['arm']) for x in selected}!={(v,a) for v in ('A','B') for a in ('full','J','nonJ')}:raise ValueError('two directions by three arms')
    ids=[x['id'] for x in sorted(selected,key=lambda x:x['id'])]
    if set(probe_scores)!=set(ids):raise ValueError('six frozen injected-vector probe scores required')
    return {'readouts':verbatim_records(records,ids),'probe_scores':probe_scores,'independent_directions':2}
