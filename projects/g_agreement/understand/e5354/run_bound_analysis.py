"""Integrator command: consume the existing E53+E54 guard exactly once."""
from types import SimpleNamespace
from .contract import ROOT, HERE, read, sha, sources
from .analyse import analyse


def main():
    sources()
    command = read(HERE/'ANALYSIS_COMMAND.json')
    args = {k: ROOT/v for k,v in command['paths'].items()}
    analyse(SimpleNamespace(**args, output_seal=command['output_seal_sha256'],
                            context_seal=sha(args['context']/'INPUT_SEAL.json')))


if __name__ == '__main__':
    main()
