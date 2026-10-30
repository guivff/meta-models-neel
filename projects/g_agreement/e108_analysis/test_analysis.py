import pytest
from . import rules as r,adapter as a

def item(i,choice='a',category='sport',arm='delayed',**hits):
    return dict(id=str(i),category=category,arm=arm,choice=choice,choice_status='ONE',J_fraction=.4,hits=dict(oracle=True,nla=False,outside=False,**hits))

def test_mode_excludes_self_and_ties_are_fixed():
    xs=[item(0,'a'),item(1,'b')]
    assert r.loo_modes(xs)=={'0':0,'1':0}
    xs=[item(0,'a'),item(1,'a'),item(2,'b')]
    assert r.loo_modes(xs)=={'0':1,'1':1,'2':0}

def test_category_pool_and_other_arm_retained():
    xs=[item(0,'a'),item(1,'a',arm='immediate'),item(2,'b',category='animal')]
    assert r.loo_modes(xs)=={'0':1,'1':1,'2':None}

def test_paired_bootstrap_and_max_baseline():
    xs=[item(i) for i in range(20)]
    modes={x['id']:int(int(x['id'])%2==0) for x in xs}
    for x in xs:x['hits'].update(oracle=bool(modes[x['id']]),outside=not modes[x['id']])
    z=r.comparison(xs,'oracle',modes)
    assert z['difference']['estimate']==0 and z['difference']['CI95'][1]==0
    # Max is recomputed inside each draw, yielding a negative lower endpoint.
    assert z['difference']['CI95'][0]<0

def test_missing_not_zero():
    xs=[item(i) for i in range(8)]
    xs[0]['hits']['oracle']=None
    z=r.comparison(xs,'oracle',{x['id']:0 for x in xs})
    assert z['rates']['oracle']['estimate']==1 and z['counts']['oracle']['missing']==1

def test_rules_boundary():
    assert r.verdict(dict(estimate=.15,CI95=[.001,.3]))['R_CH1']=='MET'
    assert r.verdict(dict(estimate=.15,CI95=[0,.3]))['R_CH1']=='NOT MET'
    assert r.verdict(dict(estimate=0,CI95=[0,0]))['falsifier']=='MET'
    assert r.verdict(dict(estimate=None,CI95=None))['R_CH1']=='NOT EVALUABLE'

def test_delayed_non_number_confirmatory_and_gt_exclusions(monkeypatch):
    import numpy as np
    monkeypatch.setattr(r,'bootstrap_ci',lambda v,fn,**kw:(lambda p:(p,p,p))(fn(np.asarray(v))))
    xs=[item(i,choice=str(i)) for i in range(5)]
    xs.append(dict(item(9),choice_status='MULTIPLE',choice=None))
    xs.append(item(10,category='number 1–10'))
    xs[-1]['hits']['oracle']=False
    z=r.analyze(xs,[])
    assert z['excluded']['MULTIPLE']==1
    assert z['readers']['oracle']['rules']['R_CH1']=='MET'
    assert z['readers']['oracle']['cells']['delayed:non_number']['counts']['oracle']['total']==5
    assert z['readers']['nla']['confirmatory'] is False

def test_source_gate_before_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('IO before commit'))
    monkeypatch.setattr('sys.argv',['e108','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_guard_never_replayed(tmp_path):
    s=dict(guard=str(tmp_path/'guard'),analysis=str(tmp_path/'output'),output_sha256='synthetic')
    a.core.claim(s,'synthetic');s['analysis']=str(tmp_path/'other')
    with pytest.raises(FileExistsError):a.core.claim(s,'synthetic')

def test_full_sealed_transport_and_tamper(tmp_path,monkeypatch):
    def bundle(name,files,**meta):
        p=tmp_path/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta);return p/'SEAL.json'
    metas=[]
    for c in r.CATEGORIES:
        for arm in r.ARMS:
            for i in range(42):metas.append(dict(id=f'{c}:{arm}:{i}',kind='native',category=c,arm=arm,prompt_id=str(i)))
    metas.extend(dict(id=f'p{i}',kind='placebo') for i in range(84))
    raw=bundle('raw',{'raw.json':dict(hits=dict(oracle=True,nla=False,outside=False),floor=dict(oracle=True,nla=False),ground_truth=dict(status='ONE',canonical_member='synthetic'),J_fraction=.5,choice_token_offset=4)})
    ms=[]
    for m in metas:
        fields={k:dict(seal_index=0,member='raw.json',keys=[k if k!='hits' or m['kind']=='native' else 'floor']) for k in (('hits','ground_truth','J_fraction','choice_token_offset') if m['kind']=='native' else ('hits',))}
        ms.append(dict(id=m['id'],fields=fields))
    inv=bundle('inv',{'INVENTORY.json':metas},experiment='E108')
    out=bundle('out',{'MEASUREMENTS.json':ms},experiment='E108',status='COMPLETE',inventory_sha256=a.sha(inv),route_verified=True,redaction_audit_complete=True,ground_truth_blind=True,source_seals=[dict(seal=str(raw),sha256=a.sha(raw))],outside_generation=dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',temperature=0,max_tokens=256,ZDR=True,data_collection='deny',fallbacks=False))
    monkeypatch.setattr(a,'ROOT',tmp_path);monkeypatch.setattr(a.subprocess,'check_output',lambda *args,**kw:inv.read_bytes())
    s=dict(inventory_seal=str(inv),inventory_sha256=a.sha(inv),inventory_commit='a'*40,output_seal=str(out),output_sha256=a.sha(out))
    xs,ps=a.inputs(s);assert len(xs)==1008 and len(ps)==84
    (raw.parent/'raw.json').write_text('{}')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(s)


def test_first_output_provenance_uses_actual_result(tmp_path):
    import os
    from .adapter import first_output_provenance,sha
    p=tmp_path/"RESULTS.json";p.write_text("{}")
    ns=1793250000123456789;os.utime(p,ns=(ns,ns))
    r=first_output_provenance(p)
    assert r["first_output_evidence"]==dict(member="RESULTS.json",sha256=sha(p),mtime_ns=p.stat().st_mtime_ns)
    assert r["first_output_utc"].endswith("+00:00")
