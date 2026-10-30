"""One-way E46 source, labels, candidates and state-function freeze."""
from io46 import *
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
from check_long import state as long_state
from build_draft import TOKENIZER_SHA,ROWS

def freeze():
    if (HERE/'BANK_SEAL.json').exists():raise ValueError('already frozen; no replacement')
    items=rows(HERE/'cache/draft/items.DRAFT.jsonl')
    assert len(items)==len({r['id'] for r in items})==len({r['text'] for r in items})==672
    for f in ROWS:
        for split in ['dev','test']:assert Counter(r['label'] for r in items if r['feature']==f and r['split']==split)=={'A':42,'B':42}
    definitions={
      'fenced_code':{'values':['inside','outside'],'kind':'syntactic','cell':'long','definition':'Inside a fenced code block versus in prose; frozen source has at least 40 tokens before closing.'},
      'latex_list':{'values':['inside','outside'],'kind':'syntactic','cell':'long','definition':'Inside a LaTeX list environment versus outside; frozen source has at least 40 tokens before closing.'},
      'word_first_piece':{'values':['first_piece','complete_word'],'kind':'semantic','cell':'short','definition':'Read token is the first piece of a multi-token source word versus a complete word.'},
      'number_completion':{'values':['next_completes','next_does_not_complete'],'kind':'semantic','cell':'short','definition':'Next authored-source token completes the number/date already begun versus no number/date begun at the read position.'}}
    dump(HERE/'ROW_DEFINITIONS.json',{'authority':'§157 and clarification 1, 50edac15; user confirms source next token','rows':definitions})
    candidates={}
    phrases={
      'fenced_code':[['The read position is inside a fenced code block.','The read position is in prose outside a fenced code block.'],['At this position, a code fence is open.','At this position, no code fence is open.']],
      'latex_list':[['The read position is inside a LaTeX list environment.','The read position is outside a LaTeX list environment.'],['At this position, a LaTeX list is open.','At this position, no LaTeX list is open.']],
      'word_first_piece':[['The read token is the first piece of an unfinished multi-token word.','The read token ends a complete word.'],['At the read position, the source word has only its first token piece.','At the read position, the source word is complete.']],
      'number_completion':[['The next source token completes the number or date already begun.','No number or date has begun at the read position.'],['One more source token finishes the current number or date.','At this position, there is no unfinished number or date.']]}
    for f,pairs in phrases.items():candidates[f]={'values':definitions[f]['values'],'olens_descriptive':[['- '+x for x in pair] for pair in pairs],'nla':pairs}
    dump(HERE/'CANDIDATES.json',{'rows':candidates,'authority':'new fixed descriptive phrasings from definitions only; two per value, arithmetic mean; E36 native scoring recipe'})
    source_names=['author.py','build_draft.py','check_long.py','states.py','freeze.py','ROW_DEFINITIONS.json','CANDIDATES.json']
    prepared=HERE/'cache/prepared';prepared.mkdir(exist_ok=False)
    # Freeze all source text and suffixes before the independent final checks.
    dump(prepared/'items.PRIVATE.json',items)
    dump(HERE/'BANK_SOURCE_SEAL.json',{'status':'FROZEN_BEFORE_FINAL_LABEL_CHECK','created_at':datetime.now(ZoneInfo('Europe/Zurich')).isoformat(),'files':{'cache/prepared/items.PRIVATE.json':sha(prepared/'items.PRIVATE.json')},'source_files':{n:sha(HERE/n) for n in source_names},'items':672,'development_checks_disclosed':True})
    from transformers import PreTrainedTokenizerFast
    tokenizer=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json'
    assert sha(tokenizer)==TOKENIZER_SHA
    tok=PreTrainedTokenizerFast(tokenizer_file=str(tokenizer))
    ledger=[]
    for r in items:
        assert tok.encode(r['text'],add_special_tokens=False)==r['ids']
        src=r['text']+r['authored_suffix'];enc=tok(src,add_special_tokens=False,return_offsets_mapping=True)
        assert enc['input_ids'][:len(r['ids'])]==r['ids']
        if r['feature'] in ROWS[:2]:
            assert long_state(r['feature'],r['text'])==r['value']
            if r['label']=='A':assert r['closing_distance_tokens']>=40
        else:
            a,b=r['source_unit_start'],r['source_unit_end'];assert src[a:b]==r['source_unit']
            offsets=enc['offset_mapping'];unit=[j for j,(start,end) in enumerate(offsets) if end>a and start<b];last=len(r['ids'])-1
            if r['value']=='first_piece':assert len(unit)>=2 and last==unit[0] and offsets[last][1]<b
            elif r['value']=='complete_word':assert offsets[last][1]==b
            elif r['value']=='next_completes':assert a<offsets[last][1]<b and offsets[last+1][1]==b
            else:assert offsets[last][1]<a and offsets[last+1][1]<b
        ledger.append({'id':r['id'],'row':r['feature'],'label_check':'PASS'})
    groups={}
    for r in items:groups.setdefault((r['feature'],r['template_index'],r['filler_index']),[]).append(len(r['ids']))
    assert len(groups)==336 and all(len(ls)==2 and max(ls)/min(ls)<=1.1 for ls in groups.values())
    dump(prepared/'label_checks.json',ledger)
    dump(HERE/'VALIDATION.json',{'label_checked':672,'label_passed':672,'pairs_length_checked':336,'pairs_length_passed':336,'max_pair_length_ratio':max(max(ls)/min(ls) for ls in groups.values()),'tokenizer_sha256':TOKENIZER_SHA,'ledger_sha256':sha(prepared/'label_checks.json')})
    with (prepared/'prefixes.jsonl').open('x') as f:
        for r in items:
            if r['split']=='test':f.write(json.dumps({'key':'E46/'+r['id'],'ids':r['ids']})+'\n')
    seal(prepared,['prefixes.jsonl'],'INPUT_SEAL.json')
    dump(HERE/'STATE_FUNCTION_SEAL.json',{'authority':'§157 clarification 1','files':{'states.py':sha(HERE/'states.py'),'check_long.py':sha(HERE/'check_long.py'),'e42/persistence_core.py':sha(HERE.parent/'e42/persistence_core.py')},'unknown_policy':'E42 carry last determined; initial unknown excluded; >20% excluded makes row NOT EVALUABLE','short_state':'anchored original unit; A first boundary, B next completed word or number; observed delimiter required'})
    dump(HERE/'BANK_SEAL.json',{'status':'FROZEN_VALIDATED_NO_READER_SCORES','frozen_at':datetime.now(ZoneInfo('Europe/Zurich')).isoformat(),'files':{n:sha(HERE/n) for n in ['BANK_SOURCE_SEAL.json','ROW_DEFINITIONS.json','CANDIDATES.json','VALIDATION.json','STATE_FUNCTION_SEAL.json','cache/prepared/items.PRIVATE.json','cache/prepared/INPUT_SEAL.json']},'items':672,'test_items':336,'dev_items':336,'rows':list(ROWS)})
    print('E46 bank frozen and validated:',sha(HERE/'BANK_SEAL.json'))
if __name__=='__main__':freeze()
