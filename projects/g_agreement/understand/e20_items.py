"""E20 §112 clarified item bank; CPU only, reusing frozen E17 twin indexing."""
import argparse
from collections import Counter,defaultdict
import gzip,hashlib,json
from pathlib import Path
from . import e17_items as E
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.items import FEATURES,load_pinned_tokenizer
SEED=20261025
DISTANCES=(2,4,8,16,32,48)
ROWS=('prose_paren','python_string','prose_sentiment_delayed','fact_once')
LEXICON={'A':['wonderful'],'B':['terrible']}
NUMBERS=('1234','5678')

def semantic_twins(tok,feature,family,variant):
    word,body,tail=E.fill(feature,family,variant)
    # Enough unrelated material before every capture; distance manipulates capture,
    # never the fact identity or lexical material within a twin pair.
    middle=' '+body+' '+body
    vals=('wonderful','terrible') if feature=='prose_sentiment_delayed' else NUMBERS
    texts=[]
    for v in vals:
        head=('The experience was '+v+'.' if feature=='prose_sentiment_delayed' else 'The recorded access code was '+v+'.')
        cue=' Overall the experience was ' if feature=='prose_sentiment_delayed' else ' The code was '
        text=head+middle+cue+v+'.'+tail+'.'
        a=len(head+middle+cue); b=a+len(v)
        enc=tok(text,add_special_tokens=False,return_offsets_mapping=True)
        slots=[i for i,(x,y) in enumerate(enc['offset_mapping']) if x<b and y>a]
        init=head.index(v); init_slots=[i for i,(x,y) in enumerate(enc['offset_mapping']) if x<init+len(v) and y>init]
        texts.append({'text':text,'consequence_index':slots[0],'consequence_end':slots[-1]+1,'consequence_chars':[a,b],
                      'initial_chars':[init,init+len(v)],'initial_end_index':init_slots[-1],
                      'consequence_ids':enc['input_ids'][slots[0]:slots[-1]+1]})
    return texts

