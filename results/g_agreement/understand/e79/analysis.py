"""Once-only E79 blind reporting + W-text frozen AUROC, CPU only."""
import argparse,sys,secrets,subprocess
from worker import *
sys.path.insert(0,str(U/'analysis402'))
from missingness import validate_judgment,signed_value,rate

def config(path):
 s=read(path);c=read(HERE/'ANALYSIS_COMMAND.json');verify(HERE,'ANALYSIS_SOURCE_SEAL.json',c['analysis_source_seal_sha256']);require(sha(path)==c['spec_sha256'] and sha(HERE/'analysis.py')==c['adapter_sha256'],'sealed analysis configuration')
 for n,h in read(HERE/'ANALYSIS_DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'analysis dependency')
 return s

def collect(s):
 req=read(HERE/'REQUEST.json');r=read(s['receipt']);require(r['verified'] is True and r['experiment']=='E79','verified pull');root=Path(r['output']);o=verify(root,'OUTPUT_SEAL.json',r['output_seal_sha256']);require(o['status']=='COMPLETE' and o['source_seal_sha256']==req['source_seal_sha256'] and o['input_seal_sha256']==req['input_seal_sha256'],'exact executed source/input')
 ass=read(root/'ASSIGNMENT.json');require(ass['pod_id']==o['pod_id']==r['pod_id'] and ass['gpu_count']==1 and ass['prior_seconds']>=0 and ass['cap_seconds']+ass['prior_seconds']<=read(HERE/'STAGE_REQUEST.json')['cap_seconds'],'custody cap');require(ass['custody_start_epoch']==ass['pod_created_epoch'] and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'] and read(root/'TIMING.json')['completed_epoch']<=ass['absolute_deadline_epoch'],'fixed stage clock')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=260,'budget');require(read(root/'FORECAST.json')['status']=='ADMIT','admission')
 require(sha(s['judge_plan'])==s['judge_plan_sha256'],'frozen per-item judge values');b=read(HERE/'INPUT_BINDING.json');require(sha(s['private_join'])==b['private_join_sha256'],'private owner map');key={x['id']:x for x in read(s['private_join'])};items=read(Path(b['inputs'])/'items.json');grid=jobs(items);require(read(root/'JOB_GRID.json')==grid and read(root/'COMPLETED.json')==list(range(len(grid))),'all registered jobs once')
 native=[];beh=[]
 for i,j in enumerate(grid):
  xs=read(root/'jobs'/f'{i:06d}.json');require(len(xs)==len(j['indices']),'batch cardinality')
  for x,ix in zip(xs,j['indices']):
   require(x['id']==items[ix]['id'],'vector identity')
   if j['kind']=='native':require(isinstance(x['text'],str),'native text');native.append(x)
   else:
    k=key[x['id']];beh.append(dict(id=k['source_item_id'],feature=k['row'],condition={'J':'d_J','nonJ':'d_perp','random':'random','none':'none'}[k['condition']],pair_logits=x['pair_logits']))
 require(len(native)==4704 and len(beh)==672,'full experiment grid');return root,key,native,beh

def blind(s,root,key,native):
 out=Path(s['blind_out']);private=Path(s['blind_key']);require(not private.resolve().is_relative_to(out.resolve()),'private key separate');require(subprocess.run(['git','check-ignore','-q',str(private)],cwd=ROOT).returncode==0,'private key ignored');require(not out.exists() and not private.exists(),'blind export once');packet=[];join=[];rng=np.random.default_rng(20261028)
 for i in rng.permutation(len(native)):
  x=native[int(i)];k=key[x['id']];v=read(s['judge_plan'])['judge_values'][k['source_item_id']] if k['arm']=='A' else s['values'][k['row']];opaque=secrets.token_hex(16);packet.append(dict(id=opaque,property=k['row'],value_A=v[0],value_B=v[1],readout=x['text']));join.append(dict(opaque_id=opaque,source_id=x['id']))
 out.mkdir(parents=True,exist_ok=False);private.parent.mkdir(parents=True,exist_ok=True);dump(private,join);private.chmod(0o600);dump(out/'RUBRIC_FIELDS.json',packet);dump(out/'JUDGE_PACKET.json',[dict(id=x['id'],property=x['property'],values={'A':x['value_A'],'B':x['value_B']},readout=x['readout']) for x in packet]);seal(out,'BLIND_SEAL.json',dict(experiment='E79',receipt_sha256=sha(s['receipt']),output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),private_key_sha256=sha(private),rubric_sha256=sha(U/'e56/job/JUDGE_RUBRIC.md')))

def judgments(s,root,native):
 out=Path(s['blind_out']);b=verify(out,'BLIND_SEAL.json');require(b['output_seal_sha256']==sha(root/'OUTPUT_SEAL.json') and b['receipt_sha256']==sha(s['receipt']) and b['private_key_sha256']==sha(s['blind_key']) and b['rubric_sha256']==sha(U/'e56/job/JUDGE_RUBRIC.md'),'blind provenance')
 js=Path(s['judgments']);z=verify(js.parent,'JUDGMENT_SEAL.json');require(z['blind_seal_sha256']==sha(out/'BLIND_SEAL.json'),'judge source');jj=read(js);join=read(s['blind_key']);packet={x['id']:x for x in read(out/'JUDGE_PACKET.json')};by={x['id']:x for x in jj};raw={x['id']:x for x in native}
 require(len(jj)==len(join)==len(packet)==len(by)==len(raw)==4704 and set(by)==set(packet) and {x['source_id'] for x in join}==set(raw) and len({x['opaque_id'] for x in join})==4704,'exact judgment/source grid');result={}
 for k in join:
  x=raw[k['source_id']];require(packet[k['opaque_id']]['readout']==x['text'],'unaltered native readout');j=by[k['opaque_id']];validate_judgment(j,x['text']);result[x['id']]=j
 return result

def differences(cells,a,b):
 # Joint item resampling, preserve each cell's missingness; point estimate is
 # difference of retained-cell means, not complete-case substitution.
 ids=sorted(set(cells[a])|set(cells[b]));x=np.array([np.nan if cells[a][k] is None else cells[a][k] for k in ids]);y=np.array([np.nan if cells[b][k] is None else cells[b][k] for k in ids])
 if not np.isfinite(x).any() or not np.isfinite(y).any():return dict(delta=None,CI95=None,status='NOT EVALUABLE')
 rng=np.random.default_rng(20261027);ix=rng.integers(0,len(ids),(2000,len(ids)));draw=np.nanmean(x[ix],axis=1)-np.nanmean(y[ix],axis=1)
 if not np.isfinite(draw).all():return dict(delta=float(np.nanmean(x)-np.nanmean(y)),CI95=None,status='NOT EVALUABLE')
 return dict(delta=float(np.nanmean(x)-np.nanmean(y)),CI95=np.quantile(draw,[.025,.975]).tolist(),status='EVALUABLE')

def rules(cells,auroc):
 summary={};a_pass=0;a_falsifier=True
 for row in sorted(A_ROWS):
  v=cells[row];stats={};passing=[]
  for alpha in (.25,.5,1,2,4):
   j=f'J:{alpha}';p=f'nonJ:{alpha}';d=differences(v,j,p);sj=rate([[x] for _,x in sorted(v[j].items())])['S'];ok=None if sj is None or d['CI95'] is None else round(sj,12)>=.30 and round(d['delta'],12)>=.30 and d['CI95'][0]>0
   stats[str(alpha)]=dict(S_target_J=sj,J_minus_perp=d,passes=ok,rule_eligible=alpha<=2)
   if ok and alpha<=2:passing.append(alpha)
   if d['delta'] is None:a_falsifier=None
   elif not round(d['delta'],12)<.10:a_falsifier=False
  row_eval=all(x['passes'] is not None for x in stats.values() if x['rule_eligible']);a_pass+=bool(passing);summary[row]=dict(alphas=stats,passing_alphas=passing,status='MET' if passing else 'NOT MET' if row_eval else 'NOT EVALUABLE')
 for row,v in summary.items():
  base=rate([[x] for _,x in sorted(cells[row]['none'].items())])['S'];trajectory=[base]+[v['alphas'][str(a)]['S_target_J'] for a in (.25,.5,1,2)]
  v['J_dose_trajectory_0_to_2']=dict(zip(('0','.25','.5','1','2'),trajectory));v['monotone_J_0_to_2']=None if None in trajectory else all(round(b-a,12)>=0 for a,b in zip(trajectory,trajectory[1:]))
 arule='MET' if a_pass>=2 else 'NOT EVALUABLE' if any(x['status']=='NOT EVALUABLE' for x in summary.values()) else 'NOT MET'
 bstats={};b_falsifier=True
 for row in sorted(B_ROWS):
  v=cells[row];drop=differences(v,'none','J');extra=differences(v,'nonJ','J');beh=auroc['d_J'][row]>=auroc['none'][row]-.10
  ok=None if drop['delta'] is None or extra['CI95'] is None else round(drop['delta'],12)>=.30 and round(extra['delta'],12)>=.20 and extra['CI95'][0]>0 and beh
  bstats[row]=dict(drop_J=drop,drop_J_minus_drop_perp=extra,behaviour_AUROC=auroc['d_J'][row],none_AUROC=auroc['none'][row],behaviour_pass=beh,status='NOT EVALUABLE' if ok is None else 'MET' if ok else 'NOT MET')
  if drop['delta'] is None:b_falsifier=None
  elif not round(drop['delta'],12)<.10:b_falsifier=False
 brule='MET' if all(x['status']=='MET' for x in bstats.values()) else 'NOT EVALUABLE' if any(x['status']=='NOT EVALUABLE' for x in bstats.values()) else 'NOT MET'
 ad=[v['J_minus_perp']['delta'] for row in summary.values() for v in row['alphas'].values() if v['rule_eligible']];bd=[v['drop_J']['delta'] for v in bstats.values()]
 a_falsifier=False if any(x is not None and round(x,12)>=.10 for x in ad) else None if None in ad else True
 b_falsifier=False if any(x is not None and round(x,12)>=.10 for x in bd) else None if None in bd else True
 return dict(R_C1=arule,ArmA=summary,ArmA_falsifier=a_falsifier,R_C2=brule,ArmB=bstats,ArmB_falsifier=b_falsifier)

def analyze(s,root,key,native,beh,jj):
 sys.path.insert(0,str(HERE/'cpu_scorer'));from score79 import score
 verify(HERE/'cpu_scorer','SCORER_SEAL.json',read(HERE/'REQUEST.json')['scorer_seal_sha256']);require(sha(s['private_items'])==read(HERE/'cpu_scorer/INPUT_CONTRACT.json')['E59_private_items_sha256'],'E59 labels pin');private={x['id']:x for x in read(s['private_items']) if x['split']=='test' and x['feature'] in B_ROWS}
 # Claim before any registered statistical calculation. No alternate output reset.
 out=Path(s['out']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE.json',dict(spec_sha256=sha(HERE/'ANALYSIS_SPEC.json'),output_seal_sha256=sha(root/'OUTPUT_SEAL.json')))
 behaviour=score(beh,private);cells={};counts={}
 for x in native:
  k=key[x['id']];cell=k['condition'] if k['alpha'] in (None,0) else k['condition']+':'+str(k['alpha']);cell='none' if cell=='baseline' else cell;v=signed_value(jj[x['id']],k['target_label'] if k['arm']=='A' else k['true_label']);cells.setdefault(k['row'],{}).setdefault(cell,{})[k['source_item_id']]=v
 rates={}
 for row,cc in cells.items():
  for cell,v in cc.items():
   rates[row+'|'+cell]=rate([[x] for _,x in sorted(v.items())]);m=sum(x is None for x in v.values());counts[row+'|'+cell]=dict(total=len(v),kept=len(v)-m,UNPARSEABLE=m,over_5_percent=20*m>len(v))
 result=rules(cells,behaviour['auroc']);result.update(rates=rates,behaviour=behaviour,armA_measure='S_target',armB_measure='S_true',bootstrap='2000 joint item draws seed20261027; masks kept per cell')
 dump(out/'RESULTS.json',result);dump(out/'UNPARSEABLE_COUNTS.json',counts);require(sha(s['diagnostics'])==s['diagnostics_sha256'],'diagnostics pin');dump(out/'DIAGNOSTICS.json',read(s['diagnostics']));verify(s['manipulation'],'MANIPULATION_SEAL.json',s['manipulation_seal_sha256']);dump(out/'MANIPULATION.json',read(Path(s['manipulation'])/'MANIPULATION.json'));(out/'RESULTS.md').write_text('# E79\n\nR-C1: '+result['R_C1']+'\nR-C2: '+result['R_C2']+'\n');seal(out,'ANALYSIS_SEAL.json',dict(experiment='E79',status='COMPLETE_ONCE',output_seal_sha256=sha(root/'OUTPUT_SEAL.json')))

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',choices=['verify','blind','analyze'],required=True);a=p.parse_args();s=config(a.spec);root,key,native,beh=collect(s)
 if a.mode=='blind':blind(s,root,key,native)
 elif a.mode=='analyze':analyze(s,root,key,native,beh,judgments(s,root,native))
if __name__=='__main__':main()
