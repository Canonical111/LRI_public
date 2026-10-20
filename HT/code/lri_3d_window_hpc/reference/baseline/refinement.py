"""Higher cutoff and independent local references, never fitting physical targets."""
from pathlib import Path
import json,sys,time,subprocess,os,concurrent.futures
R=Path(__file__).resolve().parent

def main():
 p=__import__('argparse').ArgumentParser();p.add_argument('--x',nargs='+',type=float,default=[.745,.7,.65,.6,.55,.525,.5182]);p.add_argument('--workers',type=int,default=1);a=p.parse_args()
 def job(x):
  teacher=Path(f'results/curve/teacher_L6_x{x}.json');seed=Path(f'results/curve/window_L10_x{x}.json')
  while not (R/seed).exists():time.sleep(5)
  tasks=[(['--L','12','--nz','16','--basis',str(teacher),'--seed',str(seed),'--diagnostics','first'],Path(f'results/curve/window_L12_x{x}.json'))]
  if x in [.6,.5182]:
   tasks.append((['--L','10','--nz','32','--osc','256','--seed',str(seed),'--diagnostics','first'],Path(f'results/local/independent_L10_z32_x{x}.json')))
   tasks.append((['--L','12','--nz','24','--osc','224','--seed',str(tasks[0][1]),'--diagnostics','first'],Path(f'results/local/independent_L12_z24_x{x}.json')))
  history=[]
  for opts,out in tasks:
   if (R/out).exists():continue
   cmd=[sys.executable,'code/run.py','--x',str(x),'--window','vacuum',*opts,'--output',str(out),'--resume']
   t=time.perf_counter()
   with open(R/f'results/logs/refine_x{x}.log','a') as log:
    log.write('\n'+repr(cmd)+'\n');log.flush()
    p=subprocess.run(cmd,cwd=R,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
   history.append({'command':cmd,'exit':p.returncode,'seconds':time.perf_counter()-t})
   (R/f'results/logs/refine_journal_x{x}.json').write_text(json.dumps(history,indent=2))
   if p.returncode:break
  print('REFINE FINISHED',x,history,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(job,a.x))
if __name__=='__main__':main()
