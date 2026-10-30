"""bb9f3931: 1.25 remaining-cost margin; complete future reader stage included."""
import time
from collections import Counter
from admission import Budget as BaseBudget,NoFit,atomic
class Budget(BaseBudget):
 def forecast(self,jobs,results,reload_oracle=False):
  remaining=Counter(j['phase'] for j in jobs if j['number'] not in results)
  seeds={'oracle_native':self.seed.get('oracle_native_8_items',0),'nla_native':self.seed.get('nla_native_8_items',0)}
  unknown=[p for p in remaining if not self.observed.get(p) and not seeds.get(p)]
  raw=sum(n*max(self.observed.get(p,[]) or [seeds.get(p,0)]) for p,n in remaining.items())
  if remaining.get('nla_native') and not self.observed.get('nla_setup'):raw+=self.seed.get('nla_setup',0)
  forecast=1.25*raw+60;fits=not unknown and time.time()+forecast<self.end
  report=dict(status='ADMIT' if fits else 'NO_FIT',margin=1.25,remaining_forecast_seconds=forecast,remaining_phases=dict(remaining),unknown_phases=unknown,deadline_epoch=self.end,recorded_epoch=time.time(),completed_jobs=len(results),pilot_outputs_retained=True,future_nla_setup_included=bool(remaining.get('nla_native') and not self.observed.get('nla_setup')))
  atomic(self.out/'FORECAST.json',report)
  if not fits:raise NoFit('full remaining run does not fit bb9f3931 custody')
  return report
