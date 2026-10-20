#!/usr/bin/env python3
"""Direct 2D fixed-x HT. Raw/consistent-window and fixed optimized basis.
One process/writer per output. Not the symmetry HPC dispatcher.
"""
from pathlib import Path
import argparse,hashlib,json,os,time,platform
import numpy as np
from ht2d.solver import DressedSolver
from ht2d.density import DensitySolver,select_density_basis
from diagnostics import diagnose
ROOT=Path(__file__).resolve().parents[1]


def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)


def nearest_seed(x,L):
    rows=json.loads((ROOT/'inputs/prior_2d_points.json').read_text())
    close=[r for r in rows if abs(r['delta']-x)<1e-10]
    return min(close,key=lambda r:abs(r['bath_cut']-L))['theta'] if close else None


def fingerprint():
    h=hashlib.sha256()
    for p in sorted((ROOT/'code').rglob('*.py')):
        h.update(str(p.relative_to(ROOT)).encode());h.update(p.read_bytes())
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--L',type=int,default=6);p.add_argument('--x',type=float,required=True)
    p.add_argument('--nz',type=int,default=24);p.add_argument('--osc',type=int,default=192)
    p.add_argument('--window',choices=['none','vacuum'],default='vacuum');p.add_argument('--backend',choices=['tensor','ladder'],default='tensor')
    p.add_argument('--train-keep',type=int,default=0);p.add_argument('--basis',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=Path)
    p.add_argument('--no-diagnostics',action='store_true');p.add_argument('--first-only',action='store_true')
    p.add_argument('--eig-tol',type=float,default=1e-12);p.add_argument('--tuning-tol',type=float,default=3e-11)
    p.add_argument('--ncv',type=int,default=40);p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    if not .125<a.x<.5:raise ValueError('The interacting scan requires 1/8<x<1/2')
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items() if k not in ('resume','output')}
    source=fingerprint()
    if a.resume and a.output.exists():
        rec=json.loads(a.output.read_text())
        if rec.get('source_hash')==source and rec.get('requested')==config and rec.get('accepted'):
            print('REUSE',a.output,flush=True);return
        raise ValueError('Refusing mismatched resume output')
    start=time.perf_counter();basis_record=None
    kw=dict(window=a.window,backend=a.backend,eig_tol=a.eig_tol,residual_tol=1e-8,ncv=a.ncv,max_eig_iter=10000)
    if a.basis:
        data=json.loads(a.basis.read_text());basis_record=data['basis_artifact']
        if basis_record['x']!=a.x:raise ValueError('Basis cannot transfer across x')
        uz=np.array(basis_record['isometry']);k=uz.shape[1]//2
        if a.nz>k:raise ValueError('Requested nz exceeds trained capacity')
        uz=uz[:,list(range(a.nz))+list(range(k,k+a.nz))]
        solver=DensitySolver(a.L,uz,basis_record['scale'],**kw)
        seed=data['theta']
    else:
        solver=DressedSolver(a.L,a.nz,a.osc,**kw);seed=nearest_seed(a.x,a.L)
    if a.seed:seed=json.loads(a.seed.read_text())['theta']
    solver.set_delta(a.x)
    row=solver.solve(seed,tol=a.tuning_tol,maxiter=50)
    row.update(requested=config,source_hash=source,accepted=False,implementation='2d window-density research port 0.1.0',python=platform.python_version())
    if a.train_keep:
        u,t,meta=select_density_basis(solver,row['theta'],a.train_keep)
        row['basis_artifact']={'x':a.x,'training_L':a.L,'nz_teacher':a.nz,'osc':a.osc,'keep':a.train_keep,
                               'scale':t,'isometry':u.tolist(),'metadata':meta,
                               'source_hash':source,'window':a.window}
    if basis_record:row['basis_provenance']={'file':str(a.basis),'sha256':hashlib.sha256(a.basis.read_bytes()).hexdigest(),
                                          'training_L':basis_record['training_L'],'keep':a.nz,'x':a.x}
    if not a.no_diagnostics:row['diagnostics']=diagnose(solver,row['theta'],k=6,second=not a.first_only)
    row['accepted']=True;row['elapsed_total_seconds']=time.perf_counter()-start
    atomic_json(a.output,row)
    print(json.dumps({k:row[k] for k in ['delta','bath_cut','nz_per_parity','window','Delta_thermal','tuning_residual','elapsed_total_seconds']}),flush=True)
    if 'diagnostics' in row:
        print([(r['family'],r['branch'],round(r['spacing_error'],9),round(r['overlap_probability'],5)) for r in row['diagnostics']['records']],flush=True)

if __name__=='__main__':main()
