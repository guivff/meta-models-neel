import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
P=Path(__file__).with_name('e122_logits232.py');s=importlib.util.spec_from_file_location('e122ops',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
R=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/cache/g_agreement/i2/e122_public232_v1/inputs')
def test_full_frozen_public_grid_and_all_four_multitoken_pairs():
 xs,h,c=m.validate(R,m.sha(R/'INPUT_SEAL.json'));assert len(xs)==600 and h.shape==(600,5120);assert len(c['contrasts'])==4;assert any(len(x['positive']['token_ids'])>1 for x in c['contrasts'])
def test_exact_stop_token_and_no_appended_eos():
 c=m.read(R/'CONTRASTS.json');p=next(x for x in c['contrasts']if x['id']=='stop_vs_continue');assert p['positive']['token_ids']==[248046]and p['negative']['token_ids']==[760]
def test_h44_carriers_bit_identical_to_original_sealed_public_projection():
 q=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e120-inputs-v1/decoder/h44.npy');assert m.sha(R/'H44.npy')==m.sha(q)
def test_no_private_labels_or_transplant_gate_execution():
 xs=m.read(R/'items.json');assert all(not({'addressed','genre','matched_set','label','truth','target'}&set(x))for x in xs);source=P.read_text();assert "behaviour(model,[xs[i]for i in ix],part,'continuation')"in source and "T_S_transplants_invoked=False"in source
