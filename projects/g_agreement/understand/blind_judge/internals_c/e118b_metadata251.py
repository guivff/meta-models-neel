"""Metadata-only E118b frozen-report compatibility; original bytes stay immutable."""
import ast,copy
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
MESSAGES={
 'complete distinct part-b bank',
 'actual input and pre-call source binding',
 'exact unchanged judged source and privacy',
 'same lifetime cap includes prior spend and settled part-b bank'}


def corrected_metadata(original,input_sha):
    require(original['experiment']=='E118'and original['status']=='COMPLETE'and original['phase']=='part_b','only known original terminal metadata defect')
    require(original['input_sha256']==input_sha and 'input_seal_sha256'not in original,'unchanged original input; missing alias only')
    result=copy.deepcopy(original);result['phase']='belief_wrong_consistency_judging';result['input_seal_sha256']=input_sha
    return result


def frozen_metadata_preflight(spec,adapter=None):
    """Execute ONLY the unchanged owner's four terminal/cap assertions via its AST.
    No report(), summarize(), parsing of judgment codes, or guard operation.
    """
    adapter=Path(adapter or ROOT/'projects/g_agreement/e118b_analysis/adapter.py');closure=read(spec['report_source_seal'])
    require(sha(adapter)==closure['files']['projects/g_agreement/e118b_analysis/adapter.py'],'exact frozen owner adapter')
    tree=ast.parse(adapter.read_text());report=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='report');nodes=[];seen=set()
    for node in report.body:
        if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in('judge','cap','cost'):nodes.append(node)
        elif isinstance(node,ast.Expr)and isinstance(node.value,ast.Call)and isinstance(node.value.func,ast.Name)and node.value.func.id=='require':
            args=node.value.args
            if len(args)==2 and isinstance(args[1],ast.Constant)and args[1].value in MESSAGES:nodes.append(node);seen.add(args[1].value)
    require(seen==MESSAGES and len(nodes)==7,'exact isolated owner terminal/cap assertion shape')
    code=compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(nodes),type_ignores=[])),str(adapter)+':terminal_metadata_only','exec')
    exec(code,dict(s=spec,verify=verify,read=read,require=require,Path=Path))
    return sorted(seen)


def prepare():
    source=HERE/'E118B_METADATA251_SOURCE_SEAL.json'
    for name,h in read(source)['files'].items():require(sha(ROOT/name)==h,'tested committed correction source bytes')
    oldspec_path=CACHE/'E118/analysis_handoff/REPORT_SPEC.PRIVATE.json';oldspec=read(oldspec_path)
    oldjudge=Path(oldspec['judgment_seal']);oldcap=Path(oldspec['cap_seal']);judge=verify(oldjudge,oldspec['judgment_sha256']);cap=verify(oldcap,oldspec['cap_sha256']);verify(oldspec['input_seal'],oldspec['input_sha256'])
    oldcost=read(oldcap.parent/'CAP_SETTLEMENT.json');require(oldcost['judgment_sha256']==sha(oldjudge),'original combined cap binds original terminal')
    out=CACHE/'E118/report_compat251';j=out/'judging';c=out/'cap';j.mkdir(parents=True,exist_ok=True);c.mkdir(exist_ok=True)
    before={str(p):sha(p)for p in [oldjudge,oldcap,oldspec_path]+[oldjudge.parent/n for n in judge['files']]+[oldcap.parent/n for n in cap['files']]}
    if (out/'HANDOFF_SEAL.json').exists():verify(out/'HANDOFF_SEAL.json',sha(out/'HANDOFF_SEAL.json'));frozen_metadata_preflight(read(out/'REPORT_SPEC.PRIVATE.json'));return out
    for name,h in judge['files'].items():
        p=j/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((oldjudge.parent/name).read_bytes());require(sha(p)==h,'byte-exact original judgment/response files')
    newjudge=corrected_metadata(judge,oldspec['input_sha256']);newjudge.update(compatibility_metadata_only=True,original_terminal_seal=str(oldjudge),original_terminal_sha256=sha(oldjudge),correction_source_sha256=sha(source));write(j/'JUDGMENT_SEAL.json',newjudge);verify(j/'JUDGMENT_SEAL.json',sha(j/'JUDGMENT_SEAL.json'))
    for name,h in cap['files'].items():
        if name!='CAP_SETTLEMENT.json':(c/name).write_bytes((oldcap.parent/name).read_bytes());require(sha(c/name)==h,'original cap contents unchanged')
    cost=dict(oldcost,judgment_sha256=sha(j/'JUDGMENT_SEAL.json'));require({k:v for k,v in cost.items()if k!='judgment_sha256'}=={k:v for k,v in oldcost.items()if k!='judgment_sha256'},'all financial amounts and prior spend unchanged');write(c/'CAP_SETTLEMENT.json',cost)
    newcap=copy.deepcopy(cap);newcap['files']['CAP_SETTLEMENT.json']=sha(c/'CAP_SETTLEMENT.json');newcap.update(phase_seal=str(j/'JUDGMENT_SEAL.json'),phase_sha256=sha(j/'JUDGMENT_SEAL.json'),compatibility_metadata_only=True,original_combined_cap_seal=str(oldcap),original_combined_cap_sha256=sha(oldcap));write(c/'JUDGMENT_SEAL.json',newcap);verify(c/'JUDGMENT_SEAL.json',sha(c/'JUDGMENT_SEAL.json'))
    spec=dict(oldspec,judgment_seal=str(j/'JUDGMENT_SEAL.json'),judgment_sha256=sha(j/'JUDGMENT_SEAL.json'),cap_seal=str(c/'JUDGMENT_SEAL.json'),cap_sha256=sha(c/'JUDGMENT_SEAL.json'));write(out/'REPORT_SPEC.PRIVATE.json',spec);checks=frozen_metadata_preflight(spec)
    require(all(sha(p)==h for p,h in before.items()),'ALL original seals/data/spec/cap files unchanged')
    write(out/'CUSTODY.json',dict(experiment='E118',part='b',status='METADATA_ONLY_REPORT_COMPATIBILITY',original_spec=str(oldspec_path),original_spec_sha256=sha(oldspec_path),original_judgment_sha256=sha(oldjudge),original_cap_sha256=sha(oldcap),compatible_judgment_sha256=spec['judgment_sha256'],compatible_cap_sha256=spec['cap_sha256'],response_bytes_sha256=sha(j/'RESPONSES.json'),original_response_bytes_sha256=judge['files']['RESPONSES.json'],all_original_files_unchanged=before,financial_amounts_unchanged=True,paid_calls=0,judgment_reparse=False,judgments_changed=False,analysis_or_guard_invoked=False,frozen_owner_terminal_assertions_passed=checks,correction_source_sha256=sha(source)))
    write(out/'HANDOFF_SEAL.json',dict(experiment='E118',part='b',status='COMPLETE_METADATA_COMPATIBILITY_FOR_FROZEN_REPORT',n=6790,original_artifacts_unchanged=True,analysis_run=False,paid_calls=0,files={name:sha(out/name)for name in['REPORT_SPEC.PRIVATE.json','CUSTODY.json']}))
    return out
