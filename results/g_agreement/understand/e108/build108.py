"""CPU input-bank freeze. Run once; never generate choices or load readers."""
import hashlib,json,random,tarfile
from pathlib import Path
from transformers import PreTrainedTokenizerFast
from bank108 import native_items,CATEGORIES,SEED
HERE=Path(__file__).resolve().parent
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
def build():
    assert sha(TOK)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK));raw=native_items();assert len(raw)==1008
    assert len({x['id'] for x in raw})==len({x['text'] for x in raw})==1008
    out=HERE/'cache/bank_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False)
    inventory=[];public=[]
    for x in raw:
        ids=tok.encode(x['text'],add_special_tokens=False);assert ids
        inventory.append({k:x[k] for k in ['id','kind','category','arm','prompt_id']})
        public.append(dict(id=x['id'],prompt=x['text'],input_ids=ids,read_position=len(ids)-1))
    # Balanced seven reference items per category, selected before any generation.
    rng=random.Random(SEED);placebos=[]
    for category in CATEGORIES:
        candidates=sorted((x for x in raw if x['category']==category),key=lambda x:x['id'])
        for x in rng.sample(candidates,7):
            ident='p_'+hashlib.sha256(('E108|placebo|'+x['id']).encode()).hexdigest()[:24]
            inventory.append(dict(id=ident,kind='placebo'))
            placebos.append(dict(id=ident,reference_id=x['id'],generator='E76',seed=SEED))
    assert len(placebos)==84 and len({x['id'] for x in inventory})==1092
    # The requested fixed opening delays naming; observed early choices are reported, not excluded.
    assert len(tok.encode('At the park,',add_special_tokens=False))>=3
    write(out/'PUBLIC_INPUTS.json',public);write(out/'PLACEBO_SPECS.json',placebos)
    write(HERE/'INVENTORY.json',inventory)
    with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz') as t:
        for name in ['PUBLIC_INPUTS.json','PLACEBO_SPECS.json']:t.add(out/name,arcname=name)
    write(HERE/'BUILD_VALIDATION.json',dict(native=1008,placebo=84,categories=12,per_category_arm=42,templates_per_arm=6,surfaces=7,unique_native_prompts=True,no_dev_fit=True,all_read_positions_final=True,read_token_ids=sorted({x['input_ids'][-1] for x in public}),fixed_delayed_opening_token_count=len(tok.encode('At the park,',add_special_tokens=False)),tokenizer_sha256=sha(TOK),model_calls=0,reader_outputs_opened=False))
    write(HERE/'INPUT_RECEIPT.json',dict(experiment='E108',public_directory=str(out),files={p.name:sha(p) for p in out.iterdir() if p.is_file()},source_items=1008,reader_cells=2016,placebo_vectors=84,placebo_reader_cells=168,base_max_new_tokens=64,seed=SEED,raw_prefix=True))
    print('E108 inputs: 1008 native +84 placebo specs; no outputs.')
if __name__=='__main__':build()
