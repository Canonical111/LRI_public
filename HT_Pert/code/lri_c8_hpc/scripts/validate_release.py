#!/usr/bin/env python3
"""Release validation receipt bound to source, software stack and (on Slurm) the node.

Default steps: manifest check and the pytest suite. The suite runs with a FRESH temporary
NUMBA_CACHE_DIR so the receipt never certifies kernels loaded from a stale cache.
--full adds the saved-grid replay, an original-solver comparison and a file-system probe.
make_campaign.py accepts only a passing full compute-node receipt for the current source.
"""
from pathlib import Path
import argparse,json,os,platform,re,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from lri_c8 import io
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=ROOT/'validation/release.json')
p.add_argument('--full',action='store_true',help='also replay the saved grid, compare with the original solver and probe the file system')
p.add_argument('--threads',type=int,default=4,help='Numba threads for the --full numerical steps')
p.add_argument('--compare-cutoff',type=int,default=60)
p.add_argument('--work-dir',type=Path,help='directory for --full step outputs (default: next to --output)')
p.add_argument('--fs-probe-dir',type=Path,help='directory on the production file system (default: work dir)')
a=p.parse_args()
work=(a.work_dir or a.output.parent/(a.output.stem+'_steps')).resolve();work.mkdir(parents=True,exist_ok=True)

def cpu_model():
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):return line.split(':',1)[1].strip()
    except OSError:pass
    return platform.processor() or platform.machine()

def step(name,cmd,env=None,timeout=None):
    log=work/f'{name}.log';t=time.time()
    with log.open('w') as f:
        try:rc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:rc='timeout'
    text=log.read_text()
    print(f'[validate] {name}: rc={rc} {time.time()-t:.1f}s log={log}',flush=True)
    return {'returncode':rc,'seconds':time.time()-t,'log':str(log),'tail':text[-2000:]}

steps={};t0=time.time()
steps['manifest']=step('manifest',[sys.executable,str(ROOT/'tests/verify_manifest.py')])
def counts(text):
    last=text.strip().splitlines()[-1] if text.strip() else ''
    return {k:int(n) for n,k in re.findall(r'(\d+) (passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?|tests? collected)',last)}
cache=tempfile.mkdtemp(prefix='lri_c8_valcache_')
try:
    # The release suite runs complete and unfiltered: no inherited pytest options or plugins.
    env={k:v for k,v in os.environ.items() if not k.startswith('PYTEST_')}
    env.update(NUMBA_CACHE_DIR=cache,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    base=[sys.executable,'-m','pytest',str(ROOT/'tests'),'-q','-p','no:cacheprovider','-o','addopts=']
    c=step('pytest_collect',base+['--collect-only'],env=env)
    collected=counts(c['tail']).get('tests collected',counts(c['tail']).get('test collected',0))
    s=step('pytest',base,env=env)
    s['counts']=counts(s['tail']);s['collected']=collected;s['fresh_numba_cache']=True
    if s['returncode']==0 and (collected==0 or s['counts'].get('passed',0)!=collected or
                               any(s['counts'].get(k,0) for k in ('failed','error','errors','skipped','deselected','xfailed','xpassed'))):
        s['returncode']=f"incomplete run: {s['counts']} of {collected} collected"
    steps['pytest']=s
finally:shutil.rmtree(cache,ignore_errors=True)
if a.full:
    T=str(a.threads)
    steps['grid_replay']=step('grid_replay',[sys.executable,str(ROOT/'scripts/regression_saved_grid.py'),'--threads',T,
                              '--output',str(work/'regression_grid.json'),'--compare',str(ROOT/'benchmarks/REGRESSION_GRID.json')])
    steps['original_comparison']=step('original_comparison',[sys.executable,str(ROOT/'scripts/compare_original.py'),
                              '--cutoff',str(a.compare_cutoff),'--threads',T,'--output',str(work/'compare_original.json')])
    steps['fs_probe']=step('fs_probe',[sys.executable,str(ROOT/'scripts/fs_probe.py'),str((a.fs_probe_dir or work/'fs_probe').resolve()),
                              '--output',str(work/'fs_probe.json')])
ok=all(s['returncode']==0 for s in steps.values())
import numpy,numba,scipy
try:
    import threadpoolctl;tpc=threadpoolctl.__version__
except Exception as e:tpc=repr(e)
slurm={k.lower():os.environ[k] for k in ('SLURM_JOB_ID','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST','SLURM_CPUS_ON_NODE') if k in os.environ}
receipt={'source_sha256':io.source_digest(),'status':'pass' if ok else 'fail','returncode':0 if ok else 1,
         'seconds':time.time()-t0,'full':a.full,'kind':'compute-node' if 'slurm_job_id' in slurm else 'local',
         'host':platform.node(),'cpu_model':cpu_model(),'platform':platform.platform(),'slurm':slurm,
         'stack':{'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,
                  'scipy':scipy.__version__,'threadpoolctl':tpc,'executable':sys.executable},
         'numba_threading_layer_setting':os.environ.get('NUMBA_THREADING_LAYER','default'),
         'blas':io.blas_info(),'compare_cutoff':a.compare_cutoff if a.full else None,'steps':steps}
io.atomic_save(a.output,receipt)
print(f"[validate] status={receipt['status']} receipt={a.output}",flush=True)
raise SystemExit(0 if ok else 1)
