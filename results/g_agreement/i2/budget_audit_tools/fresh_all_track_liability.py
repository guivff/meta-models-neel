from pathlib import Path
import json,subprocess,datetime,re,hashlib,math,os
root=Path.cwd();oproot=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops');ledger=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6/results/g_agreement/compute.jsonl');log=(oproot/'status.log').read_text();rows=[json.loads(l) for l in ledger.read_text().splitlines() if l.startswith('{')];rows=[r for r in rows if str(r.get('timestamp','')).startswith(('2026-10-28','2026-10-29','2026-10-30')) and r.get('track')=='Q' and isinstance(r.get('usd'),(int,float))];bills={};corrections={}
for r in rows:
 k=r['pod_id']
 if r['event']=='pod_billed':
  if k in bills:assert bills[k]['usd']==r['usd'],'UNEQUAL_DUPLICATE_Q_BILL'
  bills[k]=r
 elif r['event']=='booking_correction':corrections[(k,r['usd'])]=r
 else:raise AssertionError('UNKNOWN_Q_CHARGE_EVENT')
assert all(k[0] in bills for k in corrections);qclosed=sum(r['usd'] for r in bills.values())+sum(r['usd'] for r in corrections.values())
query='query { myself { pods { id name desiredStatus createdAt costPerHr containerDiskInGb volumeInGb } } }';r=subprocess.run(['bash','/Users/guivff/repl/tools/runpod_api.sh',query],capture_output=True,text=True,check=True);api=json.loads(r.stdout);assert not api.get('errors');pods=api['data']['myself']['pods'];running=[p for p in pods if p['desiredStatus']=='RUNNING'];state=json.loads((root/'results/g_agreement/i2/STATUS.json').read_text());known={}
restart_homes=['cache/g_agreement/i2/section212_restarts_v1/e86-a1','cache/g_agreement/i2/section212_restarts_v1/e86-a2','cache/g_agreement/i2/section212_restarts_v1/e82-full-a1']
new_e99_homes=['cache/g_agreement/i2/e99_core_three_production_v1/operator'+str(i)+'-a1' for i in range(4)]
for home in ['cache/g_agreement/i2/e81_serial_production_v1/operator2-a3','cache/g_agreement/i2/e99_core_three_v1/operator-a1','cache/g_agreement/i2/e86_selected_capture_a1']+['cache/g_agreement/i2/e81_serial_production_v1/operator'+str(i)+'-a2' for i in [3,4,5]]+new_e99_homes+restart_homes:
 h=root/home
 if not (h/'ALLOCATION.private.json').exists():continue
 a=json.loads((h/'ALLOCATION.private.json').read_text())
 if a.get('pod_id') and not (h/'CLOSEOUT.json').exists():known[a['pod_id']]=dict(owner='I-2',run_id=a['run_id'],cap_seconds=json.loads((h/'PREPARATION.json').read_text())['cap_seconds'],upper=json.loads((h/'PREPARATION.json').read_text())['gpu_forecast_upper_usd'],provider_created_epoch=a['created_epoch'])
i4gatebase=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i4/results/g_agreement/e102')
i4gate=json.loads((i4gatebase/'STATUS.json').read_text())
if i4gate.get('gpu_reservation_usd',0)>0:
 statepath=Path(i4gate['operator_state']);gate=json.loads(statepath.read_text())
 assert gate['gate_only'] is True and gate['training_admitted'] is False and gate['pod_id']==i4gate['pod_id'] and gate['cap_seconds']==3600 and abs(gate['hard_deadline_epoch']-gate['created_epoch']-3600)<.01
 known[gate['pod_id']]=dict(owner='I-4',run_id=gate['pod_name'],cap_seconds=3600,upper=float(i4gate['gpu_reservation_usd']),gate_only=True,training_admitted=False,provider_created_epoch=gate['created_epoch'],state_sha256=hashlib.sha256(statepath.read_bytes()).hexdigest(),status_sha256=hashlib.sha256((i4gatebase/'STATUS.json').read_bytes()).hexdigest())
