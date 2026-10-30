import copy,pytest
from projects.g_agreement.e133.public import compile_items,VALUES
class Tok:
    def encode(self,s,add_special_tokens=False):
        vals=sum((list(v)for v in VALUES.values()),[])
        if s.startswith(' ')and s[1:]in vals:return [100+vals.index(s[1:])]
        if ' 'in s and s.rsplit(' ',1)[1]in vals:
            a,b=s.rsplit(' ',1);return self.encode(a)+self.encode(' '+b)
        return list(range(1,13))

def rows(n):return [dict(id=str(i),prompt='original read by')for i in range(n)]

def test_public_roles_never_read_or_staged_constant45pairs_all900():
    p=rows(900);before=copy.deepcopy(p);x=compile_items(p,Tok(),'synthetic','screen')
    assert p==before and len(x)==900 and len(x[0]['candidate_ids'])==45
    assert all(v['candidate_ids']==x[0]['candidate_ids']for v in x)
    assert all(v['family']=='multi_hop'for v in x[:600])and all(v['family']=='one_hop'for v in x[600:])
    assert x[0]['pair_id']==x[1]['pair_id']!=x[2]['pair_id']
    assert not any({'current','previous','label','target'}&set(v)for v in x)


def test_babi_constant15pairs_separate_family_main42maximum():
    x=compile_items(rows(84),Tok(),'babi','main');assert len(x)==84 and len(x[0]['candidate_ids'])==15
    assert {r['family']for r in x}=={'babi'}
    with pytest.raises(ValueError):compile_items(rows(86),Tok(),'babi','main')


def test_reject_private_fields_or_malformed_rosters():
    x=rows(900);x[0]['target']='secret'
    with pytest.raises(ValueError,match='ONLY'):compile_items(x,Tok(),'synthetic','screen')
    with pytest.raises(ValueError):compile_items(rows(899),Tok(),'synthetic','screen')
    with pytest.raises(ValueError):compile_items(rows(84),Tok(),'synthetic','main')


def test_never_truncate_multitoken_global_candidate():
    class Bad(Tok):
        def encode(self,s,add_special_tokens=False):return [1,2]if s==' Alice'else super().encode(s,add_special_tokens)
    with pytest.raises(ValueError,match='single token'):compile_items(rows(900),Bad(),'synthetic','screen')


def test_babi_validation_and_main_allfive_patch_blocks(tmp_path):
    import contextlib,json
    from projects.g_agreement.e133.runner import validate_items,main_job
    from projects.g_agreement.e127.test_runner import Tiny,Tok as DecodeTok
    xs=compile_items(rows(2),Tok(),'babi','main')
    # Synthetic model vocab32: retain structural global equality with tiny pairs.
    for x in xs:x['candidate_ids']=[[[3],[4]]]
    assert validate_items(xs,'main')['babi']==1
    class Runtime:
        def __init__(self):self.model=Tiny();self.tok=DecodeTok()
        def subject(self):return self.model,self.tok,contextlib.nullcontext()
        def load_oracle(self):pass
        def sweep(self,r,h,L):return [dict(text='synthetic')for _ in h]
    assert main_job(Runtime(),xs,tmp_path/'babi',lambda*a:True,gpu_type='synthetic')=='COMPLETE'
    s=json.loads((tmp_path/'babi/OUTPUT_SEAL.json').read_text());ix=json.loads((tmp_path/'babi/INDEX.json').read_text())
    assert s['arm']=='babi'and sum(v['kind']=='patch'for v in ix)==30
    assert {v['block']for v in ix if v['kind']=='patch'}=={44,48,52,56,60}
