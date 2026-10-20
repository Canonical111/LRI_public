#!/usr/bin/env python3
"""Rebuild the exact normalization; optionally regenerate both period runs."""
from pathlib import Path
import subprocess,sys,argparse
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--numerical',action='store_true');args=p.parse_args()
subprocess.run([sys.executable,str(ROOT/'code/verify_F1b.py')],check=True)
if args.numerical:
    for label,dps,radius,taylor,asym,step in [('check70',70,80,210,125,'.30'),('check100',100,100,260,150,'.25')]:
        subprocess.run([sys.executable,str(ROOT/'code/evaluate_F1b.py'),'--label',label,'--dps',str(dps),
                       '--radius',str(radius),'--taylor',str(taylor),'--asymptotic',str(asym),'--step',step],check=True)
subprocess.run([sys.executable,str(ROOT/'code/finalize_F1b.py')],check=True)
print('Completed exact input/normalization and saved numerical consistency checks.')
print('Fresh numerical period runs: '+str(args.numerical))
