"""Prospective §221 complete hallucination-audit phase: CPU exact-wire inventory.
No API, sampling, scoring, source repair, booking or replay of GPU controllers.
"""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import sys,json,hashlib,os
R=Path.cwd();H=R/'cache/g_agreement/i2/e99_judge_cpu_v1';OUT=R/'cache/g_agreement/i2/e99_phase1_section221_v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main():
 os.umask(0o077);assert not OUT.exists()
 plan=read(R/'results/g_agreement/i2/E99_SECTION221_PHASE_PLAN.json');assert sha(H/'CALL_DAG.PRIVATE.json')==plan['phase1_original_DAG_sha256']
 d=read(H/'CALL_DAG.PRIVATE.json');wanted=[x['id']for x in d['calls']if x['family']=='hallucination'and x['stage']=='audit'];assert len(wanted)==6680
 sys.path.insert(0,str(R/'cache/g_agreement/i2/publication'))
 from projects.g_agreement.understand.blind_judge.e99_families import Renderers
 from projects.g_agreement.understand.blind_judge.e99_channel import frozen_wire,validate_wire_privacy
 from projects.g_agreement.understand.blind_judge import run
 renderer=Renderers();source={x['id']:x for x in renderer.sidecar('shared_private_items')};bindings=read(H/'SOURCE_BINDINGS.PRIVATE.json');oldhash=read(H/'WIRE_HASHES.PRIVATE.json')
 route=read(R/'cache/g_agreement/i2/publication/results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,privacy,protocol,io=run.route_modules(route)
 by={};wires={};blocks=[];total=Decimal(0)
 for name,digest in bindings['job_files'].items():
  assert sha(name)==digest
  for x in read(name):
   if x['family']!='hallucination':continue
   item=source[x['paired_capture_id']]['source_item'];sites={s['pos']:s for s in item['sites']}
   rendered=renderer.render('hallucination','audit',item=item,site=sites[x['position']],readout=x['text']);wire=frozen_wire(rendered,protocol);ident=hashlib.sha256(('E99|'+x['id']+'|audit').encode()).hexdigest()[:32];wh=hashlib.sha256(io.canonical(wire).encode()).hexdigest();assert oldhash[ident]==wh and ident not in by
   by[ident]=dict(id=ident,family='hallucination',stage='audit',rendered=rendered);wires[ident]=wh;total+=api.upper(wire)
   try:validate_wire_privacy(wire,privacy.check_wire)
   except(ValueError,AssertionError)as e:blocks.append(dict(id=ident,error_type=type(e).__name__,error_sha256=hashlib.sha256(str(e).encode()).hexdigest()))
 assert set(by)==set(wanted)and total==Decimal(plan['phase1_full_exact_initial_wire_forecast_upper_usd'])
 OUT.mkdir()
 for n,v in [('CALLS.PRIVATE.json',[by[i]for i in wanted]),('WIRE_HASHES.PRIVATE.json',wires),('PRIVACY_BLOCKS.PRIVATE.json',blocks)]:
  with(OUT/n).open('x')as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
 audit=dict(at_utc=datetime.now(timezone.utc).isoformat(),phase1_calls=len(wanted),exact_original_wire_hash_matches=len(wires),forecast_upper_usd=str(total),phase1_cap_usd=150,privacy_blocked_records=len(blocks),source_plan_sha256=sha(R/'results/g_agreement/i2/E99_SECTION221_PHASE_PLAN.json'),private_files={n:sha(OUT/n)for n in ['CALLS.PRIVATE.json','WIRE_HASHES.PRIVATE.json','PRIVACY_BLOCKS.PRIVATE.json']},no_calls_or_reservations=True,status='CPU_EXACT_PHASE1_WIRES_ONLY_NOT_ADMISSION')
 (R/'results/g_agreement/i2/E99_SECTION221_PHASE1_CPU_PREFLIGHT.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit))
if __name__=='__main__':main()
