"""One CPU label pass per sealed bank. E36 sanity precedes W1/W12; no outcomes."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump
import core

def verify(base,files):
    base=Path(base).resolve()
    for n,h in files.items():
        p=(base/n).resolve()
        if not p.is_relative_to(base) or sha(p)!=h:raise ValueError('sealed bytes differ')

def committed_value_sets():
    path=HERE/'VALUE_WORD_SETS_2026-10-27.json'
    committed=subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)
    if committed!=path.read_bytes():raise ValueError('value-word sets must be committed before scoring')
    if sha(path)!=read(HERE/'VALUE_WORD_SETS_2026-10-27.sha256.json')['sha256']:raise ValueError('value words drift')
    return read(path)

class FullRankReader:
    """Suraj s2_capture standard logits: norm((h J.T).bf16).float() @ W_U.float().T."""
    def __init__(self):
        import torch
        from safetensors import safe_open
        from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5RMSNorm
        torch.set_num_threads(8)
        sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
        from mats.jspace import load_jlens_layers
        p=read(HERE/'BASIS_INPUTS_2026-10-27.json');inputs=read(HERE/'READOUT_INPUTS_2026-10-27.json')
        for f in p['files'].values():
            if sha(f['path'])!=f['sha256']:raise ValueError('readout weight drift')
        for name,h in inputs['runtime_files'].items():
            if sha(name)!=h:raise ValueError('frozen CPU readout implementation drift')
        self.j=load_jlens_layers(p['files']['jlens']['path'],[44])[44]
        with safe_open(p['files']['unembedding_shard']['path'],framework='pt',device='cpu') as f:self.wu=f.get_tensor('lm_head.weight').float()
        with safe_open(p['files']['norm_shard']['path'],framework='pt',device='cpu') as f:w=f.get_tensor('model.language_model.norm.weight')
        self.norm=Qwen3_5RMSNorm(5120,eps=inputs['rms_norm_eps']).to(dtype=torch.bfloat16,device='cpu')
        with torch.no_grad():self.norm.weight.copy_(w)
        self.norm.requires_grad_(False)

    def score(self,acts,ids):
        import torch
        ranks=[];top=[]
        with torch.no_grad():
            for start in range(0,len(acts),16):
                h=torch.tensor(np.asarray(acts[start:start+16]),dtype=torch.float32,device='cpu')
                z=self.norm((h@self.j.T).to(torch.bfloat16)).float()
                logits=z@self.wu.T
                if not torch.isfinite(logits).all():raise ValueError('nonfinite J-lens logits')
                top.extend(logits.topk(10,dim=1).indices.tolist())
                if all(ids):
                    best=torch.stack([logits[:,side].max(1).values for side in ids],dim=1)
                    ranks.extend(torch.stack([(logits>best[:,i,None]).sum(1) for i in (0,1)],dim=1).tolist())
        return np.array(ranks,dtype=np.int64),np.array(top,dtype=np.int64)

def run(bank):
    values=committed_value_sets()
    verify(ROOT,read(HERE/'LABEL_CODE_SEAL_2026-10-27.json')['files'])
    basis=read(HERE/'BASIS_SEAL_2026-10-27.json');verify(CACHE,basis['files'])
    if bank!='E36':
        verify(HERE/'E36',read(HERE/'E36/LABEL_SEAL.json')['files'])
        if read(HERE/'E36/R1_SANITY.json')['met'] is not True:raise ValueError('R1 failed; no downstream labels or reader comparison')
    if bank=='E49':
        binding=read(HERE/'E49_CAPTURE_BINDING_2026-10-27.json')
        if binding.get('reader_scores_exist') is not False:raise ValueError('prospective capture required')
        src=ROOT/binding['directory']
    else:
        binding=read(HERE/'BANK_INPUTS_2026-10-27.json')['banks'][bank];src=ROOT/binding['directory']
    if sha(src/'INPUT_SEAL.json')!=binding['input_seal_sha256']:raise ValueError('bound bank seal drift')
    inputseal=read(src/'INPUT_SEAL.json');verify(src,inputseal['files'])
    if set(inputseal['rows'])!=set(values['banks'][bank]):raise ValueError('full frozen row set required')
    records=read(src/'items.json');acts=np.load(src/'acts44.npy',mmap_mode='r',allow_pickle=False)
    if acts.shape!=(len(records),5120):raise ValueError('capture shape')
    # The claim is created only after operational inputs validate; never reset.
    with (CACHE/(bank+'_LABEL_ONCE.json')).open('x') as f:json.dump({'bank':bank,'created_epoch':time.time(),'status':'CLAIMED_NEVER_RESET'},f)
    out=CACHE/(bank+'-labels');out.mkdir(exist_ok=False)
    reader=FullRankReader();q=np.load(CACHE/'basis_L44_r1536.npy',allow_pickle=False);null=read(CACHE/'ENRICHMENT_NULL.json')['ranks']
    rows=[];directions={};means={};t=time.time()
    for row,spec in values['banks'][bank].items():
        ix=[i for i,r in enumerate(records) if r['feature']==row];part=[records[i] for i in ix];y=np.array([r['y'] for r in part]);h=np.array(acts[ix])
        if len(ix)!=84 or len({r['id'] for r in part})!=84 or y.sum()!=42:raise ValueError('balanced84 test records per row required')
        enrichment,mu,d,norm=core.enrich(h,y,q,null);ranks,top=reader.score(h,spec['token_ids'])
        readability=core.g3(ranks,y) if all(spec['token_ids']) else {'status':'NOT EVALUABLE','reason':'empty frozen value-word/token set','readable':None}
        np.savez_compressed(out/(row+'.npz'),best_ranks=ranks,top10_token_ids=top,ids=np.array([r['id'] for r in part]))
        directions[row]=d;means[row]=mu
        rows.append({'bank':bank,'row':row,'class':spec['class'],'n_test':84,'enrichment':enrichment,'J_readability':readability,'label':core.label(enrichment,readability),'class_mean_difference_norm':norm,
            'top10_descriptive':{'A_word_present_rate':float(np.isin(top,spec['token_ids'][0]).any(1).mean()) if spec['token_ids'][0] else None,'B_word_present_rate':float(np.isin(top,spec['token_ids'][1]).any(1).mean()) if spec['token_ids'][1] else None}})
        print(bank,row,rows[-1]['label'],flush=True)
    np.savez_compressed(out/'directions.npz',**directions);np.savez_compressed(out/'class_means.npz',**means)
    dump(out/'OUTPUT_SEAL.json',{'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'bank':bank,'basis_sha256':basis['files']['basis_L44_r1536.npy']})
    publish=HERE/bank;publish.mkdir(exist_ok=False)
    dump(publish/'ROW_LABELS.json',{'experiment':'E52','bank':bank,'rows':rows,'basis_sha256':basis['files']['basis_L44_r1536.npy'],'values_sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json'),'input_seal_sha256':sha(src/'INPUT_SEAL.json'),'raw_output_seal_sha256':sha(out/'OUTPUT_SEAL.json'),'code_seal_sha256':sha(HERE/'LABEL_CODE_SEAL_2026-10-27.json'),'reader_outcomes_accessed':False,'wall_seconds':time.time()-t})
    lines=['# E52 '+bank+' labels','', '| Row | J-space label |','|---|---|']+[f"| {r['row']} | {r['label']} |" for r in rows]
    (publish/'LABELS.md').write_text('\n'.join(lines)+'\n')
    if bank=='E36':
        content=[r for r in rows if r['class']=='content'];n=sum(r['label']=='IN-J' for r in content)
        if len(content)!=9:raise ValueError('exact9 E36 content rows for sanity')
        dump(publish/'R1_SANITY.json',{'rule':'R1','met':n>=7,'IN_J':n,'denominator':9,'threshold':7,'on_failure':'STOP_ALL_DOWNSTREAM; no basis retry'})
    if bank=='E49':
        dump(HERE/'E49_JFORECAST.json',{'experiment':'E52','status':'SEALED_PROSPECTIVE_FORECAST','rows':[{'row':r['row'],'label':r['label'],'oracle_prediction':'REPORTED' if r['label']=='IN-J' else 'MISSED'} for r in rows],
            'basis_sha256':basis['files']['basis_L44_r1536.npy'],'values_sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json'),'capture_binding_sha256':sha(HERE/'E49_CAPTURE_BINDING_2026-10-27.json'),'created_epoch':time.time(),'reader_scores_accessed':False,'reader_scores_exist_at_capture':False,'R3_comparison':'only after E49 sealed analysis; once-only'})
        dump(HERE/'E49_JFORECAST.sha256.json',{'sha256':sha(HERE/'E49_JFORECAST.json')})
    dump(publish/'LABEL_SEAL.json',{'files':{p.name:sha(p) for p in publish.iterdir() if p.is_file()}})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bank',choices=['E36','W1','W12','E49']);a=p.parse_args();run(a.bank)
