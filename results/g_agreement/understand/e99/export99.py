"""Six-family E99 exporter: no wsbench imports or execution, no model calls."""
import hashlib,json,random,re,tarfile
from pathlib import Path
from transformers import PreTrainedTokenizerFast
from source99 import HERE,SOURCE,PIN,sha,dump,verify_pin
from positions99 import plan
FAMILIES=['hallucination','user_modeling','directed_modulation','agentic_misalignment','jailbreak_recognition','buggy_code']
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
def opaque(f,s):return hashlib.sha256(('E99|'+f+'|'+s).encode()).hexdigest()[:24]
def load(f):
    d=json.loads((SOURCE/'evals'/f/'items.json').read_text());items=d['items']
    if 'name' in items[0]:
        for it in items:it['id']=re.sub(r'[^A-Za-z0-9._-]','_',it['name'])
    assert len({it['id'] for it in items})==len(items)
    return d,items

def main():
    verify_pin();out=HERE/'cache/export_2026-10-28';out.mkdir(parents=True,exist_ok=False)
    assert sha(TOK/'tokenizer.json')=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK/'tokenizer.json'));tok.chat_template=(TOK/'chat_template.jinja').read_text()
    captures={r['id']:r for r in json.loads((SOURCE/'evals/hallucination/capture_rows.json').read_text())}
    targets=json.loads((SOURCE/'evals/agentic_misalignment/targets.json').read_text())
    public=[];private=[];counts={};source_paths=[]
    for family in FAMILIES:
        header,items=load(family);n=0;sites=0;cells=0
        for item in items:
            p=plan(family,item,tok,captures.get(item['id']));ident=opaque(family,item['id'])
            public.append(dict(id=ident,family=family,**p))
            private.append(dict(id=ident,family=family,source_item=item))
            n+=1;sites+=len(p['grid_positions']);cells+=len(p['grid_positions'])*(len(p['grid_oracle_layers'])+1)+2*len(p['extra_single_site_positions'])
        counts[family]=dict(items=n,grid_positions=sites,reader_cells=cells)
        source_paths.append(SOURCE/'evals'/family/'items.json')
    assert len(public)==516 and counts['hallucination']['grid_positions']==1123
    dump(out/'CAPTURE_INPUTS.json',public);dump(out/'ITEMS.PRIVATE.json',private);dump(out/'AGENTIC_TARGETS.PRIVATE.json',targets)
    # Use one seeded draw without replacement per family in this fixed family order.
    rng=random.Random(20261030);placebos=[];bindings=[]
    for family in ['user_modeling','directed_modulation','hallucination']:
        candidates=[r for r in public if r['family']==family]
        for ordinal,r in enumerate(rng.sample(candidates,30)):
            ident=opaque('placebo',f'{family}|{ordinal}|20261030')
            row={k:r[k] for k in ['family','grid_positions','grid_oracle_layers','nla_layer','single_site_position','single_site_oracle_layer','single_site_nla_layer','extra_single_site_positions']}
            row.update(id=ident,paired_capture_id=r['id'],vector_kind='random',seed=20261030,seed_key=ident,
                       norm_rule='Match paired real vector norm separately at every reader/layer/position, E76 method.')
            placebos.append(row);bindings.append(dict(id=ident,paired_real_id=r['id'],family=family,judge_sidecar_rule='Reuse the paired real item response or option list and identical cell structure.'))
    dump(out/'PLACEBO_SPECS.json',placebos);dump(out/'PLACEBO_BINDINGS.PRIVATE.json',bindings)
    with tarfile.open(out/'PUBLIC_CAPTURE.tar.gz','w:gz') as tf:
        for n in ['CAPTURE_INPUTS.json','PLACEBO_SPECS.json']:tf.add(out/n,arcname=n)
    source_paths += [SOURCE/'evals/hallucination/capture_rows.json',SOURCE/'evals/agentic_misalignment/targets.json',SOURCE/'src/wsbench/readplan.py',SOURCE/'src/wsbench/produce/render.py',SOURCE/'src/wsbench/banks.py',SOURCE/'LICENSE']
    refs=out/'reference_data';refs.mkdir()
    for f in FAMILIES:
        for n in ['prompts.py','judge.py']:
            src=SOURCE/'src/wsbench/evals'/f/n;source_paths.append(src);(refs/(f+'_'+n+'.txt')).write_bytes(src.read_bytes())
    dump(HERE/'SOURCE_PROVENANCE.json',dict(pin=PIN,repository='https://github.com/camilablank/workspace-bench',license='MIT',upstream_code_executed=False,agent_instruction_files_opened=False,files={str(p.relative_to(SOURCE)):sha(p) for p in source_paths},tokenizer_files={str(TOK/n):sha(TOK/n) for n in ['tokenizer.json','chat_template.jinja']}))
    dump(HERE/'DELIVERY.json',dict(experiment='E99',counts=counts,items=len(public),placebo_items=90,public_archive=str(out/'PUBLIC_CAPTURE.tar.gz'),public_sha256=sha(out/'PUBLIC_CAPTURE.tar.gz'),files={str(p.relative_to(HERE)):sha(p) for p in out.rglob('*') if p.is_file()},single_site_rule='§206 clarification1 e2151018; onset extras outside DM/JB grid, EOF for bare code',agentic_rule='§206 clarification2 f6a649c9: all three original stages',status='CPU_EXPORT_READY',readouts_generated=0))
    print(json.dumps(counts));print('Exported',len(public),'real and',len(placebos),'placebo items')
if __name__=='__main__':main()
