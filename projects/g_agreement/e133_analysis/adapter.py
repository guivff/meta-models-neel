"""§241 source-bound CPU analysis. Production blocked until protocol is clarified/frozen."""
import argparse,hashlib,subprocess
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e126_analysis.rules import log_odds
from . import screen,rules,probes
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/e133/ANALYSIS_ONCE.json')
REQ=core.require


def committed():
    for n,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/n)==h,'changed dependency '+n)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted adapter '+p.name)
    protocol()
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def protocol():
    REQ(core.read(HERE/'PROTOCOL.json')['status']=='FROZEN','scientific protocol clarification pending; do not open outputs')


def metadata(spec):
    inv=core.verify(spec['inventory_seal'],spec['inventory_sha256'])
    REQ(inv['experiment']=='E133'and inv['status']=='SCREENED_COHORT_FROZEN'and inv['labels_cpu_only']is True,'frozen CPU screened inventory')
    REQ(inv['classifier_sha256']==screen.MATCHER_SHA256 and inv['greedy_max_new_tokens']==32,'unchanged32-token screening classifier')
    core.verify(inv['screen_seal'],inv['screen_sha256'])
    proof=core.read(Path(inv['screen_seal']).parent/'SCREEN_SELECTION.PRIVATE.json')
    REQ(proof['classifier_sha256']==screen.MATCHER_SHA256,'original committed classifier source')
    REQ(set(screen.KINDS)<=set(proof['selected'])<=set(screen.ALL_KINDS),'registered base groups and optional QA2 only')
    for kind in proof['selected']:
        REQ(kind in screen.ALL_KINDS,'registered optional QA2 only, never QA3')
        all_rows=sorted([r for r in proof['screening']if r['kind']==kind],key=lambda r:r['generation_index'])
        if kind in screen.KINDS:REQ(len(all_rows)=={'multi_hop':300,'one_hop':150}[kind],'full original300/150screen candidate pairs')
        REQ(len({r['generation_index']for r in all_rows})==len(all_rows),'unique original source order per family')
        qualifying=[r['pair_id']for r in all_rows if r['correct_both']]
        REQ(proof['selected'][kind]==qualifying[:screen.LIMITS[kind]],'first qualifying pairs, no post-reader selection')
    inventory=core.read(Path(spec['inventory_seal']).parent/'PAIRS.PRIVATE.json')
    for kind in proof['selected']:
        REQ(kind in screen.ALL_KINDS,'registered optional QA2 only, never QA3')
        REQ([p['pair_id']for p in inventory if p['kind']==kind]==proof['selected'][kind],'same frozen screened order/cohort')
    REQ(all(p['kind']in proof['selected']for p in inventory),'no unregistered or unscreened family')
    REQ(len({p['pair_id']for p in inventory})==len(inventory),'unique frozen selected pair IDs')
    proof_by=core.unique(proof['screening'],'pair_id')
    for p in inventory:
        REQ(p['generation_index']==proof_by[p['pair_id']]['generation_index'],'original screening generation order')
        if p['kind']=='babi_qa2':REQ(p.get('source_episode_id')is not None and p['source_episode_id']==proof_by[p['pair_id']]['source_episode_id'],'original frozen QA2 episode group')
        REQ(len(p['members'])==2 and [m['member']for m in p['members']]==[0,1],'two original ordered members')
        current=[m['current']for m in p['members']];previous=[m['previous']for m in p['members']]
        REQ(len(set(current))==2 and previous[0]==previous[1]and previous[0]not in current,'original recipient-only pair/common previous')
        REQ(len(set(p['value_map'].values()))==len(p['value_map'])and set(current+previous)<=set(p['value_map'].values()),'frozen one-to-one CPU value mapping')
    names=core.read(Path(spec['inventory_seal']).parent/'FIXED_NAMES.PRIVATE.json')
    REQ(isinstance(names,list)and len(names)>=3 and len(set(names))==len(names)and all(isinstance(v,str)and v for v in names),'original frozen name list')
    REQ(all(m['current']in names and m['previous']in names for p in inventory for m in p['members']),'all state labels within original fixed list')
    return dict(pairs=inventory,fixed_name_list=names)


def original_pairs(values,indices):
    """Select only frozen ORIGINAL pair rows; never mix contrasts or rewrite raw arrays."""
    REQ(isinstance(values,list)and isinstance(indices,list)and bool(indices)and len(set(indices))==len(indices)and all(type(k)is int and 0<=k<len(values)for k in indices),'explicit frozen original contrast indices')
    return [values[k]for k in indices]


