from copy import deepcopy
import pytest
from .e117_binding import project
from .e117_close import phases
from projects.g_agreement.readerbench.io import write,sha


def rows():
    joins=[dict(id='a',native_id='nativeA',source_ref=dict(member='jobs/a.json',keys=[1,'text'])),dict(id='b',native_id='nativeB',source_ref=dict(member='jobs/a.json',keys=[0,'text']))]
    codes=[dict(id='b',kind='original57',status='UNPARSEABLE',code=None,request_id='rb',response_sha256='hb'),dict(id='a',kind='original57',status='KEPT',code=dict(id='a',category='VALUE',values=['A'],evidence='first'),request_id='ra',response_sha256='ha')]
    return joins,codes


def test_id_join_null_preservation_separate_missing_envelope():
    j,r=rows();out,m=project(j,r,dict(seal='seal',sha256='hash'),2)
    assert out['nativeA']['code_source']['keys']==[1,'code'] and out['nativeB']['code_source']['keys']==[0,'code']
    assert out['nativeB']['status']=='UNPARSEABLE' and m[0]['code']['category']=='UNPARSEABLE' and m[0]['code']['values']==[]
    assert r[0]['code'] is None and r[1]['code']['values']==['A']


@pytest.mark.parametrize('fault',['missing','duplicate','wrong_id','null_kept'])
def test_fail_closed_projection(fault):
    j,r=deepcopy(rows())
    if fault=='missing':r.pop()
    elif fault=='duplicate':j[1]['native_id']=j[0]['native_id']
    elif fault=='wrong_id':r[1]['code']['id']='changed'
    else:r[0]['status']='KEPT'
    with pytest.raises(ValueError):project(j,r,dict(seal='s',sha256='h'),2)


def test_c_only_cannot_release_shared_main_allowance(tmp_path):
    for phase,n in [('targeted_sham_judging',672),('native_judging',3024)]:
        d=tmp_path/phase/'outputs';d.mkdir(parents=True);write(d/'JUDGMENTS.json',[dict(id=str(i)) for i in range(n)])
        if phase=='targeted_sham_judging':write(d/'JUDGMENT_SEAL.json',dict(experiment='E117',status='COMPLETE',route_verified=True,files={'JUDGMENTS.json':sha(d/'JUDGMENTS.json')}))
    with pytest.raises(FileNotFoundError):phases(tmp_path)