i5home=Path('/Users/guivff/repl/activation-readers-i5/e103-core-20261028-a2')
i5state=json.loads((i5home/'STATE.json').read_text());i5budget=json.loads((i5home/'BUDGET.json').read_text());i5auth=json.loads((i5home/'AUTHORIZATION.json').read_text())
assert i5state['pod_id']=='244yq8nxxj3wzb' and i5state['gpu_type']=='H200'
assert abs(i5state['deadline_epoch']-i5state['created_epoch']-11200)<.01 and i5auth['cap_seconds']==11200 and i5budget['new_max_reservation_usd']==26.86
i5closedpath=i5home/'CLOSED.json'
if i5closedpath.exists():
 closed=json.loads(i5closedpath.read_text());assert closed['pod_id']==i5state['pod_id'] and closed['archive_verified'] is True and closed['provider_query_null'] is True
 assert closed['createdAt']==i5state['created_utc'] if 'created_utc' in i5state else closed['createdAt']=='2026-10-28T21:53:09.602Z'
 assert closed['gpu_type']=='H200' and closed['rate']==5.29 and 0<closed['charged_seconds_upper']<11200
 assert all(p['id']!=closed['pod_id'] for p in pods),'CLOSED_I5_POD_STILL_RESOLVABLE'
 current_i5status=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i5/results/g_agreement/status/I-5.md').read_text()
 assert 'Closed I-5 cost **USD23.02' in current_i5status and 'activeGPU/judgereserves0' in current_i5status and 'All five I5pods closed/queryNULL/guardsretired' in current_i5status
if not (i5home/'CLOSEOUT.json').exists() and not i5closedpath.exists():
 known[i5state['pod_id']]=dict(owner='I-5',run_id='mats-i5-e103-core-20261028-a2',cap_seconds=11200,upper=26.86,provider_created_epoch=i5state['created_epoch'],state_sha256=hashlib.sha256((i5home/'STATE.json').read_bytes()).hexdigest(),budget_sha256=hashlib.sha256((i5home/'BUDGET.json').read_bytes()).hexdigest(),authority_commit=i5auth['authorization_commit'])
i4statuspath=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i4/results/g_agreement/e96/STATUS.json');i4rerunstatus=json.loads(i4statuspath.read_text())
if i4rerunstatus.get('rerun_gpu_reserved_usd',0)>0:
 rp=Path(i4rerunstatus['replacement_operator_state']);rs=json.loads(rp.read_text())
 assert rs['pod_id']==i4rerunstatus['replacement_pod_id'] and rs['experiment']=='E96' and rs['slot']==1
 assert rs['attempt'] in ('replacement-once','replacement-second-final')
 if rs['attempt']=='replacement-second-final':
  bindingpath=i4statuspath.parent/i4rerunstatus['second_attempt_binding'];binding=json.loads(bindingpath.read_text())
  assert binding['authority_commit']=='3899e1ea073f8609f33fb35b5ce1863c6223961f' and i4rerunstatus['rerun_authority']=='3899e1ea' and rs['authority_commit']=='3899e1ea'
  assert binding['pod_id']==rs['pod_id'] and binding['created_utc']==rs['created_utc'] and binding['worker_archive_sha256']==rs['archive_sha256']
  assert binding['cap_all_in_usd']==23.16 and binding['cap_gpu_hours']==4 and binding['pool_id']=='section211_amendment1_parked' and binding['admission_shared_commit']=='1497fc92465aba9fa78c11cedb29210635ea7955'
 assert rs['gpu_type']=='H200' and rs['rate']==5.29 and rs['cap_seconds']==14400 and abs(rs['hard_deadline_epoch']-rs['created_epoch']-14400)<.01
 assert i4rerunstatus['rerun_all_in_cap_usd']==23.16 and i4rerunstatus['rerun_pool']=='parked'
 known[rs['pod_id']]=dict(owner='I-4',run_id=rs['pod_name'],cap_seconds=14400,upper=23.16,provider_created_epoch=rs['created_epoch'],pool_id='section211_amendment1_parked',state_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),status_sha256=hashlib.sha256(i4statuspath.read_bytes()).hexdigest())
