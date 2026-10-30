"""§231 descriptive stale agreement; original E94 class/join/precision/Wilson."""
import argparse,hashlib,importlib.util,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core as c
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
p=ROOT/'results/g_agreement/understand/e94/score94.py'
spec=importlib.util.spec_from_file_location('e94_frozen',p);e94=importlib.util.module_from_spec(spec);spec.loader.exec_module(e94)
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e121/ANALYSIS_ONCE.json'

def analyze(rows):
    c.unique(rows)
    c.require(len(rows)==336,'84 items x two conditions x two readers')
    ids={r['item_id'] for r in rows};c.require(len(ids)==84,'original84 item census')
    c.require({(r['item_id'],r['condition'],r['reader']) for r in rows}=={(i,a,rd) for i in ids for a in ('steered','random') for rd in ('oracle','nla')},'exact paired grid')
    out={}
    for condition in ('steered','random'):
        xs=[dict(bank='E121',unit=r['item_id'],cluster=r['item_id'],reader=r['reader'],**{'class':r['class']}) for r in rows if r['condition']==condition]
        pairs,audit=e94.join(xs);point=e94.point(pairs)
        agreements=[p for p in pairs if p['oracle']==p['nla'] and p['oracle']!='no mention']
        stale=e94.fraction(sum(p['oracle']=='wrong' for p in agreements),len(agreements));v=stale['rate']
        out[condition]=dict(same_value_agreement=e94.fraction(len(agreements),len(pairs)),old_given_agreement=stale,E94=point,audit=audit,
            reading='NOT EVALUABLE' if v is None else 'agreement endorses stale readout' if v>=.50 else 'disagreement flags staleness' if v<=.20 else 'intermediate')
    return dict(experiment='E121',authority='§231',status='DESCRIPTIVE',conditions=out,ground_truth='steered value',denominator='common parseable items; decisive same-value agreement excludes both-no-mention',fixed_items=84)

def config_cohort(config, items):
    c.require(config['experiment']=='E121' and config['row']=='fact_recall' and config['base_items']==84 and config['items']==168 and config['conditions']==['steered','random'],'original E121 config scope')
    capture=config['capture'];reader=config['reader']
    c.require(capture['alpha']==8 and capture['write_block']==40 and capture['args']['arm']=='U' and capture['module_parameters']['READ_BLOCK']==42 and reader['native_layer']==42 and reader['setup']=='load_nla only; never load_oracle','original U40 alpha8 NLA42 configuration')
    c.require(config['public_input']['all84_original_flips_verified'] is True and config['cpu_only']['sha256']==config['public_input']['original_flip_source_sha256'],'original frozen flip lineage')
    ids={x['base_id'] for x in items}
    c.require(len(items)==168 and len(ids)==84 and len({x['id'] for x in items})==168,'full original frozen input census')
    c.require({(x['base_id'],x['condition']) for x in items}=={(i,a) for i in ids for a in ('steered','random')},'exact original paired cohort')
    c.require(all(x['row']=='fact_recall' and x['alpha']==8 for x in items),'unchanged row and dose')
    return sorted(ids)

def plan_ids(s):
    if s.get('plan_mode')=='original_config_and_inputs':
        # Representation-only custody: use existing pre-output config and sealed inputs.
        # Never create or backdate a replacement PLAN.json.
        commit='39b1116039e0f12bed4c6755c8154449381a71b0'
        name='projects/g_agreement/e121/nla.json'
        import json
        config=json.loads(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT))
        op=Path(s['original_input_seal'])
        seal=c.verify(op,config['public_input']['input_sha256'])
        c.require(seal['experiment']=='E121' and 'items.json' in seal['files'] and seal['files']['deltas.npy']==config['public_input']['original_delta_sha256'],'original committed input/delta binding')
        c.require(config['cpu_only']['sha256']=='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4','original E104 flipped cohort binding')
        return config_cohort(config,c.read(op.parent/'items.json'))
    plan=Path(s['plan']);c.require(c.sha(plan)==s['plan_sha256'] and hashlib.sha256(subprocess.check_output(['git','show',s['plan_commit']+':'+str(plan.resolve().relative_to(ROOT))],cwd=ROOT)).hexdigest()==s['plan_sha256'],'committed plan')
    p=c.read(plan);c.require(p['row']=='fact_recall' and p['arm']=='U' and p['hook_block']==40 and p['alpha']==8 and p['reader_blocks']=={'oracle':44,'nla':42},'registered source scope')
    ids=p['item_ids'];c.require(len(ids)==84 and len(set(ids))==84,'frozen84 flipped IDs')
    return ids

def inputs(s):
    op=Path(s['binding_seal']);b=c.verify(op,s['binding_sha256'])
    c.require(b['experiment']=='E121' and b['status']=='COMPLETE','complete E121 binding')
    for k in ('route_verified','privacy_verified','labels_cpu_only','original_E104_oracle_judgments_verified','same_E104_hook_verified','pre_output_plan_verified'):
        c.require(b[k] is True,k)
    ids=plan_ids(s)
    sources=b['source_seals'];ss=[c.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];c.require(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'sealed original reference')
        key=(i,x['member'])
        if key not in cache:cache[key]=c.read(Path(sources[i]['seal']).parent/x['member'])
        v=cache[key]
        for k in x['keys']:v=v[k]
        return v
    c.require('MEASUREMENTS.json' in b['files'],'sealed measurements')
    rows=[]
    for m in c.read(op.parent/'MEASUREMENTS.json'):
        c.require(m['item_id'] in ids,'original item')
        code=ref(m['code']);text=ref(m['text']);target=ref(m['steered_letter']);old=ref(m['old_letter'])
        c.require(target in ('A','B') and old in ('A','B') and old!=target,'original distinct old/new candidates')
        if code is not None:
            c.require(code['id']==m['judgment_id'],'original judgment identity');c.score(code,target,text)
        rows.append(dict(id=m['id'],item_id=m['item_id'],condition=m['condition'],reader=m['reader'],**{'class':None if code is None else e94.value_class(code,target)}))
    return rows

def committed():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed scientific source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=c.read(a.spec);rows=inputs(s)
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',analyze(rows));c.write(out/'BINDING.json',s);c.seal(out,'ANALYSIS_SEAL.json',experiment='E121',status='COMPLETE_ONCE',code_commit=commit)
if __name__=='__main__':main()
