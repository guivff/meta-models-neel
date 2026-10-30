"""Precommitted E105 logits-only custody and once-only analysis. No judge/model calls."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import ROWS,analyze,validate_completed
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e105/ANALYSIS_ONCE.json')
E100_TARGET_SHA='f1c97d6800972346241385ee2e18e02ffc12c01767827d6e44d26da7cace2e35'

def committed():
    for p,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/p)==h,'pinned dependency changed')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(b).hexdigest()==sha(p),'uncommitted adapter '+p.name)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def normalize(records,targets,completed_rows=ROWS):
    completed=validate_completed(completed_rows)
    core.unique(records);seen=set();out=[]
    for x in records:
        require(x['row'] in ROWS and x['split']=='test','registered row/test split')
        require(x['item_id'] in targets,'E100 carrier identity')
        t=targets[x['item_id']]
        require(t['row']==x['row'] and x['T_donor_id']==t['donor_id'],'original E100 T pairing')
        require(x['S_donor_id'] in targets and targets[x['S_donor_id']]['row']==x['row'] and x['S_donor_id']!=x['item_id'],'different same-row S donor')
        require(x['T_label']==(1 if t['target']=='A' else 0),'E100 donor label binding')
        require(x['S_label']==(0 if targets[x['S_donor_id']]['target']=='A' else 1),'E100 same-value donor label binding')
        require(x['source_label'] in (0,1) and x['T_label']==1-x['source_label'] and x['S_label']==x['source_label'],'opposite T, same-value S')
        require(x['candidate_A_label'] in (0,1) and x['frozen_scorer_sha256'] and x['candidate_ids_sha256'],'frozen continuation orientation')
        sign=1 if x['T_label']==x['candidate_A_label'] else -1
        require(set(x['pair_logprobs'])=={'T','S','0'},'all three conditions, no reader data')
        count=x['candidate_pair_count'];require(type(count) is int and count>0,'original frozen pair count')
        c={}
        for condition,pairs in x['pair_logprobs'].items():
            require(len(pairs)==count and all(len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in pairs),'full finite continuation pairs')
            c[condition]=sign*sum(a-b for a,b in pairs)/count
        key=(x['row'],x['item_id']);require(key not in seen,'duplicate source item');seen.add(key)
        out.append(dict(id=x['id'],item_id=x['item_id'],row=x['row'],contrasts=c))
    require({x['row'] for x in out}==completed and len(out)==84*len(completed) and all(sum(x['row']==r for x in out)==84 for r in completed),'all completed rows84, no within-row shrinking')
    return out

def resolved_rows(seal,sources):
    resolution=seal['restart_resolution']
    require(resolution['status']=='E105_RESTART_RESOLVED' and resolution['authority']=='§214 amendment2 / 157fb545','registered final restart resolution')
    rows=resolution['rows'];require(set(rows)==set(ROWS),'six dispositions retained')
    completed=[]
    for row,d in rows.items():
        if d['status']=='COMPLETE':
            i=d['source_seal_index'];require(type(i) is int and 0<=i<len(sources) and sources[i]['status']=='COMPLETE','complete original row source')
            completed.append(row)
        else:
            require(row in ('indent_level','fact_recall') and d['status']=='NOT RUN (operational)','only registered restart failures omitted')
            ix=d['attempt_seal_indices'];require(len(ix)==2 and len(set(ix))==2,'original plus single restart failure receipts')
            require(all(type(i) is int and 0<=i<len(sources) and sources[i]['status']=='NO_FIT' for i in ix),'sealed terminal original/restart failures, no partial scores')
    validate_completed(completed)
    return completed

def inputs(s):
    ip=Path(s['inventory_seal']);commit=s['inventory_commit']
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'full pre-output inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.resolve().relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed input inventory seal')
    inv=core.verify(ip,s['inventory_sha256']);require(inv['experiment']=='E105' and inv['same_value_seed']==20261030 and inv['block']==44 and inv['supplied_vector_mode'] is True,'registered E105 intervention')
    require(inv['behaviour_mode']=='frozen_continuation' and inv['new_text'] is False,'unchanged frozen scorer/text')
    tp=Path(s['e100_targets']);core.verify(tp,E100_TARGET_SHA);targets=core.unique(read(tp.parent/'TARGETS.json'))
    require('INVENTORY.json' in inv['files'],'sealed input inventory')
    metadata=read(ip.parent/'INVENTORY.json');core.unique(metadata)
    require(len(metadata)==504 and all(sum(x['row']==r for x in metadata)==84 for r in ROWS),'full original504 inventory remains frozen')
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    require(seal['experiment']=='E105' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete bound acquisition')
    require('MEASUREMENTS.json' in seal['files'],'sealed raw source index')
    sources=seal['source_seals'];seals=[core.verify(x['seal'],x['sha256']) for x in sources]
    completed=resolved_rows(seal,seals)
    measurements=core.unique(read(op.parent/'MEASUREMENTS.json'));require(set(measurements)=={x['id'] for x in metadata if x['row'] in completed},'all and only completed measured rows')
    records=[]
    for m in metadata:
        if m['row'] not in completed:continue
        require('pair_logprobs' not in m,'no output in pre-output inventory')
        refs=measurements[m['id']]['conditions'];require(set(refs)=={'T','S','0'},'all original conditions')
        pairs={}
        for condition,ref in refs.items():
            ix=ref['seal_index'];require(ix==seal['restart_resolution']['rows'][m['row']]['source_seal_index'],'completed-row source, never failed attempt')
            require(ref['member'] in seals[ix]['files'],'sealed raw pair logprobs')
            value=read(Path(sources[ix]['seal']).parent/ref['member'])
            for k in ref['keys']:value=value[k]
            pairs[condition]=value
        records.append(dict(m,pair_logprobs=pairs))
    return normalize(records,targets,completed)

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec)
    rows=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(rows,{x['row'] for x in rows});write(out/'RESULTS.json',result);write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E105',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'],inventory_sha256=s['inventory_sha256'],judging=False)
if __name__=='__main__':main()
