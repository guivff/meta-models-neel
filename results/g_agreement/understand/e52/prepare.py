"""CPU metadata preparation: freeze value words and sealed test captures, no scores."""
import json
import re
import sys
from pathlib import Path
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump

NUMBERS=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty']
TENS={20:'twenty',30:'thirty',40:'forty',50:'fifty',60:'sixty',70:'seventy',80:'eighty',90:'ninety'}

def words_for(phrases):
    raw=[set(re.findall(r'[^\W\d_]+|\d+',' '.join(v).lower())) for v in phrases]
    common=raw[0]&raw[1];out=[]
    for words in raw:
        selected=words-common;expanded=set(selected)
        for w in selected:
            if w in NUMBERS:expanded.add(str(NUMBERS.index(w)))
            elif w in TENS.values():expanded.add(str(next(k for k,v in TENS.items() if v==w)))
            elif w.isdecimal():
                n=int(w)
                # Suraj s3_probe._value_words: leading digit and count word.
                expanded.add(str(n)[0])
                if n<=20:expanded.add(NUMBERS[n])
                elif n<100:expanded.add(TENS[(n//10)*10])
        out.append(sorted(expanded))
    return out,sorted(common)

def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]

def prepare():
    from transformers import AutoTokenizer
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    internals=ROOT.parent/'wt-blindspot-internals/results/g_agreement/understand/e48'
    old=read(internals/'PLAN.json');capplan=read(internals/'item6/PLAN.json')
    candidate=read(HERE.parent/'e30/CANDIDATES.json')
    tokpath=Path(read(HERE/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']['path']).parent
    tok=AutoTokenizer.from_pretrained(tokpath,local_files_only=True)
    wordsets={};banks={};metadata={};pins={}
    def pin(path,expected=None):
        path=Path(path);h=sha(path)
        if expected is not None and h!=expected:raise ValueError('sealed source changed: '+str(path))
        pins[str(path)]=h;return h
    pin(HERE.parent/'e30/CANDIDATES.json')
    pin(internals/'PLAN.json');pin(internals/'item6/PLAN.json')
    for bank in ('W1','E36','W12'):
        c=old['banks'][bank];capture=capplan['captures'][bank]
        for n in (c['items'],c['spec'],c.get('labels')):
            if n:pin(n,old['pins'][str(Path(n).resolve())])
        for n in capture.values():pin(n,capplan['pins'][n])
        seal_name={'W1':'SCORE_SEAL.json','E36':'OUTPUT_SEAL.json','W12':'CAPTURE_SEAL.json'}[bank]
        capture_root=Path(capture['acts']).parent;s=read(capture_root/seal_name);pin(capture_root/seal_name)
        for n in capture.values():
            if sha(n)!=s['files'][Path(n).name]:raise ValueError('capture seal mismatch')
        items={r['id']:r for r in rows(c['items'])};spec=read(c['spec']);spec=spec.get('rows',spec)
        labels={r['id']:r['value'] for r in rows(c['labels'])} if c.get('labels') else {k:r['value'] for k,r in items.items()}
        order=read(capture['order']);lookup={k:i for i,k in enumerate(order)};acts=np.load(capture['acts'],mmap_mode='r',allow_pickle=False)
        if len(lookup)!=len(order) or acts.shape!=(len(order),5120):raise ValueError('capture shape/order')
        selected=[];ix=[];definition={}
        for row in c['rows']:
            values=spec[row]['values']
            if len(values)!=2:raise ValueError('binary A/B mean direction required')
            test=c['item_ids'][row]['test'];dev=c['item_ids'][row]['dev']
            if len(test)!=84 or set(test)&set(dev):raise ValueError('sealed test split')
            for k in test:
                if items[k]['feature']!=row or items[k]['split']!='test' or labels[k] not in values:raise ValueError('test metadata/orientation')
                selected.append({'id':k,'feature':row,'y':int(labels[k]==values[0]),'cluster':items[k]['cluster']});ix.append(lookup[k])
            if sum(x['y'] for x in selected if x['feature']==row)!=42:raise ValueError('balanced84 item row')
            definition[row]={'values':values,'class':'structure' if row in c['structure'] else 'content'}
        out=CACHE/(bank+'-input');out.mkdir(exist_ok=False)
        matrix=np.asarray(acts[ix],dtype=np.float32)
        if not np.isfinite(matrix).all():raise ValueError('finite test activations')
        np.save(out/'acts44.npy',matrix,allow_pickle=False);dump(out/'items.json',selected)
        dump(out/'INPUT_SEAL.json',{'bank':bank,'layer':44,'split':'test','rows':definition,'source_capture_seal_sha256':sha(capture_root/seal_name),'files':{n:sha(out/n) for n in ('acts44.npy','items.json')}})
        banks[bank]={'directory':str(out.relative_to(ROOT)),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'rows':definition}
        metadata[bank]=definition
    # Freeze E49 word choices from its already sealed bank, without any reader/capture output.
    e49=ROOT.parent/'wt-wtext/results/g_agreement/understand/e49/cache/frozen_2026-10-26';s=read(e49/'BANK_SEAL.json')
    pin(e49/'BANK_SEAL.json','ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9')
    pin(e49/'items.PRIVATE.json',s['files']['items.PRIVATE.json']);records=read(e49/'items.PRIVATE.json')
    definitions={}
    for row in s['row_order']:
        vals=[]
        for label in (1,0):
            options={r['value'] for r in records if r['feature']==row and r['label']==label}
            if len(options)!=1:raise ValueError('frozen E49 values')
            vals.append(options.pop())
        definitions[row]={'values':vals,'class':'content' if row in ('user_expertise','topic_twin','next_paragraph_language','unit_system') else 'tracked_state'}
    metadata['E49']=definitions
    for bank,defs in metadata.items():
        wordsets[bank]={}
        for row,spec in defs.items():
            if row in candidate['candidates']:
                if candidate['values'][row]!=spec['values']:raise ValueError('E30 value orientation differs')
                phrases=[[pair[side] for pair in candidate['candidates'][row]] for side in (0,1)];origin='E30 CANDIDATES.json'
            else:phrases=[[str(v)] for v in spec['values']];origin='frozen row definition values'
            words,removed=words_for(phrases);ids=[token_variants(tok,v) for v in words]
            wordsets[bank][row]={'values':spec['values'],'class':spec['class'],'source':origin,'source_phrases':phrases,'shared_words_removed':removed,'value_words':words,'token_ids':ids,'readability_status':'EVALUABLE' if all(ids) else 'NOT_EVALUABLE_EMPTY_VALUE_SET'}
    dump(HERE/'VALUE_WORD_SETS_2026-10-27.json',{'authority':'§169 clarification1 and direct coordinator word-extraction ruling, before scores','banks':wordsets,'tokenizer_sha256':sha(tokpath/'tokenizer.json'),'token_variants_source':'mats.readers.jlens.token_variants','source_pins':pins})
    dump(HERE/'VALUE_WORD_SETS_2026-10-27.sha256.json',{'sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json')})
    dump(HERE/'BANK_INPUTS_2026-10-27.json',{'banks':banks,'source_pins':pins,'E49_status':'AWAITING_CAPTURE_BEFORE_READER_SCORING','values_sha256':sha(HERE/'VALUE_WORD_SETS_2026-10-27.json'),'no_reader_scores_opened':True,'W1_scope':'all40 sealed binary rows; ordinal rows have no registered two-class direction'})
    print({b:{'rows':len(v),'empty_value_sets':sum(x['readability_status']!='EVALUABLE' for x in v.values())} for b,v in wordsets.items()},flush=True)

if __name__=='__main__':prepare()
