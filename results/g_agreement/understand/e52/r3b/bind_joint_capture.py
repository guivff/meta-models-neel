"""Bind Integrator's three capture-only shards and freeze words before J scoring."""
import argparse,sys
from pathlib import Path
from datetime import datetime
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
E52=HERE.parent;CHANNEL=ROOT/'results/g_agreement/understand/e57/jlens'
sys.path.insert(0,str(E52));sys.path.insert(0,str(CHANNEL))
from build_basis import read,dump,sha
from run_labels import verify
from prepare import words_for
from cpu_job import validate_units


def bind(bank):
    source=ROOT/'cache/g_agreement/understand'/bank.lower()/'capture_delivery'
    delivery=read(source/'DELIVERY.json');verify(source,delivery['files'])
    assert delivery['issuer']=='integrator' and delivery['experiment']==bank
    assert delivery['reader_outputs_included']==0 and delivery['probe_scores_included']==0
    assert delivery['R3b']=='block-44 capture (test activations + CPU class means) before any reader output exists'
    folder=ROOT.parent/'wt-wtext/results/g_agreement/understand'/bank.lower()/'cache/bank_2026-10-27_v1'
    seal=read(folder/'BANK_SEAL.json');assert sha(folder/'BANK_SEAL.json')==delivery['bank_seal_sha256']
    private=folder/'items.PRIVATE.json';assert sha(private)==seal['files'][private.name]
    records=read(private);test={r['id']:r for r in records if r['split']=='test'}
    dp=folder/('ROW_DEFINITIONS.json' if bank=='E56' else 'DEFINITIONS.json')
    assert sha(dp)==seal['files'][dp.name];definitions=read(dp);definitions=definitions.get('rows',definitions)
    ap=folder/'ANNOTATIONS.PRIVATE.json';annotations=read(ap) if ap.exists() else {}
    if ap.exists():assert sha(ap)==seal['files'][ap.name]
    chunks=[];order=[];shards=[]
    for slot in sorted(delivery['slots'],key=int):
        d=source/('shard_'+slot);cpu=read(d/'CPU_SEAL.json');cap=read(d/'CAPTURE_SEAL.json')
        assert sha(d/'CAPTURE_SEAL.json')==delivery['slots'][slot]['capture_seal_sha256']==cpu['capture_seal_sha256']
        assert cap['pod_id']==delivery['slots'][slot]['pod_id']
        assert cpu['private_items_sha256']==sha(private)
        assert cpu['files']['CLASS_MEANS.npz']==sha(d/'CLASS_MEANS.npz')
        ids=read(d/'test.order.json');h=np.load(d/'acts44.test.npy',allow_pickle=False)
        assert h.shape==(len(ids),5120) and np.isfinite(h).all() and set(ids)<=set(test)
        means=np.load(d/'CLASS_MEANS.npz',allow_pickle=False)
        for row in sorted({test[i]['feature'] for i in ids}):
            for value in (1,0):
                ix=[k for k,i in enumerate(ids) if test[i]['feature']==row and test[i].get('label')==value]
                key=row+'__test__'+('A' if value else 'B')
                if key in means and ix:
                    expected=h[ix].mean(axis=0,dtype=np.float64).astype(np.float32)
                    assert np.array_equal(expected,means[key]),'delivered class means differ from bound test activations'
        chunks.append(h);order+=ids;shards.append({'slot':slot,'capture_seal_sha256':sha(d/'CAPTURE_SEAL.json'),'CPU_seal_sha256':sha(d/'CPU_SEAL.json')})
    assert len(order)==len(set(order)) and set(order)==set(test)
    merged=ROOT/'cache/g_agreement/understand'/bank.lower()/'jlens/bound_capture'
    merged.mkdir(parents=True,exist_ok=False)
    np.save(merged/'acts44.npy',np.concatenate(chunks),allow_pickle=False);dump(merged/'order.json',order)
    dump(merged/'CAPTURE_SEAL.json',{'experiment':bank,'layer':44,'split':'test','normalizer':'W-lens lossless shard concatenation',
        'source_delivery_path':str(source/'DELIVERY.json'),'source_delivery_sha256':sha(source/'DELIVERY.json'),'source_shards':shards,
        'files':{n:sha(merged/n) for n in ('acts44.npy','order.json')}})
    from transformers import AutoTokenizer
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tr=read(E52/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer'];assert sha(tr['path'])==tr['sha256']
    tok=AutoTokenizer.from_pretrained(Path(tr['path']).parent,local_files_only=True)
    candidates=read(E52.parent/'e30/CANDIDATES.json')
    def tokens(words):return token_variants(tok,words)
    units=[];word_audit={}
    for row in sorted({r['feature'] for r in test.values()}):
        ids=sorted(i for i,r in test.items() if r['feature']==row)
        definition=definitions[row];spec=definition.get('spec',definition);values=spec['values']
        binary=not(bank=='E57' and row in ('capacity_list','category_switch','focus_none'))
        pairmap={};groups={};audit={}
        for i in ids:
            ann=annotations.get(i,{})
            origin='frozen definition values';phrases=[[str(v)] for v in values]
            if row in candidates['candidates']:
                assert candidates['values'][row]==values
                phrases=[[p[s] for p in candidates['candidates'][row]] for s in (0,1)];origin='E30 frozen candidates'
            elif row=='multi_token_entity':
                phrases=[[v] for v in ann['distinguishing_value_words']];origin='frozen annotation distinguishing later words'
            elif row=='page_range_digit':
                phrases=[[v] for v in ann['answer_pair']];origin='frozen per-item digit pair'
            words,shared=words_for(phrases);pair=[tokens(w) for w in words] if binary else [[],[]]
            pairmap[i]=pair;groups[i]={}
            for group,entries in [('list_nouns',ann.get('list_nouns',[])),('animals',ann.get('preceding_animals',[]))]:
                if group=='animals' and row=='category_switch' and test[i].get('label')==0:entries=entries+[ann['last_item']]
                if entries:groups[i][group]=[{'name':v,'token_ids':tokens([v])} for v in dict.fromkeys(entries)]
            audit[i]={'source':origin,'phrases':phrases,'shared_removed':shared,'words':words,'binary':binary}
        units.append({'id':row,'source_row':row,'canonical_row':definition.get('canonical_row',row),
            'condition':row if definition.get('canonical_row',row)!=row else None,'binary':binary,'item_ids':ids,
            'value_token_ids':pairmap,'descriptive_token_sets':groups})
        word_audit[row]=audit
    validate_units(units,records,order)
    def ref(p):return {'path':str(p),'sha256':sha(p),'member':p.name}
    sources=[dp,private,folder/'BANK_SEAL.json',source/'DELIVERY.json',Path(tr['path']),E52.parent/'e30/CANDIDATES.json']
    if ap.exists():sources.append(ap)
    plan={'experiment':bank,'layer':44,'split':'test','bank_seal':{'path':str(folder/'BANK_SEAL.json'),'sha256':sha(folder/'BANK_SEAL.json')},
        'capture_seal':{'path':str(merged/'CAPTURE_SEAL.json'),'sha256':sha(merged/'CAPTURE_SEAL.json')},
        'records':ref(private),'order':ref(merged/'order.json'),'activations':ref(merged/'acts44.npy'),
        'value_sources':[{'path':str(p),'sha256':sha(p)} for p in sources], 'units':units,
        'value_word_policy':'unchanged E52 word/number extraction, shared removal, Suraj single-token variants; frozen entity later words and digit pair annotations',
        'word_audit_path':str(merged/'WORD_AUDIT.json'),'word_audit_sha256':None}
    dump(merged/'WORD_AUDIT.json',word_audit);plan['word_audit_sha256']=sha(merged/'WORD_AUDIT.json')
    planpath=CHANNEL/(bank+'_INPUT_PLAN.json');assert not planpath.exists();dump(planpath,plan)
    normal=ROOT/'cache/g_agreement/understand/e52/r3b';normal.mkdir(parents=True,exist_ok=True)
    dump(normal/(bank+'_DELIVERY.json'),{'issuer':'integrator','normalizer':'W-lens, from the hash-bound original Integrator declaration and Guiv custody instruction',
        'original_delivery_path':str(source/'DELIVERY.json'),'original_delivery_sha256':sha(source/'DELIVERY.json'),
        'experiment':bank,'status':'VERIFIED_CAPTURE_ONLY','delivered_epoch':datetime.fromisoformat(delivery['delivered_utc'].replace('Z','+00:00')).timestamp(),
        'bank_seal_sha256':delivery['bank_seal_sha256'],'capture_seal_sha256':sha(merged/'CAPTURE_SEAL.json'),
        'reader_outputs_opened_at_registration':False,'reader_outputs_opened_before_forecast':False,'readers_held_until_forecast_commit':True,
        'custody_authority':'original delivery: before any reader output exists; Guiv: readers cannot start until forecast commit'})
    print(bank,'bound',len(order),'test items;',sum(u['binary'] for u in units),'binary units;',len(units)-sum(u['binary'] for u in units),'exclusions; no reader outcomes')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bank',choices=['E56','E57']);a=p.parse_args();bind(a.bank)
