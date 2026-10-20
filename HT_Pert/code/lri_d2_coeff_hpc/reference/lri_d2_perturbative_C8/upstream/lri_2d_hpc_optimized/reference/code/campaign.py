#!/usr/bin/env python3
"""Serial reproduction campaign: one writer per output; all failed jobs recorded."""
from pathlib import Path
import argparse,json,subprocess,sys,time,os
from run import atomic_json
ROOT=Path(__file__).resolve().parents[1]
def tasks():
    out=[]
    for x in [.495,.475,.45,.4,.35,.3,.25,.2,.15,.126]:
        tag=f'{x:.3f}';teacher=f'results/teacher_L6_x{tag}.json'
        out.append(['--L','6','--x',str(x),'--nz','24','--osc','192','--train-keep','20','--output',teacher])
        for L in [8,10]:
            out.append(['--L',str(L),'--x',str(x),'--nz','16','--basis',teacher,'--output',f'results/window_L{L}_z16_x{tag}.json'])
        out.append(['--L','10','--x',str(x),'--nz','12','--basis',teacher,'--output',f'results/window_L10_z12_x{tag}.json'])
        out.append(['--L','10','--x',str(x),'--nz','24','--osc','192','--window','none','--output',f'results/raw_L10_x{tag}.json'])
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=300);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=10000);a=p.parse_args()
    journal=ROOT/'validation/campaign_runs.json';records=json.loads(journal.read_text()) if journal.exists() else []
    logdir=ROOT/'validation/logs';logdir.mkdir(exist_ok=True)
    env={**os.environ,**{k:'1' for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMBA_NUM_THREADS']}}
    for no,args in enumerate(tasks()):
        if not a.start<=no<a.end:continue
        target=ROOT/args[args.index('--output')+1]
        if target.exists():print('EXISTS',target.name,flush=True);continue
        print('RUN',no,' '.join(args),flush=True);t=time.perf_counter()
        try:
            cp=subprocess.run([sys.executable,str(ROOT/'code/run.py'),*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=a.timeout)
            log=cp.stdout+'\n'+cp.stderr;ok=cp.returncode==0 and target.exists();err=None if ok else f'exit {cp.returncode}'
        except subprocess.TimeoutExpired as e:
            log=str(e);ok=False;err='wall time exceeded; no accepted output'
        (logdir/f'job_{no:03d}.txt').write_text(log)
        row={'job':no,'arguments':args,'accepted':ok,'error':err,'seconds':time.perf_counter()-t}
        records.append(row);atomic_json(journal,records)
        print('DONE',no,ok,round(row['seconds'],2),flush=True)
if __name__=='__main__':main()
