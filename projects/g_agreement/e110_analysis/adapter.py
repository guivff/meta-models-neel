"""§223.4: reuse frozen E82/E107 estimands; no capture/filter/judge calls."""
import argparse,hashlib,subprocess,random
from datetime import datetime,timezone
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e82_analysis.analyze import row_summary
from projects.g_agreement.e107_analysis.rules import compare,verdict
from projects.g_agreement.e107_analysis.adapter import evaluate
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e110/ANALYSIS_ONCE.json')
REQ=core.require

def committed():
    for p,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/p)==h,'frozen dependency changed')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(blob).hexdigest()==core.sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def analyze(items, e82_reference=None):
    identities=[(x['row'],x['item_id']) for x in items];REQ(len(set(identities))==len(items),'unique source items')
    wrong=[x for x in items if x['cohort']=='belief_wrong']
    if len(wrong)<60:return dict(experiment='E110',status='NOT RUN',reason='fewer than60 belief-wrong survivors',belief_wrong=len(wrong))
    out=dict(experiment='E110',authority='§223 item4',status='COMPLETE',belief_wrong=len(wrong),target150_met=len(wrong)>=150,bootstrap=dict(draws=5000,seed=0,unit='source item',R_B2='fixed named-value cohort',R_OL1='paired source items with system-specific naming denominators'),cohorts={})
    for cohort in ('belief_wrong','belief_right'):
        xs=sorted([x for x in items if x['cohort']==cohort],key=lambda x:(x['row'],x['item_id']));out['cohorts'][cohort]={}
        for reader in ('oracle','nla'):
            REQ(all(set(x['systems'])=={'oracle','nla','outside'} for x in xs),'full three-system grid')
            rb=row_summary([dict(belief=x['systems'][reader]['belief'],truth=x['systems'][reader]['truth'],any_named=x['systems'][reader]['named']) for x in xs])
            ol=compare(xs,reader,'outside','belief',True)
            out['cohorts'][cohort][reader]=dict(R_B2_statistic=rb,reader_vs_outside=ol)
    out['rules']={}
    for reader in ('oracle','nla'):
        z=out['cohorts']['belief_wrong'][reader];b=z['R_B2_statistic'];v=verdict(z['reader_vs_outside']['difference'])
        out['rules'][reader]=dict(R_B2_prime='NOT EVALUABLE' if not b['evaluable'] else 'MET' if b['criterion_met'] else 'NOT MET',R_OL1_prime=v['R_OL1'],R_OL1_falsifier_descriptive=v['falsifier'],role='confirmatory' if reader=='oracle' else 'descriptive')
    if e82_reference is not None:
        out['descriptive_banks']={'E82_wrong_bridge': reference_summary(e82_reference)}
    return out

def reference_summary(items):
    REQ(len(items)==100 and len({x['item_id'] for x in items})==100,'exact original100 E82 reference items')
    REQ(all(x['row']=='wrong_bridge' and x['cohort']=='belief_wrong' and set(x['systems'])=={'oracle','nla','outside'} for x in items),'original wrong_bridge cohort and three systems')
    xs=sorted(items,key=lambda x:(x['row'],x['item_id']))
    stats={}
    for reader in ('oracle','nla'):
        rb=row_summary([dict(belief=x['systems'][reader]['belief'],truth=x['systems'][reader]['truth'],any_named=x['systems'][reader]['named']) for x in xs])
        # Preserve the original numerical statistic; do not promote its old criterion to a new rule.
        stats[reader]=dict(R_B2_statistic=rb,reader_vs_outside=compare(xs,reader,'outside','belief',True))
    return dict(role='descriptive only; excluded from E110 eligibility and confirmatory rules',items=100,statistics=stats)

