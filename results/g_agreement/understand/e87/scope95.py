"""E95 scope binding for the existing E87 engine; no row selection or outcomes."""
import hashlib
import re
import numpy as np
from contract import require, write


def validate95(items, plan, layers, seed):
    require(plan['layers'] == ([20,36,44,56] if plan['reduction_step']==0 else [36,44,56]) and plan['oracle_positions'] == 8
            and plan['nla_positions'] == 8 and plan['seed'] == seed, 'registered E95 grid')
    require(plan['short_positions'] == 'available', 'short-prompt ruling required')
    require(plan['nla_placebo'] is True and plan['reduction_step'] in (0,1,2,3) and
            plan['scope_authority'] == '1b0a2fcfc50d8d57d97a2f3cd84f8f88ca4e4a85', 'owner scope authority required')
    roster = plan['row_roster']
    require([r['row_index'] for r in roster] == list(range(len(roster))) and roster,
            'complete ordered opaque row roster')
    for r in roster:
        require(set(r) == {'row_index', 'test_count', 'item_ids', 'nla_norm', 'nla_norm_seal_sha256', 'placebo_positions', 'reuse_e87'} and
                type(r['test_count']) is int and r['test_count'] > 0 and
                len(r['item_ids']) == min(30 if plan['reduction_step']<2 or r['reuse_e87'] else 20, r['test_count']), 'first owner-frozen IDs')
        require(len(r['placebo_positions'])==15 and all(type(n) is int and 1<=n<=8 for n in r['placebo_positions']), '15 matched position counts')
        require(np.isfinite(r['nla_norm']) and r['nla_norm']>0 and re.fullmatch('[0-9a-f]{64}',r['nla_norm_seal_sha256']), 'sealed per-bank NLA norm')
    selected = plan['row_indices']
    require(selected == sorted(set(selected)) and selected and
            set(selected) <= set(range(len(roster))), 'whole-row shard')
    require(plan['mode'] in ('remaining','nla_placebo_only') and all(roster[r]['reuse_e87'] == (plan['mode']=='nla_placebo_only') for r in selected), 'E87 real cells must be reused, never rerun')
    ids = [i for r in selected for i in roster[r]['item_ids']]
    global_indices = [30*r+i for r in selected for i in range(len(roster[r]['item_ids']))]
    require([x['id'] for x in items] == ids == plan['item_ids'] and len(set(ids)) == len(ids)
            and [x['global_index'] for x in items] == global_indices, 'frozen shard order')
    for x in items:
        require(set(x) == {'id', 'global_index', 'ids', 'read_index', 'reuse44'}, 'public input allowlist')
        require(x['ids'] and all(type(t) is int and t >= 0 for t in x['ids']) and
                type(x['read_index']) is int and x['read_index'] == len(x['ids'])-1 and
                x['read_index'] >= 0, 'available positions exist')
        require(type(x['reuse44']) is bool, 'reuse flag')
    return items


def pseudo_items(plan):
    return [dict(id=hashlib.sha256(f'E95:placebo:{r}:{i}'.encode()).hexdigest()[:32],
                 global_index=r*15+i, read_index=plan['row_roster'][r]['placebo_positions'][i]-1,
                 position_count=plan['row_roster'][r]['placebo_positions'][i])
            for r in plan['row_indices'] for i in range(15)]


