"""§215 rules; §221.3 placebo argument is the retrained statement rate."""
from projects.g_agreement.understand.wmech2.core import stats
TRAIN=('nesting_depth','indent_level','page_range_digit')
HELD=('line_length','container_after_move','holder_after_handovers','branch_taken','var_type_at_use')
CONTENT=('format_plan','language_plan','fact_recall','tense_implicit')
DRAWS,SEED=2000,20261027

def both(*values):return False if False in values else None if None in values else True

def either(*values):return True if True in values else None if None in values else False

def threshold(x,t,op):
    if x is None:return None
    x=round(x,12)
    return x>=t if op=='ge' else x<=t

def at_least(values,n):
    yes=sum(v is True for v in values);unknown=sum(v is None for v in values)
    return True if yes>=n else None if yes+unknown>=n else False

def label(x):return 'NOT EVALUABLE' if x is None else 'MET' if x else 'NOT MET'

def paired(items):
    # Identity is source-row-local. Source transport must reject duplicate IDs.
    ids=[x['item_id'] for x in items]
    if len(set(ids))!=len(ids):raise ValueError('duplicate source item')
    original={x['item_id']:x['original'] for x in items}
    intervention={x['item_id']:x['intervention'] for x in items}
    return dict(original=stats(original),intervention=stats(intervention),difference=stats(intervention,original))

def rules(train,held,content,placebo,loss_decreased,recipe_completed):
    if set(train)!=set(TRAIN) or set(held)!=set(HELD) or set(content)!=set(CONTENT):raise ValueError('exact3/5/4 rows; no E102 scope import')
    improve=[];small=[]
    for row in TRAIN:
        d=train[row]['difference'];ci=d['CI95']
        improve.append(both(threshold(d['estimate'],.30,'ge'),None if ci is None else ci[0]>0))
        small.append(threshold(d['estimate'],.10,'le'))
    stable=[threshold(content[row]['difference']['estimate'],-.10,'ge') for row in CONTENT]
    transfer=[threshold(held[row]['difference']['estimate'],.20,'ge') for row in HELD]
    prior_ok=threshold(placebo,.20,'le');prior_bad=threshold(placebo,.30,'ge')
    train_ok=at_least(improve,2);content_ok=at_least(stable,3)
    decoder_limit=both(at_least(small,3),recipe_completed,loss_decreased)
    return dict(R_FX1=label(both(train_ok,content_ok,prior_ok)),R_FX2=label(at_least(transfer,2)),
                falsifier=label(either(decoder_limit,prior_bad)),
                train_improvement=dict(zip(TRAIN,improve)),content_no_degradation=dict(zip(CONTENT,stable)),
                heldout_transfer=dict(zip(HELD,transfer)),placebo_le_point20=prior_ok,
                placebo_ge_point30=prior_bad,decoder_limit_component=decoder_limit,
                recipe_completed=recipe_completed,loss_decreased=loss_decreased)
