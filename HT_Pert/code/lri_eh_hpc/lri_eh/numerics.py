"""Shared-wavefunction evaluation of the isolated vacuum correction.

Float64 throughout. No fastmath, threshold sparsification or physical-model
change. Raw high-order spectra in the reduced basis are deliberately not exported.
"""
from __future__ import annotations
import math
import time
from typing import Callable
import numpy as np
from numba import njit, prange
from ._core.operators import Space, quotient_components, divide_series
from ._core.solver import calibrate, fixed_wave, extract, vacuum_table, second_order_shell_value
from .exact import fast as exact_c4


def pad(a, n):
    out = np.zeros(n+1, dtype=np.float64)
    out[:min(len(a),n+1)] = a[:n+1]
    return out


def mul(a,b,n):
    return pad(np.convolve(a,b),n)


def shift(a,k,n):
    out=np.zeros(n+1)
    if k<=n: out[k:]=pad(a,n-k)
    return out


@njit(cache=True, parallel=True, fastmath=False)
def vacuum_blocks(psi, N, P, cutoff, table, degree, block_size=4096):
    """Fused lookup/contraction: no dense diagonal jet arrays are materialized."""
    nb=(len(N)+block_size-1)//block_size
    out=np.zeros((nb,degree+1),dtype=np.float64)
    for block in prange(nb):
        lo=block*block_size; hi=min(len(N),lo+block_size)
        for row in range(lo,hi):
            upper=max(0,(4*cutoff-4*N[row]-P[row])//4)
            if upper==cutoff: continue
            for a in range(min(psi.shape[1],degree+1)):
                av=psi[row,a]
                if av==0.:continue
                for b in range(min(psi.shape[1],degree-a+1)):
                    bv=psi[row,b]
                    if bv==0.:continue
                    ab=av*bv
                    for j in range(degree-a-b+1):
                        out[block,a+b+j]-=ab*(table[cutoff,j]-table[upper,j])/6
    return out


@njit(cache=True, parallel=True, fastmath=False)
def response_wave(psi,N,P,cutoff,p,g1,table0):
    out=np.zeros((len(N),1),dtype=np.float64)
    for i in prange(len(N)):
        den=p*.25-P[i]*.25-N[i]
        if N[i]%2==0 and P[i]%2==p%2 and den!=0.:
            upper=max(0,(4*cutoff-4*N[i]-P[i])//4)
            d0=-(table0[cutoff,0]-table0[upper,0])/6
            out[i,0]=g1*g1*d0*psi[i,1]/den
    return out


def vacuum_expectation(space,psi,degree,norm=None):
    t=time.perf_counter()
    if norm is None:norm=space.inner(psi,psi,degree)
    tab=vacuum_table(space.cutoff,degree)
    blocks=vacuum_blocks(psi,space.N,space.P,space.cutoff,tab,degree)
    numerator=np.array([math.fsum(blocks[:,k]) for k in range(degree+1)])
    space.timings['vacuum']=space.timings.get('vacuum',0.)+time.perf_counter()-t
    return divide_series(numerator,norm,degree)


def paired_numerators(space,psi,chi,base,degree,p):
    """Stream B^j psi and B^j chi: eight ladder sweeps, not four plus nine.

    All cross terms retain operator ordering via Hermitian conjugation only.
    Quadratic chi terms are needed only at degree seven (coupling starts at eps).
    """
    q=base-1; crossdegree=degree-4; quaddegree=degree-7
    opposite=1-p%2; parity=p%2
    b1=space.linear(psi,q,parity=parity)
    c1=space.linear(chi,crossdegree,parity=parity)
    m=2*space.inner(b1,b1,q)
    mc=2*space.inner(b1,c1,crossdegree)
    mq=2*space.inner(c1,c1,quaddegree) if quaddegree>=0 else np.zeros(1)
    b2=space.linear(b1,q,parity=opposite)
    c2=space.linear(c1,crossdegree,parity=opposite)
    m+=2*space.inner(psi,b2,q)
    mc+=space.inner(b2,chi,crossdegree)+space.inner(psi,c2,crossdegree)
    v=.5*space.inner(b2,b2,q)
    vc=.5*space.inner(b2,c2,crossdegree)
    if quaddegree>=0:
        mq+=2*space.inner(chi,c2,quaddegree)
        vq=.5*space.inner(c2,c2,quaddegree)
    else:vq=np.zeros(1)
    b3=space.linear(b2,q,parity=parity);del b2
    c3=space.linear(c2,crossdegree,parity=parity);del c2
    v+=(2/3)*space.inner(b1,b3,q)
    vc+=(space.inner(b3,c1,crossdegree)+space.inner(b1,c3,crossdegree))/3
    if quaddegree>=0:vq+=(2/3)*space.inner(c1,c3,quaddegree)
    del b1,c1
    b4=space.linear(b3,q,parity=opposite);del b3
    c4=space.linear(c3,crossdegree,parity=opposite);del c3
    v+=space.inner(psi,b4,q)/6
    vc+=(space.inner(b4,chi,crossdegree)+space.inner(psi,c4,crossdegree))/12
    if quaddegree>=0:vq+=space.inner(chi,c4,quaddegree)/6
    return m,v,2*shift(mc,3,degree-1)+shift(mq,6,degree-1),2*shift(vc,3,degree-1)+shift(vq,6,degree-1)


def components_for_reference(space,psi,p,degree,g1):
    """Low-order raw quotients plus exact high-order quotient differences.

    psi_plus=psi+eps^3 chi. Degree <=7 needs the raw couplings only through d-3.
    delta Q = (delta numerator - Q_raw delta norm)/(norm+delta norm).
    No subtraction of two complete O(1e5) seventh-order energies.
    """
    base=max(degree//2,degree-3)
    norm=space.inner(psi,psi,degree)
    fnum=space.inner(psi,psi,base,space.Efree)
    fnum[1:]+=space.inner(psi,psi,base-1,space.F1)
    f=divide_series(fnum,norm,base)
    dnorm=np.zeros(degree+1)
    df=np.zeros(degree+1);dm=np.zeros(degree+1);dv=np.zeros(degree+1)
    if degree>=6:
        chi=response_wave(psi,space.N,space.P,space.cutoff,p,g1,vacuum_table(space.cutoff,0))
        # chi is the coefficient of eps^3 in the change of trial wavefunction.
        dnorm=2*shift(space.inner(psi,chi,degree-3),3,degree)
        dnorm+=shift(space.inner(chi,chi,degree-6),6,degree)
        dnum=2*shift(space.inner(psi,chi,degree-3,space.Efree),3,degree)
        dnum+=shift(space.inner(chi,chi,degree-6,space.Efree),6,degree)
        dnum+=2*shift(space.inner(psi,chi,degree-4,space.F1),4,degree)
        if degree>=7:dnum+=shift(space.inner(chi,chi,degree-7,space.F1),7,degree)
        df=divide_series(dnum-mul(f,dnorm,degree),norm+dnorm,degree)
        mn,vn,dmn,dvn=paired_numerators(space,psi,chi,base,degree,p)
        m=divide_series(mn,norm,base);v=divide_series(vn,norm,base)
        dm=divide_series(dmn-mul(m,dnorm,degree-1),norm+dnorm,degree-1)
        dv=divide_series(dvn-mul(v,dnorm,degree-1),norm+dnorm,degree-1)
        psi[:,3]+=chi[:,0]
        del chi
    else:
        _,m,v=quotient_components(space,psi,base,parity=p%2)
    k=vacuum_expectation(space,psi,degree-2,norm+dnorm)
    return dict(F=f.tolist(),M=m.tolist(),V=v.tolist(),dF=df.tolist(),
                dM=dm.tolist(),dV=dv.tolist(),K=k.tolist())


def extract_difference(components,degree):
    """Retune only the differences. A triangular series calculation, not fitting."""
    refs=[0,1,3,2]
    base=max(degree//2,degree-3)
    raw,_=extract(components,refs,base,False)
    r=pad(raw['r'],degree);g=pad(raw['g'],degree)
    dr=np.zeros(degree+1);dg=np.zeros(degree+1)
    de=np.zeros((4,degree+1))
    for k in range(1,degree+1):
        gg=mul(g+dg,g+dg,degree)
        for ip,p in enumerate(refs):
            c=components[p]
            dm=pad(c['dM'],degree);dv=pad(c['dV'],degree)
            # Missing raw M/V coefficients multiply dr,dg starting at eps^4;
            # max required is degree-4 <=3 and is present in base quotients.
            mp=pad(c['M'],degree)+dm;vp=pad(c['V'],degree)+dv
            de[ip,k]=(pad(c['dF'],degree)+mul(r,dm,degree)+mul(g,dv,degree)
                       +mul(dr,mp,degree)+mul(dg,vp,degree)+mul(gg,c['K'],degree))[k]
        dr[k]=-(de[1,k]-de[0,k])/2
        dg[k]=-(de[2,k]-de[0,k]+6*dr[k])/3
        for ip,p in enumerate(refs):
            de[ip,k]+=2*p*dr[k]+p*(p-1)/2*dg[k]
    res=max(np.max(np.abs(de[1]-de[0])),np.max(np.abs(de[2]-de[0])))
    return dict(delta_C=(de[3]-de[0]).tolist(),delta_r=dr.tolist(),delta_g=dg.tolist(),
                validation=dict(max_raw_vacuum_shell_residual=float(abs(raw['C'][2]-second_order_shell_value(components['_cutoff']))),
                                max_tuning_residual=float(max(res,raw['tuning_residual'])),
                                response_tuning_residual=float(res)))


def compute(cutoff:int,degree:int=7,memory_limit_gib:float|None=None,
            checkpoint:dict|None=None,save:Callable[[dict],None]|None=None,
            phase:Callable[[str],None]|None=None):
    """Single-process, threaded numerical engine. Scheduling is in runner.py.

    Checkpoint contains scalar data only; completed references are not repeated.
    The scheduler validates source/configuration and checkpoint integrity.
    """
    if degree not in (4,5,6,7):raise ValueError('degree must be 4,5,6,7')
    if cutoff<4 or cutoff%2:raise ValueError('even cutoff >=4 required')
    cp={} if checkpoint is None else checkpoint
    save=(lambda x:None) if save is None else save
    phase=(lambda x:None) if phase is None else phase
    reach=(degree-2)//2;pmax=3+4*reach;qmax=4*reach;order=degree//2
    start=time.perf_counter()
    if 'low' in cp and set(cp.get('components',{}))=={'0','1','2','3'}:
        # A preemption after the final reference checkpoint must not rebuild a
        # hundreds-of-millions-state basis just to perform scalar extraction.
        phase('extraction_from_completed_checkpoint')
        components={int(p):v for p,v in cp['components'].items()};components['_cutoff']=cutoff
        out=extract_difference(components,degree)
        out['validation']['exact_delta_C4_residual']=abs(out['delta_C'][4]-exact_c4(cutoff))
        out['validation']['lower_order_invariance_residual']=float(max(abs(x) for k in ('delta_C','delta_r','delta_g') for x in out[k][:4]))
        from .planner import plan
        planned=plan(cutoff,degree)
        out.update(cutoff=cutoff,degree=degree,particle_cap=pmax,nonzero_particle_cap=qmax,
                   basis_dimension=planned['basis_dimension'],edges_bytes=planned['exact_edge_bytes'],
                   seconds=time.perf_counter()-start,ladder_calls=0,timings={'basis':0.,'calibration':0.},
                   reference_seconds=cp.get('reference_seconds',{}),dtype='float64',fastmath=False,
                   reused_completed_components=True,
                   scope='Complete paired difference for isolated g(eps)^2 D(eps), both gaps retuned; NOT complete physical matching.',
                   prescription_change='raw -> isolated g(eps)^2 D(eps), both primary gaps retuned')
        return out
    phase('basis')
    space=Space(cutoff,pmax,qmax,max(degree-4,order-1),memory_limit_gib=memory_limit_gib,compact_single=True)
    t=time.perf_counter();phase('calibration')
    if 'low' in cp:
        r=np.array(cp['low']['r']);g=np.array(cp['low']['g']);psis={}
    else:
        psis,elow,r,g=calibrate(space,order)
        cp['low']={'r':r.tolist(),'g':g.tolist(),'E':{str(p):e.tolist() for p,e in elow.items()}}
        save(cp)
    calibration_seconds=time.perf_counter()-t
    cp.setdefault('components',{})
    for p in (0,1,3,2):
        key=str(p)
        if key in cp['components']:
            psis.pop(p,None);continue
        phase(f'reference_{p}');t=time.perf_counter()
        psi=psis.pop(p) if p in psis else fixed_wave(space,p,order,r,g)[0]
        comp=components_for_reference(space,psi,p,degree,g[1]);del psi
        cp['components'][key]=comp
        cp.setdefault('reference_seconds',{})[key]=time.perf_counter()-t
        save(cp)
    phase('extraction')
    components={int(p):v for p,v in cp['components'].items()}
    components['_cutoff']=cutoff
    out=extract_difference(components,degree)
    out['validation']['exact_delta_C4_residual']=abs(out['delta_C'][4]-exact_c4(cutoff))
    out['validation']['lower_order_invariance_residual']=float(max(abs(x) for k in ('delta_C','delta_r','delta_g') for x in out[k][:4]))
    out.update(cutoff=cutoff,degree=degree,particle_cap=pmax,nonzero_particle_cap=qmax,
               basis_dimension=space.global_dim,edges_bytes=space.edges_bytes,
               seconds=time.perf_counter()-start,ladder_calls=space.ladder_calls,
               timings=dict(space.timings,calibration=calibration_seconds),
               reference_seconds=cp['reference_seconds'],dtype='float64',fastmath=False,
               scope='Complete paired difference for isolated g(eps)^2 D(eps), both gaps retuned; NOT complete physical matching.',
               prescription_change='raw -> isolated g(eps)^2 D(eps), both primary gaps retuned')
    return out
