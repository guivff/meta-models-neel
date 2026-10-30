"""E12 preparation: frozen context carriers and four-arm injection policy; no model forwards."""
from pathlib import Path
import argparse
import hashlib
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify

ARMS=('activation_only','text_activation','text_only','text_wrong_activation')
CONTEXT_PREFIX=(
    'The following is the source text up to and including the read position.\n'
    '<source_text>\n{text}\n</source_text>\n\n'
)


def user_message(native_request,text,arm):
    if arm not in ARMS:raise ValueError('unknown E12 arm')
    return native_request if arm=='activation_only' else CONTEXT_PREFIX.format(text=text)+native_request


def carrier(tok,native_request,text,arm,marker_token_id):
    content=user_message(native_request,text,arm)
    output=tok.apply_chat_template([{'role':'user','content':content}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    ids=list(output['input_ids'] if hasattr(output,'keys') else output)
    slots=[i for i,t in enumerate(ids) if t==marker_token_id]
    if len(slots)!=1:raise ValueError('injection marker must occur once;do not repair or drop context')
    return ids,slots[0]


def activation_for(arm,recipient,wrong):
    if arm not in ARMS:raise ValueError('unknown E12 arm')
    if arm=='text_only':return None  # Keep placeholder's own embedding. Zero-vector injection is not equivalent.
    return wrong if arm=='text_wrong_activation' else recipient


def main():
    import common,yaml
    from transformers import AutoTokenizer
    from mats.readers.olens import OracleLens
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'cache/g_agreement/understand/e12');a=p.parse_args()
    shared=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache')
    w=shared/'g_agreement/blindspot/w1-readonly-20261024';bank=w/'w1-bank-v2';target=w/'w1-assembled/target'
    verify(bank,'INPUT_SEAL.json');verify(target)
    manifest=read(bank/'manifest.json');private=bank/'items.DO_NOT_STAGE.jsonl'
    if sha(private)!=manifest['files']['items.DO_NOT_STAGE.jsonl']:raise ValueError('frozen private item hash mismatch')
    full=rows(private);public=rows(bank/'items.input.jsonl');mapping={r['id']:r for r in public};item_lookup={r['id']:r for r in full}
    selected={r['feature'] for r in read(ROOT/'results/g_agreement/blindspot/mechanism/w3/analysis_rk4veemwm0jf9i/metrics.residual.json')['rows']}
    test=[r for r in full if r['feature'] in selected and r['split']=='test'];assert len(test)==2100
    input_ids=[r['id'] for r in test];position={key:i for i,key in enumerate(input_ids)}
    target_order=read(target/'items.order.json');assert target_order==[r['id'] for r in full];source_index={key:i for i,key in enumerate(target_order)}
    target_tok=shared/'g_assets/Qwen__Qwen3.6-27B'
    nla_tok=Path('/Users/guivff/Documents/Neel_Exploration/wt-inverter/cache/g_agreement/r/prompt_secret/nla_tokenizer_bound_20261021')
    assert sha(target_tok/'tokenizer.json')=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    assert sha(nla_tok/'tokenizer.json')=='87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4'
    tok=AutoTokenizer.from_pretrained(target_tok,local_files_only=True);ntok=AutoTokenizer.from_pretrained(nla_tok,local_files_only=True)
    oracle=OracleLens(model=None,tok=tok,device='cpu');native_ids,slot=oracle.carrier(44);marker=native_ids[slot];char=tok.decode([marker],skip_special_tokens=False)
    native_ol=oracle.prompt.format(layer=44,char=char)
    meta_path=shared/'g_assets/ceselder__qwen3.6-27b-nla-rl/nla_meta.yaml';meta=yaml.safe_load(meta_path.read_text())
    native_nla=meta['prompt_templates']['actor'].format(injection_char=meta['tokens']['injection_char'])
    native_records={'olens':{'request':native_ol,'marker_token_id':marker,'layer':44,'tokenizer_json_sha256':sha(target_tok/'tokenizer.json')},'nla':{'request':native_nla,'marker_token_id':meta['tokens']['injection_token_id'],'layer':42,'tokenizer_json_sha256':sha(nla_tok/'tokenizer.json')}}
    a.out.mkdir(exist_ok=False,parents=True);records=[];validation={'olens':0,'nla':0};max_lengths={'olens':0,'nla':0}
    for it in test:
        wrong_id=mapping[it['id']]['donor_id'];wrong=item_lookup[wrong_id]
        if wrong_id not in position or wrong['feature']!=it['feature'] or wrong['value']==it['value'] or wrong['cluster']!=it['cluster']:
            raise ValueError('W1 frozen opposite-value donor contract differs')
        assert it['meta']['read_position']==len(it['ids'])-1
        assert tok.encode(it['text'],add_special_tokens=False)==it['ids']
        for reader,t in [('olens',tok),('nla',ntok)]:
            spec=native_records[reader]
            native=carrier(t,spec['request'],it['text'],'activation_only',spec['marker_token_id'])
            carriers=[carrier(t,spec['request'],it['text'],arm,spec['marker_token_id']) for arm in ARMS[1:]]
            if not carriers[0]==carriers[1]==carriers[2]:raise ValueError('context arms use different prompts')
            if reader=='olens' and native!=(native_ids,slot):raise ValueError('activation-only Oracle native carrier drift')
            validation[reader]+=1;max_lengths[reader]=max(max_lengths[reader],len(carriers[0][0]))
        records.append({'id':it['id'],'feature':it['feature'],'text':it['text'],'ids':it['ids'],'read_position':it['meta']['read_position'],'wrong_activation_id':wrong_id,'wrong_activation_index':position[wrong_id]})
    from .worker import jsonl
    jsonl(a.out/'items.input.jsonl',records);dump(a.out/'templates.json',{f:read(bank/'templates.json')[f] for f in sorted(selected)})
    dump(a.out/'ids.json',input_ids)
    ix=[source_index[key] for key in input_ids]
    for layer in [42,44]:np.save(a.out/f'acts{layer}.npy',np.load(target/f'acts{layer}.npy',allow_pickle=False)[ix],allow_pickle=False)
    provenance={'bank_seal_sha256':sha(bank/'INPUT_SEAL.json'),'target_seal_sha256':sha(target/'SCORE_SEAL.json'),'private_items_sha256':sha(private),'population':'all25rows,84testitems each','donor_map':'exact W1 public donor_id;opposite value,reciprocal,within same template cluster;no redraw','native_carriers':native_records,'prefix':CONTEXT_PREFIX,'score_candidates':'exact two W1 frozen phrasing pairs,unchanged;native paired log-odds','validation':'tokenization only,no model forward','validated_prefix_items':validation,'max_context_carrier_tokens':max_lengths}
    dump(a.out/'provenance.json',provenance);names=['items.input.jsonl','templates.json','ids.json','acts42.npy','acts44.npy','provenance.json']
    dump(a.out/'INPUT_SEAL.json',{'status':'E12_PREPARATION_FROZEN_BEFORE_SCORING','files':{n:sha(a.out/n) for n in names}})
    results=ROOT/'results/g_agreement/understand/e12';results.mkdir(exist_ok=True)
    dump(results/'PREPARATION.json',{'status':'PREPARATION_COMPLETE_SCORER_INTEGRATION_PENDING','path':str(a.out),'input_seal_sha256':sha(a.out/'INPUT_SEAL.json'),'n_items':2100,'n_rows':25,'native_prefix_tokenization_verified':validation,'native_model_forward_compatibility':'NOT YET TESTED','max_context_carrier_tokens':max_lengths,'GPU_hours':0})
    dump(results/'INPUT_SEAL.json',read(a.out/'INPUT_SEAL.json'))
    print('E12prepared',len(records),'items;native prefix tokenization',validation,'max lengths',max_lengths)


if __name__=='__main__':main()
