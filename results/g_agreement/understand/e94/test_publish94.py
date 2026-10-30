def test_publication_is_verbatim_projection_without_private_strata():
    from publish94 import project
    raw=dict(experiment='E94',pooled_value_grounded=dict(n=7),banks={'E67_wave1':dict(metrics=dict(n=2),pairing=dict(identity_intersection=2),strata={'private-donor-id':dict(n=2)})})
    public=project(raw)
    assert public['banks']['E67_wave1']['metrics'] is raw['banks']['E67_wave1']['metrics']
    assert public['pooled_value_grounded'] is raw['pooled_value_grounded']
    assert 'strata' not in public['banks']['E67_wave1'] and 'strata' in raw['banks']['E67_wave1']
