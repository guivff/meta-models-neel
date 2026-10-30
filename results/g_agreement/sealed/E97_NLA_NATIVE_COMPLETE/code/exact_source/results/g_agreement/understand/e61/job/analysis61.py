"""§177 once-only D3/D4 analysis and verbatim selected readouts."""
import argparse,json,sys
from pathlib import Path
from runtime61 import HERE,position_jobs,require,verify_dependencies
from contract56 import read,dump,verify,sha,seal
sys.path.insert(0,str(HERE.parents[1]/'e57/job'))
from counts57 import named_terms
from analysis_io import claim_once
from measures61 import paired_ratios,timeline_bands
from displays61 import display_html


def load_verified(spec):
    inp=Path(spec['inputs']);verify(inp,'INPUT_SEAL.json',spec['input_seal_sha256']);items=read(inp/'items.json');jobs=position_jobs(items);root=Path(spec['output']);receipt=read(spec['receipt'])
    require(receipt['verified'] is True and receipt['experiment']=='E61','integrator receipt')
    s=verify(root,'OUTPUT_SEAL.json',receipt['output_seal_sha256']);a=read(root/'ASSIGNMENT.json')
    require(s['pod_id']==receipt['pod_id']==a['pod_id'] and s['input_seal_sha256']==spec['input_seal_sha256'] and s['source_seal_sha256']==spec['source_seal_sha256'],'custody binding')
    from admission import validate_allocation
    _,end=validate_allocation(a)
    require(a['pod_created_epoch']<=read(root/'TIMING.json')['completed_epoch']<end,'E61 cumulative custody cap')
    require(read(root/'ADMISSION.json')['status']=='ADMIT','self admission')
    go=read(root/'GO_RECEIPT.json')
    require(go['reader_launch_authorized'] is True and go['pod_id']==a['pod_id'] and go['capture_seals']['E61']==sha(root/'capture/CAPTURE_SEAL.json'),'capture-bound GO')
    reuse=read(root/'PARITY_REUSE.json');previous=root.parent/'e56';verify(previous,'OUTPUT_SEAL.json',reuse['e56_output_seal_sha256'])
    require(reuse['pod_id']==a['pod_id'] and reuse['parity_result_sha256']==sha(previous/'parity/PARITY_RESULT.json') and read(previous/'parity/PARITY_RESULT.json')['status']=='PASS','same-pod parity')
    verify(root/'capture','CAPTURE_SEAL.json');require(read(root/'capture/POSITION_ORDER.json')==jobs,'every frozen position')
    records=[]
    for reader in ('oracle','nla'):
        rows=[json.loads(t) for t in (root/(reader+'.native.jsonl')).read_text().splitlines()];expected={(x['id'],i) for x in jobs for i in range(1)}
        require(len(rows)==len(expected) and {(x['id'],x['repeat']) for x in rows}==expected,'complete native grid')
        lookup={x['id']:x for x in jobs}
        for x in rows:
            require(x['reader']==reader and x['reader_native_layer']==(44 if reader=='oracle' else 42),'reader identity')
            require(all(x[k]==lookup[x['id']][k] for k in ('item_id','pair_id','position','relative_position','arm','display')),'position identity')
        records+=rows
    probs=read(root/'BASE_PROBABILITIES.json');wanted={x['id']:x for x in items if x['display']=='D4'}
    require(len(probs)==len(wanted) and {x['item_id'] for x in probs}==set(wanted),'complete D4 probability grid')
    for x in probs:
        w=wanted[x['item_id']];require(all(x[k]==w[k] for k in ('arm','concept','answer_token_id')) and x['pair_id']==w['pair_id'] and 0<=x['probability']<=1,'probability identity')
    return items,records,probs,read(inp/'LEXICON.json'),read(inp/'SELECTION.json')


