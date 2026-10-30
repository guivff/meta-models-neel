"""Model-free E1b/E12 input and unit-plan freeze for the integrator's packed pod."""
from pathlib import Path
import argparse
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify
from .e12 import carrier


def units_for(items,templates,spec,tok,batch=16):
    """Right-padding only: equal head lengths within every context scoring batch."""
    units={'native':[],'context':[]}
    for feature in sorted(templates):
        ix=[i for i,r in enumerate(items) if r['feature']==feature]
        units['native'] += [{'arm':'activation_only','feature':feature,'indices':ix[s:s+batch]} for s in range(0,len(ix),batch)]
        groups={}
        for i in ix:
            ids,_=carrier(tok,spec['request'],items[i]['text'],'text_activation',spec['marker_token_id'])
            groups.setdefault(len(ids),[]).append(i)
        for length,group in sorted(groups.items()):
            for s in range(0,len(group),batch):
                for arm in ['text_activation','text_only','text_wrong_activation']:
                    units['context'].append({'arm':arm,'feature':feature,'head_length':length,'indices':group[s:s+batch]})
    return units


def main():
    from transformers import AutoTokenizer
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'cache/g_agreement/understand/e1b_e12');a=p.parse_args()
    base=ROOT/'cache/g_agreement/understand/e12';verify(base,'INPUT_SEAL.json');old=read(base/'provenance.json')
    bank=Path(read(ROOT/'results/g_agreement/understand/PREPARATION.json')['W1_readonly_root'])/'w1-bank-v2'
    manifest=read(bank/'manifest.json');private=bank/'items.DO_NOT_STAGE.jsonl'
    if sha(private)!=manifest['files']['items.DO_NOT_STAGE.jsonl']:raise ValueError('W1 bank private hash mismatch')
    full=rows(private);templates=read(base/'templates.json');selected=set(templates)
    chosen=[r for r in full if r['feature'] in selected and r['split'] in ['dev','test']]
    assert len(chosen)==4200
    a.out.mkdir(exist_ok=False,parents=True);b=a.out/'e1b';b.mkdir();e=a.out/'e12';e.mkdir()
    records=[{'id':r['id'],'feature':r['feature'],'ids':r['ids']} for r in chosen]
    def jsonl(path,rs):path.write_text(''.join(__import__('json').dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rs))
    jsonl(b/'items.input.jsonl',records)
    for split in ['dev','test']:
        ids=[r['id'] for r in chosen if r['split']==split];assert len(ids)==2100;dump(b/(split+'_ids.json'),ids)
    groups={}
    for i,r in enumerate(records):groups.setdefault(len(r['ids']),[]).append(i)
    gu=[{'indices':ix[s:s+32],'length':length} for length,ix in sorted(groups.items()) for s in range(0,len(ix),32)]
    dump(b/'generation_units.json',gu)
    dump(b/'provenance.json',{'W1_bank_seal_sha256':sha(bank/'INPUT_SEAL.json'),'private_items_sha256':sha(private),'population':'25rows;2100dev for CPU ceiling fit +2100test for evaluation; all4200greedy continuations count against E1b cap; AR only2100test continuations',
        'decoding':'exactly16newtokens,greedy,nochat,noEOSstop;rawtokenIDs +verbatimdecodedtext retained;no strip/repair/drop;equal-length rawprefix batches32,no padding',
        'private_labels_not_staged':True,'authority_commit':'ae6ffef7'})
    names=['items.input.jsonl','dev_ids.json','test_ids.json','generation_units.json','provenance.json']
    dump(b/'INPUT_SEAL.json',{'status':'E1B_INPUTS_FROZEN_BEFORE_GENERATION','files':{n:sha(b/n) for n in names}})
    for name in read(base/'INPUT_SEAL.json')['files']:(e/name).write_bytes((base/name).read_bytes())
    items=rows(e/'items.input.jsonl')
    tokenizers={
      'olens':Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B'),
      'nla':Path('/Users/guivff/Documents/Neel_Exploration/wt-inverter/cache/g_agreement/r/prompt_secret/nla_tokenizer_bound_20261021')}
    counts={}
    for reader,path in tokenizers.items():
        spec=old['native_carriers'][reader]
        if sha(path/'tokenizer.json')!=spec['tokenizer_json_sha256']:raise ValueError('tokenizer mismatch')
        tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
        units=units_for(items,templates,spec,tok);dump(e/(reader+'_units.json'),units);counts[reader]={k:len(v) for k,v in units.items()}
        expected={(i,arm) for i in range(2100) for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
        observed=[(i,u['arm']) for phase in units.values() for u in phase for i in u['indices']]
        assert len(observed)==len(expected) and set(observed)==expected
    names=[*read(base/'INPUT_SEAL.json')['files'],'olens_units.json','nla_units.json']
    dump(e/'INPUT_SEAL.json',{'status':'E12_INPUTS_AND_RIGHT_PAD_UNIT_PLAN_FROZEN','files':{n:sha(e/n) for n in names}})
    for tag in ['e1b','e12']:
        r=ROOT/'results/g_agreement/understand'/tag;r.mkdir(exist_ok=True)
        dump(r/'PACKED_INPUT_RECEIPT.json',{'path':str(a.out/tag),'seal_sha256':sha(a.out/tag/'INPUT_SEAL.json'),'private_bank_path':str(bank),'private_items_sha256':sha(private),'GPU_hours':0})
    print('Frozen E1b generation units',len(gu),'E12 scoring units',counts)


if __name__=='__main__':main()
