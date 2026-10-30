"""E35 clarified decomposition, 2026-10-25; production analysis is once-only.

The Integrator's later decomposition launch binds raw input provenance, the
passed SAE checkpoint and its budget. This module freezes encoding/statistics;
it does not create a GPU pod, call a judge, or manufacture missing AR inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from gate_inputs import dump_new, sha
from decomp_math import (latent_share_sparse, paired_ratio, row_cluster_analysis,
                         frequency_matched_masks, control_summary)
from latent_labels import (structure_mask, cohen_kappa, validate_key,
                           validate_annotations, select_top_latents, validate_label_custody)
from decomp_probes import validate_production_metadata, run_per_row_probes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FREEZE_NAME = 'DECOMPOSITION_FREEZE.20261025.json'
PRIMARY = ('h', 'window_loss', 'policy_loss')
DESCRIPTIVE = ('window_code_difference_positive', 'policy_code_difference_positive')
SAMPLE_SHA = 'dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593'


def read(path):
    return json.loads(Path(path).read_text())


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def verify_seal(folder, filename, required=()):
    folder = Path(folder).resolve()
    record = read(folder / filename)
    pins = record.get('files', {})
    if not isinstance(pins, dict) or not set(required) <= set(pins):
        raise ValueError('complete sealed artifact files required')
    for name, expected in pins.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha(path) != expected:
            raise ValueError('artifact checksum/path mismatch')
    return record


def verify_gate(gate_dir, gate_request, checkpoint_sha):
    """Validate the returned gate without repeating its registered evaluation."""
    gate_dir, gate_request = Path(gate_dir), Path(gate_request)
    seal = verify_seal(gate_dir, 'OUTPUT_SEAL.json', ('GATE_RESULT.json',))
    gate = read(gate_dir / 'GATE_RESULT.json')
    metrics = gate.get('metrics') or {}
    fvu, dead = metrics.get('fvu'), metrics.get('dead_fraction')
    numeric = lambda x: type(x) in (int, float) and np.isfinite(x)
    if (seal.get('status') != 'PASS' or gate.get('status') != 'PASS'
            or gate.get('experiment') != 'E35' or gate.get('stage') != 'gate'
            or metrics.get('passed') is not True or metrics.get('d_model') != 5120
            or metrics.get('n_tokens') != 50000 or not numeric(fvu) or not 0 <= fvu <= .25
            or not numeric(dead) or not 0 <= dead < .1
            or gate.get('sample_sha256') != SAMPLE_SHA
            or gate.get('request_sha256') != sha(gate_request)):
        raise ValueError('complete passing registered SAE gate required')
    # Existing transfer receipts bind the SAE through their sealed gate plan.
    # A later registered fallback receipt must bind its own checkpoint explicitly.
    if 'sae_checkpoint_sha256' in gate:
        if (gate['sae_checkpoint_sha256'] != checkpoint_sha or metrics.get('d_sae') != 16384
                or gate.get('sae_k') != 64 or not gate.get('normalization_manifest_sha256')):
            raise ValueError('fallback gate/checkpoint/normalization binding mismatch')
    else:
        request = read(gate_request)
        plan_path = HERE / 'GATE_PLAN.20261025.json'
        plan = read(plan_path)
        if (request.get('source_files', {}).get(plan_path.name) != sha(plan_path)
                or checkpoint_sha != plan['sae']['sha256'] or metrics.get('d_sae') != 81920):
            raise ValueError('transfer gate/checkpoint binding mismatch')
    return gate


def authorize_preparation(path):
    """Gate + source freeze only, for dev selection and blind context preparation."""
    a = read(path)
    if (a.get('issuer') != 'integrator' or a.get('experiment') != 'E35'
            or a.get('rubric_committed') is not True
            or not re.fullmatch(r'[0-9a-f]{40}', a.get('freeze_commit', ''))):
        raise ValueError('Integrator authorization with committed rubric required')
    freeze_path = HERE / FREEZE_NAME
    if sha(freeze_path) != a.get('freeze_sha256'):
        raise ValueError('frozen decomposition source mismatch')
    freeze = read(freeze_path)
    for name, digest in freeze['files'].items():
        p = (HERE / name).resolve()
        if not p.is_relative_to(HERE.resolve()) or sha(p) != digest:
            raise ValueError('frozen decomposition file changed')
    gate = verify_gate(a['gate_dir'], a['gate_request'], a['sae_checkpoint_sha256'])
    gate_sha = sha(Path(a['gate_dir']) / 'GATE_RESULT.json')
    if gate_sha != a.get('gate_result_sha256'):
        raise ValueError('authorized gate result mismatch')
    return dict(a, _preparation_validated=True, _gate=gate)


def authorize(path):
    """No production decomposition before gate PASS and frozen blind labels."""
    a = authorize_preparation(path)
    gate, gate_sha = a['_gate'], a['gate_result_sha256']
    labels = Path(a['labels_dir'])
    if sha(labels / 'LABEL_SEAL.json') != a.get('labels_seal_sha256'):
        raise ValueError('authorized blind labels mismatch')
    label_seal = verify_seal(labels, 'LABEL_SEAL.json',
                             ('primary.jsonl', 'secondary.jsonl', 'private_key.json',
                              'primary_payloads.json', 'secondary_payloads.json', 'DISPATCH.json'))
    expected = {'gate_result_sha256': gate_sha, 'freeze_sha256': a['freeze_sha256'],
                'rubric_sha256': sha(HERE / 'LATENT_RUBRIC.20261025.md'),
                'prompt_sha256': sha(HERE / 'BLIND_JUDGE_PROMPT.20261025.txt'),
                'sae_checkpoint_sha256': a['sae_checkpoint_sha256']}
    if label_seal.get('status') != 'COMPLETE' or any(label_seal.get(k) != v for k, v in expected.items()):
        raise ValueError('labels must be bound to passed SAE and committed blind rubric')
    key = read(labels / 'private_key.json')
    custody = validate_label_custody(read(labels / 'primary_payloads.json'),
                                    read(labels / 'secondary_payloads.json'), key,
                                    read(labels / 'DISPATCH.json'),
                                    rubric_sha256=expected['rubric_sha256'],
                                    prompt_sha256=expected['prompt_sha256'])
    mapping = validate_key(key)
    primary, secondary = jsonl(labels / 'primary.jsonl'), jsonl(labels / 'secondary.jsonl')
    validate_annotations(primary, sorted(mapping))
    validate_annotations(secondary, key['secondary_blind_ids'])
    return dict(a, _validated=True, _primary=primary, _secondary=secondary, _key=key,
                _gate=gate, _label_seal=label_seal, _label_custody=custody)


def encode_triplet(sae, h, r_win, r_ol, *, authorized=False):
    """Caller supplies the passed SAE's exact encoder, including its normalization.

    Primary errors are formed in raw residual space BEFORE each encoder call.
    The positive parts of differences between codes are separate descriptive arms.
    No AR whitening or decoder bias is applied to errors or latent norm shares.
    Call in bounded batches inside the Integrator's assigned decomposition run.
    """
    if authorized is not True:
        raise ValueError('gate/rubric authorization required before encoding')
    import torch
    if (h.ndim != 2 or h.shape != r_win.shape or h.shape != r_ol.shape
            or h.shape[0] == 0 or any(not torch.isfinite(x).all() for x in (h, r_win, r_ol))):
        raise ValueError('aligned finite raw h, R_win and R_ol required')
    with torch.inference_mode():
        def checked(z):
            if (z.ndim != 2 or z.shape != (len(h), sae.d_sae)
                    or not torch.isfinite(z).all() or (z < 0).any()):
                raise ValueError('finite nonnegative SAE code with passed dictionary width required')
            return z
        z_h, z_win, z_ol = sae.encode(h), sae.encode(r_win), sae.encode(r_ol)
        for z in (z_h, z_win, z_ol):
            checked(z)
        codes = {'h': z_h, 'window_loss': sae.encode(h - r_win),
                 'policy_loss': sae.encode(r_win - r_ol),
                 DESCRIPTIVE[0]: (z_h - z_win).clamp_min(0),
                 DESCRIPTIVE[1]: (z_win - z_ol).clamp_min(0)}
        result = {}
        for name, z in codes.items():
            checked(z)
            k = sae.k
            if (z.gt(0).sum(dim=1) > k).any():
                raise ValueError('code exceeds passed SAE sparsity')
            values, indices = torch.topk(z, k, dim=-1)
            result[name] = (indices.cpu().numpy(), values.float().cpu().numpy())
    return result


def decoder_column_norms(sae):
    """Compute ||d_i|| from the passed checkpoint's W_dec, excluding its bias.

    CPU float64 chunks fix accumulation precision without copying the complete
    5120 x 81920 dictionary to float64. The collector binds its loaded checkpoint
    digest and normalization manifest in the encoding seal.
    """
    import torch
    if tuple(sae.W_dec.shape) != (sae.d_model, sae.d_sae):
        raise ValueError('passed SAE decoder column shape required')
    answer = np.empty(sae.d_sae, dtype=np.float64)
    for start in range(0, sae.d_sae, 256):
        columns = sae.W_dec[:, start:start + 256].detach().to(device='cpu', dtype=torch.float64)
        if not torch.isfinite(columns).all():
            raise ValueError('finite decoder columns required')
        answer[start:start + len(columns.T)] = torch.linalg.vector_norm(columns, dim=0).numpy()
    return answer


def validate_metadata_provenance(metadata, originals, templates):
    """Join frozen W1 records; templates' first value is the positive class."""
    original_by_id = {x['id']: x for x in originals}
    if len(original_by_id) != len(originals) or len({x['id'] for x in metadata}) != len(metadata):
        raise ValueError('unique original and encoded W1 IDs required')
    for m in metadata:
        original = original_by_id.get(m['id'])
        if original is None:
            raise ValueError('item absent from frozen W1 bank')
        row = original['feature']
        values = templates.get(row, {}).get('values', [])
        if len(values) != 2 or values[0] == values[1] or original['value'] not in values:
            raise ValueError('exactly two distinct frozen W1 values required')
        if (m['row'] != row or m['split'] != original['split']
                or m['cluster'] != str(original['cluster'])
                or type(m['label']) is not int or m['label'] != int(original['value'] == values[0])):
            raise ValueError('encoded metadata differs from frozen W1 truth/row/cluster')


