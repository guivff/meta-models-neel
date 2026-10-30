"""Separate E62 placebo namespace; unchanged sealed J channel and publisher."""
import argparse
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e57/jlens'))
import cpu_job
import forecast_once

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['channel','forecast'])
    args=parser.parse_args()
    cpu_job.verify(ROOT,cpu_job.read(HERE/'E62_PLACEBO_WRAPPER_SEAL_2026-10-27.json')['files'])
    cpu_job.verify(ROOT,cpu_job.read(HERE/'CODE_SEAL_2026-10-27.json')['files'])
    # Both original functions derive plans, claims and outputs from this distinct name.
    name='E62_PLACEBO'
    return cpu_job.run(name) if args.stage=='channel' else forecast_once.run(name)

if __name__=='__main__':raise SystemExit(main())
