#!/usr/bin/env python3
"""Small-basis reference implementation of finite-shell Schur matching.

Integrates Q=(Lambda_low,Lambda_parent] out through a requested epsilon order.
Includes all high-state excursions and the energy-dependent resolvent, not just
V_PQ R0 V_QP. Couplings are those of the parent; they are never refitted to a
physical C4--C7. This deliberately constructs a parent basis and dense blocks:
it is a validation oracle, NOT the scalable analytic kernel for HPC cutoffs.
"""
from __future__ import annotations
import argparse,json,time,sys
from pathlib import Path
import numpy as np
from numba import set_num_threads
from lri_hpc.operators import Space
from lri_hpc.solver import calibrate,fixed_wave,extract
from run_vacuum_matched import compute

def build_sector(space,parity,r,g,degree):
    ids=np.flatnonzero((space.P%2==parity)&(space.N%2==0))
    d=len(ids);H=np.zeros((degree+1,d,d))
    H[0]=np.diag(space.Efree[ids])
    H[1]+=np.diag(space.F1[ids])
    for j,idx in enumerate(ids):
        x=np.zeros((space.dim,1));x[idx,0]=1
        m,v=space.vertices(x,degree-1,parity=parity)
        for k in range(1,degree+1):
            for a in range(1,k+1):
                H[k,:,j]+=r[a]*m[ids,k-a]+g[a]*v[ids,k-a]
    err=float(np.max(np.abs(H-H.transpose(0,2,1))))
    if err>1e-9:raise ArithmeticError(f'Hermiticity failed: {err}')
    return ids,H,err

def rs_energy(H,ref,degree):
    d=H.shape[1];E=np.zeros(degree+1);E[0]=H[0,ref,ref]
    v=np.zeros((degree+1,d));v[0,ref]=1
    den=E[0]-np.diag(H[0]);R=np.zeros(d)
    sel=den!=0
    if np.sum(~sel)!=1:raise ValueError('degenerate reference')
    R[sel]=1/den[sel]
    for k in range(1,degree+1):
        t=sum((H[j]@v[k-j] for j in range(1,k+1)),np.zeros(d))
        E[k]=t[ref]
        for j in range(1,k+1):t-=E[j]*v[k-j]
        v[k]=R*t
    return E

def schur_energy(H,ref,low,degree,self_energy_order=None):
    """Full perturbative Schur complement; matrices have Taylor coefficients.

    K_m=(E0-HQQ0)^-1 [H_QP,m+sum_j(HQQ,j-E_j I)K_(m-j)].
    Sigma_k=sum_(a=1)^(k-1) H_PQ,a K_(k-a).
    H_eff(E)=HPP+Sigma(E). E_j are solved self-consistently, order by order.
    """
    if self_energy_order is None:self_energy_order=degree
    high=np.flatnonzero(~low);lo=np.flatnonzero(low)
    if ref not in lo:raise ValueError('reference not retained')
    ip=int(np.flatnonzero(lo==ref)[0]);nl=len(lo);nq=len(high)
    Hpp=H[:,lo][:,:,lo];Hpq=H[:,lo][:,:,high]
    Hqp=H[:,high][:,:,lo];Hqq=H[:,high][:,:,high]
    E=np.zeros(degree+1);E[0]=H[0,ref,ref]
    v=np.zeros((degree+1,nl));v[0,ip]=1
    den=E[0]-np.diag(Hpp[0]);Rp=np.zeros(nl);sel=den!=0;Rp[sel]=1/den[sel]
    Rq=1/(E[0]-np.diag(Hqq[0]))
    K=[np.zeros((nq,nl))];Heff=[Hpp[0]]
    for k in range(1,degree+1):
        if k>=2:
            m=k-1;t=Hqp[m].copy()
            for j in range(1,m):t+=(Hqq[j]@K[m-j]-E[j]*K[m-j])
            K.append(Rq[:,None]*t)
        eff=Hpp[k].copy()
        if k<=self_energy_order:
            for a in range(1,k):eff+=Hpq[a]@K[k-a]
        Heff.append(eff)
        rhs=sum((Heff[j]@v[k-j] for j in range(1,k+1)),np.zeros(nl))
        E[k]=rhs[ip]
        for j in range(1,k+1):rhs-=E[j]*v[k-j]
        v[k]=Rp*rhs
    herm=float(max(np.max(abs(h-h.T)) for h in Heff))
    return E,herm

def compare(low,parent,degree=7):
    if parent>16:raise ValueError('Dense validation oracle intentionally capped at parent<=16')
    if low>=parent or low<2 or low%2 or parent%2:raise ValueError('even 2<=low<parent required')
    t=time.perf_counter();parent_result=compute(parent,degree,False)
    r=np.array(parent_result['r']);g=np.array(parent_result['g'])
    space=Space(parent,3+4*(degree//2),4*(degree//2),degree-1)
    full={};match={};naive={};partial={};counts={};maxherm=0
    for parity in (0,1):
        ids,H,he=build_sector(space,parity,r,g,degree);maxherm=max(maxherm,he)
        keep=space.Efree[ids]<=low;counts[parity]=dict(parent=int(len(ids)),retained=int(np.sum(keep)))
        for p in (parity,parity+2):
            ref=int(np.flatnonzero(ids==p)[0])
            full[p]=rs_energy(H,ref,degree)
            match[p],he=schur_energy(H,ref,keep,degree);maxherm=max(maxherm,he)
            partial[p]=schur_energy(H,ref,keep,degree,self_energy_order=2)[0]
            ilow=int(np.flatnonzero(np.flatnonzero(keep)==ref)[0])
            naive[p]=rs_energy(H[:,keep][:,:,keep],ilow,degree)
    cf=full[2]-full[0];cm=match[2]-match[0];cn=naive[2]-naive[0]
    absolute=max(float(np.max(abs(full[p]-match[p]))) for p in range(4))
    # independent quotient in parent versus ordinary parent recursion
    recerr=float(np.max(abs(cf-np.array(parent_result['C']))))
    tol=5e-7
    if absolute>tol or recerr>tol:raise ArithmeticError((absolute,recerr))
    return dict(low=low,parent=parent,degree=degree,counts=counts,
       scope='Finite parent matching only. Raw parent couplings held fixed. Not a physical infinite-cutoff determination.',
       parent_C=cf.tolist(),matched_C=cm.tolist(),naive_low_same_parent_couplings_C=cn.tolist(),
       only_second_order_self_energy_C=(partial[2]-partial[0]).tolist(),
       max_parent_matched_energy_difference=absolute,max_parent_recursion_quotient_difference=recerr,
       effective_H_hermiticity_residual=maxherm,seconds=time.perf_counter()-t)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pairs',nargs='+',default=['4:8','6:12'])
    ap.add_argument('--degree',type=int,default=7);ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--output',type=Path,default=Path('finite_shell_validation.json'))
    a=ap.parse_args();set_num_threads(a.threads);out=[]
    for pair in a.pairs:
        lo,hi=map(int,pair.split(':'));res=compare(lo,hi,a.degree);out.append(res);print(json.dumps(res),flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n')
