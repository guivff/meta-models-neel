"""c3b4f1ab: terminal unparseable codes are missing, never silent/zero.
Validation mirrors W-internals normalized evidence; codes remain untouched.
"""
import re,unicodedata
from stats_native import rate as original_rate,signed_value as original_signed,reported as original_reported
from contract56 import require

def normalize(text):
 quotes=dict.fromkeys('‘’‚‛',"'")|dict.fromkeys('“”„‟«»','"')
 return re.sub(r'\s+',' ',''.join(quotes.get(c,'-' if unicodedata.category(c)=='Pd' else c) for c in text)).strip().casefold()

def missing(j):return j.get('category')=='UNPARSEABLE'
def validate_judgment(j,text):
 require(set(j)=={'id','category','values','evidence'},'judge schema')
 if missing(j):
  require(j['values']==[] and j['evidence']=='','UNPARSEABLE sentinel');return
 require(j['category'] in {'states_value','names_property_without_value','exhibits','silent'},'judge category')
 v=j['values'];require(isinstance(v,list) and len(v)==len(set(v)) and set(v)<={'A','B'},'judge values')
 require(bool(v)==(j['category']=='states_value'),'category/value mismatch')
 require(isinstance(j['evidence'],str),'judge evidence type');e=normalize(j['evidence'])
 require(e in normalize(text) and (bool(e) or j['category']=='silent'),'normalized evidence')
def signed_value(j,label):return None if missing(j) else original_signed(j,label)
def rate(matrix):
 # Acquired single-readout design: preserve each retained item/direction as a unit.
 require(all(len(x)==1 for x in matrix),'single readout per independent unit')
 kept=[x for x in matrix if x[0] is not None]
 if not kept:return {'S':None,'CI95':None,'items':0,'readouts':0,'status':'NOT EVALUABLE','reason':'no parseable judgments'}
 return original_rate(kept)
def reported(r,threshold=.2):return r['S'] is not None and original_reported(r,threshold)
def audit(native,jj):
 groups={};pool=[]
 for x in native:
  j=jj[x['id']]
  if 'category' not in j:continue # S6 binary eval-mention is a distinct measure.
  bad=missing(j);pool.append(bad);groups.setdefault((x['reader'],x['feature'],x.get('arm','text')),[]).append(bad)
 def counts(xs):
  u=sum(xs);n=len(xs);return {'total':n,'kept':n-u,'UNPARSEABLE':u,'over_5_percent':20*u>n}
 return {'authority':'c3b4f1ab','rows':{'|'.join(k):counts(v) for k,v in sorted(groups.items())},'pooled':counts(pool)}

def native_rates(data,jj):
    grouped={}
    for x in data['native']:
        kind=x['kind'];label=data['private'][x['unit_id']]['label'] if kind=='text' else int(x['direction_id'].endswith(':A'))
        key=(x['reader'],x['feature'],x.get('arm','text'));units=grouped.setdefault(key,{})
        units.setdefault(x['unit_id'],{})[x['repeat']]=signed_value(jj[x['id']],label)
    return {key:rate([[v[i] for i in range(1)] for _,v in sorted(units.items())]) for key,units in grouped.items()}


def metrics(private,native,jj):
 rates={};by={}
 for x in native:
  item=private[x['unit_id']]
  if item.get('state')=='S6':continue
  by.setdefault((x['reader'],item['feature']),[]).append((x['unit_id'],signed_value(jj[x['id']],item['label'])))
 for k,v in by.items():rates[k]=rate([[score] for _,score in sorted(v)])
 return rates

