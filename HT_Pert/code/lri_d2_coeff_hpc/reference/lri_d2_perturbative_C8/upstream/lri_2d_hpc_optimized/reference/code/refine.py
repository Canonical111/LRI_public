#!/usr/bin/env python3
"""Recompute declared independent refinements and the separately labelled alternate root."""
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
    for x in [.495,.4,.25]:
        tag=f'{x:.3f}'
        commands.append(['--L','12','--x',str(x),'--nz','16','--basis',f'results/teacher_L6_x{tag}.json','--output',f'results/window_L12_z16_x{tag}.json'])
    commands.append(['--L','12','--x','.15','--nz','16','--basis','results/teacher_L6_x0.150.json','--output','results/alternate_L12_x0.150.json'])
    for x in [.15,.126]:
        tag=f'{x:.3f}'
        commands.append(['--L','12','--x',str(x),'--nz','16','--basis',f'results/teacher_L6_x{tag}.json','--seed',f'results/window_L10_z16_x{tag}.json','--first-only','--output',f'results/window_L12_z16_x{tag}.json'])
    for x in [.25,.126]:
        tag=f'{x:.3f}'
        commands.append(['--L','12','--x',str(x),'--nz','20','--basis',f'results/teacher_L6_x{tag}.json','--seed',f'results/window_L12_z16_x{tag}.json','--no-diagnostics','--output',f'results/window_L12_z20_x{tag}.json'])
    commands.append(['--L','12','--x','.126','--nz','32','--osc','256','--seed','results/window_L12_z16_x0.126.json','--no-diagnostics','--output','results/refine_L12_z32_x0.126.json'])
    rows=[];logs=ROOT/'validation/refinement_reproduction_logs';logs.mkdir(exist_ok=True)
    for i,args in enumerate(commands):
        target=ROOT/args[args.index('--output')+1]
        if target.exists():continue
        for flag in ['--basis','--seed']:
            if flag in args and not (ROOT/args[args.index(flag)+1]).exists():
                raise FileNotFoundError(f'Required {flag} artifact missing; run the main campaign first')
        print('REFINE',i,' '.join(args),flush=True);t=time.perf_counter()
        try:
            c=subprocess.run([sys.executable,'code/run.py',*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=500)
            (logs/f'job{i}.txt').write_text(c.stdout+'\n'+c.stderr);success=c.returncode==0 and target.exists();error=None if success else f'exit {c.returncode}'
        except subprocess.TimeoutExpired:
            success=False;error='timeout: no accepted complete result'
        rows.append({'arguments':args,'accepted':success,'seconds':time.perf_counter()-t,'error':error});atomic_json(ROOT/'validation/refinement_reproduction.json',rows)
        print('DONE REFINE',i,success,round(rows[-1]['seconds'],2),flush=True)
if __name__=='__main__':main()
