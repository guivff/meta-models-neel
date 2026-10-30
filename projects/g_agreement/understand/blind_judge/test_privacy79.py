import ast
import copy
import inspect
import json
import pytest
from projects.g_agreement.readerbench.io import read
from .run import route_modules,ROOT
from .privacy79 import PATTERNS,redact,check_decoded
from .later_runner import channel_payload


def modules():
    return route_modules(read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))


def test_patterns_identical_to_frozen_e10():
    _,privacy,_,_=modules()
    # Other tests can monkeypatch check_wire; inspect the frozen source file.
    source=open(privacy.__file__).read();tree=ast.parse(source)
    assigned=[ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='patterns' for t in n.targets)]
    assert assigned==[PATTERNS]


def test_decoded_values_remove_escape_false_positive():
    # Fresh source function, not previous tests' temporary dispatch wrappers.
    _,privacy,p,_=modules();ns=dict(privacy.__dict__);exec(open(privacy.__file__).read(),ns)
    original=ns['check_wire'];items=[dict(id='a'*32,readout='A'+':'+chr(10)+'text')]
    wire=channel_payload(items,'frozen rubric','E66',p)
    with pytest.raises(ValueError):original('extract',[dict(id='a'*32,readout=json.dumps(items[0]))],wire)
    check_decoded(original,items,wire)
    bad=copy.deepcopy(wire);bad['messages'][1]['content']=json.dumps([dict(items[0],readout='changed')])
    with pytest.raises(ValueError):check_decoded(original,items,bad)


def test_only_path_tokens_change_and_originals_retained():
    original=[dict(id='a'*32,readout='Before '+chr(47)+'Users'+chr(47)+'alice'+chr(47)+'file.py and C'+':'+chr(92)+'work'+chr(92)+'x.txt; after.',rubric='rubric')]
    before=copy.deepcopy(original);wire,audit=redact(original,'E66')
    assert original==before
    assert wire[0]['readout']=='Before [REDACTED_PATH] and [REDACTED_PATH]; after.'
    assert wire[0]['rubric']=='rubric'
    assert audit['redacted_records']==1 and audit['affected'][0]['id']=='a'*32 and audit['affected'][0]['path_count']==2
    assert chr(47)+'Users' not in json.dumps(audit)
    assert len(wire)==len(original)


@pytest.mark.parametrize('text',[chr(47)+'tmp'+chr(47)+'sk'+'-proj-'+'x'*20,'h'+'f'+'_'+'x'*20,'.'.join(['127','0','0','1'])+':'+str(8080)])
def test_nonpath_classes_still_stop_even_inside_path(text):
    with pytest.raises(ValueError,match='key/token/address'):redact([dict(id='a'*32,readout=text)],'E66')


def test_non_readout_paths_not_redacted_and_guard_stops():
    _,privacy,p,_=modules();ns=dict(privacy.__dict__);exec(open(privacy.__file__).read(),ns)
    items=[dict(id='a'*32,readout='safe',rubric='source '+chr(47)+'etc'+chr(47)+'config')]
    copied,audit=redact(items,'E68');assert copied==items and audit['redacted_records']==0
    with pytest.raises(ValueError):check_decoded(ns['check_wire'],copied,channel_payload(copied,'rubric','E56',p))


def test_address_extension_preserves_original_and_records_hashes():
    address='.'.join(['192','0','2','1'])
    original=[dict(id='a'*32,readout='Before '+address+':'+str(8080)+' and '+address+' after.')]
    copied,audit=redact(original,'E76',addresses=True)
    assert copied[0]['readout']=='Before [REDACTED_ADDRESS] and [REDACTED_ADDRESS] after.'
    assert original[0]['readout'].startswith('Before '+address)
    assert audit['address_authority']=='25c32f25' and audit['affected'][0]['address_count']==2
    assert audit['redacted_records']==1 and audit['affected'][0]['original_readout_sha256']!=audit['affected'][0]['judge_readout_sha256']
    with pytest.raises(ValueError):redact([dict(id='a'*32,readout='h'+'f'+'_'+'x'*20)],'E76',addresses=True)