def filter_contract(inv,meta):
    REQ(inv['experiment']=='E110' and inv['seed']==20261029,'registered experiment/seed')
    if inv.get('deviation')==2:
        REQ(inv['item_source']=='E82_long_tail_bridge' and inv['candidate_count']==3000,'deviation2 frozen3000 generated candidates')
        REQ(inv['generation_method']=='E82_wrong_bridge' and inv['long_tail_source_bound'] is True,'original method and sealed low-frequency evidence')
    else:
        REQ(inv['item_source']=='TwoHopFact' and inv['dataset_revision']=='59a84cd883f71641a03fb6fa50da92a9603e7845','registered dataset revision')
        REQ(inv['dataset_repository']=='soheeyang/TwoHopFact' and inv['license']=='CC BY 4.0' and inv['anonymous_download'] is True,'dataset access receipt')
    REQ(type(inv['candidate_count']) is int and 0<=inv['candidate_count']<=3000 and inv['composition_types']==52,'sampled candidate scope')
    counts=inv['filter_counts'];stable=counts['stable_belief_wrong'];native=counts['native_belief_wrong']
    REQ(type(stable) is int and type(native) is int and 0<=stable<=native<=inv['candidate_count'],'filter counts')
    mode='stable belief' if stable>=60 else 'no paraphrase gate' if native>=60 else 'NOT RUN'
    REQ(inv['selection_mode']==mode,'fixed fallback, no post-output selection')
    expected=stable if stable>=60 else native
    REQ(inv['survivor_counts']['belief_wrong']==expected,'all selected wrong survivors')
    for x in meta.values():
        REQ(x['split']=='test' and x['read_token']=='end_of_native_two_hop_prompt','native two-hop read site')
        if x['cohort']=='belief_wrong':
            REQ(x['one_hop_correct'] is False and x['two_hop_correct'] is False,'wrong bridge AND wrong final answer')
            if mode=='stable belief':REQ(x['stable_one_hop_paraphrases']==3,'native plus two frozen relation paraphrases')
        else:REQ(x['one_hop_correct'] is True and x['two_hop_correct'] is True and x['matched_composition_type'] is True,'matched belief-right')
    return mode

def shard_contract(inv,meta,receipt):
    """Amendment1 custody only; never select from partial/old attempt outputs."""
    REQ(receipt['authority']=='aa8438c71' and receipt['restart_index']==1,'single authorized restart')
    candidates=receipt['original_candidate_ids']
    REQ(len(candidates)==3000 and len(set(candidates))==3000,'unchanged full source sample')
    ordered=sorted(candidates);random.Random(20261029).shuffle(ordered)
    shards=receipt['shards'];REQ(len(shards)==4 and {x['quarter'] for x in shards}==set(range(4)),'all four dispositions')
    selected=set();complete=[];jobs=set()
    cutoff=datetime(2026,10,29,15,tzinfo=timezone.utc)
    at=datetime.fromisoformat(receipt['selection_at'].replace('Z','+00:00'))
    REQ(at.tzinfo is not None,'timezone required')
    old=receipt['excluded_attempt']
    REQ(old['status']=='NO_FIT' and old['output_count']==192 and old['excluded'] is True,'old partial attempt explicitly excluded')
    old_jobs=set(old['job_ids']);REQ(len(old_jobs)==192,'exact old job census')
    for x in shards:
        q=x['quarter'];REQ(x['candidate_ids']==ordered[q*750:(q+1)*750],'frozen seeded quarter membership/order')
        REQ(x['status'] in ('COMPLETE','NOT COMPLETE'),'explicit terminal shard disposition')
        REQ(x['included'] is (x['status']=='COMPLETE'),'all and only complete shards')
        if not x['included']:
            REQ(at>=cutoff,'partial-grid selection only at registered cutoff');continue
        ended=datetime.fromisoformat(x['completed_at'].replace('Z','+00:00'))
        REQ(ended.tzinfo is not None and ended<=at,'complete before selection')
        REQ(x['attempt_id']!=old['attempt_id'],'exclude old attempt lineage')
        ids=set(x['job_ids']);REQ(len(ids)==len(x['job_ids']) and not(ids & (old_jobs|jobs)),'unique new quarter jobs, no old outputs')
        REQ(x['prompt_bytes_unchanged'] is True and x['all_candidate_jobs_complete'] is True,'complete unchanged prompts')
        jobs.update(ids);selected.update(x['candidate_ids']);complete.append(q)
    if len(complete)<4:
        REQ(all(datetime.fromisoformat(x['completed_at'].replace('Z','+00:00'))<=cutoff for x in shards if x['included']),'cutoff snapshot only')
    REQ(inv['candidate_count']==len(selected),'achieved candidate count')
    REQ(all(x['candidate_id'] in selected for x in meta.values()),'no survivors from excluded shards')
    return dict(authority='§223 amendment1',original_candidates=3000,achieved_candidates=len(selected),complete_quarters=sorted(complete),excluded_original_outputs=192,selection_at=receipt['selection_at'])

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit'];REQ(len(commit)==40,'full pre-output inventory commit')
    b=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(hashlib.sha256(b).hexdigest()==s['inventory_sha256'],'committed selected inventory')
    inv=core.verify(ip,s['inventory_sha256'])
    REQ(inv['filter_source_seal'] and inv['original_item_source_seal'],'frozen source/filter evidence')
    for entry in (inv['filter_source_seal'],inv['original_item_source_seal']):core.verify(entry['seal'],entry['sha256'])
    meta=core.unique(core.read(ip.parent/'INVENTORY.json'))
    if inv.get('deviation')==2:
        inv['shard_summary']=dict(authority='§223 deviation2',historical_TwoHopFact='NOT RUN; excluded')
    else:
        sr=inv['shard_source_seal'];ss=core.verify(sr['seal'],sr['sha256'])
        REQ('SHARD_RECEIPT.json' in ss['files'],'shard receipt covered by seal')
        shard_receipt=core.read(Path(sr['seal']).parent/'SHARD_RECEIPT.json')
        inv['shard_summary']=shard_contract(inv,meta,shard_receipt)
    filter_contract(inv,meta);counts={c:sum(x['cohort']==c for x in meta.values()) for c in ('belief_wrong','belief_right')}
    REQ(counts==inv['survivor_counts'] and sum(counts.values())==len(meta),'all selected cohorts retained')
    for x in meta.values():
        REQ(x['bank']=='E82' and x['systems']==['oracle','nla','outside'],'E82 rubric and full systems')
        REQ(set(x['target_letters_by_system'])==set(x['systems']),'per-system original letters')
    if counts['belief_wrong']<60:return [],inv
    return output_items(s,meta),inv

