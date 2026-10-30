from projects.g_agreement.understand.e13.evidence_audit import classify


def test_token_and_property_are_not_forced_binary():
    pat=r'\bnumber\b'
    assert classify('final token “4500”',pat)['bucket']=='token_like_only'
    assert classify('a number',pat)['bucket']=='property_name_only'
    assert classify('the final token is a number',pat)['bucket']=='both'
    assert classify('some unclear evidence',pat)['bucket']=='neither'


def test_bare_tokens_and_empty_evidence():
    pat=r'\bcolons?\b'
    assert classify('4500',pat)['bare_lexeme']
    assert classify('“hello”',pat)['bare_lexeme']
    assert classify(':',pat)['bare_lexeme']
    assert classify('colon',pat)['bucket']=='property_name_only'
    assert classify('',pat)['bucket']=='neither'
