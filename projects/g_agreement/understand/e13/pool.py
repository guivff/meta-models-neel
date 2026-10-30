"""Guiv's matched 150-state sample from sealed W1 only; no §84 inputs."""
from pathlib import Path
from collections import Counter
from . import io as I,protocol as P
W1=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/blindspot/w1-readonly-20261024')
def build():
 sources=[]
 def ref(p):p=Path(p);sources.append({'path':str(p),'sha256':I.sha(p),'bytes':p.stat().st_size});return p
 def verify(base,name):
  seal=I.read(ref(base/name))
  for n,h in seal['files'].items():
   if Path(n).is_absolute() or '..' in Path(n).parts or I.sha(base/n)!=h:raise ValueError('source seal mismatch')
  return seal
 bank=W1/'w1-bank-v2';verify(bank,'INPUT_SEAL.json')
 # Sampling necessarily uses values/splits, as explicitly authorized by stratification. No coding is joined here.
 labels=I.rows(ref(bank/'labels.DO_NOT_STAGE.jsonl'));inputs={x['id']:x for x in I.rows(ref(bank/'items.input.jsonl'))}
 rr={}
 for name,folder,filename,rname in [('oracle','target','unasked.target.jsonl','olens'),('nla','nla','unasked.nla.jsonl','nla')]:
  base=W1/'w1-units/priority'/folder;verify(base,'FREE_SEAL.json');rs=I.rows(ref(base/filename));rs=[x for x in rs if x['reader']==rname]
  rr[name]={(x['id'],x['sample']):x for x in rs}
  if len(rr[name])!=len(rs):raise ValueError('duplicate source readout')
 selected=[];pool=[];extra=int(I.rank('e13-stratum-extra')[:8],16)%2
 for rowindex,feature in enumerate(sorted(P.QUESTIONS)):
  for side,value in enumerate(P.QUESTIONS[feature]['values']):
   n=37+int(side==(extra+rowindex)%2)
   eligible=[x for x in labels if x['feature']==feature and x['split']=='test' and x['value']==value and any((x['id'],s) in rr['oracle'] and (x['id'],s) in rr['nla'] for s in [0,1])]
   eligible.sort(key=lambda x:I.rank('e13-item',feature,value,x['id']))
   if len(eligible)<n:raise ValueError('not enough matched test states in stratum')
   for x in eligible[:n]:
    iid=x['id'];samples=[s for s in [0,1] if (iid,s) in rr['oracle'] and (iid,s) in rr['nla']];sample=min(samples,key=lambda s:I.rank('e13-sample',iid,s))
    selected.append({'id':iid,'feature':feature,'value':value,'split':'test','sample':sample,'cluster':x['cluster']})
    for reader in ['oracle','nla']:
     r=rr[reader][iid,sample];text=r['raw']
     if not isinstance(text,str) or not text.strip() or inputs[iid]['feature']!=feature:raise ValueError('missing/mismatched raw generation')
     pool.append({'case_id':I.rank('e13-case',iid,sample,reader),'item_id':iid,'sample':sample,'feature':feature,'reader':reader,'layer':r['layer'],'raw':text,'raw_sha256':I.digest(text),'source_parser_status':r['status']})
 if len(selected)!=150 or len({x['id'] for x in selected})!=150 or len(pool)!=300:raise ValueError('sample size/uniqueness')
 I.jsonl(I.CACHE/'sample.private.DO_NOT_SEND.jsonl',selected);I.jsonl(I.CACHE/'pool.private.jsonl',sorted(pool,key=lambda x:x['case_id']))
 manifest={'section':101,'experiment':'E13b','seed':I.SEED,'scope':'Guiv narrowed to matched W1 prose_paren/table_column; §84 entirely excluded pending E13(a)','states':150,'readouts':300,'reader_counts':dict(Counter(x['reader'] for x in pool)),'strata':[{'feature':k[0],'value':k[1],'n_states':v} for k,v in sorted(Counter((x['feature'],x['value']) for x in selected).items())],'sampling':'Distinct test states only,75/row,37/38/value with opposite extra-cell allocation across rows. One common source sample0/1 per state chosen by seeded hash. Item selection by seeded hash within row/value. Both readers use same item and sample. Stratification uses sealed ground truth solely for selection; metric label join after coding seal.','sources':sources,'files':{n:I.sha(I.CACHE/n) for n in ['sample.private.DO_NOT_SEND.jsonl','pool.private.jsonl']},'excluded':'All §84 (including sealed NLA); all unsealed partial files; other14 W1 structure rows without paired sealed free readouts. No missing generation counted as nonmention.'}
 I.save(I.OUT/'POOL_MANIFEST.json',manifest);print({k:manifest[k] for k in ['states','readouts','reader_counts','strata']})
if __name__=='__main__':build()
