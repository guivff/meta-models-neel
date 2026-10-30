"""E28 full-grid training worker. Run from repository root; all outputs go to cache/."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import signal
import shutil
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C
import training_environment as E
sys.path.insert(0, str(C.ROOT))


def check_source(a):
    expected = C.read(C.HERE / 'SOURCE_MANIFEST.json')['files']
    for name, digest in expected.items():
        if C.sha(C.ROOT / name) != digest:
            raise ValueError('source hash mismatch: ' + name)
    if a['source_manifest_sha256'] != C.sha(C.HERE / 'SOURCE_MANIFEST.json'):
        raise ValueError('assignment source seal mismatch')


def check_time(a, science_deadline=None):
    deadline = min(a['deadline_epoch'] - 180, science_deadline or math.inf)
    if time.time() >= deadline:
        raise TimeoutError('E28 deadline reached; retain partials, no restart')


def arm_deadline(epoch):
    """Unix process alarm complements the Integrator's provider hardstop."""
    def timeout(_signum, _frame):
        raise TimeoutError('E28 nonresetting wall clock expired')
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, max(.001, epoch - time.time()))


def attach_lowrank(model, mapping):
    """Rank-eight LoRA on the coordinator's exact original whole-module targets."""
    import torch
    from torch import nn
    if mapping.get('status') != 'COORDINATOR_APPROVED' or mapping.get('fresh_rank') != 8:
        raise ValueError('approved rank-eight target map required')
    targets = [{'module': name, 'slices': [[0, module.out_features]]}
               for name, module in model.named_modules()
               if name.split('.')[-1] in mapping['target_modules'] and isinstance(module, nn.Linear)]
    layers = {int(m.group(1)) for x in targets if (m := re.search(r'\.layers\.(\d+)\.', x['module']))}
    if layers != set(range(64)):
        raise ValueError('approved full-module map must cover all 64 layers')
    if {x['module'].split('.')[-1] for x in targets} != set(mapping['target_modules']):
        raise ValueError('a pinned adapter target is absent in the model')
    for p in model.parameters():
        p.requires_grad_(False)

    class SliceLoRA(nn.Module):
        def __init__(self, base, spec):
            super().__init__()
            self.base = base
            self.slices = [tuple(x) for x in spec['slices']]
            occupied = set()
            for lo, hi in self.slices:
                if not 0 <= lo < hi <= base.out_features or occupied.intersection(range(lo, hi)):
                    raise ValueError('invalid/overlapping approved output slices')
                occupied.update(range(lo, hi))
            self.A = nn.ParameterList([nn.Parameter(torch.empty(8, base.in_features, device=base.weight.device)) for _ in self.slices])
            self.B = nn.ParameterList([nn.Parameter(torch.zeros(hi-lo, 8, device=base.weight.device)) for lo, hi in self.slices])
            for p in self.A:
                nn.init.kaiming_uniform_(p, a=math.sqrt(5))
            self.scale = float(mapping['fresh_lora_alpha']) / 8

        def forward(self, x):
            y = self.base(x)
            delta = torch.zeros_like(y)
            for (lo, hi), a, b in zip(self.slices, self.A, self.B):
                delta[..., lo:hi] = (torch.nn.functional.linear(torch.nn.functional.linear(x.float(), a), b) * self.scale).to(y.dtype)
            return y + delta

    mounted = []
    for spec in targets:
        parent_name, leaf = spec['module'].rsplit('.', 1)
        parent = model.get_submodule(parent_name)
        original = getattr(parent, leaf)
        if not isinstance(original, nn.Linear):
            raise ValueError('approved target is not a Linear projection')
        wrapped = SliceLoRA(original, spec)
        setattr(parent, leaf, wrapped)
        mounted.append((parent, leaf, original, wrapped))
    trainable = [p for _, _, _, w in mounted for p in list(w.A) + list(w.B)]
    actual = [p for p in model.parameters() if p.requires_grad]
    if {id(p) for p in actual} != {id(p) for p in trainable}:
        raise ValueError('base/lens weights must stay frozen')
    return mounted, trainable


def detach_lowrank(mounted):
    for parent, name, original, _ in mounted:
        setattr(parent, name, original)


