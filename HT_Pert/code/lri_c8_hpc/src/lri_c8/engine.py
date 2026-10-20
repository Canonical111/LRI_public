"""C8 via cubic trial state plus exact fourth-residual free-resolvent contraction."""
from __future__ import annotations
import time, resource, gc
import numpy as np
from ._core.operators import Space,quotient_components
from ._core.solver import extract,second_order_shell_value,vacuum_quotient
from ._reference_solver import compute as reference_compute, fixed_wave, Vacuum
from .residual import OuterSpace,resolvent_norm
from .packed import PackedCore
from ._core.kernels import solve_wave

def cubic_wave(space,p,r,g,vac):
    psi=space.seed(p,3);E=np.r_[p/4,np.zeros(3)]
    for k in range(1,4):
        m,v=space.vertices(psi[:,:k],k-1,parity=p%2)
        t=space.F1*psi[:,k-1]
        for j in range(1,k+1):t+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
        if vac is not None:t+=vac.action_coeff(psi[:,:k],k,g)
        E[k]=space.sample(t,p)
        solve_wave(t,psi,E,k,p,space.P,space.N)
    return psi,E

REFERENCES=(0,1,3,2)

def low_calibration(cutoff,scheme):
    low=reference_compute(cutoff,degree=4,scheme=scheme)
    return {'r':low['r'],'g':low['g'],
            'energies':{str(p):low['energies'][low['reference_order'].index(p)] for p in (0,1,3)},
            'C':low['C']}

def component(core,outer,p,low,scheme):
    t0=time.perf_counter();r=np.array(low['r']);g=np.array(low['g'])
    if r[1]!=0. or abs(g[1]-1/3)>1e-15:raise ValueError('Unsupported leading coupling calibration')
    vac=Vacuum(core,6) if scheme=='vacuum_only' else None
    psi,E=cubic_wave(core,p,r,g,vac)
    wave_seconds=time.perf_counter()-t0
    m,v=core.vertices(psi,3,parity=p%2)
    t=core.F1*psi[:,3]
    for j in range(1,5):t+=r[j]*m[:,4-j]+g[j]*v[:,4-j]
    if vac is not None:t+=vac.action_coeff(psi,4,g)
    for j in range(1,4):t-=E[j]*psi[:,4-j]
    inside=resolvent_norm(t,core.P,core.N,p)
    del m,v,t
    t1=time.perf_counter()
    F,M,V=quotient_components(core,psi,8,parity=p%2)
    c={'F':F.tolist(),'M':M.tolist(),'V':V.tolist()}
    if vac is not None:c['K']=vacuum_quotient(core,psi,6).tolist()
    quotient_seconds=time.perf_counter()-t1
    t1=time.perf_counter();outside=outer.correction(core,psi[:,3],p,g[1])
    c['F'][8]+=inside+outside
    c['residual_inside']=inside;c['residual_outside']=outside
    c['reference']=p
    c['timing']={'wave':wave_seconds,'quotient':quotient_seconds,'outside':time.perf_counter()-t1,'total':time.perf_counter()-t0}
    if not all(np.isfinite(c[k]).all() for k in ('F','M','V')):raise ArithmeticError('nonfinite component')
    return c

def assemble(components,low,cutoff,scheme):
    if set(components)!=set(REFERENCES):raise ValueError('All four distinct references required')
    out,E=extract(components,list(REFERENCES),8,corrected=scheme=='vacuum_only')
    shell=out['C'][2]-second_order_shell_value(cutoff)
    low_res=max(np.max(abs(np.array(out[k])[:5]-np.array(low[k]))) for k in ('r','g'))
    for p in (0,1,3):low_res=max(low_res,np.max(abs(E[list(REFERENCES).index(p),:5]-low['energies'][str(p)])))
    out.update(cutoff=cutoff,degree=8,scheme=scheme,energies=E.tolist(),reference_order=list(REFERENCES),
               second_order_shell_residual=float(shell),low_order_residual=float(low_res),
               particle_cap=19,nonzero_particle_cap=16,core_particle_cap=15,core_nonzero_particle_cap=12,
               dtype='float64',fastmath=False,
               scope='Same frozen-cutoff coefficients. raw and isolated g^2D only; no Dconn or physical extrapolation.')
    validate_result(out)
    return out

