#!/usr/bin/env python3
"""Direct coefficient extraction for the frozen-cutoff phi^4 Hamiltonian.

No finite-epsilon sampling and no fits in epsilon.  Eighth order requires a
fourth-order trial wavefunction. The optional vacuum_only Hamiltonian includes
only g(eps)^2 D(eps), NOT the complete connected vacuum matching.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, resource, sys, time
from pathlib import Path
import numpy as np
from lri_hpc.operators import Space, quotient_components
from lri_hpc.kernels import solve_wave
from lri_hpc.solver import (seed, sparse_reference, extract, vacuum_table,
                           vacuum_quotient, second_order_shell_value, atomic_json)

VERSION='C8-direct-1.3'

def fingerprint():
    h=hashlib.sha256()
    for p in sorted([Path(__file__)]+list((Path(__file__).parent/'lri_hpc').glob('*.py'))):
        h.update(str(p.relative_to(Path(__file__).parent)).encode());h.update(p.read_bytes())
    return h.hexdigest()

class Vacuum:
    def __init__(self,space,degree):
        self.space=space
        self.sums=vacuum_table(space.cutoff,degree)
        self.upper=np.maximum(0,(4*space.cutoff-4*space.N-space.P)//4)
    def diag(self,k):
        return -(self.sums[self.space.cutoff,k]-self.sums[self.upper,k])/6
    def action_coeff(self,psi,k,g):
        """[eps^k] g(eps)^2 D(eps) psi(eps)."""
        out=np.zeros(self.space.dim)
        gg=np.convolve(g,g)
        for j in range(2,min(k,len(gg)-1)+1):
            if gg[j]==0:continue
            for l in range(k-j+1):
                i=k-j-l
                if i<psi.shape[1]:out+=gg[j]*self.diag(l)*psi[:,i]
        return out


def calibrate(space,order,vac=None):
    refs=(0,1,3)
    psi={p:seed(space,p,order) for p in refs}
    E={p:np.r_[p/4,np.zeros(order)] for p in refs}
    r=np.zeros(order+1);g=np.zeros(order+1);refverts={}
    for k in range(1,order+1):
        rhs={};raw={}
        for p in refs:
            m,v=space.vertices(psi[p][:,:k],k-1,parity=p%2)
            if k==1:refverts[p]=sparse_reference(m,v)
            t=space.F1*psi[p][:,k-1]
            for j in range(1,k):t+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
            if vac is not None:t+=vac.action_coeff(psi[p][:,:k],k,g)
            rhs[p]=t;raw[p]=space.sample(t,p)
            del m,v
        r[k]=((-.25 if k==1 else 0.)-(raw[1]-raw[0]))/2
        g[k]=((.25 if k==1 else 0.)-(raw[3]-raw[0])-6*r[k])/3
        for p in refs:
            t=rhs.pop(p);idx,mv,vv=refverts[p]
            t[idx]+=r[k]*mv+g[k]*vv
            E[p][k]=space.sample(t,p)
            solve_wave(t,psi[p],E[p],k,p,space.P,space.N)
    return psi,E,r,g


def calibrate_streamed(space,order,vac=None):
    # Do not retain the last wavefunction coefficient for all three calibration
    # references at once. Energies at order k require wavefunctions only to k-1.
    psi,E0,rs,gs=calibrate(space,order-1,vac)
    r=np.r_[rs,0.];g=np.r_[gs,0.];raw={}
    for p in (0,1,3):
        m,v=space.vertices(psi[p],order-1,parity=p%2)
        t=space.F1*psi[p][:,order-1]
        for j in range(1,order):t+=r[j]*m[:,order-j]+g[j]*v[:,order-j]
        if vac is not None:t+=vac.action_coeff(psi[p],order,g)
        raw[p]=space.sample(t,p)
        del m,v,t
    r[order]=-(raw[1]-raw[0])/2
    g[order]=(-(raw[3]-raw[0])-6*r[order])/3
    E={p:np.r_[E0[p],raw[p]+2*p*r[order]+p*(p-1)*g[order]/2] for p in (0,1,3)}
    return psi,E,r,g


def finish_last_wave(space,p,partial,E,r,g,vac=None):
    order=len(r)-1
    psi=np.zeros((space.dim,order+1));psi[:,:order]=partial
    m,v=space.vertices(psi[:,:order],order-1,parity=p%2)
    t=space.F1*psi[:,order-1]
    for j in range(1,order+1):t+=r[j]*m[:,order-j]+g[j]*v[:,order-j]
    if vac is not None:t+=vac.action_coeff(psi[:,:order],order,g)
    solve_wave(t,psi,E,order,p,space.P,space.N)
    return psi


def fixed_wave(space,p,order,r,g,vac=None):
    psi=seed(space,p,order);E=np.r_[p/4,np.zeros(order)]
    for k in range(1,order+1):
        m,v=space.vertices(psi[:,:k],k-1,parity=p%2)
        t=space.F1*psi[:,k-1]
        for j in range(1,k+1):t+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
        if vac is not None:t+=vac.action_coeff(psi[:,:k],k,g)
        E[k]=space.sample(t,p)
        solve_wave(t,psi,E,k,p,space.P,space.N)
    return psi,E


def compute(cutoff,degree=8,scheme='raw',checkpoint=None,memory_limit_gib=None,
            pmax=None,qmax=None):
    if degree<2 or degree>8:raise ValueError('Supported coefficient degrees: 2..8.')
    if cutoff<2 or cutoff%2:raise ValueError('Use even cutoff >=2.')
    if scheme not in ('raw','vacuum_only'):raise ValueError('Unknown prescription.')
    order=degree//2
    pcap=3+4*order if pmax is None else pmax
    qcap=4*order if qmax is None else qmax
    config=dict(version=VERSION,source_sha256=fingerprint(),cutoff=cutoff,degree=degree,
                scheme=scheme,particle_cap=pcap,nonzero_particle_cap=qcap,
                wavefunction_order=order,dtype='float64',fastmath=False)
    cp={'config':config,'components':{}}
    if checkpoint and Path(checkpoint).exists():
        cp=json.loads(Path(checkpoint).read_text())
        if cp['config']!=config:raise ValueError('Checkpoint numerical/source mismatch')
        if 'result' in cp:return cp['result']
    def save():
        if checkpoint:atomic_json(checkpoint,cp)
    start=time.perf_counter()
    if degree>=8 and 'r_low' not in cp:
        lowcp=Path(checkpoint).with_name(Path(checkpoint).stem+'_calibration4.json') if checkpoint else None
        low=compute(cutoff,degree=4,scheme=scheme,checkpoint=lowcp,memory_limit_gib=memory_limit_gib)
        cp.update(r_low=low['r'],g_low=low['g'],
                  E_low={str(p):low['energies'][low['reference_order'].index(p)] for p in (0,1,3)})
        save()
    space=Space(cutoff,pcap,qcap,degree-1,memory_limit_gib=memory_limit_gib)
    vac=Vacuum(space,degree-2) if scheme=='vacuum_only' else None
    if 'r_low' in cp:
        rlow=np.array(cp['r_low']);glow=np.array(cp['g_low']);saved={}
        elow={int(k):np.array(v) for k,v in cp['E_low'].items()}
    else:
        saved,elow,rlow,glow=calibrate_streamed(space,order,vac) if order>=2 else calibrate(space,order,vac)
        cp.update(r_low=rlow.tolist(),g_low=glow.tolist(),E_low={str(p):v.tolist() for p,v in elow.items()});save()
    refs=[0,1,3,2]
    components={int(k):v for k,v in cp['components'].items()}
    for p in refs:
        if p in components:saved.pop(p,None);continue
        if p in saved:
            partial=saved.pop(p)
            psi=finish_last_wave(space,p,partial,elow[p],rlow,glow,vac) if partial.shape[1]==order else partial
            del partial
        else:psi=fixed_wave(space,p,order,rlow,glow,vac)[0]
        F,M,V=quotient_components(space,psi,degree,parity=p%2)
        c=dict(F=F.tolist(),M=M.tolist(),V=V.tolist())
        if vac is not None:c['K']=vacuum_quotient(space,psi,degree-2).tolist()
        components[p]=c;cp['components'][str(p)]=c;save();del psi
    result,E=extract(components,refs,degree,corrected=(vac is not None))
    shell=result['C'][2]-second_order_shell_value(cutoff)
    low=max(np.max(abs(np.array(result['r'])[:order+1]-rlow)),
            np.max(abs(np.array(result['g'])[:order+1]-glow)),
            max(np.max(abs(E[refs.index(p),:order+1]-elow[p])) for p in (0,1,3)))
    result.update(config,basis_dimension=space.global_dim,second_order_shell_residual=float(shell),
                  low_order_residual=float(low),energies=E.tolist(),reference_order=refs,
                  seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  ladder_calls=space.ladder_calls,phase_seconds=space.timings,
                  scope='Direct epsilon coefficients of the specified finite-cutoff Hamiltonian; not physical continuum coefficients. vacuum_only is not Dconn.')
    # Publish only after independent shell, low-order and tuning checks.
    for k in ('C','r','g','energies'):
        if not np.all(np.isfinite(result[k])):raise ArithmeticError('Nonfinite '+k)
    if abs(shell)>1e-10 or low>1e-7 or result['tuning_residual']>1e-6:
        raise ArithmeticError('Acceptance failed: '+str((shell,low,result['tuning_residual'])))
    cp['result']=result;save()
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cutoffs',type=int,nargs='+',required=True)
    ap.add_argument('--degree',type=int,default=8)
    ap.add_argument('--scheme',choices=['raw','vacuum_only'],default='raw')
    ap.add_argument('--threads',type=int,default=2)
    ap.add_argument('--output-dir',type=Path,default=Path('results/raw'))
    ap.add_argument('--memory-limit-gib',type=float)
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    import numba
    numba.set_num_threads(args.threads)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for L in args.cutoffs:
        p=args.output_dir/f'{args.scheme}_L{L}_d{args.degree}.json'
        checkpoint=args.output_dir/'checkpoints'/p.name
        if not args.resume and checkpoint.exists():raise FileExistsError('Use --resume or a new output directory')
        r=compute(L,args.degree,args.scheme,checkpoint,args.memory_limit_gib)
        atomic_json(p,r)
        print(json.dumps({k:r[k] for k in ['cutoff','scheme','basis_dimension','C','second_order_shell_residual','tuning_residual','seconds','peak_rss_kib']}),flush=True)

if __name__=='__main__':main()
