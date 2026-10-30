"""E122 pod worker (Integrator Q; §232 E122, addition 2 e3d957076). Copy of worker105 (E105 supplied-vector logits runner);
scoring is the frozen projects.g_agreement.e105.scoring (87145590, sha c4f9daed), called unchanged. Base model only, no readers, no judging.
One public input set: part (a) unpatched condition-0 items and part (b) T/S supplied block-44 vectors. No labels/cells on the pod;
the cell and pairing join stays CPU-side. Outputs are sealed unopened (addition 2).

Model loading, timing, custody and sealing belong to the integrator (W-mechanism-B README); scoring is W-mechanism-B's
frozen adapter (projects.g_agreement.e105.scoring), called unchanged.
- §217 rule 4: timing and production on one pod. The first batch of every (row, patched/unpatched) stratum is timed
  and discarded; the forecast is the measured per-item rate times that stratum's items. Production continues only if
  now + 1.25 x forecast + RETRIEVAL fits the creation deadline; otherwise NO_FIT, sealed, and the pod is a timing pod.
- Inputs: each row's INPUT_SEAL member hashes are verified before the model loads. No labels exist on the pod.
- Assets: the model asset check is a copy of blindspot.run._assets restricted to 'model', so the pod needs no common/.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROWS = ('e122',)
MARGIN, RETRIEVAL = 1.25, 120


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, x): Path(p).write_text(json.dumps(x, indent=1, sort_keys=True)+'\n')
def require(ok, msg):
    if not ok: raise ValueError(msg)
def now_iso(): return datetime.now(timezone.utc).isoformat()


def load_inputs(root):
    rows = {}
    for r in ROWS:
        d = Path(root)/'inputs';seal = read(d/'INPUT_SEAL.json')
        require(seal.get('experiment') == 'E122' and seal.get('labels_on_pod') is False, 'E122 public input seal: '+r)
        for name, digest in seal['files'].items(): require(sha(d/name) == digest, 'input hash: '+r+'/'+name)
        items = read(d/'items.json');require(items and {x['row'] for x in items} == {r}, 'row identity: '+r)
        rows[r] = dict(items=items, vectors=np.load(d/'vectors.npy'), seal_sha256=sha(d/'INPUT_SEAL.json'))
    return rows


def check_model_asset(path):
    """blindspot.run._assets for names=('model',): revision, full file coverage, per-file and tokenizer hashes."""
    a = read(path);pinned = read(ROOT/'projects/g_agreement/manifest/assets.json')
    require(Path(a['model']).exists(), 'missing local model')
    require(a.get('revisions', {}).get('model') == pinned['target']['revision'], 'asset revision differs from registration: model')
    require(a.get('files'), 'asset file hashes required')
    actual = {}
    for item in a['files']:
        p = Path(item['path'])
        if str(p.resolve()).startswith(str(Path(a['model']).resolve())):
            require(sha(p) == item['sha256'], 'asset hash mismatch');actual[str(p.resolve())] = item['sha256']
    required = {str(p.resolve()) for p in Path(a['model']).rglob('*') if p.is_file()}
    require(required <= set(actual), 'asset hash manifest lacks file coverage')
    require(actual.get(str((Path(a['model'])/'tokenizer.json').resolve())) == pinned['target']['files_needed']['tokenizer.json_sha256'],
            'asset differs from registered SHA256: tokenizer.json')
    return a['model'], sha(path)


def load_model(model_dir):
    import torch
    from transformers import AutoModelForCausalLM
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1, 'one CUDA device')
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, device_map='cuda', local_files_only=True).eval()
    return model, torch.cuda.get_device_name(0)


def plan(rows, S):
    """[(row, baseline, [item indices])] in frozen scoring.batches order per row."""
    out = []
    for r in ROWS:
        items = rows[r]['items']
        for b in S.batches(items):out.append((r, items[b[0]]['condition'] == '0', b))
    return out


def run(args, S, load=load_model, clock=time.time):
    out = Path(args.out);require(not out.exists(), 'once only: output exists');(out/'jobs').mkdir(parents=True)
    t0 = clock();phases = []
    def mark(name, start, n=None): phases.append(dict(phase=name, seconds=round(clock()-start, 3), items=n))
    s = clock();rows = load_inputs(args.root);mark('input_verify', s)
    s = clock();model_dir, assets_sha = check_model_asset(args.assets) if args.assets else (None, None);mark('asset_verify', s)
    s = clock();model, gpu = load(model_dir);mark('model_setup', s)
    jobs = plan(rows, S)
    first = rows[ROWS[0]];x = dict(first['items'][jobs[0][2][0]]);x.update(condition='T', vector_index=0, donor_id='warmup')
    s = clock();S.score_batch(model, [x], np.random.default_rng(20261028).standard_normal((1, first['vectors'].shape[1])).astype(np.float32))
    mark('warmup_discarded', s)
    rate = {};total = {}
    for r, base, b in jobs:total[(r, base)] = total.get((r, base), 0)+len(b)
    for r, base, b in jobs:
        if (r, base) in rate:continue
        s = clock();S.score_batch(model, [rows[r]['items'][i] for i in b], rows[r]['vectors']);dt = clock()-s
        rate[(r, base)] = dt/len(b);phases.append(dict(phase=f'timing_discarded:{r}:{"0" if base else "TS"}', seconds=round(dt, 3), items=len(b)))
    forecast = sum(rate[k]*n for k, n in total.items())
    remaining = args.deadline-clock();need = MARGIN*forecast+RETRIEVAL
    profile = dict(forecast_production_seconds=round(forecast, 1), need_seconds=round(need, 1), remaining_seconds=round(remaining, 1),
                   per_item_seconds={f'{r}:{"0" if b else "TS"}': round(v, 4) for (r, b), v in rate.items()}, phases=phases)
    write(out/'MEASURED_PROFILE.json', profile)
    status = 'NO_FIT'
    if need <= remaining:
        done = 0
        for k, (r, base, b) in enumerate(jobs):
            if clock() > args.deadline-RETRIEVAL:status = 'TIMEOUT_PARTIAL';break
            res = S.score_batch(model, [rows[r]['items'][i] for i in b], rows[r]['vectors'])
            write(out/'jobs'/f'{k:04d}_{r}.json', dict(row=r, baseline=base, indices=b, records=res));done += len(b)
        else:status = 'COMPLETE'
        phases.append(dict(phase='production', seconds=round(clock()-t0-sum(p['seconds'] for p in phases), 3), items=done))
    else:write(out/'NO_FIT.json', profile)
    files = sorted(out.rglob('*.json'), key=lambda p: p.stat().st_mtime_ns)
    js = [p for p in files if p.parent.name == 'jobs']
    seal = dict(experiment='E122', status=status, gpu_name=gpu, assets_sha256=assets_sha, deadline_epoch=args.deadline,
                input_seals={r: rows[r]['seal_sha256'] for r in ROWS}, evaluations=sum(len(rows[r]['items']) for r in ROWS),
                first_output_utc=(datetime.fromtimestamp(js[0].stat().st_mtime, timezone.utc).isoformat() if js else 'none'),
                first_output_evidence=(dict(member=str(js[0].relative_to(out)), sha256=sha(js[0]), source='file mtime') if js else None),
                sealed_utc=now_iso(), files={str(p.relative_to(out)): sha(p) for p in files})
    write(out/'OUTPUT_SEAL.json', seal)
    return seal


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True);p.add_argument('--assets');p.add_argument('--out', required=True)
    p.add_argument('--deadline', type=float, help='pod creation epoch + cap (fixed custody)')
    p.add_argument('--assignment', help='integrator assignment.json; its absolute_deadline_epoch (created + cap) is the deadline')
    a = p.parse_args();sys.path.insert(0, str(ROOT))
    if a.assignment:
        x = read(a.assignment);require(x['experiment'] == 'E122' and a.deadline is None, 'one deadline source');a.deadline = float(x['absolute_deadline_epoch'])
    require(a.deadline is not None, 'deadline required')
    from projects.g_agreement.e105 import scoring as S
    require(a.assets, 'assets required on a pod')
    print(json.dumps({k: v for k, v in run(a, S).items() if k != 'files'}))


if __name__ == '__main__':main()
