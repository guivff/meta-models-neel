import math
import contract as C

def validate_operational_gates(root, receipt, assignment):
    """2026-10-25: verify authorized environment/parity evidence before unblinding."""
    bindings = {'TRAINING_ENVIRONMENT.json': 'environment_manifest_sha256',
                'ENVIRONMENT_RUNTIME_RESULT.json': 'environment_runtime_result_sha256',
                'PARITY_RESULT.json': 'parity_result_sha256', 'PARITY_SCORES.jsonl': 'parity_scores_sha256'}
    for name, key in bindings.items():
        if receipt.get(key) != C.sha(root / name):
            raise ValueError('missing or altered E44 environment/parity receipt')
    if (assignment.get('training_environment_sha256') != receipt['environment_manifest_sha256']
            or assignment.get('parity_input_seal_sha256') != receipt.get('parity_input_seal_sha256')
            or receipt['parity_input_seal_sha256'] != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']):
        raise ValueError('environment/parity assignment mismatch')
    parity = C.read(root / 'PARITY_RESULT.json')
    reference = C.read(root / 'PARITY_REFERENCE.json')
    expected = {'prose_sentiment': 0.9109977324263039, 'prose_paren': 0.4846938775510204,
                'python_string': 0.6439909297052154}
    if (parity.get('schema') != 'E28_PRETRAIN_PARITY_RESULT_v1' or parity.get('status') != 'PASS'
            or parity.get('optimizer_steps_before_gate') != 0 or set(parity.get('rows', {})) != set(expected)
            or parity.get('environment_manifest_sha256') != receipt['environment_manifest_sha256']
            or parity.get('parity_input_seal_sha256') != receipt['parity_input_seal_sha256']
            or parity.get('raw_scores_sha256') != receipt['parity_scores_sha256']
            or parity.get('reference_sha256') != C.sha(root / 'PARITY_REFERENCE.json')
            or reference.get('reference_auc') != expected or reference.get('max_abs_auroc_delta') != .03
            or reference.get('original_e28_input_seal_sha256') != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['original_e28_input_seal_sha256']):
        raise ValueError('authorized pre-training parity evidence required')
    for row, cell in parity['rows'].items():
        values = [cell.get(k) for k in ('observed', 'reference', 'absolute_delta')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or cell.get('n') != 84 or cell.get('threshold') != .03 or cell['reference'] != expected[row]
                or not 0 <= cell['observed'] <= 1
                or abs(cell['absolute_delta'] - abs(cell['observed'] - cell['reference'])) > 1e-12
                or not 0 <= cell['absolute_delta'] <= .03):
            raise ValueError('E44 W1 AUROC environment parity failed')
    ready = C.read(root / 'ENVIRONMENT_RUNTIME_RESULT.json')
    epoch, gate_epoch = ready.get('completed_epoch'), parity.get('completed_epoch')
    if (ready.get('schema') != 'E44_TRAINING_ENV_RUNTIME_v1' or ready.get('status') != 'TRAINING_ENVIRONMENT_READY'
            or ready.get('device') != 'cuda' or ready.get('real_cuda_backward') is not True
            or ready.get('finite_loss') is not True or ready.get('finite_gradients') is not True
            or ready.get('fresh_lora_only') is not True or ready.get('optimizer_steps_in_readiness') != 1
            or ready.get('environment_manifest_sha256') != receipt['environment_manifest_sha256']
            or ready.get('parity_result_sha256') != receipt['parity_result_sha256']
            or ready.get('readiness_deadline_epoch') != 1793314740
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in (epoch, gate_epoch))
            or not 0 < gate_epoch <= epoch <= 1793314740):
        raise ValueError('real CUDA backward readiness by programme cutoff required')
