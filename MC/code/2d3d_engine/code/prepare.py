#!/usr/bin/env python3
"""Prepare immutable, relocatable 2d/3d long-range Ising cluster campaigns.

Supply provisional beta centers in a CSV with columns d,s,L,beta. An empty L
applies to all lengths. Centers are NOT assumed critical temperatures.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,uuid
from pathlib import Path
import numpy as np
from kernel import save_kernel
SR_SIGMA={2:.125,3:.518148806}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--dim',type=int,choices=[2,3],required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--delta-sigma',type=float,nargs='+');g.add_argument('--s',type=float,nargs='+')
    p.add_argument('--sizes',type=int,nargs='+',required=True);p.add_argument('--centers',type=Path,required=True)
    p.add_argument('--replicas',type=int,default=8);p.add_argument('--measurements',type=int,default=1000000)
    p.add_argument('--warmup',type=int,default=50000);p.add_argument('--beta-points',type=int,default=3)
    p.add_argument('--beta-halfwidth',type=float,default=.001);p.add_argument('--window-exponent',type=float,default=0)
    p.add_argument('--reference-length',type=float,default=32);p.add_argument('--seed-base',type=int,default=20260915)
    p.add_argument('--campaign-id',help='stable namespace; default new UUID, copied unchanged to other clusters')
    p.add_argument('--sampler',choices=['hybrid','lattice','flat','core'],default='hybrid')
    p.add_argument('--rng',choices=['xoshiro','mt'],default='xoshiro')
    p.add_argument('--record',choices=['basic','extended'],default='extended')
    p.add_argument('--core-radius',type=int,default=16);p.add_argument('--near-radius',type=int,default=1)
    p.add_argument('--nn-extra',type=float,default=0)
    p.add_argument('--ewald-cut',type=int,choices=[3,4,5],default=4);p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();d=a.dim
    campaign_id=a.campaign_id or uuid.uuid4().hex
    if not 1<=a.near_radius<a.core_radius<=32 or a.core_radius&(a.core_radius-1):p.error('need 1<=near-radius<core-radius<=32 and power-of-two core-radius')
    if a.nn_extra<0 or not np.isfinite(a.nn_extra):p.error('nn-extra must be finite and nonnegative')
    ss=sorted(set(a.s if a.s is not None else [d-2*x for x in a.delta_sigma]))
    if any(not d/2<s<d-2*SR_SIGMA[d] for s in ss):p.error('use interior LRI points; exact endpoints require marginal/logarithmic treatment')
    if any(L<2 or L&(L-1) or L**d>2**28 for L in a.sizes):p.error('L must be a power of two; N=L^d <= 2^28')
    if min(a.measurements,a.replicas,a.beta_points)<1 or a.warmup<0:p.error('invalid counts')
    if a.beta_points%2!=1:p.error('an odd number of temperatures identifies a unique central histogram')
    if a.beta_halfwidth<0 or not np.isfinite(a.beta_halfwidth):p.error('invalid beta width')
    if a.beta_points>1 and a.beta_halfwidth<=0:p.error('multiple temperatures require a positive width')
    centers={}
    for r in csv.DictReader(a.centers.open()):
        if int(r['d'])!=d:continue
        centers[(float(r['s']),int(r['L']) if r.get('L','').strip() else None)]=float(r['beta'])
    def center(s,L):
        opts=[(sl,b) for (ss,sl),b in centers.items() if abs(ss-s)<1e-11 and sl in (None,L)]
        if not opts:raise ValueError(f'no center for d={d},s={s},L={L}')
        return next((b for l,b in opts if l==L),opts[0][1])
    tasks=[]
    for s in ss:
      for L in sorted(set(a.sizes)):
        bc=center(s,L);width=a.beta_halfwidth*(L/a.reference_length)**(-a.window_exponent)
        betas=bc+np.linspace(-width,width,a.beta_points) if a.beta_points>1 else [bc]
        for ib,beta in enumerate(betas):
          if not np.isfinite(beta) or beta<=0:p.error('invalid temperature bracket')
          for rep in range(a.replicas):
            key=f'{campaign_id}|{float(a.nn_extra).hex()}|{a.seed_base}|{d}|{s.hex()}|{L}|{float(beta).hex()}|{rep}'
            seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'little')
            tid=len(tasks)
            tasks.append(dict(id=tid,campaign_id=campaign_id,sampler=a.sampler,rng=a.rng,record=a.record,core_radius=a.core_radius,near_radius=a.near_radius,nn_extra=a.nn_extra,d=d,L=L,N=L**d,s=s,Delta_sigma=(d-s)/2,beta=float(beta),
                beta_index=ib,central_temperature=ib==a.beta_points//2,replica=rep,seed=seed,
                initialization='hot' if rep%2==0 else 'cold',measurements=a.measurements,warmup=a.warmup,
                directory=f'chains/{tid:06d}',couplings=f'kernels/d{d}_s{s:.10g}_L{L}.bin'))
    plan=dict(tasks=len(tasks),measurement_sweeps=sum(t['measurements'] for t in tasks),
        raw_GB=(64 if a.record=='extended' else 32)*sum(t['measurements'] for t in tasks)/1e9,
        spin_sweeps=sum(t['N']*(t['measurements']+t['warmup']) for t in tasks),
        max_spins=max(t['N'] for t in tasks),estimated_checkpoint_peak_MiB=(10*max(t['N'] for t in tasks)+16e6)/2**20,campaign_id=campaign_id,runtime_note='Benchmark actual compute node; one serial chain per core.')
    print(json.dumps(plan,indent=2))
    if a.dry_run:return
    if a.out.exists():p.error('output already exists; use a new campaign or resume with run_task.py')
    a.out.mkdir(parents=True);(a.out/'logs').mkdir()
    kernels={}
    for t in tasks:
        f=a.out/t['couplings']
        if a.sampler in ('flat','core') and t['couplings'] not in kernels:
            save_kernel(f,d,t['L'],t['s'],a.ewald_cut)
            kernels[t['couplings']]=hashlib.sha256(f.read_bytes()).hexdigest()
        t['coupling_sha256']=kernels.get(t['couplings'])
        dr=a.out/t['directory'];dr.mkdir(parents=True);(dr/'task.json').write_text(json.dumps(t,indent=2)+'\n')
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()}
    (a.out/'manifest.json').write_text(json.dumps(dict(format=5,campaign_id=campaign_id,model='Euclidean full-periodized classical LRI',config=config,tasks=tasks),indent=2)+'\n')
    (a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
if __name__=='__main__':main()
