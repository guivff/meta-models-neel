"""§231 E120c prospective extraction and balanced accuracy; no model calls."""
import re
from projects.g_agreement.understand.wmech2 import core as c

def extract(text):
    if text is None:return None
    c.require(isinstance(text,str),'original readout text')
    m=re.match(r'^\s*(yes|no)\b',text,re.IGNORECASE)
    return None if m is None else m.group(1).lower()=='yes'

def summarize(rows):
    c.unique(rows)
    c.require(len(rows)==800,'400 test items x targeted/sham')
    ids={x['item_id'] for x in rows};c.require(len(ids)==400,'original400 test IDs')
    c.require({(x['item_id'],x['arm']) for x in rows}=={(i,a) for i in ids for a in ('targeted','sham')},'full paired arm grid')
    out={}
    for arm in ('targeted','sham'):
        xs=[x for x in rows if x['arm']==arm]
        c.require(all(x['genre'] in (0,1) and x['addressed'] in (0,1) and (x['yes'] is None or type(x['yes']) is bool) for x in xs),'factor and extraction types')
        c.require(all(sum(x['genre']==g and x['addressed']==a for x in xs)==100 for g in (0,1) for a in (0,1)),'original100 per cell')
        rates={}
        for label in (0,1):
            group=[x for x in xs if x['addressed']==label];kept=[x for x in group if x['yes'] is not None]
            rates[label]=dict(total=len(group),kept=len(kept),missing=len(group)-len(kept),correct=sum(x['yes']==bool(label) for x in kept),rate=sum(x['yes']==bool(label) for x in kept)/len(kept) if kept else None)
        kept=[x for x in xs if x['yes'] is not None]
        out[arm]=dict(by_addressed=rates,balanced_accuracy=sum(z['rate'] for z in rates.values())/2 if all(z['rate'] is not None for z in rates.values()) else None,yes_rate=sum(x['yes'] for x in kept)/len(kept) if kept else None,missing=400-len(kept))
    c.require({x['item_id']:(x['genre'],x['addressed']) for x in rows if x['arm']=='targeted'}=={x['item_id']:(x['genre'],x['addressed']) for x in rows if x['arm']=='sham'},'paired source factors unchanged')
    return out


def readings(summary):
    t,s=summary['targeted'],summary['sham'];ba=t['balanced_accuracy'];sham=s['yes_rate']
    complete=t['missing']==s['missing']==0
    rates=s['by_addressed']
    # Within each addressed class, recover yes rate from the recorded accuracy.
    no=rates[0]['rate'];yes=rates[1]['rate']
    difference=None if no is None or yes is None else yes-(1-no)
    return dict(targeted_reading='NOT EVALUABLE' if not complete else 'INVALIDATED BY SHAM' if sham>=.70 else 'reporting-priority failure' if ba>=.75 and sham<=.60 else 'not recoverable by asking' if ba<=.60 else 'intermediate',
                sham_invalidates=None if s['missing'] else sham>=.70,
                sham_yes_by_addressed={'0':None if no is None else 1-no,'1':yes},
                sham_addressed_minus_unaddressed=difference,cue_driven_yes_bias=None if difference is None else round(difference,12)>=.20,
                missing_policy='Rates use known extractions with denominators; readings require complete targeted and sham extractions; unavailable outcomes never become no')
