"""Decode sealed top10 IDs and attach the existing W1 J-lens column. No rescoring."""
import json
from pathlib import Path
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump
from run_labels import verify

def main():
    from transformers import AutoTokenizer
    source=read(HERE/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']
    if sha(source['path'])!=source['sha256']:raise ValueError('tokenizer changed')
    tok=AutoTokenizer.from_pretrained(Path(source['path']).parent,local_files_only=True)
    for bank in ('E36','W1','W12'):
        data=read(HERE/bank/'ROW_LABELS.json');raw=CACHE/(bank+'-labels');verify(raw,read(raw/'OUTPUT_SEAL.json')['files'])
        output=CACHE/(bank+'-top10');output.mkdir(exist_ok=False)
        for row in data['rows']:
            x=np.load(raw/(row['row']+'.npz'),allow_pickle=False)
            with (output/(row['row']+'.jsonl')).open('x') as f:
                for key,ids in zip(x['ids'].tolist(),x['top10_token_ids'].tolist()):
                    f.write(json.dumps({'id':key,'token_ids':ids,'tokens':[tok.decode([i]) for i in ids]},ensure_ascii=False)+'\n')
        seal={'files':{p.name:sha(p) for p in output.iterdir()},'source_raw_seal_sha256':sha(raw/'OUTPUT_SEAL.json'),'tokenizer_sha256':source['sha256'],'operation':'decode frozen top10 token IDs only; no rank or model rerun'}
        dump(output/'TOP10_SEAL.json',seal)
        dump(HERE/('TOP10_'+bank+'_2026-10-27.json'),{'directory':str(output.relative_to(ROOT)),'seal_sha256':sha(output/'TOP10_SEAL.json'),'rows':len(data['rows']),'items':len(data['rows'])*84,'reader_outcomes_accessed':False})
    original=ROOT.parent/'blindspot-worktree/results/g_agreement/blindspot/w1/analysis'
    seal=read(original/'ANALYSIS_SEAL.json')
    if sha(original/'metrics.json')!=seal['files']['metrics.json']:raise ValueError('sealed W1 J-lens summaries changed')
    # Only the already sealed J-lens column is selected; no Oracle/probe comparison.
    selected=[{'row':x['feature'],'layer':x['layer'],'auroc':x['true']['auroc'],'ci95':[x['true']['lo'],x['true']['hi']]} for x in read(original/'metrics.json')['rows'] if x['reader']=='jlens' and x['layer']==44]
    names={x['row'] for x in read(HERE/'W1/ROW_LABELS.json')['rows']}
    if len(selected)!=40 or {x['row'] for x in selected}!=names:raise ValueError('complete existing W1 J-lens column required')
    dump(HERE/'W1_EXISTING_JLENS_2026-10-27.json',{'rows':selected,'source_metrics_sha256':sha(original/'metrics.json'),'source_analysis_seal_sha256':sha(original/'ANALYSIS_SEAL.json'),'source_path':str(original),'purpose':'registered existing W1 J-lens AUROC column; descriptive; no recomputation, Oracle comparison or label override'})
    print('Decoded sealed top10 bags and copied existing W1 J-lens column; no scoring rerun')

if __name__=='__main__':main()
