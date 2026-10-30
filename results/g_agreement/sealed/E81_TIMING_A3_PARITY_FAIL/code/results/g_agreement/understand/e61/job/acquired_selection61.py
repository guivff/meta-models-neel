"""§177 clarification1,6f9088bb: select by acquired identities, never readout content."""
from displays61 import select_three


def complete_units(records):
    groups={}
    for x in records:groups.setdefault((x['unit_id'],x['reader']),[]).append(x['repeat'])
    return {k for k,r in groups if all(len(groups.get((k,reader),[]))==1 and set(groups[k,reader])==set(range(1)) for reader in ('oracle','nla'))}


def select_d2(implicit_records,first_letter_records):
    acquired56=complete_units(implicit_records);acquired57=complete_units(first_letter_records)
    eligible=sorted(k for k in acquired56 if k.startswith('linewrap_implicit:') and k.replace('linewrap_implicit:','linewrap_asked:',1) in acquired56 and k.replace('linewrap_implicit:','count_gradient_first_letter:',1) in acquired57)
    selected=select_three(eligible)
    return {'eligible_implicit_ids':eligible,'implicit_ids':selected,'report_ids':[k.replace('linewrap_implicit:','linewrap_asked:',1) for k in selected],'first_letter_ids':[k.replace('linewrap_implicit:','count_gradient_first_letter:',1) for k in selected],'seed':20261027,'authority':'6f9088bb'}


def select_d3_d4(items,records):
    # Require every registered position and the single readout for both readers.
    from runtime61 import position_jobs
    jobs=position_jobs(items);adapted=[dict(x,unit_id=x['id']) for x in records];complete=complete_units(adapted)
    acquired={x['id'] for x in items if all(j['id'] in complete for j in jobs if j['item_id']==x['id'])}
    d3=select_three(sorted(x['id'] for x in items if x['display']=='D3' and x['id'] in acquired))
    bases=sorted({x['pair_id'] for x in items if x['display']=='D4' and all(y['id'] in acquired for y in items if y['display']=='D4' and y['pair_id']==x['pair_id'])})
    return {'D3':d3,'D4_base_items':select_three(bases),'seed':20261027,'authority':'6f9088bb'}
