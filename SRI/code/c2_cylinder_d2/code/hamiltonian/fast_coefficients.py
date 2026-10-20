"""Streaming Cauchy extraction using precomputed monomial phases and reality.
Mathematically identical to coefficients4 in resummed.py. Uses disk only for
large temporary arrays, and keeps the perturbative-state sum independent of
any proposed LRI fourth-order value.
"""
from pathlib import Path
import json,time,os
import numpy as np
from scipy.fft import fftn,irfft,next_fast_len
from math import pi
ROOT=Path(__file__).parent

def compute(K,oversample=5,rc=4.,prefix='fast'):
    start=time.time();M=next_fast_len(oversample*K)
    if M%2:M=next_fast_len(M+1)
    r=np.exp(-rc/K);ph=np.exp(2j*pi*np.arange(M)/M)
    z=r*ph;v=z[:,None];w=z[None,:]
    sq=[None]+[np.sqrt(1-r**d*ph) for d in [1,2,3]]
    pw=[None]+[(1-r**d*ph)**(-.125) for d in [1,2,3]]
    ids=(np.arange(M)[:,None]+np.arange(M)[None,:])%M
    sqvw=sq[2][ids];base=pw[1][:,None]*pw[1][None,:]*pw[2][ids]
    fn=ROOT/f'{prefix}_tmp_K{K}.dat'
    tmp=np.memmap(fn,mode='w+',dtype=np.complex128,shape=(6,M//2+1,K,K))
    for i in range(M//2+1):
        u=z[i];idx=(ids+i)%M;j=(np.arange(M)+i)%M
        s=sq[2][j][:,None]*sqvw;t=sq[1][:,None]*sq[3][idx]
        D=pw[1][i]*base*pw[2][j][:,None]*pw[3][idx]
        R=np.sqrt((s+t)/2);Q=sq[1][i]*sq[1][None,:]
        A=s*(1+u*w);B=t*(u+w)
        uvw=u*v*w
        sk=(u+uvw)-(1+u*v);ik=(1/u+1/uvw)-(1+1/(u*v))
        sl=(u+u*v)-(1+uvw);il=(1/u+1/(u*v))-(1+1/uvw)
        k=uvw*(1-sk*ik/4);l=uvw*(1-sl*il/4)
        f=np.array([D*R,.5*D*Q/R,.25*D*(A+B)/R,.5*D*R/Q*(A-B),.25*D*(A*k+B*l)/R,.5*D*R/Q*(A*k-B*l)])
        ft=fftn(f,axes=(1,2))[:,:K,:K]/(M*M)
        tmp[:,i]=ft
        if i%max(1,M//16)==0:
            tmp.flush();print('FAST',K,i,M//2,round(time.time()-start,2),flush=True)
    tmp.flush();del f,ft,D,R,Q,A,B,k,l,s,t,base,sqvw
    outpath=ROOT/f'{prefix}_coeff4_K{K}_o{oversample}_r{rc}.npy'
    out=np.lib.format.open_memmap(outpath,mode='w+',dtype=float,shape=(6,K,K,K))
    for field in range(6):
        for lo in range(0,K,8):
            hi=min(lo+8,K)
            a=irfft(np.conj(tmp[field,:,lo:hi,:]),n=M,axis=0)[:K]
            sc=np.exp(rc*(np.arange(K)[:,None,None]+np.arange(lo,hi)[None,:,None]+np.arange(K)[None,None,:])/K)
            out[field,:,lo:hi,:]=a*sc
        out.flush();print('FFT U',K,field,round(time.time()-start,2),flush=True)
    del tmp,out;fn.unlink()
    meta=dict(K=K,M=M,oversample=oversample,radius_cost=rc,radius=r,elapsed=time.time()-start,method='phase_lookup_and_conjugate_half_grid')
    outpath.with_suffix('.json').write_text(json.dumps(meta,indent=2))
    return outpath,meta

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=64);p.add_argument('--oversample',type=int,default=5);p.add_argument('--radius-cost',type=float,default=4.);a=p.parse_args()
 print(compute(a.size+1,a.oversample,a.radius_cost),flush=True)
