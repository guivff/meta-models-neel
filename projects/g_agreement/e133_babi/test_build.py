import copy
from projects.g_agreement.e133_babi.build import questions,twin,replay

def q():
    facts=[(1,'Mary went to the kitchen.'),(2,'John moved to the garden.'),(3,'Mary got the milk there.'),(4,'Mary travelled to the hallway.'),(5,'Mary dropped the milk.')]
    return dict(facts=facts,question='Where is the milk?',answer='hallway')


def test_single_destination_only_and_same_previous_location():
    x=q();before=copy.deepcopy(x);r,reason=twin(x)
    assert reason is None and x==before
    assert r['original_current']=='hallway'and r['twin_current']=='garden'and r['previous']=='kitchen'
    assert r['original_statement']=='Mary travelled to the hallway.'and r['twin_statement']=='Mary travelled to the garden.'
    assert r['original_prompt'].replace('Mary travelled to the hallway.','Mary travelled to the garden.',1)==r['twin_prompt']
    assert r['original_prompt'].endswith('Where is the milk?\nAnswer:')


def test_qa3_historical_questions_never_silently_rewritten():
    x=q();x['question']='Where was the milk before the hallway?'
    assert twin(x)==(None,'not_current_location_question')


def test_unknown_previous_no_alternative_or_mismatch_refused():
    x=q();x['facts']=x['facts'][1:];assert twin(x)[1]=='no_known_previous_location_at_object_movement'
    x=q();x['facts'].pop(1);assert twin(x)[1]=='no_distinct_alternative_already_in_prior_story'
    x=q();x['answer']='office';assert twin(x)[1]=='source_answer_not_reproduced'


def test_final_object_movement_not_later_person_move_after_drop():
    x=q();x['facts'] += [(6,'Mary moved to the office.')]
    r,reason=twin(x);assert reason is None and r['event']['number']==4
    assert r['twin_prompt'].endswith('6 Mary moved to the office.\nWhere is the milk?\nAnswer:')


def test_questions_keep_source_order_and_no_prior_answer_leak():
    text='1 Mary moved to the kitchen.\n2 Where is the milk? \tkitchen\t1\n3 John moved to the garden.\n4 Where is the apple? \tgarden\t3\n1 Mary moved to the office.\n2 Where is the apple? \toffice\t1\n'
    xs=list(questions(text));assert [x['source_line']for x in xs]==[2,4,6]and[x['story']for x in xs]==[1,1,2]
    assert len(xs[1]['facts'])==2 and all('\t'not in s for _,s in xs[1]['facts'])


def test_real_sealed494pairs_public_id_prompt_only_and_literal_single_edit():
    import json,hashlib
    from pathlib import Path
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e133-babi-v1/packet')
    xs=json.loads((root/'public/items.json').read_text());labels=json.loads((root/'cpu_only/LABELS.PRIVATE.json').read_text())
    assert len(labels)==494 and len(xs)==988
    by={x['id']:x for x in xs};assert len(by)==988
    for label in labels:
        a,b=[by[i]['prompt']for i in label['member_ids']]
        prefix=str(label['event']['number'])+' '
        assert a.replace(prefix+label['original_statement'],prefix+label['twin_statement'],1)==b
        assert label['previous']not in (label['original_current'],label['twin_current'])
        assert label['original_current']!=label['twin_current']
        assert label['twin_current']in label['event']['prior_locations']
        assert label['source_split']=='test'and label['question'].startswith('Where is the ')
    assert all(set(x)=={'id','prompt'}for x in xs)
    for d,name in [('public','INPUT_SEAL.json'),('cpu_only','LABEL_SEAL.json')]:
        s=json.loads((root/d/name).read_text())
        for n,h in s['files'].items():assert hashlib.sha256((root/d/n).read_bytes()).hexdigest()==h
