"""CPU-only descriptive audit of existing E24-D outputs, no inference or rule changes."""
from pathlib import Path
import json,hashlib,collections
import numpy as np

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
RUN=ROOT/'cache/g_agreement/understand/e24d/hydxzymqlfryhy/final/out/E24D_NEW_RUN'
BANK=ROOT/'cache/g_agreement/understand/e24d-stage-v1'
PLAN=ROOT/'results/g_agreement/understand/e24d/RUN_PLAN.json'
TOKENIZER=Path('cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
rows=lambda p:[json.loads(x) for x in Path(p).read_text().splitlines()]
def verify(root,name):
    data=read(root/name)
    for n,h in data['files'].items():
        if sha(root/n)!=h:raise ValueError('seal mismatch: '+str(root/n))
    return sha(root/name)

def main():
    seals={'diagnostic':verify(RUN,'DIAGNOSTIC_SEAL.json'),'input':verify(BANK,'INPUT_SEAL.json')}
    plan=read(PLAN)
    assert plan['input_seal_sha256']==seals['input']
    arms={a:rows(RUN/a/'records.jsonl') for a in 'abcd'}
    by={a:{x['id']:x for x in v} for a,v in arms.items()}
    selected=read(BANK/'selected.json');selection={x['id'] for x in selected}
    items={x['id']:x for x in rows(BANK/'items.input.jsonl')};layout=read(BANK/'layout.json')
    original={x['id']:x for x in rows(ROOT/'cache/g_agreement/blindspot/w1-bank/items.DO_NOT_STAGE.jsonl')}
    reference=np.load(BANK/'reference44.npy',mmap_mode='r');order=read(BANK/'reference.order.json')
    for a in 'abcd':
        seals[a]=verify(RUN/a,'CAPTURE_SEAL.json')
        assert len(arms[a])==300 and set(by[a])==selection
        binding=read(RUN/a/'BINDING.json')
        assert binding['input_seal_sha256']==seals['input'] and binding['plan_sha256']==sha(PLAN)
    failed={a:{x['id'] for x in rr if x['cosine']<.999} for a,rr in arms.items()}
    assert not failed['a'] and len(failed['b'])==7 and failed['b']<=failed['c'] and failed['b']==failed['d']
    assert sha(TOKENIZER)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    tokdata=read(TOKENIZER);special={x['id']:x['content'] for x in tokdata['added_tokens'] if x.get('special')}
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(str(TOKENIZER))
    evidence=[]
    for uid in sorted(failed['b'],key=lambda i:by['b'][i]['reference_index']):
        x=items[uid];ids=x['ids'];n=len(ids)
        assert ids==original[uid]['ids'] and order[by['b'][uid]['reference_index']]==uid
        info={}
        for a in 'abcd':
            rr=by[a][uid];batches=[bb for bb in layout[a] if uid in bb['ids']];assert len(batches)==1
            bb=batches[0];position=bb['ids'].index(uid);width=max(len(items[i]['ids']) for i in bb['ids'])
            assert rr['token_count']==n and rr['batch_position']==position and rr['padding_length']==width-n
            info[a]={k:rr[k] for k in ('cosine','padding_length','batch_position','batch_size','batch_unit','batch_start','best_reference_index','best_reference_id','best_cosine')}
            info[a].update(read_position_spec=-1,resolved_read_position=n-1,batch_width=width,
                           right_padding_starts_at=n,read_position_is_padding=False)
        index=by['a'][uid]['reference_index'];ai=[z['id'] for z in arms['a']].index(uid)
        avec=np.load(RUN/'a/acts44.npy',mmap_mode='r')[ai]
        evidence.append({'id':uid,'row':x['feature'],'split':original[uid]['split'],'token_count':n,'read_token_id':ids[-1],
                         'read_token_text':tokenizer.decode(ids[-1:]),'tail_token_ids':ids[-12:],'tail_text':tokenizer.decode(ids[-12:]),
                         'token_ids_sha256':hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),
                         'tokens_identical_to_W1':True,'special_tokens':[{'position':i,'id':t,'text':special[t]} for i,t in enumerate(ids) if t in special],
                         'a_vector_bitwise_equal_to_reference':bool(np.array_equal(avec,reference[index])), 'arms':info})
    groups={}
    for label,subset in [('failed',failed['b']),('passed',selection-failed['b'])]:
        groups[label]={'n':len(subset),'row_counts':dict(collections.Counter(items[i]['feature'] for i in subset)),
                       'token_count_range':[min(len(items[i]['ids']) for i in subset),max(len(items[i]['ids']) for i in subset)],
                       'items_containing_special_tokens':sum(any(t in special for t in items[i]['ids']) for i in subset),
                       'read_token_special':sum(items[i]['ids'][-1] in special for i in subset),
                       'b_zero_padding':sum(by['b'][i]['padding_length']==0 for i in subset),
                       'b_padding_range':[min(by['b'][i]['padding_length'] for i in subset),max(by['b'][i]['padding_length'] for i in subset)],
                       'c_zero_padding':sum(by['c'][i]['padding_length']==0 for i in subset)}
    exact_a=all(np.array_equal(np.load(RUN/'a/acts44.npy',mmap_mode='r')[j],reference[x['reference_index']]) for j,x in enumerate(arms['a']))
    metrics={'authority':'01c5775e §133 items1–2','scope':'CPU-only descriptive; no inference; no registered diagnostic rerun',
             'input_and_output_seals':seals,'plan_sha256':sha(PLAN),'tokenizer_sha256':sha(TOKENIZER),
             'all300_a_vectors_bitwise_equal_to_W1':exact_a,'same_seven_persist_b_c_d':True,'additional_c_only_failures':[by['c'][i] for i in sorted(failed['c']-failed['b'])],'groups_defined_by_b':groups,'failing_items':evidence,
             'code_difference':{'w1_requested_layers':[42,44],'w1_terminal_capture_block':44,'e24_requested_layers':[44,20,60,32,52,28,36,40,48,56,24],'e24_terminal_capture_block':60,
                                'both_read_position':-1,'both_padding':'right','capture_helper':'mats.capture.capture','snapshot_implementation':'cur[L] = _hidden(o).detach(); gathered after terminal capture; detach is not clone'},
             'mechanism_limit':'No read-index, input-token, special-token, padding, batch-size or environment explanation established. Later-forward aliasing is a code-level hypothesis only, not measured on the real model.'}
    (OUT/'COMPARISON.json').write_text(json.dumps(metrics,indent=2)+'\n')
    lines=['# E24-D seven-item CPU comparison','',
           'Verified the input seal, top diagnostic seal and all four arm capture seals, including their arrays and plan/input bindings. No inference or diagnostic rules were rerun. §133 supplies the operational cause-class ruling; the original DIAGNOSIS remains INCONCLUSIVE and unchanged.','',
           f"Arm (a): 300/300 pass and all 300 saved vectors are bitwise identical to W1. Arms (b), (d): seven items fail (three prose_sentence, four latex_item); all seven also fail in (c). Arm (c) has one additional borderline miss: f4fc39ada190712708124ecc, cosine 0.998948902. Thus the seven persist, but the total failure counts are a=0, b=7, c=8, d=7.",'',
           '| ID | Row | Tokens / read index | Read token | cos a | cos b | cos c | cos d | Padding a/b/c/d |',
           '|---|---|---:|---|---:|---:|---:|---:|---|']
    for x in evidence:
        aa=x['arms'];lines.append('| '+x['id']+' | '+x['row']+f" | {x['token_count']} / {x['token_count']-1} | `{x['read_token_id']}` ({x['read_token_text'].strip()}) | "+' | '.join(f"{aa[a]['cosine']:.6f}" for a in 'abcd')+' | '+' / '.join(str(aa[a]['padding_length']) for a in 'abcd')+' |')
    lines+=['','## What differs, and what does not','',
            '- All seven input token arrays exactly match their W1 originals. Every arm requests position −1 and resolves it to token_count−1, before any right padding. No item-index mismatch is present in these inputs.',
            f"- Special tokens do not distinguish the failures: {groups['failed']['items_containing_special_tokens']}/7 failing and {groups['passed']['items_containing_special_tokens']}/293 passing items contain tokenizer-declared special tokens; no failing read token is special.",
            '- Padding is not a sufficient explanation. Three failed items have zero padding in arm (b); all seven still fail in arm (c), whose batches contain one item with zero padding. Across (a)/(b)/(d), their batch positions and padding differ as recorded in COMPARISON.json.',
            '- Counts in the JSON comparison groups are defined by arm (b): 7 failed /293 passed. The extra c-only miss is separately recorded.',
            '- Only prose_sentence and latex_item occur among failures, but both rows also contain passing sampled items. Lengths overlap the passing population; neither row membership nor the recorded length establishes a mechanism.',
            '- Two of seven b-vectors have a different best reference index. Their best cosines are only 0.827874 and 0.966851, both below parity, so remapping does not recover a matching reference. The other five best-match their original index.',
            '- A concrete capture-code difference: W1 capture_and_score requests blocks [42,44], stopping the forward at 44. E24 requests the full grid through 60. Both call the same mats.capture.capture helper and use the same read-position convention.',
            '- That helper saves a detached view, not a clone, of each block output, and gathers the requested positions after the terminal captured block. A later-forward alias/mutation effect is therefore a plausible code hypothesis; this audit does not establish that it occurred. The measured finding is that stopping through the W1 path reproduces h44 and continuing through E24’s path does not on these seven.',
            '', 'The authorised fix should be assessed by the unchanged every-item parity gate. This descriptive audit does not gate relaunch and makes no new causal verdict.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    files=['compare.py','COMPARISON.json','RESULTS.md'];(OUT/'SEAL.json').write_text(json.dumps({'status':'CPU_DESCRIPTIVE_COMPLETE_NO_INFERENCE','files':{n:sha(OUT/n) for n in files}},indent=2)+'\n')
    print(json.dumps({'groups':groups,'all300_a_bitwise':exact_a,'output':str(OUT)},indent=2))

if __name__=='__main__':main()
