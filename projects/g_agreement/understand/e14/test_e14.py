import numpy as np
from projects.g_agreement.understand.e14.run import label, enacts, states, analyse, RL, SFT

def test_labels():
    assert label('foo (bar')['paren'] and not label('foo (bar) baz')['paren'] and not label(') x')['paren']
    assert label('x = "abc')['quote'] and not label('x = "abc"')['quote'] and not label('"a\nb')['quote']
    assert label('```py\nx')['code'] and not label('```py\nx\n```\n')['code']
    assert label('| a | b')['table'] and not label('a | b')['table']
    assert label('- item')['list'] and label('  2) x')['list'] and not label('text - x')['list']

def test_codes():
    assert enacts('paren', 'and more) then (x') and not enacts('paren', '(a) b')
    assert enacts('quote', 'abc" said') and not enacts('quote', 'abc\n"x')
    assert enacts('table', ' c | d |') and enacts('list', 'x\n- y') and enacts('code', 'y\n```')
    assert states('paren', 'We are inside a parenthetical') and states('table', 'second column of the table')
    assert not states('list', 'the listener')

def test_analyse_signal():
    rows = []
    for i in range(400):
        on = i % 2 == 0
        r = {'left_ctx': 'see (the' if on else 'see the', 'token': ' cat', 'next16': ') ran' if on else ' ran'}
        for c in RL: r[c] = 'thinking about cats'
        for c in SFT: r[c] = ') and then' if on else 'and then'
        rows.append(r)
    res, _ = analyse(rows, np.random.default_rng(0))
    assert res['results']['paren/sft/enacts']['diff_on_minus_off'][0] == 1.0
    assert res['results']['paren/rl/enacts']['diff_on_minus_off'][0] == 0.0
    assert res['results']['paren/next16/enacts']['diff_on_minus_off'][0] == 1.0
