import json
import pytest
from projects.g_agreement.e96 import launch_second3899 as l
def test_requires_exact_final_authority_before_any_network(tmp_path,monkeypatch):
 (tmp_path/'SECOND_ATTEMPT_AUTHORITY.json').write_text(json.dumps({'authority_commit':'wrong','attempt_number':2,'final_attempt':True}))
 monkeypatch.setattr(l,'query',lambda q:pytest.fail('network forbidden before authority'))
 with pytest.raises(ValueError,match='authority'):l.launch(tmp_path)
def test_existing_attempt_never_creates_again(tmp_path,monkeypatch):
 (tmp_path/'SECOND_ATTEMPT_AUTHORITY.json').write_text(json.dumps({'authority_commit':'3899e1ea073f8609f33fb35b5ce1863c6223961f','attempt_number':2,'final_attempt':True}))
 (tmp_path/'STATE.json').write_text('{}')
 monkeypatch.setattr(l,'query',lambda q:pytest.fail('duplicate network'))
 with pytest.raises(ValueError,match='one replacement'):l.launch(tmp_path)
