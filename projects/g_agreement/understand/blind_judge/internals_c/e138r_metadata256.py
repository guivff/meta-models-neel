"""Metadata-only correction-contract companion; original judgments remain byte exact."""
from pathlib import Path
from .transport import ROOT,HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
INPUT='a9b55f3b72f257cb4b86aec5441f3be18f5cc57b51a92fe1ee717ab71c467f39'

def companion(source,dest):
    source=Path(source);dest=Path(dest);before=sha(source);s=verify(source,before)
    require(source.parent==dest.parent and source!=dest,'new sibling seal, no original rewrite')
    require(s['experiment']=='E138R' and s['status']=='COMPLETE' and s['input_sha256']==INPUT,'actual corrected terminal and reviewed whole-value input')
    rows=read(source.parent/'JUDGMENTS.json');require(len(rows)==168 and len({r['id']for r in rows})==168 and all(r['kind']=='E138R'for r in rows),'whole corrected168 emitted rows')
    require(s.get('input_seal_sha256',INPUT)==INPUT,'no conflicting metadata alias')
    out=dict(s,input_seal_sha256=INPUT,original_judgment_seal_sha256=before,metadata_only_compatibility=True)
    if dest.exists():require(read(dest)==out,'same immutable companion')
    else:write(dest,out)
    verify(dest,sha(dest));require(sha(source)==before and read(dest)['files']==s['files'],'all original bytes and member hashes preserved')
    return dest

def build():
    for p,h in read(HERE/'E138R_METADATA256_SOURCE.json')['files'].items():require(sha(ROOT/p)==h,'frozen metadata-only helper')
    d=CACHE/'E138R/whole_value_judging254b';jp=d/'outputs/JUDGMENT_SEAL.json';cp=companion(jp,jp.parent/'JUDGMENT_REPORT_COMPAT256.json');closed=CACHE/'E138R/complete254';verify(closed/'JUDGMENT_SEAL.json',sha(closed/'JUDGMENT_SEAL.json'))
    refs=read(closed/'READOUT_CODE_BINDINGS.PRIVATE.json');new={}
    for k,v in refs.items():
        r=v['code_source'];require(r['seal']==str(jp) and r['sha256']==sha(jp),'exact original code pointer source')
        new[k]=dict(v,code_source=dict(r,seal=str(cp),sha256=sha(cp)))
    out=CACHE/'E138R/report_compat256';out.mkdir(exist_ok=True);p=out/'READOUT_CODE_BINDINGS.PRIVATE.json'
    if p.exists():require(read(p)==new,'same literal binding source projection')
    else:write(p,new);p.chmod(0o600)
    h=out/'HANDOFF_SEAL.json';body=dict(experiment='E138R',status='COMPLETE_METADATA_COMPANION',correction_authority='250_deviation2_37d27a217',corrected_input_sha256=INPUT,corrected_judgments=dict(seal=str(cp),sha256=sha(cp)),original_judgments=dict(seal=str(jp),sha256=sha(jp)),original_bank=dict(seal=str(closed/'JUDGMENT_SEAL.json'),sha256=sha(closed/'JUDGMENT_SEAL.json')),judgments_changed=False,analysis_run=False,files={p.name:sha(p)})
    if h.exists():require(read(h)==body,'same source-only handoff')
    else:write(h,body)
    return h
