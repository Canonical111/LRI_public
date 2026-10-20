#!/usr/bin/env python3
"""Engine integration checks: run_task builds the right command for both engines; a tiny '1d' campaign prepared by prepare.py
runs to completion through run_task.py, passes completion_check-style record checks (format 5, engine tag, 4 columns, N/beta/seed),
resumes bitwise after an interruption, and analyze.py reads it; a 'v1' campaign prepared the same way still works."""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import run_task

def prepare(out, engine, N=1024, s=.65, beta=.31, meas=3000, reps=2, betas=2):
    c=out.parent/f'centres_{engine}.csv'; c.write_text(f's,N,beta\n{s},,{beta}\n')
    cmd=[sys.executable,str(ROOT/'prepare.py'),'--out',str(out),'--s',str(s),'--sizes',str(N),'--replicas',str(reps),'--measurements',str(meas),
         '--warmup','200','--beta-points',str(betas),'--beta-halfwidth','0.002','--window-exponent','0','--centers',str(c),'--seed-base','777','--seed-namespace',f'test_{engine}','--engine',engine]
    r=subprocess.run(cmd,capture_output=True,text=True); assert r.returncode==0, r.stderr
    return json.loads((out/'manifest.json').read_text())

def main():
    report={}
    with tempfile.TemporaryDirectory(prefix='lri-engine-') as tmp:
        tmp=Path(tmp)
        m1=prepare(tmp/'c1d','1d'); mv=prepare(tmp/'cv1','v1')
        assert m1['engine']=='1d' and all(t['engine']=='1d' for t in m1['tasks']) and mv['engine']=='v1'
        cmd1=run_task.command(tmp/'c1d',0); cmdv=run_task.command(tmp/'cv1',0)
        assert cmd1[0].endswith('bin/lri_mc_1d') and '--sampler' in cmd1 and cmd1[cmd1.index('--sampler')+1]=='backbone' and cmd1[cmd1.index('--record')+1]=='basic' and cmd1[cmd1.index('--length')+1]=='1024'
        assert cmdv[0].endswith('bin/lri_mc') and '--n' in cmdv and '--couplings' in cmdv and '--sampler' not in cmdv
        # run all four 1d chains; then check the records the way completion_check does
        for t in m1['tasks']:
            r=subprocess.run(run_task.command(tmp/'c1d',t['id']),capture_output=True,text=True); assert r.returncode==0, r.stderr[-300:]
            d=tmp/'c1d'/t['directory']; st=json.loads((d/'DONE.json').read_text())
            assert st['format']==5 and st['engine']=='1d' and st['record_columns']==4 and st['N']==t['N'] and abs(st['beta']-t['beta'])<1e-15 and st['seed']==t['seed']
            assert st['measurements_done']==st['measurements_target']==t['measurements'] and (d/'samples.bin').stat().st_size==32*t['measurements']
            assert (d/'binary.sha256').exists()
        # resume: a fresh copy of task 0 interrupted by --max-seconds then completed must equal the uninterrupted trajectory
        t=m1['tasks'][0]; src=tmp/'c1d'/t['directory']
        alt=tmp/'c1d'/'chains/alt0'; alt.mkdir()
        cmd=run_task.command(tmp/'c1d',0); cmd[cmd.index('--out')+1]=str(alt); cmd[cmd.index('--checkpoint-seconds')+1]='0.05'; cmd[cmd.index('--max-seconds')+1]='0.15'
        r=subprocess.run(cmd,capture_output=True,text=True); assert r.returncode in (0,75)
        cmd[cmd.index('--max-seconds')+1]='0'; r=subprocess.run(cmd,capture_output=True,text=True); assert r.returncode==0, r.stderr[-300:]
        assert (alt/'samples.bin').read_bytes()==(src/'samples.bin').read_bytes(), 'resumed 1d trajectory differs'
        report['resume_bitwise']=True
        # analyze reads the campaign (two temperatures x two replicas) and returns six finite observables per temperature
        r=subprocess.run([sys.executable,str(ROOT/'analyze.py'),str(tmp/'c1d'),'--block','100','--out',str(tmp/'an1d'),'--no-tau'],capture_output=True,text=True); assert r.returncode==0, r.stderr[-400:]
        S=json.loads((tmp/'an1d'/'summary.json').read_text()); assert len(S['entries'])==2 and all(np.all(np.isfinite(e['data'])) and len(e['data'])==6 for e in S['entries'])
        report['analyze_reads_1d']=True
        # v1 still runs and analyzes
        r=subprocess.run(run_task.command(tmp/'cv1',0),capture_output=True,text=True); assert r.returncode==0, r.stderr[-300:]
        st=json.loads((tmp/'cv1'/mv['tasks'][0]['directory']/'DONE.json').read_text()); assert st['format']==2 and 'engine' not in st
        report['v1_unchanged']=True
    (ROOT/'tests/engine_1d_test_results.json').write_text(json.dumps(report,indent=1)+'\n'); print('engine integration checks passed',report)
if __name__=='__main__':main()
