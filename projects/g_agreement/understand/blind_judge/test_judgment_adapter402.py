import json
import pytest
from .judgment_adapter402 import render_record,adapt_grid,validate_flat,summarize_row,score_values,adapt_files


def test_verbatim_render_fixed_order_no_correctness():
    r=dict(id='a'*32,property='Literal {property}',values={'B':'dog\nquoted','A':'cat'},readout='text')
    got=render_record(r,'FROZEN\n')
    assert got==dict(id=r['id'],readout='text',rubric='FROZEN\n\n\nProperty: Literal {property}\nA: cat\nB: dog\nquoted\n')
    with pytest.raises(ValueError):render_record(dict(r,label='A'),'FROZEN')


def test_adapter_both_and_unparseable_exclusion():
    packet=[dict(id=str(i),readout='cat dog') for i in range(3)]
    codes=[dict(id='0',category='states_value',values=['A','B'],evidence='CAT DOG'),
           dict(id='1',category='states_value',values=['A'],evidence='cat')]
    terminal=[dict(id=x['id'],status='KEPT',code=x,attempts=0) for x in codes]
    terminal.append(dict(id='2',status='UNPARSEABLE',code=None,attempts=2))
    flat,audit=adapt_grid(terminal,packet)
    assert flat[:2]==codes
    assert flat[2]==dict(id='2',category='UNPARSEABLE',values=[],evidence='')
    assert summarize_row(flat,['A']*3)['S']==.5
    assert score_values(flat,['A']*3)==[0,1]
    assert summarize_row(flat,['A']*3)['unparseable']==1
    assert summarize_row([flat[2]],['A'])['S'] is None
    for x in flat:validate_flat(x,'cat dog')
    with pytest.raises(ValueError):adapt_grid(terminal+terminal[:1],packet)
    terminal[-1]['attempts']=1
    with pytest.raises(ValueError):adapt_grid(terminal,packet)


def test_sealed_adapter_output_for_analysis402(tmp_path,monkeypatch):
    from . import later_runner as runner
    from projects.g_agreement.readerbench.io import write,sha,verify
    monkeypatch.setattr(runner,'HERE',tmp_path)
    write(tmp_path/'RUNNER_SOURCE_SEAL.json',dict(files={}))
    blind=tmp_path/'blind';blind.mkdir();terminal=tmp_path/'terminal';terminal.mkdir()
    write(blind/'JUDGE_PACKET.json',[dict(id='a'*32,readout='cat')])
    write(blind/'EVAL_PACKET.json',[])
    write(blind/'BLIND_SEAL.json',dict(experiment='E57',files={p.name:sha(p) for p in blind.iterdir()}))
    write(terminal/'JUDGMENTS.json',[dict(id='a'*32,status='UNPARSEABLE',code=None,attempts=2)])
    write(terminal/'RESULT_SEAL.json',dict(bank='E57',channel='value',status='TERMINAL_BLIND_GRID_NO_ANALYSIS',
        packet_seal_sha256=sha(blind/'BLIND_SEAL.json'),files={p.name:sha(p) for p in terminal.iterdir()}))
    out=tmp_path/'joined'
    adapt_files(blind,sha(blind/'BLIND_SEAL.json'),terminal,sha(terminal/'RESULT_SEAL.json'),out)
    seal=verify(out/'JUDGMENT_SEAL.json',sha(out/'JUDGMENT_SEAL.json'))
    assert seal['blind_seal_sha256']==sha(blind/'BLIND_SEAL.json')
    assert json.loads((out/'JUDGMENTS.json').read_text())[0]['category']=='UNPARSEABLE'
    with pytest.raises(FileExistsError):adapt_files(blind,sha(blind/'BLIND_SEAL.json'),terminal,sha(terminal/'RESULT_SEAL.json'),out)


