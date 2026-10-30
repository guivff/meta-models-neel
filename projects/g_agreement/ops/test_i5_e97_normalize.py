import pytest
from projects.g_agreement.ops.i5_e97_normalize import assemble

def fixture():
 mapping=[dict(id='a',item_id='item',reader='oracle',row='row',malformed=False,source_sha256='rawA'),dict(id='b',item_id='item',reader='nla',row='row',malformed=True,source_sha256='rawB')]
 labels={'item':dict(row='row',label='A',value='alpha')};rows={'row':dict(values={'A':'alpha','B':'beta'})};primary={'a':dict(id='a',category='states_value',values=['A'],evidence='alpha')};regex={'a':None,'b':'B'};copies={'a':'alpha'};native={'a':'alpha','b':'beta'}
 return mapping,labels,rows,primary,regex,copies,native

def test_exact_ground_truth_and_regex_scope_preserved():
 out=assemble(*fixture());assert [x['label']for x in out]==['A','A'];assert out[0]['code_source']=='judge'and out[1]['code_source']=='frozen_regex';assert out[1]['code']['values']==['B']and out[1]['malformed']
def test_wrong_truth_polarity_refused():
 args=fixture();args[1]['item']['label']='B'
 with pytest.raises(ValueError):assemble(*args)
def test_missing_judgment_never_silent():
 args=fixture();args[3]['a']=dict(id='a',category='UNPARSEABLE',values=[],evidence='');out=assemble(*args);assert out[0]['code']['category']=='UNPARSEABLE'
def test_copy_evidence_context_and_identity():
 args=fixture();args[5]['a']='redacted alpha';args[3]['a']['evidence']='redacted alpha';assert assemble(*args)[0]['code']['evidence']=='redacted alpha'
 args[3]['a']['id']='wrong'
 with pytest.raises(ValueError):assemble(*args)
