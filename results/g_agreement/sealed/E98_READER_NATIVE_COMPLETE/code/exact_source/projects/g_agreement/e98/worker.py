"""E98 separated capture/readout stages. Never accepts a private key or labels."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import signal
import threading
import time
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    os.replace(tmp, path)


def verify(root, seal_name, expected):
    p = root / seal_name
    if sha(p) != expected:
        raise ValueError('Seal digest mismatch')
    seal = json.loads(p.read_text())
    for name, digest in seal['files'].items():
        f = (root / name).resolve()
        if not f.is_relative_to(root.resolve()) or sha(f) != digest:
            raise ValueError('Sealed file mismatch')
    return seal


def seal(root, name, **metadata):
    records = list((root / 'records').glob('*.json')) if metadata.get('phase') == 'reader' else []
    first = min(records, key=lambda p: p.stat().st_mtime_ns) if records else None
    metadata['first_output_utc'] = (datetime.fromtimestamp(first.stat().st_mtime, timezone.utc).isoformat()
                                    if first else 'unknown')
    metadata['first_output_evidence'] = ({'source': 'archived_file_mtime',
        'path': str(first.relative_to(root)), 'mtime_ns': first.stat().st_mtime_ns}
        if first else {'source': 'none', 'reason': 'No readout, judgment or analysis output in this stage'})
    metadata['files'] = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
                         if p.is_file() and p.name != name and not p.name.endswith('.tmp')}
    write(root / name, metadata)


def validate(items, reader_ids):
    if not items or any(set(x) != {'id', 'ids', 'read_index'} for x in items):
        raise ValueError('Public allowlist only')
    ids = [x['id'] for x in items]
    if len(ids) != len(set(ids)) or len(reader_ids) != len(set(reader_ids)) or not set(reader_ids) <= set(ids):
        raise ValueError('Unique capture/test IDs required')
    for x in items:
        if len(x['id']) != 32 or any(c not in '0123456789abcdef' for c in x['id']):
            raise ValueError('Opaque ID required')
        if not x['ids'] or any(type(t) is not int or t < 0 for t in x['ids']):
            raise ValueError('Token IDs required')
        if x['read_index'] != len(x['ids']) - 1:
            raise ValueError('Prefix must end at read token')


def require_inventory(root, ids, phase):
    suffix = '.npy' if phase == 'capture' else '.json'
    expected = {i + suffix for i in ids}
    records = root / 'records'
    actual = {p.name for p in records.iterdir() if p.is_file()} if records.is_dir() else set()
    if actual != expected or (root / 'FAILURE.json').exists():
        raise ValueError('Complete expected record inventory without FAILURE required')
    if phase == 'capture':
        for name in sorted(expected):
            value = np.load(records / name, allow_pickle=False)
            if value.shape != (2560,) or not np.isfinite(value).all():
                raise ValueError('Invalid capture activation')


def require_capture(root, digest, input_sha, items):
    cap = verify(root, 'CAPTURE_SEAL.json', digest)
    if cap.get('status') != 'COMPLETE' or cap.get('input_sha256') != input_sha:
        raise ValueError('Complete same-input capture required')
    require_inventory(root, [x['id'] for x in items], 'capture')
    expected = {'records/' + x['id'] + '.npy' for x in items}
    if not expected <= set(cap['files']):
        raise ValueError('Capture records must be sealed')
    return cap


class Clock:
    def __init__(self, out, deadline):
        self.out, self.deadline, self.samples = out, deadline, []
    def check(self):
        if time.time() >= self.deadline - 60:
            raise TimeoutError('Custody deadline, including retrieval reserve')
    def measure(self, fn):
        self.check()
        start = time.monotonic()
        result = fn()
        self.samples.append(time.monotonic() - start)
        self.check()
        return result
    def fits(self, remaining):
        forecast = 1.25 * remaining * float(np.mean(self.samples))
        fits = time.time() + forecast < self.deadline - 60
        write(self.out / 'FORECAST.json', dict(remaining_items=remaining,
              mean_real_seconds=float(np.mean(self.samples)), forecast_seconds=forecast,
              margin=1.25, admitted=fits, deadline_epoch=self.deadline))
        return fits


def capture_one(model, ids, layer):
    import torch
    values = []
    def hook(module, args, output):
        z = output[0] if isinstance(output, tuple) else output
        values.append(z[0, -1].detach().float().cpu().numpy())
    handle = model.model.layers[layer].register_forward_hook(hook)
    try:
        with torch.inference_mode():
            model(input_ids=torch.tensor([ids], device=model.device), use_cache=False, logits_to_keep=1)
    finally:
        handle.remove()
    if len(values) != 1 or values[0].shape != (2560,) or not np.isfinite(values[0]).all():
        raise ValueError('Exactly one finite block18 residual required')
    return values[0]


def oracle_one(model, tokenizer, config, activation, layer):
    import torch
    from transformers import GenerationConfig
    text = config['prompt_template'].format(layer=layer, marker=config['injection']['marker'])
    ids = tokenizer.apply_chat_template([{'role': 'user', 'content': text}], tokenize=True,
                                        add_generation_prompt=True, enable_thinking=False)
    if not isinstance(ids, list):
        ids = ids['input_ids']
    marker = config['injection']['token_id']
    slots = [i for i, t in enumerate(ids) if t == marker]
    if len(slots) != 1 or slots[0] == 0 or slots[0] == len(ids) - 1:
        raise ValueError('Exactly one interior marker')
    slot = slots[0]
    if [ids[slot - 1], ids[slot + 1]] != config['injection']['neighbor_ids']:
        raise ValueError('Marker neighbors mismatch')
    v = torch.as_tensor(activation, dtype=torch.float32)
    if v.shape != (2560,) or not torch.isfinite(v).all() or v.norm() <= 0:
        raise ValueError('Finite nonzero activation required')
    with torch.inference_mode():
        embedding = model.get_input_embeddings()
        x = embedding(torch.tensor([ids], device=embedding.weight.device)).clone()
        x[0, slot] = (config['injection']['norm'] * v / v.norm()).to(x.device, dtype=x.dtype)
        eos = model.generation_config.eos_token_id
        stop = set(eos if isinstance(eos, list) else [eos])
        stop.update([tokenizer.eos_token_id, marker]); stop.discard(None)
        generation = GenerationConfig(do_sample=False, temperature=None, top_p=None, top_k=None,
             max_new_tokens=128, eos_token_id=sorted(stop), pad_token_id=tokenizer.pad_token_id)
        result = model.generate(inputs_embeds=x, attention_mask=torch.ones(x.shape[:2], dtype=torch.long,
                     device=x.device), generation_config=generation)[0].tolist()
    end = next((i for i, t in enumerate(result) if t in stop), len(result))
    return {'text': tokenizer.decode(result[:end], skip_special_tokens=True).strip(),
            'tokens': result[:end], 'truncated': len(result) >= 128 and not any(t in stop for t in result)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['capture', 'reader'])
    for key in ('inputs', 'assignment', 'card', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--input-sha', required=True)
    p.add_argument('--card-sha', required=True)
    p.add_argument('--source-sha', required=True)
    p.add_argument('--capture', type=Path)
    p.add_argument('--capture-sha')
    p.add_argument('--go', type=Path)
    a = p.parse_args()
    if sha(Path(__file__)) != a.source_sha:
        raise ValueError('Worker source digest mismatch')
    if sha(a.card) != a.card_sha:
        raise ValueError('Pinned card required')
    card = json.loads(a.card.read_text())
    if card['verdict'] != 'PASS':
        raise ValueError('E98 not run (assets)')
    source = verify(a.inputs, 'INPUT_SEAL.json', a.input_sha)
    items = json.loads((a.inputs / 'items.json').read_text())
    reader_ids = json.loads((a.inputs / 'reader_ids.json').read_text())
    validate(items, reader_ids)
    assignment = json.loads(a.assignment.read_text())
    if (assignment['experiment'] != 'E98' or assignment['phase'] != a.phase
            or assignment['gpu_count'] != 1 or assignment['budget_admitted'] is not True
            or not 0 < assignment['cap_seconds'] <= 36000
            or assignment['prior_gpu_seconds'] + assignment['cap_seconds'] > 36000
            or assignment['deadline_epoch'] != assignment['custody_start_epoch'] + assignment['cap_seconds']):
        raise ValueError('Budget/custody cap invalid')
    if source['layer'] != 18 or source['hidden_size'] != 2560:
        raise ValueError('Frozen capture site mismatch')
    # Reader launch cannot load or open a capture unless GO binds committed forecast evidence.
    if a.phase == 'reader':
        if not (a.go and a.capture and a.capture_sha):
            raise ValueError('Capture and GO required')
        go = json.loads(a.go.read_text())
        if (go.get('experiment') != 'E98' or go.get('input_sha256') != a.input_sha
                or go.get('capture_sha256') != a.capture_sha
                or go.get('forecast_commit_verified') is not True
                or len(go.get('forecast_commit', '')) != 40
                or len(go.get('forecast_sha256', '')) != 64
                or go.get('forecast_committed_epoch', float('inf')) >= go.get('issued_epoch', 0)):
            raise ValueError('R3b forecast-before-GO binding required')
        require_capture(a.capture, a.capture_sha, a.input_sha, items)
    a.out.mkdir(parents=True, exist_ok=False)
    write(a.out / 'ASSIGNMENT.json', assignment)
    clock = Clock(a.out, assignment['deadline_epoch'])
    clock.check()
    timer = threading.Timer(max(0, clock.deadline - time.time()), lambda: os.kill(os.getpid(), signal.SIGKILL))
    timer.daemon = True; timer.start()
    status = 'FAILED'
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        start = time.monotonic()
        tokenizer = AutoTokenizer.from_pretrained(card['model']['repo'], revision=card['model']['revision'], token=False)
        model = AutoModelForCausalLM.from_pretrained(card['model']['repo'], revision=card['model']['revision'],
                    token=False, dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda').eval()
        if a.phase == 'reader':
            from huggingface_hub import snapshot_download
            from peft import PeftModel
            from safetensors import safe_open
            root = Path(snapshot_download(card['oracle']['repo'], revision=card['oracle']['revision'], token=False,
                           allow_patterns=['adapter_config.json', 'adapter_model.safetensors', 'lens_config.json']))
            config = json.loads((root / 'lens_config.json').read_text())
            if config != card['oracle']['config']:
                raise ValueError('Oracle contract differs from audited config')
            model = PeftModel.from_pretrained(model, root).eval()
            stem = lambda s: s.removeprefix('base_model.model.').replace('.default', '')
            live = {stem(n) for n, _ in model.named_parameters() if 'lora_' in n}
            with safe_open(root / 'adapter_model.safetensors', framework='pt') as f:
                saved = {stem(n) for n in f.keys() if 'lora_' in n}
            if not saved or not saved <= live:
                raise ValueError('Adapter keys do not map exactly')
        write(a.out / 'SETUP.json', {'seconds': time.monotonic()-start, 'charged_to_clock': True})
        clock.check()
        # Independent synthetic warmup, discarded and excluded from real-item timing.
        dummy = tokenizer.encode(' A neutral synthetic warmup.', add_special_tokens=False)
        if a.phase == 'capture':
            capture_one(model, dummy, 18)
            units = items
        else:
            oracle_one(model, tokenizer, config, np.random.default_rng(20261028).normal(size=2560), 18)
            units = [{'id': i} for i in reader_ids]
            write(a.out / 'GO.json', go)
        (a.out / 'records').mkdir()
        for index, item in enumerate(units):
            if a.phase == 'capture':
                value = clock.measure(lambda: capture_one(model, item['ids'], 18))
                np.save(a.out / 'records' / (item['id'] + '.npy'), value, allow_pickle=False)
            else:
                value = np.load(a.capture / 'records' / (item['id'] + '.npy'), allow_pickle=False)
                result = clock.measure(lambda: oracle_one(model, tokenizer, config, value, 18))
                write(a.out / 'records' / (item['id'] + '.json'), dict(id=item['id'], **result))
            write(a.out / 'PROGRESS.json', dict(completed=index+1, total=len(units)))
            if not clock.fits(len(units)-index-1):
                status = 'NO_FIT'; break
        else:
            require_inventory(a.out, [x['id'] for x in units], a.phase)
            status = 'COMPLETE'
        write(a.out / 'TIMING.json', dict(completed_epoch=time.time(), deadline_epoch=clock.deadline,
                                         real_seconds=clock.samples))
    except Exception as error:
        status = 'FAILED'
        write(a.out / 'FAILURE.json', {'type': type(error).__name__, 'message': str(error)[:300]})
        raise
    finally:
        timer.cancel()
        seal(a.out, 'CAPTURE_SEAL.json' if a.phase == 'capture' else 'OUTPUT_SEAL.json',
             experiment='E98', phase=a.phase, status=status, input_sha256=a.input_sha,
             card_sha256=a.card_sha, layer=18, reader_outputs_opened=False)


if __name__ == '__main__':
    main()
