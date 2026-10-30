"""Synthetic receipt validation; no production E40 gate is read."""
import json,math,sys
from pathlib import Path
from dataclasses import asdict
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from followup import verify_pass
from e40_common import sha
from e40_sae import FIXED_CONFIG

@pytest.fixture
def receipt(tmp_path):
    def write(name,obj):
        (tmp_path/name).write_text(json.dumps(obj))
    (tmp_path/'layer44.e40.sae.pt').write_bytes(b'synthetic sealed weight bytes, never loaded')
    cal={'population_tokens':1000000,'heldout_statistics_used':False,'position_zero_included':False,
         'd_model':5120,'median_raw_norm':2.,'outlier_threshold_raw_norm':20.,
         'mean_raw_norm_after_outlier_exclusion':2.,'scale':math.sqrt(5120)/2}
    write('CALIBRATION.json',cal)
    write('CALIBRATION_SEAL.json',{'status':'COMPLETE','before_training_step':1,
        'files':{'CALIBRATION.json':sha(tmp_path/'CALIBRATION.json')}})
    metric={'d_model':5120,'d_sae':65536,'n_tokens':49764,'passed':True,'fvu':.2,'dead_latents':12}
    gate={'experiment':'E40','status':'PASS','request_sha256':'a'*64,
          'sample_sha256':'dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593',
          'primary_gate':'filtered','sae_k':128,'calibration_sha256':sha(tmp_path/'CALIBRATION.json'),
          'sae_checkpoint_sha256':sha(tmp_path/'layer44.e40.sae.pt'),'scale':cal['scale'],
          'metrics':{'filtered':metric,'all_tokens':{'n_tokens':50000,'fvu':.9,'passed':False},'excluded':{'union':236}}}
    training={'experiment':'E40','synthetic':False,'training_tokens':100000000,'optimizer_updates':24415,
              'config':asdict(FIXED_CONFIG),'data_passes':1,'recaptured_training_occurrences':0,
              'checkpoint_selection':'final_only','normalization':{'scale':cal['scale']},
              'sae_checkpoint_sha256':gate['sae_checkpoint_sha256'],'calibration_sha256':gate['calibration_sha256']}
    write('GATE_RESULT.json',gate);write('TRAINING_RESULT.json',training)
    write('GATE.RUN_ONCE.json',{})
    def seal():
        write('OUTPUT_SEAL.json',{'status':'PASS','files':{p.name:sha(p)for p in tmp_path.iterdir()if p.name!='OUTPUT_SEAL.json'}})
    seal()
    return tmp_path,write,seal


def test_complete_filtered_pass_admits_same_rubric_even_when_all_token_fvu_fails(receipt):
    path,_,_=receipt
    result=verify_pass(path,'a'*64)
    assert result['metrics']['n_tokens']==49764 and result['sae_k']==128

@pytest.mark.parametrize('file,key,value',[
    ('GATE_RESULT.json','status','FAIL'),('GATE_RESULT.json','scale',1),
    ('TRAINING_RESULT.json','training_tokens',99999999),('TRAINING_RESULT.json','optimizer_updates',24414),
    ('TRAINING_RESULT.json','synthetic',True),('TRAINING_RESULT.json','data_passes',2),
    ('TRAINING_RESULT.json','recaptured_training_occurrences',1),
    ('CALIBRATION_SEAL.json','before_training_step',2)])
def test_semantic_validity_survives_resealed_bytes(receipt,file,key,value):
    path,write,seal=receipt
    x=json.loads((path/file).read_text());x[key]=value;write(file,x);seal()
    with pytest.raises(ValueError):verify_pass(path,'a'*64)


def test_wrong_request_or_changed_weights_cannot_authorize_decomposition(receipt):
    path,_,_=receipt
    with pytest.raises(ValueError):verify_pass(path,'b'*64)
    (path/'layer44.e40.sae.pt').write_bytes(b'changed')
    with pytest.raises(ValueError):verify_pass(path,'a'*64)


def test_original_fvu_threshold_is_inclusive_and_dead_fraction_is_strict(receipt):
    path,write,seal=receipt
    x=json.loads((path/'GATE_RESULT.json').read_text());x['metrics']['filtered']['fvu']=.25
    write('GATE_RESULT.json',x);seal()
    verify_pass(path,'a'*64)
    x['metrics']['filtered']['dead_latents']=6554
    write('GATE_RESULT.json',x);seal()
    with pytest.raises(ValueError):verify_pass(path,'a'*64)
