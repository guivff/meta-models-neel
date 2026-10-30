"""Fresh §84 templates for every frozen §79 feature; selection precedes banking."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from . import protocol as P
from .items import Feature, TOKENIZER_REVISION, TOKENIZER_SHA256
from .w1b import registry_features as S

# Twelve authored carrier grammars, fixed without viewing the screen ranking.
FRAMES = (
    'memo {a}: {b}', 'archive {a} = {b}', 'ledger {a} / {b}',
    'capsule {a} :: {b}', 'docket {a} -- {b}', 'folio {a}; {b}',
    'packet {a} >> {b}', 'bundle {a} -> {b}', 'record {a}, {b}',
    'annotation {a} ~ {b}', 'fragment {a} + {b}', 'excerpt {a} | {b}',
)
NATIVE_PAIRS = [['true', 'false'], ['yes', 'no']]
SEPARATORS = ('\n\n', '.\n', '\n', '. ', ' ', '')


class StatementFeature(Feature):
    """§79 definitions are whole statements, so avoid W1's nominal 'has X' wrapper."""
    def pairs(self, reader):
        positive, negative = self.descriptions
        wrappers = ('- {s}', '- At the read position: {s}.') if reader == 'olens' else (
            S.ASKED_TEMPLATE, 'At the read position, the following statement is true: {statement}.')
        return [(w.format(s=positive, statement=positive), w.format(s=negative, statement=negative)) for w in wrappers]


def domain(feature):
    f=S.BY_ID[feature]
    if f.family in {'paren_depth','square_depth','brace_depth','bracket_depth','indent_spaces',
                    'inside_paren','inside_square','inside_brace','inside_string','inside_single_quote',
                    'inside_double_quote','inside_triple_quote','inside_comment','unmatched_close'} and 'python' in f.domains:
        return 'python'
    return f.domains[0]


def witness(feature, positive, template, variant=0):
    """An authored prefix recipe; the frozen extractor always checks its meaning."""
    f=S.BY_ID[feature]; family=f.family
    feature_index=list(S.BY_ID).index(feature)
    tag=f'zeta{feature_index}t{template}v{variant}'; word=('amber','cobalt','velvet','quartz','cedar','lilac','marble')[variant%7]
    frame=lambda b:FRAMES[template].format(a=tag,b=b)
    n=int(f.threshold or 0)-(0 if positive else 1)
    if f.threshold is not None:
        if family in {'paren_depth','square_depth','brace_depth','bracket_depth'}:
            opening={'paren_depth':'(','square_depth':'[','brace_depth':'{','bracket_depth':'('}[family]
            return frame(opening*n+word)
        if family=='line_index':return '\n'.join(frame(word) for _ in range(n))
        if family=='column_chars':return frame(word)+'\n'+('x'*n)
        if family=='indent_spaces':return frame(word)+'\n'+(' '*n)+word
        if family=='line_words':return frame(word)+'\n'+' '.join([word]*n)
        if family=='sentence_words':return frame(word)+'. '+' '.join([word]*n)
        if family=='paragraph_sentences':return frame(word)+'\n\n'+((word+'. ')*(n-1))+word
        if family=='table_column':return frame(word)+'\n|'+'|'.join([word]*n)
        if family=='list_items':return frame(word)+'\n'+'\n'.join('- '+word for _ in range(n))
        if family=='list_depth':return frame(word)+'\n'+'  '*(n-1)+'- '+word
        if family=='number_magnitude':return frame(word)+' '+str(int(f.threshold)+variant if positive else max(0,int(f.threshold)-1-variant))
        if family=='number_digits':return frame(word)+' '+('3'*n)
        if family=='line_commas':return frame(word)+'\n'+(','.join([word]*(n+1)))
        if family in {'latex_sections','latex_items'}:
            command='\\section{'+word+'}' if family=='latex_sections' else '\\item '+word+' '
            return frame(word)+'\n'+command*n+word
        raise ValueError('missing counter recipe '+family)
    if family.startswith('lexicon_'):
        words=sorted(S.LEXICONS[family.removeprefix('lexicon_')])
        return frame(words[(template+variant)%len(words)] if positive else word)
    if family.startswith('wordlist_'):
        words=sorted(S.CLOSED_CLASSES[family.removeprefix('wordlist_')])
        return frame(word)+' '+(words[(template+variant)%len(words)] if positive else 'zircon')
    if family in {'inside_paren','inside_square','inside_brace'}:
        op,cl={'inside_paren':('(',')'),'inside_square':('[',']'),'inside_brace':('{','}') }[family]
        return frame(op+word+('' if positive else cl))
    if family in {'inside_string','inside_single_quote','inside_double_quote','inside_triple_quote'}:
        q={'inside_string':'"','inside_single_quote':"'",'inside_double_quote':'"','inside_triple_quote':'"""'}[family]
        return frame(q+word+('' if positive else q))
    if family=='inside_comment':return frame(word)+'\n'+('# '+word if positive else word)
    if family=='inside_fence':return frame(word)+'\n```python\n'+word+('' if positive else '\n```')
    if family=='inside_inline_code':return frame('`'+word+('' if positive else '`'))
    if family in {'inside_math','inside_display_math'}:
        q='$' if family=='inside_math' else '$$'
        return frame(q+word+('' if positive else q))
    if family in {'inside_latex_environment','inside_latex_table','inside_latex_itemize'}:
        env={'inside_latex_environment':'quote','inside_latex_table':'tabular','inside_latex_itemize':'itemize'}[family]
        return frame('\\begin{'+env+'}'+word+('' if positive else '\\end{'+env+'}'))
    states={'line_blank':(' '*((variant%3)+1),word),'line_heading':('## '+word,word),
            'line_bullet':('- '+word,word),'line_ordered':('3. '+word,word),
            'line_task':('- [ ] '+word,'- '+word),'line_task_checked':('- [x] '+word,'- [ ] '+word),
            'line_table':('| '+word+' |',word),'word_allcaps':('AMBER','amber'),
            'word_titlecase':('Amber','amber'),'word_lowercase':('amber','AMBER'),
            'word_nonascii':('café','amber'),'current_number':('123','amber'),
            'current_question':(word+'?',word+'.'),'current_colon':(word+':',word+'.'),
            'unmatched_close':(') '+word,'() '+word)}
    if family not in states:raise ValueError('missing state recipe '+family)
    return frame(word)+'\n'+states[family][0 if positive else 1]


