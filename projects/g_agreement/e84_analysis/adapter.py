"""E84 revived: CPU-only, sealed source joins, descriptive E81 signed rates."""
import argparse
import hashlib
import math
import subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e81_rt1.analysis import rate

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e84/deviation1/ANALYSIS_ONCE.json')
STATES=('last_test_passed','file_being_edited','failed_attempts')
SYSTEMS=('oracle','nla','text_generic')
REQ=core.require
NOT_BUILT_REASON='not built: the source agents were instructed not to execute tests'

def shard_counts(xs):
    REQ(isinstance(xs,list) and len(xs)>=2,'initial plus one confirmation shard')
    REQ(len({x['shard'] for x in xs})==len(xs),'distinct seeded shards')
    for x in xs:
        REQ(x['seed']==20261029 and x['sha256'] and type(x['trajectories']) is int and x['trajectories']>=0,'sealed shard counts')
        REQ(type(x['state_candidates']) is int and x['state_candidates']>=0,'state candidate count')

def committed():
    for name,digest in core.read(HERE/'DEPENDENCIES.json').items():
        REQ(core.sha(ROOT/name)==digest,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def gate(g):
    if g.get('disposition')=='NOT BUILT':
        REQ(g['reason']==NOT_BUILT_REASON,'registered source limitation')
        shard_counts(g['shard_counts'])
        return 'NOT BUILT'
    REQ(g['probe_fit_split']=='dev' and g['test_used_for_fit'] is False,'dev-only probe')
    REQ(g['probe_metric']=='test_AUROC' and g['probe_blocks']=={'oracle':44,'nla':42},'registered reader-specific probes')
    REQ(g['dev_n']==100 and g['test_n']==200 and g['bow_window_tokens']==512,'registered splits and BOW window')
    REQ(set(g['probe_test'])=={'oracle','nla'},'both probe dispositions')
    for v in list(g['probe_test'].values())+[g['bow_test']]:
        REQ(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1,'test AUROC')
    return 'TEXT_READABLE' if g['bow_test']>.65 else 'PASS'

def eligible(g):
    if gate(g)=='NOT BUILT':return ()
    return tuple(r for r in SYSTEMS if r=='text_generic' or g['probe_test'][r]>=.90)

def analyze(rows,gates):
    REQ(set(gates)==set(STATES),'all three state dispositions')
    REQ(len({(x['state'],x['item_id'],x['system']) for x in rows})==len(rows),'duplicate item/system')
    REQ(all(x['state'] in STATES and x['system'] in SYSTEMS for x in rows),'registered cells')
    report={'experiment':'E84','scope':'revived deviation1; DESCRIPTIVE','states':{},'decision_rules':'None registered for E84'}
    for state in STATES:
        status=gate(gates[state]);REQ(status!='NOT BUILT' or state in ('last_test_passed','failed_attempts'),'file row must be built');xs=[x for x in rows if x['state']==state]
        r={'disposition':status,'gates':gates[state],'test_target':200,'systems':{}}
        r['reader_dispositions']={} if status=='NOT BUILT' else {r:('PASS' if gates[state]['probe_test'][r]>=.90 else 'DROPPED_GATE') for r in ('oracle','nla')}
        if status=='NOT BUILT':REQ(not xs,'unbuilt state has no scores')
        else:
            systems=eligible(gates[state]);REQ(all(x['system'] in systems for x in xs),'failed reader dropped only for that reader')
            sets=[{x['item_id'] for x in xs if x['system']==s} for s in systems]
            REQ(all(len(ids)==200 for ids in sets) and all(ids==sets[0] for ids in sets),'same 200 test items for all systems')
            for system in systems:
                vals=[x['score'] for x in sorted(xs,key=lambda x:x['item_id']) if x['system']==system]
                REQ(all(v is None or type(v) is int and v in (-1,0,1) for v in vals),'signed E56 scores')
                r['systems'][system]=rate(vals)
        report['states'][state]=r
    return report

def inventory(inv,items):
    REQ(inv['experiment']=='E84' and inv['authority']=='revived deviation1' and inv['seed']==20261029,'registration')
    d=inv['dataset'];REQ(d['family']=='SWE-Zero OpenHands' and d['repository'] and d['revision'] and d['license']=='CC BY 4.0','exact public dataset receipt')
    REQ(d['anonymous_download'] is True and d['terms_acceptance_required'] is False,'ungated only')
    REQ(d['original_release_check_sha256'] and inv['parser_source_sha256'] and inv['probe_recipe_sha256'],'source/parser/probe custody')
    REQ(inv['read_point']=='start_of_next_assistant_turn' and inv['window_policy']=='complete_rendered_prefix' and inv['absence_window_tokens']==512 and inv['cropped'] is False and inv['reader_blocks']=={'oracle':44,'nla':42},'read sites/window')
    REQ(set(inv['ambiguity_counts'])==set(STATES) and all(type(n) is int and n>=0 for n in inv['ambiguity_counts'].values()),'all ambiguity drops counted')
    REQ(inv['state_dispositions']=={'file_being_edited':'BUILT','last_test_passed':'NOT BUILT','failed_attempts':'NOT BUILT'},'direct user Option1 scope')
    shard_counts(inv['confirmation_shards'])
    REQ(inv['additional_shard_confirmed'] is True and inv['e110_finished_before_e84_freeze'] is True,'confirmation and E110-first freeze order')
    REQ(len(items)==200,'full frozen file row test inventory')
    REQ(len({(x['state'],x['item_id']) for x in items.values()})==200,'unique state/item')
    for state in STATES:REQ(sum(x['state']==state for x in items.values())==(200 if state=='file_being_edited' else 0),'explicit built/unbuilt state counts')
    for x in items.values():
        REQ(x['split']=='test' and x['state_absent_from_last512'] is True and x['unambiguous_cpu_parse'] is True,'hidden unambiguous test state')
        REQ(x['source_transcript_sha256'] and x['window_sha256'] and x['parser_record_sha256'],'original item lineage')
        REQ(set(x['targets'])==set(SYSTEMS) and all(v in ('A','B') for v in x['targets'].values()),'per-system original private letters')

def inputs(s):
    ip=Path(s['inventory_seal']).resolve()
    b=subprocess.check_output(['git','show',s['inventory_commit']+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(len(s['inventory_commit'])==40 and hashlib.sha256(b).hexdigest()==s['inventory_sha256'],'pre-output committed inventory')
    inv=core.verify(ip,s['inventory_sha256']);REQ('INVENTORY.json' in inv['files'],'sealed inventory member');items=core.unique(core.read(ip.parent/'INVENTORY.json'));inventory(inv,items)
    core.verify(inv['e110_finished_seal']['seal'],inv['e110_finished_seal']['sha256'])
    for ref in inv['source_seals']:core.verify(ref['seal'],ref['sha256'])
    REQ(bool(inv['source_seals']),'original source/split/parser seals')
    op=Path(s['output_seal']);o=core.verify(op,s['output_sha256']);REQ({'GATES.json','MEASUREMENTS.json'}<=set(o['files']),'sealed normalized manifests')
    REQ(o['experiment']=='E84' and o['status']=='COMPLETE' and o['inventory_sha256']==s['inventory_sha256'],'complete inventory-bound output')
    for k in ('route_verified','privacy_verified','labels_cpu_only','one_greedy_readout_per_cell','same_window_verified','gate_before_readers_verified'):
        REQ(o[k] is True,'source/route/privacy/gate admission')
    sources=o['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    REQ(bool(ss),'original source/gate/reader/judge seals')
    def resolve(ref):
        i=ref['seal_index'];REQ(type(i) is int and 0<=i<len(ss),'source index')
        REQ(ref['member'] in ss[i]['files'],'sealed member')
        key=(i,ref['member'])
        if key not in cache:cache[key]=core.read(Path(sources[i]['seal']).parent/ref['member'])
        value=cache[key]
        for k in ref['keys']:value=value[k]
        return value
    gates={k:resolve(v) for k,v in core.read(op.parent/'GATES.json').items()}
    REQ(set(gates)==set(STATES),'full gate inventory')
    REQ(all(gates[k].get('disposition')=='NOT BUILT' for k in ('last_test_passed','failed_attempts')),'both source-limited rows retained as unbuilt')
    passing={k for k,v in gates.items() if gate(v)!='NOT BUILT'}
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json'))
    REQ(set(ms)=={k for k,v in items.items() if v['state'] in passing},'no omitted passing or added failed items')
    rows=[]
    for ident,m in ms.items():
        x=items[ident];REQ(set(m['systems'])==set(eligible(gates[x['state']])),'exact eligible reader/baseline grid')
        for system,refs in m['systems'].items():
            REQ(set(refs)=={'text','code','target_letter','window_sha256'},'exact original pointers')
            REQ(resolve(refs['target_letter'])==x['targets'][system] and resolve(refs['window_sha256'])==x['window_sha256'],'private target and identical window')
            code=resolve(refs['code']);text=resolve(refs['text'])
            REQ(code is None or code['id']==m['judgment_ids'][system],'original code identity')
            score=None if code is None else core.score(code,x['targets'][system],text)
            rows.append(dict(state=x['state'],item_id=x['item_id'],system=system,score=score))
    return rows,gates,inv

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=core.read(a.spec);rows,gates,inv=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(rows,gates);result['ambiguity_counts']=inv['ambiguity_counts'];result['dataset']=inv['dataset']
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E84',authority='revived deviation1',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=s['inventory_sha256'],output_sha256=s['output_sha256'])
if __name__=='__main__':main()
