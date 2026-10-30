"""CPU-only, precommitted E100 blind export and once-only analysis.

No model imports. Real readouts are read only behind the committed-source gate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from rules import ROWS, REPORTED, MISSED, CONDITIONS, production
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CORE=ROOT/'projects/g_agreement/understand/wmech2/core.py'
spec=importlib.util.spec_from_file_location('e100_custody',CORE)
core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e100/ANALYSIS_ONCE.json')

def committed():
    pins=read(HERE/'DEPENDENCIES.json')
    for name,digest in pins.items():
        require(sha(ROOT/name)==digest,'changed custody dependency: '+name)
    files=list(HERE.glob('*.py'))+list(HERE.glob('*.json'))+list(HERE.glob('*.md'))
    for p in files:
        rel=str(p.relative_to(ROOT))
        data=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)
        require(hashlib.sha256(data).hexdigest()==sha(p),'uncommitted analysis source: '+rel)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def config(path):
    s=read(path)
    require(s['authority']=='69f8c08e4' and s['stage']=='ab','withdrawal authority/stage')
    require(set(s['shards'])=={'reported','missed'},'both full shards required')
    return s

def inputs(s):
    """Read only after committed() in both production entry points."""
    ts=Path(s['targets_seal']); targetseal=core.verify(ts,s['targets_sha256'])
    require(targetseal['experiment']=='E100' and targetseal['labels_cpu_only'] is True,'CPU target provenance')
    require(targetseal['mapping']=='donor_family_registered_values','explicit donor-family mapping required')
    targets=core.unique(read(ts.parent/'TARGETS.json'))
    require(len(targets)==672,'all 8 × 84 sealed CPU targets required')
    for row in ROWS:
        require(sum(t['row']==row for t in targets.values())==84,'84 targets per row')
    for t in targets.values():
        require(t['target'] in ('A','B') and set(t['values'])=={'A','B'},'registered target mapping')
        require(t.get('donor_id') in targets and targets[t['donor_id']]['row']==t['row'],'same-row donor')
        require(t.get('source_item_id') and t.get('donor_source_item_id'),'original source join required')
    rows=[]; seals={}
    for shard,group in [('reported',REPORTED),('missed',MISSED)]:
        entry=s['shards'][shard]; path=Path(entry['seal'])
        seal=core.verify(path,entry['sha256']); seals[shard]=entry['sha256']
        require(seal.get('experiment')=='E100' and seal.get('stage')=='ab' and seal.get('status')=='COMPLETE','complete E100 a/b seal')
        require(seal.get('shard')==shard and seal.get('labels_cpu_only') is True,'shard/CPU receipt')
        require(seal['source_seal_sha256']==s['runner_source_sha256'],'runner source provenance')
        require(seal['input_seal_sha256']==entry['input_sha256'],'sealed vector input provenance')
        require(bool(seal.get('gpu_type')) and bool(seal.get('actual_gpu_name')),'GPU type per shard')
        grid=read(path.parent/'JOB_GRID.json'); completed=read(path.parent/'COMPLETED.json')
        require(sum(len(j['indices']) for j in grid)==len(group)*84*10 and sorted(completed)==list(range(len(grid))),'complete registered jobs')
        require(read(path.parent/'NOT_RUN.json')==[], 'no skipped active jobs')
        for index in range(len(grid)):
            p=path.parent/'jobs'/('%06d.json'%index)
            require(str(p.relative_to(path.parent)) in seal['files'],'job missing from seal')
            output=read(p)
            records=output if isinstance(output,list) else [output]
            require(len(records)==len(grid[index]['indices']),'one greedy readout per scheduled item')
            for x in records:
                item=x['item_id']; require(item in targets,'unknown opaque item')
                t=targets[item]
                require(all(x[k]==grid[index][k] for k in ('row','reader','condition')),'scheduled cell metadata')
                require(x['row']==t['row'] and x['row'] in group,'row/shard mismatch')
                require(x['reader'] in ('oracle','nla') and x['condition'] in CONDITIONS,'unregistered cell')
                require(x['id']==item+':'+x['reader']+':'+x['condition'],'output identity')
                require(x['repeat']==0 and x['basis_block']==44 and x['read_block']==(44 if x['reader']=='oracle' else 42),'readout/basis contract')
                ratio=x['norm_ratio']; require(isinstance(ratio,(int,float)) and 0<=ratio<float('inf'),'finite norm ratio')
                require(x['norm_over_1_5']==(ratio>1.5) and x['gpu_type']==seal['gpu_type'],'norm/hardware receipt')
                require(isinstance(x['text'],str),'text field')
                rows.append(dict(x,property=t['property'],values=t['values'],target=t['target']))
    byid=core.unique(rows)
    expected={item+':'+reader+':'+c for item in targets for reader in ('oracle','nla') for c in CONDITIONS}
    require(set(byid)==expected,'exact 6720-cell grid')
    digest=hashlib.sha256(json.dumps(seals,sort_keys=True).encode()).hexdigest()
    return rows,digest

def figure(result,e79,output):
    """Plot saved E79 estimates only: no E79 scoring, resampling or rule rerun."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(8,1,figsize=(16,24),layout='constrained')
    for ax,row in zip(axes,ROWS):
        cells=[('E100 Oracle '+c,result['rows'][row]['oracle'][c]) for c in CONDITIONS]
        cells += [('E100 NLA '+c,result['rows'][row]['nla'][c]) for c in CONDITIONS]
        if row in MISSED:
            cells += [('E79 sealed '+c,v) for c,v in e79['states'][row]['rates'].items()]
        for i,(name,value) in enumerate(cells):
            point=value['estimate']; ci=value['CI95']
            if point is not None:
                ax.plot(i,point,'o',color='C1' if name.startswith('E79') else 'C0')
                if ci is not None: ax.vlines(i,*ci,color='C1' if name.startswith('E79') else 'C0')
        ax.set_xticks(range(len(cells)),[x[0] for x in cells],rotation=60,ha='right',fontsize=7)
        ax.set_ylim(-1.05,1.05); ax.axhline(0,color='gray',lw=.5); ax.set_ylabel('S_target'); ax.set_title(row)
    fig.suptitle('E79 Arm A: R-C1 NOT MET (0/3). E100 active a/b; original c/d WITHDRAWN.\nHistorical E79 doses, including α=4 descriptive, are copied from the sealed analysis.')
    fig.savefig(output); plt.close(fig)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['export','analyze']); ap.add_argument('--spec',required=True)
    args=ap.parse_args(); commit=committed(); s=config(args.spec)
    rows,digest=inputs(s)
    if args.action=='export':
        core.export(rows,s['blind'],s['private'],digest,commit); return
    binding=dict(s,output_sha256=digest)
    scored,judgment_hash=core.load_codes(binding)
    require({x['id'] for x in scored}=={x['id'] for x in rows},'scored identity grid')
    original={x['id']:x for x in rows}
    for x in scored:
        require(all(x[k]==original[x['id']][k] for k in ('item_id','row','reader','condition','text','target','values','norm_ratio','gpu_type')),'blind private join differs from sealed outputs')
    ep=Path(s['e79_seal']); require(s['e79_sha256']=='eb8367a52f0a8d5577aed2c48ed74dd29260e3172e6fe66dd12815d48bc6e2d9','E79 seal from commit23ed827a')
    require(sha(ep)==s['e79_sha256'],'historical E79 seal integrity')
    historical=read(ep); require(sha(ep.parent/'RESULTS.json')==historical['files']['RESULTS.json'],'sealed E79 estimates integrity')
    e79=read(ep.parent/'RESULTS.json')
    # Import plotting dependency before consuming once-only claim.
    import matplotlib
    binding['guard']=str(GUARD)
    out=core.claim(binding,commit)
    cells={}; sensitivity={}
    for x in scored:
        key=(x['row'],x['reader'],x['condition'])
        cells.setdefault(key,{})[x['item_id']]=x['score']
        sensitivity.setdefault(key,{})[x['item_id']]=None if x['redacted'] else x['score']
    result=production(cells); write(out/'RESULTS.json',result)
    write(out/'REDACTION_SENSITIVITY.json',production(sensitivity))
    write(out/'MANIPULATION.json',[{k:x[k] for k in ('id','norm_ratio','norm_over_1_5','gpu_type')} for x in rows])
    figure(result,e79,out/'FIGURE.png')
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E100',status='COMPLETE_ONCE',stage='ab',code_commit=commit,
              output_seal_sha256=digest,judgment_sha256=judgment_hash,targets_sha256=s['targets_sha256'],e79_sha256=s['e79_sha256'],authority='69f8c08e4')
if __name__=='__main__': main()
