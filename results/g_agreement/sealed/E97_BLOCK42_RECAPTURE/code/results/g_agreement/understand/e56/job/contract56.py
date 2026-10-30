"""E56 shared custody and grid contract; imports no models."""
import sys,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
E49=HERE.parents[1]/'e49/job'
sys.path.insert(0,str(E49))
from contract49 import sha,read,dump,verify,seal,require,auc
SEED=20261026
BANK_SHA='e733bed854700d0129a7b59ed1e1e6ddf82947add11c2f3e77feb36bfb451112'
POD_CAP=3000

def deadline(a):
 require(a['slot'] in (0,1,2) and type(a['slot']) is int,'slot')
 require(a['gpu_count']==1 and a['cap_seconds']==POD_CAP,'allocation')
 require(math.isfinite(a['pod_created_epoch']) and math.isfinite(a['deadline_epoch']) and bool(a['pod_id']),'custody identity')
 require(a['deadline_epoch']==a['pod_created_epoch']+POD_CAP,'own creation deadline')
 return a['deadline_epoch']

def check_injection(vectors,items):
 import numpy as np
 require(vectors.shape==(36,5120) and vectors.dtype==np.float32 and np.isfinite(vectors).all(),'injection matrix')
 require(len(items)==36 and {x['index'] for x in items}==set(range(36)),'injection indices')
 require(len({(x['row'],x['variant']) for x in items})==12,'twelve directions')
 require({x['arm'] for x in items}=={'full','J','nonJ'},'registered injection arms')
 require(len({(x['row'],x['variant'],x['arm']) for x in items})==36,'unique direction-arm grid')

def direction_id(x):return x['row']+':'+x['variant']

def validate_judgment(x,text):
 require(set(x)=={'id','category','values','evidence'},'judge schema')
 require(x['category'] in {'states_value','names_property_without_value','exhibits','silent'},'judge category')
 require(x['values'] in [[],['A'],['B'],['A','B']],'judge value set')
 require(bool(x['values'])==(x['category']=='states_value'),'value/category mismatch')
 require(isinstance(x['evidence'],str) and (x['evidence'] in text),'verbatim evidence')
 require(bool(x['evidence'])==(x['category']!='silent'),'evidence required except silent')
