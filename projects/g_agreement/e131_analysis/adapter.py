"""Integrator-only once command. Preparation validates INPUTS ONLY; never discovers outputs."""
import argparse,hashlib,json,math,os
from pathlib import Path
from .rules import CONDITIONS,classify,require,summarize
ROOT=Path(__file__).resolve().parents[3]
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def verify(root,name,digest):
    root=Path(root).resolve();p=root/name;require(sha(p)==digest,'seal digest');s=read(p)
    require(bool(s.get('files')),'nonempty seal')
    for n,h in s['files'].items():
        f=(root/n).resolve();require(f.is_relative_to(root) and sha(f)==h,'sealed member')
    return s

def bind():
    binding=read(ROOT/'results/g_agreement/understand/e131/INPUT_BINDING.json')
    pub=Path(binding['input_root']);cpu=Path(binding['CPU_only_root'])
    verify(pub,'INPUT_SEAL.json',binding['input_sha256']);verify(cpu,'POINTER_SEAL.json',binding['CPU_only_seal_sha256'])
    pointer=read(cpu/'LABEL_SOURCE.json');require(sha(pointer['root'])==pointer['sha256'],'old/new label seal')
    labels={x['base_id']:x for x in read(pointer['root'])}
    require(sha(TOKENIZER)==TOKENIZER_SHA,'pinned tokenizer')
    from transformers import PreTrainedTokenizerFast
    tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
    items=read(pub/'items.json');require(len(items)==840 and len({x['id'] for x in items})==840,'input count')
    bound={}
    for x in items:
        lab=labels[pointer['e131_to_e127_base'][x['base_id']]];old,new=lab['old_value'],lab['new_value']
        pairs=x['candidate_ids'];require(len(pairs)==1 and all(len(v)==1 for v in pairs[0]),'one single-token pair')
        decoded=[tok.decode(v).strip().casefold() for v in pairs[0]]
        require(set(decoded)=={old.casefold(),new.casefold()} and len(set(decoded))==2,'candidate to value binding')
        bound[x['id']]=dict(item=x,old=old,new=new,a_value='old' if decoded[0]==old.casefold() else 'new')
    require({(v['item']['base_id'],v['item']['condition']) for v in bound.values()}=={(b,c) for b in pointer['e131_to_e127_base'] for c in CONDITIONS},'input grid')
    return binding,bound,tok

def validate_record(r,x,tok):
    require(all(r.get(k)==x[k] for k in ('id','base_id','condition')),'record/input identity')
    ids=r['token_ids'];require(1<=len(ids)<=64 and all(type(i)is int and i>=0 for i in ids),'generation token count')
    require(r['greedy_max_new_tokens']==64 and r['first_greedy_token_id']==ids[0],'generation contract')
    require(r['stop_reason'] in ('eos','length') and (r['stop_reason']!='length' or len(ids)==64),'stop contract')
    require(r['text']==tok.decode(ids,skip_special_tokens=True) and r['text_with_special_tokens']==tok.decode(ids,skip_special_tokens=False),'text/token agreement')
    lp=r['pair_logprobs'];lg=r['pair_logits'];require(len(lp)==len(lg)==1 and len(lp[0])==len(lg[0])==2,'pair shapes')
    vals=lp[0]+lg[0]+[r['pair_mean_a_minus_b']];require(all(isinstance(v,(int,float)) and math.isfinite(v) for v in vals),'finite pair scores')
    margin=lp[0][0]-lp[0][1]
    require(abs(margin-r['pair_mean_a_minus_b'])<1e-5 and abs(margin-(lg[0][0]-lg[0][1]))<1e-3,'ordered same-forward pair consistency')
    return margin

def output_header(seal):
    require(seal.get('experiment')=='E131' and seal.get('status')=='COMPLETE' and seal.get('cells')==840 and seal.get('max_new_tokens')==64 and seal.get('reader_calls')==seal.get('judging_calls')==0,'complete registered generation only')

def main():
    p=argparse.ArgumentParser();p.add_argument('--validate-inputs-only',action='store_true');p.add_argument('--output-root',type=Path);p.add_argument('--output-seal-sha256');p.add_argument('--analysis-root',type=Path);a=p.parse_args()
    code=read(Path(__file__).with_name('CODE_SEAL.json'))
    for n,h in code['files'].items():require(sha(ROOT/n)==h,'frozen analysis code')
    binding,bound,tok=bind()
    if a.validate_inputs_only:
        require(a.output_root is None and a.analysis_root is None,'inputs only');print(json.dumps(dict(status='INPUTS_VALIDATED',cells=len(bound),output_opened=False)));return
    require(a.output_root is not None and a.output_seal_sha256 is not None and a.analysis_root is not None,'explicit verified pull and output digest required')
    # One fixed attempt guard shared across checkouts; acquired before opening output.
    guard=Path(binding['CPU_only_root']).parent/'E131_ANALYSIS239_ONCE.json'
    fd=os.open(guard,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as f:json.dump(dict(output_root=str(a.output_root),output_sha256=a.output_seal_sha256,code_sha256=sha(Path(__file__).with_name('CODE_SEAL.json'))),f)
    a.analysis_root.mkdir(parents=True,exist_ok=False)
    seal=verify(a.output_root,'OUTPUT_SEAL.json',a.output_seal_sha256)
    output_header(seal)
    require('INDEX.json' in seal['files'],'sealed output index')
    index=read(a.output_root/'INDEX.json');require(len(index)==840 and {e['id'] for e in index}==set(bound),'full output index')
    rows=[];cache={};slots=set()
    for e in index:
        require(e['member'] in seal['files'] and (e['member'],e['record']) not in slots,'sealed unique index slot');slots.add((e['member'],e['record']))
        if e['member'] not in cache:cache[e['member']]=read(a.output_root/e['member'])
        require(type(e['record']) is int and 0<=e['record']<len(cache[e['member']]),'index record bounds')
        r=cache[e['member']][e['record']];b=bound[e['id']];margin=validate_record(r,b['item'],tok)
        rows.append(dict(id=r['id'],base_id=r['base_id'],condition=r['condition'],**classify(r['text'],b['old'],b['new'],margin,b['a_value'])))
    require(len(index)==sum(len(v) for v in cache.values()),'no unindexed records')
    metrics=summarize(rows)
    write(a.analysis_root/'CLASSIFICATIONS.PRIVATE.json',rows);write(a.analysis_root/'METRICS.json',metrics)
    write(a.analysis_root/'ANALYSIS_SEAL.json',dict(experiment='E131',status='COMPLETE_ONCE',input_sha256=binding['input_sha256'],output_sha256=a.output_seal_sha256,code_sha256=sha(Path(__file__).with_name('CODE_SEAL.json')),files={p.name:sha(p) for p in a.analysis_root.iterdir()}))
    print(json.dumps(dict(status='COMPLETE_ONCE',seal_sha256=sha(a.analysis_root/'ANALYSIS_SEAL.json'))))
if __name__=='__main__':main()
