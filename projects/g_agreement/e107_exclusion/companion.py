"""Authorized post-hoc strict-evidence companion; never invokes primary entrypoint."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import subprocess
from pathlib import Path
from projects.g_agreement.e107_analysis import adapter
from projects.g_agreement.e107_analysis.rules import analyze
from projects.g_agreement.understand.wmech2 import core
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE=adapter.GUARD.parent
PRIMARY_SHA='f2da69a4f0e7acb560552cb9bee8c56ea8012a926a9508303113a2d3ccdd93b8'
V5_SHA='bfd0809d3a5444ed8471f8dadc6e4ad6e1e595990f60293ee7556cdd392a1e71'

def strict_failures(meta, measurements):
    failures=[]
    for system, targets in measurements.items():
        for target, data in targets.items():
            c=data['code']
            if c is None or c['category']=='UNPARSEABLE':continue
            texts=data['text']
            texts=[p['readout'] for p in texts] if isinstance(texts,list) else [texts]
            if not any(c['evidence'] in text for text in texts):
                failures.append(dict(id=meta['id'],bank=meta['bank'],system=system,target=target))
    return failures

def mask(item, failures):
    out=deepcopy(item)
    for f in failures:
        z=out['systems'][f['system']]
        z[f['target']]=None
        z['named']=None
        if item['bank']=='E82':
            z.update({k:None for k in z})
    return out

def table(items):
    """Belief and truth indicators may overlap; other/no-value/missing are disjoint."""
    rows=[]
    for row,cohort in sorted({(x['row'],x['cohort']) for x in items if x['bank']=='E82'}):
        xs=[x for x in items if x['bank']=='E82' and x['row']==row and x['cohort']==cohort]
        for reader in ('oracle','nla','outside'):
            counts=Counter(planned=len(xs),states_belief=0,states_truth=0,states_other=0,no_value=0,missing=0,both_belief_and_truth=0)
            truth_known=cohort!='no_canonical_truth'
            for x in xs:
                z=x['systems'].get(reader)
                if z is None or z['named'] is None:counts['missing']+=1;continue
                b=z.get('belief')==1;t=z.get('truth')==1
                counts['states_belief']+=b;counts['states_truth']+=t
                counts['both_belief_and_truth']+=b and t
                counts['states_other']+=z['named'] and not b and not t
                counts['no_value']+=not z['named']
            observed=counts['planned']-counts['missing']
            if not truth_known:
                counts['states_truth']=None;counts['both_belief_and_truth']=None
            rows.append(dict(row=row,cohort=cohort,reader=reader,**counts,truth_available=truth_known,
                unconditional_belief_rate_observed=counts['states_belief']/observed if observed else None,
                unconditional_truth_rate_observed=counts['states_truth']/observed if observed and truth_known else None))
    return rows

def committed():
    receipt=core.read(HERE/'SOURCE_RECEIPT.json')
    for rel,h in receipt['files'].items():
        core.require(core.sha(ROOT/rel)==h,'source receipt mismatch')
        blob=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)
        core.require(hashlib.sha256(blob).hexdigest()==h,'uncommitted source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=core.read(a.spec)
    core.require(s['output_sha256']==V5_SHA,'binding v5 only')
    primary=BASE/'analysis_once'
    core.verify(primary/'ANALYSIS_SEAL.json',PRIMARY_SHA)
    primary_guard_hash=core.sha(adapter.GUARD)
    saved=core.read(primary/'RESULTS.json')
    failures=[];original=adapter.evaluate
    def capture(meta,measurements):
        item=original(meta,measurements)
        fs=strict_failures(meta,measurements);failures.extend(fs)
        return mask(item,fs)
    adapter.evaluate=capture
    try:items,inv,_=adapter.inputs(s)
    finally:adapter.evaluate=original
    core.require(len(failures)==31 and Counter(x['bank'] for x in failures)=={'E81':29,'E86':2},'exact strict v5 exclusions: 29 E81 and 2 E86')
    core.require(len({(x['id'],x['system'],x['target']) for x in failures})==31,'unique excluded cells')
    out=core.claim(dict(analysis=str(BASE/'strict_exclusion_companion_once'),guard=str(BASE/'STRICT_EXCLUSION_COMPANION_ONCE.json'),output_sha256=V5_SHA),commit)
    core.write(out/'EXCLUSIONS.PRIVATE.json',failures)
    result=analyze(items,inv['e81_rows'])
    result['caveat']='Shared model family between describer and judge is a confound of unknown direction.'
    result['authority']='§236 clarification 3 item 2; §218 reporting note 1'
    result['role']='descriptive post-hoc strict word-for-word exclusion companion; primary unchanged'
    result['excluded_cells']=31;result['excluded_by_bank']={'E81':29,'E86':2}
    result['primary_seal_sha256']=PRIMARY_SHA
    result['primary_R_OL1_copied']=saved['E82']['belief_wrong']['oracle']['pooled']['difference']
    result['companion_R_OL1']=result['E82']['belief_wrong']['oracle']['pooled']['difference']
    result['table']=table(items)
    result['table_scope']='E82, by row/cohort/reader; belief/truth overlap counted explicitly as both; no-canonical-truth truth rate unavailable. Other means named neither available target; not a fabricated truth label.'
    core.write(out/'RESULTS.json',result)
    core.write(out/'BINDING.PRIVATE.json',s)
    core.require(core.sha(adapter.GUARD)==primary_guard_hash,'primary guard unchanged')
    core.verify(primary/'ANALYSIS_SEAL.json',PRIMARY_SHA)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E107 strict exclusion companion',status='COMPLETE_ONCE',code_commit=commit,primary_seal_sha256=PRIMARY_SHA,binding_sha256=V5_SHA)
    print(core.sha(out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':main()
