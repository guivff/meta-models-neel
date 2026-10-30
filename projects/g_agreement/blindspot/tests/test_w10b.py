from collections import Counter
import copy
import json
import os
import pytest
from projects.g_agreement.blindspot import w10b_items as B,w10b_dev as D,w10_items as W


@pytest.fixture(scope='module')
def tok():
    p=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    if not p:pytest.skip('pinned Qwen tokenizer required')
    return B.load_pinned_tokenizer(p)


@pytest.fixture(scope='module')
def bank(tok):return B.build(tok)


def test_full_strong_carrier(tok,bank):
    r=B.verify(tok,bank)
    assert r['pairs']==960 and len(r['checks'])==32
    assert all(x['ks_p']==1 and x['mean_token_difference']==0 for x in r['checks'])


@pytest.mark.parametrize('mode',list(B.MODES))
def test_all_three_instruction_spans_and_carrier_identical(tok,bank,mode):
    selected=[x for x in bank if x['meta']['mode']==mode]
    for a,b in zip(selected[::2],selected[1::2]):
        assert a['meta']['instruction_token_spans']==b['meta']['instruction_token_spans']
        for lo,hi in a['meta']['instruction_token_spans']:
            assert hi>lo
        keep=B.np_keep(len(a['ids']),a['meta']['instruction_token_spans'])
        assert [a['ids'][i] for i in keep]==[b['ids'][i] for i in keep]
        assert a['ids'][a['meta']['assistant_start']:]==b['ids'][b['meta']['assistant_start']:]
        text=a['text']
        assert text.count('Operating instruction:')==2
        assert text.count('Acknowledged:')==1


def test_mode_checks_dev_only_balanced_and_family_split(bank):
    ids=set(W.mode_check_ids(bank));chosen=[x for x in bank if x['id'] in ids]
    assert len(chosen)==320 and {x['split'] for x in chosen}=={'dev'}
    assert Counter(x['feature'] for x in chosen)==dict.fromkeys(B.specs(),20)
    for feature,spec in B.specs().items():
        rows=[x for x in chosen if x['feature']==feature]
        assert Counter(x['value'] for x in rows)==dict.fromkeys(spec['values'],10)
        assert len({x['cluster'] for x in rows})==6


def test_real_native_jlens_candidate_support(tok):
    from mats.readers.jlens import token_variants
    for spec in B.specs().values():
        assert len(spec['olens'])==len(spec['nla'])==len(spec['jlens'])==2
        for pair in spec['jlens']:
            for word in pair:assert token_variants(tok,[word]),word


def test_verify_rejects_changed_noninstruction(tok,bank):
    changed=copy.deepcopy(bank);changed[1]['ids'][-1]+=1
    with pytest.raises(ValueError):B.verify(tok,changed)


def synthetic(yes):
    labels={};checks=[];judged=[]
    for feature,spec in B.specs().items():
        for i in range(20):
            key=feature+str(i);labels[key]={'split':'dev','value':spec['values'][i%2]}
            checks.append({'id':key,'feature':feature})
            follows=i<yes
            judged.append({'id':key,'A_follows':follows,'B_follows':follows})
    return labels,checks,judged


@pytest.mark.parametrize('yes,passes',[(15,False),(16,True),(20,True)])
def test_exact_sixteen_of_twenty_gate(yes,passes):
    rows=D.activity(*synthetic(yes),B.specs())
    assert len(rows)==16 and all(r['pass']==passes and r['active']==yes for r in rows)


def test_gate_rejects_test_label_and_wrong_judge_types():
    labels,checks,judged=synthetic(16)
    labels[checks[0]['id']]['split']='test'
    with pytest.raises(ValueError):D.activity(labels,checks,judged,B.specs())
    labels[checks[0]['id']]['split']='dev';judged[0]['A_follows']='true'
    with pytest.raises(ValueError):D.activity(labels,checks,judged,B.specs())


