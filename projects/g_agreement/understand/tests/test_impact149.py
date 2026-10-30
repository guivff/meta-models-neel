import pytest
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.impact149 import population,run


def test_deduplicates_scoring_repeats(tmp_path):
    p=tmp_path/'scores';P.jsonl(p,[{'id':'a','feature':'latex_item'},{'id':'a','feature':'latex_item'},{'id':'b','feature':'prose_paren'}])
    result=population([{'path':str(p)}]);assert result['items']==2 and result['fraction']==.5


def test_failure_cannot_retry(tmp_path):
    spec=tmp_path/'spec';P.dump(spec,{'lock':str(tmp_path/'lock'),'out':str(tmp_path/'out'),'pins':{str(tmp_path/'absent'):'bad'}})
    with pytest.raises(FileNotFoundError):run(spec,P.sha(spec))
    with pytest.raises(FileExistsError):run(spec,P.sha(spec))
