#!/usr/bin/env python3
"""Freeze a small per-delta training campaign; numerical seeds are copied as theta.

No cluster submission occurs here. Artifacts are trained separately from runs.
"""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,claim,digest,source_fingerprint,release_fingerprint,runtime
from lri_dressed.cli import seed_theta
from lri_dressed.basis_training import train_configuration
from lri_dressed.planning import plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deltas',type=float,nargs='+',required=True)
    p.add_argument('--bath-cut',type=int,default=16);p.add_argument('--teacher-nz',type=int,default=48)
    p.add_argument('--keep',type=int,default=24);p.add_argument('--osc',type=int,default=384)
    p.add_argument('--backend',choices=['auto','tensor','ladder'],default='ladder')
    p.add_argument('--threads',type=int,default=1);p.add_argument('--memory-limit-gib',type=float,default=8.)
    p.add_argument('--seed-dir',default=str(ROOT/'inputs'))
    p.add_argument('--basis-dir',required=True);p.add_argument('--out',required=True)
    p.add_argument('--max-sweeps',type=int,default=6);p.add_argument('--basis-tol',type=float,default=2e-8)
    p.add_argument('--teacher-tol',type=float,default=1e-7);p.add_argument('--eig-tol',type=float,default=3e-11)
    p.add_argument('--residual-tol',type=float,default=2e-7);p.add_argument('--tuning-tol',type=float,default=5e-10)
    p.add_argument('--ncv',type=int,default=36);p.add_argument('--maxiter',type=int,default=40)
    p.add_argument('--max-eig-iter',type=int,default=10000);p.add_argument('--window-tol',type=float,default=1e-12)
    p.add_argument('--window-maxiter',type=int,default=50)
    a=p.parse_args();jobs=[];dest=Path(a.basis_dir).resolve()
    for d in sorted(set(a.deltas),reverse=True):
        a.delta=d;cfg=train_configuration(a)
        candidates=[]
        for pp in Path(a.seed_dir).glob('*.json'):
            try:
                theta=seed_theta(pp,d);raw=json.loads(pp.read_text());row=raw.get('payload',raw)
                candidates.append((abs(row.get('bath_cut',-100)-a.bath_cut),-row.get('nz_per_parity',0),str(pp.resolve()),theta))
            except (ValueError,TypeError,KeyError,OSError):continue
        if not candidates:
            raise ValueError(f'No accepted exact-delta seed for {d}; add a scalar seed before freezing the request')
        _,_,seed,theta=min(candidates)
        cfg['initial_theta']=list(map(float,theta))
        teacher_plan=plan(a.bath_cut,a.teacher_nz,a.osc,a.backend,a.ncv,'vacuum')
        small_plan=plan(a.bath_cut,a.keep,a.osc,a.backend,a.ncv,'vacuum')
        mem=(teacher_plan['memory_envelope_bytes']+small_plan['memory_envelope_bytes']+8*a.osc*a.osc*4)/2**30
        if a.memory_limit_gib<mem:raise ValueError(f'Training memory limit {a.memory_limit_gib} below envelope {mem:g} GiB')
        name=f'x{d:.12g}_L{a.bath_cut}_teacher{a.teacher_nz}_keep{a.keep}_o{a.osc}_{digest(cfg)[:12]}.json'
        jobs.append({'config':cfg,'threads':a.threads,'memory_limit_gib':a.memory_limit_gib,
            'plan_envelope_gib':mem,'output':str(dest/name),'seed_provenance':{'path':seed,'sha256':hashlib.sha256(Path(seed).read_bytes()).hexdigest()}})
    row={'schema':'lri-dressed-basis-training-v1','source_sha256':source_fingerprint(),
         'release_sha256':release_fingerprint(),'runtime':runtime(),'jobs':jobs}
    row['sha256']=digest(row);out=Path(a.out).resolve()
    with claim(out.with_name(out.name+'.lock')):
        if out.exists():raise FileExistsError('Training request exists: use a new versioned path')
        atomic_json(out,row)
    print(f'{len(jobs)} training jobs, array 0-{len(jobs)-1}; target basis directory {dest}')
if __name__=='__main__':main()
