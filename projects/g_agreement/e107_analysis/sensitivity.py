"""Prospective affected-readout exclusion; original scientific functions unchanged."""
from copy import deepcopy
from projects.g_agreement.understand.wmech2 import core
from .rules import analyze


def affected_items(items, audit, mapping, plans):
    core.require(audit['redacted_records']==len(audit['affected'])==5,'exact five affected opaque IDs')
    records={x['id']:x for x in audit['affected']}
    core.require(len(records)==5 and mapping['all_affected_mapped'] is True,'complete unique audit')
    links=mapping['affected']
    core.require(len(links)==5 and {x['opaque_id'] for x in links}==set(records),'exact audit/map membership')
    by=core.unique(items); affected=set()
    for link in links:
        plan=plans[link['plan_index']]
        ident=link['inventory_id']; target=link['target']
        core.require(plan['inventory_id']==ident and plan['target']==target,'original frozen plan mapping')
        core.require(ident in by and target in by[ident]['systems']['outside'],'mapped original outside target')
        for field in ('original_readout_sha256','judge_readout_sha256'):
            h=records[link['opaque_id']][field]
            core.require(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h),'original/copy hash custody')
        affected.add(ident)
    return affected


def sensitivity(items, rows, affected):
    masked=deepcopy(items)
    core.require(affected <= {x['id'] for x in items},'no unknown exclusion')
    for item in masked:
        if item['id'] in affected:
            # One readout may have both belief and truth targets. Exclude the
            # whole affected outside readout, preserving paired source census.
            item['systems']['outside']={k:None for k in item['systems']['outside']}
    return dict(role='affected outside readouts excluded; companion only',
                affected_source_items=len(affected),affected_opaque_ids=5,
                results=analyze(masked,rows))
