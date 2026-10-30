"""CPU-only E127 values/prefixes, frozen before any model output."""
import hashlib,json,re,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import sha,write,read,verify
ROOT=Path(__file__).resolve().parents[3]
SEED=20261030
PATTERN=r'Current question: The capital of (.+) is$'
TEMPLATE='In this reference work, the capital of {entity} is {value}.'
# Fixed genuine third-entity facts, declared before output; original bank has only France/Peru.
NEUTRAL_FACTS={'Italy':'Rome','Spain':'Madrid','Japan':'Tokyo','Germany':'Berlin','Canada':'Ottawa','Portugal':'Lisbon'}


def prefix_pair(text,original_ids,new_value,pool,tok,rng):
    match=re.search(PATTERN,text)
    if match is None:raise ValueError('original final capital question and read token')
    entity=match.group(1);update=TEMPLATE.format(entity=entity,value=new_value)
    ids=tok.encode(update+'\n'+text,add_special_tokens=False)
    if ids[-len(original_ids):]!=original_ids:raise ValueError('original prompt token suffix must remain byte-identical')
    mentioned=set(re.findall(r'The capital of (.+?) is',text))
    options=[]
    for other,value in sorted(pool.items()):
        if other in mentioned or other==entity or value==new_value:continue
        neutral=TEMPLATE.format(entity=other,value=value);ni=tok.encode(neutral+'\n'+text,add_special_tokens=False)
        if len(ni)==len(ids)and ni[-len(original_ids):]==original_ids:options.append((other,value,neutral,ni))
    if not options:raise ValueError('no genuine unrelated fact with exact matched prefix token length; no padding fallback')
    other,value,neutral,ni=options[int(rng.integers(len(options)))]
    return ids,ni,dict(entity=entity,new_value=new_value,update_prefix=update,neutral_entity=other,neutral_value=value,neutral_prefix=neutral,prefix_tokens=len(ids)-len(original_ids),matched_full_token_length=len(ids))


def build(out):
    from transformers import AutoTokenizer
    out=Path(out);out.mkdir(exist_ok=False);public=out/'inputs';public.mkdir();cpu=out/'cpu_only';cpu.mkdir()
    tok=AutoTokenizer.from_pretrained('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_assets/Qwen__Qwen3.6-27B',local_files_only=True,trust_remote_code=False)
    parent=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall')
    verify(parent,'INPUT_SEAL.json','1e91a33f801d1eff72641fee56fa718957c65f57a7667fea5b5145a8db77b04a')
    original=[x for x in read(parent/'items.json')if x['condition']=='steered'];assert len(original)==84
    src=read(ROOT/'results/g_agreement/understand/e101/vectors/cpu_only/SOURCES.json')['E56'];meta=Path(src['metadata_path']);assert sha(meta)==src['metadata_sha256']
    bank=[x for x in read(meta)if x['feature']=='fact_recall'];by={hashlib.sha256(f'E101:E56:{x["id"]}'.encode()).hexdigest():x for x in bank}
    pool={}
    for x in bank:
        entity=re.search(PATTERN,x['text']).group(1)
        if entity in pool:assert pool[entity]==x['value']
        pool[entity]=x['value']
    private=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E104/PRIVATE.json');assert sha(private)=='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4'
    targets={x['item_id']:x for x in read(private)if x['arm']=='U'and x['row']=='fact_recall'and x['condition']=='steered'}
    rng=np.random.default_rng(SEED);items=[];labels=[];fallback=0
    for n,x in enumerate(original):
        m=by[x['base_id']];assert m['split']=='test'and m['ids']==x['ids']and tok.encode(m['text'],add_special_tokens=False)==x['ids']
        if x['base_id']in targets:
            t=targets[x['base_id']];new=t['values'][t['target']];origin='original E104 sealed steer target'
        else:
            choices=sorted({v for v in pool.values()if v!=m['value']});new=choices[int(rng.integers(len(choices)))];origin='seed20261030 same-capital-relation donor value';fallback+=1
        assert new!=m['value']
        updated,neutral,binding=prefix_pair(m['text'],x['ids'],new,dict(pool,**NEUTRAL_FACTS),tok,rng)
        base=f'E127-{n:04d}';indices={}
        for condition,ids in [('context_update',updated),('neutral_prefix',neutral),('none',x['ids'])]:
            ident=f'{base}:{condition}';indices[condition]=ident
            items.append(dict(id=ident,base_id=base,row='fact_recall',condition=condition,ids=ids,read_index=len(ids)-1,candidate_ids=x['candidate_ids'],input_index=len(items)))
        labels.append(dict(base_id=base,original_base_id=x['base_id'],original_source_id=m['id'],old_value=m['value'],new_value_source=origin,**binding,condition_ids=indices))
    write(public/'items.json',items);write(public/'SCORER.json',read(parent/'SCORER.json'))
    manifest=dict(experiment='E127',authority='§236/2ebe22138',seed=SEED,items=84,cells=252,oracle_layers=[44,52,60],oracle_readouts=756,greedy_answer_tokens=3,hook_enabled=False,prefix_template=TEMPLATE,neutral_reference_facts=NEUTRAL_FACTS,neutral_length='exact full prompt token length matched to context-update; same original suffix, unrelated third entity; no padding',parent_input_sha256=sha(parent/'INPUT_SEAL.json'),e104_private_sha256=sha(private),metadata_sha256=sha(meta),fallback_value_count=fallback)
    write(public/'MANIFEST.json',manifest);write(public/'INPUT_SEAL.json',dict(experiment='E127',labels_on_pod=False,files={p.name:sha(p)for p in public.iterdir()}))
    write(cpu/'LABELS.PRIVATE.json',labels);write(cpu/'LABEL_SEAL.json',dict(experiment='E127',input_sha256=sha(public/'INPUT_SEAL.json'),files={'LABELS.PRIVATE.json':sha(cpu/'LABELS.PRIVATE.json')}))
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as t:
        for p in public.iterdir():t.add(p,arcname=p.name)
    receipt=dict(experiment='E127',public_root=str(public),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(out/'inputs.tar.gz'),archive_sha256=sha(out/'inputs.tar.gz'),cpu_only=dict(root=str(cpu),seal_sha256=sha(cpu/'LABEL_SEAL.json'),stage_to_pod=False),items=84,cells=252,readouts=756,fallback_value_count=fallback,labels_on_pod=False,GPU_calls=0)
    write(ROOT/'results/g_agreement/understand/e127/INPUT_BINDING.json',receipt);return receipt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
