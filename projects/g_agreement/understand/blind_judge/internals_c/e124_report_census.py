"""Pre-call E124 report census: literal original classifications and fixed ID slots."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from projects.g_agreement.e82_analysis.analyze import mention
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def classification(cross,reference,resolve):
    require(cross['id']==reference['id'],'explicit reference/crosswalk ID')
    if cross['source_set']=='E118a':
        require(cross['condition']==reference['condition'],'original condition copy')
        return dict(id=cross['id'],condition=cross['condition'])
    require(cross['source_set']=='E118b' and reference['condition']=='E82_belief_wrong' and reference['cohort'] in ('belief_wrong','no_canonical_truth'),'source-bound E82 cohort')
    b=cross['original_label_refs']['belief'];code=resolve(b)
    return dict(id=cross['id'],condition=reference['condition'],reader='oracle',row=cross['family'],item_id=cross['item_id'],position=cross['position'],belief_stating=mention(code,b['target_letter']),cohort=reference['cohort'])


def prepare():
    source=HERE/'E124_REPORT_CENSUS_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published report census source/dependencies')
    rp=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e124/model_reference_v3/REFERENCE_SEAL.json');rs=verify(rp,'61d87c57337064e297ccb6b183f9b6e6a647ac60c0940e5df18540fb4d6111c0')
    roster=CACHE/'E124/readout_roster/ROSTER_SEAL.json';verify(roster,'5877ab154a58e818d0596c45168f8531a2bb625d094b41b68ecd83405d55aacf')
    cross=read(roster.parent/'CROSSWALK.PRIVATE.json');readouts=read(roster.parent/'READOUTS.json');refs=read(rp.parent/'MODEL_REFERENCES.PRIVATE.json');by={x['id']:x for x in refs}
    require(len(by)==len(refs)==len(cross)==7042 and set(by)=={x['id'] for x in cross},'full sealed7042 exact census')
    verified={};objects={}
    def resolve(ref):
        sp=Path(ref['seal']);key=str(sp)
        if key not in verified:verified[key]=verify(sp,ref['sha256'])
        require(ref['member'] in verified[key]['files'],'original classification member')
        p=sp.parent/ref['member']
        if str(p) not in objects:objects[str(p)]=read(p)
        v=objects[str(p)]
        for k in ref['keys']:v=v[k]
        return v
    labels={x['id']:classification(x,by[x['id']],resolve) for x in cross}
    d=CACHE/'E124/report_census';d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
    if(d/'INPUT_SEAL.json').exists():
        verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));require(read(d/'CLASSIFICATIONS.PRIVATE.json')==labels,'immutable original source classification');return d
    write(d/'CLASSIFICATIONS.PRIVATE.json',labels)
    write(d/'CLASSIFICATION_PROVENANCE.PRIVATE.json',dict(roster_seal=str(roster),roster_sha256=sha(roster),reference_seal=str(rp),reference_sha256=sha(rp),normalization='unchanged original E82 mention(code,target_letter); null remains unknown, no new judgments',source_group_label_pointers={x['id']:x.get('original_label_refs') for x in cross}))
    write(d/'CLASSIFICATION_SEAL.json',dict(experiment='E124',status='COPY_ONLY_CPU_BEFORE_E124_CALL',files={n:sha(d/n) for n in ('CLASSIFICATIONS.PRIVATE.json','CLASSIFICATION_PROVENANCE.PRIVATE.json')}))
    indices={x['id']:i for i,x in enumerate(readouts)};rows=[]
    for x in sorted(cross,key=lambda x:x['id']):
        ident=x['id'];r=by[ident]
        row=dict(id=ident,classification=dict(seal_index=5,member='CLASSIFICATIONS.PRIVATE.json',keys=[ident]))
        if r.get('cohort')=='no_canonical_truth':row.update(disposition='EXCLUDED_BY_REGISTERED_SOURCE_COHORT_NO_JUDGMENT')
        else:
            row.update(readout=dict(seal_index=3,member='READOUTS.json',keys=[indices[ident],'readout']),model_reference=r['reference_text'],context_terminal=dict(seal_index=6 if x['source_set']=='E118a' else 7,member='TERMINALS.PRIVATE.json',keys=[ident]),model_terminal=dict(seal_index=8,member='TERMINALS.PRIVATE.json',keys=[ident]))
        rows.append(row)
    write(d/'CENSUS.PRIVATE.json',rows)
    fixed=rs['source_seals_for_spec']+[dict(seal=str(roster),sha256=sha(roster)),dict(seal=str(rp),sha256=sha(rp)),dict(seal=str(d/'CLASSIFICATION_SEAL.json'),sha256=sha(d/'CLASSIFICATION_SEAL.json'))]
    write(d/'SOURCE_SLOT_CONTRACT.PRIVATE.json',dict(fixed_source_slots=fixed,future_source_slots={'6':'original E118a status/result literal projection keyed to C124 IDs via sealed crosswalk','7':'original E118b status/result literal projection after COMPLETE, same crosswalk','8':'new E124 status/result literal projection after COMPLETE, exact dispatch ID'},no_fake_terminal_seals=True,report_requires_all_actual_terminal_seals_before_once_guard=True))
    write(d/'INPUT_SEAL.json',dict(experiment='E124',status='FROZEN_BEFORE_FIRST_CALL',system_sha256=sha(ROOT/'projects/g_agreement/e124_analysis/SYSTEM.txt'),reference_sha256=sha(rp),full_custody_census=7042,registered_judgments=6424,source_builder_sha256=sha(source),files={n:sha(d/n) for n in ('CENSUS.PRIVATE.json','SOURCE_SLOT_CONTRACT.PRIVATE.json','CLASSIFICATIONS.PRIVATE.json','CLASSIFICATION_PROVENANCE.PRIVATE.json','CLASSIFICATION_SEAL.json')}))
    return d


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E124 frozen report census '+sha(prepare()/'INPUT_SEAL.json'))