def load_base(assets, arm):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    tok = AutoTokenizer.from_pretrained(assets['model'], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(assets['model'], dtype=torch.bfloat16,
              device_map='cuda', local_files_only=True)
    if arm in ('L', 'S'):
        model = PeftModel.from_pretrained(model, assets['olens'], local_files_only=True).merge_and_unload(safe_merge=True)
    for p in model.parameters():
        p.requires_grad_(False)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    return model, tok


def make_reader(model, tok):
    import common
    from mats.readers.olens import OracleLens
    return OracleLens(model=model, tok=tok, device=str(next(model.parameters()).device))


def train_step(reader, batch, labels, acts, spec, optimizer, diagnostics=False):
    import torch
    device = next(reader.model.parameters()).device
    head, slot = reader.carrier(44)
    targets = [reader.tok.encode(spec['olens'][b['phrasing']][0 if b['y'] else 1], add_special_tokens=False) for b in batch]
    if any(not t for t in targets):
        raise ValueError('empty frozen target tokens')
    n = len(head) + max(map(len, targets))
    ids = torch.full((len(batch), n), reader.tok.pad_token_id or 0, dtype=torch.long, device=device)
    attention = torch.zeros_like(ids)
    target = torch.full_like(ids, -100)
    for i, tail in enumerate(targets):
        seq = head + tail
        ids[i, :len(seq)] = torch.tensor(seq, device=device)
        attention[i, :len(seq)] = 1
        target[i, len(head):len(seq)] = torch.tensor(tail, device=device)
    x = torch.as_tensor(acts[[labels[b['id']] for b in batch]], device=device)
    reader.model.train()
    optimizer.zero_grad(set_to_none=True)
    embed = reader._embed(ids, slot, x)
    loss = reader.model(inputs_embeds=embed, attention_mask=attention, labels=target, use_cache=False).loss
    if not torch.isfinite(loss):
        raise ValueError('nonfinite loss')
    loss.backward()
    parameters = list(reader.model.parameters())
    trainable = [p for p in parameters if p.requires_grad]
    gradients = [p.grad for p in trainable]
    if not gradients or any(g is None for g in gradients):
        raise ValueError('fresh LoRA backward did not reach every trainable matrix')
    finite = bool(torch.isfinite(torch.stack([g.detach().norm() for g in gradients])).all())
    frozen_clean = all(p.grad is None for p in parameters if not p.requires_grad)
    if not finite or not frozen_clean:
        raise ValueError('nonfinite LoRA gradients or a gradient on frozen weights')
    optimizer.step()
    if device.type == 'cuda':
        torch.cuda.synchronize(device)
    value = float(loss.detach())
    return {'loss': value, 'finite_loss': True, 'finite_gradients': finite,
            'frozen_parameter_grads_none': frozen_clean} if diagnostics else value


def score(reader, test, acts, spec, row):
    import torch
    indices = [i for i, r in enumerate(test) if r['feature'] == row]
    reader.model.eval()
    a = torch.as_tensor(acts[indices], device=reader.device)
    values = reader.paired_logodds_templates(a, 44, spec['olens'])
    if tuple(values.shape) != (2, 84) or not torch.isfinite(values).all():
        raise ValueError('complete finite asked grid required')
    return [{'id': test[i]['id'], 'scores': values[:, j].tolist()} for j, i in enumerate(indices)]


def free(reader, test, acts, row, force_cap=False, deadline_check=lambda: None):
    import torch
    indices = [i for i, r in enumerate(test) if r['feature'] == row]
    reader.model.eval()
    a = torch.as_tensor(acts[indices], device=reader.device)
    head, slot = reader.carrier(44)
    values = []
    with torch.no_grad():
        for s in range(0, len(indices), 8):
            deadline_check()
            ids = torch.tensor([head] * min(8, len(indices)-s), device=reader.device)
            e = reader._embed(ids, slot, a[s:s+8])
            generated = reader.model.generate(inputs_embeds=e, attention_mask=torch.ones_like(ids),
                do_sample=False, max_new_tokens=128, min_new_tokens=128 if force_cap else 0,
                use_cache=True, pad_token_id=reader.tok.pad_token_id or reader.tok.eos_token_id)
            values.extend(reader.tok.batch_decode(generated, skip_special_tokens=True))
            deadline_check()
    return [{'id': test[i]['id'], 'raw': values[j]} for j, i in enumerate(indices)]


def optimizer_for(parameters):
    import torch
    return torch.optim.AdamW(parameters, lr=1e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0)


def runtime_inputs(a):
    import numpy as np
    from projects.g_agreement.blindspot.run import _assets
    assignment = C.assignment(C.read(a.assignment))
    check_source(assignment)
    C.worker_input(a.input)
    if C.sha(a.input / 'INPUT_SEAL.json') != assignment['input_seal_sha256']:
        raise ValueError('assigned input seal mismatch')
    if C.sha(a.mapping) != assignment['target_mapping_sha256']:
        raise ValueError('unapproved mapping bytes')
    mapping = C.read(a.mapping)
    if C.sha(a.assets) != assignment['assets_sha256']:
        raise ValueError('assigned asset manifest mismatch')
    assets = _assets(a.assets, names=('model', 'olens'))
    if C.sha(Path(assets['olens']) / 'adapter_config.json') != mapping['source_file_sha256']:
        raise ValueError('original adapter configuration differs from the frozen source')
    dev, test = C.rows(a.input / 'dev.jsonl'), C.rows(a.input / 'test.jsonl')
    if any(set(x) != {'id', 'feature'} for x in test):
        raise ValueError('test labels must never reach GPU worker')
    devacts = np.load(a.input / 'dev.acts44.npy', allow_pickle=False)
    testacts = np.load(a.input / 'test.acts44.npy', allow_pickle=False)
    return assignment, mapping, assets, dev, test, devacts, testacts, C.read(a.input / 'templates.json')


PARITY_ROWS = ('prose_sentiment', 'prose_paren', 'python_string')


class ParityFailed(RuntimeError):
    pass


def parity_inputs(path, assignment):
    import numpy as np
    required = {'items.jsonl', 'acts44.npy', 'labels.json', 'templates.json', 'REFERENCE.json'}
    if {p.name for p in path.iterdir()} != required | {'INPUT_SEAL.json'}:
        raise ValueError('parity payload must contain exactly its sealed authorized files')
    seal = C.verify(path)
    if set(seal['files']) != required or C.sha(path / 'INPUT_SEAL.json') != assignment['parity_input_seal_sha256']:
        raise ValueError('parity input seal mismatch')
    if assignment['parity_input_seal_sha256'] != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']:
        raise ValueError('parity input differs from reviewed preparation')
    reference = C.read(path / 'REFERENCE.json')
    if (reference.get('schema') != 'E28_PRETRAIN_PARITY_v1' or reference.get('status') != 'FROZEN'
            or reference.get('rows') != list(PARITY_ROWS) or reference.get('max_abs_auroc_delta') != .03
            or reference.get('original_e28_input_seal_sha256') != assignment['input_seal_sha256']):
        raise ValueError('frozen three-row parity reference required')
    items, labels, templates = C.rows(path / 'items.jsonl'), C.read(path / 'labels.json'), C.read(path / 'templates.json')
    if (len(items) != 252 or len({r['id'] for r in items}) != 252
            or any(set(r) != {'id', 'feature'} for r in items)
            or set(labels) != {r['id'] for r in items} or set(templates) != set(PARITY_ROWS)
            or any(type(v) is not int or v not in (0, 1) for v in labels.values())):
        raise ValueError('only the authorized 252 parity labels may be opened')
    for row in PARITY_ROWS:
        group = [r for r in items if r['feature'] == row]
        if len(group) != 84 or sum(labels[r['id']] for r in group) != 42:
            raise ValueError('complete balanced parity rows required')
    acts = np.load(path / 'acts44.npy', allow_pickle=False)
    if acts.shape != (252, 5120) or not np.isfinite(acts).all():
        raise ValueError('complete finite parity activations required')
    return items, labels, templates, acts, reference


def parity_gate(reader, inputs, source, out, assignment, environment_sha256, deadline_check=lambda: None):
    import numpy as np
    items, labels, templates, acts, reference = inputs
    if any(p.requires_grad for p in reader.model.parameters()):
        raise ValueError('parity requires the untrained frozen merged RL lens')
    records, cells = [], {}
    for row in PARITY_ROWS:
        deadline_check()
        values = score(reader, items, acts, templates[row], row)
        for record in values:
            record.update(feature=row, score=float(np.mean(record['scores'])))
        positives = np.array([r['score'] for r in values if labels[r['id']] == 1])
        negatives = np.array([r['score'] for r in values if labels[r['id']] == 0])
        difference = positives[:, None] - negatives[None, :]
        observed = float(np.mean((difference > 0) + .5 * (difference == 0)))
        ref = reference['reference_auc'][row]
        cells[row] = {'n': 84, 'observed': observed, 'reference': ref,
                      'absolute_delta': abs(observed-ref), 'threshold': .03}
        records.extend(values)
        deadline_check()
    C.jsonl(out / 'PARITY_SCORES.jsonl', records)
    shutil.copyfile(source / 'REFERENCE.json', out / 'PARITY_REFERENCE.json')
    result = {'schema': 'E28_PRETRAIN_PARITY_RESULT_v1',
        'status': 'PASS' if all(x['absolute_delta'] <= .03 for x in cells.values()) else 'FAIL',
        'rows': cells, 'optimizer_steps_before_gate': 0,
        'environment_manifest_sha256': environment_sha256,
        'parity_input_seal_sha256': assignment['parity_input_seal_sha256'],
        'raw_scores_sha256': C.sha(out / 'PARITY_SCORES.jsonl'),
        'reference_sha256': C.sha(out / 'PARITY_REFERENCE.json'), 'completed_epoch': time.time()}
    C.dump(out / 'PARITY_RESULT.json', result)
    if result['status'] != 'PASS':
        raise ParityFailed('pre-training W1 parity failed; no optimizer steps or retry')
    return result


def run(a):
    import torch
    assignment = C.assignment(C.read(a.assignment))
    out = C.cache_output(a.out)
    science_started, environment_ready = None, False
    C.dump(out / 'assignment.json', assignment)
    status = 'NOT_RUN_ENVIRONMENT'
    try:
        arm_deadline(min(assignment['provider_created_epoch'] + 2400, assignment['deadline_epoch'] - 180))
        E.verify_manifest(a.environment_manifest, assignment['training_environment_sha256'])
        shutil.copyfile(a.environment_manifest, out / 'TRAINING_ENVIRONMENT.json')
        assignment, mapping, assets, dev, test, devacts, testacts, specs = runtime_inputs(a)
        gate_inputs = parity_inputs(a.parity_inputs, assignment)
        torch.manual_seed(C.SEED)
        if time.time() - assignment['provider_created_epoch'] > 2400:
            raise TimeoutError('setup cap exceeded')
        devindex = {r['id']: i for i, r in enumerate(dev)}
        # The only authorized test labels are the separate 252-item parity gate.
        # It runs on untrained merged RL before any optimizer, including pilots.
        timings = {}
        for family in ('L', 'B'):
            check_time(assignment, science_started + 10800 if science_started is not None else None)
            t = time.time()
            model, tok = load_base(assets, family)
            load_s = time.time() - t
            reader = make_reader(model, tok)
            if family == 'L':
                science_started = time.time()
                if science_started - assignment['provider_created_epoch'] > 2400:
                    raise TimeoutError('setup including first model load exceeded 2400s')
                arm_deadline(min(science_started + 10800, assignment['deadline_epoch'] - 180, E.READINESS_DEADLINE))
                parity_gate(reader, gate_inputs, a.parity_inputs, out, assignment,
                            assignment['training_environment_sha256'],
                            deadline_check=lambda: check_time(assignment, min(science_started+10800, E.READINESS_DEADLINE)))
                del gate_inputs
            warm_row = max(C.ROWS, key=lambda row: max(len(tok.encode(c, add_special_tokens=False))
                           for pair in specs[row]['olens'] for c in pair))
            mounted, parameters = attach_lowrank(model, mapping)
            reader = make_reader(model, tok)
            schedule = C.training_schedule(dev, warm_row, family)
            opt = optimizer_for(parameters)
            check_time(assignment, science_started + 10800)
            diagnostics = train_step(reader, schedule[0], devindex, devacts, specs[warm_row], opt, diagnostics=True)
            if not environment_ready:
                result = E.runtime_ready(diagnostics, reader.device, time.time(),
                    assignment['training_environment_sha256'], C.sha(out / 'PARITY_RESULT.json'))
                C.dump(out / 'ENVIRONMENT_RUNTIME_RESULT.json', result)
                environment_ready = True
                status = 'FAILED'
                arm_deadline(min(science_started + 10800, assignment['deadline_epoch'] - 180))
            t = time.time()
            for b in schedule[1:5]:
                check_time(assignment, science_started + 10800)
                train_step(reader, b, devindex, devacts, specs[warm_row], opt)
            step_s = (time.time() - t) / 4
            # Full 84-item dev row is used as the warmed inference timing surrogate.
            t = time.time()
            score(reader, dev, devacts, specs[warm_row], warm_row)
            score_s = time.time() - t
            t = time.time()
            free(reader, dev, devacts, warm_row, force_cap=True,
                 deadline_check=lambda: check_time(assignment, science_started + 10800))
            free_s = time.time() - t
            timings[family] = {'load_s': load_s, 'train_step_s': step_s, 'asked_84_s': score_s,
                               'free_84_s': free_s, 'warm_row_longest_target': warm_row}
            del reader, opt, parameters, mounted, model
            gc.collect()
            torch.cuda.empty_cache()
        remaining = sum(400 * timings['B' if arm == 'B' else 'L']['train_step_s']
                        + 6 * timings['B' if arm == 'B' else 'L']['asked_84_s']
                        + timings['B' if arm == 'B' else 'L']['free_84_s'] for _, arm in assignment['runs'])
        remaining += sum(x['load_s'] for x in timings.values())
        forecast = {'status': 'WARMED_FORECAST', 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
            'slot': assignment['slot'], 'pod_count': assignment['pod_count'],
            'allocated_gpu_seconds': assignment['allocated_gpu_seconds'],
            'previous_gpu_seconds': assignment['previous_gpu_seconds'],
            'elapsed_provider_seconds': time.time() - assignment['provider_created_epoch'],
            'setup_elapsed_seconds': science_started - assignment['provider_created_epoch'],
            'science_started_epoch': science_started,
            'elapsed_science_seconds': time.time() - science_started,
            'forecast_remaining_seconds': remaining, 'timings': timings,
            'input_seal_sha256': assignment['input_seal_sha256'], 'assignment_sha256': C.sha(a.assignment)}
        C.dump(out / 'FORECAST.json', forecast)
        # Integrator runs CPU admit after collecting every pod's forecast and copies it here.
        while not a.admission.exists():
            check_time(assignment, science_started + 10800)
            time.sleep(2)
        admission = C.read(a.admission)
        if admission['status'] != 'ADMIT_FULL_GRID' or admission['plan_sha256'] != C.sha(C.HERE / 'PLAN.json'):
            status = 'NO_FIT_STOP'
            raise SystemExit(2)
        mine = [x for x in admission['pods'] if x['slot'] == assignment['slot']]
        if len(mine) != 1 or mine[0]['forecast_sha256'] != C.sha(out / 'FORECAST.json'):
            raise ValueError('admission not bound to this warmed forecast')
        if (len(admission['pods']) != assignment['pod_count']
                or admission.get('previous_gpu_seconds') != assignment['previous_gpu_seconds']
                or admission.get('total_experiment_reserved_gpu_seconds') !=
                    admission['total_allocated_gpu_seconds'] + assignment['previous_gpu_seconds']
                or admission['total_experiment_reserved_gpu_seconds'] > C.CAP):
            raise ValueError('global admission coverage/cap mismatch')
        science_deadline = science_started + mine[0]['science_seconds']
        if science_deadline > assignment['deadline_epoch'] - 180:
            raise TimeoutError('admission wait consumed forecast reserve')
        if not C.full_scope_still_fits(remaining, science_deadline, assignment['deadline_epoch'], time.time()):
            status = 'NO_FIT_STOP'
            raise SystemExit(2)
        arm_deadline(min(science_deadline, assignment['deadline_epoch'] - 180))
        for family in ('L', 'B'):
            check_time(assignment, science_deadline)
            model, tok = load_base(assets, family)
            for row, arm in assignment['runs']:
                if ('B' if arm == 'B' else 'L') != family:
                    continue
                torch.manual_seed(C.SEED)
                mounted, parameters = attach_lowrank(model, mapping)
                opt = optimizer_for(parameters)
                reader = make_reader(model, tok)
                schedule = C.training_schedule(dev, row, arm)
                runout = out / (row + '__' + arm)
                runout.mkdir()
                C.dump(runout / 'SCHEDULE.json', schedule)
                for step in range(401):
                    check_time(assignment, science_deadline)
                    if step in C.CHECKPOINTS:
                        records = score(reader, test, testacts, specs[row], row)
                        C.jsonl(runout / ('asked.' + str(step) + '.jsonl'), records)
                        C.seal(runout, 'CHECKPOINT_' + str(step) + '.json', ['asked.' + str(step) + '.jsonl'])
                    if step < 400:
                        loss = train_step(reader, schedule[step], devindex, devacts, specs[row], opt)
                        with (runout / 'train.jsonl').open('a') as f:
                            f.write(json.dumps({'step': step+1, 'loss': loss, 'epoch': time.time()})+'\n')
                C.jsonl(runout / 'free.400.jsonl', free(reader, test, testacts, row,
                    deadline_check=lambda: check_time(assignment, science_deadline)))
                torch.save({n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad}, runout / 'adapter.400.pt')
                check_time(assignment, science_deadline)
                C.seal(runout, 'SCORE_SEAL.json')
                check_time(assignment, science_deadline)
                detach_lowrank(mounted)
                del reader, opt, parameters, mounted
                gc.collect()
                torch.cuda.empty_cache()
            del model
            gc.collect()
            torch.cuda.empty_cache()
        check_time(assignment, science_deadline)
        status = 'COMPLETE_FULL_ASSIGNED_GRID'
    except ParityFailed:
        status = 'PARITY_FAILED_STOP'
        raise
    except Exception:
        if not environment_ready:
            status = 'NOT_RUN_ENVIRONMENT'
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        elapsed = time.time() - assignment['provider_created_epoch']
        C.dump(out / 'RUN_RECEIPT.json', {'status': status, 'gpu_seconds_provider': elapsed,
            'gpu_hours_provider': elapsed / 3600, 'runs': assignment['runs'],
            'plan_sha256': C.sha(C.HERE / 'PLAN.json'), 'test_labels_opened': False,
            'full_private_test_labels_opened': False,
            'science_started_epoch': science_started,
            'termination_required': True, 'retry_authorized': False,
            'previous_gpu_seconds': assignment['previous_gpu_seconds'],
            'parity_input_seal_sha256': assignment.get('parity_input_seal_sha256'),
            'parity_labels_opened_only_252': (out / 'PARITY_RESULT.json').exists(),
            **{key: C.sha(out / name) for name, key in {
                'TRAINING_ENVIRONMENT.json': 'environment_manifest_sha256',
                'ENVIRONMENT_RUNTIME_RESULT.json': 'environment_runtime_result_sha256',
                'PARITY_RESULT.json': 'parity_result_sha256',
                'PARITY_SCORES.jsonl': 'parity_scores_sha256'}.items() if (out / name).is_file()}})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    for key in ('bank', 'capture', 'out'):
        prep.add_argument('--' + key, type=Path, required=True)
    launch = sub.add_parser('run')
    for key in ('assignment', 'mapping', 'input', 'assets', 'out', 'admission', 'environment-manifest', 'parity-inputs'):
        launch.add_argument('--' + key, type=Path, required=True)
    admit = sub.add_parser('admit')
    admit.add_argument('--forecasts', type=Path, nargs='+', required=True)
    admit.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    C.validate_plan(C.plan())
    if a.command == 'prepare':
        print(json.dumps(C.prepare(a.bank, a.capture, a.out), sort_keys=True))
    elif a.command == 'admit':
        forecasts = [dict(C.read(f), forecast_sha256=C.sha(f)) for f in a.forecasts]
        C.dump(a.out, C.admit(forecasts))
    else:
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        run(a)


if __name__ == '__main__':
    main()
