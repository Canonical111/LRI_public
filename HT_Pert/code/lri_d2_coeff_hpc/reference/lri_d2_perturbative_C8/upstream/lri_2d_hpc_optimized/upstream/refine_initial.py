#!/usr/bin/env python3
"""Independent local/auxiliary and extra bath-cutoff checks. No curve fits."""
from pathlib import Path
import subprocess,sys,time,json,os
from run import atomic_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    env={**os.environ,**{k:'1' for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMBA_NUM_THREADS']}}
    commands=[]
    for x in [.495,.3,.126]:
        tag=f'{x:.3f}'
        commands.append(['--L','10','--x',str(x),'--nz','32','--osc','256','--output',f'results/refine_L10_z32_x{tag}.json'])
    for x in [.495,.4,.25,.15,.126]:
        tag=f'{x:.3f}';teacher=ROOT/f'results/teacher_L6_x{tag}.json'
        # Training output must already be accepted; the driver does not regenerate it silently.
        commands.append(['--L','12','--x',str(x),'--nz','16','--basis',str(teacher),'--output',f'results/window_L12_z16_x{tag}.json'])
    for x in [.25,.126]:
        tag=f'{x:.3f}';teacher=ROOT/f'results/teacher_L6_x{tag}.json'
        commands.append(['--L','12','--x',str(x),'--nz','20','--basis',str(teacher),'--output',f'results/window_L12_z20_x{tag}.json'])
    # Independent moving-basis larger reference at strong coupling and largest bath cut.
    commands.append(['--L','12','--x','.126','--nz','32','--osc','256','--output','results/refine_L12_z32_x0.126.json'])
    rows=[];logs=ROOT/'validation/refine_logs';logs.mkdir(exist_ok=True)
    for i,args in enumerate(commands):
        target=ROOT/args[args.index('--output')+1]
        if target.exists():continue
        if '--basis' in args:
            needed=Path(args[args.index('--basis')+1])
            while not needed.exists():time.sleep(2)
        print('REFINE',i,' '.join(args),flush=True);t=time.perf_counter()
        try:
            c=subprocess.run([sys.executable,'code/run.py',*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=400)
            (logs/f'job{i}.txt').write_text(c.stdout+'\n'+c.stderr);success=c.returncode==0 and target.exists();error=None if success else f'exit {c.returncode}'
        except subprocess.TimeoutExpired:
            success=False;error='timeout: no accepted complete result'
        rows.append({'arguments':args,'accepted':success,'seconds':time.perf_counter()-t,'error':error});atomic_json(ROOT/'validation/refinements.json',rows)
        print('DONE REFINE',i,success,round(rows[-1]['seconds'],2),flush=True)
if __name__=='__main__':main()
