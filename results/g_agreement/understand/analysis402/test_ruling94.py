import sys,copy,tarfile,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import analyze as a
from packet_fields import fields,convert,seal,dump,verify

def test_verbatim_fields_fixed_order():
 x={'id':'opaque','property':'a property\nwith punctuation','values':{'B':'beta "B"','A':'alpha\nA'},'readout':'verbatim output'};v=fields(x)
 assert list(v)==['id','property','value_A','value_B','readout']
 assert v['property']==x['property'] and v['value_A']==x['values']['A'] and v['value_B']==x['values']['B'] and v['readout']==x['readout']
 with pytest.raises(ValueError):fields(dict(x,true_label='A'))

def test_sealed_packet_archive_roundtrip(tmp_path):
 blind=tmp_path/'blind';blind.mkdir();dump(blind/'JUDGE_PACKET.json',[{'id':'opaque','property':'property','values':{'A':'a','B':'b'},'readout':'text'}]);seal(blind,'BLIND_SEAL.json',{})
 archive=tmp_path/'packet.tar'
 with tarfile.open(archive,'w') as t:t.add(blind,arcname='blind')
 clean=tmp_path/'clean';clean.mkdir()
 with tarfile.open(archive) as t:t.extractall(clean,filter='data')
 records=convert(clean/'blind',tmp_path/'fields');verify(tmp_path/'fields','RUBRIC_FIELDS_SEAL.json');assert records[0]['value_A']=='a'
 with pytest.raises(FileExistsError):convert(clean/'blind',tmp_path/'fields')

def test_not_run_never_opens_placebo(monkeypatch):
 def forbidden(*args):raise AssertionError('placebo must not be opened')
 monkeypatch.setattr(a,'load_config',forbidden);monkeypatch.setattr(a,'collect',forbidden);monkeypatch.setattr(a,'judgments',forbidden)
 assert a.load_placebo(True)==(None,None)

def test_only_placebo_rules_change(monkeypatch):
 states=['S1','S2','S3','S4','S5'];probe={s+'_L'+str(i):.95 for s in states for i in range(5)};rates={('oracle',k):{'S':int(k[-1])*.1} for k in probe};prates={('oracle',s+'_'+r+'p'):{'S':0.} for s in states for r in ('L2','L4')};jrows={k:{'J_fraction':i/30} for i,k in enumerate(probe)}
 data={'private':{},'native':['real'],'behaviour':[]};pdata={'private':{},'native':['placebo']}
 monkeypatch.setattr(a,'probe_aucs',lambda d:probe)
 monkeypatch.setattr(a,'metrics',lambda private,native,jj:rates if native==['real'] else prates)
 monkeypatch.setattr(a,'behaviour_aucs',lambda *args:{'AUROC':dict.fromkeys(states,.9)})
 monkeypatch.setattr(a,'eval_measure',lambda *args:{'oracle':{'R_L4':'MET'}})
 monkeypatch.setattr(a,'sha',lambda p:'pin');monkeypatch.setattr(a,'read',lambda p:{'frozen':'confound'})
 spec={'placebo_confound_check':'path','placebo_confound_check_sha256':'pin'}
 full,_=a.compute62(spec,data,{},jrows,pdata,{})
 missing,_=a.compute62({},data,{},jrows)
 assert missing['E62P']['status']=='NOT RUN' and missing['R_L5']['oracle']['verdict']=='NOT EVALUABLE'
 for key in ('R_L0','readers','behaviour','eval_ladder','probe','rates','J_rows'):assert missing[key]==full[key]
