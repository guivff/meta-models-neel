"""Lossless E95 source-record grouping; no regex or judge code is produced.

This only prepares candidates. A final packet still requires the original
regex disposition audit, frozen JUDGE_INDEX and existing admission.
"""
import hashlib
from collections import defaultdict
from pathlib import Path

from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge import e87
from .judge_admission import group_id


def row_values(records, feature):
    """Same frozen 1->A, 0->B orientation as funded_queue.prepare_e87."""
    selected = [x for x in records if x['feature'] == feature]
    values = {letter: sorted({x['value'] for x in selected if x['label'] == label})
              for letter, label in (('A', 1), ('B', 0))}
    require(all(len(v) == 1 for v in values.values()), 'unique original literal row values')
    return {letter: value[0] for letter, value in values.items()}


def grouped(row, arm, reader, layer, unit, records, item, values):
    """Validate exact source IDs/positions before copying any native text."""
    require(arm in ('real','placebo') and reader in ('oracle','nla'), 'native arm/reader')
    require(layer in row['oracle_layers'] if reader == 'oracle' else layer == 42,
            'only frozen achieved layers')
    if arm == 'real':
        require(unit in row['item_ids'] and item['id'] == unit, 'frozen real item')
        index, endpoint = item['global_index'], item['read_index']
        n = min(8, len(item['ids']))
    else:
        candidates = {hashlib.sha256(f"E95:placebo:{row['row_index']}:{i}".encode()).hexdigest()[:32]: i
                      for i in range(15)}
        require(unit in candidates, 'original deterministic placebo identity')
        i = candidates[unit]
        index = row['row_index']*15+i
        # The exact pseudo-item is supplied by the sealed original worker input.
        require(item['id'] == unit and item['global_index'] == index, 'original placebo source item')
        endpoint = item['read_index']; n = item['position_count']
        require(type(n) is int and 1 <= n <= 8, 'sealed original placebo position count')
    ordered = sorted(records, key=lambda x:x['position_offset'])
    require([x['position_offset'] for x in ordered] == list(range(1-n,1)),
            'whole original ordered positions, no duplicates or padding')
    require(all(x['unit_id']==unit and x['global_index']==index
                and x['reader']==reader and x['arm']==arm and x['layer']==layer
                and x['position']==endpoint+x['position_offset']
                and type(x['text']) is str for x in ordered),
            'literal original item/reader/arm/layer/position source keys')
    stratum=f"{row['row_index']}:{arm}:{reader}"
    result=dict(id=group_id(stratum,f'{unit}:{layer}'),property=row['row'],values=values,
                positions=[dict(offset=x['position_offset'],readout=x['text']) for x in ordered])
    e87.validate_source([result])
    return result