def summarize(items,records,probs,lexicon):
    lookup={x['id']:x for x in items};groups={}
    for x in records:groups.setdefault((x['reader'],x['item_id'],x['relative_position']),[]).append(x)
    probability={x['item_id']:x['probability'] for x in probs};out={}
    for reader in ('oracle','nla'):
        timeline={};common={};p=[];m=[]
        for pair in sorted({x['pair_id'] for x in items if x['display']=='D3'}):
            paired={x['arm']:x for x in items if x['display']=='D3' and x['pair_id']==pair}
            a=paired['decline'];b=paired['answer'];length=min(a['pre_answer_index']-a['instruction_end_index'],b['pre_answer_index']-b['instruction_end_index'])+1
            for pos in range(length):
                own=[];decline=[]
                for arm,item in [('decline',a),('answer',b)]:
                    xs=groups[reader,item['id'],pos];found=[named_terms(x['text'],{k:lexicon[k] for k in ('decline','answer')},'word_exact_casefold') for x in xs]
                    own.append(sum(arm in f for f in found)/1);decline.append(sum('decline' in f for f in found)/1)
                timeline.setdefault(pos,[]).append(own);common.setdefault(pos,[]).append(decline)
        for pair in sorted({x['pair_id'] for x in items if x['display']=='D4'}):
            arms={x['arm']:x for x in items if x['display']=='D4' and x['pair_id']==pair};p.append([probability[arms[a]['id']] for a in ('think','ignore','none')]);values=[]
            for arm in ('think','ignore','none'):
                item=arms[arm];xs=groups[reader,item['id'],0];concept=item['concept'];values.append(sum(bool(named_terms(x['text'],{concept:lexicon[concept]},'word_exact_casefold')) for x in xs)/1)
            m.append(values)
        out[reader]={'D3_own_plan_naming':timeline_bands(timeline),'D3_common_decline_mentions':timeline_bands(common),'D4':paired_ratios(p,m)}
    from native_nla512 import truncation_summary
    out['nla']['truncation']=truncation_summary([x for x in records if x['reader']=='nla'],row_key='display')
    return out


def main():
    verify_dependencies()
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True,type=Path);a=p.parse_args();spec=read(a.spec)
    require(sha(a.spec)==read(HERE/'ANALYSIS_COMMAND.json')['spec_sha256'],'analysis spec pin');verify(HERE,'SOURCE_SEAL.json',spec['source_seal_sha256'])
    items,records,probs,lex,selection=load_verified(spec);out=claim_once(spec['analysis_out'],'E61',sha(a.spec))
    result=summarize(items,records,probs,lex);dump(out/'RESULTS.json',result)
    chosen=[dict(x,unit_id=x['id']) for x in records if (x['display']=='D3' and x['item_id'] in selection['D3']) or (x['display']=='D4' and x['pair_id'] in selection['D4_base_items'])]
    dump(out/'SELECTED_VERBATIM.json',chosen);(out/'SELECTED_VERBATIM.html').write_text(display_html('E61 registered examples',chosen))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for reader in ('oracle','nla'):
        rows=result[reader]['D3_own_plan_naming']['positions'];positions=sorted(rows);fig,ax=plt.subplots()
        for index,name in enumerate(('decline arm','answer arm')):
            ax.plot(positions,[rows[k]['mean'][index] for k in positions],label=name)
            ax.fill_between(positions,[rows[k]['CI95'][0][index] for k in positions],[rows[k]['CI95'][1][index] for k in positions],alpha=.2)
        ax.set(xlabel='Token offset from instruction end (inclusive)',ylabel='Own-plan naming rate',ylim=(0,1));ax.legend();fig.tight_layout();fig.savefig(out/(reader+'_timeline.png'),dpi=160);plt.close(fig)
    (out/'RESULTS.md').write_text('# E61 D3/D4\n\nPrediction: R-W holds for Oracle.\n\n'+'\n'.join(r+': R-W '+result[r]['D4']['R_W']+'; falsifier '+str(result[r]['D4']['falsifier']) for r in result)+'\n\nD3 is descriptive; first-crossing positions and both naming summaries are in RESULTS.json. All selected readouts are verbatim; no repeats omitted.\n')
    seal(out,'ANALYSIS_SEAL.json',{'experiment':'E61','source_seal_sha256':spec['source_seal_sha256'],'status':'COMPLETE'})
if __name__=='__main__':main()