def test_dispatch_fake_transport_to_adapter(tmp_path,monkeypatch):
    import sys
    from . import later_runner as m
    from projects.g_agreement.readerbench.io import write,sha,read,verify
    # Fresh production E10 modules, with only network I/O replaced by an offline stub.
    for name in list(sys.modules):
        if name.startswith('_authorized_e10_judge'):monkeypatch.delitem(sys.modules,name)
    route=read(m.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,privacy,protocol,io=m.route_modules(route)
    monkeypatch.setattr(m,'route_modules',lambda plan:(api,privacy,protocol,io))
    monkeypatch.setattr(m,'LEDGER',tmp_path/'ledger')
    monkeypatch.setattr(m,'HERE',tmp_path/'here');m.HERE.mkdir()
    write(m.HERE/'RUNNER_SOURCE_SEAL.json',dict(files={}))
    proof=tmp_path/'proof';write(proof,dict(private_input_output_logging=False,openrouter_use_inputs_outputs=False,verified_at='synthetic'))
    route=dict(route,privacy_proof=str(proof),privacy_proof_sha256=sha(proof))
    monkeypatch.setattr(privacy,'check_route',lambda key:None)
    sent=[]
    class Response:
        status_code=200
        def __init__(self,body):self.body=body
        def json(self):return self.body
    def post(url,**kwargs):
        wire=kwargs['json'];sent.append(wire);items=json.loads(wire['messages'][1]['content'])
        codes=[dict(id=x['id'],category='states_value',values=['A','B'],evidence='cat dog') for x in items]
        return Response(dict(provider=protocol.PROVIDER_NAME,model=protocol.MODEL,usage=dict(cost=.001),
            choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=codes))))]))
    monkeypatch.setattr(api.requests,'post',post)
    blind=tmp_path/'blind';blind.mkdir()
    record=dict(id='a'*32,property='pet',values={'A':'cat','B':'dog'},readout='cat dog')
    write(blind/'JUDGE_PACKET.json',[record]);write(blind/'EVAL_PACKET.json',[])
    write(blind/'BLIND_SEAL.json',dict(experiment='E57',files={p.name:sha(p) for p in blind.iterdir()}))
    digest=sha(blind/'BLIND_SEAL.json');spec=dict(bank='E57',packet_seal_sha256=digest)
    m.dispatch(spec,[render_record(record,'frozen rubric')],'frozen rubric',route,'synthetic-test-only')
    terminal=m.LEDGER/'E57_judgments'
    adapt_files(blind,digest,terminal,sha(terminal/'RESULT_SEAL.json'),tmp_path/'analysis_input')
    assert len(sent)==1
    assert set(json.loads(sent[0]['messages'][1]['content'])[0])=={'id','rubric','readout'}
    assert read(tmp_path/'analysis_input/JUDGMENTS.json')[0]['values']==['A','B']


def test_eval_flat_kept_and_missing():
    p=[dict(id='one',readout='a test'),dict(id='two',readout='other')]
    t=[dict(id='one',status='KEPT',attempts=0,code=dict(id='one',eval_mention=True,evidence='test')),
       dict(id='two',status='UNPARSEABLE',attempts=2,code=None)]
    flat,_=adapt_grid(t,p,'S6')
    assert flat[0]==t[0]['code'] and flat[1]['category']=='UNPARSEABLE'


def test_list_values_frozen_order():
    r=dict(id='a'*32,property='antonym',values={'A':['large','big'],'B':['long']},readout='big')
    assert render_record(r,'frozen')['rubric'].endswith('A: large / big\nB: long\n')
    r['values']['A']=['big',1]
    with pytest.raises(ValueError):render_record(r,'frozen')


def test_e62_complete_combined_adapter(tmp_path,monkeypatch):
    from . import later_runner as m
    from projects.g_agreement.readerbench.io import read,write,sha
    monkeypatch.setattr(m,'HERE',tmp_path);write(tmp_path/'RUNNER_SOURCE_SEAL.json',dict(files={}))
    b=tmp_path/'blind';b.mkdir()
    write(b/'JUDGE_PACKET.json',[dict(id='v',readout='cat')]);write(b/'EVAL_PACKET.json',[dict(id='e',readout='test')])
    write(b/'BLIND_SEAL.json',dict(experiment='E62',files={p.name:sha(p) for p in b.iterdir()}));bs=sha(b/'BLIND_SEAL.json')
    for channel,ident,code in [('value','v',dict(id='v',category='states_value',values=['A'],evidence='cat')),
                                ('eval','e',dict(id='e',eval_mention=True,evidence='test'))]:
        t=tmp_path/channel;t.mkdir();write(t/'JUDGMENTS.json',[dict(id=ident,status='KEPT',code=code,attempts=0)])
        write(t/'RESULT_SEAL.json',dict(bank='E62',channel=channel,status='TERMINAL_BLIND_GRID_NO_ANALYSIS',packet_seal_sha256=bs,files={'JUDGMENTS.json':sha(t/'JUDGMENTS.json')}))
    v=tmp_path/'value';e=tmp_path/'eval'
    with pytest.raises(ValueError):adapt_files(b,bs,v,sha(v/'RESULT_SEAL.json'),tmp_path/'incomplete')
    adapt_files(b,bs,v,sha(v/'RESULT_SEAL.json'),tmp_path/'complete',e,sha(e/'RESULT_SEAL.json'))
    assert {x['id'] for x in read(tmp_path/'complete/JUDGMENTS.json')}=={'v','e'}


