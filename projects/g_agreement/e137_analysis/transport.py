"""Source-pointer transport repointed literally from committed E133 deviation1."""
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e133_analysis.adapter import original_pairs
from projects.g_agreement.e126_analysis.rules import log_odds
from projects.g_agreement.e133_analysis import probes
from . import screen,rules
REQ=core.require

def inputs(spec,inventory):
    seal=core.verify(spec['output_seal'],spec['output_sha256'])
    REQ(seal['experiment']=='E137'and seal['status']=='COMPLETE'and seal['inventory_sha256']==spec['inventory_sha256'],'complete same-inventory original sources')
    REQ(seal['reader_layers']==[44,52,60]and seal['vector_layers']==list(probes.LAYERS)and seal['no_steer']is True,'registered natural/no-steer read sites')
    REQ(seal['judging_bank']=='E137'and 0<seal['judging_cap_usd']<=2 and seal['route_verified']is True and seal['redaction_audit_complete']is True and seal['labels_cpu_only']is True,'registered blinded E133 bank/route/privacy')
    REQ(seal['rubric_sha256']==spec['rubric_sha256'],'exact committed adapted E104 rubric')
    sources=seal['source_seals'];ss=[core.verify(s['seal'],s['sha256'])for s in sources]
    REQ(all(s['experiment']=='E137'and s['status']in ('COMPLETE','COMPLETE_ONCE','SCREENED_COHORT_FROZEN')for s in ss),'complete original E133 sources, no pilot/substitution')
    cache={}
    def ref(p):
        i=p['seal_index'];REQ(type(i)is int and 0<=i<len(ss)and p['member']in ss[i]['files'],'original sealed source pointer')
        key=(i,p['member'])
        if key not in cache:
            path=Path(sources[i]['seal']).parent/p['member'];cache[key]=np.load(path,allow_pickle=False)if path.suffix=='.npy'else core.read(path)
        obj=cache[key];REQ(isinstance(p['keys'],list)and all(type(k)in(int,str)for k in p['keys']),'literal source keys')
        for k in p['keys']:obj=obj[k]
        return obj
    grid=core.unique(core.read(Path(spec['output_seal']).parent/'MEASUREMENTS.json'),'pair_id');REQ(set(grid)=={p['pair_id']for p in inventory},'complete frozen pair grid')
    out=[]
    for p in inventory:
        m=grid[p['pair_id']];REQ(len(p['members'])==2 and len(m['members'])==2,'both matched members')
        members=[]
        for j,(label,z)in enumerate(zip(p['members'],m['members'])):
            REQ({'greedy','own','readouts','vectors','patches'}<=set(z),'required original member fields missing; only preference may be absent')
            def identity(cell,mode,block=None,control=None):
                i=ref(cell['identity']);REQ(i['pair_id']==p['pair_id']and i['item_id']==label['item_id']and i['kind']==p['kind']and i['member']==j and i['mode']==mode and i.get('block')==block and i.get('control')==control,'original item/pair/member/mode/site identity')
                if p['kind']=='babi_qa2':REQ(i['source_episode_id']==p['source_episode_id'],'original QA2 source episode identity')
                return i
            def score(cell,mode,block=None,control=None):
                i=identity(cell,mode,block,control);raw=ref(cell['raw'])
                REQ(i['raw_id']==raw['id']and i['contrast_sha256']==p['recipient_contrast_sha256']and i['pair_count']==p['pair_count'],'same ORIGINAL ordered recipient contrast for own/other/patched')
                if mode=='patch':
                    REQ(i['donor_pair_id']==p['pair_id']and i['donor_member']==1-j and i['patch_binding_verified']is True,'opposite matched member donor and original patch binding')
                    if control=='earlier_token':REQ(i['unscaled_residual_replacement']is True and type(i['position'])is int and 0<=i['position']<i['read_index']-8,'original earlier-token replacement outside read site')
                    else:REQ(i['position']==i['read_index'],'read-token patch or norm control')
                    if control=='random_norm_matched':REQ(i['norm_matched']is True and type(i['random_seed'])is int,'original frozen norm-matched random seed')
                    else:REQ(i['unscaled_residual_replacement']is True,'unscaled donor residual, no extra dose')
                indices=p['recipient_pair_indices'];REQ(len(indices)==p['pair_count'],'frozen common recipient-pair count')
                return log_odds(original_pairs(raw['pair_logprobs'],indices),'A','A',p['pair_count'])
            native=ref(z['greedy']['record']);ni=identity(z['greedy'],'greedy')
            REQ(ni['raw_id']==native['id'],'original32-token text identity')
            answer=screen.classify(native,[p['members'][0]['current'],p['members'][1]['current'],label['previous']])
            preferred=prefer_current=first_agreement=masses=None
            preference_status='NOT MEASURED'
            preference_captured='preference'in z
            if preference_captured:
                pi=identity(z['preference'],'preference')
                flag=pi.get('current_previous_contrast_captured',True)
                REQ(type(flag)is bool,'explicit captured-preference boolean')
                preference_captured=flag
                if not flag:REQ(pi['raw_id']==ref(z['preference']['record'])['id'],'original unmeasured capture identity')
            if preference_captured:
                pref=ref(z['preference']['record']);pi=identity(z['preference'],'preference')
                REQ(pi['raw_id']==pref['id']and pi['current_previous_contrast_sha256']==label['current_previous_contrast_sha256'],'separate original current-vs-previous preference contrast')
                all_pairs=np.asarray(pref['pair_logits'],dtype=float);ix=label['current_previous_pair_indices']
                a=np.asarray(original_pairs(pref['pair_logits'],ix),dtype=float)
                REQ(a.ndim==2 and a.shape[1]==2 and np.isfinite(a).all(),'original separate current/previous preference pairs')
                delta=float(np.mean(a[:,0]-a[:,1]));REQ(label['current_in_preference']in ('A','B'),'frozen current/previous orientation')
                prefer_current=delta>0 if label['current_in_preference']=='A'else delta<0
                preferred=None if delta==0 else label['current']if prefer_current else label['previous']
                first_logprobs=None if pref.get('first_token_logprobs')is None else np.asarray(pref['first_token_logprobs'],dtype=float)[ix]
                source_ids=pi.get('candidate_ids')
                if first_logprobs is None and source_ids is not None and pi.get('single_token_scorer')=='E131 global-vocabulary first-step logsoftmax':
                    REQ(len(source_ids)==len(all_pairs)and all(len(q)==2 and all(len(v)==1 and type(v[0])is int for v in q)for q in source_ids),'original E131 single-token source input proof')
                    first_logprobs=np.asarray(pref['pair_logprobs'],dtype=float)[ix]
                if first_logprobs is not None:REQ((pref.get('probability_kind')=='global_vocab_logsoftmax_at_read'or pi.get('single_token_scorer')=='E131 global-vocabulary first-step logsoftmax')and first_logprobs.shape==a.shape and np.isfinite(first_logprobs).all()and (first_logprobs<=0).all(),'original global-vocabulary first-token probabilities, not two-candidate renormalization')
                token_pairs=None if pref.get('candidate_first_token_ids')is None else [pref['candidate_first_token_ids'][k]for k in ix]
                if token_pairs is None and source_ids is not None:
                    REQ(all(len(source_ids[k])==2 and all(len(v)==1 and type(v[0])is int for v in source_ids[k])for k in ix),'single-token candidate IDs')
                    token_pairs=[[v[0]for v in source_ids[k]]for k in ix]
                if token_pairs is not None:REQ(len(token_pairs)==len(a)and all(len(v)==2 and all(type(t)is int for t in v)for v in token_pairs),'frozen original candidate first-token IDs')
                preferred_column=0 if delta>0 else 1
                first_agreement=None if preferred is None or not native['token_ids']or token_pairs is None else any(native['token_ids'][0]==v[preferred_column]for v in token_pairs)
                masses=None if first_logprobs is None else np.exp(first_logprobs).mean(axis=0)
                preference_status='MEASURED'
            ro={}
            for l in rules.READS:
                cell=z['readouts'][str(l)];i=identity(cell,'readout',l);code=ref(cell['code']);text=ref(cell['text'])
                if code is None:
                    ptr=cell['code'];REQ(ptr['keys']and ptr['keys'][-1]=='code','original terminal code pointer');terminal=ref(dict(ptr,keys=ptr['keys'][:-1]));REQ(terminal['id']==i['judgment_id']and terminal['status']=='UNPARSEABLE','recorded same-ID null missing')
                else:REQ(code['id']==i['judgment_id'],'original judgment identity')
                ro[l]=rules.readout(code,text,p['value_map'],label['current'],label['previous'])
            blocks=(44,52)if p['kind']=='one_hop'else rules.BLOCKS
            REQ(set(z['patches'])=={str(b)for b in blocks},'registered blocks by group')
            patches={b:{c:score(z['patches'][str(b)][c],'patch',b,c)for c in rules.PATCHES}for b in blocks}
            vectors={}
            for l in probes.LAYERS:
                cell=z['vectors'][str(l)];identity(cell,'vector',l);v=ref(cell['vector']);vectors[l]=None if v is None else np.asarray(v,dtype=float).tolist()
            members.append(dict(member=j,item_id=label['item_id'],current=label['current'],previous=label['previous'],own_logodds=score(z['own'],'own'),patches=patches,readouts=ro,vectors=vectors,text_answer=answer,text_missing=False,text_no_value=answer is None,preference_status=preference_status,preference_current=None if preferred is None else bool(prefer_current),preferred_value=preferred,preferred_is_greedy_first=first_agreement,first_token_candidate_probability_masses=None if masses is None else masses[[0,1]if label['current_in_preference']=='A'else[1,0]].tolist()))
        out.append(dict(pair_id=p['pair_id'],kind=p['kind'],generation_index=p['generation_index'],source_episode_id=p.get('source_episode_id'),members=members))
    return out