def dev_statistics(indices, values, metadata, n_latents):
    dev = np.array([m['split'] == 'dev' for m in metadata])
    ix, value = np.asarray(indices)[dev], np.asarray(values)[dev]
    fired = value > 0
    counts = np.bincount(ix[fired], minlength=n_latents)
    sums = np.bincount(ix.ravel(), weights=value.ravel(), minlength=n_latents)
    return counts, sums


def primary_report(codes, decoder_norms, mask, dev_counts, metadata):
    test = np.array([m['split'] == 'test' for m in metadata])
    rows = np.array([m['row'] for m in metadata])[test]
    controls = frequency_matched_masks(dev_counts, mask)

    def shares(name, selected):
        indices, values = codes[name]
        return latent_share_sparse(indices[test], values[test], decoder_norms, selected)

    baseline = shares('h', mask)
    baseline_null = np.stack([shares('h', selected) for selected in controls])
    result = {'primary_encoding': 'encode_raw_difference_directly', 'rules': {},
              'descriptive_code_differences': {}}
    for name, rule in (('window_loss', 'R1'), ('policy_loss', 'R2')):
        observed = shares(name, mask)
        report = row_cluster_analysis(observed, baseline, rows)
        null = np.stack([shares(name, selected) for selected in controls])
        report['frequency_matched_control'] = control_summary(null, baseline_null,
                                                               masks=controls, structure_mask=mask)
        report['term'] = name
        result['rules'][rule] = report
    for name in DESCRIPTIVE:
        result['descriptive_code_differences'][name] = dict(paired_ratio(shares(name, mask), baseline),
                                                         rule_applied=False)
    return result


