"""CPU-only E76 source selection, blind input export and immutable source map."""
from collections import Counter
from datetime import datetime,timezone
import gzip,io,tarfile
import numpy as np
from common76 import *

INVENTORY=HERE.parent/'e65/SOURCE_INVENTORY_V2_2026-10-27.json'
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def package(path,files):
    with Path(path).open('xb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w') as t:
                for name in sorted(files):
                    data=(ROOT/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
                    t.addfile(info,io.BytesIO(data))


def prepare():
    from tokenizers import Tokenizer
    require(sha(TOKENIZER)==TOKENIZER_SHA,'Pinned tokenizer required');tokenizer=Tokenizer.from_file(str(TOKENIZER))
    require(not CACHE.exists(),'Do not overwrite a sealed E76 build or guard');CACHE.mkdir(parents=True);pod=CACHE/'pod_inputs';pod.mkdir();cpu=CACHE/'cpu_only';cpu.mkdir()
    inv=read(INVENTORY);all_items=[];sources={}
    for bank in BANKS:
        spec=inv['sources'][bank];path=Path(spec['path']);require(sha(path)==spec['sha256'],'Frozen bank hash changed')
        text=path.read_text();xs=[json.loads(x) for x in text.splitlines()] if path.suffix=='.jsonl' else json.loads(text)
        test=[x for x in xs if x['split']=='test'];require(Counter(x['feature'] for x in test)==Counter(spec['rows']),'Bank scope changed')
        sources[bank]={'path':str(path),'sha256':sha(path),'test_items':len(test)}
        for x in test:
            require(tokenizer.encode(x['text'],add_special_tokens=False).ids==x['ids'],'Frozen raw prompt token mismatch')
            all_items.append((bank,x))
    all_items.sort(key=lambda z:(z[0],z[1]['id']));require(len({(b,x['id']) for b,x in all_items})==len(all_items),'Unique source universe required')
    chosen=np.random.default_rng(20261028).choice(len(all_items),N,replace=False).tolist()
    bank={'experiment':'E76','schema':'E76_BLIND_V1','source_bank_count':5,'items':[], 'selected_indices':chosen}
    identities=[]
    for i,(b,x) in enumerate(all_items):
        opaque=hashlib.sha256(f'E76 source item {i}'.encode()).hexdigest()[:32]
        bank['items'].append({'id':opaque,'ids':list(x['ids']),'bank':BANKS.index(b)})
        identities.append({'id':opaque,'bank':b,'row':x['feature'],'original_item_id':x['id'],'source_index':i})
    validate_bank(bank);dump(pod/'BANK.json',bank)
    z=np.random.default_rng(20261027).standard_normal((N,DIM)).astype(np.float32);np.save(pod/'gaussian.npy',z,allow_pickle=False)
    dump(pod/'INPUT_SEAL.json',{'experiment':'E76','schema':'E76_INPUT_V1','files':{n:sha(pod/n) for n in ('BANK.json','gaussian.npy')}})
    dump(cpu/'POOL_MAP.PRIVATE.json',{'experiment':'E76','CPU_only':True,'judge_or_pod_access_forbidden':True,
        'source_bank_codes':list(BANKS),'sources':sources,'full_test_item_map':identities,
        'pool_map':[{'pool_index':i,**identities[j]} for i,j in enumerate(chosen)],'sample_seed':20261028,'gaussian_seed':20261027,
        'pseudo_label_seed':20261029,'input_seal_sha256':sha(pod/'INPUT_SEAL.json')})
    dump(cpu/'CPU_MAP_SEAL.json',{'experiment':'E76','CPU_only':True,'files':{'POOL_MAP.PRIVATE.json':sha(cpu/'POOL_MAP.PRIVATE.json')}})
    dump(HERE/'INPUT_BINDING.json',{'experiment':'E76','authority_commits':['a68a228d','24070152'],'source_inventory_sha256':sha(INVENTORY),
        'sources':sources,'source_banks':list(BANKS),'reference_items':len(all_items),'items_per_bank':dict(Counter(b for b,x in all_items)),
        'shuffled_vectors':N,'gaussian_vectors':N,'readouts_per_vector':1,'readouts_total':2000,'dimension':DIM,
        'median_population':'All frozen test raw read-point vectors in each bank at the native layer, captured before E76 generation',
        'input_seal_sha256':sha(pod/'INPUT_SEAL.json'),'tokenizer_sha256':TOKENIZER_SHA,
        'CPU_map':str((cpu/'POOL_MAP.PRIVATE.json').relative_to(ROOT)),'CPU_map_sha256':sha(cpu/'POOL_MAP.PRIVATE.json'),
        'CPU_map_seal_sha256':sha(cpu/'CPU_MAP_SEAL.json'),'model_calls':0})
    print(json.dumps({'reference_items':len(all_items),'source_counts':dict(Counter(b for b,x in all_items)),
        'shuffled_source_counts':dict(Counter(all_items[i][0] for i in chosen)),'selected_vectors':len(chosen)}))


if __name__=='__main__':prepare()
