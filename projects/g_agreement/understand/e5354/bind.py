"""Bind an integrator-verified E49 capture, without opening reader scores."""
import argparse,shutil
from .contract import *
def bind(prepared,capture,capture_sha,out):
 sources();s=verify(prepared,'INPUT_SEAL.json');cs=verify(capture,'CAPTURE_SEAL.json',capture_sha)
 require({'CAPTURE_METADATA.json','items.order.json','acts42.npy','acts44.npy'}<=set(cs['files']),'required capture members unsealed')
 require(s.get('stage')=='PREPARED_NEEDS_E49_CAPTURE_BIND','prepared input stage')
 meta=read(capture/'CAPTURE_METADATA.json')
 require(meta['bank_seal_sha256']==E49_SHA and meta['block']==44,'wrong E49 capture')
 order=read(capture/'items.order.json');require(len(order)==len(set(order))==2688,'complete E49 capture order')
 ix={v:i for i,v in enumerate(order)};items=read(prepared/'e49_items.json')
 require(all(x['id'] in ix for x in items),'capture missing planned item')
 shutil.copytree(prepared,out)
 (out/'INPUT_SEAL.json').rename(out/'PREPARED_INPUT_SEAL.json')
 for block in (42,44):
  require('acts'+str(block)+'.npy' in read(capture/'CAPTURE_SEAL.json')['files'],'unsealed capture array')
  h=np.load(capture/f'acts{block}.npy',allow_pickle=False);require(h.shape==(2688,5120) and np.isfinite(h).all(),'capture array')
  np.save(out/f'e49_acts{block}.npy',h[[ix[x['id']] for x in items]],allow_pickle=False)
 dump(out/'CAPTURE_BINDING.json',{'capture_seal_sha256':capture_sha,'e49_bank_sha256':E49_SHA,'capture_metadata':meta,'prepared_input_seal_sha256':sha(prepared/'INPUT_SEAL.json')})
 seal(out,'INPUT_SEAL.json',{'experiment':'E53+E54','stage':'BOUND','e49_capture_seal_sha256':capture_sha,'e54_bank_sha256':E54_SHA})
 print(sha(out/'INPUT_SEAL.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prepared','capture','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--capture-seal',required=True);a=p.parse_args();bind(a.prepared,a.capture,a.capture_seal,a.out)
