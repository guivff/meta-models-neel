"""Select sealed E49 gates/captures only; never recompute gates or original analysis."""
import sys,tarfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];E56=HERE.parents[1]/'e56/job';sys.path.insert(0,str(E56))
from contract56 import read,dump,verify,sha,seal,require

def prepare():
 original=HERE.parent/'job';binding=read(original/'INPUT_BINDING.json');source=ROOT/'cache/g_agreement/understand/e49/verified_section149/out';outer=verify(source,'OUTPUT_SEAL.json');capture=source/'capture';verify(capture,'CAPTURE_SEAL.json',outer['capture_seal_sha256'])
 analysis=original/'analysis';verify(analysis,'ANALYSIS_SEAL.json');gates=read(analysis/'GATES.json')['qualified_rows'];require(len(gates)==8,'sealed eight-row gate')
 bank=Path(binding['private_items_path']);require(sha(bank)==binding['private_items_sha256'],'same original items');private=read(bank);order=read(capture/'items.order.json');ix={k:i for i,k in enumerate(order)};byid={x['id']:x for x in private};import json
 items=[byid[json.loads(line)['id']] for row in gates for line in (source/'readers'/row/'nla_native.jsonl').read_text().splitlines()];require(len(items)==672 and all(sum(x['feature']==r for x in items)==84 for r in gates),'eight by84same items')
 out=ROOT/'cache/g_agreement/understand/e49/nla_supplement/inputs_v2';out.mkdir(parents=True,exist_ok=False)
 h=np.load(capture/'acts42.npy',mmap_mode='r');np.save(out/'acts42.npy',np.array(h[[ix[x['id']] for x in items]],dtype=np.float32));dump(out/'items.json',[{'id':x['id'],'feature':x['feature']} for x in items])
 dump(out/'ORIGINAL_BINDING.json',{'output_seal_sha256':sha(source/'OUTPUT_SEAL.json'),'capture_seal_sha256':sha(capture/'CAPTURE_SEAL.json'),'analysis_seal_sha256':sha(analysis/'ANALYSIS_SEAL.json'),'gates_sha256':sha(analysis/'GATES.json'),'qualified_rows':gates,'original_native_primary_sha256':sha(analysis/'NATIVE_PRIMARY.json'),'private_items_sha256':sha(bank)})
 seal(out,'INPUT_SEAL.json',{'experiment':'E49_NLA_SUPPLEMENT','authority':'259db20a','descriptive_only':True,'k':1,'native_layer':42,'items':672})
 archive=out.parent/'inputs_v2.tar.gz'
 with tarfile.open(archive,'w:gz') as t:t.add(out,arcname='inputs')
 target=HERE/'INPUT_BINDING.json'
 if target.exists():target.rename(HERE/'INPUT_BINDING_v1_superseded.json')
 dump(target,{'inputs':str(out),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'archive':str(archive),'archive_sha256':sha(archive),'private_items':str(bank),'private_items_sha256':sha(bank),'qualified_rows':gates,'original_analysis':str(analysis),'original_native_primary_sha256':sha(analysis/'NATIVE_PRIMARY.json')})
if __name__=='__main__':prepare()
