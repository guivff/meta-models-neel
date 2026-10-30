"""W-text's sole CPU entrypoint, only after the operator's COMPLETE output seal."""
from pathlib import Path
import argparse,re
from .analyze_once import run
CPU_ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e139-inputs-v1/cpu_only')
CPU_SHA='78a68412815eacdd76066ddf11152fffd638da48ad34631aa459d6b8b2b33dad'
OUT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e139-analysis-once')
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e139-analysis-once.ATTEMPT.json')
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--acquisition-root',type=Path,required=True);p.add_argument('--acquisition-sha',required=True);a=p.parse_args(argv)
 if not re.fullmatch('[0-9a-f]{64}',a.acquisition_sha):p.error('actual COMPLETE OUTPUT_SEAL SHA256 required')
 run(CPU_ROOT,CPU_SHA,a.acquisition_root,a.acquisition_sha,OUT,GUARD)
if __name__=='__main__':main()
