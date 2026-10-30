"""Literal sealed-source validation followed by one fixed CPU guard."""
import argparse
import os
import subprocess
from pathlib import Path, PurePosixPath
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.e127_analysis.common import require
from .analysis import analyze, BLOCKS
from .value_records import preserve_record
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e140/ANALYSIS_ONCE.json'


def committed():
    receipt=read(HERE/'SOURCE_RECEIPT.json')
    for name,h in receipt['files'].items():
        require(sha(ROOT/name)==h,'frozen source hash')
        require(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)==(ROOT/name).read_bytes(),'committed source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def verify_selection(screen, pairs, original_pair_ids=None):
    n=600 if original_pair_ids is None else 300
    require(len(screen)==n and len({r['pair_id'] for r in screen})==n,'full registered screen pairs')
    if original_pair_ids is not None:
        require(type(original_pair_ids)is list and len(original_pair_ids)==600 and len(set(original_pair_ids))==600,'original frozen600 identity census')
        require([r['pair_id'] for r in screen]==original_pair_ids[:300],'literal first300 original pairs, no reranking')
    eligible=[]
    for i,r in enumerate(screen):
        require(r['generation_index']==i and r['greedy_max_new_tokens']==32,'original generation order and cap')
        require(type(r['answer_A']) is str and type(r['answer_B']) is str,'original frozen parser strings')
        if r['answer_A'] and r['answer_B'] and r['answer_A']!=r['answer_B']:
            eligible.append((r['pair_id'],r['answer_A'],r['answer_B']))
    require([(p['pair_id'],p['X'],p['Y']) for p in pairs]==eligible[:84],'first84 literal original screen labels; no replacement/selection')


def native_identity(p, identity, native, block, ref):
    """Use the original sealed Oracle index when records have no embedded ID."""
    if 'native_index' not in p:
        require(identity['native_id']==native['id'],'original native join')
        return
    ip=p['native_index']; np=p['native']; index=ref(ip)
    require(PurePosixPath(ip['member']).name=='INDEX.json','original native index member')
    require(ip['seal_index']==np['seal_index'],'index and native share original seal')
    require(index['kind']=='oracle' and index['block']==block,'original Oracle index site')
    require(index['id']==identity['native_id'],'literal original index identity')
    require(type(index['record']) is int and index['record']>=0,'original record offset')
    require(np['member']==str(PurePosixPath(ip['member']).parent/index['member']) and np['keys']==[index['record']],'exact index member/record pointer')
    require('id' not in native or native['id']==index['id'],'no contradictory embedded identity')


