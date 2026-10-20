"""Warm compiler/JIT caches, then run local numerical and operational checks.

Warmup is separate so subprocess signal/ownership test time limits measure the
operation being tested rather than a first C++ build. No large campaign is hidden.
"""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='4',NUMBA_NUM_THREADS='4')
    env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
    env.setdefault('LRI_COEFF_NATIVE_CACHE',str(ROOT.parent/'lri_coeff_nativecache'))
    # Native library is compiled once, not concurrently by the first two task tests.
    program=("from numba import set_num_threads; set_num_threads(4); "
             "from lri_coeff.engine import Engine; "
             "Engine(2,backend='native').solve(verbose=False); "
             "Engine(2,backend='numba').solve(verbose=False); "
             "print('Native/JIT warmup complete.')")
    t=time.monotonic()
    warm=subprocess.run([sys.executable,'-c',program],env=env,capture_output=True,text=True,cwd=ROOT)
    out=dict(command='python -m pytest -q tests --durations=8',warmup_seconds=time.monotonic()-t,
             warmup_returncode=warm.returncode,warmup_stdout=warm.stdout,warmup_stderr=warm.stderr,
             scope='Local validation, not an actual Slurm or inter-node test.')
    print(warm.stdout,flush=True)
    if warm.returncode:
        out.update(returncode=warm.returncode,seconds=0,stdout='',stderr='Warmup failed; tests not run.')
    else:
        t=time.monotonic()
        p=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'tests'),'--durations=8'],env=env,capture_output=True,text=True,cwd=ROOT)
        out.update(returncode=p.returncode,seconds=time.monotonic()-t,stdout=p.stdout,stderr=p.stderr)
        print(p.stdout);print(p.stderr)
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/validation.json').write_text(json.dumps(out,indent=2)+'\n')
    raise SystemExit(out['returncode'])
