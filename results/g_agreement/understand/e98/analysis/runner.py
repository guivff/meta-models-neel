"""E98 final operational binding and exclusive descriptive publication. CPU only."""
import hashlib,json,subprocess,sys,time,datetime
from pathlib import Path
from adapter import describe,gate,rate,reported,signed_value,validate_judgment,require
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def old_sensitivity(units,primary,original,native,expected):
    old={x['id']:x for x in original}
    require(len(old)==len(original)==len(expected) and set(old)==set(expected),'exact seeded old-rubric subset')
    require(set(old)<=set(primary),'old rubric only actual categorical judgment items')
    for k,j in old.items():validate_judgment(j,native[k])
    rows=[]
    for u in units:
        xs=sorted([x for x in u['items'] if x['id'] in old],key=lambda x:x['id'])
        row=dict(bank=u['bank'],row=u['row'],matched_items=len(xs),binary=u['binary'])
        if u['binary'] and xs:
            row.update(primary=rate([[signed_value(primary[x['id']],x['label'])] for x in xs]),
                       original=rate([[signed_value(old[x['id']],x['label'])] for x in xs]))
        else:row.update(primary=None,original=None,reason='Nonbinary or no sampled items; no binary S invented')
        rows.append(row)
    return dict(scope='Matched seeded old-rubric subset only; not full-bank replacement',items=len(old),rows=rows)
def verify(plan):
    for p,h in plan['pins'].items():require(sha(p)==h,'exact pin '+p)
    for path in plan['member_seals']:
        s=read(path)
        for n,h in s['files'].items():require(sha(Path(path).parent/n)==(h['sha256'] if isinstance(h,dict) else h),'sealed member '+n)
    prod=read(plan['producer_plan']);receipt=read(plan['normalization_receipt']);binding=plan['binding']
    n=read(plan['native_seal']);j=read(plan['judgment_seal']);close=read(plan['native_closeout'])
    require(n['experiment']=='E98' and n['status']=='COMPLETE' and n['layer']==18,'native model/site')
    require(n['card_sha256']==plan['card_sha256'],'exact 4B card')
    require(j['bank']=='E98' and j['terminal'] and j['route_verified'] and j['redaction_audit_complete'],'terminal frozen route/privacy')
    require(j['old_rubric_records']==447 and j['primary_records']==1785 and j['binary_items']==1932 and j['nonbinary_items']==252,'original channel scopes')
    require(close['first_output_utc']>plan['original_forecast_commit_utc'] and close['capture_sha256']==binding['capture_seal_sha256'],'original forecast before native / capture lineage')
    for name,p in prod['normalized_inputs'].items():
        require(sha(p['path'])==p['sha256']==receipt['normalized_files'][name], 'normalized member '+name)
    require(prod['native_seal_sha256']==sha(plan['native_seal'])==receipt['native_seal_sha256'],'producer/native lineage')
    require(prod['judgment_seal_sha256']==sha(plan['judgment_seal'])==receipt['judgment_seal_sha256'],'producer/judgment lineage')
    bundle={name:read(p['path']) for name,p in prod['normalized_inputs'].items()}
    require(len(bundle['ORIGINAL.json'])==len(read(plan['original_sample_ids']))==447,'447 matched old-rubric codes')
    units=bundle['UNITS.PRIVATE.json'];native=bundle['NATIVE.json'];primary=bundle['JUDGMENTS.json'];counts=bundle['COUNT_MEASURES.json'];qwen=bundle['ORIGINAL_QWEN.json']
    require(len(native)==2184 and len(primary)==2016 and len(counts)==168,'normalized terminal scopes')
    rawp=read(Path(plan['judgment_seal']).parent/'PRIMARY.json');rawr=read(Path(plan['judgment_seal']).parent/'REGEX_RESOLVED.json');rawc=read(Path(plan['judgment_seal']).parent/'COUNT_MEASURES.json')
    require(primary=={x['id']:{k:x[k] for k in ('id','category','values','evidence')} for x in rawp+rawr},'codes unchanged from sealed primary/regex')
    require(counts=={x['id']:x['measurement'] for x in rawc},'typed counts unchanged')
    require(bundle['ORIGINAL.json']==read(Path(plan['judgment_seal']).parent/'ORIGINAL.json'),'old codes unchanged')
    for k,text in native.items():require(text==read(Path(plan['native_seal']).parent/'records'/(k+'.json'))['text'],'native text unchanged')
    for u in units:
        key=u['bank']+'|'+u['row'];source=receipt['original_qwen_source'][u['bank']];res=read(source['results_path'])
        require(qwen[key]['source']==source and qwen[key]['no_baseline_rerun'] is True,'original Qwen source mapping')
        require(qwen[key]['original_signed_metric']==res['rates'].get('oracle|'+u['row']),'original Qwen metric exact')
        co=Path(source['results_path']).parent/'COUNTS.json';ids={x['source_id'] for x in u['items']}
        expected=[x for x in read(co) if x['reader']=='oracle' and x['feature']==u['row'] and x['unit_id'] in ids] if co.exists() else []
        require(qwen[key]['original_count_records']==expected,'original Qwen counts exact')
    nv=dict(experiment='E98',status='COMPLETE',items=2184,unique_items=2184,capture_seal_sha256=binding['capture_seal_sha256'],input_seal_sha256=n['input_sha256'],sha256=sha(plan['native_seal']))
    jv=dict(nv,input_seal_sha256=j['input_sha256'],sha256=sha(plan['judgment_seal']),native_seal_sha256=j['native_seal_sha256'],rubric_sha256=j['rubric_sha256'],terminal=j['terminal'])
    gate(binding,nv,jv)
    return bundle,{x['id']:x for x in rawc}
