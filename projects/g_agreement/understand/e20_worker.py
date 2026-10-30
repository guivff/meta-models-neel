"""E20 five-channel acquisition; parser frozen before this worker was authored."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import sys
import time

from projects.g_agreement.blindspot import protocol as P, run as W
from .e20_parser import positive

SEED = 20261025
ROWS = ('prose_paren', 'python_string', 'prose_sentiment_delayed', 'fact_once')
CAP, SETUP, BATCH = 7200, 2400, 8


def batches(items):
    # No left padding in the recurrent subject model. Equal-length base batches.
    groups = defaultdict(list)
    for x in items:
        groups[x['feature'], len(x['ids'])].append(x)
    return [v[s:s+BATCH] for _, v in sorted(groups.items()) for s in range(0, len(v), BATCH)]


def seed_for(tag, items):
    key = f'{SEED}:{tag}:' + ','.join(x['id'] for x in items)
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def auc(scores, labels):
    a = [s for s, y in zip(scores, labels) if y == 1]
    b = [s for s, y in zip(scores, labels) if y == 0]
    if not a or not b:
        raise ValueError('both states required')
    return sum((u > v) + .5 * (u == v) for u in a for v in b) / (len(a) * len(b))


def gate(items, records, labels):
    expected = {x['id'] for x in items if x['split'] == 'dev' and x['distance'] == 2}
    if set(records) != expected or set(labels) != expected or len(expected) != 320:
        raise ValueError('exact dev/d=2 gate population required')
    result = {}
    for row in ROWS:
        ids = [x['id'] for x in items if x['id'] in expected and x['feature'] == row]
        value = auc([records[i]['positive_count']/8 for i in ids], [labels[i] for i in ids])
        result[row] = {'auroc': value, 'n': len(ids), 'status': 'EVALUABLE' if value >= .8 else 'NOT EVALUABLE'}
    return result


def allocation(elapsed, remaining, used):
    forecast = used + elapsed + remaining
    cap = min(1.5 * forecast + 360, CAP)
    return {'forecast_total_s': forecast, 'allocation_total_s': cap,
            'remaining_estimate_s': remaining, 'previous_science_s': used,
            'status': 'FIT' if math.isfinite(forecast) and 0 < forecast <= cap else 'NO_FIT'}


def consequence_layout(carrier, bullet, items):
    seqs, starts, lengths, owner = [], [], [], []
    for j, x in enumerate(items):
        head = carrier + bullet + x['intervening_ids']
        for candidate in x['candidates']:
            if not candidate:
                raise ValueError('empty consequence')
            seqs.append(head + candidate)
            starts.append(len(head)); lengths.append(len(candidate)); owner.append(j)
    return seqs, starts, lengths, owner


class Engine:
    def __init__(self, assets, phrasings):
        self.ol = W._load_oracle(assets)
        self.phrasings = phrasings

    def base(self, items):
        import torch
        if len({len(x['ids']) for x in items}) != 1:
            raise ValueError('generation cannot pad source prefixes')
        torch.manual_seed(seed_for('base', items)); torch.cuda.manual_seed_all(seed_for('base', items))
        ids = torch.tensor([x['ids'] for x in items for _ in range(8)], device=self.ol.device)
        with self.ol.base(), torch.inference_mode():
            out = self.ol.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                do_sample=True, temperature=1., top_p=1., top_k=0, max_new_tokens=16,
                pad_token_id=self.ol.tok.pad_token_id or self.ol.tok.eos_token_id)
        generated = out[:, ids.shape[1]:].tolist()
        texts = self.ol.tok.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        return [{'id':x['id'], 'feature':x['feature'], 'texts':texts[8*j:8*j+8],
                 'generated_ids':generated[8*j:8*j+8],
                 'positive_count':sum(positive(x['feature'], t) for t in texts[8*j:8*j+8])}
                for j, x in enumerate(items)]

    def capture(self, items):
        from mats.capture import capture
        with self.ol.base():
            return capture(self.ol.model, [x['ids'] for x in items], [44], [[-1] for _ in items],
                           batch_size=BATCH, pad_id=self.ol.tok.pad_token_id or 0)[44][:, 0]

    def consequence(self, items, h):
        import torch
        ol = self.ol
        carrier, slot = ol.carrier(44)
        seqs, starts, lengths, owner = consequence_layout(carrier, ol.tok.encode('- ', add_special_tokens=False), items)
        width = max(map(len, seqs))
        ids = torch.full((len(seqs), width), ol.tok.pad_token_id or 0, dtype=torch.long, device=ol.device)
        mask = torch.zeros_like(ids)
        for j, seq in enumerate(seqs):
            ids[j, :len(seq)] = torch.tensor(seq, device=ol.device); mask[j, :len(seq)] = 1
        positions = sorted({start-1+k for start, n in zip(starts, lengths) for k in range(n)})
        keep = torch.tensor(positions, device=ol.device)
        with torch.inference_mode():
            embeds = ol._embed(ids, slot, h[owner])
            logits = ol.model(inputs_embeds=embeds, attention_mask=mask, logits_to_keep=keep, use_cache=False).logits
            values = []
            for j, (start, n) in enumerate(zip(starts, lengths)):
                p = torch.arange(start-1, start+n-1, device=ol.device)
                lp = torch.log_softmax(logits[j, torch.searchsorted(keep, p)].float(), -1)
                values.append(float(lp.gather(1, ids[j, start:start+n, None]).sum()))
        return [values[j]-values[j+1] for j in range(0, len(values), 2)]

    def lens(self, items, acts):
        import torch
        from mats.readers.olens import Sampling
        h = torch.stack([acts[x['id']] for x in items])
        # Unchanged native carrier; greedy output first, then three native samples.
        greedy = self.ol.verbalize(h, 44, k=1, sampling=Sampling(temperature=0, max_new_tokens=16), batch=BATCH)
        torch.manual_seed(seed_for('lens', items)); torch.cuda.manual_seed_all(seed_for('lens', items))
        sampled = self.ol.verbalize(h, 44, k=3,
            sampling=Sampling(temperature=1., top_p=.95, top_k=64, max_new_tokens=16), batch=3*BATCH)
        scores = {}
        for arm, key in [('true', 'id'), ('random_donor', 'random_donor_id'), ('opposite_donor', 'opposite_donor_id')]:
            donor_h = torch.stack([acts[x[key]] for x in items])
            scores[arm] = self.consequence(items, donor_h)
        asked = self.ol.paired_logodds_templates(h, 44, self.phrasings[items[0]['feature']])
        if not torch.isfinite(asked).all():
            raise ValueError('nonfinite asked scores')
        result = []
        for j, x in enumerate(items):
            bullets = greedy[j] + sampled[j]
            result.append({'id':x['id'], 'feature':x['feature'], 'bullets':bullets,
                'positive_count':sum(positive(x['feature'], t) for t in bullets),
                'consequence':{arm:values[j] for arm, values in scores.items()},
                'donors':{'random_donor':x['random_donor_id'], 'opposite_donor':x['opposite_donor_id']},
                'asked':asked[:, j].tolist()})
        if any(not math.isfinite(s) for x in result for s in x['consequence'].values()):
            raise ValueError('nonfinite consequence scores')
        return result


def validate_assignment(q, plan, plan_hash, prefix, pod):
    if prefix != '/weights/venv-kernels':
        raise ValueError('worker requires /weights/venv-kernels without fallback')
    if (q.get('issuer') != 'integrator' or q.get('experiment') != 'E20' or q.get('pod_id') != pod or not pod
        or q.get('plan_sha256') != plan_hash or q.get('external_hardstop_verified') is not True
        or q.get('items_published') is not True or q.get('parser_freeze_published') is not True):
        raise ValueError('bound integrator assignment required')
    for key in ('previous_science_seconds', 'previous_setup_seconds'):
        if not math.isfinite(float(q[key])) or float(q[key]) != float(plan[key]):
            raise ValueError('prerequisite costs must carry forward exactly')


def run(a):
    import numpy as np
    import torch
    plan = json.loads(a.plan.read_text()); q = json.loads(a.assignment.read_text())
    validate_assignment(q, plan, P.sha(a.plan), sys.prefix, os.environ.get('RUNPOD_POD_ID'))
    P.verify(a.bank, 'INPUT_SEAL.json'); W._labels_absent(a.bank)
    if P.sha(a.bank/'INPUT_SEAL.json') != plan['input_seal_sha256'] or P.sha(a.dev_labels) != plan['dev_labels_sha256']:
        raise ValueError('input/dev-gate binding failed')
    for name, h in plan['source_files'].items():
        if P.sha(P.ROOT/name) != h:
            raise ValueError('source mismatch: '+name)
    items = P.rows(a.bank/'items.input.jsonl'); lookup = {x['id']:x for x in items}
    if len(items) != 5760 or len(lookup) != 5760:
        raise ValueError('full frozen E20 bank required')
    label_rows = P.rows(a.dev_labels)
    if any(x['split'] != 'dev' or x['distance'] != 2 for x in label_rows):
        raise ValueError('only dev/d=2 gate labels may be staged')
    labels = {x['id']:x['label'] for x in label_rows}
    if len(label_rows) != len(labels) or len(labels) != 320:
        raise ValueError('dev labels incomplete or duplicated')
    used = float(plan['previous_science_seconds']); setup_used = float(plan['previous_setup_seconds'])
    created = float(q['provider_created_epoch']); absolute = float(q['deadline_epoch'])-180
    if used >= CAP or setup_used >= SETUP or not created <= time.time() < absolute:
        raise ValueError('invalid budget or provider clock')
    end = min(created+SETUP-setup_used, absolute); first = None
    a.out.mkdir(parents=True, exist_ok=False)
    def expired(*_):
        raise TimeoutError('E20 shared science/setup/provider deadline')
    def check():
        if time.time() >= end: expired()
        signal.setitimer(signal.ITIMER_REAL, max(.001, end-time.time()))
    old = signal.signal(signal.SIGALRM, expired)
    def call(fn, *args):
        check(); value = fn(*args); torch.cuda.synchronize(); check(); return value
    def append(name, rows):
        with (a.out/name).open('a') as f:
            for row in rows: f.write(json.dumps(row)+'\n')
            f.flush()
    try:
        check(); assets = W._assets(a.assets, names=('model','olens'))
        engine = Engine(assets, json.loads((a.bank/'phrasings.json').read_text()))
        if P.sha(Path(assets['model'])/'tokenizer.json') != plan['tokenizer_sha256']:
            raise ValueError('pinned tokenizer mismatch')
        dev = [x for x in items if x['split']=='dev' and x['distance']==2]
        db = batches(dev)
        call(engine.base, db[0])  # unretained setup warmup, no lens or source capture
        first = time.time(); end = min(first+CAP-used, absolute)
        P.dump(a.out/'CLOCK.json', {'first_science_epoch':first, 'previous_science_seconds':used})
        base = {}; times = []
        for j, batch in enumerate(db):
            start = time.perf_counter(); records = call(engine.base, batch); times.append(time.perf_counter()-start)
            base.update({x['id']:x for x in records}); append('base.partial.jsonl', records)
            if j == 2:
                # A prerequisite-only bound; full five-channel forecast follows gate.
                est = allocation(time.time()-first, statistics.median(times)*(len(db)-3), used)
                P.dump(a.out/'DEV_FORECAST.json', est)
                if est['status'] != 'FIT': raise TimeoutError('dev prerequisite NO_FIT')
        validity = gate(items, base, labels); P.dump(a.out/'VALIDITY.json', validity)
        P.jsonl(a.out/'base.dev_gate.jsonl', [base[x['id']] for x in dev])
        P.dump(a.out/'VALIDITY_SEAL.json', {'status':'DEV_GATE_BEFORE_ANY_LENS_SCORING',
            'files':{n:P.sha(a.out/n) for n in ['VALIDITY.json','base.dev_gate.jsonl']}})
        allowed = {r for r, v in validity.items() if v['status']=='EVALUABLE'}
        all_batches = batches(items)
        base_batches = batches([x for x in items if x['id'] not in base])
        lens_batches = batches([x for x in items if x['feature'] in allowed])
        timing = []; remaining = 0.
        for row in ROWS:
            representative = max((b for b in all_batches if b[0]['feature']==row), key=lambda b:(len(b),len(b[0]['ids'])))
            for channel, fn, units in [('base',engine.base,base_batches), ('capture',engine.capture,all_batches)]:
                call(fn, representative)
                ts=[]
                for _ in range(3):
                    start=time.perf_counter(); call(fn,representative); ts.append(time.perf_counter()-start)
                count=sum(b[0]['feature']==row for b in units); remaining+=statistics.median(ts)*count
                timing.append({'row':row,'channel':channel,'seconds':ts,'units':count})
            if row in allowed:
                ids=sorted({x[k] for x in representative for k in ('id','random_donor_id','opposite_donor_id')})
                hs=call(engine.capture,[lookup[i] for i in ids]); warm_acts=dict(zip(ids,hs))
                call(engine.lens,representative,warm_acts); ts=[]
                for _ in range(3):
                    start=time.perf_counter();call(engine.lens,representative,warm_acts);ts.append(time.perf_counter()-start)
                count=sum(b[0]['feature']==row for b in lens_batches);remaining+=statistics.median(ts)*count
                timing.append({'row':row,'channel':'lens_all_three_channels','seconds':ts,'units':count})
        forecast=allocation(time.time()-first,remaining,used)
        forecast.update({'timings':timing,'timing_outputs_retained':False,'full_scope':True})
        P.dump(a.out/'FORECAST.json',forecast)
        if forecast['status']!='FIT':raise TimeoutError('full E20 NO_FIT; no scope cuts/retry')
        end=min(end,first+forecast['allocation_total_s']-used)
        if time.time()+remaining>end:raise TimeoutError('provider allowance cannot fit full E20')
        acts={}
        for batch in all_batches:
            h=call(engine.capture,batch)
            if h.ndim!=2 or len(h)!=len(batch) or not torch.isfinite(h).all():raise ValueError('invalid source capture')
            acts.update({x['id']:h[j] for j,x in enumerate(batch)})
        np.save(a.out/'acts44.npy',torch.stack([acts[x['id']] for x in items]).numpy(),allow_pickle=False)
        P.dump(a.out/'items.order.json',[x['id'] for x in items])
        P.dump(a.out/'CAPTURE_SEAL.json',{'status':'E20_BLOCK44_SOURCE_CAPTURE_COMPLETE','files':{n:P.sha(a.out/n) for n in ['acts44.npy','items.order.json']}})
        for batch in base_batches:
            records=call(engine.base,batch);base.update({x['id']:x for x in records});append('base.partial.jsonl',records)
        lens={}
        for batch in lens_batches:
            records=call(engine.lens,batch,acts);lens.update({x['id']:x for x in records});append('lens.partial.jsonl',records)
        if set(base)!=set(lookup) or set(lens)!={x['id'] for x in items if x['feature'] in allowed}:
            raise ValueError('incomplete production grid')
        P.jsonl(a.out/'base.jsonl',[base[x['id']] for x in items]);P.jsonl(a.out/'lens.jsonl',[lens[x['id']] for x in items if x['id'] in lens])
        P.dump(a.out/'PROVENANCE.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':plan['input_seal_sha256'],
            'parser_sha256':plan['parser_sha256'],'parser_freeze_sha256':plan['parser_freeze_sha256'],
            'assignment_sha256':P.sha(a.assignment),'dev_labels_sha256':P.sha(a.dev_labels),'source_files':plan['source_files']})
        check()
        names=['base.jsonl','lens.jsonl','PROVENANCE.json','FORECAST.json','CLOCK.json','VALIDITY.json','VALIDITY_SEAL.json','base.dev_gate.jsonl','CAPTURE_SEAL.json']
        P.dump(a.out/'SCORE_SEAL.json',{'status':'E20_COMPLETE_BEFORE_TEST_LABEL_JOIN','files':{n:P.sha(a.out/n) for n in names}})
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','reason':str(exc),'retry_authorized':False});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        P.dump(a.out/'RECEIPT.json',{'science_seconds':0 if first is None else time.time()-first,
            'previous_science_seconds':used,'setup_seconds':(first or time.time())-created,
            'previous_setup_seconds':setup_used,'carry_forward_required':True})


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('bank','plan','assignment','assets','dev-labels','out'):
        p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
