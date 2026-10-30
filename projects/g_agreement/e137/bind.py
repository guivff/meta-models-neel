"""Source-only field binding through ORIGINAL E133 adapt; no item generation."""
import json,tarfile
from pathlib import Path
from collections import Counter
from transformers import AutoTokenizer
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e133.bind_screen import adapt
from projects.g_agreement.e137.runner import validate_items
PUBLIC=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e137-public-v1')
BANK=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e137-bank-v1')
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
PUBLIC_SHA='dd5f6d41d0d87cb0f018a8001f11bab346a645d436e9aa06f469f5bad0b1df30'
PAIR_SHA='92a5af53112e750be82336f0bdbfb996aa25cbe0d5b5e9102ba860f8b764e9dc'
TOK_SHA='57863bd010d3ee1609f384ecf9c47dbcdd2a2f9a35f40565e6d8d2b5a81bda98'

def build(out):
    verify(PUBLIC,'INPUT_SEAL.json',PUBLIC_SHA)
    if sha(BANK/'PAIRS.PRIVATE.json')!=PAIR_SHA or sha(BANK/'TOKENIZATION_CPU.PRIVATE.json')!=TOK_SHA:
        raise ValueError('original frozen CPU bindings changed; no silent substitute')
    source=read(PUBLIC/'items.json');pairs=read(BANK/'PAIRS.PRIVATE.json')['pairs'];tokens=read(BANK/'TOKENIZATION_CPU.PRIVATE.json')
    if len(source)!=720 or len(pairs)!=360 or Counter(p['subdesign']for p in pairs)!=dict(D1=150,D2=150,one_hop=60):
        raise ValueError('actual frozen source150/150/60 PAIRS')
    if sha(TOKENIZER/'tokenizer.json')!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42':
        raise ValueError('pinned original tokenizer')
    tok=AutoTokenizer.from_pretrained(TOKENIZER,local_files_only=True,trust_remote_code=False)
    items,roles=adapt(source,pairs,tok,'synthetic') # literal original field wrapper
    validate_items(items,'screen');by={x['id']:x for x in tokens}
    if len(by)!=720:raise ValueError('original token record census')
    private=[]
    for order,p in enumerate(pairs):
        for member in sorted(p['members'],key=lambda x:x['member']):
            x=items[len(private)];native=by[member['id']]
            if x['id']!=member['id'] or x['ids']!=native['input_ids']or x['read_index']!=native['read_index']:
                raise ValueError('all original token/position identities preserved')
            expected=sorted(native['ordered_recipient_candidate_ids'])
            if x['candidate_ids']!=[[[expected[0]],[expected[1]]]]:raise ValueError('same original recipient contrast, ascending only')
            if p['subdesign']in ('D1','D2')and member['current_holder']==member['latest_mention']:
                raise ValueError('owner source violates registered nonrecency design')
            private.append(dict(id=x['id'],original_pair_index=order,subdesign=p['subdesign'],generation_order=p['generation_order'],original_token_record_id=native['id']))
    out=Path(out);out.mkdir(exist_ok=False);pub=out/'inputs';cpu=out/'cpu_only';pub.mkdir();cpu.mkdir()
    write(pub/'items.json',items)
    write(pub/'MANIFEST.json',dict(experiment='E137',stage='screen',labels_on_pod=False,one_hop_candidate_pairs=60,source_input_sha256=PUBLIC_SHA,source_items_sha256=sha(PUBLIC/'items.json'),order='exact original frozen pair/member order',candidate_policy='only recipient pair ascending token IDs; no previous/current/sign',tokenizer_revision=TOKENIZER.name))
    write(pub/'INPUT_SEAL.json',dict(experiment='E137',stage='screen',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()}))
    write(cpu/'ROLES.PRIVATE.json',roles);write(cpu/'SOURCE_DESIGNS.PRIVATE.json',private)
    write(cpu/'CPU_SEAL.json',dict(experiment='E137',input_sha256=sha(pub/'INPUT_SEAL.json'),source_cpu_paths={str(BANK/'PAIRS.PRIVATE.json'):PAIR_SHA,str(BANK/'TOKENIZATION_CPU.PRIVATE.json'):TOK_SHA},files={p.name:sha(p)for p in cpu.iterdir()}))
    for p in cpu.iterdir():p.chmod(0o600)
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as t:
        for p in sorted(pub.iterdir()):t.add(p,arcname=p.name)
    result=dict(experiment='E137',public_root=str(pub),input_sha256=sha(pub/'INPUT_SEAL.json'),archive=str(out/'inputs.tar.gz'),archive_sha256=sha(out/'inputs.tar.gz'),CPU_only_root=str(cpu),CPU_only_seal_sha256=sha(cpu/'CPU_SEAL.json'),source_public_root=str(PUBLIC),source_public_sha256=PUBLIC_SHA,original_CPU_pair_path=str(BANK/'PAIRS.PRIVATE.json'),original_CPU_pair_sha256=PAIR_SHA,original_CPU_token_path=str(BANK/'TOKENIZATION_CPU.PRIVATE.json'),original_CPU_token_sha256=TOK_SHA,prompts=720,candidate_pairs=dict(D1=150,D2=150,one_hop=60),actual_token_read_candidate_bindings='PASS720/720',nonrecency_source_fields='PASS600MHmembers current!=latest_mention',original_E133_adapter='unchanged code function adapt',selected_pairs=None,model_calls=0,GPU_calls=0,labels_on_pod=False)
    write(Path(__file__).resolve().parents[3]/'results/g_agreement/understand/e137/RUNNER_INPUT_BINDING.json',result)
    return result
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
