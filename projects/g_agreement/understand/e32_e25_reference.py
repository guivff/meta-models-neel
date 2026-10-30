"""2026-10-25: E25 base-Qwen text likelihood, integrator-operated only.

No reader imports, adapters, activation inputs, hooks, generation or label joins.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time

MODEL = 'Qwen/Qwen3.6-27B'
REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def read(path):
    return json.loads(Path(path).read_text())


def verify_stage(stage, plan):
    seal = read(stage / 'INPUT_SEAL.json')
    if set(seal['files']) != {'items.jsonl', 'candidates.json'}:
        raise ValueError('stage must contain only frozen text and candidates')
    if set(p.name for p in stage.iterdir()) != {*seal['files'], 'INPUT_SEAL.json'}:
        raise ValueError('unexpected stage file (labels/activations forbidden)')
    if sha(stage / 'INPUT_SEAL.json') != plan['input_seal_sha256']:
        raise ValueError('input seal mismatch')
    for name, digest in seal['files'].items():
        if sha(stage / name) != digest:
            raise ValueError('staged file changed: ' + name)
    items = [json.loads(x) for x in (stage / 'items.jsonl').read_text().splitlines()]
    if [{'id': x['id'], 'feature': x['feature']} for x in items] != plan['items']:
        raise ValueError('item identity/order mismatch')
    if any(set(x) != {'id', 'feature', 'text'} for x in items):
        raise ValueError('unexpected item fields')
    candidates = read(stage / 'candidates.json')
    if set(candidates) != set(plan['rows']):
        raise ValueError('candidate row mismatch')
    if any(len(v) != 2 or any(len(p) != 2 or not all(isinstance(c,str) and c for c in p) for p in v) for v in candidates.values()):
        raise ValueError('require two literal W1 candidate pairs')
    return items, candidates


def encode_frame(tokenizer, text, candidate):
    prefix = text + '\n'
    encoded = tokenizer(prefix + candidate, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded['offset_mapping']
    if any(lo < len(prefix) < hi for lo, hi in offsets):
        raise ValueError('token crosses prefix/candidate boundary')
    positions = [i for i, (lo, hi) in enumerate(offsets) if lo >= len(prefix) and hi > lo]
    if not positions or positions[0] == 0 or positions != list(range(positions[0], len(offsets))):
        raise ValueError('invalid candidate suffix')
    return {'ids': encoded['input_ids'], 'candidate_start': positions[0], 'token_count': len(positions)}


def score_batch(model, frames, pad_id):
    """Mean causal log probability of candidate only; left padding never scored."""
    import torch
    width = max(len(x['ids']) for x in frames)
    keep = max(x['token_count'] for x in frames) + 1
    ids = torch.full((len(frames), width), pad_id, dtype=torch.long, device=model.device)
    mask = torch.zeros_like(ids)
    for row, frame in enumerate(frames):
        ids[row, -len(frame['ids']):] = torch.tensor(frame['ids'], device=model.device)
        mask[row, -len(frame['ids']):] = 1
    positions = (mask.cumsum(-1) - 1).clamp(min=0)
    with torch.inference_mode():
        logits = model(input_ids=ids, attention_mask=mask, position_ids=positions,
                       use_cache=False, logits_to_keep=keep).logits
        if logits.shape[1] != keep:
            raise ValueError('target must honor logits_to_keep')
        lp = logits.float().log_softmax(-1)
        result = []
        for row, frame in enumerate(frames):
            n = frame['token_count']
            # Final candidate token uses the penultimate logit; final logit is unused.
            selected = lp[row, keep-n-1:keep-1].gather(1, ids[row, -n:, None]).squeeze(1)
            value = float(selected.mean().cpu())
            if not math.isfinite(value):
                raise ValueError('nonfinite candidate score')
            result.append(value)
    return result


def forecast_gate(elapsed, remaining, first, provider_deadline, now):
    if not all(math.isfinite(x) and x >= 0 for x in (elapsed, remaining)):
        raise ValueError('invalid warmed timing')
    forecast = elapsed + remaining
    cap = min(1.5 * forecast + 360, 1800)
    deadline = min(first + cap, provider_deadline - 180)
    return {'forecast_s': forecast, 'science_cap_s': cap,
            'deadline_epoch': deadline, 'status': 'FIT' if now + remaining <= deadline else 'NO_FIT'}


def validate_assignment(a, plan, plan_path, now):
    if (a.get('issuer') != 'integrator' or a.get('experiment') != 'E25'
        or not a.get('pod_id') or a['pod_id'] != os.environ.get('RUNPOD_POD_ID')
        or a.get('plan_sha256') != sha(plan_path)
        or a.get('source_files') != plan['source_files']):
        raise ValueError('exact integrator assignment required')
    for flag in ('source_published', 'inputs_published', 'registration_published', 'external_hardstop_verified'):
        if a.get(flag) is not True:
            raise ValueError('missing ' + flag)
    choices = plan.get('clarifications',{})
    if (a.get('clarification_commit') != 'e4225a1e'
        or choices.get('clarification_commit') != 'e4225a1e'
        or choices.get('D_definition') != 'AUROC(s_A-s_B,value_is_A)'
        or choices.get('phrasing_aggregation') != 'mean_of_two_W1_pairs'
        or choices.get('integrator_acknowledged') is not True):
        raise ValueError('published D clarification e4225a1e and matching plan required')
    if a.get('previous_science_seconds') != 0 or a.get('setup_allowance_seconds') != 1500 or a.get('science_ceiling_seconds') != 1800:
        raise ValueError('wrong allowance or duplicate/retry allocation')
    created, deadline = a['provider_created_epoch'], a['deadline_epoch']
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (created,deadline,now)):
        raise ValueError('nonfinite assignment clock')
    if not created <= now < created + 1500 or deadline <= now + 180:
        raise ValueError('setup expired or no retrieval reserve')
    if deadline > created + 1500 + 1800 + 180:
        raise ValueError('provider deadline exceeds total allowance')


def run(args):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    plan_path, stage, out = Path(args.plan), Path(args.stage), Path(args.out)
    plan, a = read(plan_path), read(args.assignment)
    validate_assignment(a, plan, plan_path, time.time())
    def timeout(*_):
        raise TimeoutError('E25 hard deadline reached')
    signal.signal(signal.SIGALRM, timeout)
    setup_deadline = min(a['provider_created_epoch'] + 1500, a['deadline_epoch'] - 180)
    signal.setitimer(signal.ITIMER_REAL, max(.001, setup_deadline-time.time()))
    root = Path(__file__).resolve().parents[4]
    for name, digest in plan['source_files'].items():
        if sha(root / name) != digest:
            raise ValueError('source mismatch: ' + name)
    items, candidates = verify_stage(stage, plan)
    if not torch.cuda.is_available():
        raise ValueError('acquisition requires integrator-assigned CUDA, never local fallback')
    assets = read(args.assets)
    if a.get('assets_manifest_sha256') != sha(args.assets):
        raise ValueError('assignment must bind verified asset manifest')
    model_path = Path(assets['model_path'])
    if assets.get('model_id') != MODEL or assets.get('revision') != REVISION:
        raise ValueError('wrong base checkpoint')
    if assets.get('adapter') is not None or assets.get('injection') is not None:
        raise ValueError('adapters and injection forbidden')
    # The integrator provides hashes for every model/config/tokenizer file.
    files = assets['files']
    index = read(model_path / 'model.safetensors.index.json')
    required = set(index['weight_map'].values()) | {'model.safetensors.index.json','config.json','tokenizer.json','tokenizer_config.json'}
    if not required <= set(files) or any(Path(n).is_absolute() or '..' in Path(n).parts for n in files):
        raise ValueError('incomplete/unsafe verified asset manifest')
    for name, digest in files.items():
        if sha(model_path / name) != digest:
            raise ValueError('model asset changed: ' + name)
    if sha(model_path / 'tokenizer.json') != TOKENIZER_SHA:
        raise ValueError('wrong W1 tokenizer')
    if (model_path / 'adapter_config.json').exists():
        raise ValueError('adapter directory supplied')
    out.mkdir(parents=True, exist_ok=False)
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True,
                    dtype=torch.bfloat16, device_map='cuda').eval()
        if hasattr(model, 'peft_config'):
            raise ValueError('unexpected adapted model')
        frames = []
        for item in items:
            for phrasing, pair in enumerate(candidates[item['feature']]):
                for label, candidate in zip(('A','B'), pair):
                    frames.append({'id':item['id'], 'feature':item['feature'], 'phrasing':phrasing,
                                   'candidate':label, **encode_frame(tokenizer,item['text'],candidate)})
        if len(frames) != 8400:
            raise ValueError('require all 2100 items x2 phrasings x2 candidates')
        if time.time() >= setup_deadline:
            raise TimeoutError('setup expired')
        first = time.time()
        clock = Path(args.assignment).resolve().with_suffix('.science-clock.json')
        dump(clock, {'first_science_epoch':first,'assignment_sha256':sha(args.assignment)})
        deadline = min(first+1800, a['deadline_epoch']-180)
        def check():
            remaining = deadline-time.time()
            if remaining <= 0:
                raise TimeoutError('science expired')
            signal.setitimer(signal.ITIMER_REAL, remaining)
        check()
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        # Fixed longest frames form a conservative warm-up; all warm-up time is science.
        batch = plan['batch_size']
        warm = sorted(frames,key=lambda x:(-len(x['ids']),x['id'],x['phrasing'],x['candidate']))[:batch]
        score_batch(model,warm,pad); torch.cuda.synchronize()
        groups = {}
        for frame in frames:
            groups.setdefault((frame['feature'],frame['phrasing'],frame['candidate']),[]).append(frame)
        records, timings, pending = [], [], []
        for key, group in sorted(groups.items()):
            batches = [group[i:i+batch] for i in range(0,len(group),batch)]
            units = []
            for chunk in batches[:3]:
                check(); torch.cuda.synchronize(); start = time.monotonic()
                values = score_batch(model,chunk,pad); torch.cuda.synchronize()
                units.append(time.monotonic()-start)
                records.extend({k:f[k] for k in ('id','feature','phrasing','candidate','token_count')} | {'mean_logprob':v} for f,v in zip(chunk,values))
            timings.append({'feature':key[0],'phrasing':key[1],'candidate':key[2], 'unit_seconds':units,'remaining_batches':len(batches)-len(units)})
            pending.extend(batches[3:])
        now = time.time()
        remaining = sum(statistics.median(t['unit_seconds'])*t['remaining_batches'] for t in timings)
        forecast = forecast_gate(now-first,remaining,first,a['deadline_epoch'],now)
        dump(out/'FORECAST.json',forecast | {'timings':timings,'warmup_in_science':True})
        if forecast['status'] != 'FIT':
            raise ValueError('NO_FIT; preserve forecast, no scope cut or retry')
        deadline = forecast['deadline_epoch']
        for chunk in pending:
            check()
            values = score_batch(model,chunk,pad)
            records.extend({k:f[k] for k in ('id','feature','phrasing','candidate','token_count')} | {'mean_logprob':v} for f,v in zip(chunk,values))
        check()
        if len(records)!=8400 or len({(r['id'],r['phrasing'],r['candidate']) for r in records})!=8400:
            raise ValueError('incomplete acquisition')
        with (out/'scores.jsonl').open('x') as stream:
            for record in records:
                stream.write(json.dumps(record,sort_keys=True,allow_nan=False)+'\n')
        dump(out/'provenance.json',{'date':'2026-10-25','experiment':'E25','model_id':MODEL,'revision':REVISION,
             'adapter':None,'injection':None,'source_files':plan['source_files'],
             'assignment_sha256':sha(args.assignment),'assets_manifest_sha256':sha(args.assets),
             'input_seal_sha256':sha(stage/'INPUT_SEAL.json'),'first_science_epoch':first,
             'science_elapsed_seconds':time.time()-first,'setup_seconds':first-a['provider_created_epoch'],
             'labels_joined':False})
        dump(out/'SCORE_SEAL.json',{'schema_version':1,'complete':True,'plan_sha256':sha(plan_path),
             'files':{name:sha(out/name) for name in ('scores.jsonl','provenance.json','FORECAST.json')}})
    except Exception as error:
        if out.exists() and not (out/'FAILURE.json').exists():
            dump(out/'FAILURE.json',{'status':'INCOMPLETE','error_type':type(error).__name__,
                                    'retry_authorized':False,'score_seal_produced':False})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','stage','assignment','assets','out'):
        p.add_argument('--'+name,required=True)
    run(p.parse_args())
