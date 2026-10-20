#!/usr/bin/env python3
"""Recompute raw five-loop Laurent amplitudes; no analytic periods are inputs.

Examples:
  python run_sector.py --method scalar --order 18 --threads 4
  python run_sector.py --method combined-simd --order 22 --threads 4
The SIMD implementation requires x86 AVX-512F/FMA. The scalar control is the
portable fallback on platforms with a 64-bit long-double significand.
Large-degree grids can require several gigabytes of memory.
"""
from pathlib import Path
import argparse,json,os,platform,subprocess,sys
from kernel_inputs import ROOT,graph_file,weight_file
import numpy as np

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--method',choices=['scalar','original-double','combined-simd'],default='scalar')
    ap.add_argument('--order',type=int,default=18)
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--workdir',type=Path)
    args=ap.parse_args()
    if args.threads<1:ap.error('threads must be positive')
    if args.order>24:ap.error('This full-grid driver limits degree to 24 to avoid excessive memory use')
    method=args.method;combined=method=='combined-simd';extended=method!='original-double'
    folder=(args.workdir or ROOT/'work'/method).resolve();folder.mkdir(parents=True,exist_ok=True)
    if combined:
        flags=Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists()else ''
        if 'avx512f' not in flags:ap.error('combined-simd requires AVX-512F; use --method scalar')
    graph_file(folder,combined);weight_file(folder,args.order,extended)
    source=ROOT/'source'/({'scalar':'ising_five_engine_extended.cpp','original-double':'ising_five_engine_original.cpp','combined-simd':'ising_five_engine_combined_simd.cpp'}[method])
    exe=folder/'engine'
    command=['g++','-O3','-march=native','-std=c++17','-fopenmp']
    if combined:command+=['-ffp-contract=off']
    command+=[str(source),'-o',str(exe)]
    subprocess.run(command,check=True)
    metadata={'method':method,'degree':args.order,'threads':args.threads,'platform':platform.platform(),'numpy_version':np.__version__,'longdouble_significand_bits':np.finfo(np.longdouble).nmant+1,'longdouble_storage_bytes':np.dtype(np.longdouble).itemsize,'compile_command':command,'analytic_periods_used_by_integrator':False}
    (folder/f'environment_{args.order}.json').write_text(json.dumps(metadata,indent=2))
    subprocess.run([str(exe),str(args.order),str(folder),str(args.threads)],check=True)
if __name__=='__main__':main()
