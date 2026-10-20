"""Independent-process benchmarks, sequential execution to avoid contention."""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    outdir=ROOT/'results/benchmarks';outdir.mkdir(exist_ok=True)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='4',LRI_COEFF_NATIVE_CACHE=os.environ.get('LRI_COEFF_NATIVE_CACHE',str(Path.home()/'.cache/lri_coeff')))
    designs=[]
    for L in [16,20]:
        for rep in range(1,4):
            for backend,threads in [('reference',1),('optimized',1),('optimized',4)]:designs.append((L,backend,threads,rep))
    for L,backend,threads,rep in designs:
        dest=outdir/f'{backend}_L{L}_t{threads}_r{rep}.json'
        if dest.exists():continue
        cmd=[sys.executable,str(ROOT/'scripts/benchmark.py'),'--backend',backend,'--L',str(L),'--threads',str(threads),'--out',str(dest)]
        env['OMP_NUM_THREADS']=str(threads)
        print('START',dest.name,time.ctime(),flush=True)
        p=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=400)
        if p.returncode:
            (outdir/(dest.stem+'.failed.json')).write_text(json.dumps(dict(returncode=p.returncode,stderr=p.stderr,stdout=p.stdout),indent=2));raise SystemExit(p.returncode)
        r=json.loads(dest.read_text());print('DONE',round(r['total_seconds'],3),round(r['peak_rss_KiB']/2**20,3),'GiB',flush=True)
    print('ALL BENCHMARKS COMPLETE',flush=True)
