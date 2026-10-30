from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re

import pytest

from projects.g_agreement.blindspot import items as I
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.w1_templates import TABLES, ROLE_PAIRS, render_body


def test_forty_features_cover_requested_domains_and_categories():
    assert len(I.FEATURES) == 40
    assert {f.domain for f in I.FEATURES.values()} == {'prose', 'python', 'latex', 'json', 'table', 'list'}
    assert Counter(f.kind for f in I.FEATURES.values()) == {'count-like':19, 'state-like':11, 'semantic':10}
    for f in ('python_depth','python_indent','latex_brace','json_depth','list_depth'):
        assert I.FEATURES[f].kind == 'count-like'
    for spec in I.ALL_FEATURES.values():
        for reader in ('olens','nla','jlens','logit'):
            assert len(spec.pairs(reader)) >= 2
            assert all(a != b for a,b in spec.pairs(reader))
            assert len(set(spec.pairs(reader))) == len(spec.pairs(reader))


def test_builder_shape_balance_read_position_and_retokenisation(tok):
    bank = I.build_items(tok, n_templates=12, pairs_per_template=7)
    report = I.assert_design(bank)
    assert len(bank) == 40*168
    assert report['binary_rows'] == 40
    pairs = defaultdict(list)
    for it in bank:
        assert it['ids'] == I.encode(tok,it['text'])
        assert it['meta']['read_position'] == len(it['ids'])-1
        assert it['text'].endswith(it['meta']['body'])
        assert it['text'].count(I.DELIMITER) == 1
        pairs[it['meta']['pair_id']].append(it)
    for pair in pairs.values():
        assert len(pair) == 2
        assert len({it['split'] for it in pair}) == 1
        assert len({it['cluster'] for it in pair}) == 1
        assert len({len(it['ids']) for it in pair}) == 1
        assert len({it['value'] for it in pair}) == 2
    for feature in I.FEATURES:
        row = [it for it in bank if it['feature']==feature]
        assert Counter(it['split'] for it in row) == {'dev':84,'test':84}
        assert Counter(it['value'] for it in row) == dict.fromkeys(I.FEATURES[feature].values,84)
        assert len({it['cluster'] for it in row}) == 12
        assert len({it['meta']['body'] for it in row}) == 168
        assert {it['cluster'] for it in row if it['split']=='dev'}.isdisjoint(
            {it['cluster'] for it in row if it['split']=='test'})
    lengths = I.assert_lengths(bank)
    assert len(lengths) == 80
    assert all(v['ks_p'] > .2 and v['abs_mean_difference'] <= 1 for v in lengths.values())


def test_deterministic_and_seed_changes_bank(tok):
    a=I.build_items(tok,2,2,seed=42,features=['python_line'])
    assert a == I.build_items(tok,2,2,seed=42,features=['python_line'])
    assert a != I.build_items(tok,2,2,seed=43,features=['python_line'])


def test_early_padding_preserves_local_feature(tok):
    bank=I.build_items(tok,2,2,features=['python_line','prose_sentence'])
    for early,late in (bank[i:i+2] for i in range(0,len(bank),2)):
        assert len(early['meta']['body']) < len(late['meta']['body'])
        assert early['text'].split(I.DELIMITER)[0].count(' note') > late['text'].split(I.DELIMITER)[0].count(' note')
        if early['feature']=='python_line':
            for it in (early,late):
                assert len(it['meta']['body'].splitlines())-1 == it['meta']['local_index']


def test_structural_ground_truth_all_twelve_families(tok):
    features=['prose_paren','prose_quote','list_depth','python_indent','prose_budget',
              'python_depth','latex_brace','json_depth','table_column','table_row','python_argument',
              'latex_fraction','latex_math','json_type','list_completed','prose_sentence']
    bank=I.build_items(tok,12,2,features=features)
    for it in bank:
        b=it['meta']['body'];feature=it['feature'];side=I.FEATURES[feature].values.index(it['value'])
        if feature=='prose_paren': assert b.count('(')-b.count(')') == 1-side
        if feature=='prose_quote': assert b.count('"') == (1 if side==0 else 2)
        if feature=='list_depth': assert (len(b.splitlines()[-1])-len(b.splitlines()[-1].lstrip()))//2+1 == (1 if side==0 else 3)
        if feature=='python_indent': assert (len(b.splitlines()[-1])-len(b.splitlines()[-1].lstrip()))//4 == (1 if side==0 else 3)
        if feature=='prose_budget': assert 40-len(b.split('\n\n')[1].split()) == (22 if side==0 else 3)
        if feature=='python_depth': assert b.count('[')-b.count(']') == (1 if side==0 else 3)
        if feature in ('latex_brace','json_depth'): assert b.count('{')-b.count('}') == (1 if side==0 else 3)
        if feature=='table_column': assert len(b.splitlines()[-1].split('|'))-1 == (1 if side==0 else 5)
        if feature=='table_row': assert len(b.splitlines())-2 == it['meta']['local_index']
        if feature=='python_argument': assert b.splitlines()[-1].count(',') == (0 if side==0 else 4)
        if feature=='latex_fraction': assert ('}{' in b) == (side==1)
        if feature=='latex_math': assert b.count('$')%2 == 1-side
        if feature=='json_type': assert bool(re.search(r': "\d+$',b)) == (side==0)
        if feature=='list_completed': assert b.count('[x]') == it['meta']['local_index']
        if feature=='prose_sentence': assert b.count('.')+1 == it['meta']['local_index']



