"""E96 one-item reconstructor smoke; consumes sealed greedy text, never samples.

Input directory: INPUT_SEAL.json hashes exactly item.json, h44.npy, h42.npy.
item.json: id, oracle_text, nla_text, source_seals (nonempty SHA256 list).
Each activation is float [1,5120]. Supply already staged, pinned asset manifests.
Run in an exclusively admitted one-GPU allocation with an external pod hardstop.
The deadline may be at most 1,800 s after allocation creation; staging and loading
consume that same allowance. The worker watchdog receives only remaining time.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

DECODER_WRAPPER_SOURCE_SHA256 = '31f447d4cb2681d10f4e4ef89199e412ad330cf6e7a5f846f9014449543bf3ac'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


def inputs(root):
    import numpy as np
    seal = json.loads((root / 'INPUT_SEAL.json').read_text())
    names = {'item.json', 'h44.npy', 'h42.npy'}
    if set(seal['files']) != names:
        raise ValueError('input seal must contain exactly the three label-free input files')
    if {p.name for p in root.iterdir()} != names | {'INPUT_SEAL.json'}:
        raise ValueError('extra files in label-free smoke input directory')
    for name, expected in seal['files'].items():
        if digest(root / name) != expected:
            raise ValueError('input hash mismatch: ' + name)
    item = json.loads((root / 'item.json').read_text())
    if set(item) != {'id', 'oracle_text', 'nla_text', 'source_seals'}:
        raise ValueError('item schema mismatch; labels/answers are forbidden')
    if any(not isinstance(item[k], str) or not item[k].strip()
           for k in ('id', 'oracle_text', 'nla_text')):
        raise ValueError('nonempty sealed ID and greedy text required')
    if not isinstance(item['source_seals'], list) or not item['source_seals']:
        raise ValueError('source seal provenance required')
    for value in item['source_seals']:
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('source seals must be SHA256 strings')
    acts = {}
    for reader, filename in [('oracle', 'h44.npy'), ('nla', 'h42.npy')]:
        x = np.load(root / filename, allow_pickle=False)
        if x.shape != (1, 5120) or not np.issubdtype(x.dtype, np.floating) or not np.isfinite(x).all() or np.linalg.norm(x) == 0:
            raise ValueError('invalid one-item activation: ' + reader)
        acts[reader] = x.astype('float32')
    return item, acts


def check_prediction(pred, gold):
    import numpy as np
    p = pred.detach().float().cpu().numpy()
    if p.shape != (1, 5120) or not np.isfinite(p).all() or np.linalg.norm(p) == 0:
        raise ValueError('invalid reconstruction: finite nonzero [1,5120] required')
    p64, g64 = p.astype('float64'), gold.astype('float64')
    raw = float(np.square(p64 - g64).mean())
    normalized = float(np.square(p64 / np.linalg.norm(p64) - g64 / np.linalg.norm(g64)).sum())
    if not np.isfinite([raw, normalized]).all():
        raise ValueError('nonfinite reconstruction error')
    return p, {'shape': list(p.shape), 'raw_mse': raw,
               'unit_scaled_mse': normalized, 'norm': float(np.linalg.norm(p64))}


def pinned_heads(oracle_manifest, nla_manifest):
    expected = {
        'ar_ptag_pooled/heads.pt': '9f4cb6d193679c8683d7b49c8d2821c71567b3fc720baa73d7dbddb95f4c2179',
        'ar_ptag_pooled/lora/adapter_model.safetensors': 'd90bb9df02c352ef19f28536374e4a333e6dae8a103ba37d9e1c4e5183654e8a',
        'ar_reconstructor/value_head.safetensors': '8693094f0ec375b6c649255bd1a392487ea0e7b6faffab5c01c5518928b4b20c',
        'ar_reconstructor/model.safetensors': 'a2f64fcf22d0013411eae279e4a6e6d34a8c01aafb49a474c0ea82aebe4619df',
    }
    records = []
    for path in (oracle_manifest, nla_manifest):
        records.extend(json.loads(path.read_text())['files'])
    for suffix, sha in expected.items():
        matches = [r for r in records if r['path'].endswith('/' + suffix)]
        if len(matches) != 1 or matches[0]['sha256'] != sha:
            raise ValueError('reconstructor checkpoint pin mismatch: ' + suffix)


def load_decoder_only(assets_path):
    """Minimal wrapper copied from understand/worker.py in wt-wmech.

    Original source file SHA256 is DECODER_WRAPPER_SOURCE_SHA256. The actual math and checkpoint
    loading remain in the vendored mats.readers.nla module. No AV is loaded.
    """
    import common  # Adds the repository's vendored mats source to sys.path.
    import yaml
    from transformers import AutoTokenizer
    from projects.g_agreement.blindspot.run import _assets
    from mats.readers.nla import _load_ar, NLA
    root = Path(_assets(assets_path, ('nla',))['nla'])
    meta = yaml.safe_load((root / 'nla_meta.yaml').read_text())
    tok = AutoTokenizer.from_pretrained(root / 'av_base', local_files_only=True)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    ar, head = _load_ar(root, 'cuda')
    return NLA(av=None, tok=tok, ar=ar, value_head=head, meta=meta,
               prompt_ids=[], marker=0, device='cuda')


def dependency_preflight():
    """Import every local runtime dependency without loading model weights."""
    import common
    import numpy
    import torch
    import yaml
    import transformers
    from safetensors.torch import load_file
    from projects.g_agreement.blindspot.run import _assets
    from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
    from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
    from mats.readers.nla import _load_ar, NLA
    import inspect
    paths = {Path(inspect.getfile(fn)).resolve() for fn in
             (_assets, ar_assets, load_reconstructor, reconstruct, _load_ar, NLA)}
    return {str(path): digest(path) for path in sorted(paths)}


def remaining_budget(created, deadline, now):
    if not all(math.isfinite(x) for x in (created, deadline, now)):
        raise ValueError('allocation timestamps must be finite')
    if created > now or not 0 < deadline - created <= 1800:
        raise ValueError('deadline must fit the allocation-wide 1800-second cap')
    if deadline <= now:
        raise ValueError('allocation deadline already expired')
    return deadline - now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'oracle-assets', 'nla-assets', 'official', 'whitener', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--allocation-created-epoch', type=float, required=True)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    a = parser.parse_args()
    remaining = remaining_budget(a.allocation_created_epoch, a.deadline_epoch, time.time())
    a.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()

    # Separate process: the cap still fires if a native/CUDA call holds the GIL.
    # Pipe EOF ends the watchdog if this process exits or is killed early.
    read_fd, write_fd = os.pipe()
    watchdog_code = '''import json,os,select,signal,sys,time
fd,pid=int(sys.argv[1]),int(sys.argv[2])
ready,_,_=select.select([fd],[],[],max(0,float(sys.argv[4])-time.time()))
if not ready:
    with open(sys.argv[3],'w') as f:
        json.dump({'status':'INCOMPLETE_TIMEOUT','cap_seconds':1800},f)
    os.kill(pid,signal.SIGKILL)
'''
    watchdog = subprocess.Popen([sys.executable, '-c', watchdog_code, str(read_fd),
                                 str(os.getpid()), str(a.out / 'TIMEOUT.json'), str(a.deadline_epoch)], pass_fds=(read_fd,))
    os.close(read_fd)
    report = {'status': 'INCOMPLETE', 'generation_calls': 0, 'gpu_cap_seconds': 1800,
              'allocation_created_epoch': a.allocation_created_epoch,
              'deadline_epoch': a.deadline_epoch, 'remaining_seconds_at_start': remaining,
              'external_pod_hardstop_required': True,
              'readers': {}, 'source_sha256': digest(__file__)}
    try:
        import numpy as np
        import torch
        report['runtime_dependency_hashes'] = dependency_preflight()
        from projects.g_agreement.blindspot.run import _assets
        from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
        from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        pinned_heads(a.oracle_assets, a.nla_assets)
        item, acts = inputs(a.inputs)
        report.update(item_id=item['id'], source_seals=item['source_seals'],
                      input_seal_sha256=digest(a.inputs / 'INPUT_SEAL.json'),
                      oracle_assets_sha256=digest(a.oracle_assets), nla_assets_sha256=digest(a.nla_assets))
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError('exactly one visible CUDA GPU required')
        assets = _assets(a.oracle_assets, ('model',))
        ar_assets(a.oracle_assets, ('ar',))
        ar, tok, ruler = load_reconstructor(a.official, a.whitener, assets['ar'], assets['model'])
        pred = reconstruct(ar, tok, [item['oracle_text']])
        p, metrics = check_prediction(pred, acts['oracle'])
        np.save(a.out / 'oracle_reconstruction.npy', p, allow_pickle=False)
        report['readers']['oracle'] = dict(status='PASS', layer=44, **metrics)
        write(a.out / 'REPORT.json', report)
        del ar, tok, ruler, pred
        gc.collect()
        torch.cuda.empty_cache()
        decoder = load_decoder_only(a.nla_assets)
        pred = decoder.reconstruct([item['nla_text']], batch=1)
        p, metrics = check_prediction(pred, acts['nla'])
        np.save(a.out / 'nla_reconstruction.npy', p, allow_pickle=False)
        report['readers']['nla'] = dict(status='PASS', layer=42, **metrics)
        del decoder, pred
        gc.collect()
        torch.cuda.empty_cache()
        report['status'] = 'PASS'
    except Exception as exc:
        # A staging/access/load error is not proof the public reconstructor is absent.
        report.update(status='INCOMPLETE', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        write(a.out / 'REPORT.json', report)
        files = {p.name: digest(p) for p in a.out.iterdir() if p.is_file() and p.name != 'SCORE_SEAL.json'}
        write(a.out / 'SCORE_SEAL.json', {'status': report['status'], 'files': files})
        os.close(write_fd)
        watchdog.wait(timeout=5)


if __name__ == '__main__':
    main()
