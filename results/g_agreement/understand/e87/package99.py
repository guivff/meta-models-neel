"""CPU E99 public package, paired-cell norm binding and measured admission."""
import argparse
import math
from pathlib import Path
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'late198'))
from contract import read,write,sha,seal,verify,require,digest
import scope99 as S


def prepare(items_path,owner_seal,destination,shards=4,reduction=0,probe_cap=1800):
    from worker87 import HERE,ROOT
    require(digest(owner_seal),'owner-frozen export seal')
    items=read(items_path);destination.mkdir(parents=True,exist_ok=False)
    source_sha=sha(HERE/'SOURCE_SEAL.json');source=verify(HERE,'SOURCE_SEAL.json',source_sha)
    deps=read(HERE/'DEPENDENCIES.json')
    for name,h in deps.items():require(sha(ROOT/name)==h,'dependency '+name)
    names=set(deps)|{str((HERE/n).relative_to(ROOT)) for n in source['files']}|{str((HERE/'SOURCE_SEAL.json').relative_to(ROOT))}
    with tarfile.open(destination/'source.tar.gz','w:gz') as archive:
        for name in sorted(names):archive.add(ROOT/name,arcname=name,recursive=False)
    requests=[]
    for i in range(shards):
        plan=dict(experiment='E99',seed=S.SEED,reduction_step=reduction,owner_seal_sha256=owner_seal,
            items_sha256=sha(items_path),shards=shards,shard=i,item_ids=[])
        plan['item_ids']=[x['id'] for x in S.shard_items(items,plan)];S.validate(items,plan)
        require(plan['item_ids'],'nonempty shard')
        inp=destination/f'shard{i}'/'inputs';inp.mkdir(parents=True)
        (inp/'items.json').write_bytes(items_path.read_bytes());write(inp/'PLAN.json',plan)
        write(inp/'STAGE_REQUEST.json',dict(experiment='E99',status='READY',cap_seconds=probe_cap,
            cumulative_cap_seconds=probe_cap,account_gate_USD=1500,seed_seconds_per_batch={}))
        input_sha=seal(inp,'INPUT_SEAL.json',experiment='E99',owner_seal_sha256=owner_seal)
        archive_path=inp.parent/'inputs.tar.gz'
        with tarfile.open(archive_path,'w:gz') as archive:archive.add(inp,arcname='inputs')
        requests.append(dict(shard=i,item_ids=plan['item_ids'],source_seal_sha256=source_sha,input_seal_sha256=input_sha,
            input_archive=str(archive_path.resolve()),input_archive_sha256=sha(archive_path),profile_cap_seconds=probe_cap))
    request=dict(status='TIMING_PROBE_ONLY',experiment='E99',shards=requests,source_archive=str((destination/'source.tar.gz').resolve()),
        source_archive_sha256=sha(destination/'source.tar.gz'),owner_seal_sha256=owner_seal,items_sha256=sha(items_path),
        reduction_step=reduction,reader_batch_size=32,live_parity_required=True,parity_mismatch_is_gate=False,parity_authority=S.PARITY_AUTHORITY,full_launch_allowed=False,
        integrator='I-2',labels_on_pod=False,first_probe_one_pod=True)
    write(destination/'REQUEST.json',request)
    return request


def admit(profile_paths,out,prior_seconds=0):
    profiles=[read(p) for p in profile_paths]
    for path,profile in zip(profile_paths,profiles):
        receipt=read(path.parent/'OUTPUT_SEAL.json')
        require(receipt['status']=='PROFILE_ONLY' and not receipt.get('synthetic',False) and
                receipt['files'].get(path.name)==sha(path) and receipt['source_seal_sha256']==profile['source_seal_sha256'],
                'verified terminal timing profile seal required')
    require(4<=len(profiles)<=8 and sorted(x['shard'] for x in profiles)==list(range(len(profiles))),'all shard profiles')
    for field in ('items_sha256','source_seal_sha256','reduction_step'):
        require(len({x[field] for x in profiles})==1,'same bank/source/reduction')
    require(all(x['status']=='TIMING_ONLY_NOT_SCIENCE' and x['margin']==1.25 and x['batch_size']==32 and
                x['parity_items']==8 and all(x['parity_counts'][r]>=8 for r in ('oracle','nla')) for x in profiles),'complete timing and parity')
    require(type(prior_seconds) in (int,float) and math.isfinite(prior_seconds) and prior_seconds>=0,'prior measured custody')
    caps=[math.ceil(x['forecast_seconds']) for x in profiles]
    write(out,dict(status='WITHIN_E99_CEILING' if sum(caps)+prior_seconds<=86400 else 'REDUCTION_REQUIRED',
        total_cap_seconds=sum(caps),prior_seconds=prior_seconds,cumulative_seconds=sum(caps)+prior_seconds,ceiling_seconds=86400,margin=1.25,
        next_reduction_step=profiles[0]['reduction_step']+1 if sum(caps)+prior_seconds>86400 and profiles[0]['reduction_step']<3 else None,
        shards=[dict(shard=x['shard'],cap_seconds=n,measured_profile_sha256=sha(p)) for x,n,p in zip(profiles,caps,profile_paths)],
        integrator_daily_budget_admission_still_required=True))



