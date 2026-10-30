import json
from pathlib import Path
import numpy as np,torch
from projects.g_agreement.e100.contract import sha,verify
from projects.g_agreement.e120.test_questions import Tiny,Tok
from mats.readers.olens import OracleLens,Sampling
HERE=Path(__file__).parent

def config():return json.loads((HERE/'questions.json').read_text())

def test_frozen_four_rows_questions_sham_and_cpu_scope():
    c=config();assert c['items']==336 and c['readouts']==672 and c['source_block']==44 and c['per_row']==84
    assert c['questions']['targeted_by_row']=={
      'nesting_depth':'What is the current nesting depth? Answer with the value, then one sentence.',
      'indent_level':'What is the current indent level? Answer with the value, then one sentence.',
      'page_range_digit':'What is the current page-range digit? Answer with the value, then one sentence.',
      'fact_recall':'What fact is being recalled? Answer with the value, then one sentence.'}
    assert c['questions']['sham']=="Does this activation indicate that the user's name is Dana? Answer yes or no, then one sentence."
    assert c['labels_on_pod']is False and c['cpu_only_labels']['stage_to_pod']is False
    assert c['launch']['planning_GPU_hours']==.15 and c['judging']['additional_max_USD']==2 and c['launch']['owner']=='Track Q'

def test_actual_native_prompt_swap_all_eight_variants_preserves_slot_scale_greedy():
    c=config();m=Tiny();tok=Tok();lenses=[]
    for row in c['rows']:
        for q in [c['questions']['targeted_by_row'][row],c['questions']['sham']]:
            prompt=c['carrier_prefix']+' '+q;assert prompt.count('{char}')==1 and 'Produce distinct concepts'not in prompt
            o=OracleLens(m,tok,prompt=prompt,alpha=16000,device='cpu');lenses.append(o)
            result=o.verbalize(torch.tensor([[3.,4,0,0]]),44,k=1,sampling=Sampling(temperature=0,max_new_tokens=128),batch=8)
            assert len(result)==len(result[0])==1
            ids,slot=o.carrier(44);assert torch.allclose(m.calls[-1][:,slot],torch.tensor([[9600.,12800,0,0]]))
    assert len(m.calls)==8 and len({id(o._slots)for o in lenses})==8

def test_original336_test_carriers_byte_identical_and_no_answer_labels():
    c=config();p=c['public_input'];root=Path(p['root']);verify(root,'INPUT_SEAL.json',p['input_sha256']);assert sha(p['archive'])==p['archive_sha256']
    xs=json.loads((root/'items.json').read_text());a=np.load(root/'H44.npy',allow_pickle=False);assert a.shape==(336,5120)and a.dtype==np.float32
    assert all(set(x)=={'id','row','vector_index','block','split'}and x['split']=='test'and x['block']==44 and x['vector_index']==i for i,x in enumerate(xs))
    assert all(sum(x['row']==r for x in xs)==84 for r in c['rows'])
    cp=c['cpu_only_labels'];assert sha(cp['path'])==cp['sha256'];ptr=json.loads(Path(cp['path']).read_text())
    src=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e113-inputs-v1/inputs');seal=json.loads((src/'INPUT_SEAL.json').read_text());assert sha(src/'INPUT_SEAL.json')==p['source_seal']and sha(src/'h44.npy')==seal['files']['h44.npy']
    original=np.load(src/'h44.npy',allow_pickle=False)
    assert all(a[i].tobytes()==original[x['original_vector_index']].tobytes()for i,x in enumerate(ptr))
