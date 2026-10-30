import json,math,collections,random
def kappa(a,b):
    n=len(a); cats=sorted(set(a)|set(b)); po=sum(x==y for x,y in zip(a,b))/n
    pa=collections.Counter(a); pb=collections.Counter(b); pe=sum(pa[c]*pb[c] for c in cats)/n/n
    return (po-pe)/(1-pe) if pe<1 else float('nan'), po
def boot(a,b,B=2000,seed=20261030):
    r=random.Random(seed); n=len(a); ks=[]
    for _ in range(B):
        ix=[r.randrange(n) for _ in range(n)]; k,_=kappa([a[i] for i in ix],[b[i] for i in ix])
        if not math.isnan(k): ks.append(k)
    ks.sort(); return ks[int(.025*len(ks))], ks[int(.975*len(ks))-1]
def wilson(k,n,z=1.96):
    if n==0: return (float('nan'),)*2
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
def cww(code,true):
    if code.get('category')!='states_value': return 'other'
    v=sorted(code.get('values',[]))
    if v==[true]: return 'correct'
    if len(v)==1: return 'wrong'
    return 'other'
out={}
key=json.load(open('/mnt/user-data/uploads/Activation_Readers/wt-blindspot-internals/cache/g_agreement/understand/e71/rebuild_24070152/KEY.DO_NOT_SHARE.json'))
hum={json.loads(l)['id']:json.loads(l) for l in open('review_in/E71_JUDGMENTS.jsonl')}
rows=[k for k in key if k['judge_reference_available'] and isinstance(k.get('judge'),dict) and k['judge'].get('category') in ('states_value','names_property_without_value','exhibits','silent')]
res={'n_packet':len(key),'n_with_judge':len(rows),'n_missing_judge':len(key)-len(rows)}
for name,sub in (('all',rows),('oracle',[r for r in rows if r['reader']=='oracle']),('nla',[r for r in rows if r['reader']=='nla'])):
    h=[cww(hum[r['opaque_id']],r['true_value']) for r in sub]; j=[cww(r['judge'],r['true_value']) for r in sub]
    k,po=kappa(h,j); lo,hi=boot(h,j)
    h4=[hum[r['opaque_id']]['category'] for r in sub]; j4=[r['judge']['category'] for r in sub]; k4,po4=kappa(h4,j4)
    hs=[x=='states_value' for x in h4]; js=[x=='states_value' for x in j4]
    fy=sum(jj and not hh for hh,jj in zip(hs,js)); fn=sum(hh and not jj for hh,jj in zip(hs,js)); hn=sum(not x for x in hs); hy=sum(hs)
    res[name]=dict(n=len(sub),kappa_cww=round(k,3),kappa_cww_CI=[round(lo,3),round(hi,3)],agree_cww=round(po,3),kappa_4cat=round(k4,3),agree_4cat=round(po4,3),
      judge_states_human_not=f'{fy}/{hn}',false_yes_rate=round(fy/hn,3) if hn else None,false_yes_wilson=[round(x,3) for x in wilson(fy,hn)],
      judge_not_human_states=f'{fn}/{hy}',false_no_rate=round(fn/hy,3) if hy else None,false_no_wilson=[round(x,3) for x in wilson(fn,hy)],
      confusion_cww={f'{a}|{b}':c for (a,b),c in collections.Counter(zip(h,j)).items()} )
res['R_H1']='MET' if res['all']['kappa_cww']>=0.70 else 'NOT MET'
dis=[dict(id=r['opaque_id'][:8],reader=r['reader'],property=r['property'],human=hum[r['opaque_id']]['category']+str(hum[r['opaque_id']]['values']),judge=r['judge']['category']+str(r['judge']['values']),true=r['true_value']) for r in rows if cww(hum[r['opaque_id']],r['true_value'])!=cww(r['judge'],r['true_value'])]
res['disagreements']=dis
# spotcheck
sk=json.load(open('e71x/SPOTCHECK_JUDGE_KEY_DO_NOT_OPEN.json')); pk={r['id']:r for r in json.load(open('e71x/SPOTCHECK_PACKET.json'))}
sh={json.loads(l)['id']:json.loads(l) for l in open('review_in/SPOTCHECK_JUDGMENTS.jsonl')}
ids=[i for i in sk if sk[i].get('category') in ('states_value','names_property_without_value','exhibits','silent')]
sp={}
for prop in ('all','fact_recall','language_plan'):
    sub=[i for i in ids if prop=='all' or pk[i]['property']==prop]
    h4=[sh[i]['category'] for i in sub]; j4=[sk[i]['category'] for i in sub]
    hv=[(sh[i]['category'],tuple(sorted(sh[i]['values']))) for i in sub]; jv=[(sk[i]['category'],tuple(sorted(sk[i]['values']))) for i in sub]
    k4,po4=kappa(h4,j4); kv,pov=kappa([str(x) for x in hv],[str(x) for x in jv])
    hs=[x=='states_value' for x in h4]; js=[x=='states_value' for x in j4]
    fy=sum(jj and not hh for hh,jj in zip(hs,js)); fn=sum(hh and not jj for hh,jj in zip(hs,js))
    sp[prop]=dict(n=len(sub),agree_4cat=round(po4,3),kappa_4cat=round(k4,3),agree_code_and_value=round(pov,3),
      judge_states_human_not=f'{fy}/{sum(not x for x in hs)}',fy_wilson=[round(x,3) for x in wilson(fy,sum(not x for x in hs))],
      judge_not_human_states=f'{fn}/{sum(hs)}',fn_wilson=[round(x,3) for x in wilson(fn,sum(hs))],
      human_cats=dict(collections.Counter(h4)),judge_cats=dict(collections.Counter(j4)))
sp['disagreements']=[dict(n=pk[i]['n'],property=pk[i]['property'],human=sh[i]['category']+str(sh[i]['values']),judge=sk[i]['category']+str(sk[i].get('values')),readout=pk[i]['readout'][:160]) for i in ids if (sh[i]['category'],tuple(sorted(sh[i]['values'])))!=(sk[i]['category'],tuple(sorted(sk[i].get('values',[]))))]
res['spotcheck']=sp
json.dump(res,open('e71_agreement.json','w'),indent=1,default=str)
