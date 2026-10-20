#!/usr/bin/env python3
"""Direct d=3 spherical dressed-zero-mode HT. Finite regulator, not a continuum fit."""
from __future__ import annotations
import argparse,json,os,time,hashlib,platform,signal
from pathlib import Path
import numpy as np
from d3dressed.solver import DressedSolver

def atomic(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False));os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--bath-cut',type=int,default=6);p.add_argument('--nz',type=int,default=16);p.add_argument('--osc',type=int,default=128)
    p.add_argument('--deltas',type=float,nargs='+',default=[.7499,.749,.745,.74,.725,.7,.675,.65,.625,.6,.575,.55,.535,.525,.52,.5182])
    p.add_argument('--output-dir',type=Path,default=Path('results/scan'));p.add_argument('--seed-dir',type=Path);p.add_argument('--resume',action='store_true')
    p.add_argument('--point-timeout',type=int,default=240);p.add_argument('--eig-tol',type=float,default=1e-12);p.add_argument('--root-tol',type=float,default=1e-10)
    args=p.parse_args();s=DressedSolver(args.bath_cut,args.nz,args.osc,backend='tensor',eig_tol=args.eig_tol,ncv=40,max_eig_iter=3000)
    source=hashlib.sha256(b''.join(f.read_bytes() for f in sorted((Path(__file__).parent/'d3dressed').glob('*.py')))).hexdigest()
    guess=None
    def timeout(signum,frame):raise TimeoutError('Per-point wall limit')
    signal.signal(signal.SIGALRM,timeout)
    for x in args.deltas:
        if not .518148806<x<.75:raise ValueError('Scan only the interacting 3d LR interval, reference lower bound 0.518148806')
        path=args.output_dir/f'L{args.bath_cut}_z{args.nz}_o{args.osc}_x{x:.8f}.json'
        if args.resume and path.exists():
            r=json.loads(path.read_text())
            if r.get('source_fingerprint')!=source:raise ValueError('Source mismatch in resume')
            if (r['bath_cut'],r['nz_per_parity'],r['auxiliary_oscillator_size'])!=(args.bath_cut,args.nz,args.osc):raise ValueError('Resume cutoff mismatch')
            if r['tuning_residual']>1e-8 or r['max_eigenvector_residual']>2e-7:raise ValueError('Resume gates failed')
            guess=r['theta'];print('resume',path.name,flush=True);continue
        start=time.perf_counter();s.set_delta(x)
        if args.seed_dir:
            candidates=[]
            for f in args.seed_dir.rglob(f'*x{x:.8f}.json'):
                if f.name.startswith('FAILED_'):continue
                try:
                    r=json.loads(f.read_text())
                    if r.get('spacetime_dimension')==3 and 'theta' in r:candidates.append(r)
                except (OSError,ValueError):pass
            if candidates:guess=max(candidates,key=lambda z:(z['bath_cut'],z['nz_per_parity']))['theta']
        if 3-4*x<.04:guess=None
        try:
            signal.alarm(args.point_timeout)
            r=s.solve(guess=guess,tol=args.root_tol,maxiter=45);signal.alarm(0)
            r['point_seconds_including_operators']=time.perf_counter()-start;r['source_fingerprint']=source;r['python']=platform.python_version()
            r['sphere_quadrature_nodes']=s.op.nodes;r['angular_hermiticity_residual']=s.op.hermiticity_residual
            atomic(path,r);guess=r['theta']
            print(f"L={args.bath_cut} z={args.nz} x={x:.8f} D={r['Delta_thermal']:.12f} g={r['g']:.5g} dim={r['dimension']} t={r['point_seconds_including_operators']:.2f}",flush=True)
        except Exception as e:
            signal.alarm(0);atomic(path.with_name('FAILED_'+path.name),{'x':x,'exception':repr(e),'scope':'Failed, not accepted curve data'})
            print('FAILED',x,repr(e),flush=True);guess=None
if __name__=='__main__':main()
