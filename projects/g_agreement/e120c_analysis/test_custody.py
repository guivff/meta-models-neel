import copy,json,subprocess
import pytest
from . import adapter as a

def fixture():
    p=json.loads(subprocess.check_output(['git','show','39b111603:projects/g_agreement/e120/questions.json'],cwd=a.ROOT))
    return p,{'private_sha256':p['cpu_only_labels']['sha256']},list(range(400))

def test_original_config_accepts_exact_inventory():
    p,cfg,ids=fixture();a.validate_config(p,cfg,ids,ids)

@pytest.mark.parametrize('fault',['population','prompt','layer','greedy','private','absence'])
def test_config_rejects_custody_changes(fault):
    p,cfg,ids=fixture();test=ids[:]
    if fault=='population':ids[-1]=999
    elif fault=='prompt':p['questions']['sham']='Different question'
    elif fault=='layer':p['reader']['layer']=52
    elif fault=='greedy':p['reader']['temperature']=1
    elif fault=='private':cfg['private_sha256']='wrong'
    elif fault=='absence':p['sham_name_absent_in_all400_original_test_prompts_verified']=False
    with pytest.raises(ValueError):a.validate_config(p,cfg,ids,test)
