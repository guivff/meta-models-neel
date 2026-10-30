"""§92 E5: frozen elicitation phrasing pairs, exploratory scoring-only analysis."""
from pathlib import Path
import argparse,json
import numpy as np
from . import core as K
from projects.g_agreement.blindspot import protocol as P

FEATURES=['table_column','prose_paren','python_depth','prose_sentiment','prose_topic','python_error']
KINDS=['direct_question','statement','reader_native','which_more_likely','paraphrase1','paraphrase2','plain_value1','plain_value2']
WORDS={
 'table_column':('the first table column','a later table column','the leftmost cell in its row','a cell after earlier cells in its row','the first column','the fifth column'),
 'prose_paren':('inside an open parenthesis','outside any parenthesis','a parenthetical span that remains open','text with no open parenthetical span','an unclosed parenthesis','no unclosed parenthesis'),
 'python_depth':('shallow bracket nesting','deep bracket nesting','only one open bracket','three nested open brackets','one bracket level','three bracket levels'),
 'prose_sentiment':('positive sentiment','negative sentiment','an upbeat and approving tone','an unhappy and disapproving tone','positive feelings','negative feelings'),
 'prose_topic':('gardening content','ocean content','plants growing in soil','the sea and marine life','gardening','the ocean'),
 'python_error':('exception raising','normal function return','code that throws an error','code that returns a value','raising an exception','returning normally'),
}


def phrasings():
    out={}
    for f,(a,b,c,d,e,g) in WORDS.items():
        pairs=[(f'Does the current excerpt involve {a}? Yes.',f'Does the current excerpt involve {a}? No.'),
            (f'The current excerpt has {a}.',f'The current excerpt has {b}.'),
            (f'The read position indicates {a}.',f'The read position indicates {b}.'),
            (f'It is more likely that this excerpt involves {a}.',f'It is more likely that this excerpt involves {b}.'),
            (f'This is {c}.',f'This is {d}.'),
            (f'The relevant property is {c}.',f'The relevant property is {d}.'),
            (f'In plain words: {e}.',f'In plain words: {g}.'),
            (f'The text expresses {e}.',f'The text expresses {g}.')]
        if f=='prose_paren':pairs[7]=('The next character should be a closing parenthesis.','The next character should not be a closing parenthesis.')
        readers={}
        for name in ('olens','nla','jlens'):
            value=[list(p) for p in pairs]
            if name=='olens':value[2]=['- '+s for s in pairs[2]]
            readers[name]=value
        out[f]={**readers,'kinds':KINDS,'score_orientation':'W1 value A positive; no flips',
            'jlens_supported':False,'jlens_limitation':'W1 J-lens scores single-token candidate variants, not natural-language query sequences. All8 frozen phrasings retained and reported unsupported; no alternative scorer.'}
    return out


def prepare():
    def select(items):return [i for i,x in enumerate(items) if x['feature'] in FEATURES and x['split']=='test']
    return K.prepare('E5',FEATURES,select,phrasings(),1080,{'prediction':'Oracle structure stays near chance across phrasings; meaning near ceiling',
        'reporting':'all8 per reader, best and spread exploratory; no confirmation threshold or outcome-based dropping',
        'format_limitation':'J-lens has no sequence-query prompt interface under the required unchanged W1 scorer; report unsupported explicitly'})


def analyse(bank,outputs,out):
    from dataclasses import asdict
    from mats import metrics
    bank,outputs,out=map(Path,(bank,outputs,out));P.verify(bank,'INPUT_SEAL.json');P.verify(outputs,'SCORE_SEAL.json')
    plan=json.loads((bank/'plan.json').read_text());provenance=json.loads((outputs/'provenance.json').read_text())
    if provenance['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json'):raise ValueError('wrong score lineage')
    items=P.rows(bank/'items.input.jsonl');raw=P.rows(outputs/'scores.jsonl')
    expected={(x['id'],r,l) for x in items for r,l in K.READERS}
    keys=[(r['id'],r['reader'],r['layer']) for r in raw]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('incomplete score grid')
    if P.sha(Path(plan['labels_local']))!=plan['labels_sha256']:raise ValueError('wrong labels')
    labels={r['id']:r for r in P.rows(Path(plan['labels_local']))};mapping=dict(zip(keys,raw))
    _,_,w1spec=K.load_w1();rows=[]
    for feature in FEATURES:
        ids=[x['id'] for x in items if x['feature']==feature]
        y=np.array([labels[i]['value']==w1spec[feature]['values'][0] for i in ids],int)
        groups=np.array([labels[i]['cluster'] for i in ids])
        for name,site in K.READERS:
            cells=[mapping[i,name,site] for i in ids]
            if any(r['status']!='COMPLETE' for r in cells):
                rows.append({'feature':feature,'reader':name,'status':'UNSUPPORTED_SEQUENCE_QUERY_WITH_W1_J_LENS','pairs':8});continue
            results=[{'phrasing':j,'kind':KINDS[j],**asdict(metrics.auroc_ci([r['scores'][j] for r in cells],y,groups,n_boot=2000,seed=P.SEED))} for j in range(8)]
            auc=np.array([r['auroc'] for r in results])
            rows.append({'feature':feature,'reader':name,'status':'EXPLORATORY','phrasings':results,
                'best_phrasing':int(np.argmax(auc)),'best_auroc':float(auc.max()),'spread':float(auc.max()-auc.min()),
                'oracle_structure_above_075':bool(name=='olens' and feature in FEATURES[:3] and auc.max()>.75)})
    out.mkdir(parents=True,exist_ok=False);P.dump(out/'metrics.json',{'status':'EXPLORATORY','rows':rows,'prediction':plan['prediction']})
    lines=['# E5 exploratory results','',plan['prediction'],'',
        'All phrasings and failures are reported; the best is selected descriptively and has selection optimism.',
        'J-lens natural-language sequence queries are unsupported by the unchanged W1 native scorer.']
    for r in rows:
        lines.append('\n'+str(r))
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare');a=sub.add_parser('analyse')
    for n in ('bank','outputs','out'):a.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args()
    if args.command=='prepare':prepare()
    else:analyse(args.bank,args.outputs,args.out)
