"""Pure custody helpers, tested before any corrected preload launch."""
import math


def native_identity(environ_bytes):
    fields=dict(p.split(b'=',1) for p in environ_bytes.split(b'\0') if b'=' in p)
    return fields.get(b'RUNPOD_POD_ID',b'').decode()


def cap_valid(assignment):
    prior=assignment.get('prior_seconds',0);cap=assignment['cap_seconds']
    return (all(isinstance(v,(int,float)) and math.isfinite(v) for v in (prior,cap))
       and prior>=0 and cap>0 and prior+cap<=1440
       and assignment['absolute_deadline_epoch']==assignment['pod_created_epoch']+cap)


def stop_result(data,pod):
    value=data['podStop']
    if value['id']!=pod:raise ValueError('wrong exact-ID stop receipt')
    return value