def output_items(s,meta):
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    REQ(seal['experiment']=='E110' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete bound bank')
    REQ(seal['route_verified'] is True and seal['privacy_verified'] is True and seal['labels_cpu_only'] is True,'route/privacy custody')
    REQ(seal['reader_blocks']==dict(oracle=44,nla=42) and seal['one_greedy_readout_per_item'] is True,'registered reader sites/count')
    REQ(seal['outside_generation']==dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',temperature=0,max_tokens=256,ZDR=True,data_collection='deny',fallbacks=False),'E107 outside describer')
    ss=[core.verify(x['seal'],x['sha256']) for x in seal['source_seals']];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'sealed source pointer')
        p=Path(seal['source_seals'][i]['seal']).parent/x['member']
        if p not in cache:cache[p]=core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    REQ('MEASUREMENTS.json' in seal['files'],'sealed measurement census')
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json'));REQ(set(ms)==set(meta),'exact inventory; no exclusions')
    out=[]
    for ident,x in meta.items():
        data=ms[ident]['systems'];REQ(set(data)==set(x['systems']),'three system grid');values={}
        for system,targets in data.items():
            REQ(set(targets)=={'belief','truth'},'both original targets');values[system]={}
            for target,fields in targets.items():
                REQ(set(fields)=={'text','code','target_letter'},'original text/code/letter pointers')
                values[system][target]={k:ref(v) for k,v in fields.items()}
        out.append(evaluate(x,values))
    return out

def reference_inputs(s):
    ip=Path(s['inventory_seal']).resolve()
    blob=subprocess.check_output(['git','show',s['inventory_commit']+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed E82 reference inventory')
    inv=core.verify(ip,s['inventory_sha256'])
    REQ(inv['experiment']=='E110' and inv['bank_role']=='E82_wrong_bridge_descriptive','separate descriptive bank')
    REQ('INVENTORY.json' in inv['files'],'sealed reference census')
    source=inv['original_e82_source'];original=core.verify(source['seal'],source['sha256'])
    pointer=source['wrong_bridge_item_ids'];REQ(pointer['member'] in original['files'],'original E82 census pointer')
    ids=core.read(Path(source['seal']).parent/pointer['member'])
    for key in pointer['keys']:ids=ids[key]
    REQ(isinstance(ids,list) and len(ids)==100 and len(set(ids))==100,'original100 exact IDs')
    meta=core.unique(core.read(ip.parent/'INVENTORY.json'))
    REQ(len(meta)==100 and {x['item_id'] for x in meta.values()}==set(ids),'all and only original E82 IDs')
    REQ(all(x['row']=='wrong_bridge' and x['cohort']=='belief_wrong' and x['bank']=='E82' and x['split']=='test' and x['systems']==['oracle','nla','outside'] for x in meta.values()),'unaltered reference cohort')
    return output_items(s,meta)

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=committed();s=core.read(args.spec);items,inv=inputs(s)
    reference=None
    if inv.get('deviation')==2 and inv['survivor_counts']['belief_wrong']>=60:
        reference=reference_inputs(s['e82_reference'])
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s.get('output_sha256',s['inventory_sha256'])),commit)
    result=analyze(items,reference);result['selection_mode']=inv['selection_mode'];result['item_source']=inv['item_source'];result['authority']='§223 deviation2' if inv.get('deviation')==2 else '§223 deviation1 / clarification1 / amendment1';result['shard_summary']=inv['shard_summary']
    if inv['survivor_counts']['belief_wrong']<60:result['belief_wrong']=inv['survivor_counts']['belief_wrong']
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E110',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=s['inventory_sha256'],output_sha256=s.get('output_sha256'))
if __name__=='__main__':main()
