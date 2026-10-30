"""One E49 forecast, row-complete checkpoints, fixed deadline, no backfilling."""
from datetime import datetime, timezone
import json
import signal
import sys
import time
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump
from run_labels import verify,committed_value_sets,FullRankReader
from sparse_primary import fraction,primary_label
import core

STOP_AT=datetime(2026,10,27,5,20,tzinfo=timezone.utc).timestamp()
SEAL=HERE/'DEADLINE_CODE_SEAL_2026-10-27.json'

class DeadlineExpired(TimeoutError):pass

def alarm(signum,frame):raise DeadlineExpired('fixed compute deadline')

def missing(row,spec,reason):
    return {'bank':'E49','row':row,'class':spec['class'],'label':'NO FORECAST','oracle_prediction':'NO FORECAST','computational_reason':reason,'J_readability':{'status':'NOT EVALUABLE','readable':None},'enrichment':None,'secondary_SVD_label':'NO FORECAST','disagrees_with_SVD':None}

def finish(values,completed,raw,reason,binding):
    primary=[];secondary=[]
    for row,spec in values.items():
        item=completed.get(row) or missing(row,spec,reason)
        if item['label']=='NO FORECAST' and not item.get('computational_reason'):raise ValueError('missing computational reason')
        primary.append(item)
        secondary.append({**item,'label':item['secondary_SVD_label']})
    dump(raw/'OUTPUT_SEAL.json',{'files':{p.name:sha(p) for p in raw.iterdir() if p.is_file() and p.name!='OUTPUT_SEAL.json'},'deadline_utc':'2026-10-27T05:20:00Z'})
    for dest,data,kind in ((HERE/'E49',secondary,'SECONDARY_SVD'),(HERE/'primary/E49',primary,'PRIMARY_SPARSE')):
        dest.mkdir(parents=True,exist_ok=False)
        dump(dest/'ROW_LABELS.json',{'experiment':'E52','bank':'E49','label_role':kind,'rows':data,'input_seal_sha256':binding['input_seal_sha256'] if binding else None,'raw_output_seal_sha256':sha(raw/'OUTPUT_SEAL.json'),'code_seal_sha256':sha(SEAL),'reader_outcomes_accessed':False})
        (dest/'LABELS.md').write_text('# E52 E49 '+kind+' labels\n\n| Row | Label | Computational reason if missing |\n|---|---|---|\n'+'\n'.join('| '+r['row']+' | '+r['label']+' | '+r.get('computational_reason','')+' |' for r in data)+'\n')
        dump(dest/'LABEL_SEAL.json',{'files':{p.name:sha(p) for p in dest.iterdir()}})
    f={'experiment':'E52','status':'SEALED_PROSPECTIVE_FORECAST','label_of_record':'nonnegative sparse J pursuit, k16','authority_commit':'e0a2e9ef','rows':[{'row':r['row'],'label':r['label'],'secondary_SVD_label':r['secondary_SVD_label'],'oracle_prediction':r['oracle_prediction'],**({'computational_reason':r['computational_reason']} if r['label']=='NO FORECAST' else {})} for r in primary],
       'basis_sha256':read(HERE/'BASIS_SEAL_2026-10-27.json')['files']['basis_L44_r1536.npy'],'values_sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json'),'capture_binding_sha256':sha(HERE/'E49_CAPTURE_BINDING_2026-10-27.json') if binding else None,'primary_label_seal_sha256':sha(HERE/'primary/E49/LABEL_SEAL.json'),'code_seal_sha256':sha(SEAL),'created_epoch':time.time(),'reader_scores_accessed':False,'reader_scores_exist_at_capture':False if binding else None,'no_backfill':True,'commit_deadline_utc':'2026-10-27T05:30:00Z','R3_comparison':'forecasted gated rows, minimum8; native correct-value>=0.10 and >wrong-only; sensitivity counts all gated NO FORECAST as wrong'}
    with (HERE/'E49_JFORECAST.json').open('x') as out:json.dump(f,out,indent=2,sort_keys=True,allow_nan=False);out.write('\n')
    dump(HERE/'E49_JFORECAST.sha256.json',{'sha256':sha(HERE/'E49_JFORECAST.json')})
    print('SEALED forecast; '+str(sum(r['label']!='NO FORECAST' for r in primary))+'/16 computable; commit now before readers',flush=True)