active=[];parse=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
for pod in running:
 k=pod['id'];assert k not in bills,'BOOKED_POD_STILL_RUNNING'
 if k in known:
  a=known[k]
  if a.get('owner')=='I-2':assert abs(parse(pod['createdAt']).timestamp()-a['provider_created_epoch'])<.01 and 0<float(pod['costPerHr'])<=5.29
  if a.get('owner') in ('I-4','I-5'):assert abs(parse(pod['createdAt']).timestamp()-a['provider_created_epoch'])<.01 and abs(float(pod['costPerHr'])-5.29)<.001
 else:
  matches=re.findall(r'([^\n]+) CREATED '+re.escape(k)+r' createdAt=([^ ]+) hardstop=([^ ]+) backstop=([^ ]+) [^\n]*',log)
  assert matches,'UNKNOWN_LIVE_CAP_'+pod['name'];line,created,hard,back=matches[-1];assert abs((parse(created)-parse(pod['createdAt'])).total_seconds())<.001
  seconds=math.ceil((parse(back)-parse(created)).total_seconds())+60;assert 60<=seconds<=86400
  a=dict(owner='Q',run_id=pod['name'],cap_seconds=seconds,upper=math.ceil((seconds*float(pod['costPerHr'])/3600+2)*100)/100,cap_evidence='original logged backstop minus exact provider creation plus60s conservative clock allowance, plus2USD nonGPU extras')
 if re.match(r'^mats-minis-r-e95-',pod['name']) and parse(pod['createdAt']).timestamp()>=1793224200:
  a['pool_id']='section211_amendment1_parked';a['pool_evidence']='E95 explicitly second in direct §211 amendment1 parked order; actual Q creation/backstop/rate joined after authority'
 active.append(a)
running_known={p['id']for p in running if p['id']in known};uncertain_held=[];pods_by_id={p['id']:p for p in pods}
for k in set(known)-running_known:
 a=dict(known[k]);pod=pods_by_id.get(k)
 assert pod is None or pod['desiredStatus']=='EXITED','KNOWN_CAP_NONRUNNING_STATE_NEEDS_RECONCILIATION'
 if pod is not None:assert abs(parse(pod['createdAt']).timestamp()-a['provider_created_epoch'])<.01
 a.update(provider_state=pod['desiredStatus']if pod else 'QUERY_NULL_OWNER_RESERVATION_STILL_HELD',uncertain_held=True,reason='Provider no longer RUNNING but owner still holds original full cap; carry the whole upper pending exact owner closeout/booking, never treat unreported custody as zero')
 uncertain_held.append(a)
