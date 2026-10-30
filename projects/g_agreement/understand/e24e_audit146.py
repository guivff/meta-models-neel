"""§146 descriptive CPU audit of sealed captures; no registered analysis rerun."""
import argparse,json
from pathlib import Path
import numpy as np
from projects.g_agreement.blindspot import protocol as P
from .e24_environment import cosines
from .e24_worker import seal

def audit(bank,source,out):
    P.verify(bank,'INPUT_SEAL.json');P.verify(source,'DIAGNOSTIC_SEAL.json');P.verify(source,'ANALYSIS_SEAL.json')
    selection=json.loads((bank/'selected.json').read_text());ids=[x['id'] for x in selection]
    acts={};records={}
    for arm in ('A','C','D'):
        P.verify(source/arm,'CAPTURE_SEAL.json');binding=json.loads((source/arm/'BINDING.json').read_text())
        assert binding['input_seal_sha256']==P.sha(bank/'INPUT_SEAL.json')
        records[arm]=P.rows(source/arm/'records.jsonl');assert [x['id'] for x in records[arm]]==ids
        acts[arm]=np.load(source/arm/'acts44.npy',allow_pickle=False)
    ref=np.load(bank/'reference44.npy',allow_pickle=False)[[x['reference_index'] for x in selection]]
    wc=cosines(ref,acts['C']);wd=cosines(ref,acts['D']);cd=cosines(acts['C'],acts['D'])
    inputs={x['id']:x for x in P.rows(bank/'items.input.jsonl')};layout=json.loads((bank/'layout.json').read_text())['A'];padding={}
    for b in layout:
        width=max(len(inputs[u]['ids']) for u in b['ids'])
        for pos,uid in enumerate(b['ids']):
            if uid in ids:padding[uid]=(width-len(inputs[uid]['ids']),pos,b['unit'],b['start'])
    rows=[]
    for i,(x,a) in enumerate(zip(selection,records['A'])):
        uid=x['id'];pad,pos,unit,start=padding[uid]
        assert a['padding_length']==pad and a['batch_position']==pos and a['batch_unit']==unit and a['batch_start']==start
        assert a['token_count']==len(inputs[uid]['ids']) and x['row']==inputs[uid]['feature']
        if wc[i]<.999:rows.append({'id':uid,'row':x['row'],'length':len(inputs[uid]['ids']),'W1_batch_padding':pad,
            'cos_W1_C':float(wc[i]),'cos_W1_D':float(wd[i]),'cos_C_D':float(cd[i]),'W1_unit':unit,'W1_batch_start':start,'W1_batch_position':pos})
    assert len(selection)==500 and len(rows)==18
    old=json.loads((source/'DECISION.json').read_text());assert old['below_0999']['C']==len(rows)
    out.mkdir(parents=True,exist_ok=False)
    P.jsonl(out/'MISMATCHES.jsonl',rows)
    summary={'n':500,'threshold':.999,'C_D_agree':int(sum(cd>=.999)),'C_D_disagree':int(sum(cd<.999)),
        'C_D_minimum_cosine':float(min(cd)),'W1_C_mismatches':len(rows),'mismatches_W1_C_below_099':sum(x['cos_W1_C']<.99 for x in rows),
        'sensitivity_triggered':bool(any(x['cos_W1_C']<.99 for x in rows)),
        'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'diagnostic_seal_sha256':P.sha(source/'DIAGNOSTIC_SEAL.json'),
        'original_analysis_seal_sha256':P.sha(source/'ANALYSIS_SEAL.json'),'code_sha256':P.sha(Path(__file__)),
        'registered_analysis_rerun':False,'model_calls':0,'padding_source':'OriginalW1-neighbourA layout independently reconstructed and matched to sealed A records'}
    P.dump(out/'SUMMARY.json',summary)
    lines=['# §146: 18 C-versus-W1 mismatches','',f"C/D agreement: **{summary['C_D_agree']}/500** at cosine ≥0.999; {summary['C_D_disagree']} fail. Minimum cosine {summary['C_D_minimum_cosine']:.9f}.",'',
      f"**Sensitivity trigger: {summary['mismatches_W1_C_below_099']}/18 have cos(W1,C)<0.99.** This is not the all-≥0.99 bf16-only branch. The G-mode release stands; sealed verdicts remain unchanged.",'',
      'Padding is the count of right-pad tokens in the original W1 batch, verified against the sealed A layout. Cosines use W1’s stored vectors, not arm A as a substitute. JSONL retains full precision and original unit/batch position.','',
      '| ID | Row | Tokens | W1 padding | cos(W1,C) | cos(W1,D) | cos(C,D) |','|---|---|---:|---:|---:|---:|---:|']
    for x in rows:lines.append(f"| `{x['id']}` | {x['row']} | {x['length']} | {x['W1_batch_padding']} | {x['cos_W1_C']:.9f} | {x['cos_W1_D']:.9f} | {x['cos_C_D']:.9f} |")
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    seal(out,['MISMATCHES.jsonl','SUMMARY.json','RESULTS.md'],'AUDIT_SEAL.json','SECTION146_DESCRIPTIVE_CPU_ONLY')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bank','source','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();audit(a.bank,a.source,a.out)
