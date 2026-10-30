"""Reject S2 provenance/coverage errors before the CPU-only W1 projection join."""
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.blindspot import ar_tests as AR, protocol as P, w2_cpu as W


def fixture(tmp_path):
    texts=tmp_path/'texts';texts.mkdir();rec=tmp_path/'rec';rec.mkdir()
    definitions={f:{'row_class':'state-like','values':['A','B'],'descriptions':['A state','B state']} for f in ('w1_row','s79_row')}
    records,labels=AR.freeze_text_records(definitions)
    label_file=tmp_path/'labels.DO_NOT_STAGE.jsonl';P.jsonl(label_file,labels)
    P.jsonl(texts/'texts.input.jsonl',records);P.dump(texts/'definitions.json',definitions)
    P.dump(texts/'provenance.json',{'labels_sha256':P.sha(label_file)})
    P.seal(texts,['texts.input.jsonl','definitions.json','provenance.json'],'INPUTS_FROZEN_TEST')
    np.save(rec/'recon.npy',np.ones((len(records),2),np.float32));P.dump(rec/'ids.json',[r['id'] for r in records])
    P.dump(rec/'provenance.json',{'text_seal_sha256':P.sha(texts/'INPUT_SEAL.json'),'stage':'S2','whitener_sha256':'178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'})
    P.seal(rec,['recon.npy','ids.json','provenance.json'],'SCORES_SEALED_TEST')
    return texts,rec,label_file


def test_sealed_s2_batch_can_be_reused_without_model_loading(tmp_path):
    texts,rec,labels=fixture(tmp_path)
    records,label_rows,definitions,vectors=W.sealed_s2(texts,rec,labels)
    assert len(records)==len(label_rows)==len(vectors)==80
    assert len([r for r in records if r['feature']=='w1_row'])==40
    assert set(definitions)=={'w1_row','s79_row'}


@pytest.mark.parametrize('bad',['missing_seal','reordered_ids','wrong_text_seal','missing_vector','labels','stage'])
def test_reuse_rejects_unsealed_or_misaligned_outputs(tmp_path,bad):
    texts,rec,labels=fixture(tmp_path)
    if bad=='missing_seal': (rec/'SCORE_SEAL.json').unlink()
    elif bad=='reordered_ids': P.dump(rec/'ids.json',list(reversed(AR._read(rec/'ids.json'))))
    elif bad=='wrong_text_seal': P.dump(rec/'provenance.json',{'text_seal_sha256':'wrong'})
    elif bad=='missing_vector': np.save(rec/'recon.npy',np.ones((79,2),np.float32))
    elif bad=='stage':
        provenance=AR._read(rec/'provenance.json');provenance['stage']='other';P.dump(rec/'provenance.json',provenance)
    else: labels.write_text(labels.read_text()+'\n')
    if bad not in ('missing_seal','labels'):
        P.seal(rec,['recon.npy','ids.json','provenance.json'],'SCORES_SEALED_TEST')
    with pytest.raises((ValueError,FileNotFoundError)):
        W.sealed_s2(texts,rec,labels)


