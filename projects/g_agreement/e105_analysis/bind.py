"""CPU custody binder for original runner105 MEASUREMENT_INDEX; never reads scores."""
import argparse
from pathlib import Path
from . import adapter as a
from .rules import ROWS

def build(plan,dest):
    require=a.require
    require(plan['status']=='E105_RESTART_RESOLVED' and set(plan['rows'])==set(ROWS),'final six-row dispositions')
    inv=Path(plan['inventory_seal']);a.core.verify(inv,plan['inventory_sha256'])
    meta=a.read(inv.parent/'INVENTORY.json');expected={r:{x['id'] for x in meta if x['row']==r} for r in ROWS}
    require(all(len(ids)==84 for ids in expected.values()) and len(meta)==504,'original504 inventory')
    sources=[];seals=[];states={};measurements=[]
    def source(x,row,status):
        p=Path(x['seal']);s=a.core.verify(p,x['sha256'])
        require(s['experiment']=='E105' and s['status']==status and s['input_sha256']==plan['input_hashes'][row],'exact source status/input')
        require(s.get('source_sha256') and s.get('gpu_type'),'executed source/GPU custody')
        i=len(sources);sources.append(dict(seal=str(p.resolve()),sha256=x['sha256']));seals.append(s)
        return i,p,s
    for row in ROWS:
        d=plan['rows'][row]
        if d['status']=='COMPLETE':
            i,p,s=source(d,row,'COMPLETE');require('MEASUREMENT_INDEX.json' in s['files'],'original runner index')
            index=a.core.unique(a.read(p.parent/'MEASUREMENT_INDEX.json'))
            require(set(index)==expected[row],'all84 source IDs, no replacement or omission')
            for ident,x in index.items():
                require(set(x['conditions'])=={'T','S','0'},'three conditions')
                refs={}
                for c,ref in x['conditions'].items():
                    require(set(ref)=={'member','keys'} and ref['member'] in s['files'] and isinstance(ref['keys'],list),'unaltered runner source pointer')
                    refs[c]=dict(ref,seal_index=i)
                measurements.append(dict(id=ident,conditions=refs))
            states[row]=dict(status='COMPLETE',source_seal_index=i)
        else:
            require(row in ('indent_level','fact_recall') and d['status']=='NOT RUN (operational)' and len(d['attempts'])==2,'amendment2 failure disposition')
            indices=[source(x,row,'NO_FIT')[0] for x in d['attempts']]
            require(len({sources[i]['sha256'] for i in indices})==2,'distinct initial/restart failures')
            states[row]=dict(status=d['status'],attempt_seal_indices=indices)
    resolution=dict(status=plan['status'],authority='§214 amendment2 / 157fb545',rows=states)
    a.resolved_rows(dict(restart_resolution=resolution),seals)
    require(not dest.exists(),'never overwrite binding');dest.mkdir(parents=True)
    a.write(dest/'MEASUREMENTS.json',sorted(measurements,key=lambda x:x['id']))
    a.core.seal(dest,'OUTPUT_SEAL.json',experiment='E105',status='COMPLETE',inventory_sha256=plan['inventory_sha256'],source_seals=sources,restart_resolution=resolution)
    spec={k:plan[k] for k in ('inventory_seal','inventory_sha256','inventory_commit','e100_targets','analysis')}
    spec.update(output_seal=str((dest/'OUTPUT_SEAL.json').resolve()),output_sha256=a.sha(dest/'OUTPUT_SEAL.json'))
    a.write(dest/'SPEC.json',spec)
    return dict(experiment='E105',status='BINDING_VERIFIED_NO_ANALYSIS',completed_rows=[r for r in ROWS if states[r]['status']=='COMPLETE'],not_run=[r for r in ROWS if states[r]['status']!='COMPLETE'],items=len(measurements),conditions=3*len(measurements),output_sha256=spec['output_sha256'],source_seals=sources,raw_scores_parsed=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    commit=a.committed();receipt=build(a.read(args.plan),args.out);receipt['binder_commit']=commit
    a.write(args.out/'NORMALIZER_RECEIPT.json',receipt)
if __name__=='__main__':main()
