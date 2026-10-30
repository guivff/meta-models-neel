"""Measured-source CPU forecast; no GPU-speed claims inferred for B200."""
from pathlib import Path
from collections import Counter
import numpy as np
from .contract import ROOT,read,write,sha,require,ROWS,jobs
OUT=ROOT/'results/g_agreement/understand/e100/runner'

def timing(exp):
 config=read(ROOT/f'projects/g_agreement/understand/wmech2/{exp}.json');p=Path(config['output']);s=read(p/'OUTPUT_SEAL.json');require(sha(p/'OUTPUT_SEAL.json')==config['output_sha256'],'pinned historical output seal')
 require(sha(p/'PHASE_TIMINGS.json')==s['files']['PHASE_TIMINGS.json'],'sealed historical timing bytes')
 rows=read(p/'PHASE_TIMINGS.json');return rows,dict(experiment=exp,path=str(p/'PHASE_TIMINGS.json'),sha256=sha(p/'PHASE_TIMINGS.json'),output_seal_sha256=config['output_sha256'])
def main():
 a,ap=timing('E79');b,bp=timing('E70')
 def mean(rows,phase):return float(np.mean([x['seconds'] for x in rows if x['phase']==phase and x.get('status')=='COMPLETE']))
 native={'oracle':mean(a,'native'),'nla':mean(b,'nla_native')};setup={'oracle':mean(a,'oracle_setup'),'nla':mean(b,'nla_setup')};warm=mean(a,'native_warmup_discarded')
 result={}
 for shard in ROWS:
  items=[]
  for row,n in ROWS[shard].items():
   for _ in range(n):items.append(dict(row=row,slot=len(items)))
  jj=jobs(items,shard);counts=Counter(j['reader'] for j in jj)
  science=sum(n*native[r] for r,n in counts.items());load=2*sum(setup.values());warmups=2*warm+240 # NLA warmup unmeasured: explicit120s/load allowance
  predicted=1.25*(science+load+warmups)+180+600 #180seal reserve +600s staging allowance
  result[shard]=dict(items=len(items),readouts=sum(len(j['indices']) for j in jj),batches=dict(counts),seconds_before_margin=science+load+warmups,forecast_seconds=predicted,forecast_GPU_hours=predicted/3600,load_count_per_reader=2,staging_allowance_seconds=600,seal_reserve_seconds=180)
 write(OUT/'FORECAST.json',dict(experiment='E100',scope='a/b only, all84,69f8c08e4',status='HISTORICAL_PROXY_REQUIRES_RETAINED_REAL_PILOTS',sources=[ap,bp],batch8_seconds=native,setup_seconds=setup,measured_oracle_warmup_seconds=warm,unmeasured_nla_warmup_allowance_per_load_seconds=120,batch4_policy='Conservatively charged full batch8 proxy; separate actual batch4 pilot before admission',margin=1.25,shards=result,total_GPU_hours=sum(x['forecast_GPU_hours'] for x in result.values()),hardware_caveat='Historical proxy only; no claimed B200 speedup. Actual GPU name/type is recorded per shard. Same-image smoke required for B200. Live retained pilots replace each reader/batch-size mean.',allocation='Integrator must provide verified per-shard cumulative cap and daily budget; this forecast does not authorize an increase or launch.'))
 print({k:round(v['forecast_GPU_hours'],3) for k,v in result.items()})
if __name__=='__main__':main()
