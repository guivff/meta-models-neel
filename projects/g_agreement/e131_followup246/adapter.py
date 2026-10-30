"""§246 prospective exploratory join; sealed classifications/codes only."""
import argparse
from pathlib import Path
import numpy as np
from projects.g_agreement.e127_analysis import transport as t
from projects.g_agreement.e127_analysis.common import require,rate
from projects.g_agreement.e128_addenda.adapter import category
from projects.g_agreement.e135_analysis.adapter import fixed_cohort
from projects.g_agreement.e121_analysis import adapter as e121
from projects.g_agreement.e123_analysis import adapter as e123, rules as dis

CUSTODY=t.CUSTODY.parents[3]/'wt-wmech'/'cache/g_agreement/understand/e131/followup246'
TEXT_SEAL='88f4252d7c45e9ffa93fd79c5bca1248dfec3e36dab7dd2003b86fcb122d5b9f'
E104_SEAL='ce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b'
E121_SEAL='77a66f703234e4973f63057e2eb53743e06dc0a1ba1da3bffd347cf4934d6473'
E123_SEAL='0c4fd523773e273dfb4d0f8214cbe294cb931623b36005286504d3073f28b9a2'


def indicator(code,old,new,which):
    if code is None or code['category']=='UNPARSEABLE':return None
    value=category(code,old,new)
    return int(value==('neither_or_unparseable' if which=='neither' else which))


def difference(rows,bank,draws=5000,seed=0):
    # Resample original items, carrying group membership and missingness together.
    rows=sorted(rows,key=lambda x:x['item_id'])
    values=np.array([np.nan if (v:=indicator(x[bank]['steered'],x['old_value'],x['new_value'],'old')) is None else v for x in rows])
    groups=np.array([x['text_class']=='new' for x in rows]);rng=np.random.default_rng(seed)
    def stat(ix):
        v=values[ix];g=groups[ix];left=v[g & np.isfinite(v)];right=v[~g & np.isfinite(v)]
        return float(left.mean()-right.mean()) if len(left) and len(right) else None
    point=stat(np.arange(len(rows)));boot=[stat(ix) for ix in rng.integers(0,len(rows),(draws,len(rows)))];valid=[v for v in boot if v is not None]
    return dict(contrast='text-new minus text-neither old44 rate',estimate=point,CI95=np.quantile(valid,[.025,.975]).tolist() if valid else None,draws=draws,valid_draws=len(valid),undefined_draws=draws-len(valid),seed=seed,unit='original item; membership and missingness travel with item',CI_policy='percentile95 conditional on defined draws')


def analyze(rows,draws=5000):
    require(len(rows)==84 and len({x['item_id'] for x in rows})==84,'exact original84')
    require(sum(x['text_class']=='new' for x in rows)==43 and sum(x['text_class']=='neither' for x in rows)==41,'sealed text split43/41')
    require(all(type(x['alpha4_cohort']) is bool for x in rows) and sum(x['alpha4_cohort'] for x in rows)==42,'original native alpha4 cohort42')
    reports={}
    for group in ('new','neither'):
        xs=[x for x in rows if x['text_class']==group]
        reports[group]=dict(n=len(xs),reader_banks={},e121_agreements={},e123_disagreement_flags={})
        for bank in ('e104_original44','e109_reference44'):
            reports[group]['reader_banks'][bank]={c:{v:rate([indicator(x[bank][c],x['old_value'],x['new_value'],v) for x in xs]) for v in ('old','new','dual','neither')} for c in ('steered','random')}
        reports[group]['block52_new']={c:rate([indicator(x['e109_52'][c],x['old_value'],x['new_value'],'new') for x in xs]) for c in ('steered','random')}
        for c in ('steered','random'):
            def agree(x):
                a,b=x['e121'][c]
                return None if a is None or b is None else int(a==b and a!='no mention')
            reports[group]['e121_agreements'][c]=rate([agree(x) for x in xs])
        for c in ('steered','random','unhooked'):
            reports[group]['e123_disagreement_flags'][c]=rate([dis.disagreement(*x['e123'][c]) for x in xs])
    return dict(experiment='E131 followup246',label='exploratory, post hoc',groups=reports,
        text_by_alpha4_cohort={g:{k:sum(x['text_class']==g and x['alpha4_cohort']==v for x in rows) for k,v in [('in',True),('out',False)]} for g in ('new','neither')},
        old44_difference={bank:difference(rows,bank,draws) for bank in ('e104_original44','e109_reference44')},
        provenance='Original E104 judgment bank and E109 rejudged E104-source reference kept separate; no substitution.',
        caveat='Unhooked text states neither on84/84 while pair preference is old84/84: text measure lacks sensitivity to unflipped answers in this prompt format. Pair preference flips84/84; steered text new43/84,old0/84.',
        missing_policy='UNPARSEABLE/missing excluded from observed denominator, never neither or zero; all planned/known/missing counts retained.',new_calls=0)


