import re
import warnings
import numpy as np
from scipy.stats import rankdata
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from collections import Counter
SEED=20261026

def auc(y,s):
    y=np.asarray(y,dtype=int);s=np.asarray(s,float)
    if len(y)!=len(s) or set(y)!={0,1} or not np.isfinite(s).all():raise ValueError('binary finite AUROC grid')
    n=y.sum();return float((rankdata(s)[y==1].sum()-n*(n+1)/2)/(n*(len(y)-n)))

def auc_boot(y,s,rng,n=2000):
    y=np.asarray(y);s=np.asarray(s);values=[]
    while len(values)<n:
        ix=rng.integers(len(y),size=len(y))
        if len(set(y[ix]))<2:continue
        values.append(auc(y[ix],s[ix]))
    return {'auroc':auc(y,s),'ci95':np.quantile(values,[.025,.975]).tolist(),'n':len(y)}

def rho(x,y):
    a=rankdata(x);b=rankdata(y);a-=a.mean();b-=b.mean();den=np.linalg.norm(a)*np.linalg.norm(b)
    return None if den==0 else float(a@b/den)

def correlations(x,y,rng,n=10000,other=None):
    x=np.asarray(x);y=np.asarray(y);other=None if other is None else np.asarray(other);boot=[];diff=[];attempts=0
    if len(x)<3 or rho(x,y) is None:return {'rho':None,'ci95':None,'n':len(x),'status':'NOT EVALUABLE'}
    while len(boot)<n:
        ix=rng.integers(len(x),size=len(x));a=rho(x[ix],y[ix]);b=None if other is None else rho(other[ix],y[ix]);attempts+=1
        if attempts>n*10:raise ValueError('too many degenerate row-bootstrap draws')
        if a is None or (other is not None and b is None):continue
        boot.append(a)
        if other is not None:diff.append(a-b)
    result={'rho':rho(x,y),'ci95':np.quantile(boot,[.025,.975]).tolist(),'n':len(x),'draws':n,'status':'COMPLETE'}
    if other is not None:result.update(rho_difference=rho(x,y)-rho(other,y),difference_ci95=np.quantile(diff,[.025,.975]).tolist())
    return result

def words(text):
    # Remove entire TeX command names before word extraction, retaining arguments.
    text=re.sub(r'\\[A-Za-z]+\*?', ' ', text)
    return re.findall(r'[^\W\d_]+',text.lower(),flags=re.UNICODE)

def bags(items,tok,mode):
    out=[]
    for r in items:
        ids=r['ids'][-32:]
        tokens=words(tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)) if mode=='words' else [str(x) for x in ids]
        c=Counter(tokens)
        out.append({k:1 if mode=='presence' else v for k,v in c.items()})
    return out

def fit_score(dev,test,y,mode,tok):
    tr=bags(dev,tok,mode);te=bags(test,tok,mode);v=DictVectorizer(sparse=False);x=v.fit_transform(tr);z=v.transform(te)
    if x.shape[1]==0:return np.zeros(len(te)),{'vocabulary':0,'constant':True}
    clf=LogisticRegression(C=1.,penalty='l2',solver='liblinear',max_iter=10000,tol=1e-8,random_state=SEED)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning);clf.fit(x,y)
    return clf.decision_function(z),{'vocabulary':x.shape[1],'constant':False,'iterations':int(clf.n_iter_[0])}

def shown(text):
    # Fixed orientations; never flip by observed labels. Raw native text, no cleanup.
    lines=text.splitlines()
    return {'close_minus_open_paren':text.count(')')-text.count('('),
            'double_quote_parity':text.count('"')%2,
            'single_quote_parity':text.count("'")%2,
            'leading_space_runs':sum(len(re.match(r' *',line).group()) for line in lines),
            'pipe_count':text.count('|')}

def rules(rows,presence,words_result):
    violations=[r['key'] for r in rows if (r['asked']>=.8 and r['presence']<.8) or (r['presence']<=.6 and r['asked']>.65)]
    paren=[r['key'] for r in rows if r['row']=='prose_paren' and r['presence']>=.8 and r['asked']<=.65]
    string=[r['key'] for r in rows if r['row']=='python_string' and r['presence']>=.8 and r['asked']<=.65]
    exceptions=[r['key'] for r in rows if r['words']>=.75 and r['asked']<=.65]
    h3s=presence['rho'] is not None and presence['rho']>=.6 and presence['ci95'][0]>.3 and len(violations)<=2
    h3f=presence['rho'] is not None and (presence['rho']<.3 or bool(paren and string))
    h5s=words_result['rho'] is not None and words_result['rho']>=.6 and words_result['rho_difference']>=.15
    h5f=len(exceptions)>=3
    def verdict(s,f):return 'CONFLICTING_RULES' if s and f else 'SUPPORTED' if s else 'FALSIFIED' if f else 'NOT RESOLVED'
    return {'H3':{'status':verdict(h3s,h3f),'support_rule':h3s,'falsification_rule':h3f,'pattern_violations':violations,'paren_exceptions':paren,'string_exceptions':string},'H5':{'status':verdict(h5s,h5f),'support_rule':h5s,'falsification_rule':h5f,'word_predictable_unsayable_rows':exceptions,'paired_difference_ci95':words_result.get('difference_ci95'),'CI_role':'reported; registration does not require exclusion of zero for H5'}}
