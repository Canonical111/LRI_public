#!/usr/bin/env python3
"""Run planned C8 shards on one machine, with the same checkpoints as Slurm.

The product of --workers and --threads is the requested CPU concurrency.
Completed jobs are skipped by the normal checked worker, making this resumable.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import os
from pathlib import Path
import subprocess
import sys
import time
from common import ROOT,load


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    ap.add_argument('--workers',type=int,default=1)
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--scratch',type=Path)
    ap.add_argument('--indices',help='Optional comma-separated job indices')
    args=ap.parse_args()
    if min(args.workers,args.threads)<1:raise ValueError('Positive worker and thread counts required')
    directory=args.directory.resolve()
    manifest=load(directory/'manifest.json')
    indices=list(range(len(manifest['jobs']))) if args.indices is None else [int(x)for x in args.indices.split(',')]
    if len(set(indices))!=len(indices) or any(i<0 or i>=len(manifest['jobs']) for i in indices):
        raise ValueError('Invalid or duplicate job index')
    logs=directory/'local_logs';logs.mkdir(exist_ok=True)
    scratch=args.scratch.resolve() if args.scratch else directory/'local_scratch'
    scratch.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    def run(index):
        start=time.monotonic()
        path=logs/f'job_{index:06d}.log'
        cmd=[sys.executable,'-B',str(ROOT/'tools/production.py'),'run',str(directory),
             '--index',str(index),'--threads',str(args.threads),'--scratch',str(scratch)]
        with path.open('a') as log:
            code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
        if code:raise RuntimeError(f'Job {index} failed, exit {code}: {path}')
        return index,time.monotonic()-start
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(run,i):i for i in indices}
        for f in concurrent.futures.as_completed(futures):
            try:index,seconds=f.result()
            except BaseException:
                for g in futures:g.cancel()
                raise
            print(f'completed job {index}/{len(manifest["jobs"])-1} in {seconds:.2f} s',flush=True)


if __name__=='__main__':main()
