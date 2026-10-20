"""Finite-cutoff solver preserving the supplied Hamiltonian and tuning.

Thermal degree 6/7; phi6 degree 3/5 in both original prescriptions. This is a
performance rewrite, NOT new matching, a different regulator, or an extrapolation.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib,json,math,os,resource,time
from pathlib import Path
import numpy as np
from .operators import Space,quotient_components,divide_series
from .kernels import solve_wave
from .parallel import global_sum

VERSION='1.0.0'

def source_fingerprint():
    h=hashlib.sha256()
    for p in sorted(Path(__file__).parent.glob('*.py')):
        h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()

def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    with tmp.open('w') as f:
        json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def seed(space,p,order):
    psi=np.zeros((space.dim,order+1),dtype=np.float64)
    if space.begin<=p<space.end:psi[p-space.begin,0]=1.
    # Degeneracy check remains exact in integer-quarter energies.
    local=np.sum((space.N%2==0)&(space.P%2==p%2)&(4*space.N+space.P==p))
    if int(global_sum(space.comm,np.array([local]))[0])!=1:
        raise RuntimeError('Reference is degenerate in the selected sector')
    return psi

def sparse_reference(m,v):
    idx=np.flatnonzero((m[:,0]!=0.)|(v[:,0]!=0.))
    return idx,m[idx,0].copy(),v[idx,0].copy()

def calibrate(space,order):
    refs=(0,1,3)
    psi={p:seed(space,p,order) for p in refs}
    E={p:np.r_[p/4,np.zeros(order)] for p in refs}
    r=np.zeros(order+1);g=np.zeros(order+1);refverts={}
    for k in range(1,order+1):
        rhs={};raw={}
        for p in refs:
            m,v=space.vertices(psi[p][:,:k],k-1,parity=p%2)
            if k==1:refverts[p]=sparse_reference(m,v)
            t=space.F1*psi[p][:,k-1]
            for j in range(1,k):t+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
            rhs[p]=t;raw[p]=space.sample(t,p)
            del m,v
        r[k]=((-.25 if k==1 else 0.)-(raw[1]-raw[0]))/2
        g[k]=((.25 if k==1 else 0.)-(raw[3]-raw[0])-6*r[k])/3
        for p in refs:
            t=rhs.pop(p);idx,mv,vv=refverts[p]
            t[idx]+=r[k]*mv+g[k]*vv
            E[p][k]=space.sample(t,p)
            solve_wave(t,psi[p],E[p],k,p,space.P,space.N)
    return psi,E,r,g

def fixed_wave(space,p,order,r,g):
    """One reference at a time, given the shared low-order tuning."""
    psi=seed(space,p,order);E=np.r_[p/4,np.zeros(order)]
    for k in range(1,order+1):
        m,v=space.vertices(psi[:,:k],k-1,parity=p%2)
        t=space.F1*psi[:,k-1]
        for j in range(1,k+1):t+=r[j]*m[:,k-j]+g[j]*v[:,k-j]
        E[k]=space.sample(t,p)
        solve_wave(t,psi,E,k,p,space.P,space.N)
    return psi,E

def vacuum_table(cutoff,degree):
    w=np.zeros(degree+1);w[0]=1.
    sums=np.zeros((cutoff+1,degree+1));running=np.zeros(degree+1)
    for m in range(cutoff):
        if m:
            old=w.copy();w=(m+1.)/m*old;w[1:]-=2./m*old[:-1]
        if m%2==0:
            den=np.array([(m+1.)**(-j-1) for j in range(degree+1)])
            running+=np.convolve(w,den)[:degree+1]
        sums[m+1]=running
    return sums

def vacuum_quotient(space,psi,degree):
    norm=space.inner(psi,psi,degree);coeff=np.zeros(degree+1)
    sums=vacuum_table(space.cutoff,degree)
    upper=np.maximum(0,(4*space.cutoff-4*space.N-space.P)//4)
    for k in range(degree+1):
        diag=-(sums[space.cutoff,k]-sums[upper,k])/6
        coeff[k:]+=space.inner(psi,psi,degree-k,diag)
    return divide_series(coeff,norm,degree)

def extract(components,refs,degree,corrected=False):
    F=np.array([components[p]['F'] for p in refs]);M=np.array([components[p]['M'] for p in refs]);V=np.array([components[p]['V'] for p in refs])
    K=np.array([components[p]['K'] for p in refs]) if corrected else None
    E=F.copy();r=np.zeros(degree+1);g=np.zeros(degree+1)
    i0=refs.index(0);i1=refs.index(1);i3=refs.index(3)
    for k in range(1,degree+1):
        gg=np.convolve(g,g)
        for ip,p in enumerate(refs):
            E[ip,k]+=sum(r[j]*M[ip,k-j]+g[j]*V[ip,k-j] for j in range(1,k))
            if corrected:E[ip,k]+=sum(gg[j]*K[ip,k-j] for j in range(2,k+1))
        r[k]=((-.25 if k==1 else 0.)-(E[i1,k]-E[i0,k]))/2
        g[k]=((.25 if k==1 else 0.)-(E[i3,k]-E[i0,k])-6*r[k])/3
        E[:,k]+=r[k]*M[:,0]+g[k]*V[:,0]
    t1=np.zeros(degree+1);t1[:2]=[.25,-.25]
    t3=np.zeros(degree+1);t3[:2]=[.75,.25]
    result={'C':(E[refs.index(2)]-E[i0]).tolist(),'r':r.tolist(),'g':g.tolist(),
            'tuning_residual':float(max(np.max(abs(E[i1]-E[i0]-t1)),np.max(abs(E[i3]-E[i0]-t3))))}
    if 6 in refs:result['D6']=(E[refs.index(6)]-E[i0]).tolist()
    return result,E

def second_order_shell_value(cutoff):
    """Independent float64 evaluation of the exact even-shell C2 identity."""
    v=1.;terms=[]
    for n in range(cutoff-1):
        if n:v*=(n-.5)/n
        if n%2==0:
            f=2/(81*(n-.5))+2/(9*(n+.5))+2/(81*(n+1))
            if n>0:f+=2/(9*n)
            terms.append(v*f)
    return math.fsum(terms)

def compute(cutoff:int,task:str='thermal',degree:int|None=None,comm=None,
            checkpoint:Path|None=None,memory_limit_gib:float|None=None,
            basis_cache:Path|None=None):
    if task not in ('thermal','phi6'):raise ValueError('Unknown task')
    if degree is None:degree=7 if task=='thermal' else 5
    if (task=='thermal' and degree not in (6,7)) or (task=='phi6' and degree not in (3,5)):
        raise ValueError('Supported degrees: thermal 6/7, phi6 3/5')
    if cutoff<2 or cutoff%2:raise ValueError('cutoff must be even and >=2')
    if task=='phi6' and cutoff<4:raise ValueError('phi6 requires cutoff >=4')
    root=comm is None or comm.Get_rank()==0
    order=degree//2;pmax=(3 if task=='thermal' else 6)+4*order;qmax=4*order
    config={'task':task,'degree':degree,'cutoff':cutoff,'pmax':pmax,'qmax':qmax,
            'version':VERSION,'source_sha256':source_fingerprint()}
    cp={'config':config,'components':{}}
    if checkpoint:
        old=json.loads(Path(checkpoint).read_text()) if root and Path(checkpoint).exists() else None
        if comm is not None:old=comm.bcast(old,root=0)
        if old:
            if old.get('config')!=config:raise ValueError('Checkpoint configuration/source mismatch; use a new checkpoint path')
            cp=old
            if 'result' in cp:
                from .validate import check_result
                return check_result(cp['result'])
    def save():
        if checkpoint and root:atomic_json(checkpoint,cp)
    start=time.perf_counter()
    # basis_cache is handled by RankedBasis; operator jets are rebuilt from tiny tables.
    space=Space(cutoff,pmax,qmax,degree-1,comm,memory_limit_gib,basis_cache=basis_cache)
    if 'r_low' in cp:
        rlow=np.array(cp['r_low']);glow=np.array(cp['g_low']);saved_psi={};elow={int(p):np.array(x) for p,x in cp['E_low'].items()}
    else:
        saved_psi,elow,rlow,glow=calibrate(space,order)
        cp.update(r_low=rlow.tolist(),g_low=glow.tolist(),E_low={str(p):v.tolist() for p,v in elow.items()});save()
    components={int(p):v for p,v in cp['components'].items()}
    # Release each calibration wavefunction after its scalar quotient is recorded.
    refs=[0,1,3,2]+([6] if task=='phi6' else [])
    for p in refs:
        if p in components:
            saved_psi.pop(p,None);continue
        if p in saved_psi:psi=saved_psi.pop(p)
        else:psi,_=fixed_wave(space,p,order,rlow,glow)
        F,M,V=quotient_components(space,psi,degree,parity=p%2)
        c={'F':F.tolist(),'M':M.tolist(),'V':V.tolist()}
        if task=='phi6':c['K']=vacuum_quotient(space,psi,degree-2).tolist()
        components[p]=c;cp['components'][str(p)]=c;save();del psi
    raw,E=extract(components,refs,degree)
    import numba
    result={'cutoff':cutoff,'degree':degree,'task':task,'basis_dimension':space.global_dim,'threads':int(numba.get_num_threads()),
            'particle_cap':pmax,'nonzero_particle_cap':qmax,'dtype':'float64',
            'fastmath':False,'source_sha256':config['source_sha256'],
            'scope':'Same finite-cutoff Hamiltonian and prescriptions as the supplied code; no new physical matching or extrapolation.'}
    if task=='thermal':result.update(raw)
    else:
        result['raw']=raw
        result['vacuum_subtracted'],_=extract(components,refs,degree,True)
    result['second_order_shell_residual']=float(raw['C'][2]-second_order_shell_value(cutoff))
    if abs(result['second_order_shell_residual'])>1e-10:
        raise ArithmeticError('Independent second-order shell check failed')
    result['low_order_residual']=float(max(np.max(abs(np.array(raw['r'])[:order+1]-rlow)),np.max(abs(np.array(raw['g'])[:order+1]-glow)),
               max(np.max(abs(E[refs.index(p),:order+1]-elow[p])) for p in (0,1,3))))
    local={'rank':space.rank,'local_dim':space.dim,'edges_creation':len(space.creation.index),'edges_annihilation':len(space.annihilation.index),
           'edges_bytes':space.edges_bytes,'table_bytes':space.table_bytes,'ladder_calls':space.ladder_calls,
           'halo_remote_creation':space.haloC.remote_count,'halo_remote_annihilation':space.haloB.remote_count,
           'halo_bytes_sent':space.haloC.bytes_sent+space.haloB.bytes_sent,
           'halo_seconds':space.haloC.seconds+space.haloB.seconds,
           'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
           'phase_seconds':space.timings,'elapsed_seconds':time.perf_counter()-start}
    result['ranks']=[local] if comm is None else comm.allgather(local)
    result['seconds']=max(x['elapsed_seconds'] for x in result['ranks'])
    from .validate import check_result
    check_result(result)   # never publish a failing result as completed (review LRI-001)
    cp['result']=result;save()
    return result