def test_first_item_labels_mean_exactly_one_for_every_template_and_variant(tok):
    # Unlike 'early' rows, these frozen candidate descriptions explicitly say first.
    bank=I.build_items(tok,12,7,features=['latex_item','list_index','table_column','python_argument','json_field'])
    for it in bank:
        b=it['meta']['body'];feature=it['feature'];first=it['value']=='first'
        if feature=='latex_item':
            index=b.count('\\item ')
            assert index==it['meta']['local_index']
        elif feature=='list_index':
            index=len(b.splitlines())
            assert index==it['meta']['local_index']
        elif feature=='table_column':
            index=len(b.splitlines()[-1].split('|'))-1
        elif feature=='python_argument':
            index=b.splitlines()[-1].count(',')+1
        else:
            # Only fields in the currently open object determine the field index.
            index=b.rsplit('{',1)[1].count(':')
        assert (index==1)==first
        if not first: assert index>=4


def test_templates_are_fresh_and_family_content_is_not_only_padding():
    pilot_columns={'Name','City','Team','Role','Status','Office','Level','Language'}
    assert all(not (set(headers.split()) & pilot_columns) for headers,_ in TABLES)
    for feature in I.ALL_FEATURES:
        assert len({I.template_signature(feature,t) for t in range(12)}) == 12
    for t in range(12):
        inside,_=render_body('prose_paren',0,t,0,'river')
        outside,_=render_body('prose_paren',1,t,0,'river')
        assert 'old stone bridge' not in inside
        assert inside.replace('(', '').split() == outside.replace('(','').replace(')','').split()
        assert inside.split()[-5:] == outside.split()[-5:]



def test_latex_role_is_semantic_statement_versus_worked_calculation():
    assert len(ROLE_PAIRS)==12
    for t,(statement,worked) in enumerate(ROLE_PAIRS):
        abstract,_=render_body('latex_role',0,t,0,'river')
        concrete,_=render_body('latex_role',1,t,0,'river')
        wrapper=r'\noindent River case. '
        assert abstract==wrapper+statement and concrete==wrapper+worked
        assert abstract!=concrete
        assert not any(tag in abstract+concrete for tag in (r'\begin{theorem}',r'\begin{example}'))
        # Each worked side contains concrete numerical substitution/evaluation,
        # not merely the same generic sentence under a different environment.
        assert len(re.findall(r'\d+',worked))>=3 and '=' in worked
        assert statement!=worked and statement not in worked


def test_ordinal_levels_have_matched_lengths_and_structural_truth(tok):
    bank=I.build_ordinal_items(tok)
    assert len(bank) == 2*12*3*8
    for feature in I.ORDINAL_FEATURES:
        row=[x for x in bank if x['feature']==feature]
        assert Counter(x['value'] for x in row) == dict.fromkeys(range(1,9),36)
        assert len({x['cluster'] for x in row}) == 12
        assert {x['cluster'] for x in row if x['split']=='dev'}.isdisjoint(
            {x['cluster'] for x in row if x['split']=='test'})
        for x in row:
            b=x['meta']['body'];level=x['value']
            assert level == x['meta']['level']
            if feature=='table_column_ordinal': assert len(b.splitlines()[-1].split('|'))-1 == level
            else: assert b.count('[')-b.count(']') == level
    report=I.assert_lengths(bank)
    assert len(report)==4
    assert all(len(r['comparisons'])==28 and r['ks_p']==1 and r['abs_mean_difference']==0 for r in report.values())


def test_bank_separates_labels_and_freezes_causal_subset(tok,tmp_path):
    bank=I.build_items(tok,12,7,features=['python_line'])+I.build_ordinal_items(tok,2,1)
    root=tmp_path/'bank'
    P.write_bank(root,bank,I.assert_lengths(bank),'toy-test-only')
    P.verify(root,'INPUT_SEAL.json')
    data=P.rows(root/'items.input.jsonl')
    assert all(set(x)=={'id','feature','ids','donor_id'} for x in data)
    labels={x['id']:x for x in P.rows(root/'labels.DO_NOT_STAGE.jsonl')}
    for row in data:
        if row['feature'] in I.ORDINAL_FEATURES:
            assert row['donor_id'] is None
        else:
            assert labels[row['id']]['value'] != labels[row['donor_id']]['value']
            assert labels[row['id']]['cluster'] == labels[row['donor_id']]['cluster']
    causal=json.loads((root/'causal.input.json').read_text())
    assert len(causal)==84
    assert all(labels[k]['split']=='test' for k in causal)
    assert all(row['donor_id'] in causal for row in data if row['id'] in causal)
    templates=json.loads((root/'templates.json').read_text())
    assert templates['python_depth_ordinal']['score_orientation']=='increasing_level_positive'
    assert len(templates['python_line']['olens'])==2


