"""Exact state/edge counting, conservative planning without allocating a basis."""
from __future__ import annotations
import math
from ._core.basis import count_tables


def plan(cutoff,degree,budget_gib=None):
    if degree not in (4,5,6,7) or cutoff<4 or cutoff%2:raise ValueError('even cutoff>=4 and degree 4--7')
    reach=(degree-2)//2;pmax=3+4*reach;qmax=4*reach
    tab=(qmax+1)*(4*cutoff+1)*(cutoff+1)*8+(pmax+1)*(qmax+1)*(4*cutoff+1)*8
    if tab>2**30:raise MemoryError('Planner table >1 GiB: use a reviewed large-cutoff counting implementation')
    G,Z=count_tables(cutoff,pmax,qmax);dim=int(Z[pmax,qmax,4*cutoff])
    # Removing one occurrence of mode n bijects occupied-mode edges with states
    # counted in the smaller P/Q/energy budget. Both orientations have this count.
    edges=sum(int(Z[pmax-1,qmax-int(n>0),4*cutoff-4*n-1]) for n in range(cutoff))
    indexbytes=4 if dim<=2**31-1 else 8;modebytes=2 if cutoff<=65536 else 4
    edgebytes=2*(8*(dim+1)+edges*(indexbytes+modebytes+1))
    # At most 35 simultaneously live float64-vector equivalents in the response
    # engine's large-array phases. Budget 64 for temporaries/allocator slack,
    # exact edge bytes, 48 B/state metadata, and 512 MiB process headroom.
    # This is not an RSS guarantee; target-node calibration remains mandatory.
    conservative=64*8*dim+48*dim+edgebytes+tab+512*2**20
    return dict(cutoff=cutoff,degree=degree,particle_cap=pmax,nonzero_particle_cap=qmax,
                basis_dimension=dim,edges_per_orientation=edges,index_bytes=indexbytes,
                exact_edge_bytes=edgebytes,count_table_bytes=tab,
                conservative_gib=conservative/2**30,
                recommended_request_gib=math.ceil(conservative/2**30),
                fits_budget=None if budget_gib is None else conservative<=budget_gib*2**30,
                model_scope='64-vector planning envelope, exact edge bytes, metadata, 512 MiB headroom. Calibrate RSS on target node; no measured runtime prediction.')
