"""Exact rotational-trace vertex construction, without polar quadrature.

For scalar matrix elements the integrand is constant over S^2. For a spin-J
multiplicity space the angular integral is its magnetic trace at the north pole,
divided by 2J+1. At the pole only m=0 oscillators contribute. Intermediate
magnetic states are not heuristically pruned: this is an exact group average.
"""
from __future__ import annotations
from collections import Counter
import math
import numpy as np
from scipy.sparse import csr_matrix, csc_matrix, coo_matrix
from numba import njit
from .basis import _rank_path


def canonical(a):
    a=a.tocsr();a.sum_duplicates();a.sort_indices();a.eliminate_zeros();return a

@njit(cache=True)
def _magnetic_edges(tree,last,particles,source,lookup,levels,counts,cut,ells,ms,sign):
    # Ladder m -> m+sign. No amplitudes are dropped; exact magnetic selection.
    count=0
    for row in source:count+=int(particles[row])
    rr=np.empty(count,np.int64);cc=np.empty(count,np.int64);dd=np.empty(count,np.float64)
    path=np.empty(cut+1,np.int64);nedge=0
    for c in range(len(source)):
        row=source[c];node=row;p=int(particles[row])
        for k in range(p-1,-1,-1):path[k]=last[node];node=tree[node]
        at=0
        while at<p:
            mode=path[at];end=at+1
            while end<p and path[end]==mode:end+=1
            l=ells[mode];m=ms[mode]
            if (sign>0 and m<l) or (sign<0 and m>-l):
                target=mode+sign;nt=0
                for k in range(p):
                    if path[k]==target:nt+=1
                # Modify first for lowering / last for raising: sorted order retained.
                pos=end-1 if sign>0 else at
                path[pos]=target
                dest=_rank_path(path,p,levels,counts,cut)
                path[pos]=mode
                if lookup[dest]<0:raise ValueError('magnetic ladder left expected sector')
                rr[nedge]=lookup[dest];cc[nedge]=c
                dd[nedge]=math.sqrt((l-sign*m)*(l+sign*m+1)*(end-at)*(nt+1))
                nedge+=1
            at=end
    return rr[:nedge],cc[:nedge],dd[:nedge]


def magnetic_component(basis, S, magnetic):
    """Lower one step; preserve the multiplicity/column gauge of S."""
    src=np.flatnonzero(np.diff(S.indptr));dst=np.flatnonzero(basis.M==magnetic-1)
    lookup=np.full(len(basis.N),-1,np.int64);lookup[dst]=np.arange(len(dst))
    labs=np.asarray(basis.labels,dtype=np.int64)
    r,c,d=_magnetic_edges(basis.tree,basis.last,basis.P,src,lookup,
        basis.mode_levels,basis.counts,basis.cutoff,labs[:,1],labs[:,2],-1)
    small=csr_matrix((d,(r,c)),shape=(len(dst),len(src)))@S[src]
    v=small.tocoo()
    return canonical(csr_matrix((v.data,(dst[v.row],v.col)),shape=S.shape))


@njit(cache=True)
def _pole_csr(selected,lookup,ptr,parents,modes,sqocc,amp,mode_m):
    rowptr=np.zeros(len(selected)+1,np.int64)
    for i in range(len(selected)):
        row=selected[i];count=0
        for e in range(ptr[row],ptr[row+1]):
            if mode_m[modes[e]]==0:count+=1
        rowptr[i+1]=rowptr[i]+count
    ix=np.empty(rowptr[-1],np.int64);data=np.empty(rowptr[-1],np.float64)
    for i in range(len(selected)):
        row=selected[i];q=rowptr[i]
        for e in range(ptr[row],ptr[row+1]):
            k=modes[e]
            if mode_m[k]!=0:continue
            ix[q]=lookup[parents[e]]
            if ix[q]<0:raise ValueError('m=0 annihilator changed magnetic quantum number')
            data[q]=sqocc[e]*amp[k];q+=1
    return rowptr,ix,data


def _single_pole(basis, S, particles, x, magnetic):
    """Complete normal-ordered vertices at one pole for a fixed M representation."""
    nB=S.shape[1]
    selected=np.flatnonzero(basis.M==magnetic)
    # C has only exact m=0 edges. Use rectangular selection before any powers.
    labels=np.asarray(basis.labels,dtype=np.int64)
    amp=basis.weights(x)*np.sqrt(2*labels[:,1]+1)*(labels[:,2]==0)
    lookup=np.full(len(basis.N),-1,np.int64);lookup[selected]=np.arange(len(selected))
    ptr,ix,data=_pole_csr(selected,lookup,basis.ptr,basis.parents,basis.modes,basis.sqocc,amp,labels[:,2])
    C=csr_matrix((data,ix,ptr),shape=(len(selected),len(selected)))
    B=canonical(C.T)
    smallS=S[selected].tocsc()
    ix={int(p):np.flatnonzero(particles==p) for p in np.unique(particles)}
    blocks={p:smallS[:,ii] for p,ii in ix.items()}
    ans=[{} for _ in range(4)];cache={}
    def images(p):
        if p not in cache:
            arr=[blocks[p]]
            for k in range(1,5):
                arr.append((B@arr[-1]).tocsc() if k<=p else csc_matrix(arr[0].shape))
            cache[p]=arr
        return cache[p]
    for pb in sorted(ix):
        for old in [p for p in cache if p<pb]:del cache[old]
        ar=images(pb)
        for diff in range(5):
            pa=pb+diff
            if pa not in ix:continue
            al=images(pa)
            for k in range(1,5):
                if diff>k or (diff+k)%2:continue
                j=(diff+k)//2
                v=canonical(al[j].T@ar[k-j])
                if v.nnz:ans[k-1][pa,pb]=v*math.comb(k,j)
    out=[]
    for block in ans:
        rr=[];cc=[];dd=[]
        for (pa,pb),v in block.items():
            v=v.tocoo();r=ix[pa][v.row];c=ix[pb][v.col]
            rr.append(r);cc.append(c);dd.append(v.data)
            if pa!=pb:rr.append(c);cc.append(r);dd.append(v.data)
        if rr:out.append(canonical(coo_matrix((np.concatenate(dd),(np.concatenate(rr),np.concatenate(cc))),shape=(nB,nB))))
        else:out.append(csr_matrix((nB,nB)))
    return out


def build_rotational_vertices(basis, S, particles, x, spin=0):
    """Average all magnetic components at the pole: exact SO(3) trace identity.

    Uses the same highest-weight gauge as the reference. No tolerance, model,
    local space, particle support, or cutoffs are changed.
    """
    if int(spin)!=spin or spin<0:raise ValueError('spin must be nonnegative integer')
    result=[csr_matrix((S.shape[1],S.shape[1])) for _ in range(4)]
    component=S
    for m in range(spin,-spin-1,-1):
        block=_single_pole(basis,component,particles,x,m)
        for k in range(4):result[k]+=block[k]/(2*spin+1)
        if m>-spin:
            component=magnetic_component(basis,component,m)/math.sqrt((spin+m)*(spin-m+1))
    return [canonical(a) for a in result]