def test_design_fails_for_template_leakage_and_bad_lengths(tok):
    bank=I.build_items(tok,2,2,features=['python_line'])
    bank[0]['cluster']=next(x['cluster'] for x in bank if x['split']=='test')
    with pytest.raises(ValueError,match='leak'):
        I.assert_design(bank,require_complete=False)
    bank=I.build_items(tok,2,2,features=['python_line'])
    for x in bank:
        if x['value']=='early': x['ids'] += [999]*10
    with pytest.raises(ValueError,match='length mismatch'):
        I.assert_lengths(bank)



def test_qwen_native_baseline_pairs_are_frozen_single_token_contrasts(tmp_path):
    import common  # expose only the pinned vendored src tree
    from mats.readers.jlens import token_variants
    default=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots'/I.TOKENIZER_REVISION
    configured=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    path=Path(configured) if configured else default
    if not (path/'tokenizer.json').is_file():
        if configured: pytest.fail('configured pinned Qwen tokenizer is missing')
        pytest.skip('real tokenizer absent: native baseline labels not validated')
    tok=I.load_pinned_tokenizer(path)
    assert set(P.BASELINE_SYNONYMS)==set(I.ALL_FEATURES)
    # Audit the actually frozen templates, including both ordinal rows.
    bank=I.build_items(tok,2,1)+I.build_ordinal_items(tok,2,1)
    destination=tmp_path/'baseline-audit'
    P.write_bank(destination,bank,I.assert_lengths(bank),path)
    definitions=json.loads((destination/'templates.json').read_text())
    for feature,spec in I.ALL_FEATURES.items():
        definition=definitions[feature]
        assert definition['values']==list(spec.values)
        assert definition['olens']==[list(pair) for pair in spec.pairs('olens')]
        assert definition['nla']==[list(pair) for pair in spec.pairs('nla')]
        pairs=definition['jlens']
        assert pairs==definition['logit']
        assert pairs==[list(spec.tokens),list(P.BASELINE_SYNONYMS[feature])]
        assert len(pairs)==2 and pairs[0]!=pairs[1]
        for a,b in pairs:
            assert len(a.split())==len(b.split())==1
            ia,ib=token_variants(tok,[a]),token_variants(tok,[b])
            assert ia and ib, (feature,a,b)
            assert set(ia).isdisjoint(ib), (feature,a,b)
        assert definition['score_orientation']==('increasing_level_positive' if feature in I.ORDINAL_FEATURES else 'value_A_positive')
    # Explicitly exercise rows whose positive direction differs from related rows.
    assert definitions['prose_budget']['jlens']==[['many','few'],['more','less']]
    assert definitions['prose_words']['jlens']==[['few','many'],['fewer','more']]
    assert definitions['python_depth']['jlens']==[['shallow','deep'],['flat','nested']]
    assert definitions['python_depth_ordinal']['jlens']==[['deep','shallow'],['nested','flat']]
    assert definitions['table_column_ordinal']['jlens']==[['later','earlier'],['subsequent','initial']]


def test_qwen_tokenizer_full_bank_preflight():
    """Mandatory executed pre-capture check; a skipped test is never a receipt."""
    default=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots'/I.TOKENIZER_REVISION
    configured=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    path=Path(configured) if configured else default
    if not (path/'tokenizer.json').is_file():
        if configured: pytest.fail('configured pinned Qwen tokenizer is missing')
        pytest.skip('real tokenizer absent: capture remains blocked until this test executes')
    tok=I.load_pinned_tokenizer(path)
    bank=I.build_items(tok)+I.build_ordinal_items(tok)
    design=I.assert_design(bank)
    assert design['items']==7296
    assert all(x['ids']==I.encode(tok,x['text']) for x in bank)
    lengths=I.assert_lengths(bank)
    assert len(lengths)==84
    assert all(v['ks_p']>.2 and v['abs_mean_difference']<=1 for v in lengths.values())
    assert P.sha(path/'tokenizer.json')==I.TOKENIZER_SHA256
    receipt=os.environ.get('BLINDSPOT_PREFLIGHT_RECEIPT')
    if receipt:
        P.dump(receipt,{'status':'PASS','tokenizer_sha256':I.TOKENIZER_SHA256,'tokenizer_revision':I.TOKENIZER_REVISION,
                        'items':len(bank),'binary_rows':40,'ordinal_rows':2,'strata':len(lengths),
                        'min_ks_p':min(v['ks_p'] for v in lengths.values()),
                        'max_abs_mean_difference':max(v['abs_mean_difference'] for v in lengths.values()),
                        'all_items_retokenized':True,'lengths':lengths,
                        'items_source_sha256':P.sha(Path(I.__file__)),
                        'templates_source_sha256':P.sha(Path(I.__file__).with_name('w1_templates.py'))})