def build(tok):
    records=[]
    for feature in ROWS:
        for family in range(12):
            for variant in range(10):
                pair=E.digest(f'E20:{SEED}:{feature}:{family}:{variant}')[:24]
                if feature in ROWS[:2]:
                    raw=E.span_pair(tok,feature,family,variant,'long')
                    twins=[]
                    for text,oi,ci,oc,cc in raw:
                        ids=E.encode(tok,text)
                        twins.append({'text':text,'opener_index':oi,'opener_chars':list(oc),'consequence_index':ci,
                         'consequence_end':ci+1,'consequence_chars':list(cc),'span_tokens':ci-oi-1,'consequence_ids':[ids[ci]]})
                else:twins=semantic_twins(tok,feature,family,variant)
                for d in DISTANCES:
                    r=twins[0]['consequence_index']-d
                    for side,twin in enumerate(twins):
                        text=twin['text'];ids=E.encode(tok,text)
                        assert r>=0
                        obj={**twin,'feature':feature,'family':family,'variant':variant,'pair_id':pair,
                          'id':E.digest(f'{pair}:{d}:{side}')[:24], 'distance':d,'label':1-side,'state':'AB'[side],
                          'split':'dev' if family<4 else 'test','cluster':f'{feature}:t{family:02d}',
                          'read_index':r,'ids':ids[:r+1],'full_ids':ids,
                          'intervening_ids':ids[r+1:twin['consequence_index']],
                          'candidates':[x['consequence_ids'] for x in twins]}
                        records.append(obj)
    groups=defaultdict(list);pairs=defaultdict(list)
    for x in records:
        groups[x['feature'],x['distance'],x['split'],x['cluster'],len(x['ids'])//16].append(x['id'])
        pairs[x['pair_id'],x['distance']].append(x)
    for pair in pairs.values():
        for x,y in (pair,pair[::-1]):
            x['opposite_donor_id']=y['id']; pool=sorted(groups[x['feature'],x['distance'],x['split'],x['cluster'],len(x['ids'])//16])
            x['random_donor_id']=pool[int(E.digest(f'E20-random:{SEED}:{x["id"]}'),16)%len(pool)]
    return records

def audit(tok,records,complete=True):
    pairs=defaultdict(list);counts=Counter();ranges=defaultdict(list)
    for x in records:
        enc=tok(x['text'],add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];r=x['read_index'];c=x['consequence_index']
        assert ids==x['full_ids'] and ids[:r+1]==x['ids'] and c-r==x['distance']
        a,b=x['consequence_chars'];slots=[i for i,(u,v) in enumerate(enc['offset_mapping']) if u<b and v>a]
        assert slots==list(range(c,x['consequence_end']))
        assert ids[c:x['consequence_end']]==x['consequence_ids']==x['candidates'][1-x['label']]
        assert ids[r+1:c]==x['intervening_ids'] and len(x['intervening_ids'])==x['distance']-1
        assert x['split']==('dev' if x['family']<4 else 'test')
        assert x['state']==('A' if x['label'] else 'B')
        prefix=E.decode(tok,x['ids'])
        if x['feature'] in ROWS[:2]:
            oi=E.token_at(tok,x['text'],*x['opener_chars']);assert oi==x['opener_index']<r
            assert 60<=c-oi-1<=80 and x['span_tokens']==c-oi-1
            if x['feature']=='prose_paren':assert prefix.count('(')-prefix.count(')')==x['label']
            else:assert prefix.count('"')%2==x['label']
            ranges[x['feature']].append(c-oi-1)
        else:
            a0,b0=x['initial_chars']; initial=[i for i,(u,v) in enumerate(enc['offset_mapping']) if u<b0 and v>a0]
            assert initial[-1]==x['initial_end_index']
            assert r-initial[-1]>=(8 if x['feature']=='prose_sentiment_delayed' else 20)
            val=(LEXICON[x['state']][0] if x['feature']=='prose_sentiment_delayed' else NUMBERS[1-x['label']])
            assert x['text'][a0:b0]==x['text'][a:b]==val
            assert prefix.count(val)==1 and x['text'].count(val)==2
            ranges[x['feature']].append(r-initial[-1])
        pairs[x['pair_id'],x['distance']].append(x);counts[x['feature'],x['distance'],x['split'],x['label']]+=1
    for pair in pairs.values():
        assert len(pair)==2
        a,b=sorted(pair,key=lambda x:-x['label']); assert a['label']==1 and b['label']==0
        assert a['read_index']==b['read_index'] and a['consequence_index']==b['consequence_index']
        assert len(a['full_ids'])==len(b['full_ids'])
        changes=[i for i,(u,v) in enumerate(zip(a['full_ids'],b['full_ids'])) if u!=v]
        if a['feature'] in ROWS[:2]:assert changes==[a['opener_index'],a['consequence_index']]
        else:
            allowed=[]
            enc=tok(a['text'],add_special_tokens=False,return_offsets_mapping=True)
            for start,end in (a['initial_chars'],a['consequence_chars']):allowed += [i for i,(u,v) in enumerate(enc['offset_mapping']) if u<end and v>start]
            assert changes and set(changes)<=set(allowed)
        assert a['intervening_ids']==b['intervening_ids']
        assert a['opposite_donor_id']==b['id'] and b['opposite_donor_id']==a['id']
    if complete:
        assert len(records)==5760 and len(pairs)==2880
        assert dict(counts)=={(f,d,s,y):(40 if s=='dev' else 80) for f in ROWS for d in DISTANCES for s in ('dev','test') for y in (0,1)}
        assert not {x['cluster'] for x in records if x['split']=='dev'} & {x['cluster'] for x in records if x['split']=='test'}
        assert len({x['pair_id'] for x in records})==480
    return {'status':'PASS','capture_records':len(records),'text_pairs':len({x['pair_id'] for x in records}),'capture_pairs':len(pairs),
      'ranges':{f:[min(v),max(v)] for f,v in ranges.items()},'counts':{'/'.join(map(str,k)):v for k,v in counts.items()},
      'checks':['every index independently retokenized','A-text distance and exact B alignment','state parsed before capture','only designated state/consequence token slots differ','common intervening tokens','disjoint template splits','120 pairs per row;40 dev80 test','six distances per text']}

def freeze(tok,tokenizer,out,stage):
    records=build(tok);checked=audit(tok,records)
    out=Path(out);stage=Path(stage);out.mkdir(parents=True,exist_ok=False);stage.mkdir(parents=True,exist_ok=False)
    payload=''.join(json.dumps(x,sort_keys=True)+'\n' for x in records).encode();(out/'items.jsonl.gz').write_bytes(gzip.compress(payload,mtime=0))
    P.dump(out/'CPU_AUDIT.json',checked)
    keys=('id','pair_id','feature','distance','split','cluster','read_index','ids','intervening_ids','candidates','random_donor_id','opposite_donor_id')
    P.jsonl(stage/'items.input.jsonl',[{k:x[k] for k in keys} for x in records])
    labels=stage.parent/(stage.name+'.labels.DO_NOT_STAGE.jsonl')
    P.jsonl(labels,[{k:x[k] for k in ('id','pair_id','feature','distance','split','cluster','state','label')} for x in records])
    phr={f:FEATURES['prose_sentiment' if f=='prose_sentiment_delayed' else f].pairs('olens') for f in ROWS[:-1]}
    phr['fact_once']=[('- The recorded access code is 1234.','- The recorded access code is 5678.'),('- At the read position, the stated code is 1234.','- At the read position, the stated code is 5678.')]
    P.dump(stage/'phrasings.json',phr);P.dump(stage/'events.json',{'sentiment_lexicon':LEXICON,'fact_numbers':NUMBERS,'positive_event':'fixed A event in both states, never true-state correctness','distances':DISTANCES,'seed':SEED})
    paths=['projects/g_agreement/understand/'+n for n in ('e20_items.py','e17_items.py')]+['results/g_agreement/understand/e20/REGISTERED_SECTION.md']
    manifest={'experiment':'E20','section':112,'authority':'e4e627bf','clarifications':['a84ff80c','e4e627bf'],'seed':SEED,'pairs_per_row':120,'rows':ROWS,'dev_pairs_per_row':40,'test_pairs_per_row':80,'captures':5760,'bank_sha256':P.sha(out/'items.jsonl.gz'),'uncompressed_sha256':hashlib.sha256(payload).hexdigest(),'labels_sha256':P.sha(labels),'tokenizer_sha256':P.sha(Path(tokenizer)/'tokenizer.json'),'authoring_source_files':{n:P.sha(P.ROOT/n) for n in paths},'inherited_E17_generator_commit':'75f60d3d','worker_python':'/weights/venv-kernels/bin/python','parser_status':'NOT_VALIDATED_NOT_FROZEN','model_calls':0}
    P.dump(stage/'manifest.json',manifest);P.seal(stage,['items.input.jsonl','phrasings.json','events.json','manifest.json'],'E20_ITEMS_FROZEN_BEFORE_PARSER_VALIDATION_AND_CAPTURE')
    for name in ('manifest.json','INPUT_SEAL.json','phrasings.json','events.json'):(out/name).write_bytes((stage/name).read_bytes())
    print(json.dumps({'audit':checked['status'],'capture_records':len(records),'bank_sha256':manifest['bank_sha256']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
    freeze(load_pinned_tokenizer(a.tokenizer),a.tokenizer,a.out,a.stage)
