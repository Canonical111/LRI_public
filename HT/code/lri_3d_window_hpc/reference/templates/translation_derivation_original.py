"""One-step free-conformal radial/trace enrichment in a COMMON finite parent.
No energies or residues are imposed except the original sigma and chi gaps.
The free generators are source directions, NOT assumed interacting charges.
"""
from __future__ import annotations
import math,time,json
from collections import Counter
import numpy as np
from scipy.sparse import csr_matrix
from scipy.linalg import eigh, svd
from scipy.optimize import root
from ward import WardSystem,load_seed,atomic_json
from buffer import BufferedSystem


def lowering(b):
    lookup={lab:k for k,lab in enumerate(b.labels)};r=[];c=[];d=[]
    for col,st in enumerate(b.states):
        occ=Counter(st)
        for k,num in occ.items():
            n,l,m=b.labels[k]
            if m<=-l:continue
            dst=lookup[n,l,m-1];out=list(st);out.remove(k);out.append(dst);out.sort()
            r.append(b.index[tuple(out)]);c.append(col);d.append(math.sqrt((l+m)*(l-m+1)*num*(occ.get(dst,0)+1)))
    return csr_matrix((d,(r,c)),shape=(len(b.N),len(b.N)))


def generator_bath(b,x):
    """P_0=sum a_dst^dagger a_src p_dst,src with an explicit zero-mode term."""
    labs=((0,0,0),)+b.labels;idx={lab:k for k,lab in enumerate(labs)};w=np.r_[1.,b.weights(x)]
    transitions={};zero_coeff=None;zero_mode=None
    for src,(n,l,m) in enumerate(labs):
        tg=[((n,l+1,m),(2*n+2*l+3)*math.sqrt(((l+1)**2-m*m)/(4*(l+1)**2-1)))]
        if l>0:tg.append(((n+1,l-1,m),2*(n+1)*math.sqrt((l*l-m*m)/(4*l*l-1))))
        for lab,v in tg:
            if lab not in idx:continue
            dst=idx[lab];amp=v*w[dst]/w[src]
            if src==0:zero_coeff=amp;zero_mode=dst-1
            else:transitions.setdefault(src-1,[]).append((dst-1,amp))
    rr=[];cc=[];dd=[];zr=[];zc=[];zd=[]
    for col,st in enumerate(b.states):
        if b.N[col]>=b.cutoff:continue
        occ=Counter(st)
        for src,num in occ.items():
            for dst,amp in transitions.get(src,[]):
                out=list(st);out.remove(src);out.append(dst);out.sort()
                rr.append(b.index[tuple(out)]);cc.append(col);dd.append(amp*math.sqrt(num*(occ.get(dst,0)+1-(dst==src))))
        out=tuple(sorted(st+(zero_mode,)))
        zr.append(b.index[out]);zc.append(col);zd.append(zero_coeff*math.sqrt(occ.get(zero_mode,0)+1))
    shape=(len(b.N),len(b.N))
    return csr_matrix((dd,(rr,cc)),shape=shape),csr_matrix((zd,(zr,zc)),shape=shape)


def product_term(W,A,dst,src,field):
    """Dense packed tensor matrix; used only by this small-parent reference."""
    z=dst.nz;out=np.zeros((dst.dim,src.dim))
    for pout in (0,1):
        ixout=np.flatnonzero((dst.kpar^field)==pout)
        oi=(ixout[:,None]*z+np.arange(z)).ravel()
        for pin in (0,1):
            ixin=np.flatnonzero((src.kpar^field)==pin)
            ii=(ixin[:,None]*z+np.arange(z)).ravel()
            if not len(oi) or not len(ii):continue
            block=A[pout*z:(pout+1)*z,pin*z:(pin+1)*z]
            out[np.ix_(oi,ii)]+=np.kron(W[ixout][:,ixin].toarray(),block)
    return out


def hermitian_terms(sys,j,field,local):
    op=sys.ops[j];z=sys.nz;I=np.eye(2*z);U=local[2];t=local[3]['local_scale']
    q=[I]+[U.T@(t**k*sys.local.q[k])@U for k in range(1,5)]
    from scipy.sparse import eye
    eb=eye(op.nB,format='csr')
    M=product_term(eb,q[2]-I,op,op,field)+2*product_term(op.W[0],q[1],op,op,field)+product_term(op.W[1],I,op,op,field)
    V=product_term(eb,(q[4]-6*q[2]+3*I)/12,op,op,field)
    V+=product_term(op.W[0],(q[3]-3*q[1])/3,op,op,field)
    V+=product_term(op.W[1],(q[2]-I)/2,op,op,field)
    V+=product_term(op.W[2],q[1]/3,op,op,field)+product_term(op.W[3],I/12,op,op,field)
    H=sys.operator(j,field,[0,0],local=local)@np.eye(op.dim) # local overrides placeholder theta
    return (H+H.T)/2,(M+M.T)/2,(V+V.T)/2


