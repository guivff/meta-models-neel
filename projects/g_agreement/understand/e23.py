"""E23 frozen inputs, controls and schedules under section117 clarification2."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .followup_packed import jsonl
from . import e23_sources as sources

SEED=20261025
BATCH=8
FEATURES=('table_column','list_index','prose_paren','python_string','prose_sentiment')
S_ROWS={'tb_tablecol':('table_column','first'), 'tb_paren':('prose_paren','inside'), 'bk_listidx':('list_index','early')}
ARMS=('F16','P32','Pfull','Mis','Swap')
UNIQUE_ARMS=('F16','P32','Pfull')
LAYERS=(44,40)
TARGET_PATHS=('capture','generation','asked_42_W1','asked_42_Suraj','asked_44_W1','asked_44_Suraj')
AR_PATHS=tuple(f'ar_{layer}_{arm}' for layer in LAYERS for arm in UNIQUE_ARMS)
PATHS=TARGET_PATHS+AR_PATHS
BRIEF='results/g_agreement/understand/e23/BRIEF_UNDERSTAND.e347b86a.md'
PLAN='results/g_agreement/understand/e23/PLAN.json'
CONTRACT={'F16':'in-contract','P32':'off-contract','Pfull':'off-contract','Mis':'mismatched following-span control','Swap':'secondary opposite-value following-span control'}


def donor_maps(items):
    """Mis has no value conditioning, including self draws; Swap is opposite-valued."""
    rng=np.random.default_rng(SEED); result={'Mis':{},'Swap':{}}
    for dataset,feature in sorted({(r['set'],r['feature']) for r in items}):
        pool=sorted((r for r in items if (r['set'],r['feature'])==(dataset,feature)),key=lambda r:r['id'])
        for r in pool:
            result['Mis'][r['id']]=pool[int(rng.integers(len(pool)))]['id']
    rng=np.random.default_rng(SEED)
    for r in sorted(items,key=lambda r:(r['set'],r['feature'],r['id'])):
        pool=sorted((q['id'] for q in items if q['set']==r['set'] and q['feature']==r['feature'] and q['y']!=r['y']))
        if not pool: raise ValueError('missing opposite-value donor')
        result['Swap'][r['id']]=pool[int(rng.integers(len(pool)))]
    return result


def chunks(ix): return [ix[j:j+BATCH] for j in range(0,len(ix),BATCH)]


def schedule(items):
    plan={k:[] for k in PATHS}
    si=[i for i,r in enumerate(items) if r['set']=='S']
    plan['capture']=chunks(si)
    for n in sorted({len(items[i]['ids']) for i in si}):
        plan['generation']+=chunks([i for i in si if len(items[i]['ids'])==n])
    for key in AR_PATHS: plan[key]=chunks(list(range(len(items))))
    for key in TARGET_PATHS[2:]:
        for dataset in ('O','S'):
            plan[key]+=chunks([i for i,r in enumerate(items) if r['set']==dataset and r['feature']=='table_column' and r['split']=='test'])
    return plan


def assemble_texts(items,continuations,donors):
    if set(continuations)!={r['id'] for r in items} or any(len(c['ids'])!=16 for c in continuations.values()):
        raise ValueError('all F16 continuations must be complete before AR assembly')
    return {arm:[continuations[donors[arm][r['id']]]['text'] if arm in ('Mis','Swap') else
                 continuations[r['id']]['text'] if arm=='F16' else r[arm] for r in items] for arm in ARMS}


def prepare(a):
    import torch
    from transformers import AutoTokenizer
    audit=sources.audit(a.upstream)
    if not audit['launch_allowed']: raise ValueError('E23 source gate failed')
    bank=a.w1/'w1-bank-v2'; target=a.w1/'w1-assembled/target'
    verify(bank,'INPUT_SEAL.json'); verify(target); verify(a.w1_analysis,'ANALYSIS_SEAL.json'); verify(a.e1b)
    private=bank/'items.DO_NOT_STAGE.jsonl'
    if sha(private)!=read(bank/'manifest.json')['files'][private.name]: raise ValueError('W1 label seal mismatch')
    previous=read(ROOT/'results/g_agreement/understand/e1b/PACKED_INPUT_RECEIPT.json')
    if read(a.e1b/'provenance.json')['input_seal_sha256']!=previous['seal_sha256']: raise ValueError('E1b lineage mismatch')
    templates=read(bank/'templates.json'); tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    if sha(a.tokenizer/'tokenizer.json')!=read(ROOT/'projects/g_agreement/manifest/assets.json')['target']['files_needed']['tokenizer.json_sha256']:
        raise ValueError('tokenizer pin mismatch')
    old_cont={r['id']:r for r in rows(a.e1b/'continuations.jsonl')}
    items=[]; continuations=[]
    original=[r for r in rows(private) if r['feature'] in FEATURES and r['split'] in ('dev','test')]
    for r in sorted(original,key=lambda r:(r['feature'],r['split'],r['id'])):
        q={**r,'id':'O|'+r['id'],'source_id':r['id'],'set':'O','y':int(r['value']==templates[r['feature']]['values'][0])}
        items.append(q); continuations.append({**old_cont[r['id']],'id':q['id']})
    suraj=[]
    for path,pin,blob,feature in sources.FILES:
        if feature:
            for r in read(a.upstream/path)['items']:
                f,positive=S_ROWS[feature]
                q={**r,'id':'S|'+r['id'],'source_id':r['id'],'source_feature':feature,'feature':f,
                   'set':'S','split':'dev' if r['split']=='mine' else 'test','original_split':r['split'],'y':int(r['value']==positive)}
                suraj.append(q)
    items+=sorted(suraj,key=lambda r:(r['feature'],r['split'],r['id']))
    if len(items)!=1440 or len({r['id'] for r in items})!=1440: raise ValueError('exact 840 O +600 S grid required')
    for dataset,features,counts in [('O',FEATURES,(84,84)),('S',('table_column','list_index','prose_paren'),(40,160))]:
        for f in features:
            rr=[r for r in items if r['set']==dataset and r['feature']==f]
            if [sum(r['split']==s for r in rr) for s in ('dev','test')]!=list(counts): raise ValueError('split mismatch')
            if {r['cluster'] for r in rr if r['split']=='dev'} & {r['cluster'] for r in rr if r['split']=='test'}: raise ValueError('cluster leakage')
    for r in items:
        r['P32']=tok.decode(r['ids'][-32:],skip_special_tokens=False,clean_up_tokenization_spaces=False)
        r['Pfull']=r['text']
    donors=donor_maps(items)
    a.out.mkdir(parents=True,exist_ok=False)
    a.private.mkdir(parents=True,exist_ok=False)
    jsonl(a.private/'labels.DO_NOT_STAGE.jsonl',[{k:r[k] for k in ('id','set','feature','split','cluster','y')} for r in items])
    public=[{k:r[k] for k in ('id','source_id','set','feature','split','cluster','ids','P32','Pfull')} for r in items]
    jsonl(a.out/'items.input.jsonl',public); jsonl(a.out/'O.continuations.jsonl',continuations)
    dump(a.out/'donors.json',donors); dump(a.out/'units.json',schedule(public))
    dump(a.out/'pairs.json',{'W1':templates['table_column']['olens'],'Suraj':[['- column one','- column five']]})
    order=read(target/'items.order.json'); ix={k:i for i,k in enumerate(order)}
    if read(target/'provenance.target.json')['input_seal_sha256']!=sha(bank/'INPUT_SEAL.json'): raise ValueError('target lineage mismatch')
    for layer in (42,44):
        arr=np.load(target/f'acts{layer}.npy',mmap_mode='r',allow_pickle=False)
        np.save(a.out/f'O.acts{layer}.npy',np.asarray(arr[[ix[r['source_id']] for r in items if r['set']=='O']]),allow_pickle=False)
    vectors=np.load(a.w1_analysis/'probe_directions.npz',allow_pickle=False)
    meta=read(a.w1_analysis/'probe_directions.json')
    frozen={r['feature']:vectors[r['array_prefix']+'__unit'] for r in meta['rows'] if r['layer']==44 and r['feature'] in FEATURES}
    if set(frozen)!=set(FEATURES): raise ValueError('frozen native44 W1 directions missing')
    np.savez(a.out/'W1.directions.npz',**frozen)
    si=[r for r in items if r['set']=='S']; parity={l:{} for l in (40,42,44)}
    for path,blob in sources.PARITY_FILES:
        obj=torch.load(a.upstream/path,map_location='cpu',weights_only=True)
        for l,x in obj['acts'].items():
            for key,v in zip(obj['ids'],x): parity[int(l)]['S|'+key]=v.float().numpy()
    for l in parity:
        if set(parity[l])!={r['id'] for r in si}: raise ValueError('parity IDs mismatch')
        np.save(a.out/f'S.parity{l}.npy',np.stack([parity[l][r['id']] for r in si]),allow_pickle=False)
    # Timing-only inputs are dev-derived and extended to production maximum length.
    dev=max((r for r in si if r['split']=='dev'),key=lambda r:len(r['ids']))
    target_max=max(len(r['ids']) for r in si)
    pilot={**{k:dev[k] for k in ('id','feature','ids')},'id':'timing-only-dev','split':'dev'}
    neutral_ids=tok.encode(' neutral',add_special_tokens=False)
    pilot['ids']=(pilot['ids']+neutral_ids*target_max)[:target_max]
    bounds={'F16':64,**{arm:max(len(tok.encode(r[arm],add_special_tokens=False)) for r in items) for arm in ('P32','Pfull')}}
    neutral={}
    for arm,length in bounds.items():
        value='A neutral passage about ordinary daily activities. '
        while len(tok.encode(value,add_special_tokens=False))<length: value+='neutral '
        neutral[arm]=value
    dump(a.out/'pilot.json',{'target':[pilot for _ in range(BATCH)],'AR_neutral_text':neutral,
                            'maximum_AR_token_length_bound':bounds,'target_token_length':target_max,
                            'no_pilot_output_is_scored':True})
    provenance={'authority_commit':'e347b86a','clarification2':'1642d63e','tokenizer_json_sha256':sha(a.tokenizer/'tokenizer.json'),
        'source_audit_sha256':sha(ROOT/'results/g_agreement/understand/e23/SURAJ_FILES.e347b86a.json'),
        'private_sha256':sha(a.private/'labels.DO_NOT_STAGE.jsonl'),'W1_bank_seal_sha256':sha(bank/'INPUT_SEAL.json'),
        'W1_target_seal_sha256':sha(target/'SCORE_SEAL.json'),'W1_analysis_seal_sha256':sha(a.w1_analysis/'ANALYSIS_SEAL.json'),
        'E1b_continuation_seal_sha256':sha(a.e1b/'SCORE_SEAL.json'),'seed':SEED,'contract':CONTRACT,
        'controls':'Mis independent of value; Swap opposite; both reuse exact donor F16 outputs, no refit',
        'donor_pool':'same row and set, both frozen splits; Mis includes self with replacement',
        'M2_O':'fivefold CV over 84 test items, grouped W1 clusters','M2_S':'fivefold CV over all200, item clusters',
        'T_O':'same grouped folds as M2','T_S':'mine40 fit, select160 test'}
    dump(a.out/'provenance.json',provenance)
    seal(a.out,[p.name for p in a.out.iterdir() if p.is_file()],'E23_INPUTS_FROZEN')
    (a.out/'SCORE_SEAL.json').rename(a.out/'INPUT_SEAL.json')
    dump(a.private/'provenance.json',{'input_seal_sha256':sha(a.out/'INPUT_SEAL.json'),'labels_sha256':provenance['private_sha256']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('upstream','w1','w1-analysis','e1b','tokenizer','out','private'): p.add_argument('--'+k,type=Path,required=True)
    prepare(p.parse_args())