def load(spec):
    require(spec['experiment']=='E140' and spec['status']=='COMPLETE','complete E140 specification')
    require(spec['other_policy_authority']=='direct_user_xy_only' and spec['other_policy']=='xy_only','resolved pre-output denominator authority')
    require(spec.get('multiple_value_authority')=='252_clarification2_d1d15ccf2','explicit multiple-value primary/sensitivity authority')
    inv=verify(spec['inventory_seal'],spec['inventory_sha256'])
    require(inv['experiment']=='E140' and inv['selection_frozen_before_reads'] is True and inv['labels_cpu_only'] is True,'frozen CPU selection')
    require(inv['seed']==20261030 and inv['screen_candidates'] in (300,600) and inv['category_count']>=8,'registered screen inventory')
    require(inv['selection']=='first_up_to84_nonempty_different_in_generation_order' and inv['parser']=='first_nonempty_line_lowercase_punctuation_stripped','original selection/parser')
    require(inv['other_policy']==spec['other_policy'],'pre-output denominator binding')
    pairs=read(Path(spec['inventory_seal']).parent/'PAIRS.PRIVATE.json')
    require(40<=len(pairs)<=84 and len({p['pair_id'] for p in pairs})==len(pairs),'eligible fixed pair roster')
    require(all(p['X'] and p['Y'] and p['X']!=p['Y'] for p in pairs),'distinct original per-paraphrase answers')
    screen_seal=verify(spec['screen_seal'],spec['screen_sha256'])
    require(screen_seal['experiment']=='E140' and screen_seal['status']=='COMPLETE' and screen_seal['parser_frozen_before_screen'] is True,'original completed frozen-parser screen')
    require(screen_seal['selection_frozen_before_reads'] is True and screen_seal['no_answer_words_in_prompts_verified'] is True,'prospective source/selection custody')
    require(inv['screen_sha256']==spec['screen_sha256'],'inventory binds original screen')
    for source in screen_seal['source_seals']:verify(source['seal'],source['sha256'])
    original_ids=None
    if inv['screen_candidates']==300:
        require(spec.get('screen_scope_authority')=='252_deviation2_b10b2694e','explicit first300 authority')
        require(screen_seal.get('screen_candidates')==300,'same reduced scope in original screen seal')
        parent=spec['original_pair_ids_ref']
        parent_seal=verify(parent['seal'],parent['sha256'])
        require(parent['member'] in parent_seal['files'],'sealed original600 parent identity member')
        original_ids=read(Path(parent['seal']).parent/parent['member'])
        for key in parent['keys']:original_ids=original_ids[key]
        require(inv.get('parent_identity_sha256')==parent['sha256'],'selection binds original600 parent')
    verify_selection(read(Path(spec['screen_seal']).parent/'SCREEN_PAIRS.PRIVATE.json'),pairs,original_ids)

    out=verify(spec['output_seal'],spec['output_sha256'])
    require(out['experiment']=='E140' and out['status']=='COMPLETE' and out['inventory_sha256']==spec['inventory_sha256'],'terminal bound outputs')
    require(out['layers']==list(BLOCKS) and out['read_position']=='final_prompt_token','original read sites')
    require(out['judging_bank']=='E140' and 0<out['judging_cap_usd']<=1 and 0<=out['lifetime_booked_usd']<=out['judging_cap_usd'] and out['unknown_charge_requests']==0,'same terminal USD1 bank')
    require(all(out[k] is True for k in ('route_verified','labels_cpu_only','redaction_audit_complete')) and out['redacted_count']==0,'privacy/source admission')
    sources=out['source_seals']; seals=[verify(s['seal'],s['sha256']) for s in sources]; cache={}
    def ref(p):
        n=p['seal_index'];require(type(n)is int and 0<=n<len(seals) and p['member'] in seals[n]['files'],'sealed original pointer')
        require(seals[n]['status'] in ('COMPLETE','COMPLETE_ONCE'),'terminal original source')
        key=(n,p['member'])
        if key not in cache:cache[key]=read(Path(sources[n]['seal']).parent/p['member'])
        v=cache[key]
        for k in p['keys']:v=v[k]
        return v
    rows=read(Path(spec['output_seal']).parent/'MEASUREMENTS.PRIVATE.json')
    require([r['pair_id'] for r in rows]==[p['pair_id'] for p in pairs],'exact selected order')
    normalized=[]; used=set()
    for row in rows:
        require(set(row['blocks'])=={str(b) for b in BLOCKS},'full block grid')
        target={'pair_id':row['pair_id'],'blocks':{}}
        for b in BLOCKS:
            arms=row['blocks'][str(b)];require(set(arms)=={'A','B'},'both paraphrases')
            target['blocks'][str(b)]={}
            for arm,p in arms.items():
                identity=ref(p['identity']);judgment=ref(p['judgment']);native=ref(p['native'])
                require(identity['pair_id']==row['pair_id'] and identity['paraphrase']==arm and identity['block']==b,'literal identity join')
                require(identity['judgment_id']==judgment['id'],'original code join')
                native_identity(p,identity,native,b,ref)
                require(judgment['id'] not in used,'one judgment per readout');used.add(judgment['id'])
                cell=preserve_record(judgment,native['text'])
                target['blocks'][str(b)][arm]=cell
        normalized.append(target)
    require(len(used)==6*len(rows)<=504,'full original readout census')
    return normalized


def run(path):
    commit=committed();require(not GUARD.exists(),'consumed guard; never replay')
    spec=read(path);rows=load(spec);result=analyze(rows,spec['other_policy'])
    out=GUARD.parent/'analysis_once';require(not out.exists(),'fresh output only')
    GUARD.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(GUARD,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write('{"experiment":"E140","status":"CLAIMED_ONCE"}\n')
    out.mkdir();write(out/'RESULTS.json',result);write(out/'BINDING.PRIVATE.json',spec)
    write(out/'ANALYSIS_SEAL.json',dict(experiment='E140',status='COMPLETE_ONCE',code_commit=commit,files={n:sha(out/n) for n in ('RESULTS.json','BINDING.PRIVATE.json')}))
    return out/'ANALYSIS_SEAL.json'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);print(run(p.parse_args().spec))