def matched_pair(tok, feature, template, variant=0):
    """Padding is validated by extraction on the entire final prefix, never assumed neutral."""
    bodies=[witness(feature, side, template, variant) for side in (True,False)]
    d=domain(feature)
    encode=lambda text:list(tok(text,add_special_tokens=False)['input_ids'])
    value=lambda text:S.extract(text,d)[feature]
    for separator in SEPARATORS:
        def render(body,n):return 'pad '*n+separator+body
        base=[render(b,0) for b in bodies]
        if [value(x) for x in base]!=[True,False]:continue
        sizes=[len(encode(x)) for x in base]
        for target in range(max(sizes)+8+(variant%5),max(sizes)+80):
            found=[]
            for body,size,side in zip(bodies,sizes,(True,False)):
                guess=max(0,target-size)
                for n in [guess]+[j for j in range(max(0,guess-6),guess+10) if j!=guess]:
                    text=render(body,n);ids=encode(text)
                    if len(ids)==target and value(text) is side:
                        found.append((text,ids));break
                else:break
            if len(found)==2:return found
    raise ValueError(f'no meaning-preserving exact length match: {feature}, template {template}')


def selection(receipt_path):
    """Require committed evidence and exact list, never infer a selection from ranks."""
    from .analysis import validate_selection_receipt
    r=validate_selection_receipt(json.loads(Path(receipt_path).read_text()))
    committed=subprocess.check_output(['git','show',r['source_commit']+':'+r['selection_file']],cwd=P.ROOT)
    if hashlib.sha256(committed).hexdigest()!=r['selection_sha256']:
        raise ValueError('selection bytes do not match committed receipt')
    payload=json.loads(committed)
    if isinstance(payload,dict):
        candidates=[payload[k] for k in ('section79_features','features','selected_features','top10','top_10','candidates') if k in payload]
        if len(candidates)!=1:raise ValueError('selection file needs one unambiguous selected-feature list')
        payload=candidates[0]
    selected=[x if isinstance(x,str) else x.get('feature',x.get('id')) for x in payload]
    if selected!=r['section79_features']:
        raise ValueError('receipt §79 list differs from committed selection')
    if r.get('section81_features'):raise ValueError('§81 candidates need their own committed list; not inferred from §79')
    if not set(selected)<=set(S.BY_ID):raise ValueError('unknown frozen §79 feature')
    return r,selected


