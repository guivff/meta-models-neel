"""E57 acquisition extension to the E56 native backend. No forced choice."""
import json
import sys
import time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
E56 = HERE.parents[1] / 'e56/job'
sys.path.insert(0, str(E56))
from worker56 import Backend, readout_records
from contract56 import read, dump, seal, require, SEED
from counts57 import count_item


class ExtensionBudget:
    def __init__(self, started, pod_created, seconds=1800):
        require(seconds == 1800, 'E57 per-shard allocation')
        require(started >= pod_created, 'extension clock precedes custody')
        self.end = min(started + seconds, pod_created + 4800)
        self.observed = {}

    def check(self):
        require(time.time() < self.end - 60, 'E57 custody reserve')

    def call(self, phase, fn, remaining_units=0):
        self.check()
        started = time.monotonic()
        value = fn()
        self.observed[phase] = max(time.monotonic() - started, self.observed.get(phase, 0))
        self.check()
        require(time.time() + 1.5 * self.observed[phase] * remaining_units < self.end - 60, 'E57 NO_FIT ' + phase)
        return value


def validate_plan(plan, items, dev_labels):
    require(plan['experiment'] == 'E57' and plan['seed'] == SEED, 'E57 identity')
    require(set(plan['shards']) == {'0', '1', '2'}, 'same three E56 pods')
    rows = [row for rs in plan['shards'].values() for row in rs]
    require(len(rows) == len(set(rows)) and set(rows) == {x['feature'] for x in items}, 'row partition')
    lookup = {x['id']: x for x in items}
    require(len(lookup) == len(items), 'duplicate input item')
    for row in rows:
        ids = plan['native_ids'][row]
        require(len(ids) == len(set(ids)) == len([x for x in items if x['feature']==row and x['split']=='test']), 'all test items per condition')
        require(all(k in lookup and lookup[k]['feature'] == row and lookup[k]['split'] == 'test' for k in ids), 'native selection')
        specification = plan['rows'][row]
        if specification['probe_applicable']:
            dev = [x for x in items if x['feature'] == row and x['split'] == 'dev']
            require(len(dev) == 84 and len([x for x in items if x['feature'] == row and x['split'] == 'test']) == 84, 'binary probe split')
            require(dev_labels is None, 'labels stay on CPU')
        else:
            require(bool(specification['probe_not_applicable_reason']), 'explicit nonbinary probe reason')
        if specification['continuation_pairs'] is None:
            require(bool(specification['continuation_not_applicable_reason']), 'explicit unavailable continuation')
        for k in ids:
            if row in ('category_switch', 'capacity_list'):
                require(k in plan['count_metadata'], 'frozen count metadata required')
    return lookup


def acquire57(items, dev_labels, plan, backend, budget, out, assignment):
    validate_plan(plan, items, dev_labels)
    rows = plan['shards'][str(assignment['slot'])]
    selected = [x for x in items if x['feature'] in rows]
    indices = {x['id']: i for i, x in enumerate(selected)}
    out = Path(out)
    budget.call('oracle_setup', backend.load_oracle)
    backend.validate_tokenization(selected)
    parts = {42: [], 44: []}
    chunks = [selected[i:i + 8] for i in range(0, len(selected), 8)]
    for n, chunk in enumerate(chunks):
        values = budget.call('capture', lambda: backend.capture(chunk), len(chunks) - n - 1)
        for layer in parts:
            parts[layer].append(values[layer])
    acts = {layer: np.concatenate(v) for layer, v in parts.items()}
    cap = out / 'capture'
    cap.mkdir()
    for layer, h in acts.items():
        require(h.shape == (len(selected), 5120) and np.isfinite(h).all(), 'capture grid')
        np.save(cap / f'acts{layer}.npy', h)
    dump(cap / 'items.order.json', [x['id'] for x in selected])
    seal(cap, 'CAPTURE_SEAL.json', {'experiment': 'E57', 'slot': assignment['slot'], 'input_seal_sha256': assignment['e57_input_seal_sha256']})
    dump(out/'CPU_POSTPROCESS_REQUIRED.json',{'probe':True,'labels_on_pod':False})
    counts = []
    for reader in ('oracle', 'nla'):
        if reader == 'nla':
            budget.call('nla_setup', backend.load_nla)
        layer = 44 if reader == 'oracle' else 42
        jobs = [(row, plan['native_ids'][row][i:i + 8]) for row in rows for i in range(0, len(plan['native_ids'][row]), 8)]
        with (out / (reader + '.native.jsonl')).open('x') as stream:
            for n, (row, ids) in enumerate(jobs):
                ix = [indices[k] for k in ids]
                units = [selected[i] for i in ix]
                outputs = budget.call(reader + '_native', lambda: backend.native_one(reader, acts[layer][ix]), len(jobs) - n - 1)
                records = readout_records(reader, units, outputs, 'text')
                for r in records:
                    stream.write(json.dumps(r, allow_nan=False) + '\n')
                if row in ('category_switch', 'capacity_list'):
                    for unit in units:
                        counts.append(count_item([r for r in records if r['unit_id'] == unit['id']], plan['count_metadata'][unit['id']]))
        own={}
        for row in rows:
            pairs=plan['rows'][row]['continuation_pairs']
            if pairs is None:continue
            ix=[i for i,x in enumerate(selected) if x['feature']==row and x['split']=='test']
            size=1 if pairs=='PER_ITEM' else 8
            for start in range(0,len(ix),size):
                batch=ix[start:start+size];units=[selected[i] for i in batch]
                local_pairs=plan['item_pairs'][units[0]['id']] if pairs=='PER_ITEM' else pairs
                scores=budget.call(reader+'_continuation',lambda:backend.score('continuation' if reader=='oracle' else 'nla',units,backend.take(acts[layer],batch),local_pairs))
                for x,value in zip(units,scores):own[x['id']]=value
        with (out/(reader+'.continuation.jsonl')).open('x') as stream:
            for k,value in own.items():
                donor=plan['donors'][k]
                require(donor in own,'same-shard donor continuation')
                for arm,score in [('own',value),('swap',own[donor])]:
                    stream.write(json.dumps({'id':k,'feature':selected[indices[k]]['feature'],'reader':reader,'arm':arm,'scores':score},allow_nan=False)+'\n')
    from native_nla512 import truncation_summary
    dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(line) for line in (out/'nla.native.jsonl').read_text().splitlines()]))
    dump(out / 'COUNTS.json', counts)
    dump(out / 'TIMING.json', {'completed_epoch': time.time(), 'deadline_epoch': budget.end, 'phase_max_seconds': budget.observed})
    seal(out, 'OUTPUT_SEAL.json', {'experiment': 'E57', 'slot': assignment['slot'], 'pod_id': assignment['pod_id'], 'input_seal_sha256': assignment['e57_input_seal_sha256'], 'source_seal_sha256': assignment['e57_source_seal_sha256']})
