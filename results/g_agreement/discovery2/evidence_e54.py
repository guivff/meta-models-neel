"""Read-only E54 full native grid and final sealed contextual judgments.

No true labels exported. Run with python -B. Do not serialize private prompts.
"""
import hashlib
import json
from pathlib import Path
from evidence_e67 import WORK, read, digest, verified_read

def load_e54(include_private=False):
    base=WORK/'wt-blindspot-internals'
    job=base/'results/g_agreement/understand/e5354'
    analysis=read(job/'analysis_c9076571_541b23b1/ANALYSIS_SEAL.json')
    agg=verified_read(job/'analysis_c9076571_541b23b1/E54_RESULTS.json',analysis['files']['E54_RESULTS.json'])
    assert (base/'cache/g_agreement/understand/e5354/ANALYSIS_ONCE.json').exists()
    context=base/'cache/g_agreement/understand/e5354/context_c9076571_541b23b1'
    cs=verified_read(context/'INPUT_SEAL.json',analysis['context_seal_sha256'])
    judged=verified_read(context/'JUDGMENTS.json',cs['files']['JUDGMENTS.json'])
    packets=base/'cache/g_agreement/understand/blind_judge/E54_packet'
    ps=read(packets/'RESULT_SEAL.json')
    public=verified_read(packets/'JUDGE_PACKET.json',ps['files']['JUDGE_PACKET.json'])
    public={x['id']:x for x in public}
    source=base/'cache/g_agreement/understand/e5354/verified_output_d8z2quqdxth285'
    ss=verified_read(source/'OUTPUT_SEAL.json',analysis['output_seal_sha256'])
    inputs=base/'cache/g_agreement/understand/e5354/bound_inputs_21a39c48'
    ins=verified_read(inputs/'INPUT_SEAL.json',ss['input_seal_sha256'])
    items=verified_read(inputs/'e54_items.json',ins['files']['e54_items.json'])
    items={x['id']:x for x in items if x['split']=='test'}
    out=[]
    defs={'reasoning_bridge':{'A':'cat','B':'dog'},'injection_awareness':{'A':'directly from the user','B':'quoted tool output'}}
    for j in judged:
        item=items[j['id']]
        reader={'olens':'oracle','nla':'nla'}[j['reader']]
        p=public[j['blind_id']]
        assert hashlib.sha256(p['readout'].encode()).hexdigest()==j['raw_sha256']
        row=item['feature']
        r=dict(bank='E54',reader=reader,feature=row,property=row,values=defs[row],
            opaque_id=p['id'],pair_id=hashlib.sha256(('E54|'+item['id']).encode()).hexdigest()[:24],
            text=p['readout'],judge={'category':j['category'],'values':j['values'],'evidence':j['evidence'],
            'status':'SEALED_FINAL_CONTEXT'},probe=next(x['probe'] for x in agg['rows'] if x['row']==row))
        if include_private:r['_prompt']=item['text']
        out.append(r)
    assert len(out)==336
    return out
