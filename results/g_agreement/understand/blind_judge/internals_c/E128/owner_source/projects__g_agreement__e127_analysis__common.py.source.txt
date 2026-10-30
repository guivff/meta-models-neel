"""Original E104/E109 categorical validation and common Wilson intervals."""
from common.stats import wilson
from results.g_agreement.understand.e94.score94 import value_class


def require(ok,message):
    if not ok:raise ValueError(message)


def state(code,value):
    require(value in ('A','B'),'original binary value')
    value_class(code,value)  # original category/value/missing validation
    if code['category']=='UNPARSEABLE':return None
    return int(code['values']==[value])  # dual-value reports are not exclusive


def rate(values):
    known=[x for x in values if x is not None]
    require(all(type(x)is int and x in (0,1)for x in known),'binary/missing outcomes')
    k=sum(known);n=len(known);missing=len(values)-n
    p,lo,hi=wilson(k,n)if n else (None,None,None)
    return dict(k=k,n=n,planned_n=len(values),missing_n=missing,estimate=None if p is None else float(p),Wilson95=None if p is None else [float(lo),float(hi)],missing_over5percent=bool(values)and missing/len(values)>.05)


def criterion(stat,minimum,lower=None):
    if stat['estimate'] is None or lower is not None and stat['Wilson95'] is None:return None
    return bool(stat['estimate']>=minimum and (lower is None or stat['Wilson95'][0]>lower))


def rule(tests):
    return 'NOT MET' if False in tests else 'NOT EVALUABLE' if None in tests else 'MET'
