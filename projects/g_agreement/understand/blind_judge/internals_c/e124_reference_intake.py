"""Literal Track-Q reference/readout intake; source cohort only, no new measures."""
import argparse
from pathlib import Path
from .transport import ROOT,HERE
from .runner import CACHE
from .e124_channel import verify_unit_refs
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def project(readouts,references,resolve):
    by={x['id']:x for x in readouts}
    require(len(by)==len(readouts)==len(references) and len({r['id'] for r in references})==len(references) and set(by)=={r['id'] for r in references},'exact full original custody census by ID')
    out=[];refs=[];excluded=[]
    for r in references:
        require(r['condition'] in ('E104_U_44_steered','E104_U_44_random','E109_52_steered','E82_belief_wrong'),'registered source set')
        if r['condition']=='E82_belief_wrong':
            require(r['cohort'] in ('belief_wrong','no_canonical_truth'),'literal owner cohort required')
            if r['cohort']=='no_canonical_truth':excluded.append(r['id']);continue
        else:require(r.get('cohort') is None,'original252 has no E82 cohort')
        reference=resolve(r['reference_text']);require(type(reference) is str and reference.strip(),'literal registered behaviour reference')
        x=by[r['id']];require(type(x['readout']) is str,'original native readout including malformed/empty')
        out.append(dict(id=r['id'],model_reference=reference,readout=x['readout']))
        refs.append(dict(id=r['id'],model_reference_ref=r['reference_text']))
    return sorted(out,key=lambda x:x['id']),sorted(refs,key=lambda x:x['id']),sorted(excluded)


def prepare():
    for n,h in read(HERE/'E124_REFERENCE_INTAKE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published tested intake/owner report source')
    rp=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e124/model_reference_v3/REFERENCE_SEAL.json')
    rs=verify(rp,'61d87c57337064e297ccb6b183f9b6e6a647ac60c0940e5df18540fb4d6111c0')
    require(rs['authority']=='2045d4a96' and rs['owner']=='Track Q' and rs['status']=='FROZEN_BEFORE_FIRST_CALL' and rs['original_records_verified'] is True,'actual owner provenance not C-invented')
    roster=CACHE/'E124/readout_roster/ROSTER_SEAL.json';verify(roster,'5877ab154a58e818d0596c45168f8531a2bb625d094b41b68ecd83405d55aacf')
    sources=rs['source_seals_for_spec'];ss=[verify(r['seal'],r['sha256']) for r in sources];cache={}
    def resolve(ref):
        i=ref['seal_index'];require(type(i) is int and 0<=i<len(ss) and ref['member'] in ss[i]['files'],'original reference member')
        path=Path(sources[i]['seal']).parent/ref['member']
        if str(path) not in cache:cache[str(path)]=read(path)
        v=cache[str(path)]
        for k in ref['keys']:v=v[k]
        return v
    references=read(rp.parent/'MODEL_REFERENCES.PRIVATE.json');readouts=read(roster.parent/'READOUTS.json')
    from projects.g_agreement.e124_analysis.adapter import model_reference,registered_reference
    for r in references:
        if registered_reference(r):model_reference(r,dict(id=r['id'],condition=r['condition']),resolve)
    units,refs,excluded=project(readouts,references,resolve)
    require(len(readouts)==7042 and len(units)==6424 and len(excluded)==618,'owner full7042 custody / registered6424 scope /618 no-truth excluded without judging')
    index={x['id']:i for i,x in enumerate(readouts)};roster_index=len(sources)
    sources=sources+[dict(seal=str(roster),sha256=sha(roster)),dict(seal=str(rp),sha256=sha(rp))]
    for r in refs:r['readout_ref']=dict(seal_index=roster_index,member='READOUTS.json',keys=[index[r['id']],'readout'])
    custody=dict(registered_behavior_references_verified=True,complete_eligible_grid=True,labels_cpu_only=True,units=refs,cohort_authority='TrackQ61d87c57/Wmech2 source26tests; no_canonical_truth census retained/excluded per owner',no_new_behavior_measure=True)
    verify_unit_refs(units,custody,sources)
    d=CACHE/'E124/registered_reference_units';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'UNIT_SEAL.json').exists():
        verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable original reference intake');return d
    write(d/'UNITS.json',units);write(d/'CUSTODY.PRIVATE.json',custody);write(d/'EXCLUDED_CENSUS_IDS.PRIVATE.json',excluded)
    write(d/'UNIT_SEAL.json',dict(experiment='E124',phase='model_reference_consistency',frozen_before_judging=True,unit_definition_frozen=True,n=6424,full_custody_census=7042,source_seals=sources,files={n:sha(d/n) for n in ('UNITS.json','CUSTODY.PRIVATE.json','EXCLUDED_CENSUS_IDS.PRIVATE.json')}))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E124 literal registered units '+sha(prepare()/'UNIT_SEAL.json'))
