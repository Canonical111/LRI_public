"""Allocation-free state/edge planning (integer DP tables, never Fock rows)."""
from __future__ import annotations
import math
import numpy as np
from ._core.basis import count_tables

def counts(cutoff,p,q):
    if cutoff<2 or cutoff%2:raise ValueError('cutoff must be even >=2')
    # DP table guard is independent of the exponentially larger Fock arrays.
    tab=8*((q+1)*(4*cutoff+1)*(cutoff+1)+(p+1)*(q+1)*(4*cutoff+1))
    if tab>2**30:raise MemoryError('Planning tables exceed 1 GiB; use a dedicated counting implementation')
    G,Z=count_tables(cutoff,p,q);E=4*cutoff;dim=int(Z[p,q,E])
    ne=int(Z[p-1,q,E-1])
    for n in range(1,cutoff):
        if q and E-4*n-1>=0:ne+=int(Z[p-1,q-1,E-4*n-1])
    parity=[0,0];previous=0
    for k in range(p+1):
        v=int(Z[k,q,E]);parity[k%2]+=v-previous;previous=v
    return dict(dim=dim,edges_per_orientation=ne,parity_dimensions=parity,table_bytes=tab)

def plan(cutoff,backend='stored'):
    if backend not in ('stored','ranked'):raise ValueError('unknown backend')
    core=counts(cutoff,15,12);outer=counts(cutoff,19,16);cal=counts(cutoff,11,8)
    dc=core['dim'];do=outer['dim'];ds=max(core['parity_dimensions'])
    md=2 if cutoff<=65536 else 4;ic=4 if dc<=2**31-1 else 8;io=4 if do<=2**31-1 else 8
    ce=16*(dc+2)+2*(ic+md+1)*core['edges_per_orientation']
    oe=(8*(do+1)+(io+md+1)*outer['edges_per_orientation']) if backend=='stored' else outer['table_bytes']
    # Counted storage plus an intentionally padded vector workspace. Not calibrated
    # Expanse RSS. Peak may occur in edge repacking, not in a ladder application.
    basis_packing=2*ce+48*dc+core['table_bytes']
    operating=ce+oe+40*dc+6*do+io*dc+8*(30*ds+3*do)+2*outer['table_bytes']
    # Calibration uses the unmodified fourth-order oracle, in a smaller cap space.
    calibration=800*cal['dim']+32*cal['edges_per_orientation']+cal['table_bytes']
    modeled=max(basis_packing,operating,calibration)+384*2**20
    conservative=1.25*modeled+512*2**20
    return {'cutoff':cutoff,'degree':8,'backend':backend,'core':core,'full_residual':outer,
            'calibration':cal,'core_edge_bytes':ce,'outer_edge_or_table_bytes':oe,
            'model_bytes':int(modeled),'conservative_gib':conservative/2**30,
            'scope':'Exact dimensions and edge counts; UNCALIBRATED memory envelope. No runtime prediction.'}
