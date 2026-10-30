"""Freeze E1 texts, E2 spans and E7 W4 pairs without any model forwards."""
from pathlib import Path
import hashlib
import numpy as np
from tokenizers import Tokenizer
from .cpu import ROOT, SEED, read, rows, dump, sha, verify

SHARED=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache')


def jsonl(path, records):
    path.write_text(''.join(__import__('json').dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in records))


def freeze(directory, names, provenance):
    dump(directory/'provenance.json',provenance)
    names=[*names,'provenance.json']
    dump(directory/'INPUT_SEAL.json',{'status':'EXPLORATORY_INPUTS_FROZEN_BEFORE_SCORING','files':{n:sha(directory/n) for n in names}})


def main():
    out=ROOT/'cache/g_agreement/understand';out.mkdir(exist_ok=False)
    w=SHARED/'g_agreement/blindspot/w1-readonly-20261024';bank=w/'w1-bank-v2';target=w/'w1-assembled/target'
    verify(bank,'INPUT_SEAL.json');verify(target)
    manifest=read(bank/'manifest.json')
    private=bank/'items.DO_NOT_STAGE.jsonl'
    assert sha(private)==manifest['files']['items.DO_NOT_STAGE.jsonl']
    items=rows(private);public=rows(bank/'items.input.jsonl')
    assert [r['id'] for r in items]==read(target/'items.order.json')==[r['id'] for r in public]
    selected={r['feature'] for r in read(ROOT/'results/g_agreement/blindspot/mechanism/w3/analysis_rk4veemwm0jf9i/metrics.residual.json')['rows']}
    tests=[r for r in items if r['split']=='test' and r['feature'] in selected];assert len(tests)==2100
    tokpath=SHARED/'g_assets/Qwen__Qwen3.6-27B/tokenizer.json'
    pin=read(ROOT/'projects/g_agreement/manifest/assets.json')['target']['files_needed']['tokenizer.json_sha256']
    assert sha(tokpath)==pin;tok=Tokenizer.from_file(str(tokpath))
    for it in tests:
        assert tok.encode(it['text'],add_special_tokens=False).ids==it['ids']
        assert it['meta']['read_position']==len(it['ids'])-1
    e1=out/'e1';e1.mkdir()
    enact=[{'id':r['id'],'feature':r['feature'],'text':r['text'],'arm':'enactment'} for r in tests]
    s2=ROOT/'cache/g_agreement/blindspot/mechanism/s2-texts-dc0e1316';verify(s2,'INPUT_SEAL.json')
    description=[{**r,'arm':'description'} for r in rows(s2/'texts.input.jsonl') if r['feature'] in selected];assert len(description)==1000
    jsonl(e1/'enactment.input.jsonl',enact);jsonl(e1/'decoder.input.jsonl',description+enact)
    freeze(e1,['enactment.input.jsonl','decoder.input.jsonl'],{'W1_bank_seal':sha(bank/'INPUT_SEAL.json'),'W1_target_seal':sha(target/'SCORE_SEAL.json'),'S2_text_seal':sha(s2/'INPUT_SEAL.json'),'tokenizer_sha256':pin,'population':'25rows;2100test enactment;1000existing description texts;AR description reused from sealedS2'})
    # Label-bearing analysis inputs never enter any worker input seal/archive.
    templates=read(bank/'templates.json')
    jsonl(out/'e1_labels.DO_NOT_STAGE.jsonl',[{'id':r['id'],'feature':r['feature'],'arm':'enactment','class':r['class'],'value':int(r['value']==templates[r['feature']]['values'][0]),'phrasing':0} for r in tests]+[{**r,'arm':'description'} for r in rows(s2/'text_labels.DO_NOT_STAGE.jsonl') if r['feature'] in selected])
    e2=out/'e2';e2.mkdir()
    corpus=SHARED/'g_agreement/blindspot/s79/frozen/corpus.jsonl'
    manifest_path=ROOT.parent/'blindspot-worktree/results/g_agreement/blindspot/s79/CORPUS_MANIFEST.json'
    cm=read(manifest_path);assert sha(corpus)==cm['corpus_sha256']
    candidates={d:[] for d in ['latex','markdown','prose','python']};rng=np.random.default_rng(SEED)
    for doc in sorted(rows(corpus),key=lambda d:d['id']):
        assert hashlib.sha256(doc['text'].encode()).hexdigest()==doc['text_sha256']
        ids=tok.encode(doc['text'],add_special_tokens=False).ids
        for length in [16,32,48,64]:
            if len(ids)<length:continue
            starts=np.unique(np.linspace(0,len(ids)-length,min(16,len(ids)-length+1),dtype=int))
            for start in starts:
                key=f"{SEED}:{doc['id']}:{int(start)}:{length}";digest=hashlib.sha256(key.encode()).hexdigest()
                token_ids=ids[int(start):int(start)+length];text=tok.decode(token_ids,skip_special_tokens=False)
                # Exact AR-text/target-span token equality; no context or truncation mismatch.
                if tok.encode(text,add_special_tokens=False).ids!=token_ids:continue
                candidates[doc['domain']].append((digest,{'id':'e2:'+digest[:24],'ids':token_ids,'text':text,'domain':doc['domain'],'document_id':doc['id'],'token_start':int(start),'length':length}))
    spans=[]
    for domain,cs in candidates.items():
        assert len(cs)>=1250,domain
        spans.extend(r for _,r in sorted(cs)[:1250])
    spans=sorted(spans,key=lambda r:r['id']);assert len(spans)==5000 and len({r['id'] for r in spans})==5000
    jsonl(e2/'spans.input.jsonl',spans)
    freeze(e2,['spans.input.jsonl'],{'corpus_sha256':sha(corpus),'corpus_manifest_sha256':sha(manifest_path),'tokenizer_sha256':pin,'seed':SEED,'sample':'1250perdomain;sha256 seeded ranking of unique doc/start/length candidates;16evenlyspaced starts per doc and lengths16/32/48/64;exacttoken roundtrip required','real_capture':'same isolated span token IDs,lastposition,blocks42/44;newtargetcapture budgeted','random_directions':200,'PCA':'globally centered;smallest variance rank reaching95%/99%;all40unitprobe directions nativeblock;fixed seed randomunitbaseline'})
    e7=out/'e7';e7.mkdir()
    collection=ROOT/'cache/g_agreement/blindspot/mechanism/w34-collection-ebf6c121';verify(collection/'bank','INPUT_SEAL.json');verify(collection/'pair_plan','INPUT_SEAL.json')
    ids=read(collection/'target/items.order.json');idx={r['id']:i for i,r in enumerate(items)}
    ix=[idx[i] for i in ids];h=np.load(target/'acts42.npy',allow_pickle=False)[ix];np.save(e7/'acts42.npy',h,allow_pickle=False)
    readouts=ROOT/'cache/g_agreement/blindspot/mechanism/w3-units/rk4veemwm0jf9i/w3-readouts';verify(readouts)
    ol=rows(readouts/'readouts.jsonl');assert [r['id'] for r in ol]==ids
    jsonl(e7/'ol.input.jsonl',ol);dump(e7/'ids.json',ids)
    for name in ['pairs.input.jsonl','templates.json','definitions.json']:(e7/name).write_bytes((collection/'pair_plan'/name).read_bytes())
    freeze(e7,['acts42.npy','ol.input.jsonl','ids.json','pairs.input.jsonl','templates.json','definitions.json'],{'W1_target_seal':sha(target/'SCORE_SEAL.json'),'W4_pair_seal':sha(collection/'pair_plan/INPUT_SEAL.json'),'OL_readout_seal':sha(readouts/'SCORE_SEAL.json'),'OL_readout_site':44,'NLA_decoder_and_readout_site':42,'OL_readout_decoding':'existing sealedW3greedy256;no newOraclegeneration','NLA_generation':'greedy,k1,128tokens,W1nativeprompt,all2772including672fixedrandomsupport','n_pairs':1000,'n_test_items':2100,'n_support_items':672,'arms':['swap','self','ol_only','nla_only','delta_only','random']})
    # All analysis-only metadata sealed by this local preparation receipt, never staged.
    receipt={'status':'FROZEN','inputs':{n:{'path':str(out/n),'seal_sha256':sha(out/n/'INPUT_SEAL.json')} for n in ['e1','e2','e7']},'private_labels':{'path':str(out/'e1_labels.DO_NOT_STAGE.jsonl'),'sha256':sha(out/'e1_labels.DO_NOT_STAGE.jsonl')},'W1_readonly_root':str(w),'brief_sha256':sha(ROOT/'results/g_agreement/understand/BRIEF_UNDERSTAND.bound.md')}
    for n in ['e1','e2','e7']:
        rdir=ROOT/'results/g_agreement/understand'/n;rdir.mkdir(exist_ok=True);dump(rdir/'INPUT_RECEIPT.json',receipt['inputs'][n]);dump(rdir/'INPUT_SEAL.json',read(out/n/'INPUT_SEAL.json'))
    dump(ROOT/'results/g_agreement/understand/PREPARATION.json',receipt)
    print('E1/E2/E7 frozen',{'E1enact':len(enact),'E1decoder':len(description)+len(enact),'E2spans':len(spans),'E7support':len(ids)})


if __name__=='__main__':main()