def build(tok, selected):
    items=[]
    for feature in selected:
        f=S.BY_ID[feature];d=domain(feature)
        for template in range(12):
            cluster=hashlib.sha256(f'W1b-v1:{feature}:{template}'.encode()).hexdigest()[:24]
            for variant in range(7):
                pair=hashlib.sha256(f'{cluster}:{variant}'.encode()).hexdigest()[:24]
                for (text,ids),side in zip(matched_pair(tok,feature,template,variant),(True,False)):
                    items.append({'id':hashlib.sha256(f'{pair}:{side}'.encode()).hexdigest()[:24],
                        'feature':feature,'class':f.kind,'domain':d,'split':'dev' if template%2==0 else 'test',
                        'cluster':cluster,'value':'present' if side else 'absent','ids':ids,'text':text,
                        'meta':{'pair_id':pair,'template_index':template,'variant':variant,'token_length':len(ids),
                                'read_position':len(ids)-1,'kind':'binary','registry_definition':f.definition}})
    if len({it['text'] for it in items})!=len(items):raise ValueError('duplicate fresh item texts')
    return items


def verify_lengths(tok, items):
    from scipy.stats import ks_2samp
    checks=[]
    for it in items:
        assert list(tok(it['text'],add_special_tokens=False)['input_ids'])==it['ids']
        assert S.extract(it['text'],it['domain'])[it['feature']] is (it['value']=='present')
    for feature in sorted({it['feature'] for it in items}):
        subset=[it for it in items if it['feature']==feature]
        assert len(subset)==168 and len({it['cluster'] for it in subset})==12
        assert Counter(it['split'] for it in subset)=={'dev':84,'test':84}
        for split in ('dev','test'):
            groups=[[len(it['ids']) for it in subset if it['split']==split and it['value']==v] for v in ('present','absent')]
            p=float(ks_2samp(*groups).pvalue);mean=abs(sum(groups[0])/len(groups[0])-sum(groups[1])/len(groups[1]))
            if p<=.2 or mean>1:raise ValueError('length match failed')
            checks.append({'feature':feature,'split':split,'ks_p':p,'mean_token_difference':mean,'n_per_value':42})
    return {'status':'PASS','checks':checks,'registry_verified_after_padding':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('selection-receipt','tokenizer','out','freeze-out','stage-out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    receipt,selected=selection(a.selection_receipt)  # before any production items
    origin=json.loads((Path(__file__).parent/'w1b/REGISTRY_ORIGIN.json').read_text())
    if P.sha(Path(S.__file__))!=origin['sha256']:raise ValueError('frozen §79 registry snapshot changed')
    from transformers import AutoTokenizer
    if P.sha(a.tokenizer/'tokenizer.json')!=TOKENIZER_SHA256:raise ValueError('wrong pinned Qwen tokenizer')
    tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    with P.logged('w1b_build_and_freeze',extra={'selection_commit':receipt['source_commit']}):
        items=build(tok,selected);checks=verify_lengths(tok,items)
        from mats.readers.jlens import token_variants
        if any(not token_variants(tok,[word]) for pair in NATIVE_PAIRS for word in pair):raise ValueError('native candidate variant unavailable')
        specs={f:StatementFeature(domain(f),S.BY_ID[f].kind,('present','absent'),(S.BY_ID[f].positive,S.BY_ID[f].negative),('true','false')) for f in selected}
        P.write_bank(a.out,items,checks,a.tokenizer,experiment='W1b',selection_receipt=receipt,
                     feature_registry=specs,native_pairs={f:NATIVE_PAIRS for f in selected})
        from .stage import export_freeze,stage_bank
        export_freeze(a.out,a.freeze_out);stage_bank(a.out,a.stage_out)
    print('W1b frozen; commit the manifest before requesting any capture.')


if __name__=='__main__':main()