def dominant_named_latents(codes, norms, metadata, primary, key, payloads):
    """Top ten labelled policy-code contributions in each registered state row."""
    mapping = validate_key(key)
    annotations = {mapping[x['blind_id']]: x for x in primary}
    contexts = {mapping[x['blind_id']]: x['contexts'] for x in payloads}
    if set(contexts) != set(annotations):
        raise ValueError('all named latent contexts required')
    indices, values = codes['policy_loss']
    named = sorted(annotations)
    result = {}
    for row in ('prose_paren', 'python_string', 'table_role'):
        selected = [i for i, m in enumerate(metadata) if m['split'] == 'test' and m['row'] == row]
        ix, mass = indices[selected], values[selected] * norms[indices[selected]]
        mean_mass = np.bincount(ix.ravel(), weights=mass.ravel(), minlength=len(norms)) / len(selected)
        ranked = sorted(named, key=lambda i: (-mean_mass[i], i))[:10]
        result[row] = [{'latent_index': i, 'label': annotations[i]['label'],
                        'short_name': annotations[i]['short_name'], 'mean_decoder_weighted_activation': float(mean_mass[i]),
                        'top_contexts': contexts[i]} for i in ranked]
    return result


def analyze_pack(pack, approval, out):
    """Production entry point. The guard is consumed before reading SAE codes."""
    if approval.get('_validated') is not True:
        raise ValueError('validated gate/rubric/label authorization required')
    pack, out = Path(pack), Path(out)
    guard = ROOT / 'cache/g_agreement/understand/e35/decomposition.analysis.RUN_ONCE.json'
    if not out.resolve().is_relative_to((ROOT / 'cache/g_agreement/understand/e35').resolve()):
        raise ValueError('production analysis outputs must stay in E35 cache')
    if guard.exists() or out.exists():
        raise FileExistsError('analysis guard or output already exists')
    required = ('items.json', 'codes.npz', 'decoder_norms.npy', 'items.DO_NOT_STAGE.jsonl',
                'items.input.jsonl', 'templates.json', 'dev_ids.json', 'test_ids.json')
    receipt = verify_seal(pack, 'ENCODING_SEAL.json', required)
    for field in ('freeze_sha256', 'gate_result_sha256', 'labels_seal_sha256', 'sae_checkpoint_sha256'):
        if receipt.get(field) != approval[field]:
            raise ValueError('encoding cache authorization mismatch')
    if receipt.get('primary_encoding') != 'encode_raw_difference_directly' or receipt.get('status') != 'COMPLETE':
        raise ValueError('complete directly encoded error cache required')
    metadata = read(pack / 'items.json')
    validate_production_metadata(metadata)
    population = read(HERE / 'DECOMPOSITION_PLAN.20261025.json')['population']
    for name in ('items.input.jsonl', 'items.DO_NOT_STAGE.jsonl', 'templates.json'):
        if sha(pack / name) != population[name + '_sha256']:
            raise ValueError('frozen W1 metadata checksum mismatch')
    validate_metadata_provenance(metadata, jsonl(pack / 'items.DO_NOT_STAGE.jsonl'), read(pack / 'templates.json'))
    # The encoding collector supplies the original frozen ID files, not new splits.
    for split in ('dev', 'test'):
        name = split + '_ids.json'
        if name not in receipt['files'] or sha(pack / name) != population[name + '_sha256']:
            raise ValueError('frozen W1 population ID checksum mismatch')
        if {m['id'] for m in metadata if m['split'] == split} != set(read(pack / name)):
            raise ValueError('encoding population differs from W1')
    guard.parent.mkdir(parents=True, exist_ok=True)
    dump_new(guard, {'freeze_sha256': approval['freeze_sha256'],
                     'gate_result_sha256': approval['gate_result_sha256'],
                     'labels_seal_sha256': approval['labels_seal_sha256']})
    out.mkdir(parents=True, exist_ok=False)
    norms = np.load(pack / 'decoder_norms.npy', allow_pickle=False)
    if (norms.ndim != 1 or len(norms) != approval['_gate']['metrics']['d_sae']
            or not np.isfinite(norms).all() or (norms < 0).any()):
        raise ValueError('finite nonnegative decoder norms required')
    with np.load(pack / 'codes.npz', allow_pickle=False) as data:
        codes = {name: (data[name + '_indices'], data[name + '_values']) for name in PRIMARY + DESCRIPTIVE}
    # Validate every split, including dev codes used for frequency matching/probes.
    k = approval['_gate'].get('sae_k', 50)
    for indices, values in codes.values():
        if indices.ndim != 2 or indices.shape != (len(metadata), k) or values.shape != indices.shape:
            raise ValueError('all code arms must align with complete item metadata')
        latent_share_sparse(indices, values, norms, np.zeros(len(norms), dtype=bool))
    counts, sums = dev_statistics(*codes['h'], metadata, len(norms))
    selected = select_top_latents(sums)
    key, primary, secondary = approval['_key'], approval['_primary'], approval['_secondary']
    if set(selected) != set(validate_key(key).values()):
        raise ValueError('labelled latents differ from frozen top300 dev selection')
    mask = structure_mask(primary, key, len(norms))
    report = primary_report(codes, norms, mask, counts, metadata)
    report.update(experiment='E35', clarification_commit='ff48f19ac143b436c7c6e9586473f1e160045da9',
                  gate_result_sha256=approval['gate_result_sha256'], freeze_sha256=approval['freeze_sha256'],
                  label_agreement=cohen_kappa(primary, secondary, key),
                  structure_latents=int(mask.sum()), labelled_latents=300,
                  per_row_code_probes=run_per_row_probes(metadata, {k: codes[k] for k in PRIMARY},
                                                        len(norms), authorized=True),
                  dominant_named_policy_latents=dominant_named_latents(codes, norms, metadata, primary, key,
                                             read(Path(approval['labels_dir']) / 'primary_payloads.json')))
    dump_new(out / 'RESULTS.json', report)
    dump_new(out / 'ANALYSIS_SEAL.json', {'status': 'COMPLETE', 'files': {'RESULTS.json': sha(out / 'RESULTS.json')},
                                       'encoding_seal_sha256': sha(pack / 'ENCODING_SEAL.json'),
                                       'registered_analysis_runs': 1})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('authorization', 'encoding-cache', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    approval = authorize(args.authorization)
    analyze_pack(args.encoding_cache, approval, args.out)
    print('E35 decomposition analysis complete')


if __name__ == '__main__':
    main()
