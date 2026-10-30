"""E43 sealed-source, CPU-only analysis. A failed attempt is never retried automatically."""
import argparse, hashlib, json, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.metrics import roc_auc_score
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from projects.g_agreement.understand.e24_statements import statement, PATTERNS

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def auc(labels,scores):
    if len(set(labels))<2:return None
    return float(roc_auc_score([x=='A' for x in labels],scores))

def silent_sets(records, mentions):
    by_item=defaultdict(list)
    for r,m in zip(records,mentions):by_item[r['id']].append(m)
    all_silent={i for i,ms in by_item.items() if all(m=='neither' for m in ms)}
    any_silent={i for i,ms in by_item.items() if any(m=='neither' for m in ms)}
    return all_silent,any_silent

def rule(results):
    candidates=[r for r in results if r['primary'] and r['reader']=='oracle' and r['classification']!='semantic']
    eligible=[r for r in candidates if r['evaluable'] and r['probe_auroc'] is not None and r['probe_auroc']>=.90]
    passed=[r for r in eligible if r['mention_rate']<=.05 and r['silent_all']['auroc']>=.85]
    return dict(verdict='NOT EVALUABLE' if not eligible else 'R1 HOLDS' if len(passed)>len(eligible)/2 else 'R1 DOES NOT HOLD',eligible_rows=len(eligible),passing_rows=len(passed),passing=[r['bank']+'/'+r['row'] for r in passed],denominator=[r['bank']+'/'+r['row'] for r in eligible])

