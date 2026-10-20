#!/usr/bin/env python3
"""Direct fourth-order Rayleigh--Schrodinger coefficients in Ising x chi.

The regulator in this file is a genuine vertex regulator:
chi -> chi_a, with oscillator coefficients multiplied by exp(-a*energy/2).
The Ising basis and chi one-particle mode level have independent cutoffs.
All intermediate zero- and two-chi sectors are retained within these cutoffs.
No finite-delta fit or asserted C2 is used. Results before continuum matching
are labelled diagnostic, NOT a physical value of C2.
"""
from __future__ import annotations
import argparse,json,time
from math import pi,sqrt
from pathlib import Path
import numpy as np
from ising_basis import Basis
from second_order import smooth_chi


def evaluate(basis:Basis,L:int,regulators:list[float],targets:list[int]):
    b=basis;ts=np.array(regulators);A=len(ts);P=len(targets)
    assert len(set(int(b.j[t]) for t in targets))==1
    spin=int(b.j[targets[0]])
    # Shape of each amplitude: (state, mode, external-state*regulator).
    B=A*P; et=np.repeat(b.e[targets],A); regs=np.tile(ts,P)
    cc=[1.]
    for k in range(1,L+1):cc.append(cc[-1]*(15/8+k-1)/k)
    modes=[(p,l-p,15/8+l,2*p-l,sqrt(cc[p]*cc[l-p])) for l in range(L+1) for p in range(l+1)]
    nm=len(modes);me=np.array([m[2] for m in modes]);mj=np.array([m[3] for m in modes])
    c=np.array([m[4] for m in modes])[:,None]*np.exp(-me[:,None]*regs[None,:]/2)
    ns=np.flatnonzero(~b.r);nsE=b.e[ns];nsJ=b.j[ns]
    nswhere={int(ix):pos for pos,ix in enumerate(ns)}
    ns_by_spin={int(j):np.flatnonzero(nsJ==j) for j in np.unique(nsJ)}
    zero=ns_by_spin[spin]
    U=np.zeros((len(ns),nm,B))
    E2=np.zeros(B);norm=np.zeros(B);central=np.zeros(B);Dmixed=np.zeros(B); chimixed=np.zeros(B)
    for jspin in sorted(set(mj)):
        js=np.flatnonzero(mj==jspin)
        r=np.flatnonzero(b.r&(b.j==spin-jspin))
        if not len(r):continue
        sig=None
        ea=et[None,None,:]
        den=ea-b.e[r,None,None]-me[js][None,:,None]
        vv=np.stack([b.spin_column(r,t) for t in targets],axis=1)
        vv=np.repeat(vv,A,axis=1)[:,None,:]
        v=2*pi*vv*c[js][None,:,:]
        w=v/den
        E2+=np.sum(v*w,axis=(0,1));norm+=np.sum(w*w,axis=(0,1))
        Dmixed+=np.sum(w*w*(b.e[r,None,None]-ea),axis=(0,1))
        chimixed+=4*pi*np.sum(np.sum(w*c[js][None,:,:],axis=1)**2,axis=0)
        flat=w.reshape(len(r),-1)
        for lo in range(0,len(ns),2048):
            hi=min(lo+2048,len(ns))
            sig=b.spin_block(ns[lo:hi],r)
            U[lo:hi,js,:]=(sig@flat).reshape(hi-lo,len(js),B)
        W=2*pi*b.energy_sparse(r)
        central+=np.sum(flat*(W@flat),axis=0).reshape(len(js),B).sum(axis=0)
    z0=2*pi*np.einsum('jcb,cb->jb',U[zero,:,:],c)
    reverse=[]
    for ip,t in enumerate(targets):
        loc=int(np.flatnonzero(ns[zero]==t)[0]); sl=slice(ip*A,(ip+1)*A)
        reverse.append(float(np.max(np.abs(z0[loc,sl]-E2[sl]))))
        z0[loc,sl]=0
    den0=et[None,:]-nsE[zero,None]
    r0=np.divide(1.,den0,out=np.zeros_like(den0),where=np.abs(den0)>1e-12)
    E40=np.sum(z0*z0*r0,axis=0)
    Wvec=np.repeat(np.stack([2*pi*b.energy_column(ns[zero],t) for t in targets],axis=1),A,axis=1)
    side=2*np.sum(Wvec*r0*z0,axis=0)
    quadratic=np.sum(Wvec*Wvec*r0,axis=0)
    E42=np.zeros(B);n2=0
    for j in range(nm):
        for k in range(j,nm):
            inds=ns_by_spin.get(spin-mj[j]-mj[k])
            if inds is None:continue
            n2+=len(inds)
            if j==k:
                z=2*pi*sqrt(2)*U[inds,j,:]*c[j]
            else:
                z=2*pi*(U[inds,j,:]*c[k]+U[inds,k,:]*c[j])
            den=et[None,:]-nsE[inds,None]-me[j]-me[k]
            E42+=np.sum(z*z/den,axis=0)
            if mj[j]+mj[k]==0:
                fac=2*pi*(sqrt(2) if j==k else 2)
                for ip,t in enumerate(targets):
                    sl=slice(ip*A,(ip+1)*A)
                    ii=np.flatnonzero(ns[inds]==t)
                    assert len(ii)==1
                    chimixed[sl]+=2*fac*c[j,sl]*c[k,sl]*z[ii[0],sl]/den[ii[0],sl]
    E4disc=-E2*norm
    records=[]
    for ip,t in enumerate(targets):
        for it,a in enumerate(ts):
            ix=ip*A+it
            records.append(dict(target=int(t),unperturbed_E=float(b.e[t]),spin=spin,a=float(a),
                E2=float(E2[ix]),norm2=float(norm[ix]),E4_0chi=float(E40[ix]),
                E4_2chi=float(E42[ix]),E4_disconnected=float(E4disc[ix]),
                E4=float(E40[ix]+E42[ix]+E4disc[ix]),
                mixed_chi_squared=float(chimixed[ix]),mixed_thermal=float(central[ix]+side[ix]),mixed_D_Ising=float(Dmixed[ix]),
                thermal_squared=float(quadratic[ix])))
    return dict(Ising_cutoff=b.cutoff,chi_level=L,Ising_states=len(b.e),chi_modes=nm,
                two_chi_states=n2,reverse_action_errors=reverse,records=records)

