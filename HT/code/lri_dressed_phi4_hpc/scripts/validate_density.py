#!/usr/bin/env python3
"""Real CLI training, restart, held-out-cutoff solve and original-solver checks.

Default: small weak/strong points suitable for a staged cluster receipt.
--extended additionally repeats the two main larger-local pilot comparisons.
No thermal value controls training; the teacher thermal gap is evaluated only
as an independent validation after each basis artifact has been published.
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,read_envelope,validate_result,source_fingerprint,runtime
from lri_dressed.local_basis import load_basis


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--workdir',required=True)
    p.add_argument('--threads',type=int,default=1);p.add_argument('--extended',action='store_true')
    a=p.parse_args();base=Path(a.workdir).resolve()/('run_'+uuid.uuid4().hex[:12]);base.mkdir(parents=True)
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS=str(max(4,a.threads)))
    logs=[];records=[];start=time.perf_counter()
    def call(args):
        proc=subprocess.run([sys.executable,'-m','lri_dressed',*args],env=env,cwd=ROOT,capture_output=True,text=True)
        logs.append({'arguments':args,'returncode':proc.returncode,'stdout':proc.stdout[-6000:],'stderr':proc.stderr[-6000:]})
        if proc.returncode:raise RuntimeError(proc.stderr[-4000:])
        return proc
    specs=[(.24,4,6,16,12,128,[10,12]),(.025,8,10,32,24,256,[16,24])]
    if a.extended:specs += [(.01,12,12,48,24,384,[16,24]),(.025,16,20,48,24,384,[16,24])]
    try:
        for index,(x,train_l,test_l,teacher,keep,osc,ks) in enumerate(specs):
            out=base/f'case{index}';out.mkdir();basis=out/'basis.json'
            seed=ROOT/'inputs'/f'N16_z24_o192_d{x:.8f}.json'
            args=['train-basis','--bath-cut',str(train_l),'--delta',repr(x),'--teacher-nz',str(teacher),'--keep',str(keep),
                  '--osc',str(osc),'--threads',str(a.threads),'--backend','ladder','--seed',str(seed),
                  '--output',str(basis),'--tuning-tol','5e-11','--maxiter','40','--ncv','36']
            call(args);b=load_basis(basis);blob=basis.read_bytes();call(args+['--resume'])
            if basis.read_bytes()!=blob:raise RuntimeError('Basis resume rewrote the immutable artifact')
            refs={}
            for k in [teacher,*ks]:
                args=['run','--bath-cut',str(test_l),'--deltas',repr(x),'--nz',str(k),'--osc',str(osc),
                      '--window','vacuum','--backend','ladder','--threads',str(a.threads),'--tuning-tol','5e-11',
                      '--ncv','36','--maxiter','40','--output-dir',str(out/f'k{k}'),
                      '--guess',*map(repr,b['payload']['theta'])]
                if k!=teacher:args+=['--local-basis',str(basis),'--local-basis-sha256',b['sha256']]
                proc=call(args)
                path=Path(json.loads(proc.stdout.splitlines()[-1])['path'])
                rec=read_envelope(path,'result');validate_result(rec['payload'],rec['config']);refs[k]=rec['payload']
                call(args+['--resume'])
            comparisons=[]
            for k in ks:
                delta=refs[k]['Delta_thermal']-refs[teacher]['Delta_thermal']
                gap=max(abs(u-v) for name in ('even_gaps','odd_gaps') for u,v in zip(refs[k][name],refs[teacher][name]))
                comparisons.append({'keep':k,'thermal_difference':delta,'max_five_level_difference':gap})
                # Local-space validation budget, not a physical error bar.
                if abs(delta)>1e-7 or gap>2e-6:raise RuntimeError(f'Local-space regression gate: {comparisons[-1]}')
            records.append({'delta':x,'training_cutoff':train_l,'test_cutoff':test_l,'teacher_nz':teacher,
                'osc':osc,'basis_path':str(basis),'basis_sha256':b['sha256'],'gates':b['payload']['gates'],
                'solutions':{str(k):v for k,v in refs.items()},'comparisons':comparisons})
            print(json.dumps({k:records[-1][k] for k in ('delta','training_cutoff','test_cutoff','comparisons')}),flush=True)
        passed=True;error=None
    except Exception as exc:
        passed=False;error=f'{type(exc).__name__}: {exc}'
    atomic_json(a.output,{'passed':passed,'error':error,'source_sha256':source_fingerprint(),'runtime':runtime(),
                         'host':os.uname().nodename,'seconds':time.perf_counter()-start,'workdir':str(base),
                         'records':records,'commands':logs,'scope':'Fresh local/integration checks against finite references, not continuum precision.'})
    if error:print(error,file=sys.stderr)
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
