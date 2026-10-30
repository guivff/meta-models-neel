"""Read-only live-route probe through fresh spawned E95 worker initialization."""
import argparse
import multiprocessing

from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require
from .judging_workers import _initialize_paid,probe_worker


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    context=multiprocessing.get_context('spawn');spec=read(a.spec)
    with context.Pool(2,initializer=_initialize_paid,initargs=(spec,False,context.Event()))as pool:
        result=pool.map(probe_worker,range(4),chunksize=1)
    require(all(x['route_verified']and x['paid_calls']==0 for x in result),'fresh worker route probes')
    print(dict(fresh_worker_pids=sorted({x['pid']for x in result}),route_verified=True,paid_calls=0))


if __name__=='__main__':main()
