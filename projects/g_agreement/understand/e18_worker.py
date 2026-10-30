"""Single-process E18: one Oracle/base backbone; native continuation then asked scoring."""
import argparse
from contextlib import nullcontext
import os
from pathlib import Path
import time
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .followup_packed import jsonl
from .e16_worker import asked
from .e18 import ARMS, BATCH, PREFIX, FEATURES, continuation_tokens, lens_head, base_head
from .e18_runtime import Gate, NoFit, PATHS, PLAN


def generate(reader, h, items):
    import torch
    native, slot = reader.carrier(44)
    head = list(native) + reader.tok.encode(PREFIX, add_special_tokens=False)
    ids = torch.tensor([head] * len(items), device=reader.device)
    vectors = torch.as_tensor(h, dtype=torch.float32, device=reader.device)
    pad = reader.tok.pad_token_id or reader.tok.eos_token_id
    eos = reader.model.generation_config.eos_token_id
    eos = set(eos if isinstance(eos, (tuple, list)) else ([] if eos is None else [eos]))
    with torch.inference_mode():
        out = reader.model.generate(inputs_embeds=reader._embed(ids, slot, vectors),
                                    attention_mask=torch.ones_like(ids), do_sample=False,
                                    num_beams=1, max_new_tokens=16, pad_token_id=pad)
    if len(out) != len(items) or out.shape[1] > 16:
        raise ValueError('native inputs_embeds generation must return at most16 new tokens')
    result = []
    for item, sequence in zip(items, out.cpu().tolist()):
        body = continuation_tokens(sequence, eos, pad)
        raw = reader.tok.decode(body, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        result.append({'id': item['id'], 'feature': item['feature'], 'layer': 44,
                       'generated_ids': sequence, 'continuation_ids': body, 'raw': raw})
    return result


def score_heads(reader, heads, slot, h, pairs, base=False):
    """E16 paired teacher-forcing, with per-row head offsets for variable continuations."""
    import torch
    if not heads or (base and (slot is not None or h is not None)):
        raise ValueError('base scoring must have no activation or injection slot')
    if not base and (slot is None or h is None):
        raise ValueError('lens scoring requires recipient activation injection')
    n_items = len(heads)
    output = []
    with (reader.base() if base else nullcontext()), torch.inference_mode():
        for pair in pairs:
            candidates = [reader.tok.encode(c, add_special_tokens=False) for c in pair]
            if len(candidates) != 2 or any(not c for c in candidates):
                raise ValueError('two nonempty frozen candidates required')
            length = max(map(len, heads)) + max(map(len, candidates))
            ids = torch.full((2*n_items, length), reader.tok.pad_token_id or 0,
                             device=reader.device, dtype=torch.long)
            mask = torch.zeros_like(ids)
            for i, head in enumerate(heads):
                for j, cand in enumerate(candidates):
                    seq = head + cand
                    ids[2*i+j, :len(seq)] = torch.tensor(seq, device=reader.device)
                    mask[2*i+j, :len(seq)] = 1
            if base:
                logits = reader.model(input_ids=ids, attention_mask=mask,
                                      use_cache=False).logits
            else:
                acts = torch.as_tensor(h, dtype=torch.float32, device=reader.device).repeat_interleave(2, 0)
                embeds = reader._embed(ids, slot, acts)
                logits = reader.model(inputs_embeds=embeds, attention_mask=mask,
                                      use_cache=False).logits
            # Full logits avoid a common fixed-offset bug in variable-length heads.
            values = []
            for i, head in enumerate(heads):
                lp = []
                for j, cand in enumerate(candidates):
                    start = len(head)-1
                    prediction = torch.log_softmax(logits[2*i+j, start:start+len(cand)].float(), -1)
                    token_ids = torch.tensor(cand, device=reader.device)
                    lp.append(float(prediction.gather(-1, token_ids[:, None]).sum()))
                values.append(lp[0]-lp[1])
            output.append(values)
    array = np.asarray(output, dtype=float).T
    if array.shape != (n_items, len(pairs)) or not np.isfinite(array).all():
        raise ValueError('complete finite paired score grid required')
    return array


def score_arm(reader, arm, items, h, templates, continuations, donors):
    if arm not in ARMS or len({r['feature'] for r in items}) != 1:
        raise ValueError('one known arm and one row per scoring unit required')
    f = items[0]['feature']
    if arm == 'a':
        # Exact registered W1 baseline through E16, no prefix or wording choice.
        return asked(reader, 'olens', {'feature': f, 'indices': list(range(len(items)))},
                     items, h, templates)
    chosen = [continuations[donors[r['id']] if arm == 'c' else r['id']] for r in items]
    if arm == 'd':
        heads = [base_head(reader.tok, r['raw']) for r in chosen]
        values = score_heads(reader, heads, None, None, templates[f]['olens'], base=True)
    else:
        hs = [lens_head(reader, r['continuation_ids']) for r in chosen]
        if len({slot for _, slot in hs}) != 1:
            raise ValueError('native injection slot drift')
        values = score_heads(reader, [head for head, _ in hs], hs[0][1], h,
                             templates[f]['olens'])
    return [{'id': r['id'], 'feature': f, 'reader': 'base' if arm == 'd' else 'olens',
             'scores': v.tolist()} for r, v in zip(items, values)]


def load_reader(a, g):
    import common, torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from mats.readers.olens import load_olens
    from projects.g_agreement.blindspot.run import _assets
    g.setup_guard()
    assets = _assets(a.assets, ('model', 'olens'))
    if sha(Path(assets['model'])/'tokenizer.json') != read(a.inputs/'provenance.json')['tokenizer_json_sha256']:
        raise ValueError('native W1 tokenizer mismatch')
    model = AutoModelForCausalLM.from_pretrained(assets['model'], dtype=torch.bfloat16,
                                               device_map='cuda', local_files_only=True).eval()
    tok = AutoTokenizer.from_pretrained(assets['model'], local_files_only=True)
    reader = load_olens(model=model, tok=tok, lora_dir=assets['olens'])
    g.setup_guard()
    return reader


class Collection:
    def __init__(self, a, g, reader):
        self.a, self.g, self.reader = a, g, reader
        self.items = rows(a.inputs/'items.input.jsonl')
        self.dev = rows(a.inputs/'dev.input.jsonl')
        self.h = np.load(a.inputs/'acts44.npy', allow_pickle=False)
        self.dev_h = np.load(a.inputs/'dev_acts44.npy', allow_pickle=False)
        self.units = read(a.inputs/'units.json')
        self.templates = read(a.inputs/'templates.json')
        self.donors = read(a.inputs/'donors.json')
        self.dev_donors = read(a.inputs/'dev.donors.json')
        self.dev_raw, self.raw = {}, {}
        self.results = {k: {} for k in ARMS}
        for path in PATHS:
            (a.out/path).mkdir()

    def setup(self):
        g = self.g; g.setup_guard()
        items, h = self.dev[:BATCH], self.dev_h[:BATCH]
        t = time.monotonic(); warm = generate(self.reader, h, items)
        g.warm('generation', time.monotonic()-t)
        cache = {r['id']: r for r in warm}; donors = read(self.a.inputs/'warm.donors.json')
        for arm in ARMS:
            g.setup_guard(); t = time.monotonic()
            score_arm(self.reader, arm, items, h, self.templates, cache, donors)
            g.warm(arm, time.monotonic()-t)
        dump(self.a.out/'DEV_SMOKE.json', {'status': 'PASS', 'split': 'dev',
             'ids': [r['id'] for r in items], 'paths': list(PATHS), 'wording_selection': False,
             'test_forwards': 0, 'scores_retained': False, 'models_loaded_once': True})

    def pilot(self):
        self.g.start()
        for path in PATHS:
            for j in range(3):
                self.g.guard(); ix = slice(j*BATCH, (j+1)*BATCH)
                items, h = self.dev[ix], self.dev_h[ix]
                t = time.monotonic()
                if path == 'generation':
                    value = generate(self.reader, h, items)
                    self.dev_raw.update({r['id']: r for r in value})
                else:
                    score_arm(self.reader, path, items, h, self.templates,
                              self.dev_raw, self.dev_donors)
                dt = time.monotonic()-t
                dump(self.a.out/path/f'dev-timing-{j:02d}.json',
                     {'ids': [r['id'] for r in items], 'seconds': dt,
                      'split': 'dev', 'scores_discarded': True, 'test_forwards': 0})
                self.g.record(path, dt, retained=False)
        self.g.admit()

    def unit(self, path, j):
        self.g.guard(); unit = self.units[j]; ix = unit['indices']
        items, h = [self.items[i] for i in ix], self.h[ix]
        t = time.monotonic()
        if path == 'generation':
            value = generate(self.reader, h, items)
            if set(self.raw) & {r['id'] for r in value}:
                raise ValueError('duplicate test generation')
            self.raw.update({r['id']: r for r in value})
        else:
            value = score_arm(self.reader, path, items, h, self.templates, self.raw, self.donors)
            if j in self.results[path]: raise ValueError('duplicate score unit')
            self.results[path][j] = value
        dump(self.a.out/path/f'unit-{j:05d}.json', value)
        self.g.record(path, time.monotonic()-t, retained=True)

    def finish(self):
        for j in range(len(self.units)): self.unit('generation', j)
        ids = read(self.a.inputs/'ids.json')
        if set(self.raw) != set(ids): raise ValueError('incomplete continuation grid')
        p = self.a.out/'continuations'; p.mkdir()
        jsonl(p/'raw.jsonl', [self.raw[k] for k in ids])
        dump(p/'provenance.json', {'input_seal_sha256': sha(self.a.inputs/'INPUT_SEAL.json'),
             'native_layer': 44, 'prefix': PREFIX, 'max_new_tokens': 16,
             'greedy': True, 'assignment_sha256': self.g.assignment_sha256,
             'source_files': self.g.assignment['source_files'], 'sealed_before_asked_scoring': True})
        dump(p/'CONTINUATION_SEAL.json', {'status': 'E18_ALL_840_NATIVE_CONTINUATIONS_SEALED',
             'files': {name: sha(p/name) for name in ('raw.jsonl', 'provenance.json')}})
        for arm in ARMS:
            for j in range(len(self.units)): self.unit(arm, j)
        per_arm = {arm: {r['id']: r for unit in self.results[arm].values() for r in unit} for arm in ARMS}
        if any(set(d) != set(ids) for d in per_arm.values()): raise ValueError('incomplete score grid')
        jsonl(self.a.out/'scores.jsonl', [{'id': k, 'feature': self.raw[k]['feature'],
              'arms': {arm: per_arm[arm][k]['scores'] for arm in ARMS}} for k in ids])


def execute(a, g, reader=None):
    status, error, loads = 'COMPLETE', None, 0
    try:
        if reader is None:
            reader = load_reader(a, g); loads = 1
        c = Collection(a, g, reader); c.setup(); c.pilot(); c.finish(); g.guard()
    except Exception as exc:
        status = 'NO_FIT' if isinstance(exc, NoFit) else 'INCOMPLETE'
        error = type(exc).__name__ + ': ' + str(exc)
    g.status = status; g.write_state()
    dump(a.out/'run.json', {'experiment': 'E18', 'status': status, 'error': error,
         'PID': os.getpid(), 'checkpoint_load_counts': {'Oracle_and_base_shared': loads},
         'input_seal_sha256': sha(a.inputs/'INPUT_SEAL.json'),
         'assignment_sha256': g.assignment_sha256, 'source_commit': g.assignment.get('source_commit'),
         'first_science_epoch': g.first_science_epoch, 'elapsed_science_seconds': g.elapsed(),
         'science_clock_resets': 0, 'test_labels_accessed': False})
    seal(a.out, [str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()], 'E18_'+status)
    return status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'assets', 'assignment', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); verify(a.inputs, 'INPUT_SEAL.json')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')): raise ValueError('private truth forbidden on worker')
    units = read(a.inputs/'units.json')
    items = rows(a.inputs/'items.input.jsonl')
    if len(items) != 840 or len(units) != 60 or any(r['split'] != 'test' for r in items):
        raise ValueError('exact840 test items and60 units required')
    if {r['feature'] for r in items} != set(FEATURES) or [i for u in units for i in u['indices']] != list(range(840)):
        raise ValueError('registered rows and canonical once-only unit order required')
    if sha(a.inputs/'INPUT_SEAL.json') != read(ROOT/PLAN)['input_seal_sha256']:
        raise ValueError('inputs differ from the frozen plan')
    g = Gate(a.assignment, {k: len(units) for k in PATHS})
    if g.assignment.get('assets_sha256') != sha(a.assets) or g.assignment.get('input_seal_sha256') != sha(a.inputs/'INPUT_SEAL.json'):
        raise ValueError('assignment asset/input mismatch')
    a.out.mkdir(parents=True, exist_ok=False); g.out = a.out; g.write_state()
    status = execute(a, g); print('HANDOFF E18', status, a.out/'SCORE_SEAL.json')
    if status != 'COMPLETE': raise SystemExit(2)


if __name__ == '__main__': main()
