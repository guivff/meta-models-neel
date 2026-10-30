from copy import deepcopy
import pytest
from .validator221 import e87_code,e87_classify,e103_parse
from .e87 import validate_code as strict

ITEM=dict(id='opaque',positions=[dict(offset=-1,readout='A red box'),dict(offset=0,readout='Nothing else')])

def silent(position):return dict(id='opaque',category='silent',values=[],evidence='',first_position=position)

@pytest.mark.parametrize('position',[-15,-7,-11,0,-1,None])
def test_audited_silent_positions_only(position):
    raw=silent(position);before=deepcopy(raw)
    if position is not None:
        with pytest.raises(ValueError):strict(ITEM,raw)
    assert e87_code(ITEM,raw)==silent(None)
    assert raw==before

@pytest.mark.parametrize('patch',[dict(evidence=' '),dict(evidence='red'),dict(values=['A']),dict(id='wrong'),dict(extra=True)])
def test_silent_does_not_relax_other_checks(patch):
    with pytest.raises(ValueError):e87_code(ITEM,dict(silent(0),**patch))


def test_nonsilent_quotes_positions_values_unchanged():
    good=dict(id='opaque',category='states_value',values=['A'],evidence='red box',first_position=-1)
    assert e87_code(ITEM,good)==good
    for patch in [dict(first_position=0),dict(first_position=None),dict(evidence='invented'),dict(values=[]),dict(category='other')]:
        with pytest.raises(ValueError):e87_code(ITEM,dict(good,**patch))


def test_group_identity_never_repaired():
    assert e87_classify([ITEM],dict(records=[silent(0),silent(0)]))[0]['status']=='INVALID'
    assert e87_classify([ITEM],dict(records=[dict(silent(0),id='other')]))[0]['status']=='INVALID'

@pytest.mark.parametrize('text,value',[('No.','no'),(' YES! ','yes'),('\n\t(no)\r','no'),('“YeS.”','yes'),('```NO```','no'),('yes','yes'),('no','no')])
def test_case_surrounding_punctuation_only(text,value):assert e103_parse(text)==value

@pytest.mark.parametrize('text',['No, because none do.','yes or no','yes\nno','y e s','not yes','{"answer":"no"}','...','',None,'ＹＥＳ'])
def test_no_other_parser_change(text):
    with pytest.raises(ValueError):e103_parse(text)


def test_revalidation_uses_original_final_attempt_preserves_kept_and_other_missing(tmp_path,monkeypatch):
    import json,hashlib
    from . import revalidate221 as r
    from projects.g_agreement.readerbench.io import write,sha
    monkeypatch.setattr(r,'CACHE',tmp_path/'cache');old=tmp_path/'strict';old.mkdir();out=tmp_path/'corrected';out.mkdir()
    strict_seal=dict(blind_seal_sha256='frozen');audits=[]
    items=[dict(ITEM,id=x) for x in ('recover','kept','still_missing')]
    for channel,filename in [('main','JUDGMENTS.json'),('original','ORIGINAL_JUDGMENTS.json')]:
        flats=[];term=[]
        for item in items:
            ident=item['id'];good=dict(id=ident,category='states_value',values=['A'],evidence='red box',first_position=-1)
            code=dict(silent(-1),id=ident) if ident=='recover' else good if ident=='kept' else dict(good,evidence='invented')
            attempt=0 if ident=='kept' else 2
            flats.append(good if ident=='kept' else dict(id=ident,category='UNPARSEABLE',values=[],evidence='',first_position=None))
            term.append(dict(id=ident,status='KEPT' if ident=='kept' else 'UNPARSEABLE',attempts=attempt,code=good if ident=='kept' else None))
            stage=f'E87_{channel}_attempt{attempt}';folder=r.CACHE/'E87/ledger'/stage;folder.mkdir(parents=True,exist_ok=True)
            wire=dict(messages=[dict(role='system',content='frozen'),dict(role='user',content=json.dumps([item]))])
            canonical=json.dumps(wire,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            rid=hashlib.sha256((stage+':frozen:'+canonical).encode()).hexdigest()
            write(folder/(rid+'.request.json'),dict(wire=wire))
            rp=folder/(rid+'.response.json');write(rp,dict(http_status=200,response=dict(provider='Google',model='google/gemini-3.1-flash-lite',usage=dict(cost=.001),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[code]))))])))
            audits.append(dict(request_id=rid,response_sha256=sha(rp)))
        write(old/filename,flats);write(old/(channel+'_TERMINAL.json'),term);write(old/(channel+'_JUDGE_COPY.json'),items)
    for name in ['PATH_REDACTION_AUDIT.json','PARALLEL_EXECUTION.json']:write(old/name,{})
    changes,counts=r.e87_revalidate(old,strict_seal,dict(requests=audits),out)
    corrected=json.loads((out/'JUDGMENTS.json').read_text())
    assert corrected[0]==dict(silent(None),id='recover')
    assert corrected[1]==json.loads((old/'JUDGMENTS.json').read_text())[1]
    assert corrected[2]==json.loads((old/'JUDGMENTS.json').read_text())[2]
    assert len(changes)==2 and counts['main']['recovered']==1


def test_e103_revalidation_no_explanation_or_length_recovery(tmp_path,monkeypatch):
    from . import revalidate221 as r
    from projects.g_agreement.readerbench.io import write,sha,read
    monkeypatch.setattr(r,'CACHE',tmp_path/'cache');old=tmp_path/'strict';old.mkdir();out=tmp_path/'corrected';out.mkdir();rows=[];audits=[]
    for ident,text,reason in [('recover','No.','FROZEN_YES_NO_PARSE'),('explanation','No, because...','FROZEN_YES_NO_PARSE'),('length','Yes.','CHARGED_LENGTH')]:
        folder=r.CACHE/'E103/ledger/E103_yesno';folder.mkdir(parents=True,exist_ok=True);rp=folder/(ident+'.response.json')
        write(rp,dict(http_status=200,response=dict(provider='Google',model='google/gemini-3.1-flash-lite',usage=dict(cost=.001),choices=[dict(finish_reason='length' if ident=='length' else 'stop',message=dict(content=text))])))
        rows.append(dict(id=ident,request_id=ident,response_sha256=sha(rp),raw_response=text,status='UNPARSEABLE',reason=reason,response='unparseable',attempts=0));audits.append(dict(request_id=ident,response_sha256=sha(rp)))
    write(old/'RESPONSES.json',rows)
    changed,_=r.e103_revalidate(old,{},dict(requests=audits),out);result=read(out/'RESPONSES.json')
    assert len(changed)==1 and result[0]['response']=='no'
    assert result[1:]==rows[1:]