def test_complete_cpu_job_reuses_all40_w1_rows_from_larger_s2_batch(tmp_path):
    bank,target,w1,texts,reconstruction=[tmp_path/n for n in ('bank','target','w1','texts','reconstruction')]
    for d in (bank,target,w1,texts,reconstruction):d.mkdir()
    items,labels,h,templates,cells,metadata,arrays=[],[],[],{},{},[],{}
    for i in range(40):
        f=f'f{i:02d}';templates[f]={'kind':'binary','class':'semantic' if i%2 else 'state-like',
            'score_orientation':'value_A_positive','values':['A','B'],
            'olens':[[f'- {f} A',f'- {f} B'],[f'- Now {f} A',f'- Now {f} B']]}
        for split in ('dev','test'):
            for value in ('A','B'):
                iid=f'{f}:{split}:{value}';items.append({'id':iid,'feature':f,'ids':[1,2]})
                labels.append({'id':iid,'feature':f,'split':split,'value':value,'cluster':split})
                h.append([1. if value=='A' else -1.,0.])
        cells[f]={'feature':f,'reader':'olens','layer':44,'status':'EVALUABLE','probe_auroc':1.,'true':{'auroc':.4+i*.01}}
        prefix=f+'__L44';metadata.append({'feature':f,'layer':44,'array_prefix':prefix,'fit_split':'dev',
            'orientation_flipped':False,'positive_value':'A','negative_value':'B','test_class_mean_projection_gap':2.})
        arrays[prefix+'__unit']=np.array([1.,0.]);arrays[prefix+'__coef']=np.array([2.,0.])
    label_file=tmp_path/'w1_labels.DO_NOT_STAGE.jsonl';P.jsonl(label_file,labels)
    P.jsonl(bank/'items.input.jsonl',items);P.dump(bank/'templates.json',templates)
    P.dump(bank/'provenance.json',{'labels_sha256':P.sha(label_file)})
    P.seal(bank,['items.input.jsonl','templates.json','provenance.json'],'INPUTS_FROZEN_TEST')
    np.save(target/'acts44.npy',np.asarray(h,np.float32));P.dump(target/'items.order.json',[r['id'] for r in items])
    P.dump(target/'provenance.target.json',{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
    P.seal(target,['acts44.npy','items.order.json','provenance.target.json'],'SCORES_SEALED_TEST')
    P.dump(w1/'metrics.json',{'rows':list(cells.values()),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'reader_seals':[P.sha(target/'SCORE_SEAL.json')],'w1':{'status':'NOT MET'}})
    P.dump(w1/'probe_directions.json',{'fit_split':'dev','rows':metadata});np.savez(w1/'probe_directions.npz',**arrays)
    P.dump(w1/'ANALYSIS_SEAL.json',{'status':'ANALYSIS_SEALED_TEST','files':{n:P.sha(w1/n) for n in ('metrics.json','probe_directions.json','probe_directions.npz')}})
    defs=AR.definitions_from_bank(bank);defs['extra_s79']={'row_class':'state-like','values':['yes','no'],'descriptions':['yes','no']}
    records,text_labels=AR.freeze_text_records(defs);text_label_file=tmp_path/'s2_labels.DO_NOT_STAGE.jsonl';P.jsonl(text_label_file,text_labels)
    P.jsonl(texts/'texts.input.jsonl',records);P.dump(texts/'definitions.json',defs)
    P.dump(texts/'provenance.json',{'labels_sha256':P.sha(text_label_file)})
    P.seal(texts,['texts.input.jsonl','definitions.json','provenance.json'],'INPUTS_FROZEN_TEST')
    rec=[]
    for r in text_labels:
        scale=.1+int(r['feature'][1:])*.01 if r['feature'].startswith('f') else 99.
        rec.append([scale if r['value'] else -scale,0.])
    np.save(reconstruction/'recon.npy',np.asarray(rec,np.float32));P.dump(reconstruction/'ids.json',[r['id'] for r in records])
    P.dump(reconstruction/'provenance.json',{'text_seal_sha256':P.sha(texts/'INPUT_SEAL.json'),'stage':'S2','whitener_sha256':'178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'})
    P.seal(reconstruction,['recon.npy','ids.json','provenance.json'],'SCORES_SEALED_TEST')
    out=tmp_path/'analysis'
    W.run(SimpleNamespace(bank=bank,target=target,w1=w1,texts=texts,reconstruction=reconstruction,
        labels=label_file,text_labels=text_label_file,out=out))
    result=AR._read(out/'metrics.w2.json')
    assert len(result['rows'])==40 and result['n_W1_texts_reused']==1600
    assert result['w1_status']=='NOT MET' and result['W2']['status']=='CONFIRMED'
    assert result['W2']['correlation']['rho']==pytest.approx(1.)
    assert all(r['n_texts']==40 and r['denominator']==2. for r in result['rows'])
    assert AR._read(out/'run.json')['model_forwards']==0
    P.verify(out,'SCORE_SEAL.json')