uncertain_upper=sum(a['upper']for a in uncertain_held)
i4=json.loads(Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i4/results/g_agreement/e96/STATUS.json').read_text());assert i4['gpu_reserved_usd'] in (0,i4.get('rerun_gpu_reserved_usd',0))
i5path=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i5/results/g_agreement/status/I-5.md');i5text=i5path.read_text();i5=float(re.search(r'Closed I-?5 cost \*\*USD([0-9.]+)',i5text).group(1));assert i5closedpath.exists() or 'Newpricedreservation26.86max held' in i5text or 'Newpricedreservation26.86maxheld' in i5text.replace(' ','')
i3path=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i3/results/g_agreement/i3/STATUS.json');i3=json.loads(i3path.read_text())
assert i3['gpu_usd_actual']==i3['gpu_usd_reserved']==i3['gpu_usd_uncertain']==i3['active_pods']==0,'I3_NONZERO_NEEDS_EXACT_RECONCILIATION'
assert i4['gpu_usd_actual']+i4gate['gpu_usd_actual']+i4gate['non_gpu_extra_upper_usd']<=160.55,'I4_KNOWN_COST_EXCEEDS_RETAINED_CONTINGENCY'
qextras=2*len(bills);bookbound=qclosed+qextras+state['GPU_budget_window_closed_upper_usd']+160.55+i5;live=sum(a['upper'] for a in active);batch=0;candidates=[]
for i in [3,4,5]:
 h=root/'cache/g_agreement/i2/e81_serial_production_v1'/('operator'+str(i)+'-a2');m=json.loads((h/'PREPARATION.json').read_text())
 if (h/'CREATE_ONCE_INTENT.json').exists():continue
 assert m['mode']=='production' and m['gpu_type']=='H200' and m['source_sha']=='9e2cb591cbb0cb4eff6265268831b73df115feb4cdba035afed6c52ffde58d60';batch+=m['gpu_forecast_upper_usd'];candidates.append(dict(shard=i,run_id=m['run_id'],cap_seconds=m['cap_seconds'],upper=m['gpu_forecast_upper_usd']))
for home in new_e99_homes:
 h=root/home
 if not (h/'PREPARATION.json').exists():raise AssertionError('ALL_FOUR_NEW_E99_INPUTS_REQUIRED')
 m=json.loads((h/'PREPARATION.json').read_text())
 if (h/'CREATE_ONCE_INTENT.json').exists():continue
 assert m['experiment']=='E99' and m['mode']=='read' and m['gpu_type']=='H200'
 assert m['prior_probe_gpu_seconds']==18451.277901887894 and m['aggregate_actual_plus_new_caps_seconds']<86400
 batch+=m['gpu_forecast_upper_usd'];candidates.append(dict(experiment='E99',shard=m['shard'],run_id=m['run_id'],cap_seconds=m['cap_seconds'],upper=m['gpu_forecast_upper_usd']))
for home in restart_homes:
 h=root/home;m=json.loads((h/'PREPARATION.json').read_text())
 if (h/'CREATE_ONCE_INTENT.json').exists():continue
 assert (m['experiment']=='E86' and m['cap_seconds']==3352 and m['prior_probe_gpu_seconds']+m['cap_seconds']<=7200) or (m['experiment']=='E82' and m['authority']=='ACTUAL_DIRECT_HUMAN_SECTION212_AMENDMENT1' and m['registered_items']==209 and m['registered_positions']==6790 and m['prior_probe_gpu_seconds']+m['cap_seconds']<=14400)
 batch+=m['gpu_forecast_upper_usd'];candidates.append(dict(experiment=m['experiment'],run_id=m['run_id'],cap_seconds=m['cap_seconds'],upper=m['gpu_forecast_upper_usd']))
proof=dict(as_of_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),policy='dfe326565b / GPU2500Oct28–30, judge500unchanged',Q_closed_GPU_usd=qclosed,Q_unique_closed_pods=len(bills),Q_corrections_usd=sum(r['usd'] for r in corrections.values()),Q_nonGPU_extra_admission_upper_usd=qextras,Q_closed_ledger_sha256=hashlib.sha256(ledger.read_bytes()).hexdigest(),Q_operator_log_sha256=hashlib.sha256((oproot/'status.log').read_bytes()).hexdigest(),I2_closed_window_all_in_upper_usd=state['GPU_budget_window_closed_upper_usd'],I3_closed_reserved_usd=0,I3_status_sha256=hashlib.sha256(i3path.read_bytes()).hexdigest(),I4_gate_closed_GPU_usd=i4gate['gpu_usd_actual'],I4_gate_extra_upper_usd=i4gate['non_gpu_extra_upper_usd'],I4_known_closed_GPU_upper_usd=i4['gpu_usd_actual'],I4_admission_upper_retained_usd=160.55,I4_unknown_extras_storage_treatment='retain the older160.55 all-in programme upper in place of known48.017GPU; difference is conservative contingency, not invoice or new booking; missing extras never treated aszero',I5_closed_all_in_upper_usd=i5,I5_status_sha256=hashlib.sha256(i5path.read_bytes()).hexdigest(),active_caps=active,active_all_in_upper_usd=live,uncertain_held_caps=uncertain_held,uncertain_held_upper_usd=uncertain_upper,account_running=len(running),account_hourly_usd=round(sum(float(p['costPerHr']) for p in running),2),nonrunning_account_pods=len(pods)-len(running),conservative_closed_admission_upper_usd=bookbound,proposed_shards=candidates,proposed_all_three_upper_usd=batch,projection_with_all_three_usd=math.ceil((bookbound+live+uncertain_upper+batch)*100)/100,not_an_invoice_or_new_booking=True,live_accrual_not_added_again=True,uncommitted_future_jobs_not_active_reservations=True,judge_new_liability_usd=0,judge_global_ceiling_usd=500,judge_admission=False)
poolpath=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/cache/g_agreement/i2/publication/results/g_agreement/compiler/PARKED_POOL_CURRENT.json');pool=json.loads(poolpath.read_text());assert pool['ceiling_usd']==900
poolactive=sum(a['upper']for a in active+uncertain_held if a.get('pool_id')=='section211_amendment1_parked');poolbooked_min=float(pool.get('confirmed_post_authority_booked_usd',0));poolbooked_evidence=[]
rr=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i4/results/g_agreement/e96/slot1_separate_not_run/RUN_RECEIPT.json')
if rr.exists():
 r=json.loads(rr.read_text());assert r['pool_id']=='section211_amendment1_parked' and r['provider_postclose_pod'] is None and r['guards_retired'] is True and r['remaining_active_cap_usd']==0
 assert r['pod_id']=='3u0pebmt3wh18g' and r['all_in_upper_usd']==r['gpu_usd_rate_based_upper']+r['non_gpu_contingency_upper_usd']
 poolbooked_min=max(poolbooked_min,float(r['all_in_upper_usd']));poolbooked_evidence.append(dict(owner='I-4',pod_id=r['pod_id'],booked_all_in_upper_usd=r['all_in_upper_usd'],receipt_sha256=hashlib.sha256(rr.read_bytes()).hexdigest()))
