from types import SimpleNamespace
from .e108_hits import build_units,choice_offset
from .banks import opaque


def test_whole_inventory_kept_with_explicit_none_multiple_and_failed_extraction():
    native=[dict(id=str(i),kind='native')for i in range(4)]
    inventory=native+[dict(id='p0',kind='placebo')]
    gt=[dict(id=str(i),kind='choice_extract',status='KEPT',code=dict(status=status,canonical_member='dog' if status=='ONE'else None))for i,status in enumerate(('ONE','NONE','MULTIPLE','UNPARSEABLE'))]
    indexed={(r+'_native',str(i)):dict(record=dict(text='A dog.')) for r in ('oracle','nla')for i in range(4)}
    indexed.update({(r+'_placebo','p0'):dict(record=dict(text='A dog.'))for r in ('oracle','nla')})
    outside=[dict(id=opaque('E108','outside',str(i)),phase='generation',status='GENERATED',text='dog',finish_reason='stop',refusal=None)for i in range(4)]
    units,plan,counts=build_units(inventory,indexed,gt,outside,[dict(id='p0',reference_id='0')])
    assert len(units)==5 and len(plan)==5 and counts==dict(ONE=1,NONE=1,MULTIPLE=1,UNPARSEABLE=1)
    assert all(set(x['data'])=={'id','chosen_member','readout'} for x in units)
    assert all(v is None for x in plan[1:4]for v in x['hit_unit_ids'].values())
    assert plan[0]['choice_token_offset'] is None


def test_offset_requires_exact_native_ids_and_unique_literal_member():
    class Tokenizer:
        def decode(self,ids,skip_special_tokens=True):return 'At dog'
        def encode(self,text,add_special_tokens=False):return SimpleNamespace(ids=[10,20],offsets=[(0,2),(2,6)])
    tok=Tokenizer()
    assert choice_offset('At dog',[10,20],'dog',tok)[0]==1
    assert choice_offset('At dog',[11,20],'dog',tok)[0] is None
    assert choice_offset('At dog',[10,20],'canine',tok)[0] is None
