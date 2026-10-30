"""Recipe/fixture tests only; no screen selection or production §84 bank."""
import hashlib
import json
import os
from pathlib import Path
import pytest
from projects.g_agreement.blindspot import w1b_items as W
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.items import Feature


def test_registry_snapshot_and_twelve_authored_frames():
    root=Path(W.__file__).parent/'w1b'
    origin=json.loads((root/'REGISTRY_ORIGIN.json').read_text())
    assert P.sha(root/'registry_features.py')==origin['sha256']
    assert len(W.S.BY_ID)==138 and len(set(W.FRAMES))==12
    for feature in W.S.BY_ID.values():
        spec=W.StatementFeature('prose',feature.kind,('present','absent'),(feature.positive,feature.negative),('true','false'))
        for reader in ('olens','nla'):
            pairs=spec.pairs(reader)
            assert len(pairs)==2 and pairs[0]!=pairs[1]
            assert all(feature.positive in a and feature.negative in b for a,b in pairs)


@pytest.mark.parametrize('feature',list(W.S.BY_ID))
def test_every_frozen_feature_has_correct_prototype_recipes(feature):
    for t in range(12):
        for side in (True,False):
            text=W.witness(feature,side,t)
            assert W.S.extract(text,W.domain(feature))[feature] is side


def test_selection_is_required_before_build_or_tokenizer_load(tmp_path,monkeypatch):
    from projects.g_agreement.blindspot import analysis
    receipt={'source_commit':'a'*40,'selection_sha256':'b'*64,'selection_file':'selection.json',
             'section79_features':['inside_fence'],'section81_features':[]}
    path=tmp_path/'receipt.json';P.dump(path,receipt)
    monkeypatch.setattr(W.subprocess,'check_output',lambda *a,**kw:b'["word_nonascii"]')
    with pytest.raises(ValueError,match='bytes'):W.selection(path)
    receipt['selection_sha256']=hashlib.sha256(b'["word_nonascii"]').hexdigest();P.dump(path,receipt)
    with pytest.raises(ValueError,match='list differs'):W.selection(path)
    receipt['section79_features']=['word_nonascii'];P.dump(path,receipt)
    assert W.selection(path)[1]==['word_nonascii']


def test_dynamic_registry_uses_same_freeze_and_donor_protocol(tmp_path):
    f='synthetic_fixture';items=[]
    for split in ('dev','test'):
        for value in ('present','absent'):
            items.append({'id':split+value,'feature':f,'class':'semantic','domain':'prose','split':split,
                'cluster':split,'value':value,'ids':[1],'text':split+value,
                'meta':{'pair_id':split,'template_index':0 if split=='dev' else 1}})
    spec=Feature('prose','semantic',('present','absent'),('a fixture property','no fixture property'),('true','false'))
    out=tmp_path/'bank'
    P.write_bank(out,items,{},tmp_path,experiment='W1b',selection_receipt={'fixture':True},
                 feature_registry={f:spec},native_pairs={f:W.NATIVE_PAIRS})
    seal=P.verify(out,'INPUT_SEAL.json');templates=json.loads((out/'templates.json').read_text())
    assert templates[f]['kind']=='binary' and templates[f]['jlens']==W.NATIVE_PAIRS
    rows=P.rows(out/'items.input.jsonl')
    assert all(r['donor_id']!=r['id'] and r['donor_id'] in {x['id'] for x in rows} for r in rows)
    assert 'labels.DO_NOT_STAGE.jsonl' not in seal['files']


def test_real_qwen_matches_and_rechecks_all_feature_template_prototypes():
    tokenizer=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    if not tokenizer:pytest.skip('set BLINDSPOT_QWEN_TOKENIZER to pinned local Qwen tokenizer')
    from transformers import AutoTokenizer
    from mats.readers.jlens import token_variants
    path=Path(tokenizer);assert P.sha(path/'tokenizer.json')==W.TOKENIZER_SHA256
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
    for feature in W.S.BY_ID:
        for template in range(12):
            for variant in range(7):
                pair=W.matched_pair(tok,feature,template,variant)
                assert len(pair[0][1])==len(pair[1][1])
                assert all(W.S.extract(text,W.domain(feature))[feature] is side
                           for (text,ids),side in zip(pair,(True,False)))
    assert all(token_variants(tok,[word]) for pair in W.NATIVE_PAIRS for word in pair)
    # Representative fixture populations exercise the final bank's 168-item design.
    fixture_items=W.build(tok,['inside_fence','line_index_ge_2','lexicon_obligation'])
    checks=W.verify_lengths(tok,fixture_items)
    assert len(fixture_items)==504 and len(checks['checks'])==6
    assert all(c['ks_p']==1 and c['mean_token_difference']==0 for c in checks['checks'])
