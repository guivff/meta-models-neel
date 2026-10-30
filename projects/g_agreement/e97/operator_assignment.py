"""mk_assign_r.py <spec.json> <pod_id> <createdAt ISO> <out> : fill a joint9-rerun shard assignment from the READY request schema.
Fills pod_id, provider createdAt (exact), the deadline field the request names (formula from the spec: staging start = createdAt,
deadline = createdAt + staging_cap + cap unless the request gives another), assets, daily_budget_verified, projected_daily_USD.
Projection = spend_today + remaining worst case of every shard in this spec's block (staging_cap + cap each, minus elapsed) at
USD 5.29/h; > 150 refuses. Validated with the request's own check function when the spec names one."""
import json,sys,os,subprocess,re,time,hashlib,importlib
from datetime import datetime
sp,pod,ct,out=json.load(open(sys.argv[1])),sys.argv[2],sys.argv[3],sys.argv[4]
R=os.path.dirname(os.path.abspath(__file__)); SP=os.path.dirname(R)
created=datetime.fromisoformat(ct.replace('Z','+00:00')).timestamp()
txt=subprocess.run([sys.executable,'-I',SP+'/spend_today.py'],capture_output=True,text=True).stdout
T=float(re.search(r'= USD ([0-9.]+) of',txt).group(1)); now=time.time(); RATE=5.29; rem=0.
for u,full in sp['block_worst_seconds'].items():
    pf=f"{R}/run_{u}/pod.id"; el=now-float(open(pf).read().split()[1]) if os.path.exists(pf) else 0.
    rem+=max(0.,full-el)
GATE=sp.get('daily_gate_USD',150); proj=round(T+rem*RATE/3600,2); assert proj<=GATE, f'PROJECTED_OVER_GATE {proj} > {GATE}'
a=dict(sp['assignment_schema'])
NOW5=now-5; HSE=float(open(f"{R}/run_{sp['unit']}/pod.id").read().split()[3]) if os.path.exists(f"{R}/run_{sp['unit']}/pod.id") else created+sp['cap']+300
dl=eval(sp['deadline_formula'],{},{'created':created,'cap':sp['cap'],'staging_cap':sp['staging_cap'],'now':NOW5})
a.update(pod_id=pod,pod_created_epoch=created,provider_createdAt=ct,staging_start_epoch=created,
         assets={'path':sp['assets_path'],'sha256':hashlib.sha256(open(sp['assets_local'],'rb').read()).hexdigest()},
         daily_budget_verified=True,projected_daily_USD=proj,
         daily_budget_basis={'spend_today_USD':T,'block_remaining_worst_seconds':round(rem,1),'rate_USD_per_h':RATE,'gate_USD':GATE,'verified_epoch':now})
for k in sp['deadline_keys']: a[k]=dl
for k,v in sp.get('assignment_extra',{}).items(): a[k]=created if v=='@@created' else created+sp['staging_cap'] if v=='@@staged' else dl-sp['cap'] if v=='@@dlstart' else NOW5 if v=='@@now' else HSE if v=='@@hardstop' else (json.load(open(v[1:])) if isinstance(v,str) and v.startswith('@') else v)
def validate_placeholders(assignment, spec):
    for key, value in assignment.items():
        if key == 'experiment' and value == 'E97_CAPTURE_V2' and value == spec['assignment_schema']['experiment']:
            continue
        assert not (isinstance(value, str) and value.isupper() and '_' in value), ('unfilled placeholder', key, value)
validate_placeholders(a, sp)
c=sp.get('check')
if c:
    for d in c['path']: sys.path.insert(0,d)
    m=importlib.import_module(c['module']); args=[a]+[json.load(open(x)) for x in c.get('json_args',[])]+list(c.get('str_args',[])); getattr(m,c['fn'])(*args)
json.dump(a,open(out,'w'),indent=1,sort_keys=True)
print(f"ASSIGNMENT_OK {sp['unit']} cap {sp['cap']} deadline-created {dl-created:.1f} projected USD {proj}")