def run():
    out=HERE/'analysis_2026-10-26';out.mkdir(exist_ok=True)
    # Exclusive lock before all input validation; retain on any error, never overwrite results.
    with (HERE/'ANALYSIS_ATTEMPT.lock').open('x') as f:f.write('E43 once-only integrator execution\n')
    code=read(HERE/'COMMAND_SEAL.json')
    for name,h in code['files'].items():
        if sha(HERE/name)!=h:raise ValueError('command/coverage changed: '+name)
    coverage_seal=read(HERE/'COVERAGE_SEAL.json')
    for name,h in coverage_seal['files'].items():
        if sha(HERE/name)!=h:raise ValueError('coverage changed: '+name)
    pins=read(HERE/'cache/SOURCE_PINS.json')
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('source changed: '+p)
    data=read(HERE/'cache/READOUTS.json');inventory=read(HERE/'INVENTORY.json')
    # Validate uniqueness before any detector call; prepare.py already froze exact-text deduplication.
    keys=[tuple(r[k] for k in ('bank','row','reader','layer','arm','id','text')) for r in data]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate prepared readout')
    # Original frozen item definitions bind the score orientation for all test items.
    label_map={}
    for p in pins:
        if p.endswith('items.DO_NOT_STAGE.jsonl'):
            path=Path(p);bank='w1b' if path.parent.name=='w1b-bank-v1' else 'w1'
            defs=read(path.parent/'manifest.json')['rows']
            for r in rows(path):
                values=defs[r['feature']]['values']
                if r['value'] in values:label_map[bank,r['id']]=(r['feature'],'A' if r['value']==values[0] else 'B',r['split'])
    for r in data:
        if label_map[r['bank'],r['id']][0:2]!=(r['row'],r['label']):raise ValueError('prepared label mismatch')
    probe_rows=rows(read(HERE/'cache/PROBE_PATH.json'))
    probes={}
    for r in probe_rows:
        key=('w1',r['id'],r['layer'])
        if key in probes:raise ValueError('duplicate probe item')
        if not np.isfinite(r['true']):raise ValueError('nonfinite probe score')
        probes[key]=r['true']
    codes={}
    for r in data:
        for ref in r['codes']:
            if ref['path'] not in codes:codes[ref['path']]={x['id']:x for x in rows(ref['path'])}
    grouped=defaultdict(list)
    for r in data:grouped[tuple(r[k] for k in ('bank','row','reader','layer','arm'))].append(r)
    results=[]
    for cov in inventory['rows']:
        key=tuple(cov[k] for k in ('bank','row','reader','layer','arm'));bank,row,reader,layer,arm=key;rs=grouped[key]
        mentions=[]
        for r in rs:
            if row in PATTERNS:m=statement(row,r['text'])
            elif r['codes']:
                values=[]
                for ref in r['codes']:
                    c=codes[ref['path']][ref['id']]
                    if type(c['mentions']) is not bool:raise ValueError('invalid frozen code')
                    values.append('neither' if not c['mentions'] else c['value'] if c['value'] in ['A','B'] else 'unclear')
                m=values[0] if len(set(values))==1 else None  # No adjudication of conflicting frozen codes.
            else:m=None
            mentions.append(m)
        known=[(r,m) for r,m in zip(rs,mentions) if m is not None]
        missing=len(rs)-len(known)
        mentioned=sum(m!='neither' for r,m in known)
        correct=sum(m==r['label'] for r,m in known);wrong=sum(m in ['A','B'] and m!=r['label'] for r,m in known)
        all_silent,any_silent=silent_sets(rs,mentions)
        def subset(ids):
            ids=sorted(ids);missing_probe=[i for i in ids if (bank,i,layer) not in probes]
            labs=[label_map[bank,i][1] for i in ids]
            return dict(n=len(ids),labels={x:labs.count(x) for x in ['A','B']},missing_probe_items=len(missing_probe),auroc=None if missing_probe else auc(labs,[probes[bank,i,layer] for i in ids]))
        sa,sy=subset(all_silent),subset(any_silent)
        # Row baseline uses all sealed test-item probe predictions, not only sampled readouts.
        full_ids=sorted(i for b,i,l in probes if b==bank and l==layer and (b,i) in label_map and label_map[b,i][0]==row and label_map[b,i][2]=='test')
        full=subset(full_ids)
        reasons=[]
        if missing:reasons.append('missing or conflicting frozen detector/codes for '+str(missing)+' readouts')
        if cov['missing_probe_items']:reasons.append('missing matching probe scores for '+str(cov['missing_probe_items'])+' readout items')
        if sa['n']<20:reasons.append('fewer than 20 all-silent items')
        if min(sa['labels'].values())==0:reasons.append('all-silent items lack both labels')
        if full['auroc'] is None:reasons.append('no evaluable full-row test probe')
        results.append({**cov,'mention_rate':None if missing else mentioned/len(rs),'value_correct_mention':None if missing else (correct-wrong)/len(rs),'coded_subset_descriptive':dict(n=len(known),mention_rate=mentioned/len(known) if known else None,value_correct_mention=(correct-wrong)/len(known) if known else None),'probe_auroc':full['auroc'],'probe_test_n':full['n'],'silent_all':sa,'silent_any_descriptive':sy,'evaluable':not reasons,'status':'EVALUABLE' if not reasons else 'NOT EVALUABLE','reasons':reasons})
    verdict=rule(results)
    save(out/'METRICS.json',dict(registration='§153 clarification 1',coverage_seal_sha256=sha(HERE/'COVERAGE_SEAL.json'),command_seal_sha256=sha(HERE/'COMMAND_SEAL.json'),R1=verdict,rows=results,bootstrap='No additional inferential rule or fitted calibration model; point estimates only.',api_calls=0,gpu_seconds=0))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,5))
    for reader,color in [('oracle','#3569aa'),('nla','#cf6b36')]:
        points=[r for r in results if r['primary'] and r['reader']==reader and r['mention_rate'] is not None and r['probe_auroc'] is not None]
        ax.scatter([r['mention_rate'] for r in points],[r['probe_auroc'] for r in points],label=reader,color=color,alpha=.65)
        # Fixed decile bins summarize the descriptive curve, with no fitted model or extra test.
        binned=[]
        for lo in np.arange(0,1,.1):
            ps=[r for r in points if lo<=r['mention_rate']<lo+.1 or lo>.89 and r['mention_rate']==1]
            if ps:binned.append((np.mean([r['mention_rate'] for r in ps]),np.mean([r['probe_auroc'] for r in ps])))
        if binned:ax.plot(*zip(*binned),color=color,linewidth=1)
    ax.set(xlabel='Mention rate over deduplicated readouts',ylabel='Sealed full-row probe AUROC',xlim=(-.02,1.02),ylim=(-.02,1.02),title='E43: native readout mention vs probe (descriptive)');ax.legend();fig.tight_layout();fig.savefig(out/'CALIBRATION.png',dpi=170);plt.close(fig)
    fmt=lambda v:'NA' if v is None else f'{v:.4f}'
    report=['# E43 silence audit — 2026-10-26','',verdict['verdict']+f" ({verdict['passing_rows']}/{verdict['eligible_rows']} eligible structure bank-rows).",'', 'Primary silent items have every deduplicated readout silent. Other layers and E28 adapted arms enter no rule. Missing coding and probes are not imputed. Point estimates; descriptive calibration lines join fixed decile-bin means.','', '| Bank / row / reader / block / arm | Readouts | Mention | Correct minus wrong | Probe | All-silent n / AUROC | Any-silent n / AUROC | Status |','|---|---:|---:|---:|---:|---|---|---|']
    for r in results:report.append('| '+' / '.join(str(r[k]) for k in ['bank','row','reader','layer','arm'])+f" | {r['deduplicated_readouts']} | {fmt(r['mention_rate'])} | {fmt(r['value_correct_mention'])} | {fmt(r['probe_auroc'])} | {r['silent_all']['n']} / {fmt(r['silent_all']['auroc'])} | {r['silent_any_descriptive']['n']} / {fmt(r['silent_any_descriptive']['auroc'])} | {r['status']}: {'; '.join(r['reasons'])} |")
    (out/'RESULTS.md').write_text('\n'.join(report)+'\n')
    save(out/'ANALYSIS_SEAL.json',dict(status='E43_COMPLETE_ONCE',files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},coverage_seal_sha256=sha(HERE/'COVERAGE_SEAL.json'),command_seal_sha256=sha(HERE/'COMMAND_SEAL.json')))
    print(verdict['verdict'])
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute-once',action='store_true',required=True);parser.parse_args();run()
