"""Matrix-free state-specific finite-parent Schur elimination.

Research/validation tool, not an analytic infinite-shell matching kernel.
Keeps the entire finite parent basis and edges, but no d x d Hamiltonian blocks
and no high x low self-energy matrices. Memory is O(parent states * order).
"""
from __future__ import annotations
import time
import numpy as np
from ._core.operators import Space,quotient_components
from ._core.solver import calibrate,fixed_wave,extract,seed
from ._core.kernels import solve_wave


def action(space,x,k,r,g,p):
    m,v=space.vertices(x,k-1,parity=p%2)
    rhs=space.F1*x[:,k-1]
    for j in range(1,k+1):rhs+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
    return rhs


def state_schur(space,p,low,degree,r,g,naive=False):
    """Apply the energy-dependent eliminated-state recurrence to ONE low state.

    Q psi_n = RQ [Q H_pert psi_<n - sum_{j<n} E_j Q psi_{n-j}].
    P psi_n = RP [P H_pert psi_<n - sum_{j<=n} E_j P psi_{n-j}].
    Q feedback at order n depends on already known Q psi at orders <n. Thus no
    dense K(E):low->high matrix is needed. All HQQ insertions/folded energy terms
    are retained by the coefficient recursion.
    """
    lowmask=space.Efree<=low
    psi=seed(space,p,degree);E=np.r_[p/4,np.zeros(degree)];feedback=np.zeros(degree+1)
    for k in range(1,degree+1):
        xp=psi[:,:k].copy();xp[~lowmask]=0.
        rp=action(space,xp,k,r,g,p);del xp
        if naive:rq=np.zeros(space.dim)
        else:
            xq=psi[:,:k].copy();xq[lowmask]=0.
            rq=action(space,xq,k,r,g,p);del xq
        feedback[k]=space.sample(rq,p)
        rhs=rp+rq;del rp,rq
        E[k]=space.sample(rhs,p)
        solve_wave(rhs,psi,E,k,p,space.P,space.N)
        if naive:psi[~lowmask,k]=0.
    return E,feedback


def compare(low,parent,degree=7,memory_limit_gib=2.):
    if degree not in (4,5,6,7) or low<2 or low>=parent or low%2 or parent%2:raise ValueError('even low<parent; degree 4--7')
    start=time.perf_counter();order=degree//2
    s=Space(parent,3+4*order,4*order,degree-1,memory_limit_gib=memory_limit_gib)
    psis,_,r,g=calibrate(s,order);components={}
    for p in (0,1,3,2):
        psi=psis.pop(p) if p in psis else fixed_wave(s,p,order,r,g)[0]
        F,M,V=quotient_components(s,psi,degree,parity=p%2);del psi
        components[p]=dict(F=F.tolist(),M=M.tolist(),V=V.tolist())
    parent_result,_=extract(components,[0,1,3,2],degree)
    r=np.array(parent_result['r']);g=np.array(parent_result['g'])
    full={};matched={};naive={};feedback={}
    for p in (0,1,2,3):
        psi,full[p]=fixed_wave(s,p,degree,r,g);del psi
        matched[p],feedback[p]=state_schur(s,p,low,degree,r,g)
        naive[p],_=state_schur(s,p,low,degree,r,g,naive=True)
    cf=full[2]-full[0];cm=matched[2]-matched[0];cn=naive[2]-naive[0]
    err=max(float(np.max(abs(full[p]-matched[p]))) for p in full)
    oracle=float(np.max(abs(cf-np.array(parent_result['C']))))
    if err>1e-7 or oracle>1e-7:raise ArithmeticError('Finite-parent matching validation failed')
    counts={str(par):dict(parent=int(np.sum((s.P%2==par)&s.even)),retained=int(np.sum((s.P%2==par)&s.even&(s.Efree<=low)))) for par in (0,1)}
    return dict(low=low,parent=parent,degree=degree,counts=counts,parent_C=cf.tolist(),matched_C=cm.tolist(),
                naive_low_same_parent_couplings_C=cn.tolist(),parent_r=r.tolist(),parent_g=g.tolist(),
                high_state_feedback={str(p):f.tolist() for p,f in feedback.items()},
                max_parent_matched_energy_difference=err,max_parent_recursion_quotient_difference=oracle,
                seconds=time.perf_counter()-start,basis_dimension=s.global_dim,edges_bytes=s.edges_bytes,
                scope='State-specific finite-parent elimination, same parent couplings. NOT infinite-shell physical matching; parent basis is still explicitly allocated.',
                dtype='float64',fastmath=False,algorithm='matrix-free-state-Schur')
