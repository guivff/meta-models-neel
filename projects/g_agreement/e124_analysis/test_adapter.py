import pytest
from . import adapter as a


def fixture(new=68,stale=16,e82=True):
    m=[];c=[];j=[]
    for cond in a.CONDITIONS:
        for i in range(84):
            ident=f'{cond}:{i}'
            j.append(dict(id=ident,condition=cond))
            yes=i<(new if cond=='E109_52_steered' else stale if cond=='E104_U_44_steered' else 42)
            m.append(dict(id=ident,status='KEPT',result={'verdict':'YES'if yes else 'NO'}))
            c.append(dict(id=ident,status='KEPT',result={'verdict':'NO'if cond=='E109_52_steered' else 'YES'}))
    if e82:
        for i in range(5):
            ident=f'e82:{i}'
            j.append(dict(id=ident,condition='E82_belief_wrong',reader='oracle',row='wrong_bridge',item_id=str(i),position=0,belief_stating=True,cohort='belief_wrong'))
            m.append(dict(id=ident,status='KEPT',result={'verdict':'YES'if i<3 else 'NO'}))
            c.append(dict(id=ident,status='KEPT',result={'verdict':'YES'if i<2 else 'NO'}))
    return m,c,j


def test_three_registered_readings():
    r=a.summarize(*fixture());assert set(r['readings'].values())=={'MET'}
    assert r['caveat']==a.CAVEAT


def test_strict_threshold_sides():
    r=a.summarize(*fixture(new=67,stale=17));assert r['readings']['correct_readout_inversion']=='NOT MET';assert r['readings']['stale_readout_detection']=='NOT MET'


def test_missing_no_imputation():
    m,c,j=fixture();m[0].update(status='UNPARSEABLE',result=None)
    r=a.summarize(m,c,j);assert r['readings']['stale_readout_detection']=='NOT EVALUABLE'


def test_original_context_zero_required():
    m,c,j=fixture();c[168]['result']['verdict']='YES'
    assert a.summarize(m,c,j)['readings']['correct_readout_inversion']=='NOT MET'


def test_duplicate_or_incomplete_census_rejected():
    m,c,j=fixture()
    with pytest.raises(ValueError):a.summarize(m+[m[0]],c,j)
    with pytest.raises(ValueError):a.summarize(m[1:],c[1:],j[1:])


def test_e82_no_subset_unknown():
    r=a.summarize(*fixture(e82=False));assert r['readings']['belief_stating_increase']=='NOT EVALUABLE'


def test_e82_item_weighting_not_positions():
    m,c,j=fixture()
    for n in range(1,10):
        ident=f'extra{n}';j.append(dict(j[-5],id=ident,item_id='0',position=n))
        m.append(dict(id=ident,status='KEPT',result={'verdict':'YES'}));c.append(dict(id=ident,status='KEPT',result={'verdict':'YES'}))
    r=a.summarize(m,c,j);assert r['E82']['paired_complete_items']==5;assert r['E82']['model_yes']['rate']==.6


def test_schema_prompt():
    assert 'behavioural reference' in a.SYSTEM and 'supplied context' not in a.SYSTEM
    with pytest.raises(ValueError):a.verdict(dict(status='KEPT',result={'verdict':'MAYBE'}))


def reference_fixture(condition='E104_U_44_steered'):
    c=dict(id='opaque',condition=condition)
    b=dict(c,kind='frozen_continuation_pair',candidates=['candidate A','candidate B'],scores=[-2.,-1.],selected_index=1,reference_text='candidate B')
    return b,c


def test_registered_pair_choice_per_condition():
    for condition in a.CONDITIONS:
        b,c=reference_fixture(condition)
        assert a.model_reference(b,c,lambda x:x)=='candidate B'
        b.update(scores=[3.,2.],selected_index=0,reference_text='candidate A')
        assert a.model_reference(b,c,lambda x:x)=='candidate A'


@pytest.mark.parametrize('changes',[
    {'kind':'greedy_answer'}, {'selected_index':0}, {'scores':[1.,1.]},
    {'scores':[float('nan'),1.]}, {'reference_text':'invented'},
    {'condition':'E104_U_44_random'}, {'id':'another-item'}])
def test_wrong_measure_or_join_rejected(changes):
    b,c=reference_fixture();b.update(changes)
    with pytest.raises(ValueError):a.model_reference(b,c,lambda x:x)


def test_e82_original_filter_label_and_rendering():
    c=dict(id='opaque',condition='E82_belief_wrong')
    b=dict(c,kind='wtext_filter_belief',belief_label='B',belief_reference={'label':'B','text':'original belief'},reference_text='original belief')
    assert a.model_reference(b,c,lambda x:x)=='original belief'
    b['belief_reference']['label']='A'
    with pytest.raises(ValueError):a.model_reference(b,c,lambda x:x)


def test_reference_fields_resolved_from_original_pointers():
    b,c=reference_fixture();original={k:b[k] for k in ('candidates','scores','selected_index','reference_text')}
    for k in original:b[k]={'key':k}
    calls=[]
    def resolve(ref):
        calls.append(ref['key']);return original[ref['key']]
    assert a.model_reference(b,c,resolve)=='candidate B'
    assert set(calls)==set(original)


def test_prompt_is_exact_amended_file():
    assert a.HERE.joinpath('SYSTEM.txt').read_text()==a.SYSTEM+'\n'
    assert 'registered behaviour' in a.SYSTEM
    assert 'greedy' not in a.SYSTEM


def test_exact_published_transport_prompt():
    import ast
    source=a.ROOT/'projects/g_agreement/understand/blind_judge/internals_c/e124_amendment1_judge.py'
    tree=ast.parse(source.read_text())
    system=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM' for t in x.targets))
    assert a.SYSTEM==system


def test_v3_cohort_overrides_legacy_condition_name():
    assert a.registered_reference(dict(condition='E82_belief_wrong',cohort='belief_wrong'))
    assert not a.registered_reference(dict(condition='E82_belief_wrong',cohort='no_canonical_truth'))
    for condition in a.CONDITIONS:
        assert a.registered_reference(dict(condition=condition))


@pytest.mark.parametrize('cohort',[None,'belief_right','unknown'])
def test_missing_or_unregistered_cohort_rejected(cohort):
    with pytest.raises(ValueError):
        a.registered_reference(dict(condition='E82_belief_wrong',cohort=cohort))


def test_original_unknown_classification_stays_unknown():
    m,c,j=fixture();j[-1]['belief_stating']=None
    r=a.summarize(m,c,j)
    assert r['E82']['unknown_classification_items']==1
    assert r['readings']['belief_stating_increase']=='NOT EVALUABLE'
    assert r['E82']['belief_stating_items']==4


def test_three_categories_use_equal_item_weights():
    m,c,j=fixture();m[-1]['result']['verdict']='OFF-TOPIC'
    for n in range(1,6):
        ident=f'multi{n}';j.append(dict(j[252],id=ident,position=n))
        m.append(dict(id=ident,status='KEPT',result={'verdict':'YES'}))
        c.append(dict(id=ident,status='KEPT',result={'verdict':'YES'}))
    r=a.summarize(m,c,j)['E82']
    assert r['model_categories']['YES']['rate']==.6
    assert r['model_categories']['NO']['rate']==.2
    assert r['model_categories']['OFF-TOPIC']['rate']==.2
    assert r['model_readout_categories']['YES']['n']==10
    assert all(v['n']==5 and v['ci95'] is not None for v in r['model_categories'].values())
