"""CPU-only frozen E136 input exporter, never loads weights or outputs."""
import argparse,json,hashlib,tarfile
from pathlib import Path
from transformers import AutoTokenizer
from .bank import generate,validate,SEED
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);pub=out/'inputs';pub.mkdir();cpu=out/'cpu_only';cpu.mkdir()
    rows=generate();validate(rows);tok=AutoTokenizer.from_pretrained(TOKENIZER,local_files_only=True)
    items=[];labels=[]
    for x in rows:
        text=tok.apply_chat_template(x['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        ids=tok.encode(text,add_special_tokens=False)
        candidates=[tok.encode(' '+x[k],add_special_tokens=False) for k in ['correct','wrong']]
        if not all(len(c)==1 for c in candidates):raise ValueError('candidate not single token for base task '+str(x['base_task']))
        if candidates[0]==candidates[1]:raise ValueError('distinct candidates')
        pair=sorted(candidates,key=lambda c:c[0])
        items.append(dict(id=x['id'],ids=ids,read_index=len(ids)-1,candidate_ids=[pair]))
        labels.append(dict(id=x['id'],pair_id=x['pair_key'],base_task=x['base_task'],template=x['template'],cue=x['cue'],label=x['label'],split=x['split'],correct=x['correct'],wrong=x['wrong'],correct_pair_index=pair.index(candidates[0]),messages=x['messages']))
    if len({x['ids'][-1] for x in items})!=1:raise ValueError('shared final rendered read token')
    source={n:sha(TOKENIZER/n) for n in ['tokenizer.json','tokenizer_config.json','chat_template.jinja']}
    manifest=dict(experiment='E136',authority='§24774b25641d',prompts=800,pairs=400,seed=SEED,tokenizer_repo='Qwen/Qwen3.6-27B',tokenizer_revision=TOKENIZER.name,tokenizer_files=source,render=dict(add_generation_prompt=True,enable_thinking=False,add_special_tokens=False,truncation=False,read='last token of exact rendered chat; final assistant onset'),public_schema=['id','ids','read_index','candidate_ids'],answer_pair='one leading-space single-token pair, tokenIDs ascending; truth sign CPU-only',labels_on_pod=False)
    write(pub/'items.json',items);write(pub/'MANIFEST.json',manifest)
    write(pub/'INPUT_SEAL.json',dict(experiment='E136',labels_on_pod=False,files={p.name:sha(p) for p in pub.iterdir()}))
    write(cpu/'LABELS.PRIVATE.json',labels);write(cpu/'LABEL_SEAL.json',dict(experiment='E136',input_sha256=sha(pub/'INPUT_SEAL.json'),files={'LABELS.PRIVATE.json':sha(cpu/'LABELS.PRIVATE.json')}))
    with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz') as t:
        for p in sorted(pub.iterdir()):t.add(p,arcname=p.name)
    result=dict(experiment='E136',input_root=str(pub.resolve()),input_seal_sha256=sha(pub/'INPUT_SEAL.json'),public_archive=str((out/'PUBLIC_INPUTS.tar.gz').resolve()),public_archive_sha256=sha(out/'PUBLIC_INPUTS.tar.gz'),CPU_only_root=str(cpu.resolve()),CPU_label_seal_sha256=sha(cpu/'LABEL_SEAL.json'),items=800,pairs=400,dev_pairs_per_cue=20,test_pairs_per_cue=80,base_tasks=25,templates=4,cues=4,single_token_pairs=800,shared_read_token=items[0]['ids'][-1],max_tokens=max(len(x['ids']) for x in items),tokenizer=manifest['tokenizer_repo'],tokenizer_revision=manifest['tokenizer_revision'],tokenizer_files=source,render=manifest['render'],model_calls=0,reader_calls=0,judge_calls=0)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