def placebo95(real, items, plan, destination, layers, dim, norm_match):
    """Fifteen independent pseudo-items, using all selected real norms per row.

    Oracle random stream stays invariant when adding optional NLA placebo. Whole-row
    sharding consumes the same global stream, independent of which rows a pod owns.
    """
    output_layers = tuple(layers) + ((42,) if plan['nla_placebo'] else ())
    pseudos = pseudo_items(plan)
    index = {x['global_index']: i for i, x in enumerate(pseudos)}
    medians = {}
    for row in plan['row_indices']:
        ix = [i for i, x in enumerate(items) if x['global_index']//30 == row]
        medians[row] = {}
        for l in output_layers:
            if l==42:
                medians[row][l]=np.full(16,plan['row_roster'][row]['nla_norm'])
            else:
                norms=np.linalg.norm(real[l][ix].astype(np.float64),axis=-1)
                medians[row][l]=np.array([np.median(norms[norms[:,j]>0,j]) if np.any(norms[:,j]>0) else 1.0 for j in range(16)])
    result = {l: np.lib.format.open_memmap(destination/f'placebo{l}.npy', mode='w+',
               dtype=np.float32, shape=(len(pseudos), 16, dim)) for l in output_layers}
    oracle_rng = np.random.default_rng(plan['seed'])
    nla_rng = np.random.default_rng(plan['seed'])
    for global_index in range(max(index)+1):
        z = oracle_rng.standard_normal((len(layers), 16, dim)).astype(np.float32)
        zn = nla_rng.standard_normal((16, dim)).astype(np.float32) if plan['nla_placebo'] else None
        if global_index not in index:
            continue
        i = index[global_index]; row = global_index//15
        start=16-pseudos[i]['position_count']
        for k, l in enumerate(layers):
            result[l][i]=0
            result[l][i,start:] = norm_match(z[k,start:], medians[row][l][start:])
        if zn is not None:
            result[42][i]=0
            result[42][i,start:] = norm_match(zn[start:], medians[row][42][start:])
    for h in result.values():
        h.flush()
    write(destination/'NORM_MATCH.json', dict(experiment='E95', seed=plan['seed'],
          target='median of selected real norms at same row/layer/position',
          real_count=len(items), placebo_count=len(pseudos), nla_placebo=plan['nla_placebo'],
          scope_authority=plan['scope_authority'],
          row_layer_position_medians={str(r): {str(l): v.tolist() for l, v in d.items()}
                                      for r, d in medians.items()}))
    write(destination/'PLACEBO_ITEMS.json', pseudos)
    return result


def acquire_reuse_placebo(items,plan,b,c,out,binding,layers,dim,norm_match):
    from contract import seal
    from worker87 import first_output
    import time
    pseudos=pseudo_items(plan)
    c.remaining=dict(oracle_setup=1,nla_setup=1,placebo_build=1,nla_native=len(pseudos))
    c.call('oracle_setup',b.load_oracle);c.remaining['oracle_setup']=0
    c.call('nla_setup',b.load_nla);c.remaining['nla_setup']=0
    cap=out/'capture';cap.mkdir()
    vectors=c.call('placebo_build',lambda:placebo95({},items,plan,cap,(),dim,norm_match))
    c.remaining['placebo_build']=0
    seal(cap,'CAPTURE_SEAL.json',**binding,reader_outputs=0,real_capture_reused=True,first_output_utc='unknown',first_output_evidence=None)
    jobs=out/'jobs';jobs.mkdir()
    dummy=np.random.default_rng(plan['seed']+42).standard_normal((8,dim)).astype(np.float32)
    c.call('nla_42_warmup_discarded',lambda:b.sweep('nla',dummy,42))
    count=0
    for i,item in enumerate(pseudos):
        n=item['position_count'];h=vectors[42][i,-n:].copy();before=h.tobytes()
        values=(c.native('nla','placebo',42,h,lambda:b.sweep('nla',h,42)) if getattr(c,'profile95',False)
            else c.call('nla_native',lambda:b.sweep('nla',h,42),real=True))
        require(h.tobytes()==before and len(values)==n,'unaltered NLA placebo grid')
        write(jobs/f'nla_placebo_42_{i:04d}.json',[
            dict(id=f"{item['id']}:nla:placebo:42:{j}",unit_id=item['id'],
                 global_index=item['global_index'],reader='nla',arm='placebo',layer=42,
                 position=j,position_offset=j-n+1,**v) for j,v in enumerate(values)])
        count+=n;c.remaining['nla_native']-=1;c.admit()
    seal(jobs,'nla_STAGE_SEAL.json',**binding,reader='nla',status='COMPLETE',**first_output(out))
    write(out/'COUNTS.json',dict(oracle=0,nla=count,real_readouts=0))
