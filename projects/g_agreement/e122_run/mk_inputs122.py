"""mk_inputs122.py <out_dir> : E122 public pod inputs (§232 E122 790dd6136; addition 2 e3d957076) + CPU-only private join.
Sources (all verified): W-text CONTRASTS_SEAL 23c9b0f8 at 713cbdeda; E85 package INPUT_SEAL 114e18fb (items, the input seal bound by the
E85 final binding); E85 a2 verified block-44 capture STAGE_SEAL (acts44.npy, POSITIONS, items.order); E85 LABELS.PRIVATE 5ed31188 (CPU only).
(a) every one of the 600 items unpatched (condition 0), all four contrasts. (b) test quartets only: per genre, the unaddressed item's block-44
read-token residual is replaced by its addressed twin's (T) or by a same-condition (addressed, same genre) donor from another test quartet (S),
donors = cyclic shift of a seed-20261030 permutation of the 100 test quartets, drawn for genre 0 then genre 1 (a derangement by construction).
candidate_ids per contrast = [positive, negative] token ids exactly as frozen; c = score(positive) - score(negative) is computed by the adapter.
No labels, cells or pairing on the pod: item ids are opaque; the join is written only to <out_dir>/cpu_only."""
import hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
A = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers'); PUB = Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_pub/wt-pub')
PKG = A/'wt-wmech/cache/g_agreement/understand/e85_runner_v1/package/inputs'; CAP = A/'wt-i2/cache/g_agreement/i2/parallel_operators/e85-a2/verified_capture'
LAB = A/'wt-wtext/results/g_agreement/understand/e85/cache/bank_2026-10-28_v1/LABELS.PRIVATE.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def req(ok, m):
    if not ok: sys.exit('FAIL: '+m)
def show(c, p): return subprocess.check_output(['git', 'show', c+':'+p], cwd=PUB)
out = Path(sys.argv[1]); req(not out.exists(), 'once: out exists'); (out/'inputs').mkdir(parents=True); (out/'cpu_only').mkdir()
CR = 'results/g_agreement/understand/e122/'; cs = show('713cbdeda', CR+'CONTRASTS_SEAL.json'); req(hashlib.sha256(cs).hexdigest().startswith('23c9b0f8'), 'contrast seal 23c9b0f8')
cseal = json.loads(cs); req(cseal['status'] == 'FROZEN_BEFORE_E122_CAPTURE', 'frozen')
for k, h in cseal['files'].items(): req(hashlib.sha256(show('713cbdeda', CR+k)).hexdigest() == h, 'contrast member '+k)
C = json.loads(show('713cbdeda', CR+'CONTRASTS.json')); req(C['experiment'] == 'E122' and len(C['contrasts']) == 4, '4 contrasts')
cand = [[c['positive']['token_ids'], c['negative']['token_ids']] for c in C['contrasts']]
req(all(c and all(type(t) is int for t in c) for p in cand for c in p), 'token ids')
pseal = json.loads((PKG/'INPUT_SEAL.json').read_text()); req(sha(PKG/'INPUT_SEAL.json').startswith('114e18fb'), 'E85 package seal 114e18fb')
for k, h in pseal['files'].items(): req(sha(PKG/k) == h, 'package member '+k)
items = json.loads((PKG/'items.json').read_text()); by = {x['id']: x for x in items}; req(len(by) == 600, '600 items')
st = json.loads((CAP/'STAGE_SEAL.json').read_text()); req(st['experiment'] == 'E85' and st['stage'] == 'capture' and st['status'] == 'COMPLETE' and st['synthetic'] is False, 'capture seal')
for k, h in st['files'].items(): req(sha(CAP/k) == h, 'capture member '+k)
order = json.loads((CAP/'items.order.json').read_text()); pos = {p['id']: p['read_index'] for p in json.loads((CAP/'POSITIONS.json').read_text())}
acts = np.load(CAP/'acts44.npy'); req(acts.shape == (600, 5120) and set(order) == set(by), 'acts44 600 x 5120 on the package ids')
row = {i: n for n, i in enumerate(order)}
req(all(pos[i] == len(by[i]['ids'])-1 == by[i]['read_index'] for i in by), 'read token = last prompt token (frozen prefix rule)')
labels = json.loads(LAB.read_text()); req(sha(LAB).startswith('5ed31188') and len(labels) == 600, 'labels 5ed31188')
L = {x['public_id']: x for x in labels}; req(set(L) == set(by) and all(L[i]['ids'] == by[i]['ids'] and L[i]['split'] == by[i]['split'] for i in by), 'labels join package exactly')
Qd = {}
for i, x in L.items(): Qd.setdefault(x['matched_set'], {})[(x['genre'], x['addressed'])] = i
req(len(Qd) == 150 and all(len(v) == 4 for v in Qd.values()), '150 quartets of 4 cells')
split = {m: {L[i]['split'] for i in v.values()} for m, v in Qd.items()}; req(all(len(s) == 1 for s in split.values()), 'quartet split uniform')
test = sorted(m for m in Qd if split[m] == {'test'}); dev = sorted(m for m in Qd if split[m] == {'dev'}); req(len(test) == 100 and len(dev) == 50, '50 dev / 100 test')
oid = lambda *k: hashlib.sha256(json.dumps(['E122', *k]).encode()).hexdigest()[:24]
pub, join, vec = [], [], []
def item(i, cond, vi, donor):
    x = dict(id=oid(i, cond, donor), inventory_id=oid('inv', i), base_id=i, row='e122', block=44, condition=cond, ids=by[i]['ids'], read_index=by[i]['read_index'],
             candidate_ids=cand, vector_index=vi, donor_id=None if donor is None else oid('donor', donor))
    pub.append(x); return x['id']
