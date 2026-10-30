"""Bind the sealed separate E62 placebo ladder only; no scores or reader outcomes."""
from pathlib import Path
from datetime import datetime
import sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CHANNEL=ROOT/'results/g_agreement/understand/e57/jlens'
sys.path.insert(0,str(CHANNEL))
from cpu_job import read,dump,sha,verify,validate_units,committed


def bind():
    source=ROOT/'cache/g_agreement/understand/e62p/capture_delivery';receipt=read(source/'DELIVERY.json')
    verify(source,receipt['files'])
    assert receipt['issuer']=='integrator' and receipt['experiment']=='E62P' and receipt['reader_outputs_included']==0 and receipt['probe_scores_included']==0
    assert receipt['R3b']=='block-44 capture (test all-position fp16 + read points + CPU class means) before any reader output exists'
    cap=read(source/'CAPTURE_SEAL.json');cpu=read(source/'CPU_SEAL.json')
    assert sha(source/'CAPTURE_SEAL.json')==receipt['capture_seal_sha256']==cpu['capture_seal_sha256']
    assert cap['pod_id']==receipt['pod_id'] and cpu['files']['CLASS_MEANS.npz']==sha(source/'CLASS_MEANS.npz')
    manifest=ROOT/'results/g_agreement/understand/e62/placebo/FREEZE_MANIFEST.json';committed(manifest)
    m=read(manifest);folder=Path(m['bank_directory']);seal=read(folder/'BANK_SEAL.json')
    assert sha(folder/'BANK_SEAL.json')==m['bank_seal_sha256']
    private=folder/'items.PRIVATE.json';assert sha(private)==seal['files'][private.name]==cpu['private_items_sha256']
    records=read(private);test={r['id']:r for r in records if r['split']=='test'}
    order=read(source/'test.order.json');h=np.load(source/'acts44.test.npy',allow_pickle=False)
    assert len(order)==len(set(order)) and set(order)==set(test)
    assert h.shape==(len(order),5120) and np.isfinite(h).all()
    expected={f'S{s}_L{r}p' for s in range(1,6) for r in (1,2,4)}
    assert {r['feature'] for r in test.values()}==expected
    means=np.load(source/'CLASS_MEANS.npz',allow_pickle=False)
    for row in sorted(expected):
        if row.startswith('S6_'):continue
        for value in (1,0):
            ix=[k for k,i in enumerate(order) if test[i]['feature']==row and test[i]['label']==value]
            assert len(ix)==42
            observed=h[ix].mean(axis=0,dtype=np.float64).astype(np.float32)
            assert np.array_equal(observed,means[row+'__test__'+('A' if value else 'B')])
    # Repackage exact bytes under the existing channel's capture-seal interface.
    bound=ROOT/'cache/g_agreement/understand/e62_placebo/jlens/bound_capture';bound.mkdir(parents=True,exist_ok=False)
    import shutil
    shutil.copyfile(source/'acts44.test.npy',bound/'acts44.npy');shutil.copyfile(source/'test.order.json',bound/'order.json')
    dump(bound/'CAPTURE_SEAL.json',{'experiment':'E62_PLACEBO','scope':'15 placebo A/B cells',
        'normalizer':'W-lens exact-byte filename adapter','original_delivery_path':str(source/'DELIVERY.json'),
        'original_delivery_sha256':sha(source/'DELIVERY.json'),'original_capture_seal_sha256':sha(source/'CAPTURE_SEAL.json'),
        'files':{n:sha(bound/n) for n in ('acts44.npy','order.json')}})
    original={};source_paths=[manifest,private,folder/'BANK_SEAL.json',source/'DELIVERY.json']
    for bank in ('E56','E57'):
        p=CHANNEL/(bank+'_INPUT_PLAN.json');committed(p);plan=read(p)
        original[bank]={u['source_row']:u for u in plan['units']};source_paths.append(p)
    from transformers import AutoTokenizer
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tr=read(HERE.parent/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer'];assert sha(tr['path'])==tr['sha256'];source_paths.append(Path(tr['path']))
    tok=AutoTokenizer.from_pretrained(Path(tr['path']).parent,local_files_only=True)
    evalwords=['evaluation','grader','judge','benchmark','test','score']
    evalsets=[{'name':w,'token_ids':token_variants(tok,[w])} for w in evalwords]
    units=[]
    for row in sorted(expected):
        ids=sorted(i for i,r in test.items() if r['feature']==row);binary=not row.startswith('S6_');tokens={};groups={}
        for i in ids:
            r=test[i]
            if binary:
                u=original[r['source_bank']][r['source_feature']]
                tokens[i]=u['value_token_ids'][r['source_id']];groups[i]={}
            else:tokens[i]=[[],[]];groups[i]={'eval_mentions':evalsets}
        units.append({'id':row,'source_row':row,'condition':row,'binary':binary,'item_ids':ids,'value_token_ids':tokens,'descriptive_token_sets':groups})
    validate_units(units,records,order)
    def ref(p):return {'path':str(p),'sha256':sha(p),'member':p.name}
    plan={'experiment':'E62_PLACEBO','scope':'PLACEBO_BANK_15_AB','layer':44,'split':'test','bank_seal':{'path':str(folder/'BANK_SEAL.json'),'sha256':sha(folder/'BANK_SEAL.json')},
        'capture_seal':{'path':str(bound/'CAPTURE_SEAL.json'),'sha256':sha(bound/'CAPTURE_SEAL.json')},'records':ref(private),
        'activations':ref(bound/'acts44.npy'),'order':ref(bound/'order.json'),'units':units,
        'value_sources':[{'path':str(p),'sha256':sha(p)} for p in source_paths],
        'value_word_policy':'Exact frozen E56/E57 source-row/item A/B token sets reused at every rung; S6 descriptive six registered evaluation words only; no outcomes'}
    target=CHANNEL/'E62_PLACEBO_INPUT_PLAN.json';assert not target.exists();dump(target,plan)
    normal=ROOT/'cache/g_agreement/understand/e52/r3b';normal.mkdir(parents=True,exist_ok=True)
    dump(normal/'E62_PLACEBO_DELIVERY.json',{'issuer':'integrator','normalizer':'W-lens from original Integrator receipt and Guiv custody order',
        'experiment':'E62_PLACEBO','status':'VERIFIED_CAPTURE_ONLY','original_delivery_path':str(source/'DELIVERY.json'),
        'original_delivery_sha256':sha(source/'DELIVERY.json'),'delivered_epoch':datetime.fromisoformat(receipt['delivered_utc'].replace('Z','+00:00')).timestamp(),
        'bank_seal_sha256':sha(folder/'BANK_SEAL.json'),'capture_seal_sha256':sha(bound/'CAPTURE_SEAL.json'),
        'reader_outputs_opened_at_registration':False,'reader_outputs_opened_before_forecast':False,'readers_held_until_forecast_commit':True,
        'custody_authority':'original receipt says before any reader output exists; Guiv requires forecast commit before readers start'})
    print('E62_PLACEBO original capture bound:1260 test items,15 binary cells,0 exclusions; no reader outcomes or J scores')

if __name__=='__main__':bind()
