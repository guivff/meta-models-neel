"""Assemble continuation context from sealed columns; never fit or score readers."""
from pathlib import Path
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
R=ROOT/'results/g_agreement/understand'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
sources={}
def document(key,path,seal):
    s=read(seal);member=str(path.relative_to(seal.parent))
    assert s['files'][member]==sha(path)
    sources[key]={'path':str(path),'sha256':sha(path),'seal_path':str(seal),'seal_sha256':sha(seal),'member':member}
    return read(path)
def ref(key,pointer):return {'document':key,'pointer':pointer}
def unavailable(reason):return {'unavailable_reason':reason}
def main():
    gridroot=ROOT.parent/'wt-blindspot-internals/cache/g_agreement/understand/e5354/prepared'
    gridseal=ROOT.parent/'wt-blindspot-internals/results/g_agreement/understand/e5354/PREPARED_INPUT_SEAL.json'
    # Prepared-input seal is stored separately; verify each selected member explicitly.
    s=read(gridseal); grid={}
    for bank in ('E36','E49','E54'):
        p=gridroot/(bank.lower()+'_items.json');assert sha(p)==s['files'][p.name]
        grid[bank]=sorted({x['feature'] for x in read(p)})
        sources['grid_'+bank]={'path':str(p),'sha256':sha(p),'seal_path':str(gridseal),'seal_sha256':sha(gridseal),'member':p.name}
    grid['W1']=grid['E36'];assert [len(grid[b]) for b in ('W1','E36','E49','E54')]==[7,7,8,2]
    labels={}
    for bank in ('W1','E36','E49'):
        p=R/'e52/primary'/bank
        labels[bank]=document('labels_'+bank,p/'ROW_LABELS.json',p/'LABEL_SEAL.json')['rows']
    w1dir=ROOT.parent/'blindspot-worktree/results/g_agreement/blindspot/w1/analysis'
    w1=document('W1_probe',w1dir/'metrics.json',w1dir/'ANALYSIS_SEAL.json')['rows']
    p=R/'e36/analysis_overnight149';e36=document('E36_probe',p/'METRICS.json',p/'ANALYSIS_SEAL.json')
    p=R/'e43/analysis_2026-10-26';e43=document('E43_native',p/'METRICS.json',p/'ANALYSIS_SEAL.json')['rows']
    p=ROOT/'cache/g_agreement/understand/e49/analysis_delivery'
    gates=document('E49_gates',p/'GATES.json',p/'ANALYSIS_SEAL.json')
    native=document('E49_native',p/'NATIVE_PRIMARY.json',p/'ANALYSIS_SEAL.json')
    rows=[]
    for bank in ('W1','E36','E49','E54'):
        for name in grid[bank]:
            x={'bank':bank,'row':name,'class':'semantic_state' if bank=='E54' else None,
                'J_label':'NOT EVALUABLE','J_label_method':'§169 amendment1 pursuit',
                'probe_auc':None,'oracle_unprompted_mention_rate':None,'column_sources':{}}
            cs=x['column_sources']
            if bank!='E54':
                matches=[(i,z) for i,z in enumerate(labels[bank]) if z['row']==name];assert len(matches)==1
                i,z=matches[0];x['class']='semantic_state' if z['class']=='tracked_state' else z['class'];x['J_label']=z['label']
                cs['J_label']=ref('labels_'+bank,f'/rows/{i}/label');cs['class']=ref('labels_'+bank,f'/rows/{i}/class')
                if z['class']=='tracked_state':x['class_mapping']='tracked_state -> semantic_state for E53 consumer; no membership change'
            else:
                cs['J_label']=unavailable('E54 primary sparse-pursuit labels have not been computed/sealed; no label inferred from reader outcomes')
                cs['class']={'registration':'E54 semantic-state rows; frozen ROW_DEFINITIONS.json'}
            if bank=='W1':
                found=[(i,z) for i,z in enumerate(w1) if z['feature']==name and z['reader']=='probe' and z['layer']==44];assert len(found)==1
                i,z=found[0];x['probe_auc']=z['true']['auroc'];cs['probe_auc']=ref('W1_probe',f'/rows/{i}/true/auroc')
                found=[(i,z) for i,z in enumerate(e43) if z['bank']=='w1' and z['row']==name and z['reader']=='oracle' and z['layer']==44 and z['arm']=='native' and z['primary']];assert len(found)==1
                i,z=found[0];x['oracle_unprompted_mention_rate']=z['mention_rate'];cs['oracle_unprompted_mention_rate']=ref('E43_native',f'/rows/{i}/mention_rate')
                x['native_support']={'unique_items':z['unique_items'],'E43_evaluable':z['evaluable'],'measure':'E43 sealed primary native mention; no filtering/recalculation'}
            elif bank=='E36':
                x['probe_auc']=e36['metrics'][name]['probe'];cs['probe_auc']=ref('E36_probe',f'/metrics/{name}/probe')
                cs['oracle_unprompted_mention_rate']=unavailable('No sealed E36 native mention summary delivered; asked AUROC/continuation not substituted')
            elif bank=='E49':
                x['probe_auc']=gates['rows'][name]['probe'];cs['probe_auc']=ref('E49_gates',f'/rows/{name}/probe')
                if name in native['rows']:
                    x['oracle_unprompted_mention_rate']=native['rows'][name]['oracle']['any_value_mention_rate']
                    cs['oracle_unprompted_mention_rate']=ref('E49_native',f'/rows/{name}/oracle/any_value_mention_rate')
                else:cs['oracle_unprompted_mention_rate']=unavailable('Excluded by sealed E49 mechanical gates; native outcomes not analysed or reopened')
            else:
                cs['probe_auc']=unavailable('E54 dev-fit probe is computed by its registered analysis, not by this map assembly')
                cs['oracle_unprompted_mention_rate']=unavailable('E54 native regex and blind judgments await its registered analysis')
            for field in ('probe_auc','oracle_unprompted_mention_rate'):
                assert x[field] is None or (math.isfinite(x[field]) and 0<=x[field]<=1)
            rows.append(x)
    out={'experiment':'E53 continuation map / E54 context','date':'2026-10-27',
        'issuer':'integrator','issuer_role':'Required destination-context issuer tag; not an attestation of completed Integrator review',
        'assembled_by':'W-lens','verification_status':'AWAITING_INTEGRATOR_CONTEXT_VERIFICATION_AND_SEAL',
        'source_seals':sources,'rows':rows,'no_new_reader_scoring':True,'no_forced_choice_substitution':True}
    with (HERE/'MAP.json').open('x') as f:json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
    (HERE/'MAP.sha256.json').write_text(json.dumps({'file':'MAP.json','sha256':sha(HERE/'MAP.json')},indent=2)+'\n')
    print('MAP assembled: 24 rows, sealed source columns; missing fields explicit')
if __name__=='__main__':main()
