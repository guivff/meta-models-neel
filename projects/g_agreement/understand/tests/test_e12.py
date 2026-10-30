import pytest
from projects.g_agreement.understand.e12 import ARMS,user_message,activation_for,carrier


def test_context_identical_across_three_arms_and_native_unchanged():
    native='Native request <activation>MARK</activation>'
    source='Unfinished LaTeX {x + y} (and\n    code'
    assert user_message(native,source,'activation_only')==native
    contexts=[user_message(native,source,a) for a in ARMS[1:]]
    assert contexts[0]==contexts[1]==contexts[2]
    assert source in contexts[0] and contexts[0].index(source)<contexts[0].index('MARK')


def test_text_only_leaves_embedding_untouched_and_wrong_uses_frozen_donor():
    h=object();wrong=object()
    assert activation_for('activation_only',h,wrong) is h
    assert activation_for('text_activation',h,wrong) is h
    assert activation_for('text_only',h,wrong) is None
    assert activation_for('text_wrong_activation',h,wrong) is wrong
    with pytest.raises(ValueError):activation_for('new_arm',h,wrong)


def test_marker_collision_rejected_without_repair():
    class Tok:
        def apply_chat_template(self,turns,**kwargs):return [1]+[7]*turns[0]['content'].count('MARK')+[2]
    with pytest.raises(ValueError,match='once'):carrier(Tok(),'Native MARK','Source MARK','text_only',7)
    ids,slot=carrier(Tok(),'Native MARK','Source','text_only',7)
    assert ids[slot]==7
