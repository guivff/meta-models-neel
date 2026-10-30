"""TH-2-F1 data/probe preparation (BRIEF_R §17); never writes shared cache.

Preflight only: python -m projects.g_agreement.r_bench.th2_f1_data preflight
After coverage is communicated: ... th2_f1_data probes --coverage-reviewed --jobs 4
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import pickle
import time
import numpy as np
import pandas as pd
from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import interim as I
from projects.g_agreement.r_bench.th2_preflight import READERS, _file_sha, _normalize, _sha, _stat

SEED = 20261022
TOKENIZER = Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
BASE_FEATURES = ['po_margin','probe_margin','log_token_count','log_char_count']


def _paths(root):
    root=Path(root).resolve(); p=A.Paths(root); p.dataset=root/'projects/g_agreement/dataset'
    out=root/'results/g_agreement/r/i2'; local=root/'.th2_f1_cache'
    out.mkdir(parents=True,exist_ok=True); local.mkdir(parents=True,exist_ok=True)
    return root,p,out,local


def _bool(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    if isinstance(v,str): return v.lower()=='true'
    return bool(v) if not pd.isna(v) else False


def eligible_facts(rows):
    n=rows.groupby(['dataset','half','label']).size()
    return {ds:all(n.get((ds,h,y),0)>=10 for h in ['calibration','endpoint'] for y in [0,1]) for ds in rows.dataset.unique()}


def select_pool_indices(index_ids, bank_by_id, all_test_hashes, finite=None):
    """Remove globally held-out documents before any balanced sampling or fitting."""
    finite=np.ones(len(index_ids),bool) if finite is None else np.asarray(finite,bool)
    out=[]
    for i,iid in enumerate(index_ids):
        row=bank_by_id[iid]
        if row['split']=='pool' and row['text_hash'] not in all_test_hashes and finite[i]: out.append(i)
    return np.asarray(out,dtype=int)


def symmetric_candidate_frequency(token_ids, counts, vocab_size):
    """Mean and absolute difference of candidate-average add-one token surprisal."""
    denom=sum(counts.values())+vocab_size
    values=[float(np.mean([np.log(denom)-np.log(counts.get(int(t),0)+1) for t in ids])) if len(ids) else np.nan for ids in token_ids]
    if not np.isfinite(values).all(): return np.nan,np.nan
    return float(np.mean(values)),float(abs(values[0]-values[1]))


def _snapshot(paths, root):
    return {str(Path(p).resolve()):{'sha256':_file_sha(p),**_stat(p)} for p in dict.fromkeys(paths)}


def _check_snapshot(snapshot, hashes=False):
    for name, record in snapshot.items():
        now=_stat(name)
        assert all(now[k]==record[k] for k in ['size','mtime_ns','inode']), f'Input changed: {name}'
        if hashes: assert _file_sha(name)==record['sha256'], f'Input content changed: {name}'


def _load_po(P, bank_by_id, datasets):
    files=A.shard_files(P.cache,'prompt_only')
    A.PROVENANCE.update(strict=True,extra_pods=set(),dropped={},off_bank={}); A.PARTIAL_TAIL.clear()
    frames=[A.provenance_filter(A.read_jsonl(f),f,'prompt_only',datasets=datasets) for f in files]
    raw=pd.concat([x for x in frames if len(x)],ignore_index=True)
    assert 'key' in raw
    repeated=int(raw.duplicated('key').sum())
    # Use the canonical reader, including the native ordered keep-last raw-key convention.
    po=A.read_jsonl_shards(P.cache,'prompt_only',datasets=datasets)
    assert not po.duplicated(['dataset','item_id']).any(), 'PO duplicate semantic keys after raw-key deduplication'
    bad=[]
    for row in po.to_dict('records'):
        b=bank_by_id.get(row['item_id'])
        if b is None:
            bad.append([row['key'],'item_id','not in bank']); continue
        for field in ['dataset','label','split']:
            assert row[field]==b[field], f"PO {field} mismatch: {row['key']}"
        assert row['candidates']==b['primary']['candidates'], f"PO candidate mismatch: {row['key']}"
        assert _bool(row.get('system'))==bool(b.get('system')), f"PO system mismatch: {row['key']}"
        assert row.get('adapter','none')=='none', f"PO adapter mismatch: {row['key']}"
        assert row.get('template','fc')=='fc', f"PO template mismatch: {row['key']}"
        lo=row.get('lo'); lp=row.get('lp_pos'); ln=row.get('lp_neg')
        if all(pd.notna(v) and np.isfinite(v) for v in [lo,lp,ln]):
            assert np.isclose(lo,lp-ln,atol=1e-8,rtol=1e-8), f"PO LO mismatch: {row['key']}"
            assert _bool(row.get('model_says_pos'))==(lo>0), f"PO vote mismatch: {row['key']}"
    assert not bad, f'PO unmatched rows: {bad[:5]}'
    return po,files,{'raw_rows':len(raw),'raw_key_duplicates':repeated,'semantic_rows':len(po),
                    'unmatched_rows':len(bad),'provenance':A.PROVENANCE,'partial_tails':dict(A.PARTIAL_TAIL)}


def _frequency_features(items, original, tokenizer, test_hashes, flagged, eligible_datasets):
    """Unlabeled counts are independent of endpoint labels/errors; computed per outer fold and block."""
    pool=items[items.split.eq('pool')&~items.text_hash.isin(test_hashes)&~items.dataset.isin(I.LABEL_DEFECT)]
    pool=pool.sort_values(['text_hash','dataset','item_id'])
    text_by_hash=pool.drop_duplicates('text_hash').set_index('text_hash').normalized.to_dict()
    hashes=list(text_by_hash)
    enc=tokenizer.encode_batch([text_by_hash[h] for h in hashes],add_special_tokens=False)
    token_by_hash={h:e.ids for h,e in zip(hashes,enc)}
    vocab=tokenizer.get_vocab_size(with_added_tokens=True)
    candidates={}
    first=items.drop_duplicates('dataset')
    # R-A candidate forms are fact-fixed; assertion prevents accidental first-item substitution.
    for ds,g in items.groupby('dataset'):
        pairs={tuple(x['candidates']) for x in g.primary}
        assert len(pairs)==1, f'Per-item candidates need explicit frequency expansion: {ds}'
        pair=next(iter(pairs)); candidates[ds]=[tokenizer.encode(x,add_special_tokens=False).ids for x in pair]
    feature_map={}; source=[]
    for block in ['A','B']:
        bp=pool if block=='A' else pool[~pool.dataset.isin(flagged)]
        for fold in range(5):
            train=bp[bp.fold.ne(fold)].drop_duplicates('text_hash')
            selected=set(train.text_hash)
            assert not selected & test_hashes
            assert not set(train.fold)&{fold}
            counts=Counter()
            for h in sorted(selected): counts.update(token_by_hash[h])
            suffix=f'_fold{fold}' if block=='A' else f'_B_fold{fold}'
            for ds in candidates:
                mean,diff=symmetric_candidate_frequency(candidates[ds],counts,vocab)
                feature_map.setdefault(ds,{})['freq_mean'+suffix]=mean
                feature_map[ds]['freq_diff'+suffix]=diff
            source.append({'block':block,'outer_fold':fold,'unique_pool_documents':len(selected),
                           'source_facts':int(train.dataset.nunique()),'tokens':int(sum(counts.values())),
                           'vocab_size':int(vocab),'source_document_sha256':_sha('|'.join(sorted(selected))),
                           'counter_sha256':_sha(json.dumps(sorted(counts.items()),separators=(',',':'))),
                           'excluded_all_frozen_test_texts':True,'excluded_audit_flags':block=='B'})
    return feature_map,source


def preflight(root=Path.cwd(), tokenizer_path=TOKENIZER):
    started_utc=datetime.now(timezone.utc).isoformat(); started=time.monotonic(); root,P,out,local=_paths(root)
    original_path=out/'th2_rows.csv.gz'; prereg=out/'th2_preflight.json'
    bank_path=P.items(); audit_path=P.results/'label_audit.csv'; frozen_path=root/'projects/g_agreement/manifest/frozen_config_r.json'
    inputs=[original_path,prereg,bank_path,audit_path,frozen_path,Path(tokenizer_path)]
    snapshot=_snapshot(inputs,root)
    old=json.loads(prereg.read_text()); frozen=json.loads(frozen_path.read_text())
    assert _file_sha(bank_path)==frozen['items_sha256']['items_r.json']==old['input_hashes']['projects/g_agreement/dataset/items_r.json']
    items,_=A.load_bank(P)
    assert not items.item_id.duplicated().any()
    items['normalized']=items.prompt_text.map(_normalize); items['text_hash']=items.normalized.map(_sha)
    group_of={ds:g['corpus_group'] for g in old['groups'] for ds in g['datasets']}
    fold_of={ds:g['fold'] for g in old['groups'] for ds in g['datasets']}
    items['corpus_group']=items.dataset.map(group_of); items['fold']=items.dataset.map(fold_of)
    assert items.fold.notna().all()
    test_hashes=set(items.loc[items.split.eq('test'),'text_hash'])
    bank=items.set_index('item_id').to_dict('index')
    flagged=set(old['audit_flagged'])
    original=pd.read_csv(original_path)
    for c in ['eligible','audit_flagged','label_defect','block_B']: original[c]=original[c].map(_bool)
    assert not original.duplicated(['dataset','item_id']).any()
    assert not original.dataset.isin(I.LABEL_DEFECT).any()
    for r in original.itertuples(index=False):
        b=bank[r.item_id]
        assert b['split']=='test' and r.dataset==b['dataset'] and r.label==b['label'] and r.text_hash==b['text_hash']
        assert r.fold==b['fold'] and r.corpus_group==b['corpus_group']
    po,po_files,po_audit=_load_po(P,bank,set(items.dataset))
    snapshot.update(_snapshot(po_files,root))
    pot=po[po.split.eq('test')].copy()
    pot['po_finite']=np.isfinite(pd.to_numeric(pot.lo,errors='coerce'))
    pot=pot[['dataset','item_id','lo','po_finite']].rename(columns={'lo':'po_lo'})
    joined=original.merge(pot,on=['dataset','item_id'],how='left',validate='one_to_one',indicator='_po_join')
    joined['po_available']=joined._po_join.eq('both')&joined.po_finite.fillna(False)
    joined['state_available']=False; joined['probe_pool_available']=False
    joined['input_token_count']=np.nan
    pool_ids={}; state_manifest=[]; coverage=[]
    for ds,g in joined.groupby('dataset',sort=True):
        idx_path=P.cache/'states'/ds/'index.json'; state_path=idx_path.parent/'chat_L42.npy'
        record={'dataset':ds,'index_exists':idx_path.exists(),'state_exists':state_path.exists(),
                'pool0_clean':0,'pool1_clean':0,'state_nonfinite_rows':0,'state_unmatched_rows':0}
        if idx_path.exists() and state_path.exists():
            snapshot.update(_snapshot([idx_path,state_path],root))
            ix=json.loads(idx_path.read_text()); ids=ix['item_ids']
            assert len(set(ids))==len(ids), f'State duplicate item IDs: {ds}'
            assert ix['dataset']==ds and ix.get('pod') in A.ALLOWED_PODS
            assert str(ix.get('git_sha'))[:7]==A.FROZEN_GIT_SHA, f'State frozen SHA mismatch: {ds}'
            assert len(ix['labels'])==len(ids)==len(ix['splits'])
            for iid,y,split in zip(ids,ix['labels'],ix['splits']):
                assert iid in bank and bank[iid]['dataset']==ds, f'State unmatched ID: {ds}:{iid}'
                assert bank[iid]['label']==y and bank[iid]['split']==split, f'State label/split mismatch: {ds}:{iid}'
            x=np.load(state_path,mmap_mode='r',allow_pickle=False)
            assert x.ndim==2 and x.shape[0]==len(ids), f'State shape mismatch: {ds}'
            finite=np.isfinite(x).all(axis=1)
            pi=select_pool_indices(ids,bank,test_hashes,finite)
            yy=np.asarray(ix['labels'],int)
            n0=int((yy[pi]==0).sum()); n1=int((yy[pi]==1).sum())
            has_pool=min(n0,n1)>=128
            pool_ids[ds]=[ids[i] for i in pi]
            pos={iid:i for i,iid in enumerate(ids)}
            token_counts=ix.get('n_tokens',{}).get('chat',[])
            assert len(token_counts)==len(ids), f'State token-count alignment: {ds}'
            for row_idx,iid in zip(g.index,g.item_id):
                present=iid in pos and finite[pos[iid]]
                joined.loc[row_idx,'state_available']=present
                joined.loc[row_idx,'probe_pool_available']=has_pool
                if iid in pos: joined.loc[row_idx,'input_token_count']=token_counts[pos[iid]]
            record.update(pool0_clean=n0,pool1_clean=n1,probe_pool_available=has_pool,
                          state_rows=len(ids),state_dimension=int(x.shape[1]),state_nonfinite_rows=int((~finite).sum()),
                          index_sha256=snapshot[str(idx_path.resolve())]['sha256'],state_sha256=snapshot[str(state_path.resolve())]['sha256'],
                          pool_ids_sha256=_sha('|'.join(sorted(pool_ids[ds]))),
                          pool_test_overlap_removed=int(sum(bank[iid]['split']=='pool' and bank[iid]['text_hash'] in test_hashes for iid in ids)))
            del x
        state_manifest.append(record)
    joined['six_available']=joined.po_available&joined.state_available&joined.probe_pool_available
    possible=joined[joined.six_available].copy()
    elig=eligible_facts(possible)
    joined['f1_eligible']=joined.dataset.map(elig).fillna(False)&joined.eligible
    # Only the original registered eligible cohort can enter F1; no replacement facts.
    for ds,g in joined.groupby('dataset',sort=True):
        sr=next(z for z in state_manifest if z['dataset']==ds)
        for half in ['calibration','endpoint']:
            for label in [0,1]:
                z=g[g.half.eq(half)&g.label.eq(label)]
                coverage.append({'dataset':ds,'corpus_group':g.corpus_group.iloc[0],'fold':int(g.fold.iloc[0]),'half':half,'label':label,
                                 'audit_flagged':bool(g.audit_flagged.iloc[0]),'label_defect':False,
                                 'original_eligible':bool(g.eligible.iloc[0]),'f1_eligible':bool(g.f1_eligible.iloc[0]),
                                 'original_items':len(z),'po_matched_finite':int(z.po_available.sum()),
                                 'state_matched_finite':int(z.state_available.sum()),'probe_pool_available':bool(g.probe_pool_available.all()),
                                 'retained_items':int(z.six_available.sum()),'pool0_clean':sr['pool0_clean'],'pool1_clean':sr['pool1_clean'],
                                 'token_count_available':int(z.input_token_count.notna().sum()),'po_margin_available':int(z.po_available.sum()),
                                 'probe_margin_expected_available':int((z.state_available&z.probe_pool_available).sum()),
                                 'char_count_available':len(z),'read_token_surprisal_available':0})
    coverage=pd.DataFrame(coverage)
    coverage.to_csv(out/'th2_f1_coverage.csv',index=False)
    retained=joined[joined.six_available&joined.f1_eligible].copy()
    retained['original_eligible']=retained['eligible']; retained['eligible']=True
    retained['po_margin']=np.log1p(abs(retained.po_lo))
    retained['log_token_count']=np.log1p(retained.input_token_count)
    retained['log_char_count']=retained.item_id.map(lambda iid:np.log1p(len(bank[iid]['prompt_text'])))
    for rd in READERS: retained['e_'+rd]=retained['err_'+rd].astype(int)
    # Frequency estimation uses no outcome or posterior. Counts are fixed, per block/outer fold.
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(tokenizer_path))
    frequency,frequency_source=_frequency_features(items,original,tok,test_hashes,flagged,set(retained.dataset))
    for name in next(iter(frequency.values())): retained[name]=retained.dataset.map(lambda ds:frequency[ds][name])
    freqcols=[c for c in retained if c.startswith('freq_')]
    # Frequencies exist for every candidate pair in the fact-fixed R-A bank; report actual missingness.
    fcounts=[]
    for name in ['po_margin','log_token_count','log_char_count',*freqcols]:
        fcounts.append({'feature':name,'n_present':int(np.isfinite(retained[name]).sum()),'n_missing':int((~np.isfinite(retained[name])).sum()),
                        'constant':bool(retained[name].dropna().nunique()<=1)})
    fcounts.extend([{'feature':'probe_margin','n_present':None,'n_expected':len(retained),'n_missing':None,'constant':None,'status':'pending registered CPU fit'},
                    {'feature':'read_token_surprisal','n_present':0,'n_missing':len(retained),'constant':None,'status':'not cached; full panel NOT RUN'},
                    {'feature':'render','n_present':len(retained),'n_missing':0,'constant':True,'value':'chat','omitted':True},
                    {'feature':'layer_configuration','n_present':len(retained),'n_missing':0,'constant':True,'value':'42/44/42/42; probe42','omitted':True}])
    pd.DataFrame(fcounts).to_csv(out/'th2_f1_feature_coverage.csv',index=False)
    retained=retained.drop(columns=['_po_join','po_finite'])
    retained.to_csv(local/'preflight_rows.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    (local/'pool_ids.json').write_text(json.dumps(pool_ids,sort_keys=True))
    summary={}
    for block in ['A','B']:
        z=retained if block=='A' else retained[~retained.audit_flagged]
        summary[block]={'facts':int(z.dataset.nunique()),'corpus_groups':int(z.corpus_group.nunique()),'items':len(z),
                        'calibration_items':int(z.half.eq('calibration').sum()),'endpoint_items':int(z.half.eq('endpoint').sum()),
                        'folds':sorted(map(int,z.fold.unique())),'adequate_population':z.dataset.nunique()>=20 and set(z.fold)==set(range(5))}
    _check_snapshot(snapshot)
    manifest={'phase':'coverage_complete_no_fits','registration':'BRIEF_R §17, 13cb102','seed':SEED,
              'coverage':summary,'original_items':len(original),'six_available_before_eligibility':int(joined.six_available.sum()),
              'po_audit':po_audit,'state_inventory':state_manifest,'feature_coverage':fcounts,'frequency_source':frequency_source,
              'feature_panel':'available-feature rule; full requested panel NOT RUN (read-token surprisal missing)',
              'tokenizer_path':str(Path(tokenizer_path).resolve()),'input_snapshot':snapshot,
              'intermediate_sha256':_file_sha(local/'preflight_rows.csv.gz'),'pool_ids_sha256':_file_sha(local/'pool_ids.json'),
              'test_hash_scope':'every test document in frozen R-A items_r.json, including excluded facts',
              'preflight_started_utc':started_utc,'preflight_completed_utc':datetime.now(timezone.utc).isoformat(),
              'preflight_timestamp_source':'runtime UTC clock','pool_frequency_fixed_in_bootstrap':True,'probe_instruments_fixed_in_bootstrap':True,
              'frequency_block_B_excludes_audit_flags':True,'preflight_seconds':time.monotonic()-started,
              'no_probe_fit_or_followup_outcome_computed':True}
    (out/'th2_f1_manifest.json').write_text(json.dumps(manifest,indent=2,default=lambda x:sorted(x) if isinstance(x,set) else str(x)))
    lines=['# TH-2-F1 coverage before fitting','','No probe, factor, posterior, regression or trust-rule fit has run in this stage.','',
           '| Block | Facts | Corpus groups | Calibration | Endpoint | Folds | Population gate |','|---|---:|---:|---:|---:|---|---|']
    for block,s in summary.items(): lines.append(f"| {block} | {s['facts']} | {s['corpus_groups']} | {s['calibration_items']} | {s['endpoint_items']} | {s['folds']} | {'PASS' if s['adequate_population'] else 'UNDERPOWERED'} |")
    lines.extend(['',f'Original four-reader rows: {len(original)}; complete six-instrument availability before fact eligibility: {int(joined.six_available.sum())}.',
                  f"Native PO raw-key repeats: {po_audit['raw_key_duplicates']}; unmatched semantic rows: {po_audit['unmatched_rows']}; semantic metadata checks passed.",
                  'Pool training candidates exclude every normalized test document in the frozen R-A bank. Exactly 128 rows of each class are required for the registered probe draw.',
                  'Empirical candidate frequency uses outer-training pool documents only, independently for blocks A and B; counts remain fixed through bootstrap.',
                  'Read-token model surprisal is unavailable: the full feature panel is NOT RUN. Render and layer configuration are constants and omitted.',
                  'Per-fact/class/half retention is in `th2_f1_coverage.csv`; per-feature availability is in `th2_f1_feature_coverage.csv`; file hashes and metadata checks are in `th2_f1_manifest.json`.',''])
    (out/'th2_f1_coverage.md').write_text('\n'.join(lines))
    print('TH2-F1 COVERAGE BEFORE FITS '+json.dumps(summary,sort_keys=True),flush=True)
    return retained,manifest


def _fit_probe(ds,ids_allowed,rows,root,local):
    P=A.Paths(root); P.dataset=root/'projects/g_agreement/dataset'
    X,ids=A.load_states(P,ds,'chat',42)
    assert len(set(ids))==len(ids)
    index=json.loads((P.cache/'states'/ds/'index.json').read_text())
    assert ids==index['item_ids']
    y=np.asarray(index['labels'],int)
    splits=np.asarray(index['splits'])
    allowed=set(ids_allowed); pool=np.array([i for i,iid in enumerate(ids) if iid in allowed],int)
    assert min(np.bincount(y[pool],minlength=2))>=128
    tr=A.balanced_draw(pool,y,256,np.random.default_rng(SEED))
    assert len(tr)==256 and np.array_equal(np.bincount(y[tr],minlength=2),[128,128])
    assert (splits[tr]=='pool').all()
    clf,Cv,_=A.probe_fit_select(X[tr],y[tr],SEED)
    positions={iid:i for i,iid in enumerate(ids)}
    wanted=rows.item_id.tolist(); ii=np.array([positions[iid] for iid in wanted],int)
    score=clf.decision_function(X[ii])
    assert np.isfinite(score).all()
    model_path=local/'probes'/f'{ds}.pkl'; model_path.parent.mkdir(exist_ok=True)
    model_path.write_bytes(pickle.dumps(clf,protocol=5))
    coefficient=hashlib.sha256()
    for step in clf.named_steps.values():
        for name in ['mean_','scale_','coef_','intercept_','classes_']:
            if hasattr(step,name): coefficient.update(name.encode()); coefficient.update(np.asarray(getattr(step,name)).tobytes())
    chosen=[ids[i] for i in tr]
    record={'dataset':ds,'seed':SEED,'n_train':len(tr),'train_label0':128,'train_label1':128,'C':float(Cv),
            'training_ids_sha256':_sha('|'.join(chosen)),'training_ids':chosen,
            'coefficient_sha256':coefficient.hexdigest(),'model_path':str(model_path.relative_to(root)),
            'model_sha256':_file_sha(model_path),'state_sha256':_file_sha(P.cache/'states'/ds/'chat_L42.npy')}
    # Standard convergence diagnostics are model-fit metadata, never outcome summaries.
    record['n_iter']=[int(x) for x in clf.named_steps['logisticregression'].n_iter_]
    return pd.DataFrame({'dataset':ds,'item_id':wanted,'probe_decision':score}),record


def probes(root=Path.cwd(),coverage_reviewed=False,jobs=1):
    assert coverage_reviewed, 'Communicate preflight coverage before fitting; then pass --coverage-reviewed.'
    started_utc=datetime.now(timezone.utc).isoformat(); started=time.monotonic();root,P,out,local=_paths(root)
    manifest_path=out/'th2_f1_manifest.json';m=json.loads(manifest_path.read_text())
    assert m['phase']=='coverage_complete_no_fits', 'Run only from the frozen preflight stage'
    _check_snapshot(m['input_snapshot'],hashes=True)
    assert _file_sha(local/'preflight_rows.csv.gz')==m['intermediate_sha256']
    assert _file_sha(local/'pool_ids.json')==m['pool_ids_sha256']
    rows=pd.read_csv(local/'preflight_rows.csv.gz')
    for c in ['eligible','audit_flagged','label_defect','block_B']: rows[c]=rows[c].map(_bool)
    pools=json.loads((local/'pool_ids.json').read_text())
    todo=[(ds,g.copy()) for ds,g in rows.groupby('dataset',sort=True)]
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        if jobs==1:
            results=[_fit_probe(ds,pools[ds],g,root,local) for ds,g in todo]
        else:
            with ThreadPoolExecutor(max_workers=jobs) as executor:
                futures=[executor.submit(_fit_probe,ds,pools[ds],g,root,local) for ds,g in todo]
                results=[f.result() for f in futures]
    predicted=pd.concat([r[0] for r in results],ignore_index=True);records=[r[1] for r in results]
    rows=rows.merge(predicted,on=['dataset','item_id'],validate='one_to_one')
    assert np.isfinite(rows.probe_decision).all()
    rows['e_probe']=((rows.probe_decision>0).astype(int)!=rows.label).astype(int)
    rows['e_prompt_only']=((rows.po_lo>0).astype(int)!=rows.label).astype(int)
    rows['probe_margin']=np.log1p(abs(rows.probe_decision))
    rows[['dataset','item_id','probe_decision','po_lo']].to_csv(local/'instrument_scores.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    rows=rows.drop(columns=['probe_decision','po_lo','input_token_count'])
    rows.to_csv(out/'th2_f1_rows.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    (local/'probe_manifest.json').write_text(json.dumps(records,indent=2))
    public=[{k:v for k,v in r.items() if k!='training_ids'} for r in records]
    pd.DataFrame(public).to_csv(out/'th2_f1_probe_manifest.csv',index=False)
    _check_snapshot(m['input_snapshot'],hashes=True)
    m.update(probes_started_utc=started_utc,probes_completed_utc=datetime.now(timezone.utc).isoformat(),
             probes_timestamp_source='runtime UTC clock',postfit_input_hashes_verified=True,phase='probes_complete_no_followup_outcomes',probe_fit_seconds=time.monotonic()-started,probe_jobs=jobs,
             probe_manifest_sha256=_file_sha(local/'probe_manifest.json'),rows_sha256=_file_sha(out/'th2_f1_rows.csv.gz'),
             probe_fits=public,no_probe_fit_or_followup_outcome_computed=False,
             no_factor_posterior_regression_or_trust_outcome_computed=True)
    for f in m['feature_coverage']:
        if f['feature']=='probe_margin':
            f.update(n_present=len(rows),n_missing=0,constant=bool(rows.probe_margin.nunique()<=1),status='available')
    pd.DataFrame(m['feature_coverage']).to_csv(out/'th2_f1_feature_coverage.csv',index=False)
    manifest_path.write_text(json.dumps(m,indent=2))
    print(f'TH2-F1 PROBES READY: {len(records)} fixed 256-label probes; {len(rows)} aligned rows; no follow-up outcome summaries.',flush=True)
    return rows,m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['preflight','probes']);p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--tokenizer',type=Path,default=TOKENIZER);p.add_argument('--coverage-reviewed',action='store_true');p.add_argument('--jobs',type=int,default=1)
    a=p.parse_args()
    if a.phase=='preflight':preflight(a.root,a.tokenizer)
    else:probes(a.root,a.coverage_reviewed,a.jobs)
