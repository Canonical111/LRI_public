"""Leading F^3 kernel for arbitrary fixed low bath states, not just zero modes.
Finite annuli are summed directly. This test involves no thermal fit or target.
"""
from pathlib import Path
import math,json,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def basis(K,pmax):
    states=[]
    def gen(st,start):
        states.append(st)
        if len(st)==pmax:return
        for i in range(start,K+1):gen(st+(i,),i)
    gen((),0);index={v:i for i,v in enumerate(states)}
    return states,index

def run(K=2,pmax=9,alpha=.5,Es=.3):
    states,index=basis(K,pmax);P=np.array([len(s) for s in states]);N=np.array([sum(s) for s in states]);H=N+alpha*P/2;D=len(states)
    ws=np.ones(K+1)
    for n in range(1,K+1):ws[n]=ws[n-1]*(alpha+n-1)/n
    B=np.zeros((D,D))
    for i,s in enumerate(states):
        for n in set(s):
            z=list(s);z.remove(n);B[index[tuple(z)],i]=math.sqrt(s.count(n)*ws[n])
    q=B+B.T;A=sum(ws);M=q@q-A*np.eye(D);beta=3*alpha
    results=[]
    for refl in [0,1]:
      inds=np.flatnonzero((N%2==refl)&(P<=6)&(N<=4))
      delta=lambda p:2+refl-2*np.ceil((p+4*refl)/8)
      # All low-bath mode occupations, not just n0, appear here.
      jp=q@(delta(P+3)[:,None]*q)-np.diag(A*delta(P+4))
      J=jp-.5*(N[:,None]*M+M*N[None,:])
      alt=q@((delta(P+3)-N)[:,None]*q)-np.diag(A*(delta(P+4)-N)-sum(np.arange(K+1)*ws))
      assert np.max(abs((J-alt)[np.ix_(inds,inds)]))<1e-12
      blocks=[m[np.ix_(inds,inds)] for m in [M,J,jp]];ml,jl,jpl=blocks
      h=H[inds];I=np.eye(len(inds))
      def primitive(L,which='full'):
        Aa=L**(beta-1)/(3*(beta-1)*math.gamma(beta));Bb=L**(beta-2)/(3*(2-beta)*math.gamma(beta))
        j=jl if which=='full' else jpl
        return Aa*ml-Bb*((2-beta)**2*ml/2+Es*ml-(h[:,None]+h[None,:])*ml/2-(2-beta)*j)
      for L in [32,64,128,256,512,1024]:
        U=2*L;v=np.ones(U+1)
        for n in range(1,U+1):v[n]=v[n-1]*(beta+n-1)/n
        n=np.arange(U+1)
        s3=np.zeros(D)
        for j in range(D):
            if not np.any(q[j,inds]):continue
            sigma=(refl-int(N[j])%2)%2
            mask=(n%2==sigma)&(n+N[j]+P[j]/4+.75>L)&(n+N[j]+P[j]/4+.75<=U)
            s3[j]=np.sum(v[mask]/(Es-H[j]-3*alpha/2-n[mask]))
        qsub=q[:,inds];actual=(qsub.T@(s3[:,None]*qsub))
        for a,i in enumerate(inds):
            for k,w in enumerate(ws):
                mask=(n%2==k%2)&(n+k+N[i]+P[i]/4+1>L)&(n+k+N[i]+P[i]/4+1<=U)
                actual[a,a]-=w*np.sum(v[mask]/(Es-H[i]-2*alpha-k-n[mask]))
        actual*=2/3
        good=primitive(L)-primitive(U);bad=primitive(L,'phase_only')-primitive(U,'phase_only')
        error=float(np.max(abs(actual-good)));errorbad=float(np.max(abs(actual-bad)))
        results.append(dict(low_mode_cutoff=K,alpha=alpha,reflection=refl,external_states=len(inds),L=L,U=U,error=error,phase_only_error=errorbad,rescaled_next_error=error*L**(3-beta),rescaled_wrong_error=errorbad*L**(2-beta)))
    return results

if __name__=='__main__':
    rows=[]
    for a in [.49,.5,.51]:rows.extend(run(alpha=a))
    (ROOT/'results/general_bath_annulus.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:
        if r['alpha']==.5:print(r)
