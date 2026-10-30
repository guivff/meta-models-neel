"""Bind W-text's frozen hallucination/R-WS2 rendering; CPU-only claim inventory.

Quote/tally rules replicated from pinned wsbench hallucination/judge.py, never
imported/executed from upstream. No scientific analysis or raw readout inspection.
"""
import importlib.util
import re
from pathlib import Path
from projects.g_agreement.readerbench.io import read,sha,verify
from projects.g_agreement.readerbench.scoring import require
ROOT=Path(__file__).resolve().parents[4]
HEADLINE_SHA='61bafdda8bfae96c533e2699c3a75bdb39c08bfe82407610bec591fd53b176eb'


def load_frozen():
    root=ROOT/'results/g_agreement/understand/e99'
    verify(root/'HEADLINE_SEAL.json',HEADLINE_SHA)
    def module(name):
        spec=importlib.util.spec_from_file_location('_e99_'+name,root/(name+'.py'))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    return module('hallucination99'),module('corroboration99')


def normalize(s):
    return re.sub(r'\s+',' ',s.translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'",'«':'"','»':'"'}))).strip().lower()


def quoted(q,readout):
    q=normalize(q);return len(q)>=3 and q in normalize(readout)


def sample_zero(raw):
    require(type(raw) is dict and type(raw.get('samples')) is list,'family samples required')
    by={s['idx']:s for s in raw['samples'] if isinstance(s,dict) and type(s.get('idx')) is int}
    require(0 in by,'sample0 missing: unjudged, never silent')
    return by[0]


def wrong_spans(raw,readout):
    sample=sample_zero(raw)
    require(type(sample.get('spans')) is list,'family spans required')
    return [s['text'] for s in sample['spans'] if quoted(s.get('text',''),readout) and str(s.get('type') or '').strip().lower()!='off_topic']


def claim_inventory(stage1,stage2,readout):
    wrong=wrong_spans(stage1,readout);sample=sample_zero(stage2)
    require(type(sample.get('claims')) is list,'verification missing: unjudged')
    units=[dict(quote=q,status='false') for q in wrong]
    counts=dict(false=len(wrong),true=0,unverifiable=0,disputed=0,off_topic=0,n_unverified=0)
    for c in sample['claims']:
        q=str(c.get('quote') or '')
        if not quoted(q,readout):counts['n_unverified']+=1;continue
        nq=normalize(q)
        if any(normalize(w) in nq or nq in normalize(w) for w in wrong):continue
        st=str(c.get('status') or '').strip().lower()
        if st=='true':counts['true']+=1;units.append(dict(quote=q,status='true'))
        elif st=='off_topic':counts['off_topic']+=1
        elif st=='disputed':counts['disputed']+=1;counts['unverifiable']+=1
        else:counts['unverifiable']+=1
    # Opaque order IDs never encode truth. Preserve original false units then verified true units;
    # truth stays in the CPU-only join, never in the corroboration render argument.
    public=[dict(claim_id=f'claim-{i:04d}',quote=u['quote']) for i,u in enumerate(units)]
    private=[dict(p,status=u['status']) for p,u in zip(public,units)]
    return public,private,counts