def rebind(probe_request,profile_paths,destination,prior_seconds):
    import shutil
    request=read(probe_request);destination.mkdir(parents=True,exist_ok=False)
    admit(profile_paths,destination/'ADMISSION.json',prior_seconds)
    admission=read(destination/'ADMISSION.json');require(admission['status']=='WITHIN_E99_CEILING','reduce in registered order before full launch')
    byshard={read(p)['shard']:p for p in profile_paths};new=[]
    for old in request['shards']:
        i=old['shard'];profile=read(byshard[i]);bound=next(x for x in admission['shards'] if x['shard']==i)
        require(profile['source_seal_sha256']==old['source_seal_sha256'] and profile['input_seal_sha256']==old['input_seal_sha256'],'profile matches exact probe source/input')
        require(sha(old['input_archive'])==old['input_archive_sha256'],'probe input archive')
        folder=destination/f'shard{i}';folder.mkdir()
        with tarfile.open(old['input_archive']) as archive:archive.extractall(folder,filter='data')
        inp=folder/'inputs';verify(inp,'INPUT_SEAL.json',old['input_seal_sha256'])
        limits=read(inp/'STAGE_REQUEST.json');limits.update(cap_seconds=bound['cap_seconds'],cumulative_cap_seconds=bound['cap_seconds']+prior_seconds,
            measured_profile_sha256=sha(byshard[i]),admission_sha256=sha(destination/'ADMISSION.json'))
        write(inp/'STAGE_REQUEST.json',limits,replace=True);(inp/'INPUT_SEAL.json').unlink()
        ih=seal(inp,'INPUT_SEAL.json',experiment='E99',owner_seal_sha256=request['owner_seal_sha256'])
        with tarfile.open(folder/'inputs.tar.gz','w:gz') as archive:archive.add(inp,arcname='inputs')
        new.append(dict(old,input_archive=str((folder/'inputs.tar.gz').resolve()),input_archive_sha256=sha(folder/'inputs.tar.gz'),
            input_seal_sha256=ih,cap_seconds=bound['cap_seconds'],measured_profile_sha256=sha(byshard[i])))
    write(destination/'REQUEST.json',dict(request,status='MEASURED_WITHIN_CEILING_REQUIRES_I2_DAILY_ADMISSION',shards=new,
        full_launch_allowed=False,admission_sha256=sha(destination/'ADMISSION.json')))


