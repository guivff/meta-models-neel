"""E95 receipt validation for the authorized H200/B200 operator paths."""
import re


def validate_assignment(assignment, rows, reused_row_gpu_types, b200_smoke=None):
    gpu_type = assignment['gpu_type']
    if gpu_type not in ('H200', 'B200'):
        raise ValueError('authorized GPU type must be explicit')
    if assignment['observed_gpu_type'] != gpu_type:
        raise ValueError('provider/runtime observation must match the assignment')
    row_indices = assignment['row_indices']
    if not row_indices or len(row_indices) != len(set(row_indices)):
        raise ValueError('unique whole rows required')
    by_index = {row['row_index']: row for row in rows}
    for index in row_indices:
        if index not in by_index:
            raise ValueError('row outside frozen roster')
        if by_index[index]['reuse_e87']:
            if reused_row_gpu_types.get(index) != gpu_type:
                raise ValueError('new placebo must match the reused real-row GPU type')
    smoke_hash = None
    if gpu_type == 'B200':
        s = b200_smoke
        if not s or s.get('image_id') != assignment['image_id']:
            raise ValueError('this B200 image needs its own smoke receipt')
        if not (s.get('verified') is True and s.get('before_production') is True
                and s.get('model_loaded') is True and s.get('reader_loaded') is True
                and s.get('finite_outputs') is True and s.get('decoding_unchanged') is True):
            raise ValueError('load/software/nonfinite failure: stop pod before production')
        items = s['items']
        if len(items) != 3 or len({x['id'] for x in items}) != 3:
            raise ValueError('three unique sealed smoke items required')
        for item in items:
            if not re.fullmatch('[0-9a-f]{64}', item['sealed_h200_readout_sha256']):
                raise ValueError('sealed H200 reference identity required')
            divergence = item['first_divergence_position']
            if divergence is not None and (type(divergence) is not int or divergence < 0):
                raise ValueError('report first divergence or null for identical readouts')
        smoke_hash = s['seal_sha256']
        if not re.fullmatch('[0-9a-f]{64}', smoke_hash):
            raise ValueError('B200 smoke source seal required')
    return dict(gpu_type=gpu_type, image_id=assignment['image_id'],
                hardware_authority='cb76843c', row_gpu_types={str(x):gpu_type for x in row_indices},
                real_placebo_control_gpu_type_matched=True,
                b200_smoke_seal_sha256=smoke_hash)
