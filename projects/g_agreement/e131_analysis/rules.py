"""Prospective §239 CPU text classification; no model or judge calls."""
import math
from common.stats import wilson
from projects.g_agreement.core.analysis_utils import parse_target_answer
CONDITIONS=('e104_steered_8','e104_random_8','unhooked','e128_steered_2','e128_random_2','e128_steered_4','e128_random_4','context_update','neutral_prefix','none')

def require(ok, message):
    if not ok: raise ValueError(message)

def classify(text, old, new, pair_margin, a_value):
    require(isinstance(text,str) and old.casefold()!=new.casefold(),'text and distinct frozen values')
    require(math.isfinite(pair_margin) and a_value in ('old','new'),'finite ordered preference')
    hit=parse_target_answer({'primary':{'candidates':[old,new],'answer':old}},text.lstrip())
    value='old' if hit==old else 'new' if hit==new else 'neither'
    preference=a_value if pair_margin>0 else ('new' if a_value=='old' else 'old') if pair_margin<0 else 'tie'
    return dict(text_value=value,pair_value=preference,agreement=value!='neither' and value==preference)

def rate(k,n):
    return dict(k=k,n=n,rate=k/n if n else None,Wilson95=list(wilson(k,n)[1:]) if n else None)

def summarize(rows):
    require(len(rows)==840 and len({r['id'] for r in rows})==840,'complete unique 840 cells')
    bases={r['base_id'] for r in rows};require(len(bases)==84,'84 bases')
    by={(r['base_id'],r['condition']):r for r in rows}
    require(set(by)=={(b,c) for b in bases for c in CONDITIONS},'exact ten-condition grid')
    reports={}
    for c in CONDITIONS:
        xs=[by[b,c] for b in sorted(bases)]; stated=[x for x in xs if x['text_value']!='neither']
        reports[c]=dict(new=rate(sum(x['text_value']=='new' for x in xs),84),old=rate(sum(x['text_value']=='old' for x in xs),84),no_unique_value=rate(84-len(stated),84),text_pair_agreement=rate(sum(x['agreement'] for x in stated),len(stated)),pair_new=rate(sum(x['pair_value']=='new' for x in xs),84),pair_ties=sum(x['pair_value']=='tie' for x in xs))
    z=reports['e104_steered_8'];p=z['new'];a=z['text_pair_agreement']
    met=p['rate']>=.80 and p['Wilson95'][0]>.65 and a['rate'] is not None and a['rate']>=.90
    flipped=[b for b in sorted(bases) if by[b,'context_update']['text_value']=='new' and by[b,'none']['text_value']=='old']
    def alpha(metric):
        return next((d for d in (2,4,8) if reports[('e104' if d==8 else 'e128')+'_steered_'+str(d)][metric]['k']>=42),None)
    return dict(experiment='E131',R_TX1='MET' if met else 'NOT MET',falsifier=p['rate']<=.50,conditions=reports,E127_text_flipped_bases=flipped,E104_text_flipped_bases=[b for b in sorted(bases) if by[b,'e104_steered_8']['text_value']=='new'],E128_alpha_min_text=alpha('new'),E128_alpha_min_pair=alpha('pair_new'),alpha_min_definition='smallest 2/4/8 with at least42 new preferences/texts; same E131 forwards; descriptive',neither_policy='both candidates or no candidate; unchanged frozen parser',historical_reader_statistics='Separate descriptive join required from sealed judgments; no new calls or old verdict changes. E127 cohort is context_update=new AND none=old; E104 cohort is steered8=new.')
