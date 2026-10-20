#!/usr/bin/env python3
"""Re-run the phase-instrumented baseline at one thread. No hardware perf access needed."""
from pathlib import Path
import argparse, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from workloads import files
import toolchain

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if any(a.out.iterdir()):raise FileExistsError('Use an empty output directory')
    src=ROOT/'benchmarks/profiling/reference';inputs=ROOT/'reference/inputs'
    for mode,cpp in [('qmc','profile_qmc.cpp'),('power','profile_power.cpp')]:
        binary=a.out/f'profile_{mode}';subprocess.run(toolchain.compile_cmd([src/cpp],binary,opt=['-O3']),check=True)
        w=files(a.out/mode,inputs,7,mode,1024 if mode=='qmc' else 2,4 if mode=='qmc' else 1)
        if mode=='qmc':cmd=[binary,inputs,7,1024,4,41946543,w['net'],a.out/'qmc.json','.8','nonprimitive',w['counts']]
        else:cmd=[binary,inputs,7,6,2,1,381957213,a.out/'power.json','power','.8',w['counts']]
        with (a.out/f'{mode}.log').open('w') as f:subprocess.run(['/usr/bin/time','-v',*map(str,cmd)],stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OMP_NUM_THREADS='1'))
        print(a.out/f'{mode}.log')
if __name__=='__main__':main()
