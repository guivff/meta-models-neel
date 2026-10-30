"""§106/107 model-free preparation and dev-only selection. No test labels on worker."""
import argparse
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify
from .followup_packed import jsonl
from .e12 import CONTEXT_PREFIX

Q1_SHA='55f105bc92ce44f3d58d6e8044e100f18b3a50e10315c9c54dbcd6326585943f'
KINDS=['direct_question','statement','reader_native','which_more_likely','paraphrase1','paraphrase2','plain_value1','plain_value2']
READERS={'olens':44,'nla':42,'base':None}
SEED=20261023


def validate_free(records,request):
    expected={(r['id'],n,j) for r in request['items'] for n in ['olens','nla'] for j in range(4)}
    if len(request['items'])!=60 or len(records)!=480 or {(r['id'],r['reader'],r['sample']) for r in records}!=expected:raise ValueError('complete exact480free grid required')
    if any(set(r)!={'id','reader','layer','sample','raw'} or r['layer']!=READERS[r['reader']] or not isinstance(r['raw'],str) for r in records):raise ValueError('free record schema/native site mismatch')


def phrasings(w1,original):
    """Keep E5's six rows verbatim; extend its eight forms mechanically, before scoring."""
    out={}
    for feature,spec in sorted(w1.items()):
        if feature in original:
            reader_pairs={name:original[feature][name] for name in ['olens','nla']}
        else:
            # All three lexical roles use existing W1 descriptions. No new synonym choice,
            # score-driven editing or outcome-dependent phrasing authoring.
            a,b=[s.removeprefix('- ') for s in spec['olens'][0]];c,d,e,g=a,b,a,b
            pairs=[(f'Does the current excerpt involve {a}? Yes.',f'Does the current excerpt involve {a}? No.'),
                (f'The current excerpt has {a}.',f'The current excerpt has {b}.'),
                (f'The read position indicates {a}.',f'The read position indicates {b}.'),
                (f'It is more likely that this excerpt involves {a}.',f'It is more likely that this excerpt involves {b}.'),
                (f'This is {c}.',f'This is {d}.'),(f'The relevant property is {c}.',f'The relevant property is {d}.'),
                (f'In plain words: {e}.',f'In plain words: {g}.'),(f'The text expresses {e}.',f'The text expresses {g}.')]
            reader_pairs={n:[list(p) for p in pairs] for n in ['olens','nla']}
            reader_pairs['olens'][2]=['- '+s for s in pairs[2]]
        assert reader_pairs['olens'][:2]==reader_pairs['nla'][:2]
        out[feature]={**reader_pairs,'base':reader_pairs['nla'][:2],'kinds':KINDS,'class':spec['class'],'values':spec['values']}
    return out


def base_head(tok,text):
    # E12's exact source wrapper, no native-reader instruction, placeholder or injection.
    ids=tok.apply_chat_template([{'role':'user','content':CONTEXT_PREFIX.format(text=text)}],
        tokenize=True,add_generation_prompt=True,enable_thinking=False)
    return list(ids['input_ids'] if hasattr(ids,'keys') else ids)


def choose(dev_scores,dev_labels,templates,reader,expected_ids):
    """Only frozen development labels are accepted; lowest frozen index breaks exact ties."""
    import common
    from mats.metrics import auroc_labels
    if len(dev_scores)!=len(expected_ids) or {r['id'] for r in dev_scores}!=set(expected_ids):raise ValueError('complete dev score grid required')
    if set(dev_labels)!=set(expected_ids):raise ValueError('only exact dev labels permitted for selection')
    index={r['id']:r for r in dev_scores};selected={}
    for f,spec in sorted(templates.items()):
        ids=[key for key in expected_ids if index[key]['feature']==f]
        y=[dev_labels[k] for k in ids];s=np.asarray([index[k]['scores'] for k in ids],float)
        if s.shape!=(len(ids),len(spec[reader])) or not np.isfinite(s).all():raise ValueError('finite complete development phrasing grid required')
        auc=[float(auroc_labels(s[:,j],y)) for j in range(s.shape[1])]
        if not np.isfinite(auc).all():raise ValueError('two-valued development row required')
        j=int(np.argmax(auc));selected[f]={'index':j,'kind':KINDS[j],'dev_aurocs':auc,'pair':spec[reader][j]}
    return selected


