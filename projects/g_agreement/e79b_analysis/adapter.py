"""E79 Arm B only: existing readers and sealed E59 behaviour; CPU only."""
import argparse, subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core as c
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ROWS=('format_plan','language_plan')
CELLS=('none','J','nonJ','random')
BASE=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e79/arm_b'
GUARD=BASE/'ANALYSIS_ONCE.json'

def source():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h,'source receipt')
        import hashlib
        c.require(hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def grid(rows):
    c.unique(rows);c.require(len(rows)==672,'672 original Arm B readouts')
    c.require({x['row'] for x in rows}==set(ROWS),'original two rows')
    for row in ROWS:
        groups={k:[x for x in rows if x['row']==row and x['direction']==k] for k in CELLS}
        c.require(sum(map(len,groups.values()))==336,'four cells only')
        ref=None;labels={}
        for xs in groups.values():
            ids={x['item'] for x in xs};c.require(len(ids)==len(xs)==84,'84 unique original items/cell')
            if ref is None:ref=ids
            c.require(ids==ref,'paired original items')
            for x in xs:
                c.require(x['target'] in ('A','B') and labels.setdefault(x['item'],x['target'])==x['target'],'unchanged true target')

def analyze(rows,behaviour,diagnostics):
    grid(rows);states={}
    for row in ROWS:
        cells={k:{x['item']:x['score'] for x in rows if x['row']==row and x['direction']==k} for k in CELLS}
        rates={k:c.stats(v) for k,v in cells.items()}
        drop=c.stats(cells['none'],cells['J'])
        extra=c.stats(cells['nonJ'],cells['J'])
        auroc={k:behaviour['auroc'][b][row] for k,b in zip(CELLS,('none','d_J','d_perp','random'))}
        c.require(all(type(v) in (int,float) and 0<=v<=1 for v in auroc.values()),'sealed E59 AUROCs')
        preserved=round(auroc['J']-auroc['none'],12)>=-.10
        known=extra['estimate'] is not None and extra['CI95'] is not None
        ok=known and round(extra['estimate'],12)>=.30 and extra['CI95'][0]>0 and preserved
        states[row]=dict(rates=rates,drop_J=drop,drop_J_minus_drop_perp=extra,AUROC=auroc,behaviour_preserved=preserved,status='NOT EVALUABLE' if not known else 'MET' if ok else 'NOT MET')
    status='MET' if all(x['status']=='MET' for x in states.values()) else 'NOT EVALUABLE' if any(x['status']=='NOT EVALUABLE' for x in states.values()) else 'NOT MET'
    drops=[x['drop_J']['estimate'] for x in states.values()]
    falsifier='NOT MET' if any(x is not None and round(x,12)>=.10 for x in drops) else 'NOT EVALUABLE' if None in drops else 'MET'
    return dict(experiment='E79_ARM_B',R_C2=status,falsifier=falsifier,states=states,diagnostics=[x for x in diagnostics['rows'] if x['arm']=='B'],
                rule='Latest Guiv: on both states drop_J minus drop_perp >=.30, paired bootstrap lower>0, AUROC(J)>=AUROC(none)-.10',
                bootstrap='Original paired item 2000 draws seed20261027; separate cell missing masks; random descriptive',Arm_A='Immutable, not rerun')

def custody(s):
    for f,h in s['inputs'].items():c.require(c.sha(f)==h,'original input hash')
    z=c.verify(Path(s['output'])/'OUTPUT_SEAL.json',s['output_sha256'])
    c.require(z['status']=='COMPLETE' and z['input_seal_sha256']==s['input_sha256'],'complete original acquisition')
    b=c.verify(s['behaviour_seal'],s['behaviour_sha256'])
    c.require(b['behaviour_only'] is True and b['output_seal_sha256']==s['output_sha256'],'original completed behaviour only')
    c.require(s['cap']==dict(bank='E79_ARM_B',lifetime_USD=3,separate_from_Arm_A=True,owner='W-internals-B'),'Guiv separate bank cap')

def prepare(s,commit):
    custody(s)
    keys=c.unique(c.read(s['key']));items=c.read(s['items']);root=Path(s['output']);jobs=c.read(root/'JOB_GRID.json')
    c.require(c.read(root/'COMPLETED.json')==list(range(len(jobs))),'all source jobs complete')
    values=c.read(s['original_analysis_spec'])['values'];rows=[]
    for number,job in enumerate(jobs):
        if job['kind']!='native':continue
        # Open only batches containing Arm B; Arm A is never reanalyzed.
        if not any(keys[items[ix]['id']]['arm']=='B' for ix in job['indices']):continue
        payload=c.read(root/'jobs'/f'{number:06d}.json')
        c.require(len(payload)==len(job['indices']),'native batch count')
        for x,ix in zip(payload,job['indices']):
            c.require(x['id']==items[ix]['id'],'original output index')
            k=keys[x['id']]
            if k['arm']!='B':continue
            c.require(k['true_label'] in (0,1),'original true label')
            v=values[k['row']]
            rows.append(dict(id=x['id'],item=k['source_item_id'],row=k['row'],direction=k['condition'],reader='oracle',target='A' if k['true_label']==1 else 'B',property=k['row'],values=dict(A=v[0],B=v[1]),text=x['text']))
    grid(rows)
    c.require(Path(s['blind']).resolve()==BASE/'blind' and Path(s['private']).resolve()==BASE/'JOIN.PRIVATE.json','fixed packet custody')
    c.export(rows,s['blind'],s['private'],s['output_sha256'],commit)
    c.write(BASE/'CAP_BINDING.json',s['cap'])
    c.write(BASE/'SPEC.json',s)
    c.seal(BASE,'DELIVERY_SEAL.json',experiment='E79_ARM_B',status='READY_FOR_B_ADMISSION',records=672,code_commit=commit,analysis_guard=str(GUARD),cap=s['cap'])

def run(s,commit):
    custody(s)
    js=Path(s['judgments'])/'JUDGMENT_SEAL.json'
    j=c.verify(js,c.sha(js))
    c.require(j.get('bank')=='E79_ARM_B' and j.get('cap_binding_sha256')==c.sha(BASE/'CAP_BINDING.json'),'B terminal bank binds separate lifetime cap')
    c.require(j.get('unknown_charges')==0 and type(j.get('actual_USD')) in (int,float) and 0<=j['actual_USD']<=3,'settled bank within authorized cap')
    rows,jsha=c.load_codes(s);grid(rows)
    c.require(Path(s['analysis']).resolve()==BASE/'analysis_once','fixed analysis destination')
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    b=c.read(Path(s['behaviour_seal']).parent/'metrics/METRICS.json');d=c.read(s['diagnostics'])
    c.write(out/'RESULTS.json',analyze(rows,b,d))
    c.write(out/'REDACTION_SENSITIVITY.json',analyze([dict(x,score=None if x['redacted'] else x['score']) for x in rows],b,d))
    c.write(out/'BINDING.json',s);c.seal(out,'ANALYSIS_SEAL.json',experiment='E79_ARM_B',status='COMPLETE_ONCE',judgment_sha256=jsha,code_commit=commit)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','analyze']);p.add_argument('--spec',required=True);a=p.parse_args();commit=source();s=c.read(a.spec)
    (prepare if a.mode=='prepare' else run)(s,commit)
