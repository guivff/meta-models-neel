"""E58a R-a1 only: committed blind categories, sealed labels, probe gates. CPU."""
from pathlib import Path
import json
import math
import subprocess
import sys
import time
import numpy as np
from scipy.stats import mannwhitneyu
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e52'))
from build_basis import read,dump,sha
from run_labels import verify
REQUEST=HERE/'REQUEST_2026-10-27.json'
CATEGORIES={'bookkeeping','delimiter','syntactic','format','content'}
TARGET={'bookkeeping','delimiter','syntactic'}

def category_rows(document):
    rows=document['rows']
    if not isinstance(rows,list):raise ValueError('category packet rows must be a list of bank,row,category records')
    result={}
    for r in rows:
        key=(r['bank'],r['row'])
        if key in result or r['category'] not in CATEGORIES:raise ValueError('duplicate row or unregistered category')
        result[key]=r['category']
    return result

def evaluate(rows):
    if len({(r['bank'],r['row']) for r in rows})!=len(rows):raise ValueError('one observation per bank/row')
    eligible=[];excluded=[]
    for r in rows:
        if r.get('probe_auroc') is None:
            if r['bank']=='E57' and r['row']=='capacity_list' and r['label']=='NOT APPLICABLE' and r['J_fraction'] is None and r.get('probe_not_applicable_reason')=='REGISTERED_COUNT_ONLY_NO_PROBE':
                excluded.append({'bank':r['bank'],'row':r['row'],'reason':'registered count-only row, no A/B label or probe (§173 clarification1c)'});continue
            raise ValueError('missing probe gate is not an exclusion')
        if r['category'] not in CATEGORIES or not math.isfinite(r['probe_auroc']) or not 0<=r['probe_auroc']<=1:raise ValueError('valid category and sealed probe AUROC required')
        if r['probe_auroc']<.85:excluded.append({'bank':r['bank'],'row':r['row'],'reason':'probe below0.85'});continue
        if r['label'] not in ('IN-J','OUT-J','DIFFUSE') or r['J_fraction'] is None or not math.isfinite(r['J_fraction']) or r['J_fraction']<0:raise ValueError('every probe-eligible row needs a computable primary J label/fraction; hold rather than drop')
        eligible.append(r)
    a=[r for r in eligible if r['category'] in TARGET];b=[r for r in eligible if r['category']=='content']
    if not a or not b:return {'status':'NOT EVALUABLE','met':None,'reason':'both registered category groups required','excluded':excluded}
    x=np.array([r['J_fraction'] for r in a]);y=np.array([r['J_fraction'] for r in b])
    ma=float(np.median(x));mb=float(np.median(y));p=float(mannwhitneyu(x,y,alternative='less',method='auto').pvalue)
    na=sum(r['label'] in ('OUT-J','DIFFUSE') for r in a);nb=sum(r['label'] in ('OUT-J','DIFFUSE') for r in b)
    met=ma<mb and p<.05 and na/len(a)>=.70 and nb/len(b)<=.30
    return {'status':'EVALUABLE','met':bool(met),'bookkeeping_delimiter_syntactic':{'n':len(a),'median_J_fraction':ma,'OUT_J_or_DIFFUSE':na,'OUT_J_or_DIFFUSE_rate':na/len(a)},'content':{'n':len(b),'median_J_fraction':mb,'OUT_J_or_DIFFUSE':nb,'OUT_J_or_DIFFUSE_rate':nb/len(b)},'mann_whitney_alternative':'less','one_sided_p':p,'excluded':excluded,'format_rows_not_in_R_a1_contrast':sum(r['category']=='format' for r in eligible),'rows':eligible}

def source(ref):
    p=Path(ref['path']).resolve();seal=Path(ref['seal_path']).resolve()
    if sha(p)!=ref['sha256'] or sha(seal)!=ref['seal_sha256']:raise ValueError('sealed input hash differs')
    if (seal.parent/ref['member']).resolve()!=p or read(seal)['files'][ref['member']]!=ref['sha256']:raise ValueError('unsealed input member')
    return read(p)

