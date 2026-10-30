"""Verified second-wave CPU preparation and sealed, once-only E62/E59 analyses."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from runtime62 import *
from contract56 import auc,validate_judgment
from cpu_capture import compute as cpu_fit
from stats_native import rate,signed_value,reported
sys.path.insert(0,str(HERE.parents[1]/'e57/job'))
from analysis_io import claim_once,continuation_aucs
from measures62 import eval_measure,behaviour_aucs

def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]
def validate_spec(path):
 s=read(path);job=HERE if s['experiment']=='E62P' else HERE.parents[1]/s['experiment'].lower()/'job';cmd=read(Path(s.get('command_file',str(job/'ANALYSIS_COMMAND.json'))));require(sha(path)==cmd['spec_sha256'],'sealed analysis spec');verify(job,'SOURCE_SEAL.json',s['source_seal_sha256'])
 for name,digest in read(job/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'analysis dependency')
 return s

def captures(s):
 root=Path(s['output']);receipt=read(s['capture_receipt']);require(receipt['verified'] is True and receipt['experiment']==s['experiment'],'capture verified')
 cap=root/'capture';sealed=verify(cap,'CAPTURE_SEAL.json',receipt['capture_seal_sha256']);require(sealed['source_seal_sha256']==s['source_seal_sha256'] and sealed['input_seal_sha256']==s['input_seal_sha256'] and sealed['pod_id']==receipt['pod_id'],'capture binding')
 verify(s['inputs'],'INPUT_SEAL.json',s['input_seal_sha256']);items=read(Path(s['inputs'])/'items.json');require(read(cap/'items.order.json')==[x['id'] for x in items],'full frozen order')
 if s['experiment'] in ('E62','E62P'):
  offsets=np.load(cap/'offsets.npy');h=np.load(cap/'all_positions44.npy',mmap_mode='r');require(h.dtype==np.float16 and h.shape==(int(offsets[-1]),5120),'all-position fp16')
  require(offsets.tolist()==[0]+np.cumsum([x['read_index']-x['first_content_index']+1 for x in items]).tolist(),'full-position offsets')
 require(sha(s['private_items'])==s['private_items_sha256'],'private labels pin');private=read(s['private_items']);require([x['id'] for x in private]==[x['id'] for x in items],'private order')
 return root,cap,private

def cpu(s):
 root,cap,items=captures(s);out=Path(s['cpu_out']);out.mkdir(parents=True,exist_ok=False)
 rows={x['feature'] for x in items if x.get('state')!='S6'};scores,means=cpu_fit(items,np.load(cap/'acts44.npy'),rows);dump(out/'PROBE.json',scores);np.savez(out/'CLASS_MEANS.npz',**means)
 seal(out,'CPU_SEAL.json',{'experiment':s['experiment'],'capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json'),'private_items_sha256':s['private_items_sha256'],'source_seal_sha256':s['source_seal_sha256'],'device':'cpu'})

def collect(s):
 root,cap,items=captures(s);receipt=read(s['receipt']);require(receipt['verified'] is True and receipt['experiment']==s['experiment'],'verified output');sealed=verify(root,'OUTPUT_SEAL.json',receipt['output_seal_sha256']);a=read(root/'ASSIGNMENT.json')
 from second_worker import allocation
 _,end=allocation(a);require(a['pod_created_epoch']<=read(root/'TIMING.json')['completed_epoch']<end,'custody cap');require(sealed['pod_id']==receipt['pod_id']==a['pod_id'] and sealed['source_seal_sha256']==s['source_seal_sha256'] and sealed['input_seal_sha256']==s['input_seal_sha256'],'output identity')
 require(a['parent_request_sha256']==s['parent_request_sha256'] and sealed['cohort_id']==a['cohort_id'],'same-run parent')
 require(read(root/'ADMISSION.json')['status']=='ADMIT','self admission');go=read(root/'GO_RECEIPT.json');require(go['reader_launch_authorized'] is True and go['pod_id']==a['pod_id'] and go['capture_seals'][s['experiment']]==sha(cap/'CAPTURE_SEAL.json'),'capture-bound GO')
 gate=root/'parity';verify(gate,'PARITY_SEAL.json') if (gate/'PARITY_SEAL.json').exists() else None
 require(read(gate/'PARITY_RESULT.json')['status']=='PASS' and read(root/'PARITY_REUSE.json')['parity_result_sha256']==sha(gate/'PARITY_RESULT.json'),'parity')
 cs=verify(s['cpu_out'],'CPU_SEAL.json');require(cs['capture_seal_sha256']==sha(cap/'CAPTURE_SEAL.json') and cs['private_items_sha256']==s['private_items_sha256'],'CPU label/capture binding')
 expected={x['id'] for x in items if x['split']=='test'};native=[]
 for reader in ('oracle','nla'):
  xs=lines(root/(reader+'.native.jsonl'));require(len(xs)==len(expected) and {x['id'] for x in xs}=={k+':'+reader+':0' for k in expected},'native once grid');require(all(x['reader']==reader and x['reader_native_layer']==(44 if reader=='oracle' else 42) and x['repeat']==0 for x in xs),'native identity');native+=xs
 probe=read(Path(s['cpu_out'])/'PROBE.json');pr={x['id']:x for x in items};eligible={x['id'] for x in items if x['split']=='test' and x.get('state')!='S6'};require(len(probe)==len(eligible) and {x['id'] for x in probe}==eligible,'probe grid')
 aucs={row:auc([pr[x['id']]['label'] for x in probe if x['feature']==row],[x['score'] for x in probe if x['feature']==row]) for row in {pr[k]['feature'] for k in eligible}}
 return root,pr,native,aucs,a

def blind(s):
 root,private,native,probe,a=collect(s);rng=np.random.default_rng(20261027);records=list(native);rng.shuffle(records);packet=[];eval_packet=[];key=[]
 for x in records:
  item=private[x['unit_id']];opaque=rng.bytes(16).hex();entry={'id':opaque,'readout':x['text']}
  if item.get('state')=='S6':eval_packet.append(entry)
  else:
   values={lab:sorted({z['value'] for z in private.values() if z['feature']==item['feature'] and z['label']==lab}) for lab in (0,1)}
   require(all(len(v)==1 for v in values.values()),'frozen A/B value names');entry.update(property=item['feature'],values={'A':values[1][0],'B':values[0][0]});packet.append(entry)
  key.append({'opaque_id':opaque,'source_id':x['id'],'eval':item.get('state')=='S6'})
 out=Path(s['blind_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'JUDGE_PACKET.json',packet);dump(out/'EVAL_PACKET.json',eval_packet);dump(Path(s['private_key']),key)
 seal(out,'BLIND_SEAL.json',{'experiment':s['experiment'],'output_seal_sha256':sha(root/'OUTPUT_SEAL.json'),'private_key_sha256':sha(s['private_key']),'value_rubric_sha256':sha(E56/'JUDGE_RUBRIC.md'),'eval_rubric_sha256':sha(HERE/'S6_RUBRIC.md')})

def judgments(s,root,native):
 bs=verify(s['blind_out'],'BLIND_SEAL.json');require(bs['output_seal_sha256']==sha(root/'OUTPUT_SEAL.json') and bs['private_key_sha256']==sha(s['private_key']),'blind custody')
 packet={x['id']:x for n in ('JUDGE_PACKET.json','EVAL_PACKET.json') for x in read(Path(s['blind_out'])/n)};key=read(s['private_key']);lookup={x['id']:x for x in native}
 js=verify(Path(s['judgments']).parent,'JUDGMENT_SEAL.json');require(js['blind_seal_sha256']==sha(Path(s['blind_out'])/'BLIND_SEAL.json'),'judgment provenance');jj=read(s['judgments']);require(len(jj)==len(key)==len(native) and {x['id'] for x in jj}==set(packet) and {x['source_id'] for x in key}==set(lookup),'complete blind grid');by={x['id']:x for x in jj};out={}
 for k in key:
  x=lookup[k['source_id']];require(packet[k['opaque_id']]['readout']==x['text'],'unaltered raw payload');j=by[k['opaque_id']]
  if not k['eval']:validate_judgment(j,x['text'])
  out[x['id']]=j
 return out

def metrics(private,native,jj):
 rates={};by={}
 for x in native:
  item=private[x['unit_id']]
  if item.get('state')=='S6':continue
  by.setdefault((x['reader'],item['feature']),[]).append((x['unit_id'],signed_value(jj[x['id']],item['label'])))
 for k,v in by.items():rates[k]=rate([[score] for _,score in sorted(v)])
 return rates

def rules62(probe,rates,jrows):
 gated=[state for state in ('S1','S2','S3','S4','S5') if all(probe[f'{state}_L{i}']>=.90 for i in range(5))];out={'R_L0':{s:s in gated for s in ('S1','S2','S3','S4','S5')},'readers':{}}
 for r in ('oracle','nla'):
  delta={s:rates[r,s+'_L4']['S']-rates[r,s+'_L0']['S'] for s in gated};means=[float(np.mean([rates[r,f'{s}_L{i}']['S'] for s in gated])) for i in range(5)] if gated else []
  rho=float(spearmanr(range(5),means).statistic) if means and len(set(means))>1 else None
  cells=[f'{s}_L{i}' for s in gated for i in range(5)];j=[jrows[c]['J_fraction'] for c in cells];v=[rates[r,c]['S'] for c in cells];corr=float(spearmanr(j,v).statistic) if len(set(j))>1 and len(set(v))>1 else None
  out['readers'][r]={'L4_minus_L0':delta,'rung_means':means,'rho_rung_S':rho,'rho_J_S':corr,'R_L1':('NOT EVALUABLE' if not gated else 'MET' if sum(round(x,12)>=.30 for x in delta.values())>=min(4,len(gated)) and rho is not None and rho>=.8 else 'NOT MET'),'R_L2':('NOT EVALUABLE' if corr is None else 'MET' if corr>=.6 else 'NOT MET'),'falsifier':'HELD: quantitative convention for J-fraction rises not registered; trajectories reported','J_trajectories':{s:[jrows[f'{s}_L{i}']['J_fraction'] for i in range(5)] for s in gated}}
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',choices=['cpu','blind','analyze'],required=True);a=p.parse_args();s=validate_spec(a.spec)
 if a.mode=='cpu':cpu(s);return
 if a.mode=='blind':blind(s);return
 root,private,native,probe,ass=collect(s);jj=judgments(s,root,native);jr=Path(s['j_input']);js=verify(jr,'J_SEAL.json');require(js['capture_seal_sha256']==sha(root/'capture/CAPTURE_SEAL.json') and js['input_seal_sha256']==s['input_seal_sha256'],'J capture/input binding');jrows=read(jr/'J_ROWS.json');require(set(jrows)==set(probe),'complete J cells')
 out=claim_once(s['analysis_out'],s['experiment'],sha(a.spec));rates=metrics(private,native,jj)
 extra={}
 if s['experiment']=='E62':
  result=rules62(probe,rates,jrows);result.update(behaviour=behaviour_aucs(list(private.values()),read(root/'BEHAVIOUR.json')),eval_ladder=eval_measure(list(private.values()),native,jj))
  available=[st for st,ok in result['R_L0'].items() if ok];result['behaviour']['R_L3']='NOT EVALUABLE' if len(available)<4 else 'MET' if sum(result['behaviour']['AUROC'][st]>=.80 for st in available)>=4 else 'NOT MET'
  ps=validate_spec(Path(s['placebo_spec']));proot,pprivate,pnative,pprobe,passign=collect(ps);require(passign['cohort_id']==ass['cohort_id'],'same ladder cohort');pjj=judgments(ps,proot,pnative);prates=metrics(pprivate,pnative,pjj)
  require(sha(s['placebo_confound_check'])==s['placebo_confound_check_sha256'],'ratified S5 construction check pin');confound=read(s['placebo_confound_check']);result['placebo_confound_check']=confound
  result['placebo_probe']=pprobe;result['placebo_rates']={'|'.join(k):v for k,v in prates.items()};result['R_L5']={}
  for reader in ('oracle','nla'):
   differences={st:{r:rates[reader,st+'_'+r]['S']-prates[reader,st+'_'+r+'p']['S'] for r in ('L2','L4')} for st in result['R_L0'] if result['R_L0'][st] and st!='S5'}
   passes=sum(all(round(v,12)>=.2 for v in ds.values()) for ds in differences.values());result['R_L5'][reader]={'real_minus_placebo':differences,'passing_states':passes,'excluded_states':{'S5':'650138c5: |phi|=0.288675>0.2; retain data, exclude L4p from R-L5'},'verdict':'NOT EVALUABLE' if len(differences)<4 else 'MET' if passes>=4 else 'NOT MET','placebo_at_least_real_L4':{st:ds['L4']<=0 for st,ds in differences.items()}}
 else:
  bow=read(Path(s['inputs'])/'BOW_QA.json');allowed=[r for r in probe if probe[r]>=.90 and bow[r]['instruction_only_test_auroc']<=.65]
  parent=Path(s['e57_analysis']);ps=verify(parent,'ANALYSIS_SEAL.json');require(ps['experiment']=='E57' and ps['status']=='COMPLETE','sealed E57 same run analysis')
  cr=read(s['cohort_receipt']);require(cr['verified'] is True and cr['cohort_id']==ass['cohort_id'] and cr['parent_request_sha256']==ass['parent_request_sha256'] and cr['e57_analysis_seal_sha256']==sha(parent/'ANALYSIS_SEAL.json'),'same-run E57 comparison receipt');prev=read(parent/'RESULTS.json')
  result={'probe_and_BOW_gates':{r:r in allowed for r in probe},'readers':{},'R2_IN_J':sum(x['J_label']=='IN-J' for x in jrows.values())}
  for r in ('oracle','nla'):
   count=sum(reported(rates[r,row]) for row in allowed);mechanics=prev['R_B']['reporting_rows'][r];result['readers'][r]={'reported_plans':count,'same_run_reported_mechanics':mechanics,'R1':'MET' if count>=4 and mechanics<=1 else 'NOT MET','falsifier':count<=1}
  cont=[x for r in ('oracle','nla') for x in read(root/(r+'.continuation.json'))];extra['continuation']=continuation_aucs({'private':private,'continuation':cont});extra['not_evaluable_continuation']=[r for r,p in read(Path(s['inputs'])/'PLAN.json')['continuation_pairs'].items() if p is None]
 result.update(probe=probe,rates={'|'.join(k):v for k,v in rates.items()},J_rows=jrows,NLA_truncation=read(root/'NLA_TRUNCATION.json'),**extra)
 dump(out/'RESULTS.json',result);(out/'RESULTS.md').write_text('# '+s['experiment']+' registered analysis\n\n'+json.dumps(result['readers'],indent=2)+'\n');seal(out,'ANALYSIS_SEAL.json',{'experiment':s['experiment'],'status':'COMPLETE','source_seal_sha256':s['source_seal_sha256'],'cohort_id':ass['cohort_id']})
if __name__=='__main__':main()
