"""Low-memory monomial convolution and complete cutoff sequences.
Only numerical bookkeeping differs from resummed.py; see finite checks.
"""
import numpy as np
import os
import mmap
from functools import partial
from scipy.fft import rfft,irfft,next_fast_len
from math import pi
FFT_WORKERS=int(os.environ.get("LRI_FFT_WORKERS","1"))
rfft=partial(rfft,workers=FFT_WORKERS)
irfft=partial(irfft,workers=FFT_WORKERS)
from resummed import CHI,coeff,inv
from improved_regulator import trunc_exp

def filt(x,kernel,direction):
    out=np.empty_like(x);N=x.shape[1];act=np.flatnonzero(direction)
    if len(act)==1:
        ax=int(act[0])+1
        perm=[0,ax]+[a for a in range(1,4) if a!=ax]
        a=np.transpose(x,perm);b=np.transpose(out,perm);M=next_fast_len(2*N-1);fk=rfft(kernel[:N],n=M)[None,:,None,None]
        for lo in range(0,N,8):
            hi=min(N,lo+8);z=rfft(a[:,:,lo:hi,:],n=M,axis=1);z*=fk
            b[:,:,lo:hi,:]=irfft(z,n=M,axis=1)[:,:N]
    elif len(act)==2:
        other=next(k for k in range(3) if k not in act);perm=[0,int(act[0])+1,int(act[1])+1,other+1]
        a=np.transpose(x,perm);b=np.transpose(out,perm)
        for off in range(-(N-1),N):
            L=N-abs(off);ii=np.arange(L)+max(off,0);jj=np.arange(L)+max(-off,0)
            M=next_fast_len(2*L-1);z=rfft(a[:,ii,jj,:],n=M,axis=1);z*=rfft(kernel[:L],n=M)[None,:,None]
            b[:,ii,jj,:]=irfft(z,n=M,axis=1)[:,:L,:]
    elif len(act)==3:
        for L in range(1,N+1):
            a=N-L
            if a==0:starts=np.zeros((1,3),int)
            else:
                starts=[(0,0,a),(0,a,0),(a,0,0),(0,a,a),(a,0,a),(a,a,0)]
                for t in range(1,a):starts.extend([(0,a,t),(0,t,a),(a,0,t),(t,0,a),(a,t,0),(t,a,0)])
                starts=np.array(starts,int)
            ids=tuple(np.arange(L)[:,None]+starts[None,:,i] for i in range(3))
            M=next_fast_len(2*L-1);z=rfft(x[(slice(None),)+ids],n=M,axis=1);z*=rfft(kernel[:L],n=M)[None,:,None]
            out[(slice(None),)+ids]=irfft(z,n=M,axis=1)[:,:L,:]
    else:raise ValueError('A nonzero 0/1 direction is required')
    return out

def prefix3(a):
    """Sum a over each centered coefficient box [0,N)^3, all N at once."""
    for ax in range(3):np.cumsum(a,axis=ax,out=a)
    ii=np.arange(a.shape[0]);return a[ii,ii,ii].copy()

def raw_sequence(base,lam,order=0):
    K=base.shape[1];N=K-1;n=np.arange(N,dtype=float);q=np.exp(-lam)
    kernel=coeff(CHI,K)*q**np.arange(K)*trunc_exp(lam*(np.arange(K)+CHI/2),order)
    dv=inv(2*n+2);de=inv(2*n+1);fac=-(2*pi)**4*q**(2*CHI)
    parts=[]
    for name,dirs,occ in [('adjacent',[(1,0,0),(0,0,1)],0),('crossed',[(1,1,0),(0,1,1)],1),('nested',[(1,1,1),(0,1,0)],1)]:
        xx=np.zeros(N)
        for p in [0,1]:
            f=np.empty((3,)+base.shape[1:],dtype=float)
            for field,idx in enumerate([p,2+p,4+p]):f[field]=base[idx]
            if isinstance(base,np.memmap) and hasattr(mmap,"MADV_DONTNEED"):
                base._mmap.madvise(mmap.MADV_DONTNEED)
            for dr in dirs:f=filt(f,kernel,dr)
            v=f[0,:N,:N,:N];e=f[1,:N,:N,:N];d=f[2,1:K,1:K,1:K]
            midv=inv(2*n+p+2*CHI*occ);mide=inv(2*n-p+2*CHI*occ)
            work=np.empty((N,N,N),dtype=float)
            np.multiply(e,2.,out=work);work-=d;work*=e
            work*=de[:,None,None];work*=mide[None,:,None];work*=de[None,None,:]
            tmp=v*v;tmp*=dv[:,None,None];tmp*=midv[None,:,None];tmp*=dv[None,None,:]
            work-=tmp;del tmp,f,v,e,d
            xx+=fac*prefix3(work)
            del work
        parts.append(dict(pairing=name,X=xx.tolist()))
    return dict(lam=lam,order=order,Nmax=N,parts=parts,Xchain=np.sum([p['X'] for p in parts],axis=0).tolist())

if __name__=='__main__':
    from pathlib import Path
    import json
    import resummed_improved as r
    rng=np.random.default_rng(734)
    errors=[]
    for d in [(1,0,0),(0,0,1),(1,1,0),(0,1,1),(1,1,1)]:
        x=rng.normal(size=(3,9,9,9));c=rng.normal(size=9)
        errors.append(float(np.max(abs(filt(x,c,d)-r.monomial_filter(x,c,d)))))
    cache=r.ROOT/'coeff4_K25_o5_r4.0.npz'
    if not cache.exists():
        from resummed import coefficients4
        coeffs,metadata=coefficients4(25,5,4.)
        np.savez_compressed(cache,coefficients=coeffs)
    base=np.load(cache)['coefficients'];rows=[]
    for order,a in [(0,.5),(1,.25)]:
        r.ORDER=order;y=raw_sequence(base,a,order)
        for n in [4,8,16,24]:
            z=r.raw4(base[:,:n+1,:n+1,:n+1],a)
            rows.append(dict(order=order,lam=a,N=n,old=z['Xchain'],new=y['Xchain'][n-1],error=z['Xchain']-y['Xchain'][n-1]))
    out=dict(filter_max_errors=errors,sequence_checks=rows)
    (r.ROOT/'lowmemory_checks.json').write_text(json.dumps(out,indent=2));print(out)
