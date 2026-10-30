"""Join stratification values only after codes/keyword flags are sealed."""
from collections import Counter
import numpy as np
from common.stats import wilson
from . import io as I,protocol as P

def rate(k,n):
 if not n:return {'k':k,'n':n,'rate':None,'ci95':None}
 p,l,h=wilson(k,n);return {'k':k,'n':n,'rate':float(p),'ci95':[float(l),float(h)]}
def paired(records):
 ids=sorted(records);n=len(ids)
 if not n:return {'n_items':0,'mention_difference':None,'mention_ci95':None,'accuracy_difference':None,'accuracy_ci95':None}
 # Columns: Oracle mention, NLA mention, Oracle correct, NLA correct.
 a=np.array([[records[i][r][k] for r,k in [('oracle','mention'),('nla','mention'),('oracle','correct'),('nla','correct')]] for i in ids],float)
 rng=np.random.default_rng(I.SEED);d=a[:,1]-a[:,0];mention=[];acc=[]
 for _ in range(2000):
  b=a[rng.integers(0,n,n)];mention.append(float(np.mean(b[:,1]-b[:,0])))
  if b[:,0].sum() and b[:,1].sum():acc.append(float(b[:,3].sum()/b[:,1].sum()-b[:,2].sum()/b[:,0].sum()))
 point=float(a[:,3].sum()/a[:,1].sum()-a[:,2].sum()/a[:,0].sum()) if a[:,0].sum() and a[:,1].sum() else None
 return {'n_items':n,'mention_difference':float(d.mean()),'mention_ci95':np.quantile(mention,[.025,.975]).tolist(),'accuracy_difference':point,'accuracy_ci95':np.quantile(acc,[.025,.975]).tolist() if len(acc)>=1900 else None,'accuracy_valid_bootstrap_draws':len(acc),'direction':'NLA minus Oracle; item paired'}
