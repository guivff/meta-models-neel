"""Source-bound E126 once-only CPU adapter; no model, reader or judge calls."""
import argparse,hashlib,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from . import rules
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/e126/ANALYSIS_ONCE.json')
PRIVATE_SHA='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4'
REQ=core.require


def committed():
    for name,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/name)==h,'changed dependency '+name)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(blob).hexdigest()==core.sha(p),'uncommitted adapter '+p.name)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def cohort(spec):
    ip=Path(spec['inventory_seal']);seal=core.verify(ip,spec['inventory_sha256'])
    REQ(seal['experiment']=='E126' and seal['status']=='SOURCE_ONLY_COHORT_BOUND' and seal['labels_cpu_only'] is True,'source-only original cohort')
    REQ(seal['source_e104_private_sha256']==PRIVATE_SHA==core.sha(spec['e104_private']),'original E104 flipped identities')
    private=core.read(spec['e104_private']);inventory=core.read(ip.parent/'INVENTORY.json');REQ(set(inventory)==set(rules.ROWS),'both original rows')
    for row,n in rules.ROWS.items():
        prior={x['item_id']:x for x in private if x['row']==row and x['arm']=='U' and x['condition']=='steered' and x['flipped']}
        by=core.unique(inventory[row],'item_id');REQ(len(by)==n and set(by)==set(prior),'unchanged E109/E104 cohort')
        for i,x in by.items():
            REQ(x['steered_value']==prior[i]['target'] and x['candidate_A_value'] in ('A','B'),'original target orientation')
            REQ(type(x['pair_count'])is int and x['pair_count']>0 and x['candidate_ids_sha256'],'original frozen continuation inventory')
    return inventory


def inputs(spec,inventory):
    op=Path(spec['output_seal']);seal=core.verify(op,spec['output_sha256'])
    REQ(seal['experiment']=='E126' and seal['status']=='COMPLETE' and seal['inventory_sha256']==spec['inventory_sha256'],'complete original normalized pointer grid')
    REQ(seal['blocks']==list(rules.BLOCKS) and seal['labels_cpu_only'] is True and seal['logits_only'] is True
        and seal['new_reader_or_judge_calls']==0,'registered logits-only source')
    REQ(seal['steer']==dict(block=40,positions='eight_before_read',alpha_by_row={'fact_recall':8,'language_plan':2}),'original E104 armU steer')
    sources=seal['source_seals'];metas=[core.verify(x['seal'],x['sha256'])for x in sources];cache={}
    def ref(pointer,numerical=False,direction=None):
        i=pointer['seal_index'];REQ(type(i)is int and 0<=i<len(metas) and pointer['member'] in metas[i]['files'],'sealed original source pointer')
        if numerical:REQ(metas[i]['status']=='COMPLETE' and metas[i]['experiment'] in (('E104','E109','E126','E105') if direction=='clean' else ('E104','E109','E126')),'no partial or unrelated raw scores')
        key=(i,pointer['member'])
        if key not in cache:cache[key]=core.read(Path(sources[i]['seal']).parent/pointer['member'])
        obj=cache[key];REQ(isinstance(pointer['keys'],list) and all(type(k)in(int,str)for k in pointer['keys']),'literal original JSON pointer')
        for k in pointer['keys']:obj=obj[k]
        return obj
    ms=core.read(op.parent/'MEASUREMENTS.json');REQ(set(ms)==set(rules.ROWS),'both measured rows')
    records=[]
    for row,items in inventory.items():
        by=core.unique(ms[row],'item_id');REQ(set(by)=={x['item_id']for x in items},'complete original item grid')
        for item in items:
            m=by[item['item_id']]
            def score(cell,direction,block=None,patch=None):
                identity=ref(cell['identity']);raw=ref(cell['raw'],numerical=True,direction=direction)
                REQ(identity['item_id']==item['item_id'] and identity['row']==row and identity['direction']==direction
                    and identity['block']==block and identity['patch']==patch,'original source identity/mode/site join')
                REQ(raw['id']==identity['raw_id'] and identity['steered_value']==item['steered_value']
                    and identity['candidate_A_value']==item['candidate_A_value'] and identity['candidate_ids_sha256']==item['candidate_ids_sha256']
                    and identity['pair_count']==item['pair_count'],'original frozen continuation/target binding')
                if block is not None:
                    REQ(identity['patch_binding_verified'] is True,'original intervention binding')
                    if patch!='random_norm_matched':REQ(identity['unscaled_residual_replacement'] is True,'unscaled original residual replacement')
                    if patch=='earlier_token':
                        p=identity['position'];r=identity['read_index'];REQ(type(p)is int and type(r)is int and 0<=p<r-8,'earlier token outside eight steered positions and read token')
                    else:REQ(identity['position']==identity['read_index'],'read-token patch/control')
                    if patch=='random_norm_matched':REQ(identity['norm_matched'] is True and type(identity['random_seed'])is int,'frozen norm-matched random control')
                return rules.log_odds(raw['pair_logprobs'],item['steered_value'],item['candidate_A_value'],item['pair_count'])
            patches={};REQ(set(m['patches'])=={str(b)for b in rules.BLOCKS},'five measured blocks')
            for block in rules.BLOCKS:
                z=m['patches'][str(block)];REQ(set(z)==set(rules.DIRECTIONS),'both measured directions');patches[block]={}
                for direction in rules.DIRECTIONS:
                    REQ(set(z[direction])==set(rules.PATCHES),'read patch and both controls')
                    patches[block][direction]={p:score(z[direction][p],direction,block,p)for p in rules.PATCHES}
            records.append(dict(item_id=item['item_id'],row=row,clean=score(m['clean'],'clean'),steered=score(m['steered'],'steered'),patches=patches))
    return records


def run(spec,commit):
    REQ(not GUARD.exists(),'once guard consumed; no replay')
    inventory=cohort(spec);records=inputs(spec,inventory)
    out=core.claim(dict(analysis=spec['analysis'],guard=str(GUARD),output_sha256=spec['output_sha256']),commit)
    result,per_item=rules.analyze(records)
    # Raw item log-odds and ratios stay local CPU, including undefined denominators.
    private=out/'PER_ITEM.PRIVATE.json';core.write(private,per_item);private.chmod(0o600)
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',spec)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E126',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=spec['inventory_sha256'],output_sha256=spec['output_sha256'],per_item_private_sha256=core.sha(private),new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=committed();print(run(core.read(args.spec),commit))

if __name__=='__main__':main()
