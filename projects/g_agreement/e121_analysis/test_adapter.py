import pytest
from . import adapter as a

def rows(value='wrong'):
    return [dict(id=f'{i}-{c}-{r}',item_id=str(i),condition=c,reader=r,**{'class':value}) for i in range(84) for c in ('steered','random') for r in ('oracle','nla')]

def test_stale_agreement_and_precision():
    z=a.analyze(rows())['conditions']['steered']
    assert z['same_value_agreement']['rate']==1 and z['old_given_agreement']['rate']==1
    assert z['E94']['ensemble']['precision']['rate']==0
    assert z['reading']=='agreement endorses stale readout'

def test_no_mention_not_decisive():
    z=a.analyze(rows('no mention'))['conditions']['steered']
    assert z['same_value_agreement']['rate']==0 and z['old_given_agreement']['rate'] is None
    assert z['E94']['agreement']['rate']==1

def test_new_value_positive_reading():
    z=a.analyze(rows('correct'))['conditions']['steered']
    assert z['E94']['ensemble']['precision']['rate']==1 and z['reading']=='disagreement flags staleness'

def test_missing_census_and_parseability():
    with pytest.raises(ValueError):a.analyze(rows()[:-1])
    xs=rows();xs[0]['class']=None
    z=a.analyze(xs)['conditions']['steered'];assert z['same_value_agreement']['n']==83 and z['audit']['excluded_either_UNPARSEABLE']==1

def test_wilson_reuse():
    z=a.e94.fraction(42,84);assert z['Wilson95'][0]<.5<z['Wilson95'][1]

def config_packet():
    config=dict(experiment='E121',row='fact_recall',base_items=84,items=168,conditions=['steered','random'],
        capture=dict(alpha=8,write_block=40,args={'arm':'U'},module_parameters={'READ_BLOCK':42}),
        reader=dict(native_layer=42,setup='load_nla only; never load_oracle'),
        public_input=dict(all84_original_flips_verified=True,original_flip_source_sha256='synthetic'),cpu_only={'sha256':'synthetic'})
    items=[dict(id=f'{i}-{a}',base_id=str(i),condition=a,row='fact_recall',alpha=8) for i in range(84) for a in ('steered','random')]
    return config,items

def test_original_config_cohort_representation():
    config,items=config_packet();assert len(a.config_cohort(config,items))==84

def test_input_subset_or_pair_replacement_rejected():
    config,items=config_packet()
    with pytest.raises(ValueError):a.config_cohort(config,items[:-1])
    items[0]['condition']='random'
    with pytest.raises(ValueError):a.config_cohort(config,items)

def test_wrong_hook_or_row_rejected():
    config,items=config_packet();config['capture']['write_block']=44
    with pytest.raises(ValueError):a.config_cohort(config,items)
    config,items=config_packet();items[0]['row']='other'
    with pytest.raises(ValueError):a.config_cohort(config,items)

def test_wrong_flip_lineage_rejected():
    config,items=config_packet();config['cpu_only']['sha256']='changed'
    with pytest.raises(ValueError):a.config_cohort(config,items)
