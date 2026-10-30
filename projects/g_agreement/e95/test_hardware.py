import pytest

from projects.g_agreement.e95.hardware import validate_assignment


def smoke():
    return dict(image_id='fixed-image', verified=True, before_production=True,
                model_loaded=True, reader_loaded=True, finite_outputs=True, decoding_unchanged=True,
                seal_sha256='a'*64,
                items=[dict(id=str(i), sealed_h200_readout_sha256='b'*64,
                            first_divergence_position=0 if i==0 else None) for i in range(3)])


def test_first_divergence_is_reported_without_becoming_a_parity_gate():
    a=dict(gpu_type='B200',observed_gpu_type='B200',image_id='fixed-image',row_indices=[0])
    out=validate_assignment(a,[dict(row_index=0,reuse_e87=False)],{},smoke())
    assert out['gpu_type']=='B200' and out['b200_smoke_seal_sha256']=='a'*64
    for change in [dict(image_id='different-image'),dict(model_loaded=False),dict(finite_outputs=False)]:
        with pytest.raises(ValueError):
            validate_assignment(a,[dict(row_index=0,reuse_e87=False)],{},dict(smoke(),**change))


def test_reused_row_and_new_placebo_cannot_cross_gpu_types():
    a=dict(gpu_type='B200',observed_gpu_type='B200',image_id='fixed-image',row_indices=[0])
    rows=[dict(row_index=0,reuse_e87=True)]
    with pytest.raises(ValueError,match='match'):
        validate_assignment(a,rows,{0:'H200'},smoke())
    with pytest.raises(ValueError):
        validate_assignment(a,rows,{},smoke())
    assert validate_assignment(a,rows,{0:'B200'},smoke())['row_gpu_types']=={'0':'B200'}
