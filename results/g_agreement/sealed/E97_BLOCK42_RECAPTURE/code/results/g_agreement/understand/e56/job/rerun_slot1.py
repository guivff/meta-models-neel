"""Integrator dispatcher for sealed slot1 native-only reruns; separate output trees."""
import argparse,subprocess,sys
from pathlib import Path
from contract56 import read,require,HERE

def main():
 raise RuntimeError('SUPERSEDED by 8c66b004; no slot1 Oracle output exists')
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec)
 require(set(s['stages'])=={'E56','E57'},'both original slot1 stages, no Oracle command')
 for experiment in ('E56','E57'):
  stage=s['stages'][experiment];ass=read(stage['assignment']);require(ass['experiment']==experiment and ass['slot']==1,'stage identity')
  argv=[sys.executable,str(HERE/'rerun_nla_only.py')]
  for key in ('inputs','original','receipt','assets','assignment','out'):argv+=['--'+key,stage[key]]
  subprocess.run(argv,check=True)
if __name__=='__main__':main()
