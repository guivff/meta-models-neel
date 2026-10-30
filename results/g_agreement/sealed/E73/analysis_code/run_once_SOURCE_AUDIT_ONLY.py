"""Operational custody adapter around frozen E73 statistics; once-only primary+sensitivity."""
import argparse,copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2');H=Path(__file__).resolve().parent
BASELINE='c06ae1b774126ba8b6922b4216050d686e375b22'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def need(x,m):
 if not x:raise ValueError(m)
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def module():
 sys.path.insert(0,str(H/'frozen'))
 from projects.g_agreement.e73 import analyze as A,analyze_controls as C
 return A,C

def checked_plan(ref):
 raw=subprocess.check_output(['git','-C',str(ROOT),'show',ref['commit']+':'+ref['path']]);need(hashlib.sha256(raw).hexdigest()==ref['sha256'],'COMMITTED_PLAN_HASH');p=json.loads(raw)
 need(p['source_sha256']==sha(__file__) and p['analysis_invocations']==1 and p['controls_complete'],'FROZEN_PLAN_SCOPE')
 for f,digest in p['source_bindings'].items():need(sha(f)==digest,'FROZEN_SOURCE')
 for f,digest in p['input_bindings'].items():need(sha(f)==digest,'EXACT_INPUT_HASH')
 for name,digest in p['frozen_sources'].items():
  raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASELINE+':'+name]);need(hashlib.sha256(raw).hexdigest()==digest==sha(H/'frozen'/name),'FROZEN_SCIENCE')
 return p

def adapt_bank(bank,out,A):
 """Invoked only after exclusive once claim. Preserve all terminal codes/attempts."""
 terminal=read(bank['terminal_path']);packet=read(bank['builder_spec']);wire=read(bank['judge_wire']);original_wire=read(Path(packet['out'])/'WIRE_PACKET.json');transform=read(bank['transform_path']);records=transform['records'];ids={x['opaque_id'] for x in records}
 wm={x['id']:x for x in wire};om={x['id']:x for x in original_wire};need(len(terminal)==bank['n'] and {x['id']for x in terminal}==set(wm)==set(om),'TERMINAL_WIRE_GRID')
 # Recompute the exact authorised span-only copy from the preserved originals.
 sys.path.insert(0,str(ROOT/'cache/g_agreement/i2/e73_controls_judging_candidate'));import dispatch_controls as T
 expected,derived=T.transform(original_wire);need(expected==wire,'EXACT_AUTHORISED_JUDGE_COPY')
 need({x['opaque_id']for x in derived}==ids,'REDACTED_ID_BINDING')
 codes=[]
 for t in terminal:
  need(type(t['attempts'])is int and 0<=t['attempts']<=2,'TERMINAL_ATTEMPTS')
  if t['status']=='KEPT':
   code=t['code'];need(code['id']==t['id'],'TERMINAL_CODE_ID');A.validate_judgment(code,wm[t['id']]['readout'])
  else:
   need(t['status']=='UNPARSEABLE' and t['attempts']==2 and t['code']is None,'TERMINAL_SENTINEL');code={'id':t['id'],'category':'UNPARSEABLE','values':[],'evidence':''}
  codes.append(code)
 folder=out/bank['name'];folder.mkdir();tr=folder/'terminal';tr.mkdir();jr=folder/'adapted';jr.mkdir();dump(tr/'JUDGMENTS.json',terminal);dump(jr/'JUDGMENTS.json',codes)
 from projects.g_agreement.e73.custody import seal
 ts=seal(tr,'RESULT_SEAL.json',[tr/'JUDGMENTS.json'],bank='E73',status='TERMINAL_BLIND_GRID_NO_ANALYSIS',packet_seal_sha256=sha(Path(packet['out'])/'BLIND_SEAL.json'),original_terminal_seal_sha256=bank['terminal_seal_sha256'],redaction_transform_sha256=sha(bank['transform_path']))
 seal(jr,'JUDGMENT_SEAL.json',[jr/'JUDGMENTS.json'],blind_seal_sha256=sha(Path(packet['out'])/'BLIND_SEAL.json'),terminal_seal_sha256=sha(tr/'RESULT_SEAL.json'))
 ref=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
 i={k:ref(packet[k])for k in ['bank_manifest','labels','gate','reader_index','go']}
 i.update(probe_seal=ref(bank['probe_seal']),reader_input_seal=ref(Path(packet['reader_index']).parent/'READER_INPUT_SEAL.json'),forecast=bank['forecast'],native_seals=[ref(Path(x['path'])/'READER_SEAL.json')for x in packet['native']],packet_seal=ref(Path(packet['out'])/'BLIND_SEAL.json'),private_key=ref(packet['private_key']),judgment_seal=ref(jr/'JUDGMENT_SEAL.json'),terminal_seal=ref(tr/'RESULT_SEAL.json'))
 original_validator=A.validate_judgment
 def authorised_evidence(code,text):
  uid=code['id'];need(text==om[uid]['readout'],'ORIGINAL_PACKET_BINDING')
  return original_validator(code,wm[uid]['readout'] if uid in ids else text)
 A.validate_judgment=authorised_evidence
 try:loaded=A.load_inputs({'inputs':i},controls=bank['name']=='controls')
 finally:A.validate_judgment=original_validator
 return loaded,ids

