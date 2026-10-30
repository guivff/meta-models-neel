"""Integrator-only §86 worker. No labels, no autonomous pod operations or retries.

Requires an H200-class GPU: target/Oracle, J projection, and NLA stay resident
after setup. A warmed, median-of-three unretained all-row smoke estimates the unchanged
bank. If it does not fit, stop; never choose fewer rows or items from timing.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import signal
import time
from . import protocol as P
from . import run as W1
from .w10_items import source_hashes, SECTION


def seal_named(out, files, name, status):
    receipt = {'status': status, 'files': {n: P.sha(Path(out)/n) for n in files}}
    P.dump(Path(out)/name, receipt)
    return receipt


def allocation(forecast):
    if not math.isfinite(forecast) or forecast <= 0:
        raise ValueError('invalid forecast')
    requested = 1.5*forecast+360
    if requested > 3600:
        raise ValueError(f'NO_FIT: 1.5F + 360 = {requested:.3f} > 3600 s')
    return requested


def admit(assignment, bank, now=None, pod_id=None):
    now = time.time() if now is None else now
    a = json.loads(Path(assignment).read_text())
    pod_id = pod_id or os.environ.get('RUNPOD_POD_ID')
    if not pod_id or a.get('pod_id') != pod_id or a.get('issuer') != 'integrator' or a.get('experiment') != 'W10':
        raise ValueError('requires exact integrator W10 pod assignment')
    required_true = ('brief_registered', 'brief_pushed', 'manifest_committed', 'external_hardstop_verified')
    if any(a.get(k) is not True for k in required_true):
        raise ValueError('registration, committed freeze and independent guard required')
    for field in ('source_commit', 'brief_commit', 'manifest_commit'):
        s = a.get(field, '')
        if len(s) != 40 or any(c not in '0123456789abcdef' for c in s):
            raise ValueError('missing exact commit '+field)
    P.verify(bank, 'INPUT_SEAL.json')
    manifest = json.loads((Path(bank)/'manifest.json').read_text())
    if a.get('source_files') != source_hashes() or manifest['source_files'] != source_hashes():
        raise ValueError('source differs from frozen generator/worker')
    if a.get('manifest_sha256') != P.sha(Path(bank)/'manifest.json'):
        raise ValueError('manifest assignment mismatch')
    if a.get('section86_sha256') != P.sha(P.ROOT/SECTION) or manifest['registration_sha256'] != P.sha(P.ROOT/SECTION):
        raise ValueError('registered section differs')
    if a.get('previous_gpu_seconds') != 0:
        raise ValueError('only a fresh W10 attempt is authorized; retries require infrastructure-failure evidence')
    budget = P._science_budget(a)
    created, deadline = float(a['provider_created_epoch']), float(a['deadline_epoch'])
    if (budget > 3600 or float(a.get('staging_allowance_seconds', -1)) != 1500
            or not all(math.isfinite(v) for v in (now, created, deadline))
            or not created <= now < created+1500 or not 0 < deadline-created <= float(a['allocated_gpu_seconds'])):
        raise ValueError('invalid setup/science allocation')
    a['_science_clock_path'] = str(Path(assignment).resolve().with_suffix('.science-clock.json'))
    a['_assignment_sha256'] = P.sha(assignment)
    if Path(a['_science_clock_path']).exists():
        raise ValueError('existing science clock: no restart or duplicate attempt')
    P.science_deadline(a, now=now)
    return a


def inputs(bank):
    bank = Path(bank)
    P.verify(bank, 'INPUT_SEAL.json')
    W1._labels_absent(bank)
    items = P.rows(bank/'items.input.jsonl')
    specs = json.loads((bank/'templates.json').read_text())
    index = {x['id']: i for i, x in enumerate(items)}
    if len(index) != len(items) or len(items) != 4368:
        raise ValueError('wrong frozen input coverage')
    for x in items:
        if set(x) != {'id', 'feature', 'ids', 'donor_id'} or x['donor_id'] not in index:
            raise ValueError('label-free input/donor schema invalid')
        if items[index[x['donor_id']]]['feature'] != x['feature']:
            raise ValueError('random donor crosses row')
    checks = P.rows(bank/'mode_checks.input.jsonl')
    if len(checks) != 280 or len({x['id'] for x in checks}) != 280 or not {x['id'] for x in checks} <= set(index):
        raise ValueError('wrong mode-check selection')
    return items, [index[x['donor_id']] for x in items], specs, checks


def current_token_surprisal(logits, token_ids):
    """logits must predict the current token, i.e. come from position p-1."""
    import torch
    values = -torch.log_softmax(logits.float(), dim=-1).gather(-1, token_ids[:, None]).squeeze(-1)
    if not torch.isfinite(values).all():
        raise ValueError('nonfinite surprisal')
    return values


def capture_with_surprisal(model, tok, items, checkpoint, batch=8):
    """One full base-model forward captures 42/44 and current-token surprisal."""
    import torch
    from mats.capture import decoder_blocks, _hidden
    blocks = decoder_blocks(model)
    captured = {}
    handles = [blocks[L].register_forward_hook(lambda m, i, o, layer=L: captured.__setitem__(layer, _hidden(o))) for L in (42, 44)]
    by_layer = {42: [], 44: []}
    surprisals = []
    try:
        with torch.no_grad():
            for start in range(0, len(items), batch):
                checkpoint()
                chunk = items[start:start+batch]
                n = max(len(x['ids']) for x in chunk)
                device = next(model.parameters()).device
                ids = torch.full((len(chunk), n), tok.pad_token_id or 0, dtype=torch.long, device=device)
                mask = torch.zeros_like(ids)
                lengths = torch.tensor([len(x['ids']) for x in chunk], device=device)
                for i, x in enumerate(chunk):
                    ids[i, :len(x['ids'])] = torch.tensor(x['ids'], device=device)
                    mask[i, :len(x['ids'])] = 1
                # Only last two vocabulary projections; right-padding differences
                # are handled by asking the model for the absolute positions needed.
                positions = torch.unique(lengths-2, sorted=True)
                output = model(input_ids=ids, attention_mask=mask, logits_to_keep=positions, use_cache=False)
                rows = torch.arange(len(chunk), device=device)
                local = torch.searchsorted(positions, lengths-2)
                values = current_token_surprisal(output.logits[rows, local], ids[rows, lengths-1])
                for layer in by_layer:
                    by_layer[layer].append(captured[layer][rows, lengths-1].detach().float().cpu())
                surprisals.extend({'id': x['id'], 'surprisal_nats': float(v)} for x, v in zip(chunk, values))
                captured.clear()
    finally:
        for handle in handles:
            handle.remove()
    return {L: torch.cat(v) for L, v in by_layer.items()}, surprisals


def generate_one(model, tok, item, checkpoint):
    import torch
    checkpoint()
    ids = torch.tensor([item['prompt_ids']], device=next(model.parameters()).device)
    with torch.no_grad():
        out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
            max_new_tokens=48, pad_token_id=tok.pad_token_id or tok.eos_token_id, use_cache=True)
    return {'id': item['id'], 'text': tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True),
            'generated_tokens': out.shape[1]-ids.shape[1]}


def reader_values(name, obj, h, spec):
    if name == 'olens':
        return obj.paired_logodds_templates(h, 44, W1._pairs(spec, name))
    if name == 'nla':
        from mats.readers.nla import paired_logodds_templates
        return paired_logodds_templates(obj, h, W1._pairs(spec, name), batch=32)
    return W1.native_baseline_contrasts(obj, h, 44, W1._pairs(spec, name))


def synchronize():
    import torch
    torch.cuda.synchronize()


def timed(fn):
    synchronize()
    start = time.monotonic()
    value = fn()
    synchronize()
    return value, time.monotonic()-start


def warmup(ol, jl, nla, checkpoint):
    """One unscored setup unit through every measured kernel path."""
    warm = list(ol.tok('A neutral setup record is complete.', add_special_tokens=False)['input_ids'])
    item = {'id': 'unscored-setup', 'ids': warm, 'prompt_ids': warm}
    with ol.base():
        h, _ = capture_with_surprisal(ol.model, ol.tok, [item]*8, checkpoint, batch=8)
    spec = {'olens': [('- A record.', '- A note.'), ('- A page.', '- A sheet.')],
            'nla': [('A record.', 'A note.'), ('A page.', 'A sheet.')],
            'jlens': [('record', 'note'), ('page', 'sheet')]}
    for name, obj, layer in (('olens', ol, 44), ('jlens', jl, 44), ('nla', nla, 42)):
        checkpoint()
        reader_values(name, obj, h[layer].repeat(2, 1), spec)
    with ol.base():
        generate_one(ol.model, ol.tok, item, checkpoint)
    synchronize()
    checkpoint()


def timed_median(fn, normalize=lambda value, seconds: seconds):
    """Median of three post-warm-up real units; retain all gate timings."""
    samples = []
    for _ in range(3):
        value, seconds = timed(fn)
        samples.append((value, normalize(value, seconds)))
    value, seconds = sorted(samples, key=lambda sample: sample[1])[1]
    return value, seconds, [sample[1] for sample in samples]


def smoke(items, specs, checks, ol, jl, nla, checkpoint):
    """Worst-length representative per row; outputs discarded, timing only.

    Capture is projected by padded token work in the fixed batch of eight;
    reader times use actual frozen phrasings in a native sixteen-vector batch.
    Free generation uses the slowest of all fourteen row representatives,
    conservatively scaled to the full 48-token allowance.
    No score or label is used to select items or choose the run's scope.
    """
    groups = defaultdict(list)
    for i, x in enumerate(items):
        groups[x['feature']].append(i)
    per_row = 16  # native scorer batches 32 candidates = 16 activations
    representatives = [i for indices in groups.values() for i in
        sorted(indices, key=lambda i: (len(items[i]['ids']), items[i]['id']), reverse=True)[:per_row]]
    selected = [items[i] for i in representatives]
    with ol.base():
        (h, _), capture_s, capture_units = timed_median(lambda: capture_with_surprisal(ol.model, ol.tok, selected, checkpoint, batch=8))
    capture_work = sum(max(len(x['ids']) for x in items[s:s+8])*len(items[s:s+8]) for s in range(0, len(items), 8))
    smoke_work = sum(max(len(x['ids']) for x in selected[s:s+8])*len(selected[s:s+8]) for s in range(0, len(selected), 8))
    forecast = capture_s*capture_work/smoke_work
    timings = {'capture_s': capture_s, 'capture_units_s': capture_units, 'capture_projected_s': forecast, 'reader_rows': []}
    for k, (feature, indices) in enumerate(groups.items()):
        for name, obj, layer in (('olens', ol, 44), ('jlens', jl, 44), ('nla', nla, 42)):
            checkpoint()
            _, elapsed, units = timed_median(lambda: reader_values(name, obj, h[layer][k*per_row:(k+1)*per_row], specs[feature]))
            forecast += elapsed*len(indices)/per_row  # donor scores are deterministic reindexing
            timings['reader_rows'].append({'feature': feature, 'reader': name, 'sixteen_vectors_s': elapsed, 'units_s': units})
    generation_times, generation_units = [], []
    with ol.base():
        for feature in sorted({x['feature'] for x in checks}):
            chosen = max((x for x in checks if x['feature'] == feature), key=lambda x: len(x['prompt_ids']))
            _, elapsed, units = timed_median(
                lambda: generate_one(ol.model, ol.tok, chosen, checkpoint),
                normalize=lambda generated, seconds: seconds*48/max(1, generated['generated_tokens']))
            generation_times.append(elapsed)
            generation_units.append({'feature': feature, 'projected_48_token_units_s': units})
    forecast += max(generation_times)*len(checks)
    timings.update(mode_generation_smoke_s=generation_times, mode_generation_units=generation_units,
                   timing_policy="one unscored setup warm-up per code path; median of next three real units",
                   remaining_work_forecast_s=forecast,
                   unretained_smoke=True, donor_scoring='deterministic reindex of own-activation scores, identical scorer and batch')
    return forecast, timings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'assignment', 'assets', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    assignment = admit(a.assignment, a.bank)
    items, donors, templates, checks = inputs(a.bank)
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('w10_capture_score', gpu=True), P.compute_window(assignment):
        assets = W1._assets(a.assets)
        ol = W1._load_oracle(assets)
        from mats.readers.jlens import load_jlens
        from mats.readers.nla import load_nla
        jl = load_jlens(ol.model, ol.tok, layers=[44], path=assets['jlens'])
        nla = load_nla(root=assets['nla'], load_ar=False, enable_thinking=False)
        P.science_deadline(assignment)  # fail if setup elapsed; no first marker yet
        # All measured paths warm before any timed science unit; outputs discarded.
        warmup(ol, jl, nla, lambda: P.science_deadline(assignment))
        P.science_checkpoint(assignment)
        clock = json.loads(Path(assignment['_science_clock_path']).read_text())
        first = clock['first_science_epoch']
        projected_end = [clock['science_deadline_epoch']]
        def check():
            P.science_checkpoint(assignment)
            if time.time() >= projected_end[0]:
                raise TimeoutError('W10 measured forecast deadline reached')
            signal.setitimer(signal.ITIMER_REAL, max(.01, projected_end[0]-time.time()))
        F_remaining, diagnostics = smoke(items, templates, checks, ol, jl, nla, check)
        forecast = time.time()-first+F_remaining
        try:
            budget = allocation(forecast)
            if budget > P._science_budget(assignment):
                raise ValueError('NO_FIT: assigned science smaller than measured requirement')
        except ValueError as exc:
            P.dump(a.out/'FORECAST.json', {'status': 'NO_FIT', 'forecast_s': forecast, 'reason': str(exc), **diagnostics})
            raise
        projected_end[0] = min(projected_end[0], first+budget)
        P.dump(a.out/'FORECAST.json', {'status': 'FIT', 'forecast_s': forecast,
            'science_allocation_s': budget, 'first_science_epoch': first, 'science_deadline_epoch': projected_end[0], **diagnostics})
        check()
        with ol.base():
            h, surprisal = capture_with_surprisal(ol.model, ol.tok, items, check)
        import numpy as np
        for layer, vectors in h.items():
            np.save(a.out/f'acts{layer}.npy', vectors.numpy(), allow_pickle=False)
        P.dump(a.out/'items.order.json', [x['id'] for x in items])
        P.jsonl(a.out/'surprisal.jsonl', [r for r, x in zip(surprisal, items) if x['feature'].startswith('surprisal_')])
        P.dump(a.out/'provenance.json', {'input_seal_sha256': P.sha(a.bank/'INPUT_SEAL.json'),
            'assignment_sha256': P.sha(a.assignment), 'assets_sha256': P.sha(a.assets), 'source_files': source_hashes(),
            'surprisal_position': 'current token, predicted from p-1', 'teacher_forced_read_position': 'last token of frozen ids',
            'first_science_epoch': first, 'readers': [['olens', 44], ['nla', 42], ['jlens', 44]]})
        seal_named(a.out, ['acts42.npy', 'acts44.npy', 'items.order.json', 'surprisal.jsonl', 'provenance.json'], 'CAPTURE_SEAL.json', 'W10_CAPTURE_SEALED')
        groups = defaultdict(list)
        for i, it in enumerate(items):
            groups[it['feature']].append(i)
        all_scores = []
        for feature, indices in groups.items():
            local = {i: j for j, i in enumerate(indices)}
            for name, obj, layer in (('olens', ol, 44), ('jlens', jl, 44), ('nla', nla, 42)):
                check()
                v = reader_values(name, obj, h[layer][indices], templates[feature])
                for arm, values in (('true', v), ('random_donor', v[:, [local[donors[i]] for i in indices]])):
                    rows = W1._score_rows(items, indices, values, name, layer, arm,
                        'max_token_cosine_contrast' if name == 'jlens' else 'summed_sequence_logodds')
                    all_scores.extend(rows)
                    with (a.out/'scores.partial.jsonl').open('a') as f:
                        for r in rows:
                            f.write(json.dumps(r, sort_keys=True, allow_nan=False)+'\n')
                        f.flush()
                        os.fsync(f.fileno())
        P.jsonl(a.out/'scores.jsonl', all_scores)
        seal_named(a.out, ['scores.jsonl', 'items.order.json', 'provenance.json', 'surprisal.jsonl', 'FORECAST.json'], 'SCORE_SEAL.json', 'SCORES_SEALED_W10_BEFORE_LABEL_JOIN')
        generated = []
        with ol.base():
            with (a.out/'mode_generations.partial.jsonl').open('x') as stream:
                for item in checks:
                    row = generate_one(ol.model, ol.tok, item, check)
                    generated.append(row)
                    stream.write(json.dumps(row, sort_keys=True)+'\n')
                    stream.flush()
        P.jsonl(a.out/'mode_generations.jsonl', generated)
        seal_named(a.out, ['mode_generations.jsonl', 'provenance.json'], 'MODE_GENERATION_SEAL.json', 'MODE_GENERATIONS_SEALED_BEFORE_LABEL_JOIN')
        check()
        P.dump(a.out/'SCIENCE_RECEIPT.json', {'first_science_epoch': first,
            'completed_epoch': time.time(), 'science_elapsed_s': time.time()-first,
            'science_deadline_epoch': projected_end[0], 'forecast_s': forecast,
            'science_allocation_s': budget, 'assignment_sha256': P.sha(a.assignment),
            'status': 'COMPLETE_NO_LABEL_JOIN'})


if __name__ == '__main__':
    main()
