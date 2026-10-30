"""Finish the public/CPU E100 split after explicit count/token rulings."""
import argparse
import math
import shutil
import tarfile
from pathlib import Path
import numpy as np
from build100 import ROWS,SEED,HERE,ROOT,sha,read,write,inputs,verified_members,opaque
from math100 import unit,pair_other,manipulation

MAPPING={
 'nesting_depth':[' ]',' ]]]'],
 'indent_level':['\n    pass','\n            pass'],
 'page_range_digit':[' 3',' 7'],
 'format_plan':['-','The'],
 'language_plan':['Je','The'],
 'tense_implicit':[' was',' is'],
 'language_continuation':[' et',' und'],
 'fact_recall':[' Paris',' Lima']}


def tokens(tokenizer,row,nesting_rule):
    strings=MAPPING[row];encoded=[tokenizer.encode(s,add_special_tokens=False) for s in strings]
    ids=[e.ids for e in encoded];position=0;status='READY';reason=None
    if row in ('nesting_depth','indent_level'):
        position=next((i for i in range(min(map(len,ids))) if ids[0][i]!=ids[1][i]),None)
        if position is None:
            if row=='nesting_depth' and nesting_rule=='2205_vs_4891':
                positions=[0,1];assert ids==[[2205],[2205,4891]]
            else:status='NOT_RUN';reason='shared prefix; shorter value has no differing token';positions=[None,None]
        else:positions=[position,position]
    elif ids[0][0]==ids[1][0]:status='NOT_RUN';reason='shared first token under fd07c12a';positions=[None,None]
    else:positions=[0,0]
    records=[]
    for label,s,e,p in zip([1,0],strings,encoded,positions):
        token=e.ids[p] if p is not None else None
        records.append(dict(target_label=label,input_string=s,all_token_ids=e.ids,all_token_pieces=e.tokens,
            selected_token_index=p,token_id=token,token_piece=tokenizer.id_to_token(token) if token is not None else None,
            decoded_token=tokenizer.decode([token],skip_special_tokens=False) if token is not None else None))
    return dict(status=status,reason=reason,values=records)


