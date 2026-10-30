"""Expose the unchanged E56/E57 J-channel to the E59/E62 registered banks."""
import argparse
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e57/jlens'))
import cpu_job
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bank',choices=['E56','E57','E59','E62']);args=parser.parse_args()
    cpu_job.verify(ROOT,cpu_job.read(HERE/'CODE_SEAL_2026-10-27.json')['files'])
    raise SystemExit(cpu_job.run(args.bank))
