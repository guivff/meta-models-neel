"""E90 registered lexical analysis; consumes frozen CPU-only bindings, never calls APIs."""
import argparse,datetime,hashlib,json,random
from pathlib import Path
import numpy as np
import style90

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--private-home',type=Path,required=True);a.add_argument('--pairing-freeze',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args();h=args.private_home;freeze=json.loads(args.pairing_freeze.read_text())
 for name,key in [('JOINED.PRIVATE.json','joined_private_sha256'),('ORACLE_SOURCES.PRIVATE.json','oracle_source_inventory_sha256'),('CONTROL_PAIRINGS.PRIVATE.json','pairing_map_sha256')]:assert sha(h/name)==freeze[key],name
 assert sha(Path(style90.__file__))==freeze['style_rule_sha256']
 assert freeze['before_lexical_scoring'] and freeze['scoring_run'] is False
 assert not args.output.exists(),'EXCLUSIVE_ANALYSIS_OUTPUT_ALREADY_EXISTS'
 joined=json.loads((h/'JOINED.PRIVATE.json').read_text());items={r['id']:r for r in joined if r['arm']=='plain_continuation'};assert len(items)==3688
 sources=json.loads((h/'ORACLE_SOURCES.PRIVATE.json').read_text());pairs=json.loads((h/'CONTROL_PAIRINGS.PRIVATE.json').read_text());mis={r['real_item_id']:r['mismatched_item_id'] for r in pairs['mismatched']};assert set(mis)==set(items) and set(mis.values())==set(items) and all(k!=v for k,v in mis.items())
 intake=json.loads((h/'E76_RANDOM_SOURCE_INTAKE.private.json').read_text());source=Path(intake['source']);assert sha(source)==freeze['E76_oracle_source_sha256'];randoms={r['id']:r for r in map(json.loads,source.read_text().splitlines()) if r['arm']=='random'};assert len(randoms)==500
 real=[];placebo=[]
 for key,r in sorted(items.items()):
  text=sources[r['bank']][r['source_id']]['text'];c=style90.classify(text);row=dict(id=key,bank=r['bank'],source_id=r['source_id'],**c)
  row.update(real_overlap=style90.jaccard(text,r['generated_text']),mismatched_overlap=style90.jaccard(text,items[mis[key]]['generated_text']));real.append(row)
 for p in pairs['random_vector']:
  r=randoms[p['random_vector_id']];item=items[p['assigned_item_id']];placebo.append(dict(id=r['id'],assigned_item_id=item['id'],**style90.classify(r['text']),overlap=style90.jaccard(r['text'],item['generated_text'])))
 assert len(placebo)==500 and {r['id'] for r in placebo}==set(randoms)
 selected=[r for r in real if r['continuation_style'] is True]
 def rate(rows):
  evaluable=sum(r['evaluable'] for r in rows);continuation=sum(r['continuation_style'] is True for r in rows)
  return dict(total=len(rows),evaluable=evaluable,no_bullets=len(rows)-evaluable,continuation_style=continuation,rate_among_evaluable=continuation/evaluable if evaluable else None,rate_among_all=continuation/len(rows) if rows else None)
 summary=dict(experiment='E90',rule='R-TB1 / section201',analysis_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),real_style=rate(real),random_style=rate(placebo),bank_style={b:rate([r for r in real if r['bank']==b]) for b in sorted(sources)},pairing_freeze_sha256=sha(args.pairing_freeze),analysis_code_sha256=sha(Path(__file__)),bootstrap_seed=20261028,bootstrap_replicates=10000,CI='two-sided percentile95%; item resampling; real/mismatch paired, random assigned-item sample independent',random_overlap_population='all500 E76 random-vector Oracle records per registration; no continuation-style selection',judging_calls=0)
 if selected:
  x=np.array([r['real_overlap'] for r in selected]);y=np.array([r['mismatched_overlap'] for r in selected]);z=np.array([r['overlap'] for r in placebo]);rng=np.random.default_rng(20261028);paired=[];independent=[]
  for _ in range(10000):
   ids=rng.integers(len(x),size=len(x));zp=rng.integers(len(z),size=len(z));paired.append(float(np.mean(x[ids]-y[ids])));independent.append(float(np.mean(x[ids])-np.mean(z[zp])))
  lower_mismatch,upper_mismatch=map(float,np.quantile(paired,[.025,.975]));lower_random,upper_random=map(float,np.quantile(independent,[.025,.975]));dx=float(x.mean()-y.mean());dz=float(x.mean()-z.mean())
  summary.update(continuation_style_real_n=len(selected),real_mean=float(x.mean()),mismatched_mean=float(y.mean()),random_mean=float(z.mean()),difference_vs_mismatch=dx,difference_vs_random=dz,CI_vs_mismatch=[lower_mismatch,upper_mismatch],CI_vs_random=[lower_random,upper_random],R_TB1='MET' if dx>=.05 and dz>=.05 and lower_mismatch>0 and lower_random>0 else 'NOT_MET',falsifier=bool(float(x.mean())<=float(y.mean())+.01))
 else:summary.update(R_TB1='NOT_EVALUABLE',reason='No continuation-style real Oracle readouts',falsifier=None)
 args.output.mkdir();dump(args.output/'REAL_SCORES.PRIVATE.json',real);dump(args.output/'RANDOM_SCORES.PRIVATE.json',placebo);dump(args.output/'SUMMARY.json',summary);dump(args.output/'ANALYSIS_SEAL.json',dict(status='COMPLETE',files={p.name:sha(p) for p in args.output.iterdir()},source_bindings_verified_sha256=sha(h/'SOURCE_BINDINGS_VERIFIED.private.json'),pairing_map_sha256=freeze['pairing_map_sha256'],old_E73_analysis_rerun=False))
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
