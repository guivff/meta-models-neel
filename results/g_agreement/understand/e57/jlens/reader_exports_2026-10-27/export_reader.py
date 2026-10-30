"""Lossless packaging of already sealed J-reader outputs for analysis402; no scoring."""
from pathlib import Path
import argparse,hashlib,json,subprocess,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
CHANNEL=HERE.parent
ADAPTER='769ea9e16a9dd1f9ab6bd1e14b1b6ea81e0f4531'

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False);f.write('\n')
def verify(root,name,digest=None):
    root=Path(root)
    if digest:assert sha(root/name)==digest
    s=read(root/name)
    for f,h in s['files'].items():
        p=root/f;assert p.resolve().is_relative_to(root.resolve());assert sha(p)==h,f
    return s

def committed(p):assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
def gitfile(path):return subprocess.check_output(['git','show',ADAPTER+':'+path],cwd=ROOT)

def row_view(unit,label,items):
    assert [x['id'] for x in items]==unit['item_ids']
    g=label['J_readability']
    result={'G3_AUROC':g.get('auroc'),'G3':g,'J_label':label['label'],'J_fraction':label['J_fraction'],
            'n_test':len(items),'top10':{x['id']:x['top10_tokens'] for x in items},
            'full_vocabulary_best_ranks':{x['id']:x['best_full_vocab_ranks'] for x in items}}
    for x in items:
        assert len(x['top10_tokens'])==len(x['top10_token_ids'])==10
        assert len(x['best_full_vocab_ranks'])==2
    if unit['id']=='capacity_list':
        result['top50_list_nouns']={}
        for x in items:
            d=x['descriptive']['list_nouns'];names=d['entry_names'];hits=d['top50_present']
            assert len(names)==len(hits) and len(names)==len(set(names))
            result['top50_list_nouns'][x['id']]=[n for n,hit in zip(names,hits) if hit]
    return result