def finalize(base,core,model,out,nesting_rule):
    receipt=read(core/'CORE_RECEIPT.json')
    for n,h in receipt['files'].items():assert sha(core/n)==h,'core unchanged'
    data,old,qpath,prov=inputs(base)
    assert prov==read(core/'cpu_only/SOURCES.json'),'same verified source lineage'
    # Local safetensors bytes, independently tied to the pinned download revision/LFS oid.
    from tokenizers import Tokenizer
    from safetensors import safe_open
    revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
    tokenizer_path=model/'tokenizer.json';assert sha(tokenizer_path)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    tokenizer=Tokenizer.from_file(str(tokenizer_path))
    idx=read(model/'model.safetensors.index.json');shard=model/idx['weight_map']['lm_head.weight']
    metadata=model/'.cache/huggingface/download'/(shard.name+'.metadata');lines=metadata.read_text().splitlines()
    assert lines[0]==revision;assert sha(shard)==lines[1],'original unembedding shard LFS hash'
    cont=base/'wt-wmech/cache/g_agreement/understand/e56/inputs_v2_single/CONTINUATIONS.json'
    verified_members(cont.parent/'INPUT_SEAL.json',[cont.name]);assert read(cont)['language_continuation']['pairs'][0]==MAPPING['language_continuation']
    e59=ROOT/'results/g_agreement/understand/e79/cpu_scorer/INPUT_CONTRACT.json'
    c=read(e59)
    assert all(c['candidate_strings'][r][0]==MAPPING[r] for r in ['format_plan','language_plan'])
    key_path=base/'wt-blindspot-internals/cache/g_agreement/understand/e79/inputs_v1/KEY.DO_NOT_SHARE.json'
    assert sha(key_path)=='c7fbdd045d544e9d1eb584ac665b970df04463b28cf92c70029ccd99fa653e63'
    prior_targets={}
    for k in read(key_path):
        if k['arm']=='A':
            key=(k['row'],k['source_item_id'])
            if key in prior_targets:assert prior_targets[key]==k['sign']
            prior_targets[key]=k['sign']
    out.mkdir(parents=True,exist_ok=False);shutil.copytree(core/'public',out/'public');shutil.copytree(core/'cpu_only',out/'cpu_only')
    public=out/'public';cpu=out/'cpu_only';(public/'pairings').mkdir()
    rows=read(cpu/'ROWS.json');public_rows=[];joins=[];checks=[];token_records={};q=np.load(public/'Q_J.npy',allow_pickle=False)
    with safe_open(str(shard),framework='pt',device='cpu') as f:
        unembedding=f.get_slice('lm_head.weight');assert tuple(unembedding.get_shape())==(248320,5120)
        for ri,(bank,row) in enumerate(ROWS):
            records,acts=data[bank];test=[x for x in records if x['feature']==row and x['split']=='test']
            assert len(test)==84 and sum(x['label'] for x in test)==42 and all(x['id'] in acts for x in test)
            original_ids=[x['id'] for x in test];ids=[opaque(bank,x) for x in original_ids];labels=[x['label'] for x in test]
            partners=pair_other(ids,labels);folder=public/row
            h44=np.stack([acts[x['id']] for x in test]).astype(np.float32)
            h42_by={}
            for cap in prov['banks'][bank]['captures']:
                cs=Path(cap['seal_path']);s=verified_members(cs,['acts42.npy','items.order.json'],cap['seal_sha256'])
                order=read(cs.parent/'items.order.json');a=np.load(cs.parent/'acts42.npy',mmap_mode='r',allow_pickle=False)
                for j,ident in enumerate(order):
                    if ident in set(original_ids):h42_by[ident]=a[j].copy()
            assert set(h42_by)==set(original_ids)
            h42=np.stack([h42_by[x] for x in original_ids]);assert h42.shape==h44.shape==(84,5120)
            assert np.isfinite(h44).all() and np.isfinite(h42).all()
            np.save(folder/'h44.npy',h44,allow_pickle=False);np.save(folder/'h42.npy',h42,allow_pickle=False)
            write(public/'pairings'/(row+'.json'),[dict(id=ids[i],slot=i,donor_id=ids[j],donor_slot=j) for i,j in enumerate(partners)])
            if ri<3:signs=np.array([prior_targets[row,x] for x in original_ids])
            else:
                drawn=np.random.default_rng(np.random.SeedSequence([SEED,ri,1])).permutation(np.array([1]*42+[-1]*42))
                by_id=dict(zip(sorted(original_ids),drawn));signs=np.array([by_id[x] for x in original_ids])
            target=(signs>0).astype(int)
            tr=tokens(tokenizer,row,nesting_rule);token_records[row]=tr
            token_vectors={}
            for v in tr['values']:
                if v['token_id'] is None:continue
                raw=unembedding[v['token_id']:v['token_id']+1].float().numpy()[0]
                u=unit(raw);name=opaque(row,'token:'+str(v['token_id']))+'.npy';np.save(folder/name,u,allow_pickle=False)
                v.update(vector_file=str((folder/name).relative_to(public)),vector_sha256=sha(folder/name),unembedding_row_norm=float(np.linalg.norm(raw.astype(np.float64))))
                token_vectors[v['target_label']]=u
            d=np.load(cpu/(row+'_raw_d.npy'),allow_pickle=False);dnorm=float(np.linalg.norm(d));jf=float(np.linalg.norm(q@(q.T@d))/dnorm)
            directions=['d'] if ri<3 else ['d','d_J','d_perp','r']
            if tr['status']=='READY':directions+=['u_tok']
            delta_files={};probe=np.load(cpu/(row+'_probe.npz'),allow_pickle=False)
            for direction in directions:
                u=np.stack([token_vectors[int(t)] for t in target]) if direction=='u_tok' else np.load(folder/(direction+'.npy'),allow_pickle=False)[None,:]
                delta=dnorm*signs[:,None]*u
                assert delta.shape==(84,5120) and np.isfinite(delta).all()
                path=folder/('delta_'+direction+'.npy');np.save(path,delta,allow_pickle=False)
                delta_files[direction]=str(path.relative_to(public))
                for alpha in [.5,1.,2.,4.]:
                    hp=(h44.astype(np.float64)+alpha*delta).astype(np.float32)
                    result=manipulation(h44,hp,probe['w'],probe['sd'],target)
                    for i,ident in enumerate(ids):checks.append(dict(id=ident,row=row,direction=direction,alpha=alpha,
                        probe_logit_shift=float(result['probe_logit_shift'][i]),target_signed_probe_logit_shift=float(result['target_signed_probe_logit_shift'][i]),
                        norm_ratio=float(result['norm_ratio'][i]),norm_ratio_above_1_5=bool(result['norm_ratio_above_1_5'][i])))
            public_rows.append(dict(row=row,group='missed' if ri<3 else 'reported',items=84,ids=ids,
                h44=str((folder/'h44.npy').relative_to(public)),h42=str((folder/'h42.npy').relative_to(public)),
                pairings='pairings/'+row+'.json',delta_files=delta_files,u_tok_status=tr['status'],
                missed_J_perp_random='REUSE_E79_OUTPUTS_NO_RERUN' if ri<3 else None))
            joins.extend(dict(id=ids[i],bank=bank,row=row,source_item_id=x['id'],true_label=x['label'],target_label=int(target[i]),
                sigma=int(signs[i]),donor_id=ids[partners[i]],donor_source_item_id=original_ids[partners[i]],donor_label=labels[partners[i]],
                source_value=x['value']) for i,x in enumerate(test))
            rows[ri]['J_fraction']=jf;rows[ri]['random_rank_chance']=math.sqrt(384/5120)
    write(cpu/'FINAL_ROWS.json',rows);write(cpu/'JOIN.DO_NOT_STAGE.json',joins)
    write(cpu/'TOKEN_BINDINGS.json',dict(authority='fd07c12a',rows=token_records,nesting_rule=nesting_rule,
        tokenizer_sha256=sha(tokenizer_path),model_revision=revision,unembedding_shard_sha256=sha(shard),tensor='lm_head.weight',
        e56_continuation_sha256=sha(cont),e59_continuation_contract_sha256=sha(e59)))
    write(cpu/'MANIPULATION_CHECKS.json',dict(status='CPU_INPUT_MANIPULATION_CHECK_ONLY',fit_split='dev',cells=checks,readouts_opened=False))
    write(public/'MANIFEST.json',dict(experiment='E100',authority=['f425a5e2','fd07c12a'],seed=SEED,rank=384,
        Q_J='Q_J.npy',Q_R='Q_R.npy',projector='Q @ Q.T',basis_shape=[5120,384],rows=public_rows,
        injection='cast_float32(h44.float64 + alpha * delta.float64); delta already contains norm and sigma',
        no_baselines=True,upstream='NOT_INCLUDED; optional under clarification1; needs block28/36 dev capture authority'))
    write(public/'INPUT_SEAL.json',dict(experiment='E100',labels_on_pod=False,files={str(p.relative_to(public)):sha(p) for p in public.rglob('*') if p.is_file()}))
    write(out/'VECTOR_SEAL.json',dict(experiment='E100',authority=['f425a5e2','fd07c12a'],status='SEALED_BEFORE_GPU',GPU_calls=0,reader_calls=0,
        CPU_only=['cpu_only'],public_input_seal_sha256=sha(public/'INPUT_SEAL.json'),token_bindings=token_records,
        core_receipt_sha256=sha(core/'CORE_RECEIPT.json'),files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['base','core','model','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--nesting-rule',choices=['not_run','2205_vs_4891'],required=True)
    a=p.parse_args();raise SystemExit('E100 c/d withdrawn by 69f8c08e4; use finalize_ab100.py. This draft is retained as CPU preparation history only.')
