"""§217 operational handling; frozen rubrics/routes remain unchanged."""
from copy import deepcopy
from .wmech2_channel import response_audit
from .judgment_adapter402 import adapt_grid
from projects.g_agreement.readerbench.scoring import require


def audit_response(saved,protocol):
    finish=saved.get('response',{}).get('choices',[{}])[0].get('finish_reason')
    if finish!='length':return response_audit(saved,protocol)
    # Reuse all route/charge checks while preserving the actual saved response.
    checked=deepcopy(saved);checked['response']['choices'][0]['finish_reason']='stop'
    audit=response_audit(checked,protocol)
    return dict(audit,finish_reason='length',terminal_unparseable=True)


def truncated(items):
    return [dict(id=x['id'],status='UNPARSEABLE',code=None,terminal_reason='CHARGED_LENGTH') for x in items]


def judge(items,send):
    results={}
    for start in range(0,len(items),4):
        batch=items[start:start+4]
        rows=send(batch,0)
        require([x['id'] for x in rows]==[x['id'] for x in batch],'complete ordered batch')
        for x in rows:results[x['id']]=dict(x,attempts=0)
    for item in items:
        row=results[item['id']]
        if row['status']=='KEPT' or row.get('terminal_reason')=='CHARGED_LENGTH':continue
        for attempt in (1,2):
            row=dict(send([item],attempt)[0],attempts=attempt);results[item['id']]=row
            if row['status']=='KEPT' or row.get('terminal_reason')=='CHARGED_LENGTH':break
        if row['status']!='KEPT':row.update(status='UNPARSEABLE',code=None)
    return [results[x['id']] for x in items]


def adapt(terminal,items):
    # The older adapter requires two schema retries for all missing entries.
    # Only its validation view uses that sentinel; actual attempts are retained.
    view=deepcopy(terminal)
    for row in view:
        if row.get('terminal_reason')=='CHARGED_LENGTH':
            require(row['status']=='UNPARSEABLE' and row['code'] is None,'terminal charged length')
            row['attempts']=2
    flat,audit=adapt_grid(view,items)
    for record,original in zip(audit,terminal):
        record['attempts']=original['attempts']
        if original.get('terminal_reason'):record['terminal_reason']=original['terminal_reason']
    return flat,audit