@pytest.mark.parametrize('bank',['E59','E68'])
def test_new_bank_cli_preserves_codes_sources_and_redaction(tmp_path,monkeypatch,bank):
    import sys
    from . import later_runner as runner
    from .judgment_adapter402 import main
    from .privacy79 import redact
    from projects.g_agreement.readerbench.io import read,write,sha,verify
    monkeypatch.setattr(runner,'HERE',tmp_path);write(tmp_path/'RUNNER_SOURCE_SEAL.json',dict(files={}))
    b=tmp_path/'blind';b.mkdir();t=tmp_path/'terminal';t.mkdir()
    packet=[dict(id='a'*32,readout='cat dog '+chr(47)+'tmp'+chr(47)+'file',property='pet',values={'A':'cat','B':'dog'}),dict(id='b'*32,readout='unknown',property='pet',values={'A':'cat','B':'dog'})]
    write(b/'JUDGE_PACKET.json',packet);write(b/'BLIND_SEAL.json',dict(experiment=bank,files={'JUDGE_PACKET.json':sha(b/'JUDGE_PACKET.json')}))
    bs=sha(b/'BLIND_SEAL.json');copies,audit=redact(packet,bank)
    code=dict(id='a'*32,category='states_value',values=['B','A'],evidence='cat dog')
    write(t/'JUDGMENTS.json',[dict(id='a'*32,status='KEPT',code=code,attempts=1),dict(id='b'*32,status='UNPARSEABLE',code=None,attempts=2)])
    write(t/'JUDGE_COPY.json',copies);write(t/'PATH_REDACTION_AUDIT.json',audit)
    args=['adapter','adapt','--blind',str(b),'--blind-sha',bs,'--terminal',str(t),'--out',str(tmp_path/'out')]
    ps=bs
    if bank=='E68':
        c=tmp_path/'converted';c.mkdir();write(c/'PACKET.json',packet)
        write(c/'PACKET_SEAL.json',dict(experiment='E68',source_seal_sha256=bs,source_packet_sha256=sha(b/'JUDGE_PACKET.json'),files={'PACKET.json':sha(c/'PACKET.json')}));ps=sha(c/'PACKET_SEAL.json')
        args+=['--converted',str(c),'--converted-sha',ps]
    write(t/'RESULT_SEAL.json',dict(bank=bank,channel='value',status='TERMINAL_BLIND_GRID_NO_ANALYSIS',packet_seal_sha256=ps,files={p.name:sha(p) for p in t.iterdir()}))
    args+=['--terminal-sha',sha(t/'RESULT_SEAL.json')]
    before={p:sha(p) for folder in (b,t) for p in folder.iterdir()}
    monkeypatch.setattr(sys,'argv',args);main()
    out=tmp_path/'out';verify(out/'JUDGMENT_SEAL.json',sha(out/'JUDGMENT_SEAL.json'))
    flat=read(out/'JUDGMENTS.json');assert flat[0]==code and flat[1]['category']=='UNPARSEABLE'
    for name in ('JUDGE_COPY.json','PATH_REDACTION_AUDIT.json'):assert (out/name).read_bytes()==(t/name).read_bytes()
    assert all(sha(p)==h for p,h in before.items())
    # A changed source cannot be accepted under its former seal.
    (b/'JUDGE_PACKET.json').write_text('[]')
    with pytest.raises(ValueError):main()
