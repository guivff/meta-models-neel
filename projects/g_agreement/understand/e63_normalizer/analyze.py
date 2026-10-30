"""Integrator-only once entry point for the full normalized E63 inventory.
Uses registered regex coding and item bootstrap; never rebuilds or reclassifies a bank.
"""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from .normalize import HERE,read,write,sha,require,verify,verify_config,validate,committed
from projects.g_agreement.readerbench.scoring import coded,cluster_draws,ci,placebo_labels

def patterns(f):
 require(f['policy']=='whole_word_or_frozen_regex' and len(f['patterns'])==2,'frozen binary regex policy')
 prefix='(?i)' if f['ignore_case'] else ''
 return dict(zip(('A','B'),[prefix+p for p in f['patterns']]))

def real_scores(row):
 scores=[];naming=[]
 for x in row['readouts']:
  s,n=coded([x],patterns(row['frozen_regex']['families'][x['family']]))
  scores.extend(s);naming.extend(n)
 return np.array(scores,dtype=float),np.array(naming,dtype=float)

def pool_scores(row,pool):
 # Each vector is one bootstrap cluster, shared across the row's frozen families.
 # Fixed family weights are the actual frozen84-item population, never outcomes.
 counts=Counter(x['family'] for x in row['readouts']);total=sum(counts.values())
 labeled=placebo_labels(pool);s=np.zeros(len(pool));n=np.zeros(len(pool))
 for family,count in counts.items():
  ss,nn=coded(labeled,patterns(row['frozen_regex']['families'][family]));s+=np.asarray(ss)*count/total;n+=np.asarray(nn)*count/total
 return s,n

def metric(records,s,n):
 return dict(n_readouts=len(records),n_items=len({x['item_id'] for x in records}),S=float(np.mean(s)),S_ci=ci(cluster_draws(records,s)),N=float(np.mean(n)),N_ci=ci(cluster_draws(records,n)),coding='regex')

def score_row(row,pools):
 result={k:row[k] for k in ('bank','row','reader','native_status','native_status_source','acquisition_status','analysis_seal_sha256','regex_status','regex_reason')}
 if row['regex_status']!='AVAILABLE':
  result.update(metric=None,placebo_regex={arm:dict(status='NOT_EVALUABLE',reason=row['regex_reason'],R_P1='NOT_EVALUABLE') for arm in ('random','shuffled')});return result
 real=row['readouts'];rs,rn=real_scores(row);result['metric']=metric(real,rs,rn);result['placebo_regex']={}
 for arm in ('random','shuffled'):
  pool=[x for x in pools if x['reader']==row['reader'] and x['arm']==arm];ps,pn=pool_scores(row,pool)
  delta=float(np.mean(rs)-np.mean(ps));interval=ci(cluster_draws(real,rs)-cluster_draws(pool,ps,seed=20261028))
  result['placebo_regex'][arm]=dict(real=result['metric'],placebo=metric(pool,ps,pn),delta_S_regex=delta,delta_ci=interval,
   R_P1=('PASS' if delta>=.20 and interval[0]>0 else 'FAIL') if row['native_status']=='REPORTED' else ('NOT_EVALUABLE' if row['native_status']=='NOT_EVALUABLE' else 'NOT_APPLICABLE'))
 return result

def load(cfg):
 receipt=read(cfg['receipt_destination']);require(receipt['verified'] is True and receipt['issuer']=='W-mech2','delegated verified normalizer receipt')
 require(receipt['spec_sha256']==sha(HERE/'SPEC.json') and receipt['e63_output_seal_sha256']==sha(cfg['e63_output']),'receipt bindings')
 root=Path(cfg['destination']);verify(root/'INPUT_SEAL.json',receipt['input_seal_sha256']);authority=read(root/'RECEIPT.json')
 require(authority['verified'] is True and authority['issuer']=='W-mech2' and authority['authority']==cfg['authority'] and authority['spec_sha256']==sha(HERE/'SPEC.json'),'truthful normalization authority')
 require(authority['source_files']==cfg['files'] and {x['path']:x['sha256'] for x in authority['source_seals']}==cfg['seals'],'complete source receipt')
 verify_config(cfg);data=read(root/'DATA.json');validate(data)
 # Independent checks against immutable pool export and prospective source schemas.
 require(data['placebo']==read(Path(cfg['pool']).parent/'POOLS.json'),'unchanged800 pool including order')
 from .normalize import build_bank
 cat=read(cfg['catalog'])['rows'];expected=[];extras={}
 for bank in data['banks']:
  rr,ee=build_bank(bank,cfg['banks'][bank],{r['row']:r for r in cat if r['bank']==bank});expected+=rr;extras[bank]=ee
 require(data['rows']==expected and data['non_native_records']==extras,'lossless normalization independently reconstructed')
 return data,receipt

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');args=p.parse_args();committed();cfg=read(HERE/'SPEC.json');data,receipt=load(cfg)
 if args.verify_only:
  print('Full bundle and all source bindings verified; no scoring or once guard touched.');return
 out=Path(cfg['analysis_out']);guard=Path(cfg['guard']);require(not out.exists(),'original analysis output already exists');guard.parent.mkdir(parents=True,exist_ok=True)
 with guard.open('x') as f:f.write(receipt['input_seal_sha256']+'\n')
 try:
  result={r:dict(reader=r,rows=[score_row(x,data['placebo']) for x in data['rows'] if x['reader']==r]) for r in ('oracle','nla')}
  out.mkdir(parents=True,exist_ok=False);write(out/'REGEX_RESULTS.json',result)
  write(out/'R_P2_STATUS.json',dict(status='SEPARATE_W_INTERNALS_CODING_COMMAND',matching_reader_MISSED_reference_required=True,no_judge_calls=True))
  write(out/'ANALYSIS_SEAL.json',dict(experiment='E63',status='COMPLETE_ONCE',input_seal_sha256=receipt['input_seal_sha256'],output_seal_sha256=receipt['e63_output_seal_sha256'],normalizer_receipt_sha256=sha(cfg['receipt_destination']),files={n:sha(out/n) for n in ('REGEX_RESULTS.json','R_P2_STATUS.json')}))
 except BaseException as exc:
  write(guard.with_name('REGEX_FAILURE.json'),dict(error_type=type(exc).__name__,input_seal_sha256=receipt['input_seal_sha256']));raise
if __name__=='__main__':main()
