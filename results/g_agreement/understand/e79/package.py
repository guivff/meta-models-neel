"""Bind supplied opaque vectors; join prompts on CPU, exclude all truth/target data."""
from worker import *
import hashlib,tarfile,shutil

def build(dest):
 wi=ROOT.parent/'wt-blindspot-internals';original=wi/'results/g_agreement/understand/e79';base=original/'clarification2';s=verify(base,'RESULT_SEAL.json');sup=wi/'cache/g_agreement/understand/e79/inputs_v2_low_doses';pod=sup/'pod_inputs';verify(pod,'RESULT_SEAL.json',s['pod_seal_sha256']);receipt=read(base/'BUILD_RECEIPT.json');require(sha(sup/'KEY.DO_NOT_SHARE.json')==receipt['private_map_sha256'],'owner private join pin');key={x['id']:x for x in read(sup/'KEY.DO_NOT_SHARE.json')};source=read(original/'INPUTS.json');meta=Path(source['sources']['E59']['metadata']);require(sha(meta)==source['files'][str(meta)],'E59 frozen prompt pin');prompts={x['id']:x for x in read(meta)};items=[]
 for x in read(pod/'ITEMS.json'):
  k=key[x['id']];condition={'nonJ':'perp','baseline':'none'}.get(x['condition'],x['condition']);cell=condition if x['alpha'] in (0,None) else condition+':'+str(x['alpha'])
  v=dict(id=x['id'],base_item_id=hashlib.sha256(('E79opaque:'+k['source_item_id']).encode()).hexdigest()[:32],feature=x['row'],arm=x['arm'],cell=cell,vector_index=x['index'])
  if x['arm']=='B':
   z=prompts[k['source_item_id']];require(z['split']=='test' and z['feature']==x['row'],'ArmB original test prompt');v.update(ids=z['ids'],read_index=len(z['ids'])-1)
  items.append(v)
 vectors=np.load(pod/'INPUT_VECTORS.npy',allow_pickle=False);validate(items,vectors);dest.mkdir(parents=True,exist_ok=False);inp=dest/'inputs';inp.mkdir();dump(inp/'items.json',items);shutil.copyfile(pod/'INPUT_VECTORS.npy',inp/'vectors.npy');require(sha(inp/'vectors.npy')==sha(pod/'INPUT_VECTORS.npy'),'vectors byte identical');seal(inp,'INPUT_SEAL.json',dict(experiment='E79',supplier_seal_sha256=sha(base/'RESULT_SEAL.json'),supplier_pod_seal_sha256=s['pod_seal_sha256'],labels_on_pod=False))
 archive=dest/'inputs.tar.gz'
 with tarfile.open(archive,'w:gz',compresslevel=1) as t:t.add(inp,arcname='inputs')
 atomic(HERE/'INPUT_BINDING.json',dict(inputs=str(inp),input_seal_sha256=sha(inp/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),supplier_result_seal_sha256=sha(base/'RESULT_SEAL.json'),supplier_pod_seal_sha256=s['pod_seal_sha256'],vectors_sha256=sha(inp/'vectors.npy'),private_join_sha256=receipt['private_map_sha256']))
 if __name__=='__main__':print('BOUND_LABEL_FREE4704')
if __name__=='__main__':build(Path(sys.argv[1]))
