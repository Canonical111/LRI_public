"""Benchmark actual vertex CSR applications with unchanged input precision.

Prefer --store for a verified, portable, read-only .npy vertex store.
--trusted-pickle is an explicit compatibility option for a locally generated
cache; never use it on an uploaded or otherwise untrusted pickle.

This measures the backend CSR-apply interface with reusable output. The SciPy
backend creates a temporary product before copying it to that output, whereas
the native kernel writes directly. Cropped SciPy matrices are prepared once,
outside the timed loop. It is a kernel-interface diagnostic, not a full-solver
or multi-node scaling benchmark. Run without competing local benchmark jobs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import pickle
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
from native_backend import load_backend
from vertex_store import load_vertex_store, atomic_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--store', type=Path)
    source.add_argument('--trusted-pickle', type=Path)
    p.add_argument('--threads', type=int, nargs='+', default=[1,2,4,8])
    p.add_argument('--cutoffs', type=int, nargs='+')
    p.add_argument('--vertices', type=int, nargs='+', choices=[1,2,3,4], default=[1,2,4])
    p.add_argument('--taylor-degree', type=int, default=0)
    p.add_argument('--nrhs', type=int, default=10)
    p.add_argument('--repeats', type=int, default=5)
    p.add_argument('--native-cache', type=Path)
    p.add_argument('--serial-work-threshold', type=int, default=0,
                   help='Default zero forces each requested thread count for this diagnostic')
    p.add_argument('--output', type=Path, default=ROOT/'results/native_kernel_benchmark_replay.json')
    args = p.parse_args()
    if (args.repeats < 1 or args.nrhs < 1 or args.taylor_degree < 0 or
            any(t < 1 for t in args.threads) or args.serial_work_threshold < 0):
        raise ValueError('Invalid repeat count, dimensions, thread count, or threshold')
    started = time.perf_counter()
    if args.store is not None:
        N, unused_P, vertices, metadata = load_vertex_store(args.store)
        input_metadata = {'kind':'verified-readonly-mmap', 'path':str(args.store.resolve()),
                          'manifest_sha256':hashlib.sha256((args.store/'manifest.json').read_bytes()).hexdigest()}
    else:
        with args.trusted_pickle.open('rb') as src:
            cache = pickle.load(src)
        N, vertices, metadata = cache['N'], cache['W'], cache['metadata']
        input_metadata = {'kind':'explicit-trusted-legacy-pickle', 'path':str(args.trusted_pickle.resolve())}
        del cache
    input_seconds = time.perf_counter()-started
    top_cutoff = int(metadata.get('cutoff', np.max(N)))
    cutoffs = (sorted(set(args.cutoffs)) if args.cutoffs is not None else
               sorted(set([max(0,top_cutoff-4),top_cutoff])))
    if any(c < 0 or c % 2 or c > top_cutoff for c in cutoffs):
        raise ValueError('Cutoffs must be even nonnegative values covered by the input store')
    dtype = vertices[0][0].dtype
    if dtype not in (np.dtype(np.float64),np.dtype(np.longdouble)):
        raise ValueError('Input precision must be float64 or longdouble')
    for j in args.vertices:
        if args.taylor_degree >= len(vertices[j-1]):
            raise ValueError('Requested Taylor degree is absent from the input store')
        if vertices[j-1][args.taylor_degree].dtype != dtype:
            raise ValueError('All selected input vertices must have the same dtype')
    rng = np.random.default_rng(590367)
    xfull = rng.standard_normal((len(N),args.nrhs)).astype(dtype)
    backend = load_backend('native', cache_dir=args.native_cache,
                           serial_work_threshold=args.serial_work_threshold)
    scipy = load_backend('scipy')
    results = []
    for j in args.vertices:
        matrix = vertices[j-1][args.taylor_degree]
        for cutoff in cutoffs:
            nb = int(np.searchsorted(N,cutoff,side='right'))
            x = xfull[:nb]
            cropped = matrix if nb == len(N) else matrix[:nb,:nb]
            expected = cropped @ x
            for name,threads in [('scipy',1)]+[('native',t) for t in args.threads]:
                obj, used = (scipy,cropped) if name=='scipy' else (backend,matrix)
                output = obj.csr_spmm(used,x,nrows=nb,ncols=nb,threads=threads)
                err = np.max(np.abs(output-expected),initial=dtype.type(0))
                scale = max(dtype.type(1),np.max(np.abs(expected),initial=dtype.type(0)))
                if err/scale > 8*np.finfo(dtype).eps:
                    raise AssertionError((j,cutoff,name,threads,str(err/scale)))
                timing = []
                for unused in range(args.repeats):
                    begin = time.perf_counter()
                    obj.csr_spmm(used,x,nrows=nb,ncols=nb,threads=threads,out=output)
                    timing.append(time.perf_counter()-begin)
                row_nnz = np.diff(cropped.indptr)
                row = {'bath_degree':j, 'taylor_degree':args.taylor_degree,
                       'cutoff':cutoff, 'bath_states':nb, 'nrhs':args.nrhs,
                       'full_nnz':matrix.nnz, 'retained_nnz':cropped.nnz,
                       'backend':name, 'threads':threads, 'seconds':timing,
                       'median_seconds':statistics.median(timing),
                       'max_scaled_error':str(err/scale),
                       'row_nnz_min':int(np.min(row_nnz)),
                       'row_nnz_median':float(np.median(row_nnz)),
                       'row_nnz_max':int(np.max(row_nnz))}
                results.append(row)
                print(json.dumps(row),flush=True)
    payload = {'description':__doc__, 'cpu_count':os.cpu_count(),
               'affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
               'numpy_version':np.__version__, 'dtype':str(dtype),
               'precision_significand_bits':int(np.finfo(dtype).nmant)+1,
               'backend':backend.metadata, 'input':input_metadata,
               'input_load_and_verify_seconds':input_seconds,
               'environment':{key:os.environ.get(key) for key in (
                   'OMP_NUM_THREADS','OMP_WAIT_POLICY','GOMP_SPINCOUNT','OMP_PROC_BIND',
                   'OMP_PLACES','OPENBLAS_NUM_THREADS','NUMBA_NUM_THREADS')},
               'scope':'Local kernel-interface timing, not full-solver or multi-node scaling or a DRAM-bandwidth measurement',
               'results':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    atomic_json(args.output,payload)


if __name__=='__main__':
    main()
