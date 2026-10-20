"""Opt-in full-vacuum window correction for the product regulator.

A bath state of level N can carry vacuum bath fluctuations only up to level cut-N.
The correction adds D(N)=Ev(cut)-Ev(cut-N) to the bath diagonal of every state of
level N. Ev(L) is the vacuum (field-even, reflection-even) energy of the SAME
product Hamiltonian at bath cutoff L, zero mode included:

  literal     Ev(L) = lowest eigenvalue of H(L)
  consistent  Ev(L) = lowest eigenvalue of H(L)+D_L, with D_L built from the corrected
              lower levels; the scalar fixed point s=lambda_min(s) is solved by Newton,
              F(s)=lambda_min(s)-s, F'=-p0 (p0: bath-level-0 weight of the vacuum vector).
              F is concave, so Newton converges monotonically after at most one step.

The scalar, inversion-even spherical vacuum has even N because each mode level 2n+ell has parity ell. Thus Ev(L) for odd L equals Ev(L-1). Ev(0)=0 because the
local energies are shifted to w[0]=0. Normal-ordered W_j never pass through a bath level
above both endpoints, so H(L) is exactly the N<=L projection of H(cut); H(L) is built as
a genuine bath-cutoff-L regulator.
"""
from __future__ import annotations
import time
import numpy as np
from .basis import SphereBathBasis as BathBasis
from .operators import ProductOperator,restrict_operator

WINDOWS=('none','vacuum')
MODES=('consistent','literal')
FIXED_POINT_CEILING=1e-11   # absolute acceptance ceiling for |lambda_min(s)-s| (PLAN G2)


def converged(F,s,tol):return abs(F)<=min(tol*max(1.,abs(s)),FIXED_POINT_CEILING)


def even_floor(n):return int(n)-(int(n)&1)


class WindowError(RuntimeError):
    """The window fixed point failed at this coupling point (e.g. an extreme line-search trial)."""


class VacuumWindow:
    def __init__(self,cut,nz,delta,backend,mode='consistent',eig_tol=3e-11,ncv=28,max_eig_iter=10000,
                 tol=1e-12,maxiter=50,max_states=2_000_000,max_bytes=2*1024**3,parent_op=None):
        if mode not in MODES:raise ValueError('window mode must be consistent or literal')
        self.cut=int(cut);self.top=even_floor(self.cut);self.mode=mode;self.tol=float(tol);self.maxiter=int(maxiter)
        t=time.perf_counter()
        if parent_op is not None and parent_op.W is not None:
            self.ops={lev:restrict_operator(parent_op,lev) for lev in range(2,self.top,2)}
        else:
            self.ops={lev:ProductOperator(BathBasis.build(lev,max_states=max_states,max_bytes=max_bytes),delta,nz,0,'tensor' if backend=='gram' and lev<=8 else backend) for lev in range(2,self.top,2)}
        self.setup_seconds=time.perf_counter()-t;self.seconds=0.
        self.warm={};self.guess={};self.top_guess=None
        self.last_iterations={};self.last_residuals={}

    @property
    def nbytes(self):return sum(op.nbytes for op in self.ops.values())

    def align(self,signs,main_kpar):
        """Local-basis gauge alignment of warm vectors (initialization only)."""
        for key,v in self.warm.items():
            kpar=main_kpar if key=='top' else self.ops[key].kpar
            self.warm[key]=(v.reshape(len(kpar),-1)*signs[kpar]).ravel()

    def shift(self,levels,s,Ev,L):
        """Diagonal shift s-Ev(L-N) on bath states of level N>0 for a regulator at cutoff L."""
        table=np.array([s-Ev[even_floor(L-n)] if n else 0. for n in range(L+1)],dtype=np.float64)
        return table[levels]

    def sublevels(self,w,L,solve):
        """Ev and vacuum vectors for every even level 2..top-2 (literal or consistent)."""
        Ev={0:0.};vac={};its={};res={}
        for lev,op in self.ops.items():
            levels=op.basis.N
            if self.mode=='literal':
                op.set_bath_shift(None)
                ww,vv,_,_=solve(op,w,L,0,1,self.warm,lev)
                s=float(ww[0]);x=vv[:,0];it=1;r=0.
            else:
                s=self.guess.get(lev,Ev[lev-2])
                for it in range(1,self.maxiter+1):
                    op.set_bath_shift(self.shift(levels,s,Ev,lev))
                    ww,vv,_,_=solve(op,w,L,0,1,self.warm,lev)
                    x=vv[:,0];p0=float(op.level_weights(x)[0]);F=float(ww[0])-s;r=abs(F)
                    if converged(F,s,self.tol):break
                    if not p0>1e-12:raise WindowError(f'Window fixed point at level {lev}: vanishing bath-vacuum weight')
                    s+=F/p0
                else:raise WindowError(f'Window fixed point at level {lev} did not converge (residual {r:.3e})')
                self.guess[lev]=s
            wN=op.level_weights(x);Ev[lev]=s;vac[lev]={'vector':x,'p0':float(wN[0]),'weights':wN}
            its[str(lev)]=it;res[str(lev)]=r
        self.last_iterations=its;self.last_residuals=res
        return Ev,vac

    def d_table(self,Ev):
        return {str(n):(float(Ev[self.top]-Ev[even_floor(self.cut-n)]) if n else 0.) for n in range(self.cut+1)}

    def d_vector(self,Ev):
        return np.array([float(Ev[self.top]-Ev[even_floor(self.cut-n)]) if n else 0. for n in range(self.cut+1)])

    def derivative(self,state,dvac,dtop,top_weights):
        """d Ev / d theta_j by Hellmann-Feynman. dvac[lev], dtop: <dH> of the stored vacuum vectors."""
        dEv={0:0.}
        for lev in sorted(dvac):
            if self.mode=='literal':dEv[lev]=dvac[lev]
            else:
                wN=state['vac'][lev]['weights']
                dEv[lev]=(dvac[lev]-sum(wN[n]*dEv[even_floor(lev-n)] for n in range(1,len(wN))))/state['vac'][lev]['p0']
        if self.mode=='literal':dEv[self.top]=dtop
        else:
            # States whose window reaches the cutoff itself (even_floor(cut-N)==top) carry no shift.
            low=sum(top_weights[n]*dEv[even_floor(self.cut-n)] for n in range(1,len(top_weights)) if even_floor(self.cut-n)<self.top)
            dEv[self.top]=(dtop-low)/top_weights[0]
        return np.array([dEv[self.top]-dEv[even_floor(self.cut-n)] if n else 0. for n in range(self.cut+1)])
