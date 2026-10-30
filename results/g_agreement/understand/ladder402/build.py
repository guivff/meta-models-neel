"""Oracle-only measured replan from unopened second-wave timing journals and sealed captures."""
import json,tarfile,shutil,math
from collections import Counter,defaultdict
from worker import *
from second_worker import jobs_for

def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def build():
 outbase=ROOT/'cache/g_agreement/understand/ladder402_v1';outbase.mkdir(exist_ok=False,parents=True);pull=ROOT/'cache/g_agreement/understand/second_wave_verified_v1/pods/vclnlr8h9ggu5c/out';ready=read(pull/'CAPTURE_READY.json');require(ready['cohort_id']==COHORT,'standing cohort');journal=read(pull/'PHASE_TIMINGS.json');measured=defaultdict(list)
 for x in journal:
  if x['status']=='COMPLETE':measured[x['phase']].append(x['seconds'])
 states={}
 for e,name in [('E62','INPUT_BINDING.json'),('E62P','E62P_INPUT_BINDING.json')]:
  b=read(HERE.parent/'e62/job'/name);inp=Path(b['inputs']);verify(inp,'INPUT_SEAL.json',ready['input_seals'][e]);cap=pull/e.lower()/'capture';verify(cap,'CAPTURE_SEAL.json',ready['capture_seals'][e]);items=read(inp/'items.json');require(read(cap/'items.order.json')==[x['id'] for x in items],'all-position capture order')
  offsets=np.load(cap/'offsets.npy');full=np.load(cap/'all_positions44.npy',mmap_mode='r');require(full.dtype==np.float16 and full.shape==(int(offsets[-1]),5120) and offsets.tolist()==[0]+np.cumsum([x['read_index']-x['first_content_index']+1 for x in items]).tolist(),'standing all-position fp16/offsets')
  states[e]={'items':items,'inputs':inp,'capture':cap,'acts':{l:np.load(cap/f'acts{l}.npy',mmap_mode='r') for l in (42,44)}}
 alljobs=jobs_for(states);seen=Counter();jobs=[];pilots=[]
 for j in alljobs:
  phase=j['phase'];seen[phase]+=1
  require(len(measured[phase])==2,'two original measured pilot jobs per phase')
  if j['reader']!='oracle':continue
  j=dict(j);j['key']='second:'+str(j['number']);j['original_key']=j['key'];j['stage']=j['exp'];j['measured_seconds']=max(measured[phase]);j['retained_pilot']=seen[phase]<=2
  (pilots if j['retained_pilot'] else jobs).append(j)
 forecast={'authority':'402be5f0','timing_path':str(pull/'PHASE_TIMINGS.json'),'timing_sha256':sha(pull/'PHASE_TIMINGS.json'),'cohort_id':COHORT,'derivation':'2 * sum(max(two measured Oracle pilot batch durations in phase) * remaining original jobs), then total cap ceil(forecast *1.25); original two pilots retained, never repeated; 900s staging per pod separate','original_margin':2,'cap_multiplier':1.25,'NLA':'NOT RUN','experiments':{}}
 for e,n in [('E62',3),('E62P',2)]:
  own=[j for j in jobs if j['exp']==e];loads=[0.]*n
  for j in sorted(own,key=lambda x:(-x['measured_seconds'],x['number'])):
   sh=min(range(n),key=lambda i:(loads[i],i));j['shard']=sh;loads[sh]+=2*j['measured_seconds']
  total=math.ceil(sum(loads)*1.25);caps=[math.floor(x*1.25) for x in loads]
  for i in range(total-sum(caps)):caps[i%n]+=1
  forecast['experiments'][e]={'shards':n,'phase_samples':{phase:values for phase,values in measured.items() if phase.startswith(e+'_oracle')},'remaining_jobs':len(own),'retained_pilots':len([j for j in pilots if j['exp']==e]),'measured_forecast_seconds':sum(loads),'compute_cap_seconds':total,'shard_caps':caps}
  for sh in range(n):
   out=outbase/(e+'_'+str(sh));out.mkdir();(out/'packets').mkdir();selected=[]
   for j in own:
    if j['shard']!=sh:continue
    item={k:v for k,v in j.items() if k!='h'};item['h_file']=None
    if j['h'] is not None:item['h_file']='packets/'+str(j['number'])+'.npy';np.save(out/item['h_file'],j['h'])
    selected.append(item)
   retained=[{k:v for k,v in j.items() if k not in ('h','units')} for j in pilots if j['exp']==e] if sh==0 else []
   plan={'authority':'402be5f0','cohort_id':COHORT,'experiment':e,'shard':sh,'compute_cap_seconds':caps[sh],'jobs':selected,'retained_pilots':retained,'capture_seals':{e:ready['capture_seals'][e]},'standing_all_position_capture':{'path':str(states[e]['capture']),'sha256':ready['capture_seals'][e],'dtype':'fp16','interval':'first_content..read inclusive','order_and_offsets_verified':True},'NLA':'NOT RUN'}
   write(out/'PLAN.json',plan);shutil.copytree(states['E62']['inputs']/'parity',out/'parity');seal(out,'INPUT_SEAL.json',{'experiment':e,'shard':sh,'label_free':True});arc=out.with_suffix('.tar.gz')
   with tarfile.open(arc,'w:gz',compresslevel=1) as t:t.add(out,arcname='inputs')
   write(HERE/f'{e}_{sh}_BINDING.json',{'inputs':str(out),'archive':str(arc),'archive_sha256':sha(arc),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'plan_sha256':sha(out/'PLAN.json'),'compute_cap_seconds':caps[sh],'MB':arc.stat().st_size/1e6});print(e,sh,caps[sh],arc.stat().st_size,flush=True)
 write(HERE/'MEASURED_FORECAST.json',forecast)
if __name__=='__main__':build()
