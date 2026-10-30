"""Verify ratified W-text seal before any input read; emit only public shard inputs."""
from package import *
POSITION_SHA='6b706209fb0f785eedec48d3d70a70f7dc2269fe9261797a6b8293782f9348c2'

def bind(source,dest):
 verify(source,'POSITION_SEAL.json',POSITION_SHA)
 launch=read(source/'LAUNCH_REQUEST.json');require(launch['position_seal_sha256']==POSITION_SHA and launch['gpu_cap_seconds']==2160 and not launch['ratification_required'],'ratified request')
 require(sha(launch['archive_path'])==launch['archive_sha256'],'owner archive hash; never upload private archive')
 original=read(launch['inputs_path']);positions={x['id']:x for x in read(source/'POSITIONS.json')['items'] if not x['dropped']};require(len(original)==252 and {x['id'] for x in original}==set(positions),'exact kept 252')
 items=[];mapping={'registered':'P_far','midpoint':'P_mid','pre_answer':'P_pre'}
 for x in original:
  anchor=positions[x['id']];require(anchor['row']==x['feature'],'row identity')
  require(anchor['gap']==(14 if x['feature']=='container_after_move' else 26 if x['feature']=='holder_after_handovers' else 5),'ratified gaps including control exception')
  for position,p in mapping.items():
   index=x['positions'][p];require(index==anchor['positions'][p]['index'] and x['ids'][index]==anchor['positions'][p]['token_id'],'exact ratified index/token')
   items.append(dict(id=x['id']+'::'+p,base_item_id=x['id'],feature=x['feature'],split='test',position=position,text=x['text'],ids=x['ids'],read_index=index))
 from dev_inputs import extend_dev
 items,private,dev_binding=extend_dev(source,items,launch)
 validate_items('E68',items,full=True);dest.mkdir(parents=True,exist_ok=False);bank=dest/'public_bank';bank.mkdir();dump(dest/'PRIVATE_ITEMS.json',private);atomic(HERE/'DEV_BINDING.json',dict(dev_binding,private_items=str(dest/'PRIVATE_ITEMS.json'),private_items_sha256=sha(dest/'PRIVATE_ITEMS.json')));dump(bank/'items.json',items);seal(bank,'INPUT_SEAL.json',dict(experiment='E68',position_seal_sha256=POSITION_SHA,original_inputs_sha256=sha(launch['inputs_path']),positions_sha256=sha(source/'POSITIONS.json')))
 request=pack('E68',bank,sha(bank/'INPUT_SEAL.json'),dest/'package',1)
 r=read(request);r.update(authority='7e6ea0cc section185 deviation2; bb9f3931 compute deviation',position_seal_sha256=POSITION_SHA,owner_commit='e1cd1a1',items=252,test_capture_positions=756,dev_capture_positions=756,capture_positions=1512,native_readouts=1512,measured_forecast=read(HERE/'MEASURED_FORECAST.json'),probe_status='CPU_DEV_FIT_FROM_THIS_CAPTURE_REQUIRED_BEFORE_OPENING_READOUTS',R_O1='both remaining state rows >=0.30; unchanged topic control <0.15',arithmetic_status='INFEASIBLE, not a failed reader outcome');atomic(request,r)
 atomic(HERE/'REQUEST.json',r);atomic(HERE/'EXACT_PREFLIGHT.json',read(request.with_name('EXACT_PREFLIGHT.json')));atomic(HERE/'BINDING.json',dict(position_seal_sha256=POSITION_SHA,owner_launch_request_sha256=sha(source/'LAUNCH_REQUEST.json'),owner_archive_sha256=launch['archive_sha256'],private_labels_CPU_only=launch['private_labels_CPU_only'],private_labels_sha256=sha(launch['private_labels_CPU_only']),position_name_mapping=mapping,all_indices_unchanged=True,public_bank=str(bank)));return request
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--dest',type=Path,required=True);a=p.parse_args();print(bind(a.source,a.dest))
