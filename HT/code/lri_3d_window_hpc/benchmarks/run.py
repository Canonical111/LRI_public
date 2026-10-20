"""Serial fresh-process, alternating-order benchmark campaign; no concurrent timings."""
from pathlib import Path
import sys,subprocess,argparse,json,time,os
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--group',choices=['solve','operator','setup','profile','cache'],required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
items=[]
if a.group=='solve':
    for L,x in [(10,.6),(10,.5182),(12,.6),(12,.5182)]:
        for rep in range(3):
            for impl in (['baseline','optimized'] if rep%2==0 else ['optimized','baseline']):
                items.append((f'{impl}_solve_L{L}_x{x}_r{rep}', ['--impl',impl,'--task','solve','--L',str(L),'--x',str(x)]))
elif a.group=='operator':
    for L in [10,12,14]:
        for J in ([0,1] if L<14 else [0]):
            for th in [1,2,4]:
                for impl in ['baseline','optimized']:
                    items.append((f'{impl}_operator_L{L}_J{J}_t{th}', ['--impl',impl,'--task','operator','--L',str(L),'--J',str(J),'--threads',str(th)]))
elif a.group=='setup':
    for L in [10,12,14]:
        for rep in range(3):
            for impl in (['baseline','optimized'] if rep%2==0 else ['optimized','baseline']):
                items.append((f'{impl}_setup_L{L}_r{rep}', ['--impl',impl,'--task','setup','--L',str(L)]))
elif a.group=='profile':
    for impl in ['baseline','optimized']:
        items.append((f'{impl}_profile_L12',['--impl',impl,'--task','solve','--L','12','--x','.6','--profile']))
else:
    cache=R/'runs/benchmark_cache'
    for L in [12,14]:
        for rep in range(3):
            items.append((f'cache_setup_L{L}_r{rep}', ['--impl','optimized','--task','setup','--L',str(L),'--cache-dir',str(cache)]))
    for rep in range(3):
        items.append((f'cache_solve_L12_r{rep}', ['--impl','optimized','--task','solve','--L','12','--x','.6','--cache-dir',str(cache)]))
logs=R/'results/benchmark_logs';outdir=R/'results/benchmarks';logs.mkdir(parents=True,exist_ok=True);outdir.mkdir(parents=True,exist_ok=True)
for label,args in items:
    dest=outdir/(label+'.json')
    if a.resume and dest.exists():continue
    cmd=[sys.executable,str(R/'benchmarks/worker.py'),*args,'--output',str(dest)]
    t=time.perf_counter()
    with (logs/(label+'.log')).open('w') as f:
        result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='4'),timeout=600)
    rec={'label':label,'command':cmd,'exit':result.returncode,'seconds_including_imports':time.perf_counter()-t}
    with (logs/'JOURNAL.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    print(label,result.returncode,round(rec['seconds_including_imports'],3),flush=True)
    if result.returncode:raise SystemExit('Benchmark failed; inspect '+str(logs/(label+'.log')))
