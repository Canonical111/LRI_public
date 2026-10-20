#!/usr/bin/env python3
"""Setup-only size probe at given cutoffs: NO eigensolve, no window, no couplings.

Each cutoff runs in a fresh child process that times, separately,
  graph     SphereBathBasis.build (full spherical Fock graph)
  projector highest_weight(J=0) (scalar SO(3) projector)
  vertices  build_rotational_vertices (four bare scalar bath vertices)
and records the child's peak RSS after each stage (ru_maxrss) plus sizes (full and
scalar bath states, vertex nnz/bytes). The parent adds the whole-child peak RSS from
os.wait4 and the wall time. These are measurements of setup only; a full window solve
also needs every lower-cutoff vacuum, the local space (x nz), Krylov vectors and
diagnostics, so they are a lower bound for a solve at the same L.

  python probe.py --L 14 16 18 --x 0.6 --max-bath-states 100000000 --max-basis-gib 120 --out DIR
"""
import argparse,json,os,resource,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'code'))


def rss_gib():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2


def child(a):
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
    import numba
    from threadpoolctl import threadpool_limits
    from ht3d.basis import SphereBathBasis
    from ht3d.rotational_vertices import build_rotational_vertices
    numba.set_num_threads(a.threads)
    rec={'L':a.L,'x':a.x,'threads':a.threads,'rss_gib_start':rss_gib()}
    with threadpool_limits(limits=1,user_api='blas'):
        t=time.perf_counter()
        b=SphereBathBasis.build(a.L,max_states=a.max_bath_states,max_bytes=int(a.max_basis_gib*1024**3))
        rec.update(graph_seconds=time.perf_counter()-t,full_bath_states=len(b.N),graph_bytes=int(b.nbytes),rss_gib_after_graph=rss_gib());Path(a.record).write_text(json.dumps(rec))
        t=time.perf_counter();S,N,P,keep,_=b.highest_weight(0,0)
        rec.update(projector_seconds=time.perf_counter()-t,scalar_bath_states=len(N),projector_nnz=int(S.nnz),rss_gib_after_projector=rss_gib());Path(a.record).write_text(json.dumps(rec))
        t=time.perf_counter();W=build_rotational_vertices(b,S,P,a.x,0)
        rec.update(vertex_seconds=time.perf_counter()-t,vertex_nnz=[int(w.nnz) for w in W],
                   vertex_bytes=int(sum(w.data.nbytes+w.indices.nbytes+w.indptr.nbytes for w in W)),rss_gib_after_vertices=rss_gib())
    print(json.dumps(rec),flush=True)
    Path(a.record).write_text(json.dumps(rec))
    return 0


def parent(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for L in a.L:
        rec=out/f'L{L}.json'
        cmd=[sys.executable,__file__,'child','--L',str(L),'--x',str(a.x),'--threads',str(a.threads),
             '--max-bath-states',str(a.max_bath_states),'--max-basis-gib',str(a.max_basis_gib),'--record',str(rec)]
        t=time.perf_counter();proc=subprocess.Popen(cmd);_,status,ru=os.wait4(proc.pid,0)
        row={'L':L,'rc':os.waitstatus_to_exitcode(status),'wall_seconds':time.perf_counter()-t,
             'child_peak_rss_gib':ru.ru_maxrss/1024**2,'stages':json.loads(rec.read_text()) if rec.exists() else None}
        rows.append(row);print(json.dumps(row),flush=True)
        if row['rc']!=0:break
    from ht3d.hpc import atomic_json
    atomic_json(out/'probe.json',{'purpose':'setup-only size probe; no eigensolve (lower bound for a solve)','rows':rows,
                                  'slurm_job':os.environ.get('SLURM_JOB_ID'),'node':os.uname().nodename,
                                  'max_bath_states':a.max_bath_states,'max_basis_gib':a.max_basis_gib})
    return 0 if all(r['rc']==0 for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd')
    for q in (p,):
        q.add_argument('--x',type=float,default=.6);q.add_argument('--threads',type=int,default=1)
        q.add_argument('--max-bath-states',type=int);q.add_argument('--max-basis-gib',type=float)
    p.add_argument('--L',type=int,nargs='+');p.add_argument('--out')
    c=sub.add_parser('child');c.add_argument('--L',type=int,required=True);c.add_argument('--x',type=float,required=True)
    c.add_argument('--threads',type=int,required=True);c.add_argument('--max-bath-states',type=int,required=True)
    c.add_argument('--max-basis-gib',type=float,required=True);c.add_argument('--record',required=True)
    a=p.parse_args()
    if a.cmd=='child':return child(a)
    if not a.L or not a.out or a.max_bath_states is None or a.max_basis_gib is None:
        p.error('--L, --out, --max-bath-states and --max-basis-gib are required (explicit large-L limits)')
    return parent(a)

if __name__=='__main__':raise SystemExit(main())
