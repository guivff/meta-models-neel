"""CPU-only E46 persistence, sealed before reader access. Never joins scores."""
from io46 import *
from states import state
import argparse,importlib.util,statistics

def run(receipt_path):
    with (HERE/'PERSISTENCE_ATTEMPT.lock').open('x') as f:f.write('E46 once-only persistence\n')
    verify(HERE,'CODE_SEAL.json')
    verify(HERE,'BANK_SEAL.json')
    source=read(HERE/'BANK_SOURCE_SEAL.json')
    for n,h in source['source_files'].items():
        if sha(HERE/n)!=h:raise ValueError('frozen author/checker source changed')
    state_seal=read(HERE/'STATE_FUNCTION_SEAL.json')
    for n,h in state_seal['files'].items():
        path=HERE.parent/n if n.startswith('e42/') else HERE/n
        if sha(path)!=h:raise ValueError('state/core changed')
    r=read(receipt_path)
    if r.get('issuer')!='integrator' or r.get('experiment')!='E46' or r.get('verified') is not True:raise ValueError('verified integrator pull required')
    source=Path(r['output_directory']);verify(source,'FOLLOWING_TEXT_SEAL.json',r['following_text_seal_sha256'])
    plan=read(HERE/'RUN_PLAN.json');prov=read(source/'PROVENANCE.json')
    expected={'experiment':'E46','status':'COMPLETE','plan_sha256':sha(HERE/'RUN_PLAN.json'),'input_seal_sha256':plan['input_seal_sha256'],'state_seal_sha256':sha(HERE/'STATE_FUNCTION_SEAL.json'),'source':'model-expected continuation','greedy':True,'tokens':32,'EOS_stopping':False,'items':336,'seed':20261026,'model':'Qwen/Qwen3.6-27B','revision':'6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'}
    if any(prov.get(k)!=v for k,v in expected.items()):raise ValueError('following text provenance mismatch')
    items=[x for x in read(HERE/'cache/prepared/items.PRIVATE.json') if x['split']=='test']
    generated=rows(source/'continuations.jsonl');g={x['key']:x for x in generated}
    if len(g)!=len(generated) or set(g)!={'E46/'+x['id'] for x in items}:raise ValueError('following text coverage')
    from transformers import PreTrainedTokenizerFast
    tp=Path(r['tokenizer_json'])
    if sha(tp)!=read(HERE/'VALIDATION.json')['tokenizer_sha256']:raise ValueError('tokenizer mismatch')
    tok=PreTrainedTokenizerFast(tokenizer_file=str(tp))
    spec=importlib.util.spec_from_file_location('e42_frozen_persistence',HERE.parent/'e42/persistence_core.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    out=HERE/'persistence_2026-10-26';out.mkdir(exist_ok=False);ledger=[]
    for item in items:
        v=g['E46/'+item['id']]
        if v['prefix_ids_sha256']!=hashlib.sha256(json.dumps(item['ids'],separators=(',',':')).encode()).hexdigest():raise ValueError('prefix changed')
        n=core.persistence(item['ids'],v['following_ids'],item['value'],lambda ids:tok.decode(ids),lambda text:state(item,text))
        ledger.append({'id':item['id'],'row':item['feature'],'label':item['label'],'persistence':n})
    private=HERE/'cache/persistence_items.json';dump(private,ledger)
    summaries=[]
    for name,definition in read(HERE/'ROW_DEFINITIONS.json')['rows'].items():
        rs=[x for x in ledger if x['row']==name];valid=[x['persistence'] for x in rs if x['persistence'] is not None];median=statistics.median(valid) if valid else None
        excluded=len(rs)-len(valid);evaluable=excluded/len(rs)<=.2 and median is not None
        eligible=evaluable and (median>=24 if definition['cell']=='long' else median<=4)
        summaries.append({'row':name,'cell':definition['cell'],'n':len(rs),'excluded_initial_unknown':excluded,'median':median,'eligible':eligible,'status':'ELIGIBLE' if eligible else 'CELL_MISS' if evaluable else 'NOT EVALUABLE'})
    dump(out/'ROW_MEDIANS.json',{'rows':summaries,'bank_seal_sha256':sha(HERE/'BANK_SEAL.json'),'state_seal_sha256':sha(HERE/'STATE_FUNCTION_SEAL.json'),'following_text_seal_sha256':r['following_text_seal_sha256'],'item_ledger_sha256':sha(private),'reader_scores_accessed':False})
    seal(out,['ROW_MEDIANS.json'],'PERSISTENCE_SEAL.json')
    print('Persistence sealed:',sha(out/'PERSISTENCE_SEAL.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);run(p.parse_args().receipt)
