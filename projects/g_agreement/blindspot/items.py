"""Synthetic exp-13-shaped prefixes, paired by source cluster and exact token length.

Features are relative to ``body``, after a clearly delimited unrelated archive preamble.
Both values receive padding. Padding content and target length are label-independent;
the shorter (e.g. early) body receives more of it. Never truncate the body/read position.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random

from .protocol import write_bank
from .w1_templates import render_body, template_signature, TEMPLATE_COUNT

SEED = 20261023
DELIMITER = "\n\n--- Current excerpt ---\n"


@dataclass(frozen=True)
class Feature:
    domain: str
    kind: str
    values: tuple[str, str]
    descriptions: tuple[str, str]
    tokens: tuple[str, str]

    def pairs(self, reader: str) -> list[tuple[str, str]]:
        a, b = self.descriptions
        if reader == "olens":
            return [(f"- {a}", f"- {b}"), (f"- At the read position, the excerpt has {a}.", f"- At the read position, the excerpt has {b}.")]
        return [(f"The current excerpt has {a}.", f"The current excerpt has {b}."), (f"At the read position, there is {a}.", f"At the read position, there is {b}.")]


def _f(domain, kind, values, descriptions=None, tokens=None):
    return Feature(domain, kind, tuple(values), tuple(descriptions or values), tuple(tokens or values))


# Forty hypotheses, fixed before readouts; no mining or selection on reader performance.
FEATURES = {
    "prose_sentence": _f("prose", "count-like", ("early", "late"), ("an early sentence in the paragraph", "a late sentence in the paragraph")),
    "prose_words": _f("prose", "count-like", ("few", "many"), ("few words in the current sentence", "many words in the current sentence")),
    "prose_budget": _f("prose", "count-like", ("many", "few"), ("many words remaining under the word limit", "few words remaining under the word limit")),
    "prose_column": _f("prose", "count-like", ("short", "long"), ("few words on the current line", "many words on the current line")),
    "prose_paren": _f("prose", "state-like", ("inside", "outside"), ("the read position inside a parenthesis", "the read position outside any parenthesis")),
    "prose_quote": _f("prose", "state-like", ("inside", "outside"), ("an open quotation", "a closed quotation")),
    "prose_topic": _f("prose", "semantic", ("garden", "ocean"), ("gardening content", "ocean content")),
    "prose_sentiment": _f("prose", "semantic", ("positive", "negative"), ("positive sentiment", "negative sentiment")),
    "python_line": _f("python", "count-like", ("early", "late"), ("one or two lines so far in the current function body", "six or more lines so far in the current function body")),
    "python_argument": _f("python", "count-like", ("first", "later"), ("the first argument of a call", "a later argument of a call")),
    "python_depth": _f("python", "count-like", ("shallow", "deep"), ("shallow bracket nesting", "deep bracket nesting")),
    "python_indent": _f("python", "count-like", ("shallow", "deep"), ("one level of indentation", "three levels of indentation")),
    "python_string": _f("python", "state-like", ("inside", "outside"), ("an open string literal", "a closed string literal")),
    "python_comment": _f("python", "state-like", ("comment", "code"), ("a Python comment", "executable Python code")),
    "python_effect": _f("python", "semantic", ("mutation", "copy"), ("an in-place list mutation", "construction of a new list")),
    "python_error": _f("python", "semantic", ("raise", "return"), ("exception raising", "normal function return")),
    "latex_section": _f("latex", "count-like", ("early", "late"), ("an early document section", "a late document section")),
    "latex_item": _f("latex", "count-like", ("first", "later"), ("the first enumerated item", "a later enumerated item")),
    "latex_math": _f("latex", "state-like", ("math", "text"), ("inline math mode", "ordinary text mode")),
    "latex_brace": _f("latex", "count-like", ("shallow", "deep"), ("one unclosed brace", "three unclosed braces")),
    "latex_environment": _f("latex", "state-like", ("equation", "quote"), ("an equation environment", "a quotation environment")),
    "latex_fraction": _f("latex", "state-like", ("numerator", "denominator"), ("a fraction numerator", "a fraction denominator")),
    "latex_subject": _f("latex", "semantic", ("algebra", "geometry"), ("algebra content", "geometry content")),
    "latex_role": _f("latex", "semantic", ("theorem", "example"), ("a theorem statement", "a worked example")),
    "json_field": _f("json", "count-like", ("first", "later"), ("the first object field", "a later object field")),
    "json_depth": _f("json", "count-like", ("shallow", "deep"), ("one nested JSON object", "three nested JSON objects")),
    "json_type": _f("json", "state-like", ("string", "number"), ("a string value", "a numeric value")),
    "json_status": _f("json", "semantic", ("approved", "rejected"), ("an approved request", "a rejected request")),
    "table_column": _f("table", "count-like", ("first", "later"), ("the first table column", "a later table column")),
    "table_row": _f("table", "count-like", ("early", "late"), ("an early table data row", "a late table data row")),
    "table_role": _f("table", "state-like", ("header", "data"), ("a table header cell", "a table data cell")),
    "table_status": _f("table", "semantic", ("approved", "rejected"), ("an approved table entry", "a rejected table entry")),
    "list_index": _f("list", "count-like", ("first", "later"), ("the first list item", "a later list item")),
    "list_depth": _f("list", "count-like", ("shallow", "deep"), ("a top-level list item", "a third-level list item")),
    "list_completed": _f("list", "count-like", ("few", "many"), ("few completed tasks above this item", "many completed tasks above this item")),
    "list_words": _f("list", "count-like", ("few", "many"), ("few words in the current item", "many words in the current item")),
    "list_ordered": _f("list", "state-like", ("ordered", "bullet"), ("an ordered list", "a bullet list")),
    "list_task": _f("list", "state-like", ("checked", "unchecked"), ("a checked task", "an unchecked task")),
    "list_priority": _f("list", "semantic", ("urgent", "routine"), ("an urgent task", "a routine task")),
    "list_topic": _f("list", "semantic", ("travel", "study"), ("travel planning", "study planning")),
}


ORDINAL_FEATURES = {
    'table_column_ordinal': _f('table', 'count-like', ('high', 'low'),
        ('a later table column', 'an earlier table column'), ('later', 'earlier')),
    'python_depth_ordinal': _f('python', 'count-like', ('high', 'low'),
        ('deeper bracket nesting', 'shallower bracket nesting'), ('deep', 'shallow')),
}
ALL_FEATURES = {**FEATURES, **ORDINAL_FEATURES}
DEFAULT_PAIRS_PER_TEMPLATE = 7  # 42 test pairs/row, sufficient for downstream W4's 40.
TOKENIZER_REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOKENIZER_SHA256 = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def body(feature, side, rng, template=0, variant=0):
    """Compatibility entrypoint for one of the twelve authored template families."""
    word = rng.choice(['river', 'valley', 'village', 'forest', 'harbour', 'meadow'])
    return render_body(feature, side, template, variant, word)


def encode(tok, text):
    return list(tok(text, add_special_tokens=False)['input_ids'])


def match_pair(tok, bodies, rng):
    """Match two values, or all eight ordinal levels, without truncation.

    Each group shares a label-independent archive header and target length. Whole
    strings are retokenised, including at the preamble/body boundary.
    """
    header = 'Unrelated archive note: ' + rng.choice(['stone', 'cloud', 'paper', 'basket']) + f' archive {rng.getrandbits(64)}'
    def padded(b, n):
        text = header + ' note' * n + DELIMITER + b
        return text, encode(tok, text)
    initial = [len(padded(b, 0)[1]) for b in bodies]
    target = max(initial) + rng.randint(8, 24)
    for _ in range(32):
        out=[]
        for b,size in zip(bodies,initial):
            guess=target-size
            candidates=[guess]+[n for n in range(max(0,guess-8),guess+33) if n!=guess]
            found=None
            for n in candidates:
                text,ids=padded(b,n)
                if len(ids)==target:
                    found=(text,ids);break
            if found is None: break
            out.append(found)
        if len(out)==len(bodies): return out
        target+=1
    raise ValueError('cannot match lengths without truncating; inspect tokenizer/padding')


def _opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def _item(feature, spec, template, variant, seed, value, text, ids, body_text, meta, ordinal=False):
    # Cluster is the entire template family, not the smaller paired instance.
    cluster=_opaque(f'W1-family-v2:{seed}:{feature}:{template}')
    pair_id=_opaque(f'W1-pair-v2:{seed}:{feature}:{template}:{variant}')
    return {'id':_opaque(f'{pair_id}:{value}'), 'feature':feature, 'class':spec.kind,
            'domain':spec.domain, 'split':'dev' if template%2==0 else 'test',
            'cluster':cluster, 'value':value, 'ids':ids, 'text':text,
            'meta':{**meta,'pair_id':pair_id,'body':body_text,'token_length':len(ids),
                    'read_position':len(ids)-1,'kind':'ordinal' if ordinal else 'binary'}}


def build_items(tok, n_templates=TEMPLATE_COUNT, pairs_per_template=DEFAULT_PAIRS_PER_TEMPLATE,
                seed=SEED, features=None):
    if n_templates<2 or n_templates>TEMPLATE_COUNT or n_templates%2 or pairs_per_template<1:
        raise ValueError('require an even number of 2–12 template families and positive pairs_per_template')
    out=[]
    for feature in (FEATURES if features is None else features):
        spec=FEATURES[feature]
        for template in range(n_templates):
            for variant in range(pairs_per_template):
                rng=random.Random(int(_opaque(f'W1-v2:{seed}:{feature}:{template}:{variant}'),16))
                word=['river','valley','village','forest','harbour','meadow','orchard'][variant % 7]
                rendered=[render_body(feature,side,template,variant,word) for side in (0,1)]
                matched=match_pair(tok,[b for b,_ in rendered],rng)
                for side,((text,ids),(b,meta)) in enumerate(zip(matched,rendered)):
                    out.append(_item(feature,spec,template,variant,seed,spec.values[side],text,ids,b,meta))
    assert_lengths(out)
    return out


def build_ordinal_items(tok, n_templates=TEMPLATE_COUNT, variants_per_template=3, seed=SEED):
    if n_templates<2 or n_templates>TEMPLATE_COUNT or n_templates%2 or variants_per_template<1:
        raise ValueError('invalid ordinal template/variant count')
    out=[]
    for feature,spec in ORDINAL_FEATURES.items():
        for template in range(n_templates):
            for variant in range(variants_per_template):
                rng=random.Random(int(_opaque(f'W1-ordinal-v2:{seed}:{feature}:{template}:{variant}'),16))
                word=['river','valley','village','forest','harbour','meadow','orchard'][variant % 7]
                rendered=[render_body(feature,0,template,variant,word,level=level) for level in range(1,9)]
                matched=match_pair(tok,[b for b,_ in rendered],rng)
                for level,((text,ids),(b,meta)) in enumerate(zip(matched,rendered),1):
                    out.append(_item(feature,spec,template,variant,seed,level,text,ids,b,meta,ordinal=True))
    assert_lengths(out)
    return out


def assert_lengths(items):
    """Recorded KS and mean differences for every binary row/ordinal comparison."""
    from scipy.stats import ks_2samp
    from statistics import mean
    from collections import defaultdict
    strata=defaultdict(list)
    for it in items:
        strata[(it['feature'],it['split'])].append(it)
    reports={}
    for (feature,split),group in sorted(strata.items()):
        values=list(range(1,9)) if feature in ORDINAL_FEATURES else list(FEATURES[feature].values)
        lengths={v:[len(it['ids']) for it in group if it['value']==v] for v in values}
        if any(not a for a in lengths.values()) or len({len(a) for a in lengths.values()})!=1:
            raise ValueError('unbalanced/missing length strata')
        comparisons=[]
        for i,a in enumerate(values):
            for b in values[i+1:]:
                p=float(ks_2samp(lengths[a],lengths[b]).pvalue)
                difference=abs(mean(lengths[a])-mean(lengths[b]))
                if p<=0.2 or difference>1:
                    raise ValueError(f'length mismatch: {feature}/{split}/{a}/{b}: p={p}, mean difference={difference}')
                if sorted(lengths[a])!=sorted(lengths[b]):
                    raise ValueError('builder did not preserve exact matched length distributions')
                comparisons.append({'a':a,'b':b,'ks_p':p,'abs_mean_difference':difference})
        first=lengths[values[0]]
        reports[f'{feature}/{split}']={'ks_p':min(c['ks_p'] for c in comparisons),
             'abs_mean_difference':max(c['abs_mean_difference'] for c in comparisons),
             'n_per_value':len(first),'min':min(first),'max':max(first),
             'means':{str(v):mean(lengths[v]) for v in values},'comparisons':comparisons}
    return reports


def assert_design(items, *, require_complete=True):
    """Fail before capture on missing families, leakage, imbalance, or duplicate items."""
    from collections import Counter,defaultdict
    if len({it['id'] for it in items})!=len(items) or len({it['text'] for it in items})!=len(items):
        raise ValueError('duplicate item ID or text')
    groups=defaultdict(list)
    for it in items:
        if set(it)!= {'id','feature','class','domain','split','cluster','value','ids','text','meta'}:
            raise ValueError('unexpected item schema')
        if it['meta']['read_position']!=len(it['ids'])-1 or it['meta']['token_length']!=len(it['ids']):
            raise ValueError('read-position/token-length drift')
        groups[it['feature']].append(it)
    binary=[f for f in groups if f not in ORDINAL_FEATURES]
    if require_complete:
        if not 30<=len(binary)<=40: raise ValueError('need 30–40 binary rows')
        counts=Counter(FEATURES[f].kind for f in binary)
        if any(counts[c]<8 for c in ('count-like','state-like','semantic')):
            raise ValueError('need at least eight rows in every class')
    for feature,group in groups.items():
        split_clusters={s:{x['cluster'] for x in group if x['split']==s} for s in ('dev','test')}
        if split_clusters['dev']&split_clusters['test'] or len(split_clusters['dev'])!=len(split_clusters['test']):
            raise ValueError('template clusters leak or are not split 50/50')
        if require_complete and len(split_clusters['dev']|split_clusters['test'])<12:
            raise ValueError('fewer than twelve template families')
        if len([x for x in group if x['split']=='dev'])!=len([x for x in group if x['split']=='test']):
            raise ValueError('items not split 50/50')
        families={x['meta']['template_index'] for x in group}
        if len({template_signature(feature,t) for t in families})!=len(families):
            raise ValueError('nominally distinct families have identical authored templates')
        if feature in ORDINAL_FEATURES:
            counts=Counter(x['value'] for x in group)
            if set(counts)!=set(range(1,9)) or (require_complete and min(counts.values())<30):
                raise ValueError('need levels 1–8 with at least thirty items per level')
        elif require_complete:
            counts=Counter(x['value'] for x in group)
            if len(group)<120 or min(counts.values())<60:
                raise ValueError('need at least120 items and60 per binary value')
    return {'items':len(items),'binary_rows':len(binary),'ordinal_rows':len(groups)-len(binary),
            'classes':dict(Counter(FEATURES[f].kind for f in binary)),
            'rows':{f:{'items':len(g),'clusters':len({x['cluster'] for x in g}),
                'class':ALL_FEATURES[f].kind,'domain':ALL_FEATURES[f].domain,
                'kind':'ordinal' if f in ORDINAL_FEATURES else 'binary',
                'template_signatures':{str(t):template_signature(f,t) for t in sorted({x['meta']['template_index'] for x in g})}}
                for f,g in groups.items()}}


def load_pinned_tokenizer(path):
    from transformers import AutoTokenizer
    from .protocol import sha
    if sha(Path(path)/'tokenizer.json')!=TOKENIZER_SHA256:
        raise ValueError('tokenizer differs from pinned Qwen3.6-27B tokenizer')
    return AutoTokenizer.from_pretrained(path,local_files_only=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer',required=True,help='local pinned Qwen tokenizer directory')
    p.add_argument('--out',type=Path,default=Path('cache/g_agreement/blindspot/w1-bank'))
    p.add_argument('--seed',type=int,default=SEED)
    a=p.parse_args(argv)
    tok=load_pinned_tokenizer(a.tokenizer)
    items=build_items(tok,seed=a.seed)+build_ordinal_items(tok,seed=a.seed)
    assert_design(items)
    write_bank(a.out,items,assert_lengths(items),a.tokenizer,seed=a.seed)


if __name__=='__main__':
    main()
