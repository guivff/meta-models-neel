from decimal import Decimal
import json,pathlib
p=pathlib.Path(__file__).parent
r=json.loads((p/'RECONCILIATION.json').read_text())
rows=[json.loads(x) for x in (p.parents[1]/'compute.jsonl').read_text().splitlines()]
pods={x['pod_id'] for x in r['pods']}
closed=[x for x in rows if x.get('experiment')=='E106' and x.get('pod_id') in pods and Decimal(str(x.get('gpu_usd',0)))>0]
adj=[x for x in rows if x.get('event')=='e106_provider_actual_billing_reconciliation']
assert len(closed)==6 and len(adj)==1
net=sum((Decimal(str(x['gpu_usd'])) for x in closed+adj),Decimal(0))
actual=sum((Decimal(x['actual_billed_usd']) for x in r['pods']),Decimal(0))
assert net==actual==Decimal(r['net_booked_spend_after_adjustment_usd'])
assert sum((Decimal(str(x.get('non_gpu_upper_usd',0))) for x in closed+adj),Decimal(0))==0
assert len(pods)==6 and r['judging_actual_usd']=='0'
print('PASS six pods booked net equals provider actual; contingency net0; no new run')
