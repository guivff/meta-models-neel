"""Administrative missing-shard scope from §211; never selects by readout."""
def scope(plan,retained=False):
    separate=retained=='slot1-separate'
    if isinstance(retained,str) and not separate:raise ValueError('unknown administrative scope')
    slots=[1] if separate else ([0,2] if retained else [0,1,2])
    rows=[r for r in plan['rows'] if r['slot'] in slots]
    missing=[{'key':r['key'],'bank':r['bank'],'row':r['row'],'reader':reader,'status':'NOT EVALUABLE','reason':'outside separate slot1 bank; retained primary already reviewed and never pooled' if separate else 'slot1 outputs lost; rerun parked under§211'} for r in plan['rows'] if r['slot'] not in slots for reader in r['readers']]
    samples=sum(plan['shard_samples'][s] for s in slots)
    cells=sum(len(r['readers']) for r in rows)
    if separate and (samples!=17920 or cells!=28 or len(rows)!=18 or len(missing)!=55):raise ValueError('registered separate slot1 inventory')
    if retained and not separate and (samples!=35200 or cells!=55 or len(rows)!=36 or len(missing)!=28):raise ValueError('registered retained inventory')
    return {'mode':'separate_slot1_17920' if separate else ('retained35200' if retained else 'complete53120'),'authority':'E96deviation3,3899e1ea; direct Guiv separate reporting, no primary pooling/replay' if separate else ('§2116eca49bc; E96deviation2,2bdde763; direct Guiv analyze35200now' if retained else '§204clarification1,5902d5df'),'slots':slots,'samples':samples,'records':samples+cells*80,'rows_retained':len(rows),'reader_cells_retained':cells,'missing_reader_cells':missing}
