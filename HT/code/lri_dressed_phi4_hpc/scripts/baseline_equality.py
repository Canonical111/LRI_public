#!/usr/bin/env python3
"""--window none equality against a frozen baseline source tree (e.g. e637dfd).

Each tree solves the same seeded points in a fresh subprocess with identical thread
settings; gaps and coupling coordinates must agree to --tol (default 1e-12). The baseline
tree must carry the pinned e637dfd numerical source, and at most --cores//--threads
solves run at once.
"""
import argparse,hashlib,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASELINE_SOURCE_SHA256='6984acb39d6d9f69aab8d32943e1c3c4f62b8886bc7ee668519f80b11ab1f554'   # e637dfd src/lri_dressed/*.py


def tree_fingerprint(tree):
    """Same algorithm as lri_dressed.io.source_fingerprint, applied to another tree."""
    h=hashlib.sha256();files=sorted((Path(tree)/'src'/'lri_dressed').glob('*.py'))
    if not files:raise SystemExit(f'No package sources under {tree}')
    for p in files:h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()


def check_baseline(tree):
    tree=Path(tree).resolve();got=tree_fingerprint(tree)
    if got!=BASELINE_SOURCE_SHA256:raise SystemExit(f'Baseline {tree} has source {got}, not the pinned e637dfd {BASELINE_SOURCE_SHA256}')
    if tree_fingerprint(ROOT)==got:raise SystemExit('The current tree equals the baseline; nothing to compare')
    return got
POINTS=[(16,24,192,.24),(16,24,192,.2),(16,24,192,.1),(16,24,192,.05),(16,24,192,.01),(12,20,160,.001),(12,20,160,.0001)]
CHILD='''
import json,sys
from numba import set_num_threads
from threadpoolctl import threadpool_limits
threadpool_limits(1);set_num_threads(int(sys.argv[6]))
import lri_dressed.io as io
from lri_dressed.solver import DressedSolver
where={'module':io.__file__,'source_sha256':io.source_fingerprint()}
N,z,o,d=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4])
theta=json.load(open(sys.argv[5]))['theta']
h=DressedSolver(N,z,o,backend='tensor');h.set_delta(d);r=h.solve(theta)
print(json.dumps(dict({k:r[k] for k in ('theta','even_gaps','odd_gaps','Delta_thermal')},imported=where)))
'''

def solve(tree,pt,threads,expect):
    tree=Path(tree).resolve();N,z,o,d=pt;seed=ROOT/'inputs'/f'N{N}_z{z}_o{o}_d{d:.8f}.json'
    env=dict(os.environ,PYTHONPATH=str(Path(tree)/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS=str(threads))
    p=subprocess.run([sys.executable,'-c',CHILD,str(N),str(z),str(o),repr(d),str(seed),str(threads)],env=env,capture_output=True,text=True,cwd=tree)
    if p.returncode:raise RuntimeError(f'{tree} {pt}: {p.stderr[-2000:]}')
    r=json.loads(p.stdout.strip().splitlines()[-1]);imp=r['imported']
    # The child must have imported the package of THIS tree, with the expected numerical fingerprint.
    if not Path(imp['module']).resolve().is_relative_to(tree/'src') or imp['source_sha256']!=expect:
        raise RuntimeError(f'{tree}: child imported {imp}, expected {expect} under {tree/"src"}')
    return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--tol',type=float,default=1e-12)
    ap.add_argument('--cores',type=int,default=int(os.environ.get('SLURM_CPUS_ON_NODE') or os.cpu_count()));a=ap.parse_args()
    a.baseline=str(Path(a.baseline).resolve());pinned=check_baseline(a.baseline);current=tree_fingerprint(ROOT)
    expect={a.baseline:pinned,str(ROOT):current}
    jobs=[(t,pt) for pt in POINTS for t in (a.baseline,str(ROOT))];width=max(1,a.cores//max(1,a.threads))
    with ThreadPoolExecutor(min(width,len(jobs))) as ex:res=list(ex.map(lambda j:solve(j[0],j[1],a.threads,expect[j[0]]),jobs))
    rows=[];worst=0.
    for i,pt in enumerate(POINTS):
        old,new=res[2*i],res[2*i+1]
        diff=max(max(abs(x-y) for x,y in zip(old[k],new[k])) for k in ('theta','even_gaps','odd_gaps'))
        worst=max(worst,diff);rows.append({'point':pt,'max_difference':diff})
        print(pt,'max |new-baseline|',diff,flush=True)
    passed=worst<=a.tol
    Path(a.output).write_text(json.dumps({'baseline':a.baseline,'baseline_source_sha256':pinned,'current':str(ROOT),
        'current_source_sha256':current,'imported':[r['imported'] for r in res],'tol':a.tol,'concurrency':width,'threads':a.threads,
        'worst':worst,'passed':passed,'points':rows},indent=2))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
