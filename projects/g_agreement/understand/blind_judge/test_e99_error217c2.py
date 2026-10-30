from copy import deepcopy
import pytest
from .e99_error217c2 import known_failure


def saved():
    return dict(http_status=200, response=dict(provider='Google', model='google/gemini-3.1-flash-lite',
                usage=dict(cost=0), choices=[dict(finish_reason='error', message=dict(content='partial content never parsed'))]))


def test_no_error_object_needed_and_partial_is_never_scored():
    assert known_failure('opaque',saved()) == dict(id='opaque',status='FAILED',reason='INCOMPLETE_COMPLETION')


@pytest.mark.parametrize('kind',['charged','unknown','wrongroute','402','length','stop'])
def test_every_other_envelope_retains_original_stop_or_classification(kind):
    x=deepcopy(saved())
    if kind=='charged':x['response']['usage']['cost']=.01
    if kind=='unknown':x['response']['usage'].pop('cost')
    if kind=='wrongroute':x['response']['provider']='other'
    if kind=='402':x['http_status']=402
    if kind in ('length','stop'):x['response']['choices'][0]['finish_reason']=kind
    assert known_failure('opaque',x) is None