def run():
    if (HERE/'E49_JFORECAST.json').exists():
        print('Forecast already sealed; no backfill or new computation');return 0
    verify(ROOT,read(SEAL)['files'])
    values=committed_value_sets()['banks']['E49']
    verify(HERE/'primary/E36',read(HERE/'primary/E36/LABEL_SEAL.json')['files'])
    if read(HERE/'primary/E36/R1_SANITY.json')['met'] is not True:raise ValueError('scientific R1 failure; stop')
    bp=HERE/'E49_CAPTURE_BINDING_2026-10-27.json'
    if not bp.exists() and time.time()<STOP_AT:
        print('AWAITING_CAPTURE; no claim created');return 2
    with (CACHE/'E49_LABEL_ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'code_seal_sha256':sha(SEAL)},f)
    raw=CACHE/'E49-labels';raw.mkdir(exist_ok=False)
    completed={};binding=None;reason='CAPTURE_NOT_DELIVERED_BY_COMPUTE_DEADLINE'
    if not bp.exists():finish(values,completed,raw,reason,None);return 0
    prior=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.001,STOP_AT-time.time()))
    try:
        candidate=read(bp)
        if candidate.get('reader_scores_exist') is not False or candidate.get('readers_paused_until_forecast_commit') is not True:raise ValueError('prospective capture and pause required')
        src=ROOT/candidate['directory']
        if sha(src/'INPUT_SEAL.json')!=candidate['input_seal_sha256']:raise ValueError('input binding mismatch')
        inputs=read(src/'INPUT_SEAL.json');verify(src,inputs['files'])
        if set(inputs['rows'])!=set(values):raise ValueError('complete frozen row set required')
        binding=candidate
        basis=read(HERE/'BASIS_SEAL_2026-10-27.json');verify(CACHE,basis['files'])
        sparse=CACHE/'sparse-primary';null=read(sparse/'NULL_SEAL.json')
        verify(sparse,read(sparse/'ATOM_SEAL.json')['files']);verify(sparse,null['files'])
        sanity=read(HERE/'primary/E36/ROW_LABELS.json')
        if sanity['atom_seal_sha256']!=sha(sparse/'ATOM_SEAL.json') or sanity['null_seal_sha256']!=sha(sparse/'NULL_SEAL.json'):raise ValueError('primary atom/null binding mismatch')
        records=read(src/'items.json');acts=np.load(src/'acts44.npy',mmap_mode='r',allow_pickle=False)
        if acts.shape!=(len(records),5120):raise ValueError('capture shape mismatch')
        reader=FullRankReader();q=np.load(CACHE/'basis_L44_r1536.npy',allow_pickle=False);svdnull=read(CACHE/'ENRICHMENT_NULL.json')['ranks']
        import torch
        sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
        from mats.jspace import nn_pursuit
        atoms=torch.load(sparse/'atoms.pt',map_location='cpu',weights_only=True)['atoms']
        from tokenizers import Tokenizer
        tok=Tokenizer.from_file(read(HERE/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']['path'])
        for row,spec in values.items():
            if time.time()>=STOP_AT:raise DeadlineExpired()
            stage='capture_validation'
            try:
                ix=[i for i,r in enumerate(records) if r['feature']==row];part=[records[i] for i in ix];y=np.array([r['y'] for r in part]);h=np.array(acts[ix])
                if len(ix)!=84 or len({r['id'] for r in part})!=84 or y.sum()!=42 or not np.isfinite(h).all():raise ValueError('finite balanced84 capture required')
                stage='SVD_enrichment';enrich,mu,d,norm=core.enrich(h,y,q,svdnull)
                stage='full_vocabulary_G3'
                ranks,top=reader.score(h,spec['token_ids'])
                g3=core.g3(ranks,y) if all(spec['token_ids']) else {'status':'NOT EVALUABLE','reason':'empty frozen value-word/token set','readable':None}
                stage='sparse_pursuit';hh=np.asarray(d,dtype=np.float32)[None,:];idx,coef,rec=nn_pursuit(torch.from_numpy(hh),atoms,k=16);frac=float(fraction(hh,rec.numpy())[0])
                label=primary_label(frac,null['median'],null['percentile97_5'],g3);secondary=core.label(enrich,g3)
                stage='saving_row_artifacts';np.savez_compressed(raw/(row+'.npz'),best_ranks=ranks,top10_token_ids=top,ids=np.array([r['id'] for r in part]),class_means=mu,direction=d,idx=idx.numpy(),coef=coef.numpy(),reconstruction=rec.numpy(),fraction=frac)
                dump(raw/(row+'.top10.json'),{'items':[{'id':r['id'],'tokens':[tok.decode([int(t)]) for t in tt]} for r,tt in zip(part,top)]})
                result={'bank':'E49','row':row,'class':spec['class'],'n_test':84,'enrichment':enrich,'J_readability':g3,'label':label,'secondary_SVD_label':secondary,'disagrees_with_SVD':label!=secondary,'J_fraction':frac,'class_mean_difference_norm':norm,'oracle_prediction':'REPORTED' if label=='IN-J' else 'MISSED'}
                dump(raw/(row+'.completed.json'),result);completed[row]=result
                print(row+' '+label,flush=True)
            except DeadlineExpired:raise
            except Exception as e:
                completed[row]=missing(row,spec,'ROW_COMPUTATION_FAILED_'+stage+'_'+type(e).__name__)
                dump(raw/(row+'.failed.json'),completed[row]);print(row+' NO FORECAST: '+type(e).__name__,flush=True)
        reason='NOT_COMPUTED'
    except DeadlineExpired:reason='COMPUTE_DEADLINE_REACHED_2026-10-27T05:20:00Z'
    except Exception as e:reason='INPUT_OR_SCORER_COMPUTATION_FAILED_'+type(e).__name__;print(reason,flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)
    finish(values,completed,raw,reason,binding)
    return 0

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; fixed registered deadline and inputs')
    raise SystemExit(run())
