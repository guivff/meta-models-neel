import pytest
from . import amendment1 as a


def rows():
 return [dict(id=str(i),flips={'2':False,'4':i<42,'6':True,'8':True},clean_old44=int(i>=42),answer_margin=float(i>=42),random_old44_4=1,random_old44_6=1,random_old44_8=1) for i in range(84)]


def test_exact_group_rate_difference():
 r=a.groups(rows());assert r['group_counts']['easy']==42 and r['group_counts']['resistant']==42
 assert r['quantities']['clean_old44']['difference']['estimate']==1
 assert r['quantities']['clean_old44']['difference']['CI95']==[1,1]
 assert r['quantities']['clean_old44']['resistant']['Wilson95'][0]>.9


def test_missing_retained():
 rs=rows();rs[42]['clean_old44']=None;r=a.groups(rs)
 assert r['quantities']['clean_old44']['resistant']['n']==41 and r['quantities']['clean_old44']['resistant']['missing_n']==1


def test_unknown_earlier_not_resistant():
 r=rows()[42];r['flips']['2']=None;assert a.group(r) is None


def test_nonflipper_not_resistant():
 r=rows()[42];r['flips']['6']=False;assert a.group(r) is None


def test_displacement():assert a.displacement([3,4],[6,8])==1


def test_absent_vectors():assert a.displacement(None,None) is None

@pytest.mark.parametrize('x,y',[([0,0],[1,1]),([1],[1,2]),([float('nan')],[1])])
def test_invalid_vectors(x,y):
 with pytest.raises(ValueError):a.displacement(x,y)


def test_gain_identical():
 r=a.gain_ci([0,0,1,1],[0,1,2,3],[0,1,2,3]);assert r['estimate']==0 and r['CI95']==[0,0]


def test_loo_train_class_unknown():assert a.loo_predictions([[0],[1],[2]],[0,0,1]) is None


def test_loo_separable():
 p=a.loo_predictions([[i] for i in range(8)],[0]*4+[1]*4);assert len(p)==8


def test_duplicate_identity_rejected():
 rs=rows();rs[0]['id']=rs[1]['id']
 with pytest.raises(ValueError):a.groups(rs)

def test_nonliteral_flags_rejected():
 rs=rows();rs[0]['flips']['4']=1
 with pytest.raises(ValueError):a.groups(rs)

def test_wholly_missing_stays_unknown():
 rs=rows()
 for r in rs:r['clean_old44']=None
 got=a.groups(rs)['quantities']['clean_old44']
 assert got['easy']['estimate'] is None and got['difference']['CI95'] is None

def test_models_unknown_without_required_predictors():
 rs=rows()
 for r in rs:r.update(probe_unhooked=None,displacement8=None,old44_alpha8=0)
 result=a.models(rs)
 assert not result['endpoints']['old44_alpha8']['deck_phrase_eligible']
 assert result['endpoints']['resistant']['models']['joint']['kept']==0

def test_groups_guard_checked_before_inputs(tmp_path,monkeypatch):
 from . import groups_run as g
 root=tmp_path/'wt-wmech2';root.mkdir()
 monkeypatch.setattr(g,'ROOT',root);monkeypatch.setattr(g,'source_check',lambda:None)
 guard=tmp_path/'wt-wmech/cache/g_agreement/understand/companions248/C_GROUPS_AMENDMENT1_ONCE.json'
 guard.parent.mkdir(parents=True);guard.write_text('{}')
 s=tmp_path/'spec.json';s.write_text('{"status":"COMPLETE","reviewer_source_delivered":true}')
 monkeypatch.setattr(g,'source_rows',lambda s:pytest.fail('consumed guard must stop before sources'))
 with pytest.raises(ValueError,match='consumed'):g.main(s)


def test_e131_crosswalk_is_exact_source_not_alias_guess(tmp_path):
 from . import groups_run as g
 p=tmp_path/'join.json';p.write_text('{"records":[]}')
 with pytest.raises(ValueError,match='original W-text'):g.e131_crosswalk(p,set())


def test_model_gain_target_is_staleness_not_best_endpoint(monkeypatch):
 rs=rows()
 for i,r in enumerate(rs):r.update(probe_unhooked=float(i),displacement8=1.,old44_alpha8=i%2)
 monkeypatch.setattr(a,'loo_predictions',lambda x,y:[float(v) for v in y])
 monkeypatch.setattr(a,'auc_ci',lambda x,y:{'estimate':1.})
 calls=iter([dict(estimate=.2,CI95=[.1,.3]),dict(estimate=.2,CI95=[.1,.3]),dict(estimate=.04,CI95=[.01,.1]),dict(estimate=.2,CI95=[.1,.3])])
 monkeypatch.setattr(a,'gain_ci',lambda *args:next(calls))
 r=a.models(rs)
 assert r['endpoints']['resistant']['deck_phrase_eligible'] is True
 assert r['endpoints']['old44_alpha8']['deck_phrase_eligible'] is False
 assert r['deck_phrase']=='susceptibility to steering predicts it'

def test_final_never_recomputes_groups(monkeypatch):
 from . import final_run as f
 rs=rows()
 for r in rs:r.update(displacement8=1.,displacement6=None)
 monkeypatch.setattr(a,'groups',lambda *x:pytest.fail('must reuse group seal'))
 monkeypatch.setattr(f.predictors,'analyze',lambda r:dict(PRIVATE_TABLE=[],deck_phrase_eligible=True))
 monkeypatch.setattr(a,'models',lambda r:{'tested':'elsewhere'})
 z=f.summarize(rs)
 assert z['group_results_recomputed'] is False
 assert z['displacement_by_group']['displacement6']['easy']['n']==0
 assert z['displacement_by_group']['displacement8']['difference']['estimate']==0
