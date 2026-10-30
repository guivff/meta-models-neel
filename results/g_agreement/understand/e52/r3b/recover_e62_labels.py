"""Finalize interrupted E62 labels from persisted outputs; no forward or pursuit."""
from pathlib import Path
import sys,time,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CHANNEL=ROOT/'results/g_agreement/understand/e57/jlens'
sys.path.insert(0,str(CHANNEL))
import cpu_job as c

def recover():
    c.verify(ROOT,c.read(HERE/'E62_RECOVERY_SEAL_2026-10-27.json')['files'])
    c.verify(ROOT,c.read(HERE/'CODE_SEAL_2026-10-27.json')['files'])
    planpath=CHANNEL/'E62_INPUT_PLAN.json';c.committed(planpath);plan=c.read(planpath)
    cache=ROOT/'cache/g_agreement/understand/e62/jlens';out=cache/'raw'
    claim=c.read(cache/'ONCE.json');assert claim['plan_sha256']==c.sha(planpath)
    evidence=c.read(HERE/'E62_RECOVERY_EVIDENCE_2026-10-27.json');c.verify(out,evidence['raw_files'])
    tests={r['id']:r for r in c.read(c.sealed_ref(plan['records'],plan['bank_seal'])) if r['split']=='test'}
    null=c.read(c.E52_CACHE/'sparse-primary/NULL_SEAL.json');c.verify(c.E52_CACHE/'sparse-primary',null['files'])
    q=np.load(c.E52_CACHE/'basis_L44_r1536.npy',allow_pickle=False);svdnull=c.read(c.E52_CACHE/'ENRICHMENT_NULL.json')['ranks']
    assert not (CHANNEL/'E62_results').exists()
    with (cache/'RECOVERY_FINALIZATION_ONCE.json').open('x') as f:json.dump({'epoch':time.time(),'source_claim_sha256':c.sha(cache/'ONCE.json'),'evidence_sha256':c.sha(HERE/'E62_RECOVERY_EVIDENCE_2026-10-27.json')},f)
    rows=[]
    for u in plan['units']:
        row={'bank':'E62','row':u['id'],'source_row':u['source_row'],'condition':u.get('condition'),'n_test':len(u['item_ids'])}
        if u['binary']:
            raw=c.read(out/(u['id']+'.readout.json'))['items'];assert [r['id'] for r in raw]==u['item_ids']
            z=np.load(out/(u['id']+'.direction.npz'),allow_pickle=False)
            # Same sealed statistics, from the first pass's saved class means/ranks.
            enrich,means,d,norm=c.core.enrich(z['class_means'],np.array([1,0]),q,svdnull)
            assert np.array_equal(d,z['direction']) and np.array_equal(means,z['class_means'])
            ranks=[r['best_full_vocab_ranks'] for r in raw];y=np.array([tests[i]['label'] for i in u['item_ids']])
            g3=c.core.g3(np.array(ranks,dtype=np.int64),y) if all(all(x is not None for x in r) for r in ranks) else {'status':'NOT EVALUABLE','readable':None,'reason':'empty frozen value-token sets'}
            value=float(c.fraction(np.asarray(d,dtype=np.float32)[None,:],z['reconstruction'])[0])
            row.update(label=c.primary_label(value,null['median'],null['percentile97_5'],g3),J_fraction=value,J_readability=g3,enrichment=enrich,secondary_SVD_label=c.core.label(enrich,g3),class_mean_difference_norm=norm)
        else:
            row.update(label='NOT APPLICABLE',J_fraction=None,J_readability={'status':'NOT EVALUABLE','reason':'non-binary descriptive unit; no registered A/B direction','readable':None},descriptive_readout_status='NOT COMPLETED: frozen grader single-token set is empty; original pass stopped at first S6; no retry')
        rows.append(row)
    assert len([r for r in rows if r['J_fraction'] is not None])==25
    c.dump(out/'RAW_SEAL.json',{'files':evidence['raw_files'],'operational_note':'25 original binary units complete; S6 descriptive failure; no raw files regenerated'})
    dest=CHANNEL/'E62_results';dest.mkdir(exist_ok=False)
    c.dump(dest/'ROW_LABELS.json',{'experiment':'E62','label_role':'PRIMARY_SPARSE','rows':rows,'plan_sha256':c.sha(planpath),'code_seal_sha256':c.sha(CHANNEL/'CODE_SEAL_2026-10-27.json'),'raw_seal_sha256':c.sha(out/'RAW_SEAL.json'),'raw_directory':str(out),'GPU_hours':0,'reader_outcomes_accessed':False,'recovery_seal_sha256':c.sha(HERE/'E62_RECOVERY_SEAL_2026-10-27.json'),'operational_recovery':'No model forward or sparse pursuit repeated. Deterministic sealed statistics serialized from first-pass ranks, class means and reconstruction. Original claim retained.'})
    (dest/'LABELS.md').write_text('# E62 original J labels\n\nS6 excluded; its descriptive channel stopped on an empty frozen token set. Binary results recovered from saved first-pass outputs.\n\n| Unit | Primary label |\n|---|---|\n'+'\n'.join('| '+r['row']+' | '+r['label']+' |' for r in rows)+'\n')
    c.dump(dest/'LABEL_SEAL.json',{'files':{p.name:c.sha(p) for p in dest.iterdir()}})
    print('E62 finalization:25 saved binary outputs;5 S6 exclusions; no forward/pursuit repeated')
if __name__=='__main__':recover()