remaining_upper=max(0,900-poolactive-poolbooked_min)
proof.update(parked_pool_ceiling_usd=900,parked_pool_confirmed_live_or_uncertain_held_caps_usd=poolactive,parked_pool_confirmed_booked_lower_bound_usd=poolbooked_min,parked_pool_booked_evidence=poolbooked_evidence,parked_pool_unreported_usage=pool['unreported_usage'],parked_pool_remaining_budget_upper_bound_usd=remaining_upper,parked_pool_actual_available_not_claimed=True,parked_pool_ledger_sha256=hashlib.sha256(poolpath.read_bytes()).hexdigest(),projection_with_unallocated_pool_upper_usd=math.ceil((proof['projection_with_all_three_usd']+remaining_upper)*100)/100,pool_projection_basis='Full900 counted once relative to confirmed pool-funded booked/live amounts already in all-track base; unknown unreported usage remains unknown, so remaining is an upper bound, NOT verified spendable pool balance. No new pool allocation authorized by this audit alone.')
assert proof['projection_with_all_three_usd']<1500
assert proof['projection_with_unallocated_pool_upper_usd']<2500
proof['GPU_warning2000_including_pool']=proof['projection_with_unallocated_pool_upper_usd']>=2000
cache=root/'cache/g_agreement/i2';(cache/'FRESH_ALL_TRACK_ADMISSION_20261028T1715.json').write_text(json.dumps(proof,indent=2)+'\n');(root/'results/g_agreement/i2/E81_REMAINING_SHARDS_FRESH_LIABILITY_ADMISSION.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