def load(spec):
    c=t.core
    # W-text owns the sealed source identity crosswalk; no inferred ID conversion.
    jp=Path(spec['join_packet']);require(spec['join_sha256']==c.sha(jp)=='f03acd297f0cca855167fea022a118199791062b8632afad7f0333d996e3f1f6','exact W-text214aa0f16 delivery packet')
    tp=Path(spec['e131_analysis_seal']);tm=c.verify(tp,TEXT_SEAL)
    require('CLASSIFICATIONS.PRIVATE.json' in tm['files'],'sealed original classifications')
    classes=c.unique(c.read(tp.parent/'CLASSIFICATIONS.PRIVATE.json'),'id')
    joins=c.read(jp)['records'];ji=c.unique(joins,'e104_item_id')
    require(len(ji)==84 and len({x['e131_id'] for x in joins})==84,'bijection84')
    s128=c.read(spec['e128_spec']);items,_,_=t.cohort(s128,'E128');by=c.unique(items,'item_id')
    require(set(ji)==set(by),'same original E104 IDs')
    fixed=fixed_cohort(spec,set(by))
    sp=Path(spec['e104_judgment_seal']);c.verify(sp,E104_SEAL)
    originals=c.unique(c.read(sp.parent/'JUDGMENTS.json'),'id')
    labels=c.read(s128['e104_private']);labels={(x['item_id'],x['condition']):x for x in labels if x['row']=='fact_recall' and x['arm']=='U'}
    a121=Path(spec['e121_analysis_seal']);c.verify(a121,E121_SEAL)
    r121=e121.inputs(c.read(a121.parent/'BINDING.json'));idx121={(x['item_id'],x['condition'],x['reader']):x['class'] for x in r121}
    a123=Path(spec['e123_analysis_seal']);c.verify(a123,E123_SEAL)
    s123=c.read(a123.parent/'BINDING.json');inventory=e123.metadata(s123);r123=c.unique(e123.inputs(s123,inventory)['fact_recall'],'item_id')
    require(set(r123)==set(by) and {i for i,_,_ in idx121}==set(by),'exact cross-experiment census')
    out=[]
    for i,item in by.items():
        j=ji[i];cl=classes[j['e131_id']]
        require(cl['base_id']==j['e131_base_id'] and cl['condition']=='e104_steered_8','original steered8 class pointer')
        require(j['e104_item_id']==j['e127_original_base_id']==i and j['e104_source_record_id']==labels[i,'steered']['id'],'W-text original source identity proof')
        require(j['text_class']==cl['text_value'],'unchanged sealed classification')
        original={}
        for cond in ('steered','random'):
            lab=labels[i,cond];code=originals[lab['opaque_id']];c.score(code,item['new_value'],lab['text']);original[cond]=code
        rc=r123[i]['conditions']
        out.append(dict(item_id=i,old_value=item['old_value'],new_value=item['new_value'],text_class=cl['text_value'],alpha4_cohort=i in fixed,
          e104_original44=original,e109_reference44={k:rc[k]['44'] for k in ('steered','random')},e109_52={k:rc[k]['52'] for k in ('steered','random')},
          e121={k:[idx121[i,k,'oracle'],idx121[i,k,'nla']] for k in ('steered','random')},e123={k:[rc[k]['44'],rc[k]['52']] for k in ('steered','random','unhooked')}))
    return out


def run(spec,commit):
    guard=CUSTODY/'ANALYSIS_ONCE.json';require(not guard.exists(),'followup246 guard consumed; never replay')
    require(spec['status']=='COMPLETE' and spec['owner_join_verified'] is True,'complete owner binding')
    out=t.core.claim(dict(analysis=str(CUSTODY/'analysis_once'),guard=str(guard),output_sha256=spec['join_sha256']),commit)
    rows=load(spec);t.core.write(out/'RESULTS.json',analyze(rows));t.core.write(out/'BINDING.json',spec)
    t.core.seal(out,'ANALYSIS_SEAL.json',experiment='E131 followup246',status='COMPLETE_ONCE',code_commit=commit,new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=t.committed(Path(__file__).resolve().parent)
    print(run(t.core.read(args.spec),commit))
if __name__=='__main__':main()