for m in sorted(Qd):
    for (g, a), i in sorted(Qd[m].items()):
        join.append(dict(id=item(i, '0', None, None), part='a', matched_set=m, genre=g, addressed=a, split=split[m].pop() if False else sorted(split[m])[0], public_id=i))
rng = np.random.default_rng(20261030); donors = {}
for g in (0, 1):
    p = [test[k] for k in rng.permutation(len(test))]; donors[g] = {p[k]: p[(k+1) % len(p)] for k in range(len(p))}
    req(all(d != m for m, d in donors[g].items()), 'derangement')
for m in test:
    for g in (0, 1):
        r_ = Qd[m][(g, 0)]
        for cond, src in (('T', Qd[m][(g, 1)]), ('S', Qd[donors[g][m]][(g, 1)])):
            vec.append(acts[row[src]]); j = item(r_, cond, len(vec)-1, src)
            join.append(dict(id=j, part='b', condition=cond, matched_set=m, genre=g, recipient_public_id=r_, donor_public_id=src, donor_matched_set=m if cond == 'T' else donors[g][m], split='test'))
req(len({x['id'] for x in pub}) == len(pub) == 600+400, '1000 unique items')
(out/'inputs'/'items.json').write_text(json.dumps(pub)); np.save(out/'inputs'/'vectors.npy', np.asarray(vec, np.float32))
files = {k: sha(out/'inputs'/k) for k in ('items.json', 'vectors.npy')}
(out/'inputs'/'INPUT_SEAL.json').write_text(json.dumps(dict(experiment='E122', labels_on_pod=False, files=files, contrasts_seal_sha256=hashlib.sha256(cs).hexdigest(),
    contrast_order=[c['id'] for c in C['contrasts']], candidate_order='[positive, negative]', parts={'a_unpatched': 600, 'b_T': 200, 'b_S': 200}, block=44), indent=1, sort_keys=True)+'\n')
srcs = dict(contrasts_seal=hashlib.sha256(cs).hexdigest(), contrasts_commit='713cbdeda', e85_package_input_seal=sha(PKG/'INPUT_SEAL.json'), e85_capture_stage_seal=sha(CAP/'STAGE_SEAL.json'), e85_labels=sha(LAB), donor_seed=20261030)
(out/'cpu_only'/'JOIN.PRIVATE.json').write_text(json.dumps(dict(sources=srcs, records=join), indent=1, sort_keys=True)+'\n')
(out/'cpu_only'/'JOIN_SEAL.json').write_text(json.dumps(dict(experiment='E122', files={'JOIN.PRIVATE.json': sha(out/'cpu_only'/'JOIN.PRIVATE.json')}, input_seal_sha256=sha(out/'inputs'/'INPUT_SEAL.json'), sources=srcs), indent=1, sort_keys=True)+'\n')
print(json.dumps(dict(input_seal=sha(out/'inputs'/'INPUT_SEAL.json'), join_seal=sha(out/'cpu_only'/'JOIN_SEAL.json'), items=len(pub), vectors=len(vec), sources=srcs)))
