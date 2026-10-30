"""E50 full-grid training worker. Run from repository root; all outputs go to cache/."""
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
        raise TimeoutError('E50 deadline reached; retain partials, no restart')


def arm_deadline(epoch):
    """Unix process alarm complements the Integrator's provider hardstop."""
    def timeout(_signum, _frame):
        raise TimeoutError('E50 nonresetting wall clock expired')
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


def audit_items(reader, kind, records):
    """§139: lengths, padding and frozen environment for each executed item."""
    context = getattr(reader, 'audit_context', None)
    if context is None:
        return
    path, metadata = context
    with path.open('a') as f:
        for record in records:
            f.write(json.dumps({**metadata, 'kind': kind, 'padding_side': 'right', **record}, sort_keys=True)+'\n')


def configure_audit(reader, out, assignment, **context):
    reader.audit_context = (out / 'ITEM_EXECUTION_AUDIT.jsonl', {
        'environment_sha256': assignment['training_environment_sha256'], **context})


def train_step(reader, batch, labels, acts, spec, optimizer, diagnostics=False):
    import torch
    device = next(reader.model.parameters()).device
    head, slot = reader.carrier(44)
    targets = [reader.tok.encode((spec[b['feature']] if 'feature' in b else spec)['olens'][b['phrasing']][0 if b['y'] else 1], add_special_tokens=False) for b in batch]
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
    audit_items(reader, 'training', [{'id': b['id'], 'input_length': len(head)+len(tail),
        'padding_tokens': n-len(head)-len(tail), 'batch_size': len(batch), 'phrasing': b['phrasing']}
        for b, tail in zip(batch, targets)])
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
    head, _ = reader.carrier(44)
    for phrasing, pair in enumerate(spec['olens']):
        lengths = [len(reader.tok.encode(v, add_special_tokens=False)) for v in pair]
        audit_items(reader, 'asked', [{'id': test[i]['id'], 'phrasing': phrasing, 'candidate': side,
            'input_length': len(head)+length, 'padding_tokens': max(lengths)-length,
            'activation_batch_size': min(16, len(indices)-(j//16)*16),
            'forward_batch_size': 2*min(16, len(indices)-(j//16)*16)}
            for j, i in enumerate(indices) for side, length in enumerate(lengths)])
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
            audit_items(reader, 'free', [{'id': test[i]['id'], 'input_length': len(head),
                'padding_tokens': 0, 'batch_size': len(indices[s:s+8]), 'max_new_tokens': 128,
                'min_new_tokens': 128 if force_cap else 0} for i in indices[s:s+8]])
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
    for items, acts in ((dev, devacts), (test, testacts)):
        expected_rows = C.STRUCTURE if items is dev else C.ROWS
        expected_n = len(expected_rows)*84
        if (len(items) != expected_n or len({r['id'] for r in items}) != expected_n
                or acts.shape != (expected_n, 5120) or not np.isfinite(acts).all()
                or any(sum(r['feature']==row for r in items)!=84 for row in expected_rows)):
            raise ValueError('complete finite registered pooled-dev/all-row-test input required')
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
            or reference.get('original_e28_input_seal_sha256') != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['original_e28_input_seal_sha256']):
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
    from secondary import load_secondary
    assignment=C.assignment(C.read(a.assignment));out=C.cache_output(a.out)
    C.dump(out/'assignment.json',assignment)
    science_started=None;status='INCOMPLETE';environment_ready=False
    try:
        arm_deadline(min(assignment['provider_created_epoch']+2400,assignment['deadline_epoch']-180))
        check_source(assignment)
        E.verify_manifest(a.environment_manifest,assignment['training_environment_sha256'])
        shutil.copyfile(a.environment_manifest,out/'TRAINING_ENVIRONMENT.json')
        assignment,mapping,assets,dev,test,devacts,testacts,specs=runtime_inputs(a)
        gate=parity_inputs(a.parity_inputs,assignment)
        secondary=load_secondary(a.secondary_input,assignment)
        C.dump(out/'SECONDARY_BINDING.json',assignment['secondary'])
        torch.manual_seed(C.SEED);torch.cuda.manual_seed_all(C.SEED)
        t=time.time();model,tok=load_base(assets,'L');load_s=time.time()-t
        reader=make_reader(model,tok);science_started=time.time()
        if science_started-assignment['provider_created_epoch']>2400:raise TimeoutError('setup cap exceeded')
        deadline=min(science_started+10800,assignment['deadline_epoch']-180);arm_deadline(deadline)
        configure_audit(reader,out,assignment,phase='parity',step=0)
        parity_gate(reader,gate,a.parity_inputs,out,assignment,assignment['training_environment_sha256'],lambda:check_time(assignment,deadline))
        split=assignment['runs'][0][0]
        schedule=C.training_schedule(dev,split,'L');devindex={r['id']:i for i,r in enumerate(dev)}
        mounted,parameters=attach_lowrank(model,mapping);opt=optimizer_for(parameters)
        configure_audit(reader,out,assignment,phase='warmup')
        diagnostics=train_step(reader,schedule[0],devindex,devacts,specs,opt,diagnostics=True)
        C.dump(out/'ENVIRONMENT_RUNTIME_RESULT.json',E.runtime_ready(diagnostics,reader.device,time.time(),assignment['training_environment_sha256'],C.sha(out/'PARITY_RESULT.json')))
        environment_ready=True;samples=[]
        for batch in schedule[1:5]:
            check_time(assignment,deadline);t=time.time();train_step(reader,batch,devindex,devacts,specs,opt);samples.append(time.time()-t)
        timing_specs=dict(specs)
        if secondary:timing_specs.update(secondary[2])
        warm_row=max(timing_specs,key=lambda f:max(len(tok.encode(x,add_special_tokens=False)) for pair in timing_specs[f]['olens'] for x in pair))
        train_row=C.plan()['splits'][split]['train'][0]
        ix=[i for i,r in enumerate(dev) if r['feature']==train_row]
        surrogate=[{'id':dev[i]['id'],'feature':warm_row} for i in ix]
        t=time.time();score(reader,surrogate,devacts[ix],timing_specs[warm_row],warm_row);asked_s=time.time()-t
        t=time.time();free(reader,surrogate,devacts[ix],warm_row,force_cap=True,deadline_check=lambda:check_time(assignment,deadline));free_s=time.time()-t
        detach_lowrank(mounted);del opt,parameters,mounted
        gc.collect();torch.cuda.empty_cache()
        # Both complete arms, all 25 asked rows, three post-L W1 rows, 16 free rows.
        remaining=800*max(samples)+(53+(11 if secondary else 0))*asked_s+16*free_s+120
        forecast={'status':'WARMED_FORECAST','plan_sha256':C.sha(C.HERE/'PLAN.json'),
            'science_started_epoch':science_started,'provider_deadline_epoch':assignment['deadline_epoch'],
            'forecast_remaining_seconds':remaining,'train_step_samples_seconds':samples,'asked_84_seconds':asked_s,
            'free_84_cap128_seconds':free_s,'load_seconds_in_elapsed':load_s,'longest_target_row':warm_row,
            'warmup_updates_discarded':5,'input_seal_sha256':assignment['input_seal_sha256']}
        C.dump(out/'FORECAST.json',forecast)
        admission=C.forecast_admission(forecast,time.time());C.dump(out/'ADMISSION.json',admission)
        if admission['status']!='ADMIT_FULL_GRID':status='NO_FIT_STOP';return 2
        deadline=admission['science_deadline_epoch'];arm_deadline(deadline)
        for split,arm in assignment['runs']:
            torch.manual_seed(C.SEED);torch.cuda.manual_seed_all(C.SEED)
            mounted,parameters=attach_lowrank(model,mapping);opt=optimizer_for(parameters)
            folder=out/(split+'__'+arm);folder.mkdir()
            schedule=C.training_schedule(dev,split,arm);C.dump(folder/'SCHEDULE.json',schedule)
            for step,batch in enumerate(schedule,1):
                check_time(assignment,deadline)
                configure_audit(reader,out,assignment,phase='production',split=split,arm=arm,step=step)
                loss=train_step(reader,batch,devindex,devacts,specs,opt)
                with (folder/'train.jsonl').open('a') as f:f.write(json.dumps({'step':step,'loss':loss,'epoch':time.time()})+'\n')
            for row in C.ROWS:
                check_time(assignment,deadline)
                C.jsonl(folder/(row+'.asked.jsonl'),score(reader,test,testacts,specs[row],row))
            for row in C.plan()['splits'][split]['heldout']:
                check_time(assignment,deadline)
                C.jsonl(folder/(row+'.free.jsonl'),free(reader,test,testacts,row,deadline_check=lambda:check_time(assignment,deadline)))
            if arm=='L':
                pitems,_,pspec,pacts,_=gate
                for row in PARITY_ROWS:
                    check_time(assignment,deadline)
                    C.jsonl(folder/(row+'.w1post.jsonl'),score(reader,pitems,pacts,pspec[row],row))
                if secondary:
                    sitems,sacts,sspec=secondary
                    for row in sspec:
                        check_time(assignment,deadline)
                        C.jsonl(folder/(row+'.e49.jsonl'),score(reader,sitems,sacts,sspec[row],row))
            torch.save({n:p.detach().cpu() for n,p in model.named_parameters() if p.requires_grad},folder/'adapter.pt')
            C.seal(folder,'SCORE_SEAL.json')
            detach_lowrank(mounted);del opt,parameters,mounted
            gc.collect();torch.cuda.empty_cache()
        check_time(assignment,deadline);status='COMPLETE_FULL_ASSIGNED_GRID'
    except ParityFailed:
        status='PARITY_FAILED_STOP';raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        C.dump(out/'RUN_RECEIPT.json',{'experiment':'E50','status':status,'gpu_seconds_provider':time.time()-assignment['provider_created_epoch'],
            'science_started_epoch':science_started,'test_labels_opened':False,'plan_sha256':C.sha(C.HERE/'PLAN.json'),
            'parity_input_seal_sha256':assignment.get('parity_input_seal_sha256'),'retry_authorized':False,
            'environment_ready':environment_ready,**{k:C.sha(out/n) for n,k in {
                'TRAINING_ENVIRONMENT.json':'environment_manifest_sha256','ENVIRONMENT_RUNTIME_RESULT.json':'environment_runtime_result_sha256',
                'PARITY_RESULT.json':'parity_result_sha256','PARITY_SCORES.jsonl':'parity_scores_sha256'}.items() if (out/n).is_file()}})
        C.seal(out,'OUTPUT_SEAL.json',sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'))
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('assignment','mapping','input','assets','out','environment-manifest','parity-inputs'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--secondary-input',type=Path)
    args=p.parse_args();os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    raise SystemExit(run(args))
