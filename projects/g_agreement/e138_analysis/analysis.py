"""Re-point E100 paired bootstrap and E127 rate summaries; no model/judge calls."""
from projects.g_agreement.e100_analysis.rules import Bootstrap, DRAWS, SEED
from projects.g_agreement.e127_analysis.common import rate, rule, require
ARMS=('clean','donor','random')
CODES=('recipient-old','donor-old','other','none')

def values(code):
    if code is None:return None
    if isinstance(code,str):
        require(code in CODES,'sealed role value code')
        return [] if code=='none' else [code]
    require(type(code) is list and len(code)==len(set(code)) and all(v in CODES[:3] for v in code),'original set-valued codes; none is empty list')
    return code

def exclusive(code,category):
    v=values(code)
    if v is None:return None
    if category=='dual_or_multiple':return int(len(v)>1)
    if category=='recipient_mentioned':return int('recipient-old' in v)
    if category=='donor_mentioned':return int('donor-old' in v)
    return int(v==([] if category=='none' else [category]))

def validate(records):
    require(len(records)==84 and len({x['item_id'] for x in records})==84,'exact original E104 fact_recall84')
    ids={x['item_id'] for x in records}
    for x in records:
        require(x['row']=='fact_recall' and x['block']==44,'fact_recall block44 only')
        require(x['donor_id'] in ids and x['donor_id']!=x['item_id'],'original matched donor identity')
        require(isinstance(x['recipient_old'],str) and isinstance(x['donor_old'],str) and x['recipient_old'] and x['donor_old'] and x['recipient_old']!=x['donor_old'],'distinct source-bound recipient/donor old values')
        require(set(x['arms'])==set(ARMS),'full clean/donor/random grid; no dropped cells')
        for v in x['arms'].values():values(v)
    return records

def analyze(records):
    validate(records)
    reported=CODES+('dual_or_multiple','recipient_mentioned','donor_mentioned')
    cells={('fact_recall','oracle',a+':'+c):{x['item_id']:exclusive(x['arms'][a],c) for x in records} for a in ARMS for c in reported}
    boot=Bootstrap(cells)
    arms={a:{c:dict(rate(list(cells[('fact_recall','oracle',a+':'+c)].values())),paired_item_bootstrap=boot.stat('fact_recall',a+':'+c)) for c in reported} for a in ARMS}
    for a in ARMS:
        for c,s in arms[a].items():
            s['full84_missing_bounds']=[s['k']/84,(s['k']+s['missing_n'])/84]
    recipient=arms['donor']['recipient-old'];donor=arms['donor']['donor-old'];random=arms['random']['recipient-old']
    positive=rule([None if recipient['estimate'] is None else recipient['estimate']<=.05,
                   None if donor['estimate'] is None else donor['estimate']>=.40])
    withdrawal=rule([None if random['estimate'] is None else random['estimate']>=.20])
    wording=('withdraw stale-readout wording' if withdrawal=='MET' else
             'activation specificity supported by donor arm; random withdrawal check unknown' if positive=='MET' and withdrawal=='NOT EVALUABLE' else
             'activation specificity supported by donor arm' if positive=='MET' else 'report per-arm rates; no positive activation-specificity reading')
    return dict(experiment='E138',authority='250 clarification1',status='DESCRIPTIVE',planned_n=84,
        arms=arms,donor_primary=positive,random_withdrawal=withdrawal,reading=wording,
        donor_positive_robust_to_missing=recipient['full84_missing_bounds'][1]<=.05 and donor['full84_missing_bounds'][0]>=.40,
        random_withdrawal_robust_to_missing=random['full84_missing_bounds'][0]>=.20,
        contrasts={a:boot.stat('fact_recall',a+':recipient-old','clean:recipient-old') for a in ('donor','random')},
        bootstrap=dict(draws=DRAWS,seed=SEED,unit='original paired recipient item'),
        caveat='Random may be off-distribution; low random recipient-old is never positive evidence. Activation specificity cannot separate fact reading from reconstructing and re-solving the donor question with shared weights.',
        missing_policy='none is an observed value-code outcome, distinct from terminal missing; each arm reports its none rate beside all value rates; no extra CI/completeness decision gate')
