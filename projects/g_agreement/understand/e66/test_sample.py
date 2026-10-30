from .sample import classify,choose


def test_states():
    assert classify('```python\nx = "unfinished')[0]=='S1'
    assert classify('```python\nx = call(')[0]=='S2'
    assert classify('```python\nif True:\n        answer = 7')[0]=='S4'
    assert classify('| a | b |\n| --- | --- |\n| x | y,')[0]=='S3'
    assert classify('Ordinary prose about a garden.')[0]=='C'
    assert classify('```python\n# ( " comment')[0] is None
    assert classify('```unknown\nx(')[0] is None
    assert classify('    ambiguous code')[0] is None
    assert classify('```python\nx = "(escaped \\" quote"')[0] is None


def test_sampling():
    candidates={str(i):[{'stratum':'S1' if i<49 else 'C','pos':0,'row':i,'rollout':str(i)}] for i in range(249)}
    selected,counts=choose(candidates)
    assert counts['S1']['selected']==0
    assert counts['C']['selected']==150
    assert len({r['rollout'] for r in selected})==150
    assert (selected,counts)==choose(dict(reversed(list(candidates.items()))))


def test_overlaps_unique():
    candidates={str(i):[{'stratum':s,'pos':j,'row':2*i+j,'rollout':str(i)} for j,s in enumerate(('S1','S2'))] for i in range(300)}
    selected,counts=choose(candidates)
    assert sum(c['eligible_rollouts'] for c in counts.values())==600
    assert counts['S1']['eligible_rollouts']==300
    assert len({r['rollout'] for r in selected})==len(selected)


def test_quote_and_bracket_lexing():
    from .sample import lex
    assert lex('x = "["; f(', 'python')[1]==['(']
    assert lex('/* " ( */ f(', 'js')[1]==['(']
    assert lex('x = """unfinished', 'python')[0]=='"""'
    assert lex('x = ")"', 'python')[3] is False
    assert lex('x = ]', 'python')[3] is True


def test_table_and_fence_boundaries():
    assert classify('```python\nf()\n```\nA prose sentence.')[0]=='C'
    assert classify('| a | b |\nA random | pipe')[0] is None
    assert classify('| a | b |\n| --- | --- |\n| x | y,')[1]['column_index_1based']==2


def test_materializer_is_blind_and_once(tmp_path,capsys):
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from .sample import materialize,sha,dump
    data=tmp_path/'data';out=tmp_path/'out';data.mkdir();out.mkdir()
    pq.write_table(pa.table({'rl_greedy':['SYNTHETIC_FIXTURE_NOT_REAL_READOUT']}),data/'olens_wild_rollouts.parquet')
    dump(out/'COUNTS.json',{'input_sha256':{'olens_wild_rollouts.parquet':sha(data/'olens_wild_rollouts.parquet')},'dataset_revision':'fixture'})
    dump(out/'SELECTION.PRIVATE.json',[{'row':0,'rollout':'fixture','pos':1,'stratum':'S1'}])
    materialize(data,out)
    assert 'SYNTHETIC_FIXTURE' not in capsys.readouterr().out
    packet=json.loads((out/'BLIND_PACKET.jsonl').read_text())
    assert set(packet)=={'id','readout'}
    assert 'stratum' not in packet
    assert json.loads((out/'STRATUM_MAP.PRIVATE.jsonl').read_text())['id']==packet['id']
    import pytest
    with pytest.raises(FileExistsError):materialize(data,out)
