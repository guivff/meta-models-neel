import json
from pathlib import Path
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.stage import stage_bank


def test_staging_only_copies_sealed_label_free_files(tmp_path):
    bank=tmp_path/'bank';bank.mkdir()
    P.dump(bank/'manifest.json',{'frozen':True})
    P.jsonl(bank/'items.input.jsonl',[{'id':'a','ids':[1,2]}])
    P.jsonl(bank/'labels.DO_NOT_STAGE.jsonl',[{'id':'a','value':'positive'}])
    P.seal(bank,['manifest.json','items.input.jsonl'],'INPUTS_FROZEN')
    staged=tmp_path/'staged'
    stage_bank(bank,staged)
    assert set(p.name for p in staged.iterdir())=={'manifest.json','items.input.jsonl','INPUT_SEAL.json'}
    assert P.verify(staged,'INPUT_SEAL.json')==P.verify(bank,'INPUT_SEAL.json')


def test_staging_rejects_label_bearing_seal(tmp_path):
    bank=tmp_path/'bank';bank.mkdir()
    P.jsonl(bank/'labels.DO_NOT_STAGE.jsonl',[{'value':1}])
    P.seal(bank,['labels.DO_NOT_STAGE.jsonl'],'INPUTS_FROZEN')
    with pytest.raises(ValueError,match='labels'):
        stage_bank(bank,tmp_path/'staged')
