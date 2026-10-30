"""Separate §204 hardware-aware serial binding; running A4 archive is unchanged."""
import sys
from pathlib import Path
import serial81 as S
from hardware204 import AUTHORITY,production_gate,bind_units
from runtime import Runtime


def main():
    args=sys.argv
    def path(flag):return Path(args[args.index(flag)+1])
    ass=S.W.read(path('--assignment'));assets=path('--assets')
    # Index-modulo shards interleave analysis units: require one type for the entire run.
    plan=S.W.read(path('--inputs')/'SERIAL_PLAN.json')
    types=ass['coordinated_shard_gpu_types']
    S.W.require(len(types)==plan['shards'] and set(types)=={ass['gpu_type']},'existing E81 roster requires uniform hardware across coordinated shards')
    bind_units(ass,['E81_E90_coordinated_run'])
    receipt=path('--hardware-receipt') if '--hardware-receipt' in args else None
    metadata=production_gate(ass,receipt,assets,['text'])
    if receipt:
        i=args.index('--hardware-receipt');del args[i:i+2]
    class HardwareRuntime(Runtime):
        def __init__(self,assets):
            super().__init__(assets);self.hardware_assignment=ass;self.hardware_metadata=dict(gpu_type=ass['gpu_type'],hardware=metadata)
    S.Runtime=HardwareRuntime;S.main()

if __name__=='__main__':main()