def run():
    request=read(REQUEST);receiptpath=ROOT/request['verified_inputs']
    if request['banks'] is None or not receiptpath.exists():print('E58a WAITING_FOR_SCOPE_RULING_OR_VERIFIED_CATEGORIES_LABELS_PROBE_GATES');return 2
    verify(ROOT,read(HERE/'CODE_SEAL_2026-10-27.json')['files'])
    delivery=read(receiptpath)
    if delivery['issuer']!='integrator' or delivery['status']!='VERIFIED_R_A1_INPUTS':raise ValueError('integrator verification required')
    cat=delivery['categories'];cp=ROOT/cat['repository_path']
    if sha(cp)!=cat['sha256']:raise ValueError('category hash differs')
    committed=subprocess.check_output(['git','show',cat['commit']+':'+cat['repository_path']],cwd=ROOT)
    if committed!=cp.read_bytes():raise ValueError('category assignment must be committed before the join')
    if delivery.get('category_author_blind_attestation') is not True:raise ValueError('blind category provenance required')
    cache=ROOT/'cache/g_agreement/understand/e58a';cache.mkdir(parents=True,exist_ok=True)
    # No label/probe document is opened until the category commit has been verified.
    mapping=category_rows(read(cp));required=set(request['banks'])
    if not required<=set(delivery['banks']):raise ValueError('all registered analysis banks required')
    joined=[]
    for bank in request['banks']:
        refs=delivery['banks'][bank];labeldoc=source(refs['labels']);labels=labeldoc['rows'];probes=source(refs['probe_only'])
        if labeldoc.get('label_role')!='PRIMARY_SPARSE' and not all(r.get('label_of_record')=='nonnegative sparse J pursuit, k16' for r in labels):raise ValueError('primary sparse labels required, not secondary SVD labels')
        if probes.get('measure')!='test_probe_auroc' or probes.get('layer')!=44 or probes.get('reader_outcomes_included') is not False:raise ValueError('probe-only block44 test extract required; no reader outcomes')
        pr={r['row']:r for r in probes['rows']}
        if len(pr)!=len(probes['rows']):raise ValueError('duplicate probe rows')
        expected={row for b,row in mapping if b==bank}
        if {r['row'] for r in labels}!=expected or set(pr)!=expected:raise ValueError('complete category/label/probe row coverage required')
        joined.extend({'bank':bank,'row':r['row'],'category':mapping[(bank,r['row'])],'J_fraction':r['J_fraction'],'label':r['label'],'probe_auroc':pr[r['row']]['auroc'],'probe_not_applicable_reason':pr[r['row']].get('reason')} for r in labels)
    # Preflight validates the complete scientific join before consuming the once-only claim.
    for r in joined:
        if r['probe_auroc'] is None:
            if not (r['bank']=='E57' and r['row']=='capacity_list' and r['label']=='NOT APPLICABLE' and r['J_fraction'] is None and r['probe_not_applicable_reason']=='REGISTERED_COUNT_ONLY_NO_PROBE'):raise ValueError('missing gate; hold experiment')
        elif r['probe_auroc']>=.85 and (r['label'] not in ('IN-J','OUT-J','DIFFUSE') or r['J_fraction'] is None):raise ValueError('eligible unlabelled row; hold experiment, no silent exclusion')
    with (cache/'R_A1_ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'verified_inputs_sha256':sha(receiptpath)},f)
    result=evaluate(joined);out=HERE/'R_a1';out.mkdir(exist_ok=False)
    dump(out/'RESULT.json',{'experiment':'E58a','rule':'R-a1','result':result,'banks':request['banks'],'category_commit':cat['commit'],'category_sha256':cat['sha256'],'verified_inputs_sha256':sha(receiptpath),'code_seal_sha256':sha(HERE/'CODE_SEAL_2026-10-27.json'),'R_a2':'HELD_UNTIL_E49_E56_E57_READER_ANALYSES','reader_outcomes_accessed':False})
    (out/'RESULTS.md').write_text('# E58a R-a1\n\n'+('MET' if result['met'] is True else 'NOT MET' if result['met'] is False else 'NOT EVALUABLE')+'\n\nR-a2 remains held until E49/E56/E57 readers are analysed.\n')
    dump(out/'ANALYSIS_SEAL.json',{'files':{p.name:sha(p) for p in out.iterdir()}})
    print('E58a R-a1 complete once; R-a2 held');return 0

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; use committed request')
    raise SystemExit(run())
