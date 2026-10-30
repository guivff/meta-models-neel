from copy import deepcopy
import pytest
from .e97_privacy_copy import judge_copy
from .rubric202 import original_ids


def test_only_judge_readout_copy_changes_ids_properties_sampling_same():
    raw=[dict(id=f'{i:032x}',property=dict(definition='Frozen property',values=dict(A='one',B='two')),readout='path /tmp/benchmark/file.txt' if i==0 else 'same native text') for i in range(4)]
    before=deepcopy(raw);copy,audit=judge_copy(raw)
    assert raw==before and [x['id'] for x in copy]==[x['id'] for x in raw]
    assert all(x['property']==y['property'] for x,y in zip(raw,copy))
    assert copy[0]['readout']=='path [REDACTED_PATH]' and copy[1:]==raw[1:]
    assert original_ids([x['id'] for x in copy],'E97')==original_ids([x['id'] for x in raw],'E97')
    assert audit['redacted_records']==1 and audit['affected'][0]['original_readout_sha256']!=audit['affected'][0]['judge_readout_sha256']


def test_credentials_are_never_masked_or_allowed():
    row=dict(id='opaque',property=dict(definition='frozen',values=dict(A='a',B='b')),readout='sk-or-v1-'+'x'*32)
    with pytest.raises(ValueError):judge_copy([row])