def test_prompt_is_renderable_and_blind_to_expected_value():
    for mode,(a,b) in B.CRITERIA.items():
        p=B.JUDGE_PROMPT.format(pair=mode,criterion_a=a,criterion_b=b,text='"data"')
        assert 'A_follows' in p and 'B_follows' in p
        assert 'ACTUAL VALUE' not in p and 'DISTANCE:' not in p


@pytest.mark.parametrize('active,passes',[(15,False),(16,True)])
def test_gate_reads_separate_labels_with_frozen_source_binding(tmp_path,active,passes):
    """Exercise real stage admission and every seal join, without model calls."""
    P=D.P
    bank=tmp_path/'stage';bank.mkdir()
    labels,checks,judged=synthetic(active)
    label_path=tmp_path/'private'/'labels.DO_NOT_STAGE.jsonl';label_path.parent.mkdir()
    P.jsonl(label_path,[{'id':key,**value} for key,value in labels.items()])
    sources=B.source_hashes();sources[D.DEV_SOURCE_PATH]=D.GATE_FROZEN_DEV_SOURCE
    manifest={'experiment':'W10b','source_files':sources,'labels_sha256':P.sha(label_path)}
    P.dump(bank/'manifest.json',manifest);P.dump(bank/'templates.json',B.specs())
    P.jsonl(bank/'mode_checks.input.jsonl',checks)
    def bank_seal():P.seal(bank,['manifest.json','templates.json','mode_checks.input.jsonl'],'INPUTS_FROZEN_W10B_BEFORE_DEV_MODE_CHECKS')
    bank_seal()
    generations=tmp_path/'generations';generations.mkdir()
    P.jsonl(generations/'mode_generations.jsonl',[{'id':r['id'],'text':'fixture'} for r in checks])
    D.seal(generations,['mode_generations.jsonl'],'MODE_GENERATION_SEAL.json','DEV_GENERATIONS_COMPLETE_BEFORE_CAPTURE')
    P.dump(generations/'SCIENCE_RECEIPT.json',{'elapsed_s':1})
    D.seal(generations,['MODE_GENERATION_SEAL.json','SCIENCE_RECEIPT.json'],'DEV_RUN_SEAL.json','DEV_GENERATION_AND_BUDGET_SEALED')
    packet=tmp_path/'packet';packet.mkdir()
    P.dump(packet/'provenance.json',{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'generation_seal_sha256':P.sha(generations/'MODE_GENERATION_SEAL.json')})
    D.seal(packet,['provenance.json'],'MODE_PACKET_SEAL.json','BLINDED_DEV_MODE_PACKET_FROZEN')
    judge=tmp_path/'judge';judge.mkdir()
    P.jsonl(judge/'judged.jsonl',judged)
    P.dump(judge/'provenance.json',{'packet_seal_sha256':P.sha(packet/'MODE_PACKET_SEAL.json')})
    D.seal(judge,['judged.jsonl','provenance.json'],'MODE_JUDGE_SEAL.json','BLINDED_DEV_JUDGE_COMPLETE')
    out=tmp_path/'out'
    D.gate(bank,generations,packet,judge,label_path,out)
    P.verify(out,'MODE_GATE_SEAL.json')
    result=json.loads((out/'mode_gate.json').read_text())
    assert len(result['rows'])==16
    assert all(r['active']==active and r['pass']==passes for r in result['rows'])
    assert result['mode_rows_passing']==(16 if passes else 0)
    assert not list(bank.glob('*DO_NOT_STAGE*'))
    # An independently changed dependency is still rejected, not silently exempted.
    manifest['source_files']['common/stats.py']='0'*64
    P.dump(bank/'manifest.json',manifest);bank_seal()
    with pytest.raises(ValueError,match='wrong frozen source'):
        D.gate(bank,generations,packet,judge,label_path,tmp_path/'bad-source')
