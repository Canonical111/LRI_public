"""Complete low-block linear responses to two independent leading UV operators.
The high expansion is only second order in the interaction. The low response
includes all placements, normalization, vacuum-window feedback and primary tuning.
It is not the complete physical high-order cutoff tail.
"""
from pathlib import Path
import sys,math,time,json,argparse,os
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'vendor'))
from window_jets import Space

def normal(s,psi,p,d):
    low=[psi.copy()]
    for _ in range(p):low.append(s.linear(low[-1],d))
    out=low[0].copy()
    for j in range(1,p+1):out=s.linear(out,d,True)+math.comb(p,j)*low[j]
    out[:,~s.even]=0
    return out

def phase(s,psi,d,part='full'):
    # Normal-ordered representation avoids intermediate boundary mistakes.
    P=s.P[:,None];N=s.N[:,None]
    delta=lambda m: 2-2*((m+7)//8)
    if part in ('phase','full'):
        f4=delta(P+4)
        a=s.linear(s.linear(psi*f4[None,:,:],d,True),d,True)
        b=s.linear(s.linear(psi,d)*(delta(P+3)+delta(P+5))[None,:,:],d,True)
        c=s.linear(s.linear(psi,d),d)*f4[None,:,:]
        out=a+b+c
    else:out=np.zeros((d+1,)+psi.shape[1:])
    if part in ('number','full'):
        m=normal(s,psi,2,d);mn=normal(s,psi*N[None,:,:],2,d)
        out-=.5*(N[None,:,:]*m+mn)
    out[:,~s.even]=0
    return out

def solve(L=8,degree=8,scheme='dconn',channel='full',batch=8):
    if channel not in ('phi6','phase','number','full','mass','quartic'):raise ValueError(channel)
    if scheme not in ('raw','dconn'):raise ValueError(scheme)
    if batch < 1:raise ValueError('batch must be positive')
    start=time.perf_counter();s=Space(L,degree)
    nv=2*L+1 if scheme=='dconn' else 1
    grid=np.arange(nv) if scheme=='dconn' else np.array([2*L])
    refp=np.r_[np.zeros(nv,dtype=int),0,1,2,3];cut2=np.r_[grid,np.repeat(2*L,4)]
    nc=len(refp)
    if 2*(degree+1)*s.n*nc*8 > 1.5*1024**3:
        raise MemoryError('Two wavefunction arrays alone exceed the 1.5 GiB reference guard; use a validated batched/streaming implementation.')
    refi=np.array([s.refs[p] for p in refp]);refe=refp/4
    wave=np.zeros((degree+1,s.n,nc));wave[0,refi,np.arange(nc)]=1
    deriv=np.zeros_like(wave)
    E=np.zeros((degree+1,nc));E[0]=refe;F=np.zeros_like(E)
    r=np.zeros(degree+1);g=np.zeros(degree+1);dr=r.copy();dg=g.copy()
    allow=(s.energy4[:,None]<=2*cut2[None,:])&s.even[:,None]&((s.P[:,None]%2)==refp[None,:]%2)
    den=refe[None,:]-s.E0[:,None];inv=np.divide(1,den,out=np.zeros_like(den),where=allow&(den!=0))
    lower=np.maximum(0,(2*cut2[None,:]-s.energy4[:,None])//2)
    if scheme=='dconn':lower=np.minimum(lower,2*L)
    def diag(A,k):return (A[k,cut2][None,:]-A[k,lower])*allow
    mref,vref=s.vertices(wave[:1],0);mref=mref[0];vref=vref[0]
    for k in range(1,degree+1):
        rhs=s.F1[:,None]*wave[k-1];rhs1=s.F1[:,None]*deriv[k-1]
        gg=np.convolve(g,g)
        for a in range(0,nc,batch):
            b=min(a+batch,nc)
            m,v=s.vertices(wave[:k,:,a:b],k-1);dm,dv=s.vertices(deriv[:k,:,a:b],k-1)
            for j in range(1,k):
                rhs[:,a:b]+=r[j]*m[k-j]+g[j]*v[k-j]
                rhs1[:,a:b]+=r[j]*dm[k-j]+g[j]*dv[k-j]+dr[j]*m[k-j]+dg[j]*v[k-j]
            if k>=2:
                if channel=='phi6':vq=normal(s,wave[:k-1,:,a:b],6,k-2)
                elif channel=='mass':vq=normal(s,wave[:k-1,:,a:b],2,k-2)
                elif channel=='quartic':vq=normal(s,wave[:k-1,:,a:b],4,k-2)/12
                else:vq=phase(s,wave[:k-1,:,a:b],k-2,channel)
                for j in range(2,k+1):rhs1[:,a:b]+=gg[j]*vq[k-j]
        if scheme=='dconn':
            for j in range(2,k):
                rhs+=diag(E,j)*wave[k-j]
                rhs1+=diag(E,j)*deriv[k-j]+diag(F,j)*wave[k-j]
        E[k,:nv]=rhs[s.refs[0],:nv];F[k,:nv]=rhs1[s.refs[0],:nv]
        if scheme=='dconn':rhs+=diag(E,k)*wave[0];rhs1+=diag(F,k)*wave[0]
        raw=rhs[refi,np.arange(nc)];raw1=rhs1[refi,np.arange(nc)]
        r[k]=((-.25 if k==1 else 0)-raw[nv+1]+raw[nv])/2
        g[k]=((.25 if k==1 else 0)-raw[nv+3]+raw[nv]-6*r[k])/3
        dr[k]=(-raw1[nv+1]+raw1[nv])/2
        dg[k]=(-raw1[nv+3]+raw1[nv]-6*dr[k])/3
        rhs+=r[k]*mref+g[k]*vref;rhs1+=dr[k]*mref+dg[k]*vref
        E[k]=rhs[refi,np.arange(nc)];F[k]=rhs1[refi,np.arange(nc)]
        for j in range(1,k+1):
            rhs-=wave[k-j]*E[j][None,:]
            rhs1-=deriv[k-j]*E[j][None,:]+wave[k-j]*F[j][None,:]
        wave[k]=rhs*inv;deriv[k]=rhs1*inv
    e=E[:,nv:].T;f=F[:,nv:].T
    bound=max(np.max(abs(f[1]-f[0])),np.max(abs(f[3]-f[0])))
    if bound>1e-5:raise RuntimeError(('response calibration',bound))
    return dict(low_cutoff=L,degree=degree,scheme=scheme,channel=channel,C=(e[2]-e[0]).tolist(),response=(f[2]-f[0]).tolist(),energies=e.tolist(),energy_response=f.tolist(),r=r.tolist(),g=g.tolist(),dr=dr.tolist(),dg=dg.tolist(),response_tuning_residual=float(bound),basis_dimension=s.n,seconds=time.perf_counter()-start,
        source_definition='eta*g(epsilon)^2 times the chosen low-space operator; Dconn and primary retuning are differentiated too',scope='Complete derivative of the finite low-space model, not a complete high-order Wilson coefficient or physical cutoff tail.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cutoffs',nargs='+',type=int,default=[2,4,6,8]);p.add_argument('--channels',nargs='+',default=['phi6','phase','number','full']);p.add_argument('--schemes',nargs='+',default=['raw','dconn']);p.add_argument('--degree',type=int,default=8);a=p.parse_args()
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    for L in a.cutoffs:
      for scheme in a.schemes:
       for channel in a.channels:
        o=solve(L,a.degree,scheme,channel);path=dest/f'{scheme}_{channel}_L{L}_d{a.degree}.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)
        print(L,scheme,channel,o['response'],o['seconds'],flush=True)
