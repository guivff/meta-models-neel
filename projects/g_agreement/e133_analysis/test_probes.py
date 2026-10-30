from . import probes


def pairs(n=50):
    out=[]
    for i in range(n):
        ms=[dict(member=j,current='Erin'if j==0 else'Carl',previous='Dana'if i%2==0 else'Evan',vectors={l:[float(j),float(i%2)]for l in probes.LAYERS})for j in (0,1)]
        out.append(dict(pair_id=str(i),generation_index=i,kind='multi_hop',members=ms))
    return out


def test_first30pair_dev_only_both_name_targets_and_no_test_fit(monkeypatch):
    original=probes.LogisticRegression;fits=[]
    class Tracked:
        def __init__(self,**kwargs):self.model=original(**kwargs)
        def fit(self,x,y):
            fits.append(len(x));self.model.fit(x,y);self.classes_=self.model.classes_;return self
        def predict_proba(self,x):return self.model.predict_proba(x)
    monkeypatch.setattr(probes,'LogisticRegression',Tracked)
    r=probes.analyze(pairs(),['Erin','Carl','Dana','Evan'])
    assert fits==[60]*18
    for layer in probes.LAYERS:
        for target in ('twin_identity','current','previous'):
            z=r['layers'][str(layer)][target]
            assert z['dev_pairs']==30 and z['test_pairs']==20
            assert z['groups']['multi_hop_test']['binary_AUROC'if target=='twin_identity'else'macro_ovr_AUROC']==1


def test_under30_dev_and_unseen_target_not_fabricated():
    r=probes.analyze(pairs(29),['Erin','Carl','Dana','Evan']);assert r['layers']['44']['current']['status']=='NOT EVALUABLE'
    xs=pairs()
    for p in xs[30:]:
        for m in p['members']:m['current']='Unseen'
    r=probes.analyze(xs,['Erin','Carl','Dana','Evan','Unseen']);z=r['layers']['44']['current']['groups']['multi_hop_test']
    assert z['unseen_target_n']==40 and z['macro_ovr_AUROC']is None and z['n_evaluable_classes']==0


def test_nonconverged_descriptive_probe_never_refit_or_changes_rnl1(monkeypatch):
    class NoFit:
        def __init__(self,**kwargs):pass
        def fit(self,x,y):raise probes.ConvergenceWarning('fixed fit not converged')
    monkeypatch.setattr(probes,'LogisticRegression',NoFit)
    r=probes.analyze(pairs(),['Erin','Carl','Dana','Evan'])
    assert all(z['status']=='NOT EVALUABLE'for row in r['layers'].values()for z in row.values())
    assert r['threshold_role']=='none of these probe metrics enters R-NL1'


def test_qa2_probe_folds_hold_out_whole_episodes_and_all_twins(monkeypatch):
    xs=pairs(12)
    for i,p in enumerate(xs):
        p.update(kind='babi_qa2',source_episode_id='episode:'+str(i//2))
        for m in p['members']:m['vectors']={44:[float(m['member']),float(i%2),float(i//2)]}
    monkeypatch.setattr(probes,'LAYERS',(44,))
    original=probes.LogisticRegression;fits=[]
    class Tracked:
        def __init__(self,**kwargs):self.model=original(**kwargs)
        def fit(self,x,y):
            self.episodes=set(x[:,2]);fits.append(self.episodes);self.model.fit(x,y);self.classes_=self.model.classes_;return self
        def predict_proba(self,x):
            assert self.episodes.isdisjoint(set(x[:,2]))
            return self.model.predict_proba(x)
    monkeypatch.setattr(probes,'LogisticRegression',Tracked)
    r=probes.episode_cv(xs,['Erin','Carl','Dana','Evan'])
    assert len(fits)==15
    for target in ('twin_identity','current','previous'):
        z=r['layers']['44'][target]
        assert z['n_folds']==5 and all(f['source_episode_overlap']==0 for f in z['folds'])
        assert z['binary_AUROC'if target=='twin_identity'else'macro_ovr_AUROC']==1
    for p in xs:p['source_episode_id']='single-episode'
    assert probes.episode_cv(xs,['Erin','Carl','Dana','Evan'])['layers']['44']['twin_identity']['status']=='NOT EVALUABLE'
