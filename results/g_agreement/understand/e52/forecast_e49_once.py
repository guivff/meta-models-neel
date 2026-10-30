"""E52 amended prospective E49 forecast, once, from a verified capture only."""
import json
import sys
import time
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump
from run_labels import verify,committed_value_sets,FullRankReader
from sparse_primary import fraction,primary_label
import core

def run():
    import torch
    verify(ROOT,read(HERE/'SPARSE_CODE_SEAL_2026-10-27.json')['files'])
    values=committed_value_sets()['banks']['E49']
    verify(HERE/'primary/E36',read(HERE/'primary/E36/LABEL_SEAL.json')['files'])
    if read(HERE/'primary/E36/R1_SANITY.json')['met'] is not True:raise ValueError('primary R1 failed; stop without retry')
    binding=read(HERE/'E49_CAPTURE_BINDING_2026-10-27.json')
    if binding.get('reader_scores_exist') is not False or binding.get('readers_paused_until_forecast_commit') is not True:raise ValueError('prospective capture and reader pause required')
    src=ROOT/binding['directory']
    if sha(src/'INPUT_SEAL.json')!=binding['input_seal_sha256']:raise ValueError('capture binding drift')
    inputseal=read(src/'INPUT_SEAL.json');verify(src,inputseal['files'])
    if set(inputseal['rows'])!=set(values):raise ValueError('all frozen E49 rows required')
    basis=read(HERE/'BASIS_SEAL_2026-10-27.json');verify(CACHE,basis['files'])
    sparse=CACHE/'sparse-primary';atomseal=read(sparse/'ATOM_SEAL.json');null=read(sparse/'NULL_SEAL.json')
    verify(sparse,atomseal['files']);verify(sparse,null['files'])
    sanity_labels=read(HERE/'primary/E36/ROW_LABELS.json')
    if sanity_labels['atom_seal_sha256']!=sha(sparse/'ATOM_SEAL.json') or sanity_labels['null_seal_sha256']!=sha(sparse/'NULL_SEAL.json'):raise ValueError('primary sanity atom/null binding drift')
    if null['atom_seal_sha256']!=sha(sparse/'ATOM_SEAL.json') or null['random_directions_sha256']!=basis['files']['random_unit_directions.npy']:raise ValueError('sparse null binding drift')
    records=read(src/'items.json');acts=np.load(src/'acts44.npy',mmap_mode='r',allow_pickle=False)
    if acts.shape!=(len(records),5120):raise ValueError('capture shape')
    for row in values:
        rr=[r for r in records if r['feature']==row]
        if len(rr)!=84 or len({r['id'] for r in rr})!=84 or sum(r['y'] for r in rr)!=42:raise ValueError('84 balanced test items required')
    with (CACHE/'E49_LABEL_ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'primary':'sparse pursuit'},f)
    raw=CACHE/'E49-labels';raw.mkdir(exist_ok=False)
    reader=FullRankReader();q=np.load(CACHE/'basis_L44_r1536.npy',allow_pickle=False);svdnull=read(CACHE/'ENRICHMENT_NULL.json')['ranks']
    rows=[];directions={};means={}
    for row,spec in values.items():
        ix=[i for i,r in enumerate(records) if r['feature']==row];part=[records[i] for i in ix];y=np.array([r['y'] for r in part]);h=np.array(acts[ix])
        enrichment,mu,d,norm=core.enrich(h,y,q,svdnull);ranks,top=reader.score(h,spec['token_ids'])
        readability=core.g3(ranks,y) if all(spec['token_ids']) else {'status':'NOT EVALUABLE','reason':'empty frozen value-word/token set','readable':None}
        np.savez_compressed(raw/(row+'.npz'),best_ranks=ranks,top10_token_ids=top,ids=np.array([r['id'] for r in part]))
        directions[row]=d;means[row]=mu
        rows.append({'bank':'E49','row':row,'class':spec['class'],'n_test':84,'enrichment':enrichment,'J_readability':readability,'label':core.label(enrichment,readability),'class_mean_difference_norm':norm})
        print('E49 G3 and secondary enrichment sealed in memory: '+row,flush=True)
    del reader
    np.savez_compressed(raw/'directions.npz',**directions);np.savez_compressed(raw/'class_means.npz',**means)
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.jspace import nn_pursuit
    atoms=torch.load(sparse/'atoms.pt',map_location='cpu',weights_only=True)['atoms']
    h=np.stack([directions[r['row']] for r in rows]).astype(np.float32)
    idx,coef,rec=nn_pursuit(torch.from_numpy(h),atoms,k=16);fractions=fraction(h,rec.numpy())
    np.savez_compressed(raw/'sparse_pursuit.npz',idx=idx.numpy(),coef=coef.numpy(),reconstruction=rec.numpy(),fractions=fractions)
    # Decode the sealed top10 bags only; no extra model pass.
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(read(HERE/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']['path'])
    for row in values:
        data=np.load(raw/(row+'.npz'),allow_pickle=False)
        dump(raw/(row+'.top10.json'),{'items':[{'id':str(i),'tokens':[tokenizer.decode([int(t)]) for t in tt]} for i,tt in zip(data['ids'],data['top10_token_ids'])]})
    dump(raw/'OUTPUT_SEAL.json',{'files':{p.name:sha(p) for p in raw.iterdir()},'atom_seal_sha256':sha(sparse/'ATOM_SEAL.json'),'null_seal_sha256':sha(sparse/'NULL_SEAL.json')})
    primary=[{**r,'secondary_SVD_label':r['label'],'label':primary_label(f,null['median'],null['percentile97_5'],r['J_readability']),'J_fraction':float(f),'label_of_record':'nonnegative sparse J pursuit, k16'} for r,f in zip(rows,fractions)]
    for r in primary:r['disagrees_with_SVD']=r['label']!=r['secondary_SVD_label']
    for dest,data,kind in ((HERE/'E49',rows,'SECONDARY_SVD'),(HERE/'primary/E49',primary,'PRIMARY_SPARSE')):
        dest.mkdir(parents=True,exist_ok=False)
        dump(dest/'ROW_LABELS.json',{'experiment':'E52','bank':'E49','label_role':kind,'rows':data,'input_seal_sha256':sha(src/'INPUT_SEAL.json'),'raw_output_seal_sha256':sha(raw/'OUTPUT_SEAL.json'),'code_seal_sha256':sha(HERE/'SPARSE_CODE_SEAL_2026-10-27.json'),'reader_outcomes_accessed':False})
        (dest/'LABELS.md').write_text('# E52 E49 '+kind+' labels\n\n| Row | Label |\n|---|---|\n'+'\n'.join('| '+r['row']+' | '+r['label']+' |' for r in data)+'\n')
        dump(dest/'LABEL_SEAL.json',{'files':{p.name:sha(p) for p in dest.iterdir()}})
    forecast={'experiment':'E52','status':'SEALED_PROSPECTIVE_FORECAST','label_of_record':'nonnegative sparse J pursuit, k16','authority_commit':'4c187fda','rows':[{'row':r['row'],'label':r['label'],'secondary_SVD_label':r['secondary_SVD_label'],'disagrees_with_SVD':r['disagrees_with_SVD'],'oracle_prediction':'REPORTED' if r['label']=='IN-J' else 'MISSED'} for r in primary],
        'basis_sha256':basis['files']['basis_L44_r1536.npy'],'values_sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json'),'capture_binding_sha256':sha(HERE/'E49_CAPTURE_BINDING_2026-10-27.json'),'primary_label_seal_sha256':sha(HERE/'primary/E49/LABEL_SEAL.json'),'created_epoch':time.time(),'reader_scores_accessed':False,'reader_scores_exist_at_capture':False,'R3_comparison':'only after E49 sealed analysis; once-only; correct-value >=0.10 and >wrong-only'}
    with (HERE/'E49_JFORECAST.json').open('x') as f:json.dump(forecast,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    dump(HERE/'E49_JFORECAST.sha256.json',{'sha256':sha(HERE/'E49_JFORECAST.json')})
    print('E49 prospective primary forecast sealed; commit before reader go-signal',flush=True)

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; use committed E49 forecast command once')
    run()
