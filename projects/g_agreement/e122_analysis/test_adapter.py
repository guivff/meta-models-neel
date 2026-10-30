from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import adapter as a
from .test_rules import cells, ORDER


def document():
    return dict(schema='E122_CONTINUATION_CONTRASTS_V1',E85_bank_seal_sha256=a.E85_BANK_SHA,dev_quartets=50,test_quartets=100,
                contrasts=[dict(id=c,positive=dict(token_ids=[10+i,20+i]),negative=dict(token_ids=[30+i])) for i,c in enumerate(ORDER)])


class Fixture:
    def __init__(self,tmp,monkeypatch):
        self.tmp=tmp;self.cells=cells();self.defs=a.contrasts(document());self.order=ORDER
        monkeypatch.setattr(a,'CANONICAL',tmp/'canonical')
        monkeypatch.setattr(a,'original_cells',lambda *args:deepcopy(self.cells))
        self.cp=self.bundle('contrasts',{'CONTRASTS.json':document()},experiment='E122',status='FROZEN_BEFORE_E122_CAPTURE')
        monkeypatch.setattr(a,'CONTRAST_SHA',a.sha(self.cp))
        prov=dict(e85_bank_seal='synthetic-bank',original_cpu_private_path='synthetic-private',
                  contrast_source_seal=str(self.cp),contrast_source_sha256=a.sha(self.cp))
        self.fp=self.bundle('frozen',{'CONTRASTS.json':document(),'INVENTORY.json':self.cells,
                            'S_PAIRINGS.json':a.rules.same_condition_pairs(self.cells),'PROVENANCE.json':prov},
                            experiment='E122',status='SOURCE_ONLY_CUSTODY_BOUND',block=44,same_value_seed=20261030,
                            source_e85_bank_sha256=a.E85_BANK_SHA,source_e85_private_sha256=a.E85_PRIVATE_SHA,
                            contrast_source_sha256=a.sha(self.cp))
        self.base=dict(frozen_seal=str(self.fp),frozen_sha256=a.sha(self.fp))

    def bundle(self,name,files,**meta):
        p=self.tmp/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta)
        return p/'SEAL.json'

    def output(self,phase,*,test_shift=2.,mutator=None,raw_status='COMPLETE'):
        split='dev' if phase=='dev' else 'test'
        selected=[x for x in self.cells if x['split']==split and (phase!='transplant' or x['addressed']==0)]
        raw=[];index=[];pairs={x['id']:x for x in a.rules.same_condition_pairs(self.cells)}
        for cell in selected:
            record=dict(id=cell['id'],contrast_ids=ORDER,candidate_ids_sha256=a.digest([x['candidate_ids'][0] for x in self.defs]),block=44,condition='0')
            if phase=='transplant':
                refs={}
                for condition,score in [('T',-1.),('S',-2.)]:
                    i=len(raw)
                    raw.append(dict(record,id=a.measurement_id(cell['id'],condition),base_id=cell['id'],condition=condition,
                                    donor_id=pairs[cell['id']][condition+'_donor_id'],pair_logprobs=[[-1000.+score,-1000.]]*4))
                    refs[condition]=dict(seal_index=0,member='raw.json',keys=[i])
                index.append(dict(id=cell['id'],conditions=refs))
            else:
                shifts=[1.,2.,-50.,.1] if phase=='dev' else [90.,test_shift,80.,70.]
                i=len(raw)
                raw.append(dict(record,pair_logprobs=[[-1000.+score*cell['addressed'],-1000.] for score in shifts]))
                index.append(dict(id=cell['id'],ref=dict(seal_index=0,member='raw.json',keys=[i])))
        if mutator:mutator(raw,index)
        rawseal=self.bundle(phase+'_raw',{'raw.json':raw},status=raw_status,experiment='E122',phase='combined_acquisition',
                            contrast_source_sha256=a.sha(self.cp),source_e85_bank_sha256=a.E85_BANK_SHA)
        meta=dict(experiment='E122',status='COMPLETE',phase=phase,frozen_sha256=a.sha(self.fp),block=44,
                  score_mode='full_continuation_logprob_sum',source_seals=[dict(seal=str(rawseal),sha256=a.sha(rawseal))])
        if phase!='dev':
            sp,_=a.phase_seal('dev_selection');meta.update(selection_seal_sha256=a.sha(sp),selected_contrast_id='self')
        if phase=='transplant':
            gp,_=a.phase_seal('native_test');meta.update(gate_seal_sha256=a.sha(gp),supplied_vector_mode=True,vectors_unscaled=True)
        out=self.bundle(phase+'_output',{'MEASUREMENTS.json':index},**meta)
        return dict(self.base,output_seal=str(out),output_sha256=a.sha(out))

    def select(self):
        return a.execute(self.output('dev'),'select-dev','synthetic-commit')

    def gate(self,**kwargs):
        self.select()
        return a.execute(self.output('native_test',**kwargs),'native-test','synthetic-commit')


