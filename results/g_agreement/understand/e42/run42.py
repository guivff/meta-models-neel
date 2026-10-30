"""E42 ordered once-only CPU pipeline: freeze persistence, THEN join scores."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import numpy as np
from scipy.stats import rankdata
from io42 import *
from states import state
from persistence_core import persistence


def correlation(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float)
 if len(x)<2:return None
 a=rankdata(x);b=rankdata(y);a-=a.mean();b-=b.mean();den=np.sqrt((a*a).sum()*(b*b).sum())
 return float((a*b).sum()/den) if den>0 else None

def draws(x,y,indices):
 a=rankdata(np.asarray(x)[indices],axis=1);b=rankdata(np.asarray(y)[indices],axis=1)
 a-=a.mean(1,keepdims=True);b-=b.mean(1,keepdims=True)
 den=np.sqrt((a*a).sum(1)*(b*b).sum(1))
 return np.divide((a*b).sum(1),den,out=np.full(len(indices),np.nan),where=den>0)

def ci(x):
 f=np.asarray(x)[np.isfinite(x)]
 return {'ci95':np.quantile(f,[.025,.975]).tolist() if len(f) else None,'finite_draws':len(f),'undefined_draws':len(x)-len(f)}

def tests(records):
 rng=np.random.default_rng(20261026);n=len(records)
 x=[r['persistence'] for r in records];y=[r['Oracle'] for r in records]
 ix=rng.integers(0,n,(10000,n)) if n else np.empty((10000,0),int)
 rho=correlation(x,y);r1ci=ci(draws(x,y,ix)) if n>1 else ci([])
 r1={'rho':rho,'n':n,**r1ci,'met':rho is not None and rho>=.50 and r1ci['ci95'] is not None and r1ci['ci95'][0]>0}
 subset=[r for r in records if r['D'] is not None];m=len(subset)
 if m>1:
  xx=[r['persistence'] for r in subset];yy=[r['Oracle'] for r in subset];dd=[r['D'] for r in subset]
  ix2=rng.integers(0,m,(10000,m));rp=correlation(xx,yy);rd=correlation(dd,yy)
  delta=rp-rd if rp is not None and rd is not None else None
  dc=ci(draws(xx,yy,ix2)-draws(dd,yy,ix2))
 else:rp=rd=delta=None;dc=ci([])
 r2={'n':m,'rho_persistence':rp,'rho_D':rd,'difference':delta,**dc,'met':delta is not None and delta>0 and dc['ci95'] is not None and dc['ci95'][0]>0}
 high=[r for r in records if r['persistence']>=16];low=[r for r in records if r['persistence']<=8]
 h=sum(r['Oracle']>=.65 for r in high);l=sum(r['Oracle']<=.65 for r in low)
 r3={'high_n':len(high),'high_hits':h,'low_n':len(low),'low_hits':l,'status':'NOT_EVALUABLE' if not high or not low else ('MET' if h>len(high)/2 and l>len(low)/2 else 'NOT_MET')}
 controls={}
 for key in ['probe','NLA']:
  s=[r for r in records if r[key] is not None];m=len(s)
  if m>1:
   xx=[r['persistence'] for r in s];yy=[r[key] for r in s];ix3=rng.integers(0,m,(10000,m));controls[key]={'n':m,'rho':correlation(xx,yy),**ci(draws(xx,yy,ix3))}
  else:controls[key]={'n':m,'rho':None,**ci([])}
 return {'R1':r1,'R2':r2,'R3':r3,'controls':controls,'falsifier':{'rho_le020':rho is not None and rho<=.20,'short_sayable_rows':[r['key'] for r in low if r['Oracle']>=.80]}}


def classified_persistence(item, following_ids, decode):
 initial=state(item,decode(item['ids']))
 status='undetermined' if initial is None else 'agree' if initial==item['value'] else 'disagree'
 if status!='agree':return None,status
 return persistence(item['ids'],following_ids,item['value'],decode,lambda text:state(item,text)),status

def persist(output,expected):
 verify(HERE,'STATE_FUNCTION_SEAL.json');sf=read(HERE/'STATE_FUNCTION_SEAL.json')
 for n,h in sf['external_sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('state helper changed')
 inv=read(HERE/'INVENTORY.json');private=HERE/'cache/prepared/private_items.json'
 if sha(private)!=inv['private_items_sha256']:raise ValueError('private inventory identity')
 verify(output,'FOLLOWING_TEXT_SEAL.json',expected)
 prov=read(output/'PROVENANCE.json')
 if prov['status']!='COMPLETE' or prov['state_seal_sha256']!=read(HERE/'REINVOCATION_BINDING.json')['acquisition_state_seal_sha256'] or prov['input_seal_sha256']!=inv['input_seal_sha256'] or prov['plan_sha256']!=sha(HERE/'RUN_PLAN.json'):raise ValueError('continuation provenance mismatch')
 items=read(private);following=rows(output/'continuations.jsonl');byid={r['key']:r for r in following}
 if len(following)!=len(items) or set(byid)!={r['key'] for r in items}:raise ValueError('following text grid')
 from transformers import PreTrainedTokenizerFast
 tokpath=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
 if sha(tokpath)!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42':raise ValueError('tokenizer')
 tok=PreTrainedTokenizerFast(tokenizer_file=str(tokpath))
 decode=lambda ids:tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
 out=HERE/'persistence_clarification2_2026-10-26';out.mkdir(exist_ok=False);(out/'cache').mkdir()
 dump(out/'STARTED.json',{'at':datetime.now(timezone.utc).isoformat(),'following_seal':expected,'state_seal':sha(HERE/'STATE_FUNCTION_SEAL.json'),'score_joined':False})
 ledger=[]
 for item in items:
  r=byid[item['key']]
  import hashlib,json
  digest=hashlib.sha256(json.dumps(item['ids'],separators=(',',':')).encode()).hexdigest()
  if r['prefix_ids_sha256']!=digest:raise ValueError('continuation prefix mismatch')
  k,k0_status=classified_persistence(item,r['following_ids'],decode)
  ledger.append({'key':item['key'],'bank':item['bank'],'feature':item['feature'],'persistence':k,'k0_status':k0_status})
 summaries=[]
 for bank,names in inv['rows'].items():
  for feature in names:
   group=[r for r in ledger if r['bank']==bank and r['feature']==feature];vals=[r['persistence'] for r in group if r['persistence'] is not None]
   excluded=len(group)-len(vals);ok=bool(vals) and excluded/len(group)<=.20
   summaries.append({'key':bank+':'+feature,'bank':bank,'feature':feature,'n':len(group),'excluded':excluded,'excluded_undetermined':sum(r['k0_status']=='undetermined' for r in group),'excluded_disagree':sum(r['k0_status']=='disagree' for r in group),'evaluable':ok,'median':float(np.median(vals)) if vals else None})
 dump(out/'cache/ITEM_PERSISTENCE.json',ledger);dump(out/'ROW_PERSISTENCE.json',summaries)
 seal(out,['STARTED.json','cache/ITEM_PERSISTENCE.json','ROW_PERSISTENCE.json'],'PERSISTENCE_SEAL.json')
 return out


def load_scores():
 # Called only after PERSISTENCE_SEAL exists and verifies. No earlier score adapter.
 result={};source={}
 bindings=read(HERE/'SCORE_INPUTS.json')
 for rel,digest in bindings['seal_hashes'].items():
  if sha(ROOT/rel)!=digest:raise ValueError('frozen score seal identity changed')
 for bank,path in [('W1','results/g_agreement/blindspot/w1/analysis'),('W12','results/g_agreement/blindspot/w12/analysis_gxzcklh33qpr8h')]:
  folder=ROOT/path;verify(folder,'ANALYSIS_SEAL.json');source[bank]=sha(folder/'ANALYSIS_SEAL.json')
  cells=read(folder/'metrics.json')['rows']
  for c in cells:
   if (c['reader'],c['layer']) not in [('olens',44),('nla',42)]:continue
   r=result.setdefault(bank+':'+c['feature'],{'Oracle':None,'NLA':None,'probe':None,'D':None})
   value=c.get('true');v=value.get('auroc') if isinstance(value,dict) else value
   if c['status']=='EVALUABLE':r['Oracle' if c['reader']=='olens' else 'NLA']=v
   if c['reader']=='olens':r['probe']=c.get('probe_auroc')
 folder=HERE.parent/'e36/analysis_overnight149';verify(folder,'ANALYSIS_SEAL.json');source['E36']=sha(folder/'ANALYSIS_SEAL.json')
 for f,c in read(folder/'METRICS.json')['metrics'].items():result['E36:'+f]={'Oracle':c['oracle_descriptive'],'NLA':c['nla'],'probe':c['probe'],'D':None}
 folder=HERE.parent/'e25/analysis_0jexpj58lbtuk9';verify(folder,'ANALYSIS_SEAL.json');source['E25']=sha(folder/'ANALYSIS_SEAL.json')
 for r in read(folder/'SUMMARY.json')['rows']:
  key='W1:'+r['feature']
  if key in result:result[key]['D']=r['D']
 folder=HERE.parent/'e29/w12_values';verify(folder,'VALUES_SEAL.json');source['E29']=sha(folder/'VALUES_SEAL.json')
 for r in read(folder/'METRICS.json')['rows']:result['W12:'+r['feature']]['D']=r['D']
 return result,source


def join(folder):
 verify(folder,'PERSISTENCE_SEAL.json')
 table=read(folder/'ROW_PERSISTENCE.json');scores,sources=load_scores();records=[];excluded=[]
 for r in table:
  s=scores.get(r['key'])
  if not r['evaluable'] or s is None or s['Oracle'] is None:excluded.append(r['key']);continue
  records.append({'key':r['key'],'bank':r['bank'],'feature':r['feature'],'persistence':r['median'],**s})
 out=HERE/'analysis_clarification2_2026-10-26';out.mkdir(exist_ok=False)
 report={'experiment':'E42','rows':records,'excluded_rows':excluded,'rules':tests(records),'source_seals':sources,'persistence_seal':sha(folder/'PERSISTENCE_SEAL.json'),'row_bootstrap':10000,'seed':20261026,'continuation':'model-expected','content':'Not pooled; no semantic state function registered by this lexical implementation.'}
 dump(out/'METRICS.json',report);(out/'RESULTS.md').write_text('# E42 registered analysis\n\n```json\n'+__import__('json').dumps(report,indent=2)+'\n```\n')
 seal(out,['METRICS.json','RESULTS.md'],'ANALYSIS_SEAL.json')
 print({'persistence_seal':report['persistence_seal'],'analysis_seal':sha(out/'ANALYSIS_SEAL.json'),'rules':report['rules']})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('--clarification2',action='store_true',required=True);a=p.parse_args()
 dump(HERE/'ANALYSIS_ATTEMPT_clarification2.lock.json',{'at':datetime.now(timezone.utc).isoformat(),'authority':'§151 clarification 2: single authorized re-invocation'})
 verify(HERE,'CODE_SEAL.json')
 r=read(a.receipt)
 if r.get('issuer')!='integrator' or r.get('verified') is not True or r.get('experiment')!='E42':raise ValueError('verified integrator receipt required')
 binding=read(HERE/'REINVOCATION_BINDING.json')
 if r['following_text_seal_sha256']!=binding['following_text_seal_sha256']:raise ValueError('original following-text seal required')
 if sha(HERE/'RUN_PLAN.json')!=binding['acquisition_plan_sha256']:raise ValueError('acquisition plan changed')
 for name,h in binding['preserved_failed_artifacts'].items():
  if sha(HERE/name)!=h:raise ValueError('failed attempt custody changed')
 folder=persist(Path(r['output_directory']),r['following_text_seal_sha256']);join(folder)
