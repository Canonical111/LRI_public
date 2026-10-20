"""Ising x chi RS perturbation theory resummed by chiral generating functions.
No target C2 or elliptic integral from the supplied study is an input.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from functools import lru_cache
from math import pi
import numpy as np
from scipy.fft import fft,fftn,rfft,irfft,next_fast_len
from scipy.signal import fftconvolve
from block_check import blocks
from second_order import coeff

CHI=15/8
ROOT=Path(__file__).parent

def coefficients4(N:int,oversample:int=5,radius_cost:float=4.0):
    """Cauchy/FFT Taylor coefficients, with two angular directions streamed.
    N is number of coefficients retained per variable, including shifts.
    """
    M=next_fast_len(oversample*N);r=np.exp(-radius_cost/N)
    z=r*np.exp(2j*pi*np.arange(M)/M)
    v=z[:,None];w=z[None,:]
    tmp=np.empty((6,M,N,N),dtype=np.complex128)
    for i,u in enumerate(z):
        f=np.asarray(blocks(u,v,w))
        tmp[:,i]=fftn(f,axes=(1,2))[:,:N,:N]/(M*M)
        if i%max(1,M//8)==0:print('Cauchy slice',N,i,M,flush=True)
    out=np.empty((6,N,N,N));worst=0
    ix=np.arange(N);scale=np.exp(radius_cost*(ix[:,None,None]+ix[None,:,None]+ix[None,None,:])/N)
    for j in range(6):
        c=fft(tmp[j],axis=0)[:N]/M*scale
        worst=max(worst,float(np.max(np.abs(c.imag))))
        out[j]=c.real
    return out,dict(N=N,M=M,radius=r,radius_cost=radius_cost,max_imaginary=worst)

@lru_cache(None)
def line_groups(shape:tuple[int,...],direction:tuple[int,...]):
    """Partition a coefficient box into lines parallel to a 0/1 monomial."""
    active=np.flatnonzero(direction)
    grid=np.indices(shape,dtype=np.int32).reshape(len(shape),-1).T
    start=grid[np.min(grid[:,active],axis=1)==0]
    lens=np.min(np.asarray(shape)[active]-start[:,active],axis=1)
    groups=[]
    for L in np.unique(lens):
        ss=start[lens==L]
        ids=ss[None,:,:]+np.arange(L,dtype=np.int32)[:,None,None]*np.asarray(direction)[None,None,:]
        groups.append((int(L),tuple(ids[:,:,k] for k in range(len(shape)))))
    return groups

def monomial_filter(x:np.ndarray,kernel:np.ndarray,direction:tuple[int,...]):
    """Multiply a Taylor array by sum kernel[n] monomial(direction)^n.
    x has a leading field/channel axis.  Convolution is exact to the box.
    """
    out=np.empty_like(x)
    for L,ids in line_groups(x.shape[1:],direction):
        data=x[(slice(None),)+ids]  # field, position on line, number of lines
        m=next_fast_len(2*L-1)
        f=rfft(data,n=m,axis=1)
        f*=rfft(kernel[:L],n=m)[None,:,None]
        y=irfft(f,n=m,axis=1)[:,:L,:]
        out[(slice(None),)+ids]=y
    return out

def shift_multiply(base:np.ndarray,poly:dict[tuple[int,...],float]):
    out=np.zeros_like(base)
    ndim=base.ndim
    for p,c in poly.items():
        src=tuple(slice(0,n-k) for n,k in zip(base.shape,p))
        dst=tuple(slice(k,n) for n,k in zip(base.shape,p))
        if all(n>k for n,k in zip(base.shape,p)):out[dst]+=c*base[src]
    return out

def inv(x):
    return np.divide(1.,x,out=np.zeros_like(x,dtype=float),where=abs(x)>1e-12)

def contract3(x,di,dj,dk):return float(np.einsum('ijk,i,j,k->',x,di,dj,dk,optimize=True))
def contract2(x,di,dj):return float(np.einsum('ij,i,j->',x,di,dj,optimize=True))

def raw4(base:np.ndarray,lam:float,N:int|None=None):
    if N is None:N=base.shape[1]-1
    K=base.shape[1];q=np.exp(-lam);c=coeff(CHI,K)*q**np.arange(K)
    n=np.arange(N,dtype=float);dv=inv(2*n+2);de=inv(2*n+1)
    fac=(2*pi)**4*q**(2*CHI)
    parts=[]
    for name,dirs,occ in [('adjacent',[(1,0,0),(0,0,1)],0),('crossed',[(1,1,0),(0,1,1)],1),('nested',[(1,1,1),(0,1,0)],1)]:
        f=base
        for d in dirs:f=monomial_filter(f,c,d)
        ev=ee=ed=0.
        for p in range(2):
            v=f[p,:N,:N,:N];e=f[2+p,:N,:N,:N];d=f[4+p,1:N+1,1:N+1,1:N+1]
            midv=inv(2*n+p+2*CHI*occ)
            mide=inv(2*n-p+2*CHI*occ)
            ev-=fac*contract3(v*v,dv,midv,dv)
            ee-=fac*contract3(e*e,de,mide,de)
            ed-=fac*contract3(d*e,de,mide,de)
        parts.append(dict(pairing=name,vacuum=ev,epsilon=ee,descendant=ed,X=2*ee-ed-ev))
    return dict(lam=lam,N=N,parts=parts,Xchain=sum(p['X'] for p in parts))

def two_point(lam:float,N:int=100000):
    q=np.exp(-lam);ii=np.arange(N,dtype=float)
    ci=coeff(1/8,N);cc=coeff(CHI,min(N,int(60/lam)+100))*q**np.arange(min(N,int(60/lam)+100))
    polys=[[1.],[.5,.5],[.125,.375,.375,.125]]
    f=[];weighted=[]
    for p in polys:
        a=np.convolve(ci,p)[:N]
        f.append(fftconvolve(a,cc)[:N]);weighted.append(fftconvolve(ii*a,cc)[:N])
    out=[];fac=(2*pi)**2*q**CHI
    for ia,(left,right,shift,Ea) in enumerate([(0,0,0,0),(1,1,0,1),(2,1,1,2)]):
        num=N-shift;n=np.arange(num);d=2*n+(2 if ia==0 else 1)
        fl=f[left][shift:shift+num];fr=f[right][:num]
        wl=weighted[left][shift:shift+num];wr=weighted[right][:num]
        out.append(dict(E2=float(-fac*np.sum(fl*fr/d)),norm=float(fac*np.sum(fl*fr/d**2)),
                        Dmixed=float(fac*np.sum(((1/8-Ea)*fl*fr+wl*fr+fl*wr)/d**2))))
    # exact second-order off-diagonal Hermitian matching used in the saved implementation
    ci_mix=coeff(-3/8,N);cm=fftconvolve(ci_mix,cc)[:N]
    off=-pi*pi*q**CHI*np.sum(cm*cm*(1/(2*ii+1)+1/(2*ii+2)))
    t=-off/(2*pi);k=-(out[1]['E2']-out[0]['E2'])
    disc=-2*out[1]['E2']*out[1]['norm']+out[2]['E2']*out[2]['norm']+out[0]['E2']*out[0]['norm']
    dm=2*out[1]['Dmixed']-out[2]['Dmixed']-out[0]['Dmixed']
    return dict(lam=lam,N=N,states=out,t2=float(t),k2=float(k),Xdisc=float(disc),Dmixed=float(dm),
                X2=2*out[1]['E2']-out[2]['E2']-out[0]['E2'])

# Polynomial coefficients derived by extracting external Majorana modes from the exact two-twist correlator.
CENT_E={(0,0):1,(1,1):1,(1,0):-2,(0,1):-2}
SIDE_E={(0,0):-2,(1,0):1,(1,1):1,(2,1):-2}

def descendant_polys():
    import sympy as s
    u,v=s.symbols('u v')
    cent=(u*v+1)*(u*u*v*v+2*u*u*v-4*u*u+2*u*v*v-6*u*v+2*u-4*v*v+2*v+1)/4
    side=-(v+1)*(4*u**4*v*v-2*u**3*v*v-2*u**3*v-u*u*v*v+6*u*u*v-u*u-2*u*v-2*u+4)/4
    return [{p:float(c) for p,c in s.Poly(s.expand(x),u,v).terms()} for x in (cent,side)]


def mixed(lam:float,N:int=512):
    K=N+1;q=np.exp(-lam);n=np.arange(N,dtype=float)
    chi=coeff(CHI,K)*q**np.arange(K);half=coeff(.5,K)
    neg=coeff(-3/8,K)
    diag=fftconvolve(neg,chi)[:K]
    central=monomial_filter((half[:,None]*half[None,:])[None,:,:],diag,(1,1))[0]
    sideline=fftconvolve(neg,chi)[:K]
    side=monomial_filter((half[:,None]*sideline[None,:])[None,:,:],half,(1,1))[0]
    dc,ds=descendant_polys();fac=(2*pi)**3*q**CHI
    results=[]
    for name,G,pe,pd in [('central',central,CENT_E,dc),('side',side,SIDE_E,ds)]:
        V=G/np.sqrt(2);E=shift_multiply(G,pe)/(2*np.sqrt(2));D=shift_multiply(G,pd)/(2*np.sqrt(2))
        v=V[:N,:N];e=E[:N,:N];d=D[1:N+1,1:N+1]
        if name=='central':dv1=dv2=inv(2*n+2);de1=de2=inv(2*n+1)
        else:dv1=inv(2*n+1);dv2=inv(2*n+2);de1=inv(2*n-1);de2=inv(2*n+1)
        ev=fac*contract2(v*v,dv1,dv2);ee=fac*contract2(e*e,de1,de2);ed=fac*contract2(d*e,de1,de2)
        results.append(dict(ordering=name,vacuum=ev,epsilon=ee,descendant=ed,X=2*ee-ed-ev))
    return dict(lam=lam,N=N,parts=results,Xmixed=results[0]['X']+2*results[1]['X'])


def assemble(base,lam,N=None,mixN=512):
    a=raw4(base,lam,N);b=two_point(lam);c=mixed(lam,mixN)
    x=a['Xchain']+b['Xdisc']+b['t2']*c['Xmixed']+b['k2']*b['Dmixed']+b['t2']**2*32*pi*pi/3
    return dict(lam=lam,spectral_size=a['N'],mixed_size=mixN,raw=a,two_point=b,mixed=c,X4=float(x),physical_C2_claimed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=24);p.add_argument('--a',type=float,nargs='+',default=[.35,.5,.75,1.]);p.add_argument('--mixed',type=int,default=512);p.add_argument('--oversample',type=int,default=5);p.add_argument('--radius-cost',type=float,default=4.);p.add_argument('--coeff-only',action='store_true');aa=p.parse_args()
    K=aa.size+1;fn=ROOT/f'coeff4_K{K}_o{aa.oversample}_r{aa.radius_cost}.npz'
    start=time.time()
    if fn.exists():z=np.load(fn);base=z['coefficients'];meta=json.loads(str(z['metadata']))
    else:
        base,meta=coefficients4(K,aa.oversample,aa.radius_cost)
        np.savez_compressed(fn,coefficients=base,metadata=json.dumps(meta))
    print('coefficients',meta,'seconds',time.time()-start,flush=True)
    if not aa.coeff_only:
        out=[]
        for a in aa.a:
            z=assemble(base,a,mixN=aa.mixed);out.append(z)
            print('RESULT',aa.size,a,z['X4'],'chain',z['raw']['Xchain'],'mixed',z['mixed']['Xmixed'],'seconds',time.time()-start,flush=True)
            (ROOT/f'resummed_N{aa.size}_o{aa.oversample}_r{aa.radius_cost}_m{aa.mixed}.json').write_text(json.dumps(dict(metadata=meta,results=out,elapsed=time.time()-start),indent=2))


# The legacy assemble()/diagnostic helpers do not define a physical C2.
# Use reproduce.py plus the documented local counterterms and regulator-limit
# analysis for the current calculation.