def enrich(core,images,tol=2e-11):
    """Numerical-rank closure: low core kept EXACTLY; discard only null images."""
    n=images.shape[0];res=images.copy();res[core]=0
    u,s,_=svd(res,full_matrices=False,check_finite=False)
    cutoff=tol*max(float(s[0]) if len(s) else 0,1.)
    keep=s>cutoff;T=u[:,keep];P=np.eye(n)[:,core]
    U=np.column_stack((P,T))
    return U,{'added_rank':int(sum(keep)),'singular_values':s.tolist(),'rank_tol':tol,
              'null_dropped_norm':float(np.max(s[~keep],initial=0)),
              'orthogonality':float(np.max(abs(U.T@U-np.eye(U.shape[1])),initial=0))}


class TraceClosure:
    def __init__(self,L=4,x=.5182,zlow=10,zparent=14,osc=128,extra=4,rank_tol=2e-11):
        self.L=L;self.x=x;self.zlow=zlow;self.zparent=zparent;self.extra=extra
        # Define the frozen local frame at couplings of the old scalar regulator.
        initial=BufferedSystem(L,zlow,osc,x,spins=(0,))
        theta,self.initial_cal=initial.solve(load_seed(L,x),'raw',tol=1e-11)
        self.theta0=theta
        self.sys=WardSystem(L+extra,zparent,osc,x,spins=(0,1,2))
        self.loc=self.sys.local_data(theta);self.rg0=np.array([self.loc[3]['r'],self.loc[3]['g']])
        self.H={};self.M={};self.V={};self.core={};self.bases={};self.meta={};self.Pgen={}
        b=self.sys.basis;Jm=lowering(b);proj={}
        for j,op in self.sys.ops.items():
            S=op.S
            for a in range(j):S=Jm@S/math.sqrt((2*j-a)*(a+1))
            proj[j]=S.tocsr() # physical M=0 representative, same spin J
            core=np.array([row*zparent+k for row,N in enumerate(op.N) if N<=L+j for k in range(zlow)],int)
            self.core[j]=core
            for f in (0,1):self.H[j,f],self.M[j,f],self.V[j,f]=hermitian_terms(self.sys,j,f,self.loc)
        B,C=generator_bath(b,x)
        # Physical oscillator a0=(t q_aux+i p_aux/t)/2 in the frozen local basis.
        o=osc;Cre=np.diag(np.sqrt(np.arange(1,o)),-1);ia=Cre.T-Cre
        U=self.loc[2];t=self.loc[3]['local_scale'];a0=U.T@((t*self.sys.local.q[1]+ia/t)/2)@U
        for dst,src in ((1,0),(0,1),(2,1)):
            W=(proj[dst].T@B@proj[src]).tocsr();Z=(proj[dst].T@C@proj[src]).tocsr()
            for f in (0,1):self.Pgen[dst,src,f]=product_term(W,np.eye(2*zparent),self.sys.ops[dst],self.sys.ops[src],f)+product_term(Z,a0,self.sys.ops[dst],self.sys.ops[src],f)
        for f in (0,1):
            R=3*self.Pgen[0,1,f]@self.Pgen[1,0,f]
            U0,m0=enrich(self.core[0],R[:,self.core[0]],rank_tol)
            U1,m1=enrich(self.core[1],self.Pgen[1,0,f]@U0,rank_tol)
            U2,m2=enrich(self.core[2],self.Pgen[2,1,f]@U1,rank_tol)
            for j,Q,meta in ((0,U0,m0),(1,U1,m1),(2,U2,m2)):
                self.bases[j,f]=Q;self.meta[j,f]=meta
        self.ranks={f'J{j}_f{f}':Q.shape[1] for (j,f),Q in self.bases.items()}
    def projected(self,scheme):
        mats={};bases={}
        for key,H in self.H.items():
            j,f=key
            if scheme=='core':Q=np.eye(H.shape[0])[:,self.core[j]]
            elif scheme=='trace':Q=self.bases[key]
            elif scheme=='parent':Q=np.eye(H.shape[0])
            else:raise ValueError(scheme)
            bases[key]=Q;mats[key]=[Q.T@a@Q for a in (H,self.M[key],self.V[key])]
        return mats,bases
    def solve(self,scheme,tol=1e-10):
        mats,bases=self.projected(scheme);hist=[]
        def diag(key,rg,k,vectors=False):
            H,M,V=mats[key];A=H+(rg[0]-self.rg0[0])*M+(rg[1]-self.rg0[1])*V
            return eigh(A,subset_by_index=(0,min(k,A.shape[0])-1),eigvals_only=not vectors,check_finite=False)
        def fun(rg):
            e=diag((0,0),rg,1)[0];o=diag((0,1),rg,2)
            f=np.array([o[0]-e-self.x,o[1]-e-(3-self.x)])
            hist.append({'rg':np.asarray(rg).tolist(),'residual':f.tolist()});return f
        sol=root(fun,self.rg0,tol=tol)
        res=fun(sol.x)
        if max(abs(res))>3e-9:raise RuntimeError('Primary calibration failed')
        states={key:diag(key,sol.x,12,True) for key in mats}
        e0=states[0,0][0][0];E=states[0,0][0];O=states[0,1][0]
        out={'scheme':scheme,'rg':sol.x.tolist(),'residuals':res.tolist(),'thermal':float(E[1]-e0),
            'sigma_radial_error':float(O[2]-O[0]-2),
            'thermal_radial_rank3_error':float(E[3]-E[1]-2),
            'sigma_J1_error':float(states[1,1][0][0]-O[0]-1),
            'sigma_J2_error':float(states[2,1][0][0]-O[0]-2),
            'thermal_J1_error':float(states[1,0][0][0]-E[1]-1),
            'stress_like_gap':float(states[2,0][0][0]-e0),
            'spectra':{f'J{j}_f{f}':(ev-e0).tolist() for (j,f),(ev,U) in states.items()},
            'dimensions':{f'J{j}_f{f}':m[0].shape[0] for (j,f),m in mats.items()},'history':hist}
        # Operator-based radial label diagnostic (does not affect basis or calibration).
        vac=bases[0,0]@states[0,0][1][:,0]
        for power,name,f in ((1,'phi',1),(2,'phi2',0)):
            src=self.sys.insertion(0,power,0,self.theta0,self.loc)@vac
            wt=np.abs((bases[0,f]@states[0,f][1]).T@src)**2
            out[name+'_weights']=wt.tolist()
        # Free generator defect in the actual interacting candidate states; never renamed a matched CFT charge.
        ds=bases[0,1]@states[0,1][1][:,0];g=self.Pgen[1,0,1]@ds
        H=self.H[1,1]+(sol.x[0]-self.rg0[0])*self.M[1,1]+(sol.x[1]-self.rg0[1])*self.V[1,1]
        out['free_P_sigma_residual']=float(np.linalg.norm(H@g-(O[0]+1)*g)/np.linalg.norm(g))
        out['free_P_sigma_norm_ratio']=float(g@g/(2*self.x))
        return out