def validate_result(out):
    if out.get('degree')!=8 or out.get('scheme') not in ('raw','vacuum_only'):raise ValueError('Wrong C8 prescription')
    for key in ('second_order_shell_residual','low_order_residual','tuning_residual'):
        if not np.isfinite(out[key]):raise ArithmeticError('Nonfinite diagnostic')
    if out.get('cutoff',0)<2 or out['cutoff']%2:raise ValueError('Invalid cutoff')
    for k in ('C','r','g'):
        a=np.asarray(out[k]);
        if a.shape!=(9,) or not np.isfinite(a).all():raise ArithmeticError('Invalid '+k)
    E=np.asarray(out['energies']);
    if E.shape!=(4,9) or not np.isfinite(E).all():raise ArithmeticError('Invalid energies')
    refs=out['reference_order']
    if refs!=list(REFERENCES):raise ArithmeticError('wrong reference order')
    spin=np.array([.25,-.25]+[0.]*7);shadow=np.array([.75,.25]+[0.]*7)
    tuning=max(np.max(abs(E[1]-E[0]-spin)),np.max(abs(E[2]-E[0]-shadow)))
    shell=abs(out['C'][2]-second_order_shell_value(out['cutoff']))
    if shell>1e-10 or tuning>1e-6 or out['low_order_residual']>1e-7:raise ArithmeticError('Acceptance failure')
    if not np.allclose(E[3]-E[0],out['C'],atol=1e-8,rtol=2e-14):raise ArithmeticError('Thermal assembly inconsistent')
    if out['particle_cap']!=19 or out['nonzero_particle_cap']!=16:raise ArithmeticError('Insufficient physical caps')

def compute(cutoff,scheme='raw',outer_backend='stored',references=REFERENCES,low=None,
            saved_components=None,on_low=None,on_component=None,memory_limit_gib=None):
    if cutoff<2 or cutoff%2:raise ValueError('Even cutoff >=2 required')
    if scheme not in ('raw','vacuum_only'):raise ValueError('Unknown prescription')
    if len(set(references))!=len(references) or any(p not in REFERENCES for p in references):raise ValueError('Invalid references')
    start=time.perf_counter()
    components={} if saved_components is None else dict(saved_components)
    remaining=[p for p in references if p not in components]
    if memory_limit_gib is not None and remaining:
        from .planning import plan
        est=plan(cutoff,outer_backend)
        if est['conservative_gib']>memory_limit_gib:raise MemoryError('Conservative plan exceeds --memory-limit-gib')
    if low is None:
        low=low_calibration(cutoff,scheme)
        if on_low:on_low(low)
    caltime=time.perf_counter()-start
    stats={}
    if remaining:
        core=PackedCore(cutoff)
        outer=OuterSpace(cutoff,core.dim,outer_backend,core.rows)
        for p in remaining:
            c=component(core.sector(p),outer,p,low,scheme);components[p]=c
            if on_component:on_component(p,c)
        stats={'core_dimension':core.dim,'basis_dimension':outer.dim,'core_edges_bytes':core.edges_bytes,
               'outer_storage_bytes':outer.bytes,'outer_edges':outer.nedges,'outer_build_seconds':outer.build_seconds,
               'core_phase_seconds':core.timings,'core_ladder_calls':core.ladder_calls,
               'outer_creation_calls':outer.calls,'outer_seconds':outer.seconds}
    out=assemble(components,low,cutoff,scheme) if set(components)==set(REFERENCES) else {}
    if 'basis_dimension' in stats:
        dimension=stats['basis_dimension']
    else:
        from .planning import counts
        dimension=counts(cutoff,19,16)['dim']
    out.update(basis_dimension=dimension,wavefunction_order_stored=3,
               method='cubic-Rayleigh-plus-fourth-residual',
               components={str(k):v for k,v in components.items()},low=low,stats=stats,
               seconds=time.perf_counter()-start,calibration_seconds=caltime,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return out
