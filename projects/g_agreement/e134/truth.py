"""§242 ff005a9c7 unhooked truth hierarchy; labels remain CPU-only."""
from datetime import datetime,timezone
LABEL_BASED='label-based, not behaviour-verified'
BEHAVIOUR='behaviour-verified'
FACT_FALLBACK_UTC=datetime(2026,10,30,11,0,tzinfo=timezone.utc) # 12:00 CET


def e131_value(text,old,new,margin,a_value,old_symbol,new_symbol):
    from projects.g_agreement.e131_analysis.rules import classify
    if {old_symbol,new_symbol}!={'A','B'}:raise ValueError('original old/new A/B binding required')
    original=classify(text,old,new,margin,a_value)
    stated=original['text_value']
    selected=stated if stated!='neither' else original['pair_value']
    value=old_symbol if selected=='old' else new_symbol if selected=='new' else None
    return dict(truth=value,truth_basis=BEHAVIOUR,truth_method='E131 greedy parse_target_answer' if stated!='neither' else 'E131 same-pass pair-logit fallback')


def unhooked_value(row,old_value,*,e131=None,e131_sealed_at=None,as_of):
    if row not in ('fact_recall','language_plan') or old_value not in ('A','B'):raise ValueError('registered row/old_value required')
    if as_of.tzinfo is None:raise ValueError('timezone-aware actual intake time required')
    if row=='fact_recall':
        if e131 is not None:
            if e131_sealed_at is None or e131_sealed_at.tzinfo is None or e131_sealed_at>as_of:raise ValueError('actual E131 seal time required')
            if e131_sealed_at>FACT_FALLBACK_UTC:raise ValueError('late E131 cannot replace noon fallback or frozen selection')
            if e131['truth_basis']!=BEHAVIOUR:raise ValueError('actual E131 behaviour binding required')
            return dict(e131)
        if as_of<FACT_FALLBACK_UTC:raise ValueError('await sealed E131; fact old_value fallback only at12:00CET')
    return dict(truth=old_value,truth_basis=LABEL_BASED,truth_method='registered old_value; no behaviour measurement' if row=='language_plan' else 'registered old_value; E131 not sealed by12:00CET')
