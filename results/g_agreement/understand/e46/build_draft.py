"""CPU-only provisional source bank. Not a freeze or launch authorization."""
import hashlib,json
from pathlib import Path
from collections import Counter
from author import long_pair,short_source_pair
from check_long import state
HERE=Path(__file__).resolve().parent
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
ROWS=('fenced_code','latex_list','word_first_piece','number_completion')

def build(tokenizer_path):
    from transformers import PreTrainedTokenizerFast
    p=Path(tokenizer_path)
    if hashlib.sha256(p.read_bytes()).hexdigest()!=TOKENIZER_SHA:raise ValueError('wrong tokenizer')
    tok=PreTrainedTokenizerFast(tokenizer_file=str(p));items=[];checks=[]
    for row in ROWS:
        for t in range(12):
            for f in range(7):
                pair=[]
                if row in ROWS[:2]:
                    examples=long_pair(row,t,f)
                    for text,suffix,value in examples:
                        ids=tok.encode(text,add_special_tokens=False)
                        full=tok.encode(text+suffix,add_special_tokens=False)
                        if full[:len(ids)]!=ids:raise ValueError('prefix unstable under source suffix')
                        until_close=suffix.split('\n')[0]
                        closing_distance=len(tok.encode(text+until_close,add_special_tokens=False))-len(ids)
                        assert closing_distance>=40
                        assert state(row,text)==value
                        pair.append(dict(text=text,ids=ids,authored_suffix=suffix,value=value,closing_distance_tokens=closing_distance if value=='inside' else None))
                else:
                    for source,unit,value in short_source_pair(row,t,f):
                        start=source.rfind(' '+unit)+1;end=start+len(unit)
                        encoded=tok(source,add_special_tokens=False,return_offsets_mapping=True)
                        offsets=encoded['offset_mapping'];full=encoded['input_ids']
                        unit_tokens=[i for i,(a,b) in enumerate(offsets) if b>start and a<end]
                        assert unit_tokens and len(unit_tokens)>= (2 if value in ['first_piece','next_completes'] else 1)
                        last=(unit_tokens[0] if value=='first_piece' else unit_tokens[-1]-1 if value=='next_completes' else unit_tokens[0]-2 if value=='next_does_not_complete' else unit_tokens[-1])
                        cut=offsets[last][1];ids=full[:last+1];text=tok.decode(ids)
                        assert text==source[:cut] and tok.encode(text,add_special_tokens=False)==ids
                        assert (start<cut<end)==(value in ['first_piece','next_completes'])
                        if value=='next_does_not_complete': assert cut<start
                        if value=='next_completes':assert offsets[last+1][1]==end
                        pair.append(dict(text=text,ids=ids,authored_suffix=source[cut:],value=value,source_unit=unit,source_unit_start=start,source_unit_end=end,source_unit_token_count=len(unit_tokens)))
                lengths=[len(x['ids']) for x in pair]
                assert max(lengths)/min(lengths)<=1.1,(row,t,f,lengths)
                checks.append(dict(row=row,template=t,filler=f,lengths=lengths,pass_within_10_percent=True))
                for side,item in enumerate(pair):
                    identity=json.dumps([row,t,f,side,item['text']],ensure_ascii=False)
                    items.append(dict(id=hashlib.sha256(('E46:'+identity).encode()).hexdigest()[:24],feature=row,bank='E46',class_name='state-like' if row in ROWS[:2] else 'semantic',split='dev' if t<6 else 'test',cluster=row+'_family_'+str(t).zfill(2),template_index=t,filler_index=f,label='A' if side==0 else 'B',**item))
    assert len(items)==len({r['id'] for r in items})==len({r['text'] for r in items})==672
    for row in ROWS:
        for split in ['dev','test']:assert Counter(r['label'] for r in items if r['feature']==row and r['split']==split)=={'A':42,'B':42}
    out=HERE/'cache/draft';out.mkdir(parents=True,exist_ok=True)
    (out/'items.DRAFT.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in items))
    (out/'checks.DRAFT.json').write_text(json.dumps(checks,indent=2)+'\n')
    print('DRAFT ONLY: 672 unique prefixes; 84 dev + 84 test per row; all 336 pairs within 10%; source closing distances >=40. Short-row labels provisional.')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);a=p.parse_args();build(a.tokenizer)
