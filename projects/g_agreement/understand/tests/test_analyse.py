import json
from pathlib import Path

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import analyse as C
from projects.g_agreement.understand.inputs import prepare_inputs, load_inputs
from projects.g_agreement.understand.tests.test_inputs import upstream


def make_scores(upstream,experiment,phases):
    prepare_inputs(**upstream)
    root=upstream["out"].parent/(experiment+"-scores");root.mkdir()
    statuses={p:"NOT_RUN_OR_INCOMPLETE" for p in C.PHASES[experiment]}
    allnames=[]
    for phase in phases:
        primary=upstream["out"]/('e9' if phase=='target' else experiment.lower())
        data=load_inputs(primary);feature=data["rows"][0]["feature"]
        ids=[i["id"] for i in data["items"] if i["feature"]==feature]
        directory=root/phase;directory.mkdir()
        n=len(ids)
        if experiment=='E3':
            y=np.tile([1.,0.],n//2)
            h=np.stack([2*y-1,np.zeros(n),np.ones(n)],axis=-1).astype(np.float32)
            values={'residuals':np.broadcast_to(h[:,None,None,:],(n,1,2,3)),
                    'input_stage':np.broadcast_to(h[:,None,:],(n,2,3))}
        elif phase=='target':
            values={'derivatives':np.full((n,7),.25,dtype=np.float32),
                    'rms':np.full(n,.25,dtype=np.float32),'l2':np.full(n,.25*np.sqrt(7),dtype=np.float32)}
        else:
            values={'gradients':np.tile(np.array([1.,0.,0.],dtype=np.float32),(n,1)),
                    'scores':np.full(n,-.125,dtype=np.float32)}
        arrays={}
        for key,value in values.items():
            name=feature+'.'+key+'.npy';np.save(directory/name,value);arrays[key]=name
        record={'feature':feature,'reader':phase,'status':'COMPLETE','n':n,'item_ids':ids,
                'arrays':arrays,'array_sha256':{k:P.sha(directory/name) for k,name in arrays.items()},
                'layers':[0],'positions':['injection','preanswer'],'target_objective':'toy exact J u'}
        P.dump(directory/'index.json',[record])
        P.dump(directory/'provenance.json',{'experiment':experiment,'phase':phase,
                'input_seal_sha256':P.sha(primary/'INPUT_SEAL.json'),
                'population_status':'PARTIAL','source_files':{'synthetic_fixture.py':'0'*64}})
        names=list(arrays.values())+['index.json','provenance.json']
        P.seal(directory,names,'SCORES_SEALED_EXPLORATORY_'+experiment)
        allnames.extend([phase+'/'+n for n in names]+[phase+'/SCORE_SEAL.json'])
        statuses[phase]='SEALED'
    primary_sha=P.sha(upstream['out']/experiment.lower()/'INPUT_SEAL.json')
    inputseals={'primary':primary_sha}
    if experiment=='E4':inputseals['e9']=P.sha(upstream['out']/'e9/INPUT_SEAL.json')
    P.dump(root/'provenance.json',{'experiment':experiment,'input_seal_sha256':primary_sha,
              'input_seals':inputseals,'phases':statuses,'status':'PARTIAL'})
    P.seal(root,allnames+['provenance.json'],'SCORES_SEALED_EXPLORATORY_'+experiment)
    return root


def test_e3_partial_run_keeps_all75_rows_and_oof_cache(upstream,tmp_path):
    scores=make_scores(upstream,'E3',['olens'])
    out,cache=tmp_path/'result',tmp_path/'analysis-cache'
    result=C.analyze('E3',upstream['out'],scores,upstream['out']/'labels.DO_NOT_STAGE.jsonl',out,cache)
    metrics=json.loads((out/'metrics.json').read_text())
    assert result['rows']==75 and result['evaluable_layer_cells']==2
    assert len(metrics['rows'])==75
    assert sum(r['status']=='NOT_RUN_OR_INCOMPLETE' for r in metrics['rows'])==74
    assert len(metrics['named_stages'])==2
    assert len(metrics['cells'])==50
    assert all(c['auroc']==1. for c in metrics['cells'] if c['status']=='COMPLETE')
    assert sum(c['auroc'] is None for c in metrics['cells'])==48
    assert all('oof_scores' not in c for c in metrics['cells'])
    assert len(list(cache.glob('*.oof.npz')))==1
    P.verify(out,'ANALYSIS_SEAL.json')
    assert (out/'RESULTS.md').read_text().startswith('Prediction:')


def test_e4_partial_run_keeps_all_rows_native_parity_and_e9(upstream,tmp_path):
    scores=make_scores(upstream,'E4',['olens','target'])
    out,cache=tmp_path/'result',tmp_path/'analysis-cache'
    result=C.analyze('E4',upstream['out'],scores,upstream['out']/'labels.DO_NOT_STAGE.jsonl',out,cache)
    metrics=json.loads((out/'metrics.json').read_text())
    assert result=={'experiment':'E4','rows':75,'complete_rows':1,'e9_rows':40,'e9_complete':1}
    record=next(r for r in metrics['alignment_rows'] if r['status']=='COMPLETE')
    assert record['native_layer']==44
    assert record['mean_abs_cos']==1
    assert record['score_parity_n']==84
    assert record['score_parity_max_absolute_difference']==0
    assert len(metrics['e9_target_rows'])==40
    e9=next(r for r in metrics['e9_target_rows'] if r['status']=='COMPLETE')
    assert e9['mean_rms']==.25
    assert e9['mean_l2']==pytest.approx(.25*np.sqrt(7))
    assert Path(e9['raw_derivatives_file']).exists()
    svd=metrics['receptive_subspaces']['olens']
    assert svd['population_status']=='PARTIAL_EXPLORATORY_POOL'
    assert len(svd['missing_features'])==24 and svd['numerical_rank']==1
    assert len(metrics['receptive_subspaces']['nla']['rows'])==75
    assert all(r['fraction_inside'] is None for r in metrics['receptive_subspaces']['nla']['rows'])
    P.verify(out,'ANALYSIS_SEAL.json')


def test_aggregate_tamper_prevents_any_label_join(upstream,tmp_path,monkeypatch):
    scores=make_scores(upstream,'E3',['olens'])
    with (scores/'olens/index.json').open('a') as f:f.write(' ')
    calls=[]
    monkeypatch.setattr(C,'join_labels',lambda *args:calls.append(args))
    with pytest.raises(ValueError,match='seal mismatch'):
        C.analyze('E3',upstream['out'],scores,tmp_path/'unread-labels',tmp_path/'result',tmp_path/'cache')
    assert calls==[]
    assert not (tmp_path/'result').exists()


def test_phase_seal_input_mismatch_prevents_labels_even_if_aggregate_resealed(upstream,tmp_path,monkeypatch):
    scores=make_scores(upstream,'E3',['olens'])
    path=scores/'olens/provenance.json';record=json.loads(path.read_text());record['input_seal_sha256']='wrong';P.dump(path,record)
    phase=json.loads((scores/'olens/SCORE_SEAL.json').read_text());P.seal(scores/'olens',list(phase['files']),'SCORES_SEALED_EXPLORATORY_E3')
    outer=json.loads((scores/'SCORE_SEAL.json').read_text());P.seal(scores,list(outer['files']),'SCORES_SEALED_EXPLORATORY_E3')
    calls=[];monkeypatch.setattr(C,'join_labels',lambda *args:calls.append(args))
    with pytest.raises(ValueError,match='phase/input binding'):
        C.analyze('E3',upstream['out'],scores,tmp_path/'unread-labels',tmp_path/'result',tmp_path/'cache')
    assert calls==[]


def test_complete_phase_requires_full_grid_before_labels(upstream,tmp_path,monkeypatch):
    scores=make_scores(upstream,'E3',['olens'])
    path=scores/'olens/provenance.json';record=json.loads(path.read_text());record.pop('population_status');P.dump(path,record)
    phase=json.loads((scores/'olens/SCORE_SEAL.json').read_text());P.seal(scores/'olens',list(phase['files']),'SCORES_SEALED_EXPLORATORY_E3')
    outer=json.loads((scores/'SCORE_SEAL.json').read_text());P.seal(scores,list(outer['files']),'SCORES_SEALED_EXPLORATORY_E3')
    calls=[];monkeypatch.setattr(C,'join_labels',lambda *args:calls.append(args))
    with pytest.raises(ValueError,match='full row grid'):
        C.analyze('E3',upstream['out'],scores,tmp_path/'unread-labels',tmp_path/'result',tmp_path/'cache')
    assert calls==[]


def test_cpu_analysis_logging_success_and_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(C,'analyze',lambda **kwargs:{'ok':True})
    assert C.run_logged({'experiment':'E3'},log_root=tmp_path)=={'ok':True}
    def fail(**kwargs):raise ValueError('synthetic failure')
    monkeypatch.setattr(C,'analyze',fail)
    with pytest.raises(ValueError,match='synthetic failure'):
        C.run_logged({'experiment':'E4'},log_root=tmp_path)
    records=P.rows(tmp_path/'results/g_agreement/compute.jsonl')
    assert [r['status'] for r in records]==['COMPLETE','FAILED']
    assert all(r['gpu_hours']==0 and r['wall_s']>=0 and r['seed']==20261024 for r in records)
    assert 'e3_cpu_analysis' in (tmp_path/'results/g_agreement/log.md').read_text()


@pytest.mark.parametrize('lost_key', ['residuals', 'input_stage'])
def test_lost_array_reports_only_affected_cells_missing(upstream,tmp_path,monkeypatch,lost_key):
    from projects.g_agreement.understand import custody
    scores=make_scores(upstream,'E3',['olens'])
    record=json.loads((scores/'olens/index.json').read_text())[0]
    lost='olens/'+record['arrays'][lost_key]
    monkeypatch.setattr(custody,'E3_LOST_ARRAYS',(lost,))
    (scores/lost).unlink()
    out=tmp_path/'result'
    C.analyze('E3',upstream['out'],scores,upstream['out']/'labels.DO_NOT_STAGE.jsonl',out,tmp_path/'cache',True)
    metrics=json.loads((out/'metrics.json').read_text())
    cells=[c for c in metrics['cells'] if c['row']==record['feature']]
    stages=metrics['named_stages']
    assert all(c['status']==('MISSING' if lost_key=='residuals' else 'COMPLETE') for c in cells)
    assert all(c['status']==('MISSING' if lost_key=='input_stage' else 'COMPLETE') for c in stages)
    assert lost in (out/'RESULTS.md').read_text()
    P.verify(out,'ANALYSIS_SEAL.json')


def test_missing_exception_still_rejects_corrupt_present_array(upstream,tmp_path,monkeypatch):
    from projects.g_agreement.understand import custody
    scores=make_scores(upstream,'E3',['olens'])
    record=json.loads((scores/'olens/index.json').read_text())[0]
    lost='olens/'+record['arrays']['residuals']
    monkeypatch.setattr(custody,'E3_LOST_ARRAYS',(lost,))
    (scores/lost).unlink()
    with (scores/'olens'/record['arrays']['input_stage']).open('ab') as f:f.write(b'bad')
    with pytest.raises(ValueError,match='seal mismatch'):
        C.analyze('E3',upstream['out'],scores,tmp_path/'never-read-labels',tmp_path/'result',tmp_path/'cache',True)
