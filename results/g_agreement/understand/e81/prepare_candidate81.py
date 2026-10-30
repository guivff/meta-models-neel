"""Freeze a CPU-review candidate; never authorizes a GPU retry or production."""
import argparse
from pathlib import Path
from rebind_batch import build
from contract import read,write,sha,seal


def prepare(old_request,destination,proposed_cap=1800):
    request=build(old_request,destination,proposed_cap,True)
    request['argv'][1]='/workspace/results/g_agreement/understand/e81/candidate81.py'
    request.update(status='CPU_REVIEW_ONLY_AWAITING_PARITY_FAILURE_RULING',launch_allowed=False,
        full_launch_allowed=False,profile_only=True,source_candidate='6fa6c2a586fbeeb3c62d144b999d63c8ac30eb52 mixed-length masked left padding',
        real_serial_parity_required=True,hybrid_left_padding_validation='PENDING actual checkpoint; CPU tiny hybrid only',
        proposed_cap_not_admitted=True,all_probe_outputs_scientifically_discarded=True,
        previous_live_parity_failure='a7345fdd source:3/8 real-item mismatches; immutable archive retained')
    write(destination/'REQUEST.json',request,replace=True)
    return request


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--old-request',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--proposed-cap',type=int,default=1800);a=p.parse_args();prepare(a.old_request,a.destination,a.proposed_cap)