def sensitivity(structural,controls,excluded,A,C):
 """Exclude named redaction records from all score/bootstrap denominators."""
 banks=[]
 for rows,ids in zip((structural,controls),excluded):
  key,codes,probes=copy.deepcopy(rows)
  for code in codes:
   if code['id']in ids:code.update(category='EXCLUDED_REDACTION',values=[],evidence='')
  banks.append((key,codes,probes))
 old=A.summarize
 A.summarize=lambda rows,**kw:old([x for x in rows if x[2]!='EXCLUDED_REDACTION'],**kw)
 try:result=C.compute(*banks)
 finally:A.summarize=old
 for reader,data in result['readers'].items():
  total=sum(r['n_readouts']for r in data['states'].values());data['judgment_missingness']['total']=total;data['judgment_missingness']['flag_over_5_percent']=20*data['judgment_missingness']['UNPARSEABLE']>total
  for key,ids in zip((structural[0],controls[0]),excluded):
   for state in {k['state']for k in key}:
    selected=[k for k in key if k['reader']==reader and k['state']==state and k['opaque_id']not in ids]
    row=data['states'][state];row['redaction_excluded']=sum(k['reader']==reader and k['state']==state and k['opaque_id']in ids for k in key);row['retried']=sum(k['judge_attempts']>0 for k in selected)
    if reader=='nla':
     n=sum(k['truncated']for k in selected);data['NLA_truncation'][state]={'n':len(selected),'truncated':n,'rate':n/len(selected),'flag_over_10_percent':10*n>len(selected)}
  data['judgment_missingness']['retried']=sum(r['retried']for r in data['states'].values())
 result['sensitivity']='Exclude authorised redaction records; unchanged frozen scoring/bootstrap/thresholds.'
 return result

def run(ref):
 p=checked_plan(ref);out=Path(p['output']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE.json',{'invocations':1,'plan':ref,'source_sha256':sha(__file__)})
 try:
  A,C=module();loaded=[];ids=[]
  for bank in p['banks']:
   rows,excluded=adapt_bank(bank,out,A);loaded.append(rows);ids.append(excluded)
  primary=C.compute(*loaded);secondary=sensitivity(*loaded,ids,A,C)
  result={'primary':primary,'redaction_excluded_sensitivity':secondary,'redaction_counts':[len(x)for x in ids],'inputs_plan_sha256':ref['sha256'],'analysis_invocations':1}
  dump(out/'RESULTS.json',result)
  from projects.g_agreement.e73.custody import seal
  seal(out,'ANALYSIS_SEAL.json',[out/'ONCE.json',out/'RESULTS.json'],experiment='E73',status='COMPLETE',scope='FULL_WITH_CONTROLS_AND_REDACTION_SENSITIVITY')
  print(json.dumps({'status':'COMPLETE','R_W1':primary['R_W1'],'sensitivity_R_W1':secondary['R_W1']}))
 except BaseException as e:dump(out/'FAILURE.json',{'type':type(e).__name__,'code':str(e)});raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan-ref',type=Path,required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args();ref=read(a.plan_ref)
 if a.validate_only:checked_plan(ref);print('PLAN_VALIDATED_NO_OUTCOME_LOAD')
 else:run(ref)
