from .unknown_cost_guard import known_cost,saved_unknown
from projects.g_agreement.readerbench.io import write


def test_only_explicit_finite_nonnegative_usage_cost_is_known():
    assert known_cost(dict(response=dict(usage=dict(cost=0))))
    for x in [None,True,-1,'NaN','bad']:
        assert not known_cost(dict(response=dict(usage=dict(cost=x))))
    assert not known_cost(dict(http_status=429,response=dict(error=dict(code=429))))
    assert not known_cost(dict(response=dict(usage=None)))
    assert not known_cost(dict(response=None))


def test_no_inflight_interruption_and_no_inferred_zero_or_replay(tmp_path):
    p=tmp_path/'ledger.jsonl';p.write_text('{"event":"reserve","id":"r","usd":".01","at":1}\n')
    assert saved_unknown(tmp_path,'E127')==[]
    d=tmp_path/'E127_judging';d.mkdir();write(d/'r.response.json',dict(http_status=429,response=dict(error=dict(code=429))))
    assert saved_unknown(tmp_path,'E127')[0]['unresolved_upper_usd']=='.01'
    with p.open('a') as f:f.write('{"event":"settle","id":"r","usd":"0","at":2}\n')
    assert saved_unknown(tmp_path,'E127')==[]