def analyse():
 seal=I.read(I.OUT/'CODING_SEAL.json');manifest=I.read(I.OUT/'POOL_MANIFEST.json')
 if I.sha(I.CACHE/'codes.blind.json')!=seal['sha256']:raise RuntimeError('code seal changed')
 for n,h in manifest['files'].items():
  if I.sha(I.CACHE/n)!=h:raise RuntimeError('frozen sample changed')
 codes={r['case_id']:r for r in I.read(I.CACHE/'codes.blind.json')};pool=I.rows(I.CACHE/'pool.private.jsonl')
 # First post-code metric label join; sampler used values only for authorized stratification.
 selected={r['id']:r for r in I.rows(I.CACHE/'sample.private.DO_NOT_SEND.jsonl')};rows=[];differences=[]
 for feature in sorted(P.QUESTIONS):
  records={}
  for reader in ['oracle','nla']:
   rs=[r for r in pool if r['feature']==feature and r['reader']==reader];valid=[];kw=0;disagree=0;evidence_issues=0
   for r in rs:
    c=codes[r['case_id']];kw+=c['keyword']
    if c['status']!='OK':continue
    v=c['code'];m=v['mentions'];native=P.QUESTIONS[feature]['values'];truth=selected[r['item_id']]['value'];correct=m and v['value'] in ['A','B'] and native[['A','B'].index(v['value'])]==truth
    valid.append((m,correct));disagree+=m!=c['keyword'];evidence_issues+=v['evidence_quality_issue'];records.setdefault(r['item_id'],{})[reader]={'mention':m,'correct':correct}
   mentions=sum(x[0] for x in valid);missing=len(rs)-len(valid)
   rows.append({'feature':feature,'reader':reader,'layer':44 if reader=='oracle' else 42,'sample_n':len(rs),'valid_n':len(valid),'missing':missing,'mention':rate(mentions,len(valid)),'accuracy_among_mentions':rate(sum(x[1] for x in valid),mentions),'mention_rate_missing_bounds':[mentions/len(rs),(mentions+missing)/len(rs)],'keyword':rate(kw,len(rs)),'judge_keyword_disagreements':disagree,'evidence_quality_flags_not_exclusions':int(evidence_issues)})
  differences.append({'feature':feature,**paired({k:v for k,v in records.items() if set(v)=={'oracle','nla'}})})
 result={'section':101,'status':'COMPLETE_USER_NARROWED_SAMPLE_DESCRIPTIVE','rows':rows,'paired_differences':differences,'api_cost':seal['api_cost'],'scope':'150 distinct matched W1 test states, two rows only,75 per row; one sample/state/reader. No §84 and no unsealed outputs.','unavailable':'Other14 W1 structure rows unavailable; all §84 excluded until E13(a) seals both readers for a second sample.','bootstrap':'2000 item-paired draws,seed20261024; conditional accuracy CI unavailable if <1900 draws have mentions in both readers. No labels/reader names sent to judge.'}
 I.save(I.OUT/'METRICS.json',result)
 lines=['# E13(b) §101 — matched sealed W1 mention sample','','**Prediction:** Oracle mentions structure in under10% of readouts; NLA mentions more and can identify the value. **Scope:** only prose_paren and table_column; this cannot adjudicate all16 W1 structure rows or the §84 follow-up. Results below are descriptive.','',result['scope'],'','| Row | Reader/site | Valid / sample | Mentions | Mention rate [Wilson95%] | Correct / mentions | Accuracy [Wilson95%] | Keyword flags | Judge/keyword disagreements |','|---|---|---:|---:|---|---:|---|---:|---:|']
 fmt=lambda x:'UNAVAILABLE' if x['rate'] is None else f"{x['rate']:.3f} [{x['ci95'][0]:.3f}, {x['ci95'][1]:.3f}]"
 for r in rows:
  m=r['mention'];a=r['accuracy_among_mentions'];lines.append(f"| {r['feature']} | {r['reader']} L{r['layer']} | {r['valid_n']}/{r['sample_n']} | {m['k']} | {fmt(m)} | {a['k']}/{a['n']} | {fmt(a)} | {r['keyword']['k']}/{r['keyword']['n']} | {r['judge_keyword_disagreements']} |")
 lines+=['','| Row | Paired items | NLA − Oracle mention rate [bootstrap95%] | Conditional accuracy difference [bootstrap95%] |','|---|---:|---|---|']
 for d in differences:
  value=lambda p,c:'UNAVAILABLE' if p is None or c is None else f'{p:.3f} [{c[0]:.3f}, {c[1]:.3f}]'
  lines.append(f"| {d['feature']} | {d['n_items']} | {value(d['mention_difference'],d['mention_ci95'])} | {value(d['accuracy_difference'],d['accuracy_ci95'])} |")
 oracle=[r for r in rows if r['reader']=='oracle'];nl=[r for r in rows if r['reader']=='nla'];low=all(r['mention']['rate'] is not None and r['mention']['rate']<.1 for r in oracle);more=all(d['mention_difference'] is not None and d['mention_difference']>0 for d in differences)
 lines+=['',f"**Prediction reading in this sample:** Oracle point mention rates below10% on both rows: {low}. NLA point mention rates higher on both rows: {more}. Value accuracy is evaluated only where a property is mentioned; zero mentions is UNAVAILABLE, not chance accuracy. No mechanism or whole-bank verdict follows.",'','The judge saw only an unchanged property question giving both possible values and the raw generated readout. Sampler metadata, true values, reader identities, source prompts and paths were not sent. Ground truth was used only for the user-authorized stratified selection, then withheld from metric joins until the coding seal. Raw strings include incomplete endings/source parser failures; no repair. Native44/42 sites differ, so this is not a same-vector comparison.','', 'Keyword flags are literal substring/word matches, not evidence of a current-state assertion or a correct value. Their disagreement with the judge is reported rather than resolved. Evidence quotes are audited separately, never used to discard otherwise valid primary codes. Invalid typed codes remain missing; no retry, repair or replacement. Wilson intervals treat sampled outputs as Bernoulli; item-paired bootstrap supplies the paired comparison. Missing-as-no/yes bounds and evidence flags are in METRICS.json.','',result['unavailable'],'',f"Route: Gemini3.1FlashLite via OpenRouter→Vertexglobal, ZDR/deny collection, own logging/data use verified off. API cost ${seal['api_cost']['actual_usd']} / $5 hard cap; unresolved reserve ${seal['api_cost']['unresolved_reserve_usd']};0GPU-h. Request count and exact policy audit in AUDIT.json."]
 (I.OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n');I.save(I.OUT/'ANALYSIS_SEAL.json',{'status':'USER_NARROWED_SAMPLE_COMPLETE','files':{n:I.sha(I.OUT/n) for n in ['METRICS.json','RESULTS.md']}})
 print([(r['feature'],r['reader'],r['mention']['k'],r['accuracy_among_mentions']['k'],r['valid_n']) for r in rows])
if __name__=='__main__':analyse()
