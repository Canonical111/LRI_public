from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description='HPC finite-cutoff LRI solver; unchanged Hamiltonian, float64.')
    parser.add_argument('--task',choices=['thermal','phi6'],default='thermal')
    parser.add_argument('--degree',type=int)
    parser.add_argument('--cutoffs',type=int,nargs='+',required=True)
    parser.add_argument('--threads',type=int,default=int(os.environ.get('SLURM_CPUS_PER_TASK','1')))
    parser.add_argument('--mpi',action='store_true',help='Experimental distributed-row backend; smoke-test on the target MPI first')
    parser.add_argument('--memory-limit-gib',type=float,help='Conservative per-rank working-memory budget; not a hard RSS limit')
    parser.add_argument('--output-dir',type=Path,default=Path('results'))
    parser.add_argument('--checkpoint-dir',type=Path)
    parser.add_argument('--basis-cache',type=Path)
    parser.add_argument('--resume',action='store_true',help='Skip completed source/config-matched outputs; resume scalar checkpoints')
    parser.add_argument('--plan',action='store_true',help='Count states without constructing the full basis')
    args=parser.parse_args()
    if args.threads<1:parser.error('--threads must be positive')
    if args.memory_limit_gib is not None and args.memory_limit_gib<=0:parser.error('memory limit must be positive')
    if any(L<2 or L%2 for L in args.cutoffs):parser.error('cutoffs must be even and >=2')
    degree=args.degree or (7 if args.task=='thermal' else 5)
    if degree not in ([6,7] if args.task=='thermal' else [3,5]):parser.error('unsupported task/degree')
    if args.task=='phi6' and min(args.cutoffs)<4:parser.error('phi6 cutoffs must be >=4')
    # Avoid nested threaded BLAS while the sparse kernels own the cores.
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        os.environ[key]='1'
    os.environ['NUMBA_NUM_THREADS']=str(args.threads)
    os.environ['OMP_NUM_THREADS']=str(args.threads)
    import numba
    numba.set_num_threads(args.threads)
    from .parallel import mpi_world
    comm=mpi_world(args.mpi);root=comm is None or comm.Get_rank()==0
    if args.mpi and root:
        print('NOTICE: real MPI is unbenchmarked in the delivery environment; run tests/mpi_smoke.py first.',file=sys.stderr,flush=True)
    try:
        from .solver import compute,atomic_json,source_fingerprint
        if args.plan:
            from .basis import count_tables
            order=degree//2;pmax=(3 if args.task=='thermal' else 6)+4*order;qmax=4*order
            size=1 if comm is None else comm.Get_size()
            for L in args.cutoffs:
                table_bytes=((qmax+1)*(4*L+1)*(L+1)+(pmax+1)*(qmax+1)*(4*L+1))*8
                if args.memory_limit_gib and table_bytes>args.memory_limit_gib*2**30/2:
                    raise MemoryError('Counting tables exceed half the per-rank memory budget')
                G,Z=count_tables(L,pmax,qmax);D=int(Z[pmax,qmax,4*L]);del G,Z
                if root:print(json.dumps({'cutoff':L,'dimension':D,'ranks':size,'state_rows_per_rank_upper':(D+size-1)//size,
                     'suffix_table_mib':table_bytes/2**20,
                     '100_vector_working_estimate_gib_per_rank':800*((D+size-1)//size)/2**30,
                     'note':'Estimate excludes exact edge/halo sizes and interpreter/JIT overhead. No truncation or precision changes.'}),flush=True)
            return
        args.output_dir.mkdir(parents=True,exist_ok=True)
        checkpoint_dir=args.checkpoint_dir or args.output_dir/'checkpoints'
        for L in args.cutoffs:
            stem=f'{args.task}_d{degree}_L{L}'
            output=args.output_dir/(stem+'.json')
            checkpoint=checkpoint_dir/(stem+'.json')
            old=json.loads(output.read_text()) if root and output.exists() else None
            if comm is not None:old=comm.bcast(old,root=0)
            if old:
                if not args.resume:raise FileExistsError(f'{output} exists; use --resume or a new output directory')
                if (old.get('task'),old.get('degree'),old.get('cutoff'),old.get('source_sha256'))!=(args.task,degree,L,source_fingerprint()):
                    raise ValueError('Completed output source/config mismatch; refusing to reuse it')
                if root:print(json.dumps({'skipped':str(output)}),flush=True)
                continue
            if checkpoint.exists() and not args.resume:
                raise FileExistsError(f'{checkpoint} exists; use --resume or a new checkpoint directory')
            row=compute(L,args.task,degree,comm,checkpoint,args.memory_limit_gib,args.basis_cache)
            if root:
                atomic_json(output,row)
                print(json.dumps({'output':str(output),'cutoff':L,'seconds':row['seconds'],
                                  'dimension':row['basis_dimension']}),flush=True)
    except BaseException:
        if comm is not None:
            import traceback
            traceback.print_exc();comm.Abort(1)
        raise

if __name__=='__main__':main()
