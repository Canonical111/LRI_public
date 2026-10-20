"""Direct spectra and safeguarded moving-subspace response tuning.

With window='none' (default) this computes the SAME bare, finite product-regulator
Hamiltonian as the reference. window='vacuum' adds the opt-in full-vacuum window
shift D(N) of window.py to the bath diagonal; nothing else changes.
"""
from __future__ import annotations
import math,time
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import eigsh,ArpackNoConvergence
from .basis import CircleBathBasis as BathBasis
from .local import LocalProblem
from .operators import ProductOperator
from .window import VacuumWindow,WindowError,even_floor,converged,WINDOWS,MODES,FIXED_POINT_CEILING

class DressedSolver:
    def __init__(self,bath_cut=12,nz=20,osc=160,angular=0,eig_tol=3e-11,
                 zero_scale=1.,backend='auto',ncv=28,max_eig_iter=10000,residual_tol=2e-7,
                 checkpoint=None,basis=None,window='none',window_mode='consistent',window_tol=1e-12,
                 window_maxiter=50,ground_only=True,max_bath_states=2_000_000,max_basis_bytes=2*1024**3):
        if not isinstance(angular,int):raise ValueError('angular momentum must be integer')
        if window not in WINDOWS or window_mode not in MODES:raise ValueError('Unknown window prescription')
        if not 0<window_tol<=FIXED_POINT_CEILING or window_maxiter<1:raise ValueError('Invalid window tolerances (0<window_tol<=1e-11)')
        if window!='none' and angular!=0:
            raise ValueError('The window table is built from the angular-even vacuum; use angular=0 '
                             '(identities.diagnose applies the table to odd sectors)')
        self.window=window;self.window_mode=window_mode;self.window_tol=window_tol;self.window_maxiter=int(window_maxiter)
        if bath_cut<2:raise ValueError('bath cutoff must be >=2')
        if window!='none' and bath_cut%2:raise ValueError('Window scalar solve currently requires an even bath cutoff')
        if not 0<=eig_tol<1 or residual_tol<=0:raise ValueError('Invalid solver tolerances')
        if backend=='auto':backend='tensor' if bath_cut<=12 else 'gram'
        self.backend=backend;self.bath_cut=int(bath_cut);self.nz=int(nz);self.osc=int(osc);self.angular=int(angular)
        self.eig_tol=eig_tol;self.ncv=int(ncv);self.max_eig_iter=max_eig_iter;self.residual_tol=residual_tol
        self.local_problem=LocalProblem(nz,osc,zero_scale);self.checkpoint=checkpoint
        self.max_bath_states=int(max_bath_states);self.max_basis_bytes=int(max_basis_bytes)
        self.ground_only=bool(ground_only);self._window_cache=None;self.window_cache_hits=0
        t=time.perf_counter();self.basis=basis or BathBasis.build(bath_cut,max_states=max_bath_states,max_bytes=max_basis_bytes)
        if self.basis.cutoff!=bath_cut:raise ValueError('basis cutoff mismatch')
        self.timings={'basis':time.perf_counter()-t,'bath_operators':0.,'local':0.,'eigensolver':0.,'jacobian':0.}
        self.warm={};self.calls=0;self.delta=None;self.op=None;self.win=None

    def set_delta(self,delta):
        if not np.isfinite(delta) or not 0<delta<.5:raise ValueError('Require 0<Delta_sigma<1/2')
        t=time.perf_counter();self.delta=float(delta)
        self.op=None;self.warm.clear();self._warm_U=None;self._window_cache=None
        self.op=ProductOperator(self.basis,delta,self.nz,self.angular,self.backend)
        self.win=None
        if self.window=='vacuum':
            self.win=VacuumWindow(self.bath_cut,self.nz,delta,self.backend,self.window_mode,eig_tol=self.eig_tol,
                ncv=self.ncv,max_eig_iter=self.max_eig_iter,tol=self.window_tol,maxiter=self.window_maxiter,max_states=self.max_bath_states,max_bytes=self.max_basis_bytes)
        self.timings['bath_operators']+=time.perf_counter()-t
        self.warm={}

    def initial(self,eps):
        r=.2*eps*eps;g=max(1e-8,eps/3+.5*eps*eps)
        A=self.delta/4+r-g/2;e=(g*self.delta**2/192)**(1/3)
        return np.array([A*self.delta/(4*e*e),math.log(e)])

    def prepare(self,theta):
        """Local problem at theta and gauge alignment of warm vectors (no spectra)."""
        if self.op is None:raise RuntimeError('Call set_delta first')
        t=time.perf_counter();w,L,U,info=self.local_problem.evaluate(self.delta,theta)
        self.timings['local']+=time.perf_counter()-t
        # Align only the gauge/sign of the previous warm vector to the new local
        # basis. This changes initialization, not the operator or spectrum.
        if self._warm_U is not None:
            signs=np.sign(np.sum(U*self._warm_U,axis=0));signs[signs==0]=1
            for f in self.warm:
                factor=signs.reshape(2,self.nz)[self.op.kpar^f]
                self.warm[f]=(self.warm[f].reshape(self.op.nB,self.nz)*factor).ravel()
            if self.win is not None:self.win.align(signs.reshape(2,self.nz),self.op.kpar)
        self._warm_U=U.copy()
        return w,L,U,info

    def sector_solve(self,op,w,L,f,k,warm=None,key=None,diagnostics=False):
        """Lowest min(k,n) eigenpairs of one field-parity sector of op (dense for n<=650)."""
        h=op.linear_operator(w,L,f);n=h.shape[0];t=time.perf_counter();res=orth=0.
        if n<=650:
            # Preserve the original dense threshold for small blocks.
            kk=min(k,n)
            key_local=(w.tobytes(),L.tobytes())
            if getattr(op,'_dense_key',None)!=key_local:
                op._dense_key=key_local;op._dense_base={}
            if f not in op._dense_base:
                old_hbk=op.hbk
                try:
                    op.hbk=op.hb0[op.keep]
                    op._dense_base[f]=h@np.eye(n)
                finally:
                    op.hbk=old_hbk
            H=op._dense_base[f].copy()
            H.flat[::n+1]+=np.repeat(op.hbk-op.hb0[op.keep],op.nz)
            ww,vv=eigh(H,subset_by_index=(0,kk-1),check_finite=False,driver='evr')
        else:
            kk=min(k,n-1);hs=op.linear_operator(w,L,f,1.23456789)
            v0=warm.get(key) if warm is not None else None
            if v0 is None:v0=np.random.default_rng(4901+f).normal(size=n)
            ww,vv=eigsh(hs,k=kk,which='SA',tol=self.eig_tol,
                ncv=min(n,max(self.ncv,4*kk+4)),maxiter=self.max_eig_iter,v0=v0)
            ww+=1.23456789;order=np.argsort(ww);ww=ww[order];vv=vv[:,order]
        self.timings['eigensolver']+=time.perf_counter()-t
        if warm is not None:warm[key]=vv@np.linspace(1.,.6,kk)
        if diagnostics:
            res=float(np.max(np.linalg.norm(h@vv-vv*ww[None,:],axis=0)))
            orth=float(np.max(abs(vv.T@vv-np.eye(kk))))
        return ww,vv,res,orth

    def spectrum(self,theta,k=4,diagnostics=False):
        w,L,U,info=self.prepare(theta)
        out={};maxres=0.;maxorth=0.;self.calls+=1
        kk={f:min(k,n-1) for f,n in ((0,self.op.dim),(1,self.op.dim))}
        if self.win is not None:
            out['window'],info['window']=self.window_spectrum(w,L,kk[0],out)
        for f in (0,1):
            if f in out:continue
            # The original solver always requests min(k,n-1) pairs, dense or not.
            ww,vv,res,orth=self.sector_solve(self.op,w,L,f,kk[f],self.warm,f,diagnostics)
            maxres=max(maxres,res);maxorth=max(maxorth,orth);out[f]=(ww,vv)
        if diagnostics and self.win is not None:
            for f in (0,):
                h=self.op.linear_operator(w,L,f);ww,vv=out[f]
                maxres=max(maxres,float(np.max(np.linalg.norm(h@vv-vv*ww[None,:],axis=0))))
                maxorth=max(maxorth,float(np.max(abs(vv.T@vv-np.eye(vv.shape[1])))))
        info['max_eigenvector_residual']=maxres;info['max_orthogonality_residual']=maxorth
        residual=np.array([out[1][0][0]-out[0][0][0]-self.delta,out[1][0][1]-out[0][0][0]-(2-self.delta)])
        return residual,info,out,U

    def window_spectrum(self,w,L,k0,out):
        """Reuse only exactly equal local matrices at unchanged x/basis/regulator.

        This is especially useful for the final five/six-root and density checks.
        No changed-coupling window is ever accepted from this cache.
        """
        cache=self._window_cache
        if cache is not None and np.array_equal(cache['w'],w) and np.array_equal(cache['L'],L):
            self.window_cache_hits+=1
            state=cache['state'];info=dict(cache['summary'])
            self.op.set_bath_shift(state['D'][self.basis.N])
            ww,vv=cache['even']
            if len(ww)<k0:
                ww,vv,_,_=self.sector_solve(self.op,w,L,0,k0,self.warm,0)
                if self.win.mode=='consistent':
                    defect=float(ww[0])-state['Ev'][self.win.top]
                    if not converged(defect,state['Ev'][self.win.top],self.win.tol):
                        self._window_cache=None
                        raise WindowError('Exact-window cache expanded-root check failed')
                cache['even']=(ww,vv)
            out[0]=(ww[:k0],vv[:,:k0]);info['reused_exact_window']=True
            info['seconds']=0.
            return state,info
        state,info=self._window_spectrum_uncached(w,L,k0,out)
        self._window_cache={'w':w.copy(),'L':L.copy(),'state':state,
                            'summary':dict(info),'even':out[0]}
        info['reused_exact_window']=False
        return state,info

    def _window_spectrum_uncached(self,w,L,k0,out):
        """Window table at this theta, main bath shift, and the field-0 spectrum (fixed point if consistent)."""
        t=time.perf_counter();win=self.win;levels=self.basis.N;top_iter=1;top_res=0.
        Ev,vac=win.sublevels(w,L,self.sector_solve)
        if win.mode=='literal':
            self.op.set_bath_shift(None)
            e,vv,_,_=self.sector_solve(self.op,w,L,0,1,win.warm,'top')
            Ev[win.top]=s=float(e[0]);top=vv[:,0]
            self.op.set_bath_shift(win.shift(levels,s,Ev,win.cut))
            ww,vv,_,_=self.sector_solve(self.op,w,L,0,k0,self.warm,0)
        else:
            s=win.top_guess if win.top_guess is not None else Ev[win.top-2] if win.top>=2 else 0.
            for top_iter in range(1,win.maxiter+1):
                self.op.set_bath_shift(win.shift(levels,s,{**Ev,win.top:s},win.cut))
                ww,vv,_,_=self.sector_solve(self.op,w,L,0,1 if self.ground_only else k0,
                    win.warm if self.ground_only else self.warm,'top' if self.ground_only else 0)
                p0=float(self.op.level_weights(vv[:,0])[0]);F=float(ww[0])-s;top_res=abs(F)
                if converged(F,s,win.tol):break
                if not p0>1e-12:raise WindowError('Window fixed point at the cutoff: vanishing bath-vacuum weight')
                s+=F/p0
            else:raise WindowError(f'Window fixed point at the cutoff did not converge (residual {top_res:.3e})')
            Ev[win.top]=s;win.top_guess=s;top=vv[:,0]
            if self.ground_only and k0>1:
                ww,vv,_,_=self.sector_solve(self.op,w,L,0,k0,self.warm,0)
                top_res=abs(float(ww[0])-s)
                if not converged(float(ww[0])-s,s,win.tol):
                    raise WindowError('Expanded even spectrum failed the unchanged vacuum fixed-point gate')
                top=vv[:,0]
        tw=self.op.level_weights(top)
        vac['top']={'vector':top,'p0':float(tw[0]),'weights':tw}
        out[0]=(ww,vv)
        summary={'prescription':'full-vacuum window, D(N)=Ev(cut)-Ev(cut-N)','mode':win.mode,
            'D_by_N':win.d_table(Ev),'Ev':{str(a):float(b) for a,b in sorted(Ev.items())},
            'sublevel_iterations':win.last_iterations,'sublevel_fixed_point_residuals':win.last_residuals,
            'top_iterations':top_iter,'top_fixed_point_residual':top_res,'fixed_point_tolerance':win.tol,
            'seconds':time.perf_counter()-t,'setup_seconds':win.setup_seconds,'operator_storage_bytes':win.nbytes}
        win.seconds+=summary['seconds']
        return {'Ev':dict(Ev),'vac':vac,'D':win.d_vector(Ev)},summary

    def response_jacobian(self,theta,out,Uref,step_scale=1e-5):
        t=time.perf_counter()
        con=[self.op.contractions(out[f][1][:,j],f) for f,j in ((0,0),(1,0),(1,1))]
        state=out.get('window')
        if state is not None:
            # Hellmann-Feynman for the theta-dependent window shift, on the stored vacuum vectors.
            lw=[self.op.level_weights(out[f][1][:,j]) for f,j in ((0,0),(1,0),(1,1))]
            vcon={lev:self.win.ops[lev].contractions(d['vector'],0) for lev,d in state['vac'].items() if lev!='top'}
            tcon=self.op.contractions(state['vac']['top']['vector'],0)
        jac=np.empty((2,2))
        for j in range(2):
            h=step_scale*max(1,abs(theta[j]));vals=[];loc=[]
            for sign in (1,-1):
                th=np.array(theta);th[j]+=sign*h
                w,L,U,info=self.local_problem.evaluate(self.delta,th)
                signs=np.sign(np.sum(U*Uref,axis=0));signs[signs==0]=1
                L=L*signs[None,:,None]*signs[None,None,:]
                vals.append(np.array([weights@w+np.sum(corr*L)+bath for weights,corr,bath in con]));loc.append((w,L))
            dp=(vals[0]-vals[1])/(2*h)
            if state is not None:
                d=lambda c:((c[0]@loc[0][0]+np.sum(c[1]*loc[0][1]))-(c[0]@loc[1][0]+np.sum(c[1]*loc[1][1])))/(2*h)
                dD=self.win.derivative(state,{lev:d(c) for lev,c in vcon.items()},d(tcon),state['vac']['top']['weights'])
                dp=dp+np.array([x@dD for x in lw])
            jac[:,j]=dp[1:]-dp[0]
        self.timings['jacobian']+=time.perf_counter()-t
        return jac

    def solve(self,guess=None,tol=5e-10,maxiter=30,diagnostics=True):
        if self.angular!=0:raise ValueError('Primary tuning requires angular=0; use separate J-sector operators for diagnostics')
        theta=self.initial(2-4*self.delta) if guess is None else np.array(guess,dtype=float)
        history=[];start=time.perf_counter();calls=self.calls;cache=None
        for it in range(maxiter):
            f,info,out,U=self.spectrum(theta,k=3) if cache is None else cache
            err=float(max(abs(f)));history.append({'iteration':it,'theta':theta.tolist(),'residual':err})
            if self.checkpoint:self.checkpoint(theta,history)
            if err<tol:break
            jac=self.response_jacobian(theta,out,U)
            history[-1]['jacobian_condition']=float(np.linalg.cond(jac))
            dtheta=np.linalg.solve(jac,-f);accepted=False
            for ls in range(14):
                test=theta+dtheta*2**(-ls)
                if abs(test[1])>20:continue
                try:new=self.spectrum(test,k=3)
                except WindowError:continue          # an extreme trial point is rejected like a larger residual
                if np.linalg.norm(new[0])<np.linalg.norm(f):theta=test;cache=new;accepted=True;break
            if not accepted:raise RuntimeError(f'No descent delta={self.delta} residual={err}')
        else:raise RuntimeError(f'No convergence delta={self.delta}')
        f,info,out,U=self.spectrum(theta,k=5,diagnostics=True)
        ev=out[0][0];od=out[1][0]
        if max(abs(f))>max(1e-10,5*tol):raise RuntimeError('Expanded eigenpair gate failed')
        if info['max_eigenvector_residual']>self.residual_tol:raise RuntimeError('Eigenvector residual gate failed')
        if info['max_orthogonality_residual']>1e-9:raise RuntimeError('Eigenvector orthogonality gate failed')
        bound=[];bweight=[]
        for ff,jj in ((0,0),(1,0),(0,1),(1,1)):
            v=out[ff][1][:,jj].reshape(self.op.nB,self.nz)
            bound.append(float(np.sum(v[:,-2:]**2)))
            edge=self.basis.N[self.op.keep]>=self.bath_cut-1
            bweight.append(float(np.sum(v[edge]**2)))
        row={'spacetime_dimension':2,'s':2-2*self.delta,'delta':self.delta,'epsilon':2-4*self.delta,'Delta_thermal':float(ev[1]-ev[0]),
            'Delta_sigma_measured':float(od[0]-ev[0]),'Delta_shadow_measured':float(od[1]-ev[0]),
            'even_gaps':(ev-ev[0]).tolist(),'odd_gaps':(od-ev[0]).tolist(),'bath_cut':self.bath_cut,
            'nz_per_parity':self.nz,'auxiliary_oscillator_size':self.osc,'theta':theta.tolist(),
            'dimension':2*self.op.dim,'tuning_residual':float(max(abs(f))),
            'local_retained_edge_weights':bound,'bath_edge_weights':bweight,
            'seconds':time.perf_counter()-start,'spectral_evaluations':self.calls-calls,'history':history,
            'regulator':'Circle bath total N<=L times local basis; J=0 and spatial reflection even for primaries',
            'scope':('Finite-cutoff raw Hamiltonian only. No claim of complete physical matching.' if self.win is None else
                'Finite-cutoff Hamiltonian plus the opt-in full-vacuum window shift D(N); no other matching.'),
            'window':'none' if self.win is None else self.window,
            'solver':'factorized operator; moving-subspace reduced-density response Jacobian',
            'backend':self.backend,'timings':dict(self.timings),'matvec_count':self.op.matvec_count,
            'matvec_seconds':self.op.matvec_seconds,'operator_storage_bytes':self.op.nbytes}
        if self.win is not None:
            row['window_correction']=info.pop('window')
            row['window_correction']['cumulative_seconds']=self.win.seconds
        row['window_exact_cache_hits']=self.window_cache_hits
        row.update(info);return row
