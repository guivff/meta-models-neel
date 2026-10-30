import json
import pytest
from projects.g_agreement.readerbench.io import read, sha, write, verify
from .e67_packet_adapter import convert


def source(tmp_path):
    p=tmp_path/'source';p.mkdir()
    rubric='Claims rubric\r\nUnicode quotes “é” — preserve.\r\n'.encode()
    (p/'CLAIMS_RUBRIC.txt').write_bytes(rubric)
    records=[]
    for i in (1,2):
        x={'id':str(i)*32,'prompt_text':'  é\r\n“prompt”\t','readout':f'job {i}\n\\literal —  '}
        records.append(x)
        (p/f'packet_{i:02d}.jsonl').write_text(json.dumps(x,ensure_ascii=False)+'\n')
    write(p/'JUDGE_PACKET_SEAL.json',dict(independent_packet_contexts_required=True,files={f.name:sha(f) for f in p.iterdir()}))
    return p,sha(p/'JUDGE_PACKET_SEAL.json'),records,rubric


def test_two_separate_jobs_preserve_every_byte(tmp_path):
    p,digest,records,rubric=source(tmp_path)
    for i in (1,2):
        out=tmp_path/f'job{i}';convert(p,digest,f'packet_{i:02d}.jsonl',out)
        seal=verify(out/'PACKET_SEAL.json',sha(out/'PACKET_SEAL.json'))
        assert seal['packet_id']==f'packet_{i-1}'
        assert seal['source_packet_sha256']==sha(p/f'packet_{i:02d}.jsonl')
        assert (out/'CLAIMS_RUBRIC.md').read_bytes()==rubric
        rows=read(out/'PACKET.json');assert len(rows)==1
        assert set(rows[0])=={'id','prompt','readout','rubric'}
        for old,new in [('id','id'),('prompt_text','prompt'),('readout','readout')]:
            assert rows[0][new].encode()==records[i-1][old].encode()
        assert rows[0]['rubric'].encode()==rubric
    with pytest.raises(FileExistsError):convert(p,digest,'packet_01.jsonl',tmp_path/'job1')


@pytest.mark.parametrize('member',['packet_01.jsonl','packet_02.jsonl','CLAIMS_RUBRIC.txt','JUDGE_PACKET_SEAL.json'])
def test_tampering_fails_before_output(tmp_path,member):
    p,digest,_,_=source(tmp_path)
    with (p/member).open('ab') as f:f.write(b' ')
    with pytest.raises(ValueError):convert(p,digest,'packet_01.jsonl',tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_cannot_merge_packets(tmp_path):
    p,digest,_,_=source(tmp_path)
    with pytest.raises(ValueError):convert(p,digest,'packet_01.jsonl,packet_02.jsonl',tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_wave_two_seal_has_explicit_namespace(tmp_path):
    p,digest,records,rubric=source(tmp_path)
    convert(p,digest,'packet_01.jsonl',tmp_path/'wave1')
    convert(p,digest,'packet_01.jsonl',tmp_path/'wave2',wave=2)
    assert read(tmp_path/'wave1/PACKET.json')==read(tmp_path/'wave2/PACKET.json')
    assert read(tmp_path/'wave1/PACKET_SEAL.json')['wave']==1
    assert read(tmp_path/'wave2/PACKET_SEAL.json')['wave']==2
