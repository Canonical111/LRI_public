"""Allocation-free exact dimensions and conservative, uncalibrated byte envelopes."""
import math,os
from pathlib import Path

def plan(bath_cut,nz,osc,backend='auto',ncv=28,window='none'):
    if bath_cut<2 or nz<2 or osc<2*nz+8 or osc%2:raise ValueError('Invalid caps')
    if window not in ('none','vacuum'):raise ValueError('Unknown window prescription')
    from .basis import count_table
    c=count_table(bath_cut);D=int(c[bath_cut,1]);levels=[int(c[n,1])-(int(c[n-1,1]) if n else 0) for n in range(bath_cut+1)]
    even=sum(levels[::2]);odd=sum(levels[1::2]);E=sum(int(c[n,1]) for n in range(bath_cut))
    if backend=='auto':backend='tensor' if bath_cut<=18 else 'ladder'
    index_bytes=4 if D<=2**31-1 else 8
    csr_index_bytes=4 if max(D,E)<=2**31-1 else 8
    # Metadata, creation-edge source and both floating sparse directions.
    graph=(index_bytes+2+8)*E+8*(D+1)+8*D+2*((csr_index_bytes+8)*E+8*(D+1))
    krylov=8*even*nz*(max(ncv,28)+32)
    scratch=8*D*nz*14
    auxiliary=8*osc*osc*16
    # Worst-case dense bath fill during W construction, deliberately conservative.
    bath_extra=128*D*D if backend=='tensor' else 0
    base=graph+krylov+scratch+auxiliary+bath_extra+256*2**20
    # Window: genuine sub-cutoff regulators at every even level below the top (stored
    # for the whole delta), plus transient one-vector Krylov work at the largest one.
    window_bytes=0;top=bath_cut-(bath_cut&1)
    if window=='vacuum':
        for lev in range(2,top,2):
            sub=plan(lev,nz,osc,backend,ncv)
            window_bytes+=sub['graph_estimate_bytes']+sub['tensor_bath_bytes']
        if top>2:window_bytes+=8*plan(top-2,nz,osc,backend,ncv)['dimension_per_field_parity']*(max(ncv,28)+8)
    envelope=int(1.4*(base+window_bytes))
    return {'bath_cut':bath_cut,'nz':nz,'osc':osc,'backend':backend,
        'bath_states_all_reflections':D,'bath_states_reflection_even':even,'bath_states_reflection_odd':odd,
        'creation_edges_exact':E,'dimension_per_field_parity':even*nz,'dimension_both_field_parities':2*even*nz,
        'edge_index_bytes':index_bytes,'csr_index_bytes':csr_index_bytes,'graph_estimate_bytes':graph,
        'tensor_bath_bytes':bath_extra,'window':window,'window_estimate_bytes':window_bytes,
        'memory_envelope_bytes':envelope,'memory_envelope_gib':envelope/2**30,
        'scope':'Exact dimensions; memory is a conservative uncalibrated planning envelope, not measured RSS.'}

def available_allocation_bytes():
    """Best-effort remaining cgroup memory, falling back to /proc/MemAvailable."""
    try:
        limit=Path('/sys/fs/cgroup/memory.max').read_text().strip()
        used=int(Path('/sys/fs/cgroup/memory.current').read_text())
        if limit!='max':return max(0,int(limit)-used)
    except (OSError,ValueError):pass
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):return int(line.split()[1])*1024
    except (OSError,ValueError):pass
    return None

def guard(plan_record,limit_gib=None):
    limits=[]
    if limit_gib is not None:
        if not math.isfinite(limit_gib) or limit_gib<=0:raise ValueError('memory limit must be positive')
        limits.append(int(limit_gib*2**30))
    actual=available_allocation_bytes()
    if actual is not None:limits.append(actual)
    if limits and plan_record['memory_envelope_bytes']>min(limits):
        raise MemoryError(f"Planning envelope {plan_record['memory_envelope_gib']:.3f} GiB exceeds available/requested {min(limits)/2**30:.3f} GiB; reduce caps or request more memory. No cap was changed.")