def report(result,sensitivity,out):
    lines=['# E98 Oracle 4B / block18 — DESCRIPTIVE','', 'Original prospective J forecast is immutable. Original Qwen metrics are copied from sealed E57/E59 analyses. No source analysis or count detector was rerun.','', '| Source row | 4B S [95% CI] | Original Qwen S | Original J | Native label | J agrees | Missing |','|---|---|---:|---|---|---|---:|']
    for r in result['rows']:
        q=r['original_Qwen']['original_signed_metric'];qs=q.get('S') if q else None
        s=r['S'];v='nonbinary' if s is None else str(s['S'])+' '+str(s['CI95'])
        lines.append('| '+r['bank']+'/'+r['row']+' | '+v+' | '+str(qs)+' | '+str(r.get('original_J_prediction'))+' | '+str(r['native_label'])+' | '+str(r['J_agrees'])+' | '+str(r.get('UNPARSEABLE','—'))+' |')
    lines+=['','All26rows/2184items retained:23binary/1932 plus3nonbinary/252;0port drops. capacity_list/category_switch retain168 original measurement objects, focus_none84actual mention judgments. No binary S/J invented for any nonbinary unit. Full Qwen original count records remain in RESULTS.json.','', 'OLD_RUBRIC_SENSITIVITY.json reports primary and original-rubric signed S on the exact seeded447-item subset only; separate missing masks and unchanged whole-item bootstrap2000/seed20261027. No full-bank old-rubric substitution.','', 'All74 truncated native outputs retained. No new confirmatory threshold/rule; inherited descriptive REPORTED criterion S≥.2 and CI lower>0. Operational count/schema amendments were committed after terminal judging but before any analysis claim; original adapter was committed pre-judging. See FINAL_INPUT_PLAN.json for chronology, normalized/original hashes and exact source bindings.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    import matplotlib.pyplot as plt
    rs=[r for r in result['rows'] if r['binary']];f,ax=plt.subplots(figsize=(12,11))
    for y,r in enumerate(rs):
        for off,z,col in [(-.12,r['S'],'#0b7285'),(.12,r['original_Qwen']['original_signed_metric'],'#777777')]:
            if z and z.get('S') is not None:
                ax.plot(z['S'],y+off,'o',color=col)
                if z.get('CI95'):ax.plot(z['CI95'],[y+off,y+off],color=col,lw=1.5)
    ax.set_yticks(range(len(rs)),[r['bank']+'/'+r['row'] for r in rs]);ax.invert_yaxis();ax.axvline(0,color='#999999',lw=.7);ax.set_xlim(-1.05,1.05);ax.set_xlabel('Signed S with original whole-item bootstrap 95% CI');ax.set_title('E98 DESCRIPTIVE: 4B Oracle block18 (teal) vs original Qwen Oracle (gray)');f.tight_layout();f.savefig(out/'FIGURE.png',dpi=170);f.savefig(out/'FIGURE.svg');plt.close(f)
def main():
    planpath=HERE/'FINAL_INPUT_PLAN.json';plan=read(planpath)
    for p in [planpath,HERE/'adapter.py',HERE/'runner.py']:
        blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT);require(hashlib.sha256(blob).hexdigest()==sha(p),'committed final plan/source first')
    # Import plotting before consuming a scientific claim.
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot
    bundle,counts=verify(plan)
    guard=ROOT/'cache/g_agreement/understand/e98/analysis_once/ONCE.json';out=ROOT/'results/g_agreement/understand/e98/analysis_once'
    require(not out.exists(),'no original output replay');guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:json.dump(dict(plan_sha256=sha(planpath),at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f)
    t=time.monotonic();out.mkdir(exist_ok=False)
    result=describe(bundle['UNITS.PRIVATE.json'],bundle['JUDGMENTS.json'],bundle['NATIVE.json'],bundle['FORECAST.json'],bundle['ORIGINAL_QWEN.json'],counts)
    sens=old_sensitivity(bundle['UNITS.PRIVATE.json'],bundle['JUDGMENTS.json'],bundle['ORIGINAL.json'],bundle['NATIVE.json'],read(plan['original_sample_ids']))
    write(out/'RESULTS.json',result);write(out/'OLD_RUBRIC_SENSITIVITY.json',sens);report(result,sens,out)
    write(out/'EXECUTION.json',dict(wall_seconds=time.monotonic()-t,gpu_hours=0,plan_sha256=sha(planpath),original_forecast_sha256=plan['binding']['forecast_sha256'],status='COMPLETE_ONCE'))
    write(out/'ANALYSIS_SEAL.json',dict(experiment='E98',status='COMPLETE_ONCE',scope='DESCRIPTIVE',plan_sha256=sha(planpath),files={p.name:sha(p) for p in out.iterdir()}))
    print(json.dumps(dict(status='COMPLETE_ONCE',binary_rows=23,nonbinary_rows=3,native_items=2184)))
if __name__=='__main__':main()
