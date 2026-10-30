import pytest
from .judgment_adapter import adapt, bucket


def test_full_values_lossless_both_zero_signed_contribution():
    r={'category':'states_value','values':['A','B']}
    assert adapt(r)['values']==['A','B']
    assert bucket(r,'A')==bucket(r,'B')=='states_value_both'
    assert bucket({'category':'states_value','values':['A']},'A')=='states_value_correct'
    assert bucket({'category':'states_value','values':['A']},'B')=='states_value_wrong'


def test_categories_and_legacy_mapping():
    assert adapt({'category':'names_property_without_value','values':[]})['category']=='names_property_without_value'
    assert adapt({'category':'names_property','value':None})['category']=='names_property_without_value'
    for r in [{'category':'states_value','values':[]}, {'category':'silent','values':['A']},
              {'category':'states_value','values':['A','A']}]:
        with pytest.raises(ValueError):adapt(r)


def test_context_rejects_loss_of_second_value(tmp_path):
    from .contract import dump, sha, seal
    from .judgment_adapter import context_binding
    delivery=tmp_path/'delivery';delivery.mkdir()
    context=tmp_path/'context';context.mkdir()
    codes=[dict(id=str(i),category='states_value',values=['A','B'],evidence=['A','B']) for i in range(336)]
    dump(delivery/'JUDGMENTS.json',codes);seal(delivery,'RESULT_SEAL.json')
    dump(context/'MAP.json',{})
    joined=[dict(x,blind_id=x['id']) for x in codes]
    dump(context/'JUDGMENTS.json',joined)
    cs=dict(judgment_delivery_seal_sha256=sha(delivery/'RESULT_SEAL.json'),private_key_sha256='key')
    dump(tmp_path/'CONTEXT_BINDING.json',dict(cs,map_sha256=sha(context/'MAP.json'),judgment_delivery_path=str(delivery)))
    context_binding(context,cs,tmp_path)
    joined[0]['values']=['A']
    (context/'JUDGMENTS.json').unlink();dump(context/'JUDGMENTS.json',joined)
    with pytest.raises(ValueError,match='delivered judgment changed'):context_binding(context,cs,tmp_path)
