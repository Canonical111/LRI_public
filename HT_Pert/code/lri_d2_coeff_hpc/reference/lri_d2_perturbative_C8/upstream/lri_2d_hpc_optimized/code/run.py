"""Backward-compatible command spelling; restartable driver is ht2d.hpc.
Old unchecksummed result files are reference data, not restart envelopes.
"""
import sys
from ht2d.hpc import main
if __name__=='__main__':
    args=[]
    for x in sys.argv[1:]:
        if x=='--no-diagnostics':args.extend(['--diagnostics','none'])
        elif x=='--first-only':args.extend(['--diagnostics','first'])
        else:args.append(x)
    raise SystemExit(main(args))
