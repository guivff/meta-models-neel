"""CPU-only E97 build. No model, probe, or reader scores are opened."""
import hashlib
import json
from pathlib import Path
import tarfile
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from transformers import PreTrainedTokenizerFast
from rows97 import specifications, render, check
ROOT=Path(__file__).resolve().parent
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj): p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def jsonl(p,records): p.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
def taxonomy(spec):
    row=spec['row']
    if spec['family'] in ('plan','decision_ladder') or row in ('json_key_phase','xml_tag_direction','digit_radix'):
        return 'continuation constraint', 'The active instruction or unfinished syntax constrains the next response/token.'
    if row in ('markdown_heading_level','url_query_index','ipv4_octet','escape_parity'):
        return 'numerical coordinate','The target is a level, position, or parity of a count.'
    return 'binding to earlier context','The target refers to the current earlier event sequence or completed lexical property; it does not prescribe the next token.'
def build():
    assert sha(TOKENIZER)==TOKENIZER_SHA
    dest=ROOT/'cache'/'bank_2026-10-28_v2'
    dest.mkdir(parents=True,exist_ok=False)
    tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
    public=[]; private=[]; qa={}; specs=specifications()
    for spec in specs:
        row=spec['row']; records=[]; ratios=[]
        for t in range(12):
            for f in range(7):
                pair=[]
                for label in 'AB':
                    text=render(row,t,f,label); ids=tok.encode(text,add_special_tokens=False)
                    assert check(row,text)==label
                    assert tok.decode(ids)==text
                    item_id=hashlib.sha256(f'E97|{row}|{t}|{f}|{label}'.encode()).hexdigest()[:24]
                    rec=dict(item_id=item_id,split='dev' if t<6 else 'test',text=text,input_ids=ids,read_position=len(ids)-1)
                    public.append(rec)
                    target=dict(item_id=item_id,row=row,label=label,value=spec['values'][label],template=t,filler=f,split=rec['split'])
                    private.append(target); records.append((rec,target)); pair.append(rec)
                assert pair[0]['input_ids'][-1]==pair[1]['input_ids'][-1], row
                ratio=max(len(p['input_ids']) for p in pair)/min(len(p['input_ids']) for p in pair)
                assert ratio<=1.10,(row,ratio)
                ratios.append(ratio)
        dev=[r for r in records if r[0]['split']=='dev']; test=[r for r in records if r[0]['split']=='test']
        vec=CountVectorizer(); x=vec.fit_transform([r[0]['text'] for r in dev]); y=np.array([r[1]['label']=='A' for r in dev])
        model=LogisticRegression(C=1,random_state=20261028,max_iter=1000).fit(x,y)
        auc=roc_auc_score([r[1]['label']=='A' for r in test],model.predict_proba(vec.transform([r[0]['text'] for r in test]))[:,1])
        assert auc<=.65,(row,auc)
        qa[row]=dict(dev=84,test=84,dev_A=42,test_A=42,max_pair_token_ratio=max(ratios),bow_test_auroc=float(auc),labels_checked=168)
        tag,reason=taxonomy(spec); spec.update(taxonomy=tag,taxonomy_reason=reason,taxonomy_prediction='REPORTED' if tag=='continuation constraint' else 'MISSED')
    assert len(public)==6720 and len({r['item_id'] for r in public})==6720
    jsonl(dest/'PUBLIC_ITEMS.jsonl',public); jsonl(dest/'PRIVATE_LABELS.jsonl',private)
    # Public payload deliberately contains no labels, row mappings, regexes, or forecast tags.
    with tarfile.open(dest/'PUBLIC_CAPTURE.tar.gz','w:gz') as tf:
        tf.add(dest/'PUBLIC_ITEMS.jsonl',arcname='PUBLIC_ITEMS.jsonl')
    write(ROOT/'ROW_LIST.json',dict(experiment='E97',registration='§204 and clarification 1; §205(5)',rows=specs))
    write(ROOT/'BUILD_QA.json',qa)
    write(ROOT/'MANIFEST.json',dict(experiment='E97',seed=20261028,items=6720,test=3360,dev=3360,
        tokenizer_sha256=TOKENIZER_SHA,files={str(p.relative_to(ROOT)):sha(p) for p in dest.iterdir()},
        split='Templates 0–5 dev; 6–11 test. Seven fillers × two values in each template.',
        read_rule='Final token of exact raw prefix, no chat template.',
        public_archive=str(dest/'PUBLIC_CAPTURE.tar.gz'),private_labels=str(dest/'PRIVATE_LABELS.jsonl')))
    request=dict(experiment='E97',status='READY_CAPTURE_ONLY',registration='§204; §205(5)',
        public_archive=str(dest/'PUBLIC_CAPTURE.tar.gz'),public_sha256=sha(dest/'PUBLIC_CAPTURE.tar.gz'),
        cpu_only_targets=str(dest/'PRIVATE_LABELS.jsonl'),readers_test_only=True,
        sites={'Oracle':44,'NLA':42},capture_items=6720,reader_items=3360,
        reader_go=False,forecast_gate='W-lens must commit k=16 pursuit / 200-direction null forecast after capture, before GO.',
        analysis='E75 unchanged pooled-unit analysis; I-5 separately implements §205 R-T1.',
        budget='Integrator admission required within §204 aggregate limits; registered estimate 3 GPU-h and USD15 judging.',
        no_private_files_on_pod=True,regex_primary=True,judge_only_unresolved=True,
        judge_rules='§202 clauses; 25% old-rubric check; registered pinned route only.')
    write(ROOT/'LAUNCH_REQUEST.json',request)
    print(json.dumps({'rows':len(specs),'items':len(public),'max_ratio':max(q['max_pair_token_ratio'] for q in qa.values()),'max_bow':max(q['bow_test_auroc'] for q in qa.values())}))
if __name__=='__main__': build()