def test_full_sealed_three_phase_path_all_four_can_be_captured_together(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.gate()
    seal=a.execute(f.output('transplant'),'transplant','synthetic-commit')
    result=a.read(seal.parent/'RESULTS.json')
    assert result['R_BEV2']=='MET' and result['delta']['estimate']==1 and result['fraction_recovered']['estimate']==.5
    assert a.read(a.CANONICAL/'dev_selection/SELECTION.json')['selected_contrast_id']=='self'
    assert a.read(a.CANONICAL/'native_test/RESULTS.json')['native_addressed_shift']['estimate']==2
    for phase in ('dev_selection','native_test','transplant'):
        assert (a.CANONICAL/(phase+'_ONCE.json')).exists()
        p,s=a.phase_seal(phase);a.core.verify(p,a.sha(p))
    assert not (tmp_path/'e105').exists()


def test_non_met_native_gate_does_not_open_transplant_source(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.gate(test_shift=0.)
    monkeypatch.setattr(a,'measurements',lambda *args,**kw:pytest.fail('transplant scores read after failed gate'))
    with pytest.raises(ValueError,match='gate before reading'):
        a.execute(dict(f.base,output_sha256='not-read',output_seal='not-read'),'transplant','synthetic')
    assert not (a.CANONICAL/'transplant_ONCE.json').exists()


def test_selection_required_before_any_native_test_source_read(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(a,'measurements',lambda *args,**kw:pytest.fail('test opened before dev selection'))
    with pytest.raises(FileNotFoundError):a.execute(dict(f.base,output_sha256='never',output_seal='never'),'native-test','synthetic')


def test_modified_selection_fails_before_test(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);sp=f.select()
    a.write(sp.parent/'SELECTION.json',dict(selected_contrast_id='hedge'))
    with pytest.raises(ValueError,match='member mismatch'):
        a.execute(dict(f.base,output_sha256='never',output_seal='never'),'native-test','synthetic')


@pytest.mark.parametrize('kind',['missing','wrong_order','wrong_identity','non_numeric','partial'])
def test_bad_raw_source_grid_order_identity_or_score_fails_before_claim(tmp_path,monkeypatch,kind):
    f=Fixture(tmp_path,monkeypatch);f.select()
    def mutate(raw,index):
        if kind=='missing':index.pop()
        if kind=='wrong_order':raw[0]['contrast_ids']=list(reversed(ORDER))
        if kind=='wrong_identity':raw[0]['id']='wrong'
        if kind=='non_numeric':raw[0]['pair_logprobs'][1][0]=True
    spec=f.output('native_test',mutator=mutate,raw_status='NO_FIT' if kind=='partial' else 'COMPLETE')
    with pytest.raises(ValueError):a.execute(spec,'native-test','synthetic')
    assert not (a.CANONICAL/'native_test_ONCE.json').exists()


def test_wrong_donor_fails_before_transplant_claim(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.gate()
    spec=f.output('transplant',mutator=lambda raw,index:raw[0].update(donor_id=raw[0]['base_id']))
    with pytest.raises(ValueError,match='donor identity'):a.execute(spec,'transplant','synthetic')
    assert not (a.CANONICAL/'transplant_ONCE.json').exists()


def test_claim_is_global_and_exclusive_no_second_statistics(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);spec=f.output('dev');a.execute(spec,'select-dev','synthetic')
    monkeypatch.setattr(a.rules,'select_dev',lambda *args:pytest.fail('second selection statistics'))
    with pytest.raises(ValueError,match='output exists'):a.execute(spec,'select-dev','synthetic')


def test_commit_gate_precedes_any_spec_or_outcome_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda *args:pytest.fail('read before source commit'))
    monkeypatch.setattr('sys.argv',['e122','select-dev','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()


def test_private_input_inventory_cannot_be_written_to_tracked_location(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(a,'committed_file',lambda *args:None)
    monkeypatch.setattr(a.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=1))
    with pytest.raises(ValueError,match='git-ignored'):
        a.freeze(dict(contrast_seal=str(f.cp),contrast_sha256=a.sha(f.cp),contrast_commit='a'*40,
                      e85_bank_seal='synthetic',e85_private='synthetic'),'synthetic')
    assert not (a.CANONICAL/'frozen_inputs').exists()


@pytest.mark.parametrize('pairs',[[float('nan'),-1.],[True,-1.],[[-1.],[-2.]],[-1.],[-1.,-2.,-3.],[1.,-1.]])
def test_raw_pairs_never_accept_nonfinite_boolean_or_shape_repair(pairs):
    with pytest.raises(ValueError):a.pair_score(pairs)
