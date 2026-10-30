import pytest
from . import run as r
from projects.g_agreement.analysis_late.test_extensions import e103fixture

def test_original_statistics_unchanged():
    rows=e103fixture();a=r.e103.analyze(rows)
    assert a['rules']['R-H2']['status']=='MET'
    assert a['bootstrap']['draws']==2000 and a['bootstrap']['seed']==20261027
    assert a['pooled']['CONTRADICTED']['difference']['CI95']==[1,1]

def test_fixed_guard_is_distinct():
    assert r.GUARD!=r.BASE/'ANALYSIS_ONCE.json'
    assert r.GUARD==r.BASE/'deviation1/ANALYSIS_ONCE.json'

@pytest.mark.parametrize('field,value',[('label','strict'),('authority_commit','wrong'),('deviation','other'),('experiment','E87')])
def test_wrong_authority_rejected_before_io(field,value):
    s=dict(experiment='E103',label=r.LABEL,deviation='E103 deviation 1',authority_commit=r.AUTH);s[field]=value
    with pytest.raises(ValueError):r.validate(s)

def test_separate_claim_does_not_touch_strict_and_no_replay(tmp_path):
    strict=tmp_path/'ANALYSIS_ONCE.json';strict.write_text('strict');before=r.c.sha(strict)
    s=dict(analysis=str(tmp_path/'result'),guard=str(tmp_path/'deviation1/ANALYSIS_ONCE.json'),output_sha256='synthetic')
    r.c.core.claim(s,'synthetic');assert r.c.sha(strict)==before
    s['analysis']=str(tmp_path/'another')
    with pytest.raises(FileExistsError):r.c.core.claim(s,'synthetic')