if __name__=='__main__':
    import argparse
    from pathlib import Path
    ap=argparse.ArgumentParser();ap.add_argument('--L',type=int,default=4);ap.add_argument('--x',nargs='+',type=float,default=[.745,.6,.5182]);ap.add_argument('--zlow',type=int,default=8);ap.add_argument('--zparent',type=int,default=12);ap.add_argument('--osc',type=int,default=96);ap.add_argument('--extra',type=int,default=4);ap.add_argument('--schemes',nargs='+',default=['core','trace','parent']);a=ap.parse_args()
    for x in a.x:
        t0=time.perf_counter();s=TraceClosure(a.L,x,a.zlow,a.zparent,a.osc,a.extra)
        out={'L':a.L,'x':x,'parent_cut':a.L+a.extra,'zlow':a.zlow,'zparent':a.zparent,'osc':a.osc,'reference_theta':s.theta0.tolist(),'reference_rg':s.rg0.tolist(),'closure_ranks':s.ranks,'runs':[],
            'scope':'Common finite-parent Ritz enrichment by free conformal trace images; thermal held out. Not UV matching or exact interacting generators.'}
        for kind in a.schemes:
            r=s.solve(kind);out['runs'].append(r);print('CLOSURE',a.L,x,kind,'dim',r['dimensions'],'thermal',r['thermal'],'sigR',r['sigma_radial_error'],'thermR',r['thermal_radial_rank3_error'],'J1',r['sigma_J1_error'],'Perr',r['free_P_sigma_residual'],flush=True)
            out['seconds']=time.perf_counter()-t0;atomic_json(Path(__file__).resolve().parents[1]/'results/closure'/f'L{a.L}_x{x:.6f}_p{a.extra}_z{a.zlow}-{a.zparent}.json',out)
