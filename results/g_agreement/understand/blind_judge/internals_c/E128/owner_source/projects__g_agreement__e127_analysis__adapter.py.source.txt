"""§236 E127 one CPU analysis after source/test commit; judging bank cap USD3."""
import argparse
from pathlib import Path
from . import transport,rules

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=transport.committed(Path(__file__).resolve().parent)
    print(transport.run(transport.core.read(args.spec),'E127',commit,rules.analyze))

if __name__=='__main__':main()