def prepare_owner(contract_path,owner_seal_path,destination,shards=4,reduction=0,probe_cap=1800):
    import json
    contract=read(contract_path);owner=read(owner_seal_path)
    require(owner['files'].get('CAPTURE_CONTRACT.json')==sha(contract_path),'sealed owner capture contract')
    require(sha(contract['public_archive'])==contract['public_archive_sha256'],'exact owner public archive')
    with tarfile.open(contract['public_archive']) as archive:
        require(sorted(archive.getnames())==['CAPTURE_INPUTS.json','PLACEBO_SPECS.json'] and all(x.isfile() for x in archive.getmembers()),'public-only owner members')
        public=json.load(archive.extractfile('CAPTURE_INPUTS.json'));pseudos=json.load(archive.extractfile('PLACEBO_SPECS.json'))
    require(len(public)==516 and len(pseudos)==90,'full owner inventory')
    byid={x['id']:x for x in public};paired={x['id']:[] for x in public}
    shared={'family','grid_positions','grid_oracle_layers','nla_layer','single_site_position','single_site_oracle_layer','single_site_nla_layer','extra_single_site_positions'}
    for x in public:
        require(set(x)==shared|{'id','input_ids','render','rendered_prompt'},'owner real allowlist')
        require(x['nla_layer']==x['single_site_nla_layer']==42 and x['single_site_oracle_layer']==44,'native and single layers')
        extra=[] if x['single_site_position'] in x['grid_positions'] else [x['single_site_position']]
        require(x['extra_single_site_positions']==extra and (not extra or x['family'] in ('directed_modulation','jailbreak_recognition')),'extra arm binding')
    for x in pseudos:
        require(set(x)==shared|{'id','paired_capture_id','vector_kind','seed','seed_key','norm_rule'},'owner placebo allowlist')
        require(x['paired_capture_id'] in byid and x['vector_kind']=='random' and x['seed']==S.SEED and x['seed_key']==x['id'] and
                x['norm_rule']=='Match paired real vector norm separately at every reader/layer/position, E76 method.','placebo identity/recipe')
        real=byid[x['paired_capture_id']]
        require(all(x[k]==real[k] for k in shared),'placebo paired cell structure')
        paired[real['id']].append(x['id'])
    items=[]
    for x in public:
        family_layer=next((l for l in x['grid_oracle_layers'] if l!=44),None) if x['family']=='buggy_code' else None
        item=dict(id=x['id'],family=x['family'],ids=x['input_ids'],positions=x['grid_positions'],single_position=x['single_site_position'],family_layer=family_layer,placebo_ids=paired[x['id']])
        require(sorted(x['grid_oracle_layers'])==sorted(S.layers(item,0)),'registered Oracle layers')
        items.append(item)
    # No decoded-prompt retokenization: captured hallucination token IDs are authoritative.
    normalized=destination.parent/(destination.name+'.normalized.json');normalized.parent.mkdir(parents=True,exist_ok=True);write(normalized,items)
    result=prepare(normalized,sha(owner_seal_path),destination,shards,reduction,probe_cap)
    counts={'real':0,'placebo':0}
    for i in range(shards):
        p=read(destination/f'shard{i}/inputs/PLAN.json')
        for group in S.cells(items,p).values():
            for cell in group:counts[cell['arm']]+=1
    if reduction==0:require(counts=={'real':40738,'placebo':5645},'exact owner full-grid counts')
    result.update(owner_public_archive_sha256=contract['public_archive_sha256'],cells=counts,
        norm_rule='paired real vector norm per reader/layer/position',seed=S.SEED)
    write(destination/'REQUEST.json',result,replace=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--items',type=Path,required=True);a.add_argument('--owner-seal',required=True)
    a.add_argument('--destination',type=Path,required=True);a.add_argument('--shards',type=int,default=4)
    a.add_argument('--reduction',type=int,default=0);a.add_argument('--probe-cap',type=int,default=1800)
    a=sub.add_parser('admit');a.add_argument('--profiles',type=Path,nargs='+',required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--prior-seconds',type=float,required=True)
    a=sub.add_parser('prepare-owner');a.add_argument('--contract',type=Path,required=True);a.add_argument('--owner-seal',type=Path,required=True)
    a.add_argument('--destination',type=Path,required=True);a.add_argument('--shards',type=int,default=4);a.add_argument('--reduction',type=int,default=0);a.add_argument('--probe-cap',type=int,default=1800)
    a=sub.add_parser('rebind');a.add_argument('--probe-request',type=Path,required=True);a.add_argument('--profiles',type=Path,nargs='+',required=True)
    a.add_argument('--destination',type=Path,required=True);a.add_argument('--prior-seconds',type=float,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.items,a.owner_seal,a.destination,a.shards,a.reduction,a.probe_cap)
    elif a.command=='prepare-owner':prepare_owner(a.contract,a.owner_seal,a.destination,a.shards,a.reduction,a.probe_cap)
    elif a.command=='rebind':rebind(a.probe_request,a.profiles,a.destination,a.prior_seconds)
    else:admit(a.profiles,a.out,a.prior_seconds)