def candidates(spec, out):
    """Copy whole sealed native groups; leave regex disposition to its owner."""
    from .judge_admission import universe
    from .stage_complete import admission as admit_stages
    rows=read(spec['inventory'])['rows']; by_row={r['row_index']:r for r in rows}
    expected=universe(rows)
    eligible=admit_stages(spec,expected)
    bank_rows={}
    metadata_sources=[]
    roster_sources={s['bank']:s for s in read(spec['inventory'])['sources']}
    for bank,p in spec['bank_sources'].items():
        p=Path(p);s=roster_sources[bank]
        require(sha(p)==s['bank_seal_sha256'],'original bank seal identity')
        seal=read(p);items=p.parent/'items.PRIVATE.json'
        require(sha(items)==s['items_sha256']==seal['files']['items.PRIVATE.json'],
                'original CPU-only values and labels')
        bank_rows[bank]=read(items)
        metadata_sources.append(dict(path=str(p),sha256=sha(p)))
    values={r['row_index']:row_values(bank_rows[r['bank']],r['row'])for r in rows}
    private_map=Path(spec['source_map'])
    require(sha(private_map)==spec['source_map_sha256'],'original I-3 item/source mapping')
    source_map={x['opaque_id']:x for x in read(private_map)}
    native={};joins=[];source_seals=[]
    for shard,source in spec['stage_sources'].items():
        op=Path(source['output_seal']);output=read(op);sp=Path(source['input_seal'])
        require(sha(sp)==output['input_seal_sha256'],'original shard input seal')
        inp=verify(sp,sha(sp));real_items=read(sp.parent/'items.json')
        plan=read(sp.parent/'PLAN.json')
        require(plan['experiment']=='E95' and plan['oracle_positions']==8,
                'original step3 eight-position acquisition')
        public={x['id']:x for x in real_items}
        pp=op.parent/'capture/PLACEBO_ITEMS.json'
        require(sha(pp)==output['files']['capture/PLACEBO_ITEMS.json'],'original achieved pseudo-items')
        pseudos={x['id']:x for x in read(pp)}
        manifest=read(source['manifest']);records=defaultdict(list);pointers=defaultdict(list)
        for member,h in output['files'].items():
            if not(member.startswith('jobs/') and member.endswith('.json') and not member.endswith('SEAL.json')):continue
            reader=member.split('/',1)[1].split('_',1)[0]
            if reader not in ('oracle','nla') or not manifest[reader+'_stage_complete']:continue
            p=op.parent/member
            require(sha(p)==h,'original native job member hash')
            raw=read(p)
            require(type(raw)is list,'original job record list')
            for index,x in enumerate(raw):
                row=x['global_index']//(15 if x['arm']=='placebo'else 30)
                key=(row,x['arm'],x['reader'],x['layer'],x['unit_id'])
                records[key].append(x)
                pointers[key].append(dict(seal=str(op),seal_sha256=sha(op),member=member,
                                          member_sha256=h,keys=[index,'text']))
        for (ri,arm,reader,layer,unit),raw in sorted(records.items()):
            row=by_row[ri];item=(public if arm=='real'else pseudos)[unit]
            g=grouped(row,arm,reader,layer,unit,raw,item,values[ri])
            require(g['id']in eligible and g['id']not in native,'unique eligible original native group')
            native[g['id']]=g
            join=dict(id=g['id'],row_index=ri,bank=row['bank'],row=row['row'],arm=arm,
                      reader=reader,layer=layer,public_item_id=unit,shard=shard,
                      source_pointers=pointers[(ri,arm,reader,layer,unit)])
            if arm=='real':
                m=source_map[unit]
                require(m['bank']==row['bank']and m['row']==row['row'],'same original row source')
                original=next(x for x in bank_rows[row['bank']]if x['id']==m['source_id'])
                require(original['split']=='test'and original['feature']==row['row'], 'original frozen test member')
                require(unit==hashlib.sha256(f"E95:{row['bank']}:{m['source_id']}".encode()).hexdigest()[:32],
                        'unchanged original deterministic public item identity')
                end=original.get('read_index',len(original['ids'])-1)
                require(item['ids']==original['ids'][:end+1], 'original native input prefix, no new source join')
                join.update(source_item_id=m['source_id'],true_label=original['label'],
                            target='A'if original['label']==1 else'B')
            else:
                join.update(true_label=None,target=None,
                            target_disposition='original placebo label binding remains analyst/owner custody; never inferred')
            joins.append(join)
        source_seals.extend([dict(path=str(op),sha256=sha(op)),dict(path=str(sp),sha256=sha(sp))])
    require(set(native)==eligible,'all and only whole acquired eligible groups, no stitching/refill')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    write(out/'ALL_GROUPS.PRIVATE.json',[native[k]for k in sorted(native)])
    write(out/'SOURCE_POINTERS.PRIVATE.json',joins)
    write(out/'CANDIDATE_SEAL.json',dict(experiment='E95',status='LOSSLESS_CANDIDATES_NOT_A_JUDGE_PACKET',
        n=len(native),stage_inventory_sha256=spec['stage_inventory_sha256'],
        inventory_sha256=sha(spec['inventory']),source_seals=source_seals,
        original_metadata_sources=metadata_sources,source_map_sha256=spec['source_map_sha256'],
        regex_audit_created=False,paid_calls=0,
        files={n:sha(out/n)for n in('ALL_GROUPS.PRIVATE.json','SOURCE_POINTERS.PRIVATE.json')}))
    for p in out.iterdir():p.chmod(0o600)
    return dict(n=len(native),candidate_seal_sha256=sha(out/'CANDIDATE_SEAL.json'),paid_calls=0)