def run(I,L,regulators):
    start=time.time();b=Basis(I)
    even=evaluate(b,L,regulators,[b.vac,b.eps]);desc=evaluate(b,L,regulators,[b.desc])
    results=[]
    for a in regulators:
        r0=next(r for r in even['records'] if r['target']==b.vac and r['a']==a)
        re=next(r for r in even['records'] if r['target']==b.eps and r['a']==a)
        rd=next(r for r in desc['records'] if r['a']==a)
        x={k:2*re[k]-rd[k]-r0[k] for k in ['E2','E4','E4_0chi','E4_2chi','E4_disconnected','mixed_thermal','mixed_D_Ising','thermal_squared','mixed_chi_squared']}
        match=smooth_chi(a)
        t,k=match['t2'],match['k2']
        x4=x['E4']+t*x['mixed_thermal']+k*x['mixed_D_Ising']+t*t*32*pi*pi/3
        results.append(dict(a=a,X_raw=x,second_order_matching=match,
            X4_diagnostic_after_second_order_matching=x4,
            is_physical_C2=False,
            note='The exact infinite-Ising thermal-squared term is used. Matching sufficiency and UV limits are not established.'))
    return dict(Ising_cutoff=I,chi_level=L,elapsed=time.time()-start,
                spin_zero=even,spin_one=desc,results=results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ising',type=float,default=16)
    parser.add_argument('--chi',type=int,default=12);parser.add_argument('--a',type=float,nargs='+',default=[.5,.75,1.])
    parser.add_argument('--output',required=True);args=parser.parse_args()
    data=run(args.ising,args.chi,args.a)
    Path(args.output).write_text(json.dumps(data,indent=2)+'\n')
    for r in data['results']:print(args.ising,args.chi,r['a'],r['X_raw']['E2'],r['X4_diagnostic_after_second_order_matching'],flush=True)
    print('seconds',data['elapsed'],flush=True)
