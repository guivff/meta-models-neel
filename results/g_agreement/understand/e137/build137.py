"""One-time CPU bank freeze; no base model, reader, generation or scoring calls."""
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

from transformers import PreTrainedTokenizerFast
from bank137 import generate,check,SEED,NAMES,PLACES

HERE=Path(__file__).resolve().parent
SNAP=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')


def archive_public(path,items_path):
    """The public archive contains exactly id/prompt records, never role metadata."""
    data=Path(items_path).read_bytes()
    with Path(path).open('xb') as target:
        with gzip.GzipFile(fileobj=target,mode='wb',mtime=0,filename='') as gz:
            with tarfile.open(fileobj=gz,mode='w') as tar:
                info=tarfile.TarInfo('items.json');info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data))


def build():
    assert sha(SNAP/'tokenizer.json')==TOKENIZER_SHA
    tok=PreTrainedTokenizerFast(tokenizer_file=str(SNAP/'tokenizer.json'))
    public,pairs=generate();lookup={r['id']:r['prompt'] for r in public}
    values=NAMES+PLACES
    candidates={word:tok.encode(' '+word,add_special_tokens=False) for word in values}
    assert all(len(ids)==1 for ids in candidates.values())
    tokens=[];pair_lengths=[];boundaries=0
    for pair in pairs:
        lengths=[]
        for m in pair['members']:
            prompt=lookup[m['id']];state=check(prompt)
            ids=tok.encode(prompt,add_special_tokens=False)
            assert ids[-1]==539 and tok.decode([ids[-1]])==' by'
            assert state['current']==m['current_holder'] and state['previous']==m['previous_holder']
            pool=PLACES if pair['relation']=='object_location' else NAMES
            for word in pool:
                assert tok.encode(prompt+' '+word,add_special_tokens=False)==ids+candidates[word]
                boundaries+=1
            rp=[candidates[x][0] for x in pair['recipients']]
            cp=[candidates[x][0] for x in (m['current_holder'],m['previous_holder'])]
            m['continuation_strings']={'current':' '+m['current_holder'],'previous':' '+m['previous_holder'],'twin':' '+m['twin_recipient']}
            m['ordered_recipient_candidate_ids']=rp
            m['current_previous_candidate_ids']=cp
            tokens.append(dict(id=m['id'],input_ids=ids,read_index=len(ids)-1,
                               ordered_recipient_candidate_ids=rp,current_previous_candidate_ids=cp))
            lengths.append(len(ids))
        assert lengths[0]==lengths[1]
        pair_lengths.append(lengths)
    # Everything checked before one-time output creation.
    out=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e137-bank-v1');out.mkdir(parents=True,exist_ok=False)
    dump(out/'items.json',public)
    dump(out/'PAIRS.PRIVATE.json',{'experiment':'E137','seed':SEED,'pairs':pairs,
         'candidate_token_ids':candidates,'parser_target_order':'recipient0, recipient1, previous_holder; role matching on CPU only'})
    dump(out/'TOKENIZATION_CPU.PRIVATE.json',tokens)
    archive_public(out/'PUBLIC_INPUTS.tar.gz',out/'items.json')
    with tarfile.open(out/'PUBLIC_INPUTS.tar.gz') as tar:
        assert tar.getnames()==['items.json']
        decoded=json.load(tar.extractfile('items.json'))
        assert decoded==public and all(set(r)=={'id','prompt'} for r in decoded)
    manifest={'experiment':'E137','authority':'§249 /55583c4b3; e02db7a11 item1 D2 trailing distractors','seed':SEED,'source':'fresh definition-only templates; no old items/outcomes used',
         'base_revision':SNAP.name,'tokenizer_sha256':TOKENIZER_SHA,'render':'raw prefix, no chat/instruction added; ends final by',
         'public_schema':['id','prompt'],'public_archive_members':['items.json'],
         'generation_order':'D1 orders0..149 then D2 orders0..149 then one_hop0..59; member0 then1; cyclic three relations',
         'counts':dict(Counter(p['subdesign']+'/'+p['relation'] for p in pairs)),
         'pairs':360,'prompts':720,'names':list(NAMES),'places':list(PLACES),'read_token_id':539,
         'label_checks':720,'twin_only_final_recipient_checks':360,'single_token_candidate_values':10,
         'candidate_boundary_checks':boundaries,'equal_token_length_pairs':len(pair_lengths),
         'minimum_tokens':min(len(r['input_ids']) for r in tokens),'maximum_tokens':max(len(r['input_ids']) for r in tokens),
         'files':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
         'private_never_staged':['PAIRS.PRIVATE.json','TOKENIZATION_CPU.PRIVATE.json'],
         'source_files':{n:sha(HERE/n) for n in ('bank137.py','build137.py','test_bank137.py')},
         'source_outcomes_opened':False,'GPU_or_model_calls':0,'anti_latest_mention_verified_prompts':600,'D2_returns_to_earlier_holder_verified_prompts':300,'trailing_distractors':'1or2 non-transfer sentences on BOTH D1 and D2, identical across twins, latest name/place never either recipient','original_E133_format':'publicid/prompt; PAIRS and TOKENIZATION CPU schema preserved, added subdesign distinguishes D1/D2 without rewriting original IDs'}
    dump(HERE/'BANK_MANIFEST.json',manifest)
    dump(HERE/'INPUT_SEAL.json',{'experiment':'E137','stage':'screen','labels_on_pod':False,'files':{'items.json':sha(out/'items.json')},
         'public_archive_sha256':sha(out/'PUBLIC_INPUTS.tar.gz'),'public_schema':'id,prompt only; exact raw prefix',
         'adapter_note':'Exact E133 minimal public packet schema; C wraps literal pinned raw prompts. Same private pair/role/tokenization schema plus subdesign D1/D2/one_hop; CPU selection partitions by subdesign in original generation order, no regeneration or labels on pod.'})
    dump(HERE/'BANK_SEAL.json',{'experiment':'E137','status':'FROZEN_BEFORE_SCREEN_OR_READERS','files':{
         'BANK_MANIFEST.json':sha(HERE/'BANK_MANIFEST.json'),'INPUT_SEAL.json':sha(HERE/'INPUT_SEAL.json'),
         'bank137.py':sha(HERE/'bank137.py'),'build137.py':sha(HERE/'build137.py'),'test_bank137.py':sha(HERE/'test_bank137.py')}})
    print(json.dumps({'status':'FROZEN','prompts':720,'pairs':360,'public_archive_sha256':sha(out/'PUBLIC_INPUTS.tar.gz'),
         'input_seal_sha256':sha(HERE/'INPUT_SEAL.json'),'bank_seal_sha256':sha(HERE/'BANK_SEAL.json'),
         'candidate_boundary_checks':boundaries,'read_token_id':539,'maximum_tokens':manifest['maximum_tokens']}))


if __name__=='__main__':build()