def run(bank):
    verify(HERE,'EXPORT_CODE_SEAL.json');committed(HERE/'EXPORT_CODE_SEAL.json')
    alias='E62_PLACEBO' if bank=='E62P' else bank
    planpath=CHANNEL/(alias+'_INPUT_PLAN.json');committed(planpath);plan=read(planpath)
    ld=CHANNEL/(alias+'_results');committed(ld/'ROW_LABELS.json');verify(ld,'LABEL_SEAL.json')
    labels=read(ld/'ROW_LABELS.json');assert labels['plan_sha256']==sha(planpath) and not labels['reader_outcomes_accessed']
    raw=Path(labels['raw_directory']);verify(raw,'RAW_SEAL.json',labels['raw_seal_sha256'])
    delivery=ROOT/'cache/g_agreement/understand'/('e62p' if bank=='E62P' else bank.lower())/'capture_delivery'
    receipt=read(delivery/'DELIVERY.json');assert receipt['experiment']==bank and receipt['issuer']=='integrator'
    assert receipt['reader_outputs_included']==receipt['probe_scores_included']==0
    specpath='results/g_agreement/understand/analysis402/'+bank+'_SPEC.json';specbytes=gitfile(specpath);spec=json.loads(specbytes)
    inp=Path(spec['inputs']);ins=verify(inp,'INPUT_SEAL.json',spec['input_seal_sha256'])
    assert ins['bank_seal_sha256']==plan['bank_seal']['sha256']
    assert sha(plan['records']['path'])==plan['records']['sha256'];records=read(plan['records']['path'])
    public=read(inp/'items.json');assert [x['id'] for x in records]==[x['id'] for x in public]
    if bank in ('E56','E57'):
        caps={k:v['capture_seal_sha256'] for k,v in receipt['slots'].items()}
        for k,h in caps.items():assert sha(delivery/('shard_'+k)/'CAPTURE_SEAL.json')==h==receipt['files']['shard_'+k+'/CAPTURE_SEAL.json']
        expected=set(read(inp/'RUN_PLAN.json')['rows']) if bank=='E57' else {r['feature'] for r in public if r['split']=='test'}
    else:
        caps={bank:receipt['capture_seal_sha256']};assert sha(delivery/'CAPTURE_SEAL.json')==caps[bank]
        expected={r['feature'] for r in public if r['split']=='test' and r.get('state')!='S6'}
    byid={r['row']:r for r in labels['rows']};rows={};reader={}
    for u in plan['units']:
        if u['id'] not in expected:continue
        assert u['id']+'.readout.json' in read(raw/'RAW_SEAL.json')['files']
        items=read(raw/(u['id']+'.readout.json'))['items'];rows[u['id']]=row_view(u,byid[u['id']],items);reader[u['id']]=items
    assert set(rows)==expected
    if bank=='E57':
        rp=read(inp/'RUN_PLAN.json')
        for i,nouns in rows['capacity_list']['top50_list_nouns'].items():assert set(nouns)<=set(rp['count_metadata'][i]['list_nouns'])
    out=ROOT/'cache/g_agreement/understand/j_reader_exports_2026-10-27'/bank
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'reader/READOUTS.json',reader)
    dump(out/'reader/INPUT_SEAL.json',{'files':{'READOUTS.json':sha(out/'reader/READOUTS.json')},'source_raw_seal_sha256':sha(raw/'RAW_SEAL.json'),'source_raw_directory':str(raw),'method':'exact saved first-pass full-vocabulary ranks/top10/top50/descriptive hits; no forward or statistical rerun'})
    dump(out/'labels/ROW_LABELS.json',labels)
    dump(out/'labels/INPUT_SEAL.json',{'files':{'ROW_LABELS.json':sha(out/'labels/ROW_LABELS.json')},'source_label_seal_sha256':sha(ld/'LABEL_SEAL.json')})
    dump(out/'J_ROWS.json',rows)
    dump(out/'PROVENANCE.json',{'experiment':bank,'adapter_commit':ADAPTER,'adapter_spec_path':specpath,'adapter_spec_sha256':hashlib.sha256(specbytes).hexdigest(),'plan_sha256':sha(planpath),'source_delivery_sha256':sha(delivery/'DELIVERY.json'),'original_bound_capture_seal_sha256':plan['capture_seal']['sha256'],'source_raw_seal_sha256':sha(raw/'RAW_SEAL.json'),'source_label_seal_sha256':sha(ld/'LABEL_SEAL.json'),'G3_method':'mean A/B one-vs-rest full-vocabulary rank AUROC, copied from sealed J_readability; no top10 truncation','reader_outcomes_accessed':False,'missing_descriptive_units':['S6_C'+str(i) for i in range(5)] if bank=='E62' else [],'row_grid':'E57 all20 RUN_PLAN rows incl3 nonbinary; E56 all13; E62/E62P binary probe grid only','delivery_target':spec['j_input']})
    seal={'experiment':bank,'bank_seal_sha256':plan['bank_seal']['sha256'],'input_seal_sha256':spec['input_seal_sha256'],'capture_seals':caps,'source_seals':{n:sha(out/n/'INPUT_SEAL.json') for n in ('reader','labels')},'export_code_seal_sha256':sha(HERE/'EXPORT_CODE_SEAL.json'),'reader_outcomes_accessed':False,'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
    if bank in ('E62','E62P'):seal['capture_seal_sha256']=caps[bank]
    dump(out/'J_SEAL.json',seal);verify(out,'J_SEAL.json')
    # Exercise the pinned adapter's J-only validator, never its outcome collector.
    import ast
    source=gitfile('results/g_agreement/understand/e56/job/analysis_io.py').decode()
    fun=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='j_inputs')
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    env={'Path':Path,'verify':verify,'read':read,'require':require}
    exec(compile(ast.Module(body=[fun],type_ignores=[]),'pinned_j_inputs','exec'),env)
    test_spec=dict(spec,j_input=str(out));assert env['j_inputs'](dict(test_spec,bank_seal_sha256=plan['bank_seal']['sha256']),{'capture_seals':caps})==rows
    if bank in ('E62','E62P'):
        source=gitfile('results/g_agreement/understand/analysis402/analyze.py').decode();fun=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='ladder_j')
        env['probe_aucs']=lambda data:{r:None for r in expected}
        exec(compile(ast.Module(body=[fun],type_ignores=[]),'pinned_ladder_j','exec'),env)
        assert env['ladder_j'](test_spec,{'capture_seals':caps})==rows
    target=Path(spec['j_input']);assert not target.exists();shutil.copytree(out,target);verify(target,'J_SEAL.json',sha(out/'J_SEAL.json'))
    dest=HERE/bank;dest.mkdir(exist_ok=False)
    for name in ('J_ROWS.json','J_SEAL.json','PROVENANCE.json','reader/INPUT_SEAL.json','labels/INPUT_SEAL.json'):
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/name,p)
    dump(dest/'DELIVERY.json',{'target':str(target),'complete_bundle':str(out),'J_SEAL_sha256':sha(out/'J_SEAL.json'),'J_ROWS_sha256':sha(out/'J_ROWS.json'),'rows':len(rows),'raw_reader_payload_in_cache':True,'pinned_adapter_J_validation':'PASS','reader_outcomes_accessed':False})
    print(bank+' J reader export verified and delivered: '+str(len(rows))+' rows')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bank',choices=['E57','E56','E62','E62P']);run(p.parse_args().bank)
