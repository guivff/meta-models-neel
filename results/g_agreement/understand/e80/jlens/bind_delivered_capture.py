"""E80 operational metadata adapter for actual integrator capture; no scoring."""
import json,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from forecast import ROOT,HERE,read,sha,dump,validate_export

def main():
 delivery_dir=ROOT/'cache/g_agreement/understand/e80/capture_delivery'
 dp=delivery_dir/'DELIVERY.json';assert sha(dp)=='b03c9220cb1796cfad92d4de3d30987cc77885f84c4594032a139f89d012df56'
 d=read(dp);assert d['experiment']=='E80'and d['issuer']=='integrator'and d['reader_outputs']==0
 assert d['capture_seal_sha256']=='25d02e881f2c5ceb99959a6d6c8a0a640bf1daed4e1ba71491dd0f4b34e09a32'
 for n,h in d['files'].items():assert sha(delivery_dir/n)==h
 cs=read(delivery_dir/'CAPTURE_SEAL.json');ready=read(delivery_dir/'CAPTURE_READY.json')
 assert sha(delivery_dir/'CAPTURE_SEAL.json')==d['capture_seal_sha256']==ready['capture_seal_sha256']
 assert cs['synthetic']is False and ready['synthetic']is False and cs['reader_outputs']==ready['reader_outputs']==0 and cs['layers']==[42,44]
 assert cs['pod_id']==ready['pod_id']==d['pod_id']
 for n,h in cs['files'].items():assert sha(delivery_dir/n)==h
 for k in ['input_seal_sha256','source_seal_sha256']:assert cs[k]==ready[k]
 producer=ROOT.parent/'wt-wmech';h=producer/'results/g_agreement/understand/e80';binding=read(h/'INPUT_BINDING.json');inp=Path(binding['inputs'])
 assert sha(inp/'INPUT_SEAL.json')==binding['input_seal_sha256']==cs['input_seal_sha256']
 for n,v in read(inp/'INPUT_SEAL.json')['files'].items():assert sha(inp/n)==v
 assert sha(h/'SOURCE_SEAL.json')==cs['source_seal_sha256']
 for n,v in read(h/'SOURCE_SEAL.json')['files'].items():assert sha(h/n)==v
 # Read pinned worker as data to verify this capture occurs before the mandatory forecast-bound GO.
 source=(h/'worker.py').read_text();assert 'else:wait_go(a.go,ready,c)'in source and source.index('else:wait_go(a.go,ready,c)')<source.index('complete=read_stages(items,acts,b,c,a.out)')
 public,targets=validate_export(read(HERE/'PRECAPTURE_PLAN.json'));pd={r['id']:r for r in public};items=read(inp/'items.json');actual={r['id']:r for r in items}
 assert set(actual)==set(pd)and len(items)==518
 for ident,p in pd.items():
  a=actual[ident];assert a['ids']==p['ids']and a['read_index']==p['read_position']and a['feature']==p['family']and a['text']==p['rendered_prompt']
 order=read(delivery_dir/'items.order.json');positions=read(delivery_dir/'POSITIONS.json');pos={r['id']:r['read_index']for r in positions}
 assert len(order)==len(set(order))==len(pos)==len(positions)==518 and set(order)==set(pd)==set(pos)
 for ident in order:assert pos[ident]==pd[ident]['read_position']
 for layer in [42,44]:
  x=np.load(delivery_dir/f'acts{layer}.npy',allow_pickle=False,mmap_mode='r');assert x.shape==(518,5120)and np.isfinite(x).all()
 out=ROOT/'cache/g_agreement/understand/e80/jlens/bound_capture';out.mkdir(parents=True,exist_ok=False)
 boundorder=[dict(id=i,read_position=pos[i],token_ids_sha256=hashlib.sha256(json.dumps(actual[i]['ids'],separators=(',',':')).encode()).hexdigest())for i in order]
 dump(out/'order.json',boundorder)
 ref=lambda p:{'path':str(p.resolve()),'sha256':sha(p)}
 manifest={'experiment':'E80','issuer':'integrator','normalised_by':'W-lens from exact capture-only delivery and actual sealed worker mandatory GO gate','layer':44,'site':'decoder_block_output','reader_outputs_opened':False,'readers_held_until_forecast_commit':True,'custody_authority':'Direct user order: capture ready, commit forecast before GO; delivery/ready reader_outputs=0; pinned worker blocks on forecast-bound GO before native generation','capture_inputs_sha256':read(HERE/'PRECAPTURE_PLAN.json')['capture_inputs']['sha256'],'order':ref(out/'order.json'),'activations':ref(delivery_dir/'acts44.npy'),'source_delivery':ref(dp),'source_capture_seal':ref(delivery_dir/'CAPTURE_SEAL.json'),'source_capture_ready':ref(delivery_dir/'CAPTURE_READY.json'),'input_seal':ref(inp/'INPUT_SEAL.json'),'source_seal':ref(h/'SOURCE_SEAL.json'),'capture_ready_epoch':ready['ready_epoch'],'actual_delivered_utc':d['delivered_utc'],'binding_created_utc':datetime.now(timezone.utc).isoformat(),'items':518,'all_real_sources_verified':True,'no_native_outputs_accessed':True}
 dump(out/'MANIFEST.json',manifest)
 dump(HERE/'CAPTURE_BINDING.json',{'experiment':'E80','status':'REAL_CAPTURE_VERIFIED_NO_SCORING','manifest':ref(out/'MANIFEST.json'),'files':{str(p.resolve()):sha(p)for p in [dp,delivery_dir/'CAPTURE_SEAL.json',delivery_dir/'CAPTURE_READY.json',delivery_dir/'POSITIONS.json',delivery_dir/'items.order.json',delivery_dir/'acts44.npy',delivery_dir/'acts42.npy',inp/'INPUT_SEAL.json',inp/'items.json',h/'SOURCE_SEAL.json',h/'worker.py',Path(__file__).resolve()]},'capture_ready_epoch':ready['ready_epoch'],'actual_delivered_utc':d['delivered_utc'],'no_real_claim_consumed':True})
 print('Verified518 primary read positions, exact original token IDs, source/input/capture seals; no scoring')
if __name__=='__main__':main()
