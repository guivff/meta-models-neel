"""TH-2 registered coverage preflight. CPU only; no fits or joint-error endpoints."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import datasets as D
from projects.g_agreement.r_bench import interim as I

READERS = ('jlens', 'olens', 'nla', 'skip_a')
LAYERS = {'jlens': 42, 'olens': 44, 'nla': 42, 'skip_a': 42}
COLS = ['key', 'dataset', 'item_id', 'reader', 'layer', 'render', 'condition', 'position',
        'label', 'split', 'sided', 'state_item_id', 'cand_A', 'cand_B', 'lp_A', 'lp_B', 'lo',
        'unscorable', 'items_file', 'items_sha256', 'pod', 'git_sha', 'system']
SEMANTIC = ['dataset','item_id','reader','layer','render','condition','position','system']

def _sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def _file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()
def _stat(path):
    s = Path(path).stat()
    return {'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'inode': s.st_ino}
def _normalize(text): return ' '.join(str(text).split())

class _Union:
    def __init__(self, names): self.p = {x:x for x in names}
    def find(self, x):
        if self.p[x] != x: self.p[x] = self.find(self.p[x])
        return self.p[x]
    def union(self, a, b):
        a,b = self.find(a),self.find(b)
        if a != b: self.p[max(a,b)] = min(a,b)

def split_bank(items):
    """Only labels/text/source metadata enter split construction; never reader scores."""
    items = items.copy()
    names = sorted(items.dataset.unique())
    u = _Union(names)
    parents = defaultdict(list)
    for ds in names:
        parents['corpus:'+I.corpus_of(ds)].append(ds)
        if ds in D.BINARISED_FROM: parents['parent:'+D.BINARISED_FROM[ds][0]].append(ds)
    fams = {'historical':{5,6,7}, 'temperature':{38,39,40,130,131,132}, 'context':{133,134,135},
            'cancer':{142,143,144}, 'disease':{145,146,147}, 'emotion':{148,149,150},
            'it_tickets':{151,152,153}, 'athletes':{154,155,156}}
    for ds in names:
        num = int(ds.split('_')[0])
        for fam, nums in fams.items():
            if num in nums: parents['family:'+fam].append(ds)
    for members in parents.values():
        for ds in members[1:]: u.union(members[0], ds)
    norm = items.prompt_text.map(_normalize)
    items['text_hash'] = norm.map(_sha)
    items['half'] = norm.map(lambda s: 'endpoint' if int(_sha('20261020|'+s),16)&1 else 'calibration')
    first = {}
    for ds, text in zip(items.dataset, items.text_hash):
        if text in first: u.union(ds,first[text])
        else: first[text] = ds
    comps = defaultdict(list)
    for ds in names: comps[u.find(ds)].append(ds)
    group_of = {ds:'cg_'+_sha('|'.join(sorted(members)))[:16] for members in comps.values() for ds in members}
    groups = sorted(set(group_of.values()), key=lambda g:_sha('20261019|'+g))
    fold_of = {g:i%5 for i,g in enumerate(groups)}
    items['corpus_group'] = items.dataset.map(group_of)
    items['fold'] = items.corpus_group.map(fold_of)
    return items, [{'corpus_group':group_of[members[0]], 'fold':fold_of[group_of[members[0]]],
                    'datasets':sorted(members)} for members in comps.values()]

def _frames(path, n=4000):
    """Bound memory while retaining analyze.read_jsonl's only-last-line-may-be-partial rule."""
    if path.stat().st_size <= 32*1024*1024:
        yield A.read_jsonl(path)
        return
    rows=[]
    pending_error=None
    with path.open(encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            if pending_error is not None: raise pending_error
            try: rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                pending_error=exc
                continue
            if len(rows)>=n:
                yield pd.DataFrame(rows)
                rows=[]
    if pending_error is not None: A.PARTIAL_TAIL[path.name]=A.PARTIAL_TAIL.get(path.name,0)+1
    if rows: yield pd.DataFrame(rows)

def _expected_pair(reader, primary):
    pair=list(primary['candidates'])
    if reader=='jlens':
        jl=primary.get('jlens') or [None,None]
        pair=[jl[i] or pair[i] for i in range(2)]
    return tuple(pair)

def run_preflight(root: Path, out: Path | None=None):
    root=Path(root).resolve()
    out=Path(out) if out else root/'results/g_agreement/r/i2'
    out.mkdir(parents=True,exist_ok=True)
    # A.Paths(root) has a legacy dataset-path convention; set its actual bank directory explicitly.
    P=A.Paths(root)
    P.dataset=root/'projects/g_agreement/dataset'
    bank_path=P.items()
    audit_path=P.results/'label_audit.csv'
    frozen_path=root/'projects/g_agreement/manifest/frozen_config_r.json'
    files=A.shard_files(P.cache,'reader_lo')
    sources=[bank_path,audit_path,frozen_path,*files]
    before={str(p.relative_to(root)):_stat(p) for p in sources}
    bank_hash=_file_sha(bank_path)
    frozen=json.loads(frozen_path.read_text())
    frozen_bank=(frozen.get('items_sha256') or {}).get('items_r.json',frozen.get('items_r_sha256'))
    assert bank_hash==frozen_bank, f'bank/frozen mismatch: actual={bank_hash}, frozen={frozen_bank}'
    items,bank_meta=A.load_bank(P)
    assert not items.duplicated(['dataset','item_id']).any(), 'Duplicate bank semantic key'
    assert not items.item_id.duplicated().any(), 'Bank item_id is not globally unique'
    assert set(items.label.unique()) <= {0,1}, 'Nonbinary R-A labels'
    for r in items.itertuples(index=False):
        assert len(r.primary['candidates'])==2
        assert r.primary['answer']==r.primary['candidates'][0 if int(r.label)==1 else 1], f'Bank candidate semantics: {r.item_id}'
    items,groups=split_bank(items)
    audits=pd.read_csv(audit_path)
    flagged=set(audits.loc[audits.flagged.astype(str).str.lower().eq('true'),'dataset'])
    items['audit_flagged']=items.dataset.isin(flagged)
    items['label_defect']=items.dataset.isin(I.LABEL_DEFECT)
    bank=items.set_index('item_id').to_dict('index')
    sided_of=dict(zip(items.dataset,items.sided))
    datasets=set(items.dataset)
    A.PROVENANCE.update(strict=True,extra_pods=set(),dropped={},off_bank={})
    A.PARTIAL_TAIL.clear()
    raw={}
    shard_records=[]
    duplicates=Counter()
    split_aliases=Counter()
    mismatches=[]
    for path in files:
        rec={'file':str(path.relative_to(root)), **before[str(path.relative_to(root))],
             'sha256':_file_sha(path),'rows':0,'dropped_ws13':0,'off_bank':0,'in_bank':0,'selected':0}
        for frame in _frames(path):
            if frame.empty: continue
            rec['rows']+=len(frame)
            pod=frame.get('pod',pd.Series(None,index=frame.index,dtype=object))
            ds=frame.get('dataset',pd.Series(None,index=frame.index,dtype=object))
            drop=pod.isin(A.EXCLUDED_PODS)|ds.map(A.is_ws13_dataset).fillna(False).astype(bool)|(path.name.split('.')[-2]=='D')
            rec['dropped_ws13']+=int(drop.sum())
            rec['off_bank']+=int((~drop & ~ds.isin(datasets)).sum())
            frame=A.provenance_filter(frame,path,'reader_lo',datasets=datasets)
            rec['in_bank']+=len(frame)
            if frame.empty: continue
            A.assert_conditions(frame, path.name)
            position=frame.get('position',pd.Series('last',index=frame.index)).fillna('last')
            keep=(frame.reader.isin(READERS)&frame.render.eq('chat')&frame.condition.isin(['natural','pool_eval'])&
                  frame.layer.eq(frame.reader.map(LAYERS))&position.eq('last'))
            frame=frame.loc[keep].copy()
            if frame.empty: continue
            frame['position']=position.loc[keep]
            frame['system']=frame.get('system',pd.Series(False,index=frame.index)).fillna(False).astype(bool)
            rec['selected']+=len(frame)
            for row in frame.reindex(columns=COLS).to_dict('records'):
                iid=row['item_id']; b=bank.get(iid)
                def check(ok, field, expected):
                    if not ok and len(mismatches)<30:
                        mismatches.append({'file':path.name,'key':row['key'],'field':field,'observed':str(row.get(field)),'expected':str(expected)})
                check(b is not None,'item_id','bank membership')
                if b is None: continue
                for field in ['dataset','label','sided']:
                    check(row[field]==b[field],field,b[field])
                split='pool' if row['split']=='pool_eval' else row['split']
                if split!=row['split']: split_aliases[str(row['split'])]+=1
                check(split==b['split'],'split',b['split'])
                check(row['state_item_id']==iid,'state_item_id',iid)
                check(bool(row['system'])==bool(b.get('system')),'system',bool(b.get('system')))
                check(row['items_file']=='items_r.json','items_file','items_r.json')
                check(row['items_sha256']==bank_hash,'items_sha256',bank_hash)
                ca,cb=_expected_pair(row['reader'],b['primary'])
                check(row['cand_A']==ca,'cand_A',ca); check(row['cand_B']==cb,'cand_B',cb)
                if row['condition']=='pool_eval':
                    check(b['split']=='pool','split','pool')
                row['split']=b['split']
                row['condition']='natural'
                k=row['key']
                if k in raw:
                    duplicates['raw_key_repeats']+=1
                    compare=['dataset','item_id','reader','layer','render','condition','label','sided','cand_A','cand_B','lp_A','lp_B','lo','unscorable']
                    if any(str(raw[k].get(c))!=str(row.get(c)) for c in compare): duplicates['raw_key_value_conflicts']+=1
                raw[k]=row
        assert _stat(path)==before[str(path.relative_to(root))], f'Input changed while reading: {path}'
        rec['partial_tail']=A.PARTIAL_TAIL.get(path.name,0)
        shard_records.append(rec)
        print(f"preflight: {path.name}: {rec['rows']:,} rows, {rec['selected']:,} selected",flush=True)
    manifest={'files':shard_records,'bank_sha256':bank_hash,'frozen_bank_sha256':frozen_bank,
              'bank_canonical_items_sha256':bank_meta.get('sha256_items'),'raw_key_audit':dict(duplicates),
              'split_aliases':dict(split_aliases),'semantic_mismatches':mismatches}
    (out/'th2_shards.json').write_text(json.dumps(manifest,indent=2))
    assert not mismatches, f'{len(mismatches)} semantic/provenance mismatches; see th2_shards.json'
    rows=pd.DataFrame(raw.values())
    assert not rows.duplicated(SEMANTIC).any(), 'Duplicate full semantic keys after raw-key keep-last'
    rows['score']=A.primary_score(rows,sided_of)
    rows['unscorable']=rows.unscorable.fillna(False).astype(bool)
    rows['finite']=np.isfinite(rows.score)
    rows['usable']=~rows.unscorable & rows.finite
    usable=rows[rows.usable]
    threshold=usable.groupby(['dataset','reader','split']).score.median().unstack('split')
    threshold=threshold.rename(columns={'test':'test_median','pool':'pool_median'}).reset_index()
    if 'pool_median' not in threshold: threshold['pool_median']=np.nan
    threshold.to_csv(out/'th2_thresholds.csv',index=False)
    tmap=threshold.set_index(['dataset','reader']).to_dict('index')
    test=usable[usable.split.eq('test')].copy()
    test['err']= [int((r.score>tmap[(r.dataset,r.reader)]['test_median'])!=r.label) for r in test.itertuples()]
    test['literal_err']=[int((r.score>(0.0 if sided_of[r.dataset]=='two' else tmap[(r.dataset,r.reader)]['test_median']))!=r.label) for r in test.itertuples()]
    test['pool_err']=[int((r.score>tmap[(r.dataset,r.reader)]['pool_median'])!=r.label) if np.isfinite(tmap[(r.dataset,r.reader)]['pool_median']) else np.nan for r in test.itertuples()]
    parts=[]
    for value in ['err','literal_err','pool_err']:
        v=test.pivot(index=['dataset','item_id'],columns='reader',values=value).reindex(columns=READERS)
        v.columns=[f'{value}_{r}' for r in READERS]
        parts.append(v)
    wide=pd.concat(parts,axis=1)
    wide=wide.dropna(subset=[f'err_{r}' for r in READERS]).reset_index()
    meta_cols=['dataset','item_id','label','text_hash','corpus_group','fold','half','audit_flagged','label_defect','tag','sided']
    wide=wide.merge(items[meta_cols],on=['dataset','item_id'],how='left',validate='one_to_one')
    counts=wide.groupby(['dataset','half','label']).size()
    eligible={ds:all(counts.get((ds,h,l),0)>=10 for h in ['calibration','endpoint'] for l in [0,1]) for ds in datasets}
    pool_complete=wide[[f'pool_err_{r}' for r in READERS]].notna().all(axis=1)
    pcounts=wide[pool_complete].groupby(['dataset','half','label']).size()
    pool_eligible={ds:all(pcounts.get((ds,h,l),0)>=10 for h in ['calibration','endpoint'] for l in [0,1]) for ds in datasets}
    wide['eligible']=wide.dataset.map(eligible)&~wide.label_defect
    wide['pool_eligible']=wide.dataset.map(pool_eligible)&~wide.label_defect
    wide['block_B']=~wide.audit_flagged
    coverage=[]
    for ds in sorted(datasets):
        its=items[items.dataset.eq(ds)&items.split.eq('test')]
        rr=rows[rows.dataset.eq(ds)&rows.split.eq('test')]
        ww=wide[wide.dataset.eq(ds)]
        rec={'dataset':ds,'corpus_group':its.corpus_group.iloc[0],'fold':int(its.fold.iloc[0]),'n_bank_test':len(its),
             'label_defect':ds in I.LABEL_DEFECT,'audit_flagged':ds in flagged,'n_complete':len(ww),
             'eligible':eligible[ds] and ds not in I.LABEL_DEFECT,'pool_eligible':pool_eligible[ds] and ds not in I.LABEL_DEFECT}
        for rd in READERS:
            gr=rr[rr.reader.eq(rd)]
            rec.update({f'{rd}_rows':len(gr),f'{rd}_missing':len(its)-len(gr),f'{rd}_unscorable':int(gr.unscorable.sum()),
                        f'{rd}_nonfinite':int((~gr.finite).sum()),f'{rd}_usable':int(gr.usable.sum())})
        for h in ['calibration','endpoint']:
            for lab in [0,1]: rec[f'{h}_label{lab}']=int(counts.get((ds,h,lab),0))
        coverage.append(rec)
    coverage=pd.DataFrame(coverage)
    # Excluded defects remain in coverage/manifests but never in compact rows available to a fit.
    wide=wide[~wide.label_defect].sort_values(['dataset','item_id']).reset_index(drop=True)
    wide.to_csv(out/'th2_rows.csv.gz',index=False)
    coverage.to_csv(out/'th2_coverage.csv',index=False)
    split=items[['dataset','item_id','split','label','text_hash','corpus_group','fold','half','audit_flagged','label_defect']].copy()
    split['complete']=split.item_id.isin(set(wide.item_id))
    split['eligible']=split.dataset.map(eligible)&~split.label_defect
    split.to_csv(out/'th2_split_manifest.csv.gz',index=False)
    summary={}
    for block in ['A','B']:
        w=wide[wide.eligible & ((~wide.audit_flagged) if block=='B' else True)]
        summary[block]={'facts':int(w.dataset.nunique()),'corpus_groups':int(w.corpus_group.nunique()),'complete_items':len(w),
                        'calibration_items':int(w.half.eq('calibration').sum()),'endpoint_items':int(w.half.eq('endpoint').sum()),
                        'fold_facts':{str(k):int(v) for k,v in w.groupby('fold').dataset.nunique().items()}}
    input_hashes={str(p.relative_to(root)):_file_sha(p) for p in [bank_path,audit_path,frozen_path]}
    for rec in shard_records: input_hashes[rec['file']]=rec['sha256']
    for p in sources: assert _stat(p)==before[str(p.relative_to(root))], f'Input changed: {p}'
    metadata={'preflight_only':True,'no_higher_order_endpoints_computed':True,'coverage':summary,'input_hashes':input_hashes,
              'input_stats':before,'groups':groups,'raw_key_audit':dict(duplicates),'partial_tails':dict(A.PARTIAL_TAIL),
              'excluded_LABEL_DEFECT':sorted(I.LABEL_DEFECT),'audit_flagged':sorted(flagged),
              'fold_rule':'sha256(20261019|corpus_group) sorted, round-robin 5',
              'corpus_group_id':'cg_ + first16 sha256(sorted member dataset IDs joined with |)',
              'half_rule':'sha256(20261020|whitespace-normalized prompt), low bit 0=calibration 1=endpoint',
              'semantic_joins_verified':True,'immutable_input_stats_verified':True,'readers':list(READERS)}
    (out/'th2_preflight.json').write_text(json.dumps(metadata,indent=2))
    print('COVERAGE BEFORE FITTING: '+json.dumps(summary,sort_keys=True),flush=True)
    return wide,metadata

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--out',type=Path)
    a=p.parse_args();run_preflight(a.root,a.out)
