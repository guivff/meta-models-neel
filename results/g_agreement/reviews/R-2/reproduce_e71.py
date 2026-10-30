"""Independent E71 aggregate reproduction. Private joins remain in memory only."""
import argparse,json,hashlib,collections,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from common.stats import bootstrap_ci,wilson
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def kap(rows):
 a,b=np.asarray(rows).T;n=len(a)
 pe=sum(np.count_nonzero(a==v)*np.count_nonzero(b==v) for v in set(a)|set(b))/n**2
 return (np.mean(a==b)-pe)/(1-pe) if pe<1 else float('nan')
def collapse(x,t):
 if x['category']!='states_value' or len(set(x['values']))!=1:return 'other'
 return 'correct' if x['values'][0]==t else 'wrong'
def stats(pairs,truth=True):
 hm=[h for h,j,t in pairs];jm=[j for h,j,t in pairs]
 a=np.array([[collapse(h,t),collapse(j,t)] for h,j,t in pairs]);b=np.array([[h['category'],j['category']] for h,j,t in pairs])
 out={'n':len(pairs),'agree_4cat':float(np.mean(b[:,0]==b[:,1])),'kappa_4cat':kap(b)}
 if truth:out.update(kappa_cww_CI=bootstrap_ci(a,kap,n_boot=2000,seed=20261030),agree_cww=float(np.mean(a[:,0]==a[:,1])),confusion_cww=dict(collections.Counter('|'.join(x) for x in a)))
 fy=sum(h['category']!='states_value' and j['category']=='states_value' for h,j,t in pairs);fn=sum(h['category']=='states_value' and j['category']!='states_value' for h,j,t in pairs)
 ny=sum(h['category']!='states_value' for h in hm);nn=len(hm)-ny
 out.update(false_yes=[fy,ny,*wilson(fy,ny)],false_no=[fn,nn,*wilson(fn,nn)],agree_code_and_value=sum(h['category']==j['category'] and set(h['values'])==set(j['values']) for h,j,t in pairs)/len(pairs))
 return out

def main():
 p=argparse.ArgumentParser()
 for name in ('human','key','spot-human','e104-private','e104-judgments','output'):p.add_argument('--'+name,required=True)
 a=p.parse_args();k=read(a.key);h=lines(a.human);km={x['opaque_id']:x for x in k}
 assert len(km)==len(h)==100 and set(km)=={x['id'] for x in h}
 valid=lambda x:x['judge'] and x['judge']['category'] in {'states_value','silent','exhibits','names_property_without_value'}
 out={}
 for name,reader in [('all',None),('oracle','oracle'),('nla','nla')]:
  pairs=[(x,km[x['id']]['judge'],km[x['id']]['true_value']) for x in h if valid(km[x['id']]) and (reader is None or km[x['id']]['reader']==reader)]
  out[name]=stats(pairs)
 out['missing_by_bank']=dict(collections.Counter(x['bank'] for x in k if not valid(x)))
 out['missing_detail']=dict(collections.Counter('no_reference' if not x['judge'] else x['judge']['category'] for x in k if not valid(x)))
 m={x['opaque_id']:x for x in read(a.e104_private)};j={x['id']:x for x in read(a.e104_judgments)};s=lines(a.spot_human)
 assert len(s)==len({x['id'] for x in s})==40
 out['spotcheck']={row or 'all':stats([(x,j[x['id']],None) for x in s if row is None or m[x['id']]['row']==row],False) for row in (None,'fact_recall','language_plan')}
 out['input_hashes']={n:sha(getattr(a,n)) for n in ('human','key','spot_human','e104_private','e104_judgments')}
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
