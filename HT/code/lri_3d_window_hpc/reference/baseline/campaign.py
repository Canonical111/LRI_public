"""Independent parameter jobs; cutoff continuation inside each job. Not MPI."""
from pathlib import Path
import subprocess,sys,os,json,time,concurrent.futures
R=Path(__file__).resolve().parent
XS=[.7499,.745,.74,.725,.7,.675,.65,.625,.6,.575,.55,.535,.525,.52,.5182]

def run_cmd(cmd,log):
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
    t=time.perf_counter()
    with open(log,'a') as f:
        f.write('\nCOMMAND '+repr(cmd)+'\n');f.flush()
        p=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
    return p.returncode,time.perf_counter()-t

def job(x):
    log=R/f'results/logs/campaign_x{x}.log';records=[]
    teacher=Path(f'results/curve/teacher_L6_x{x}.json')
    tasks=[(['--L','6','--x',str(x),'--nz','24','--osc','192','--window','vacuum','--train-keep','20','--diagnostics','first'],teacher)]
    prev=teacher
    for L in [8,10]:
        out=Path(f'results/curve/window_L{L}_x{x}.json')
        tasks.append((['--L',str(L),'--x',str(x),'--nz','16','--window','vacuum','--basis',str(teacher),'--seed',str(prev),'--diagnostics','all'],out));prev=out
    # Largest row subset is run separately to keep campaign sizes honest.
    tasks += [(['--L','10','--x',str(x),'--nz','20','--osc','160','--window','none','--diagnostics','first'],Path(f'results/raw/raw_L10_x{x}.json')),
              (['--L','10','--x',str(x),'--nz','12','--window','vacuum','--basis',str(teacher),'--seed',str(prev),'--diagnostics','none'],Path(f'results/local/window_L10_k12_x{x}.json'))]
    for args,out in tasks:
        if (R/out).exists():
            d=json.loads((R/out).read_text())
            if not d.get('accepted'):raise ValueError(f'Unaccepted existing {out}')
            records.append({'output':str(out),'status':'existing'});continue
        cmd=[sys.executable,'code/run.py',*args,'--output',str(out),'--resume']
        rc,dt=run_cmd(cmd,log);records.append({'command':cmd,'exit':rc,'seconds':dt,'output':str(out)})
        (R/f'results/logs/journal_x{x}.json').write_text(json.dumps(records,indent=2))
        if rc:break
    print('FINISHED',x,records[-1],flush=True);return records

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--x',nargs='+',type=float,default=XS);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(job,a.x))
