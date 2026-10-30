import importlib.util,copy
s=importlib.util.spec_from_file_location('custody','results/g_agreement/i2/e117_token_custody236.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def trace(n):return [dict(generated_position=i,norm_ratio=i+.5)for i in range(n)]
def test_early_and_long_rows():
 assert m.project([3,9,0,0],trace(3),[9])['token_ids']==[3,9]
 assert m.project([3,4,5,9],trace(3),[9])['token_ids']==[3,4,5,9]
def test_true_generated_repetition_retained():assert m.project([4,4,4,4,9],trace(4),[9])['token_ids']==[4,4,4,4,9]
def test_no_eos_unchanged():assert m.project([1,2,3],trace(2),[9])['token_ids']==[1,2,3]
def test_first_eos_once():assert m.project([9,9,9],trace(2),[9])['token_ids']==[9]
def test_input_immutable():
 a=[1,9,0];b=trace(2);old=copy.deepcopy((a,b));v=m.project(a,b,[9]);v['norm_trace'][0]['norm_ratio']=100;assert(a,b)==old
def test_hook_off_by_one():
 assert m.project([1,2,9,0],trace(3),[9])['norm_trace']==trace(2)
 assert m.project([9,0],trace(1),[9])['norm_trace']==[]
def test_reject_noncontiguous():
 try:m.project([1,2,9],[dict(generated_position=1),dict(generated_position=2)],[9])
 except ValueError:return
 raise AssertionError('bad trace accepted')
for k,v in list(globals().items()):
 if k.startswith('test_'):v()
print('7 custody-only synthetic tests PASS; no real outputs used')
