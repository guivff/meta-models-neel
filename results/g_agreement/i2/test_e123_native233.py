from pathlib import Path
import importlib.util,json,numpy as np
P=Path(__file__).with_name('e123_native233.py');sp=importlib.util.spec_from_file_location('e123ops',P);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);I=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e123-inputs-v1/inputs')
def test_complete_original_unhooked134_and_both_exact_layers():
 xs,a=m.validate(I,m.sha(I/'INPUT_SEAL.json'));assert len(xs)==134 and set(a)=={44,52}
def test_both_layer_arrays_remain_distinct_and_native_float32():
 xs,a=m.validate(I,m.sha(I/'INPUT_SEAL.json'));assert a[44].dtype==a[52].dtype==np.float32 and not np.array_equal(a[44],a[52])
def test_no_private_labels_or_source_cohort_drop():
 xs=json.loads((I/'items.json').read_text());assert all(set(x)=={'id','vector_index'}and x['vector_index']==i for i,x in enumerate(xs))
def test_existing_native_sweep_only_and_no_recapture_or_judging():
 s=P.read_text();assert "B.sweep(rt,'oracle',h,layer)"in s and 'subject_forward_calls=0'in s and 'judging_calls=0'in s and 'captures=0'in s
