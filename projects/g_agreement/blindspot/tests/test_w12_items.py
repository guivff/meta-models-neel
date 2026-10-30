import json
from pathlib import Path
import pytest
from projects.g_agreement.blindspot import w12_items as W,protocol as P

def test_frozen_binding_and_design():
    out=P.ROOT/'results/g_agreement/blindspot/w12/freeze';f=json.loads((out/'FREEZE.json').read_text())
    for n,h in f['files'].items():assert P.sha(out/n)==h
    assert P.sha(Path(W.__file__))==f['source_sha256']
    items=P.rows(out/'items.jsonl');assert len(items)==1008
    assert set(f['rows'])==set(W.DEFS)
    assert all(x['meta']['read_position']==len(x['ids'])-1 for x in items)

def test_all_authored_position_and_paragraph_labels():
    for t in range(12):
        for n in W.NOUNS:
            a,b=W.bodies('sentence_position',t,n);assert len(a.split())<=3 and len(b.split())>12
            a,b=W.bodies('paragraph_index',t,n);assert len(a.split('\n\n'))==1 and len(b.split('\n\n'))==3
            a,b=W.bodies('paragraph_start',t,n);assert '.' not in a and b.count('.')==1
            a,b=W.bodies('clause_embedding',t,n);assert not any(w in a.split() for w in ('who','whose','whom','while'));assert any(w in b.split() for w in ('who','whose','whom'))

def test_heldout_family_balance_exact_lengths():
    items=P.rows(P.ROOT/'results/g_agreement/blindspot/w12/freeze/items.jsonl')
    for row,(values,_,_) in W.DEFS.items():
        for split in ('dev','test'):
            cells=[[x for x in items if x['feature']==row and x['split']==split and x['value']==v] for v in values]
            assert all(len(c)==42 and len({x['cluster'] for x in c})==6 for c in cells)
            assert sorted(len(x['ids']) for x in cells[0])==sorted(len(x['ids']) for x in cells[1])
    assert any('by the' in a and ' was the ' in a for a,b in W.ROLE)
