import copy
import pytest
from .analysis import summarize

def boot(x):
    m=sum(x)/len(x)
    return m,m,m

def packet(items):
    ts=[];js=[]
    for i,(cells,b,t,has) in enumerate(items):
        for p,v in enumerate(cells):
            ident=f'{i}_{p}'
            ts.append(dict(id=ident,status='KEPT' if v else 'UNPARSEABLE',result={'verdict':v} if v else None))
            js.append(dict(id=ident,family='row',item_id=str(i),position=p,belief=b,truth=t,has_truth=has))
    return ts,js

def test_equal_items_not_positions():
    r=summarize(*packet([(['YES']*9,True,False,True),(['NO'],True,False,True),(['YES'],False,True,True)]),bootstrap=boot)
    b=r['pooled']['belief_stating'];assert b['categories']['YES']['item_rate']==.5
    assert b['categories']['YES']['readout_rate']==.9
    assert r['pooled']['descriptive_reading']=='MET'

def test_unknown_preserved():
    r=summarize(*packet([(['NO'],None,False,True),(['YES'],False,True,True)]),bootstrap=boot)
    assert r['pooled']['unknown_classification_items']==1
    assert r['pooled']['descriptive_reading']=='NOT EVALUABLE'

def test_missing_position_excludes_whole_item():
    r=summarize(*packet([(['NO',None],True,False,True),(['YES'],False,True,True)]),bootstrap=boot)
    b=r['pooled']['belief_stating'];assert b['n_incomplete_items']==1 and b['n_missing_positions']==1
    assert b['categories']['YES']['item_rate'] is None
    assert r['pooled']['descriptive_reading']=='NOT EVALUABLE'

def test_both_remains_in_both_groups():
    r=summarize(*packet([(['YES'],True,True,True)]),bootstrap=boot)['pooled']
    assert r['both_stating_items']==1
    assert r['belief_stating']['n_items']==r['truth_stating']['n_items']==1

def test_no_truth_descriptive_separate():
    r=summarize(*packet([(['YES'],True,None,False),(['NO'],True,False,True),(['YES'],False,True,True)]),bootstrap=boot)['pooled']
    assert r['no_canonical_truth']['n_items']==1
    assert r['belief_stating']['n_items']==1 and r['descriptive_reading']=='MET'

def test_all_three_categories():
    r=summarize(*packet([(['YES','NO','OFF-TOPIC'],True,False,True)]),bootstrap=boot)['pooled']['all_items']
    assert all(x['item_rate']==1/3 for x in r['categories'].values())

def test_duplicate_and_missing_ids_rejected():
    t,j=packet([(['YES'],True,False,True)])
    with pytest.raises(Exception):summarize(t+t,j+j,bootstrap=boot)
    with pytest.raises(Exception):summarize([],j,bootstrap=boot)

def test_changed_group_labels_rejected():
    t,j=packet([(['YES','NO'],True,False,True)]);j[1]['belief']=False
    with pytest.raises(Exception):summarize(t,j,bootstrap=boot)

def test_unknown_verdict_and_null_schema_rejected():
    t,j=packet([(['MAYBE'],True,False,True)])
    with pytest.raises(Exception):summarize(t,j,bootstrap=boot)
    t[0].update(status='REFUSED',result={'verdict':'NO'})
    with pytest.raises(Exception):summarize(t,j,bootstrap=boot)

def test_real_bootstrap_small_synthetic():
    r=summarize(*packet([(['NO'],True,False,True),(['YES'],False,True,True)]))
    assert r['pooled']['belief_stating']['categories']['YES']['item_ci95']==[0,0]

def test_original_mention_both_and_missing():
    from projects.g_agreement.e82_analysis.analyze import mention
    assert mention(None,'A') is None
    assert mention({'category':'states_value','values':['A','B']},'A') is True
    assert mention({'category':'states_value','values':['A','B']},'B') is True

def test_uncommitted_source_blocks_before_guard(tmp_path,monkeypatch):
    from . import adapter
    from projects.g_agreement.readerbench.io import write,sha
    (tmp_path/'x.py').write_text('x=1\n')
    write(tmp_path/'SOURCE_RECEIPT.json',{'files':{'x.py':sha(tmp_path/'x.py')}})
    monkeypatch.setattr(adapter,'ROOT',tmp_path);monkeypatch.setattr(adapter,'HERE',tmp_path)
    monkeypatch.setattr(adapter,'GUARD',tmp_path/'GUARD')
    monkeypatch.setattr(adapter.subprocess,'check_output',lambda *a,**k:b'x=2\n')
    with pytest.raises(ValueError,match='committed report source'):adapter.report(tmp_path/'absent')
    assert not (tmp_path/'GUARD').exists()
