"""On-node validation of a staged release; writes the campaign receipt (G1, G2).

Usage (inside validate.sbatch): python -E -s validate.py --tar T --manifest M --workdir W --receipt R --threads N
passed=true requires: full pytest suite green, reference replays within 1e-9, and the
system interpreter used by chain.sbatch for spec parsing present.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,socket,subprocess,sys,time
from pathlib import Path
from common import RELEASE,atomic_json,source_hash
import envcheck

REPLAY=[(x,L) for x in ('0.126','0.250','0.495') for L in (8,10)]+[('0.350',8)]   # x=0.35 L=8 exercises the HF-01 fallback
TOL=1e-9


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd,env=None,cwd=None):
    t=time.time();p=subprocess.run(cmd,env=env,cwd=cwd,capture_output=True,text=True)
    return p.returncode,p.stdout[-6000:],p.stderr[-6000:],time.time()-t


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('--tar','--manifest','--workdir','--receipt'):ap.add_argument(k,required=True)
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--tar-path',help='original (home) path of the release tar, recorded for reference only')
    a=ap.parse_args(argv);work=Path(a.workdir);work.mkdir(parents=True,exist_ok=True)
    py=sys.executable;checks={};ok=True
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OMP_NUM_THREADS':'1','NUMBA_NUM_THREADS':'4'}
    rc,out,err,dt=run([py,'-E','-s','-m','pytest','-q','-p','no:cacheprovider','tests'],env=env,cwd=RELEASE)
    checks['pytest']={'rc':rc,'seconds':dt,'tail':out.strip().splitlines()[-3:] if out else err[-500:]}
    ok&=rc==0
    rc2,_,_,_=run(['/usr/bin/python3','-I','-c','import json,sys;print(sys.version)'])
    checks['system_python3']={'rc':rc2};ok&=rc2==0
    env['NUMBA_NUM_THREADS']=str(a.threads);replays=[]
    for x,L in REPLAY:
        ref=RELEASE/f'reference/results/window_L{L}_z16_x{x}.json';teacher=RELEASE/f'reference/results/teacher_L6_x{x}.json'
        out_=work/f'replay_L{L}_x{x}.json'
        rc,o,e,dt=run([py,'-E','-s',str(RELEASE/'code/hpc_run.py'),'--L',str(L),'--x',str(float(x)),'--nz','16','--backend','tensor',
                       '--threads',str(a.threads),'--window','vacuum','--window-mode','consistent','--basis',str(teacher),
                       '--seed',str(ref),'--diagnostics','all','--memory-limit-gib','8','--output',str(out_),'--resume'],env=env)
        item={'x':x,'L':L,'rc':rc,'seconds':dt}
        if rc==0:
            r=json.loads(out_.read_text());R=json.loads(ref.read_text())
            d=[abs(r['Delta_thermal']-R['Delta_thermal'])]+[abs(u-v) for u,v in zip(r['even_gaps'][:5]+r['odd_gaps'][:5],R['even_gaps'][:5]+R['odd_gaps'][:5])]
            item.update(max_abs_difference=max(d),thermal_difference=d[0],passed=max(d)<=TOL)
        else:item.update(passed=False,stderr=e[-800:])
        ok&=item['passed'];replays.append(item)
    checks['replay']=replays
    ident=envcheck.identity()
    # Hashes come from the SNAPSHOT files that were extracted and tested (IR3-01).
    receipt={'passed':bool(ok),'tar':a.tar_path or str(Path(a.tar).resolve()),'tar_sha256':sha(a.tar),'manifest_sha256':sha(a.manifest),
             'source_sha256':source_hash(),'env_id':ident['env_id'],'env_packages':ident['packages'],'python':platform.python_version(),
             'node':socket.gethostname(),'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'cpu':platform.processor() or platform.machine(),
             'checks':checks,'tolerance':TOL,'unix':time.time()}
    atomic_json(a.receipt,receipt)
    print(json.dumps({'passed':receipt['passed'],'receipt':a.receipt,'env_id':ident['env_id'],
                      'replay_max':max((r.get('max_abs_difference',1) for r in replays),default=None)}))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