def inputs(spec,inventory):
    seal=core.verify(spec['output_seal'],spec['output_sha256'])
    REQ(seal['experiment']=='E133'and seal['status']=='COMPLETE'and seal['inventory_sha256']==spec['inventory_sha256'],'complete same-inventory original sources')
    REQ(seal['reader_layers']==[44,52,60]and seal['vector_layers']==list(probes.LAYERS)and seal['no_steer']is True,'registered natural/no-steer read sites')
    REQ(seal['judging_bank']=='E133'and 0<seal['judging_cap_usd']<=5 and seal['route_verified']is True and seal['redaction_audit_complete']is True and seal['labels_cpu_only']is True,'registered blinded E133 bank/route/privacy')
    REQ(seal['rubric_sha256']==spec['rubric_sha256'],'exact committed adapted E104 rubric')
    sources=seal['source_seals'];ss=[core.verify(s['seal'],s['sha256'])for s in sources]
    REQ(all(s['experiment']=='E133'and s['status']in ('COMPLETE','COMPLETE_ONCE','SCREENED_COHORT_FROZEN')for s in ss),'complete original E133 sources, no pilot/substitution')
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


def descriptives(pairs):
    out={}
    for kind in screen.KINDS+(('babi_qa2',)if any(p['kind']=='babi_qa2'for p in pairs)else()):
        ms=[m for p in pairs if p['kind']==kind for m in p['members']]
        mass=[m['first_token_candidate_probability_masses']for m in ms if m['first_token_candidate_probability_masses']is not None]
        out[kind]=dict(planned_n=len(ms),text_unclassified_n=sum(m['text_no_value']for m in ms),text_classifier_abstention='parse_target_answer None: no unique candidate match (including multiple matches); no alternative parser',text_current_rate=rules.rate([None if m['text_answer']is None else int(m['text_answer']==m['current'])for m in ms]),text_previous_rate=rules.rate([None if m['text_answer']is None else int(m['text_answer']==m['previous'])for m in ms]),preference_status='NOT MEASURED'if all(m['preference_status']=='NOT MEASURED'for m in ms)else'MEASURED'if all(m['preference_status']=='MEASURED'for m in ms)else'PARTIALLY MEASURED',preferred_is_greedy_first=rules.rate([None if m['preferred_is_greedy_first']is None else int(m['preferred_is_greedy_first'])for m in ms]),probability_kind='GLOBAL vocabulary mass, not renormalized pair probability',candidate_mass_columns=['current','previous'],candidate_mass_known_n=len(mass),candidate_mass_missing_n=len(ms)-len(mass),candidate_mass_quartiles=None if not mass else np.quantile(np.asarray(mass),[.25,.5,.75],axis=0).tolist(),combined_mass_quartiles=None if not mass else np.quantile([sum(v)for v in mass],[.25,.5,.75]).tolist())
    return out


def run(spec,commit):
    protocol()
    REQ(not GUARD.exists(),'once guard consumed; no replay')
    from . import probe_phase
    probe_phase.available()
    inventory_metadata=metadata(spec);inventory=inventory_metadata['pairs']
    # Verify all source files before claim without computing numerical outcomes.
    seal=core.verify(spec['output_seal'],spec['output_sha256'])
    REQ(any(x['sha256']==spec['native_output_sha256']for x in seal['source_seals']),'original native capture bound to shared probe phase')
    for source in seal['source_seals']:core.verify(source['seal'],source['sha256'])
    out=core.claim(dict(analysis=spec['analysis'],guard=str(GUARD),output_sha256=spec['output_sha256']),commit)
    core.write(out/'FIRST_OPENING.json',dict(utc=datetime.now(timezone.utc).isoformat(),code_commit=commit,output_sha256=spec['output_sha256'],guard_sha256=core.sha(GUARD),stage='before first outcome join; operator clock record, not independent chronology certification'))
    pairs=inputs(spec,inventory);result,private=rules.analyze(pairs);result['probes_descriptive']=probe_phase.ensure(spec,commit,pairs,inventory_metadata['fixed_name_list'])
    result['text_preference_descriptive']=descriptives(pairs)
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',spec)
    pp=out/'PER_PAIR.PRIVATE.json';core.write(pp,private);pp.chmod(0o600)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E133',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=spec['inventory_sha256'],output_sha256=spec['output_sha256'],private_sha256=core.sha(pp),new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();print(run(core.read(a.spec),commit))

if __name__=='__main__':main()