def prepare(out,q1):
    from transformers import AutoTokenizer
    shared=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache')
    source=shared/'g_agreement/blindspot/w1-readonly-20261024';bank=source/'w1-bank-v2';target=source/'w1-assembled/target'
    verify(bank,'INPUT_SEAL.json');verify(target)
    private=bank/'items.DO_NOT_STAGE.jsonl';manifest=read(bank/'manifest.json')
    if sha(private)!=manifest['files']['items.DO_NOT_STAGE.jsonl']:raise ValueError('W1 private hash mismatch')
    full=rows(private);w1=read(bank/'templates.json');selected=read(ROOT/'cache/g_agreement/understand/e1b_e12/e12/templates.json')
    records=[r for r in full if r['feature'] in selected and r['split'] in ['dev','test']]
    assert len(records)==4200
    original_path=ROOT/'results/g_agreement/understand/e16/E5_ORIGINAL.json';original=read(original_path)
    templates=phrasings({f:w1[f] for f in selected},original)
    if sha(q1)!=Q1_SHA:raise ValueError('exact lens-chat Q1 request required')
    request=read(q1);qitems=request['items']
    if len(qitems)!=60 or len({r['id'] for r in qitems})!=60 or request['expected_records']!=480:raise ValueError('exact 60-item Q1 grid required')
    s84=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement/blindspot/w1b-bank-v1')
    s84target=s84.parent/'w1b-units/ybqkwg5zoc3vwg/w1b-out/target'
    banks={'w1':bank,'s84':s84};captures={'w1':target,'s84':s84target};lineage={};free_acts={42:[],44:[]}
    for name,b in banks.items():
        if sha(b/'INPUT_SEAL.json')!=request['input_bank_seal_hashes'][name]:raise ValueError('Q1 input bank seal mismatch')
        verify(b,'INPUT_SEAL.json');capture=captures[name]
        sealname='SCORE_SEAL.json' if name=='w1' else 'CAPTURE_SEAL.json';verify(capture,sealname)
        prov=read(capture/('provenance.target.json' if name=='w1' else 'provenance.capture.json'))
        if prov.get('input_seal_sha256')!=sha(b/'INPUT_SEAL.json'):raise ValueError('captured activation provenance points to another input bank')
        # Bank/ID order linkage is checked below against the public label-free item file.
        public={r['id']:r for r in rows(b/'items.input.jsonl')};order=read(capture/'items.order.json')
        if len(order)!=len(set(order)) or set(order)!=set(public):raise ValueError('captured bank ID coverage mismatch')
        lookup={k:i for i,k in enumerate(order)};arrays={l:np.load(capture/f'acts{l}.npy',mmap_mode='r',allow_pickle=False) for l in [42,44]}
        lineage[name]={'bank_input_seal_sha256':sha(b/'INPUT_SEAL.json'),'capture_seal_sha256':sha(capture/sealname),'capture_order_sha256':sha(capture/'items.order.json'),'capture_path':str(capture),'input_bank_path':str(b)}
        for r in qitems:
            if r['bank']!=name:continue
            if r['id'] not in lookup or public[r['id']]['feature']!=r['feature']:raise ValueError('Q1 ID/feature absent from exact source bank')
        # Never read Q1 ITEM_KEY or any §84 private truth/prefix file.
        for layer in [42,44]:
            lineage[name]['acts'+str(layer)+'_sha256']=sha(capture/f'acts{layer}.npy')
        lineage[name]['_lookup']=lookup;lineage[name]['_arrays']=arrays
    for r in qitems:
        entry=lineage[r['bank']]
        for layer in [42,44]:free_acts[layer].append(np.asarray(entry['_arrays'][layer][entry['_lookup'][r['id']]],np.float32))
    for v in lineage.values():del v['_lookup'];del v['_arrays']
    out.mkdir(parents=True,exist_ok=False);(out/'E16_ITEM_REQUEST.json').write_bytes(q1.read_bytes());jsonl(out/'free.input.jsonl',qitems)
    public=[{'id':r['id'],'feature':r['feature'],'split':r['split'],'text':r['text']} for r in records]
    jsonl(out/'items.input.jsonl',public);dump(out/'templates.json',templates)
    for split in ['dev','test']:dump(out/f'{split}_ids.json',[r['id'] for r in records if r['split']==split])
    dev=[{'id':r['id'],'y':r['value']==w1[r['feature']]['values'][0]} for r in records if r['split']=='dev'];jsonl(out/'dev.labels.input.jsonl',dev)
    order=read(target/'items.order.json');ix={k:i for i,k in enumerate(order)}
    for layer in [42,44]:
        np.save(out/f'acts{layer}.npy',np.load(target/f'acts{layer}.npy',mmap_mode='r',allow_pickle=False)[[ix[r['id']] for r in records]],allow_pickle=False)
        a=np.asarray(free_acts[layer],np.float32)
        if a.shape!=(60,5120) or not np.isfinite(a).all():raise ValueError('invalid Q1 native activations')
        np.save(out/f'free_acts{layer}.npy',a,allow_pickle=False)
    tokpath=shared/'g_assets/Qwen__Qwen3.6-27B';tok=AutoTokenizer.from_pretrained(tokpath,local_files_only=True)
    units={}
    for split in ['dev','test']:
        native=[];base=[]
        for f in sorted(templates):
            ids=[i for i,r in enumerate(public) if r['feature']==f and r['split']==split]
            assert len(ids)==84
            native += [{'feature':f,'indices':ids[s:s+16]} for s in range(0,len(ids),16)]
            groups={}
            for i in ids:groups.setdefault(len(base_head(tok,public[i]['text'])),[]).append(i)
            for length,group in sorted(groups.items()):base += [{'feature':f,'head_length':length,'indices':group[s:s+16]} for s in range(0,len(group),16)]
        units[split]={'native':native,'base':base}
    units['free']=[{'indices':list(range(s,min(60,s+20)))} for s in range(0,60,20)]
    dump(out/'units.json',units)
    provenance={'authority_commit':'1095e4e9','q1_request_sha256':Q1_SHA,'q1_request_commit':'fb6fcd05','free_source_banks':lineage,
        'W1_target_seal_sha256':sha(target/'SCORE_SEAL.json'),'W1_private_sha256':sha(private),'W1_bank_seal_sha256':sha(bank/'INPUT_SEAL.json'),
        'base_tokenizer_sha256':sha(tokpath/'tokenizer.json'),'base_prefix':CONTEXT_PREFIX,'base_carrier':'user source wrapper only;no reader instruction/placeholder; E5 full candidate strings follow assistant header;no injection,adapter disabled',
        'E5_original_sha256':sha(original_path),'extension':'six E5 rows verbatim; remaining19 same8literalforms with alreadyfrozenW1descriptionpair in eachlexicalrole;frozenbeforecompute',
        'test_labels_staged':False,'selection':'devAUROC only;exactties lowestfrozenindex;sealbeforefirsttestcall;testselectedpaironce;no refit/signflip',
        'free_decoding':{'samples':4,'temperature':[0,.7,.7,.7],'max_new_tokens':128,'top_p_sampled':.95,'top_k_sampled':64,'seed':20261024,'batch_items':20,'batch_sequences':32,'raw_output':'verbatim decoded completion, no extraction or strip;failed/empty output retained'}}
    dump(out/'provenance.json',provenance);names=[p.name for p in out.iterdir() if p.is_file()]
    dump(out/'INPUT_SEAL.json',{'status':'E16_DEV_TEST_AND_Q1_INPUTS_FROZEN','files':{n:sha(out/n) for n in names}})
    report=ROOT/'results/g_agreement/understand/e16';dump(report/'PREPARATION.json',{'path':str(out),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'q1_request_sha256':Q1_SHA,'private_labels_local':str(private),'private_labels_sha256':sha(private),'items':4200,'test_items':2100,'dev_items':2100,'free_items':60,'free_records':480,'units':{s:{k:len(v) for k,v in p.items()} for s,p in units.items() if isinstance(p,dict)},'GPU_hours':0,'Q1_keys_opened':False})
    (report/'templates.json').write_bytes((out/'templates.json').read_bytes());(report/'E16_ITEM_REQUEST.json').write_bytes(q1.read_bytes());(report/'INPUT_SEAL.json').write_bytes((out/'INPUT_SEAL.json').read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--q1',type=Path,required=True);a=p.parse_args();prepare(a.out,a.q1)
