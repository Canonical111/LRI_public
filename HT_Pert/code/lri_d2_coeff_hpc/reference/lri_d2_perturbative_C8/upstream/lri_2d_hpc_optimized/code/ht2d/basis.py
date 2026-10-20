"""Exact ranked circle-bath graph, preserving the original DFS occupation order.

Only numeric arrays are stored. A lazy ``states`` view supplies the old tuple API
for diagnostics. No particle, angular, or intermediate-state truncation is added.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Sequence
import math
import numpy as np
from numba import njit
from scipy.sparse import csr_matrix


def dimension(cutoff: int) -> int:
    if int(cutoff) != cutoff or cutoff < 0:
        raise ValueError('cutoff must be a nonnegative integer')
    dp = [0] * (int(cutoff) + 1)
    dp[0] = 1
    for n in range(1, int(cutoff) + 1):
        for _ in range(n + 1):
            for k in range(n, int(cutoff) + 1):
                dp[k] += dp[k - n]
    return sum(dp)


@njit(cache=True)
def _counts(levels, cut):
    # count[k,l]: suffix multisets of labels >=k with total level <=l.
    d = np.ones((len(levels) + 1, cut + 1), np.int64)
    for k in range(len(levels) - 1, -1, -1):
        for l in range(cut + 1):
            d[k, l] = d[k + 1, l]
            if l >= levels[k]:
                d[k, l] += d[k, l - levels[k]]
    return d


@njit(cache=True)
def _enumerate(levels, spins, cut, N, P, J, tree, last, ptr):
    # Iterative preorder: identical row numbering to the original recursive code.
    path = np.empty(cut + 1, np.int64)
    nodes = np.zeros(cut + 1, np.int64)
    choices = np.zeros(cut + 1, np.int64)
    used = np.zeros(cut + 1, np.int64)
    spin = np.zeros(cut + 1, np.int64)
    unique = np.zeros(cut + 1, np.int64)
    row = 1
    depth = 0
    edges = 0
    while depth >= 0:
        k = choices[depth]
        if k >= len(levels) or used[depth] + levels[k] > cut:
            depth -= 1
            continue
        choices[depth] = k + 1
        parent = nodes[depth]
        oldlast = path[depth - 1] if depth else -1
        path[depth] = k
        used[depth + 1] = used[depth] + levels[k]
        spin[depth + 1] = spin[depth] + spins[k]
        unique[depth + 1] = unique[depth] + (k != oldlast)
        depth += 1
        nodes[depth] = row
        choices[depth] = k
        N[row] = used[depth]
        P[row] = depth
        J[row] = spin[depth]
        tree[row] = parent
        last[row] = k
        ptr[row] = edges
        edges += unique[depth]
        row += 1
    ptr[row] = edges
    return row, edges


@njit(cache=True)
def _rank_path(path, n, levels, counts, cut, skip=-1):
    rank = 0
    left = cut
    start = 0
    for i in range(n):
        if i == skip:
            continue
        k = path[i]
        rank += 1 + counts[start, left] - counts[k, left]
        left -= levels[k]
        start = k
    return rank


@njit(cache=True)
def _fill_edges(tree, last, P, ptr, levels, counts, cut, parent, mode, sqocc, mirror):
    path = np.empty(cut + 1, np.int64)
    reflected = np.empty(cut + 1, np.int64)
    swap = np.empty(len(levels), np.int64)
    for n in range(1, cut + 1):
        base = (n - 1) * (n + 2) // 2
        for a in range(n + 1):
            swap[base + a] = base + n - a
    for row in range(1, len(tree)):
        node = row
        n = int(P[row])
        for k in range(n - 1, -1, -1):
            path[k] = last[node]
            node = tree[node]
        q = ptr[row]
        at = 0
        while at < n:
            end = at + 1
            while end < n and path[end] == path[at]:
                end += 1
            parent[q] = _rank_path(path, n, levels, counts, cut, at)
            mode[q] = path[at]
            sqocc[q] = math.sqrt(end - at)
            q += 1
            at = end
        for k in range(n):
            reflected[k] = swap[path[k]]
        # Insertion sort of a very short occupation list; no Python dictionaries.
        for k in range(1, n):
            val = reflected[k]
            j = k - 1
            while j >= 0 and reflected[j] > val:
                reflected[j + 1] = reflected[j]
                j -= 1
            reflected[j + 1] = val
        mirror[row] = _rank_path(reflected, n, levels, counts, cut)


class OccupationView(Sequence):
    """Reconstruct tuples on demand; does not cache an exponentially large list."""
    def __init__(self, tree, last, particles):
        self.tree, self.last, self.particles = tree, last, particles

    def __len__(self):
        return len(self.tree)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self))) ]
        i = int(i)
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError(i)
        path = [0] * int(self.particles[i])
        for k in range(len(path) - 1, -1, -1):
            path[k] = int(self.last[i])
            i = int(self.tree[i])
        return tuple(path)


@dataclass
class CircleBathBasis:
    cutoff: int
    labels: tuple
    states: Sequence
    N: np.ndarray
    P: np.ndarray
    J: np.ndarray
    indptr: np.ndarray
    parent: np.ndarray
    mode: np.ndarray
    sqocc: np.ndarray
    mirror: np.ndarray
    tree: np.ndarray
    last: np.ndarray
    counts: np.ndarray

    @classmethod
    def build(cls, cutoff: int, max_states=2_000_000, max_bytes=2*1024**3):
        if isinstance(cutoff, bool) or int(cutoff) != cutoff or cutoff < 0:
            raise ValueError('cutoff must be a nonnegative integer')
        cutoff = int(cutoff)
        size = dimension(cutoff)
        if size > max_states or size >= np.iinfo(np.int64).max:
            raise MemoryError(f'{size} bath states exceeds explicit guard {max_states}')
        labels = tuple((a, n-a) for n in range(1, cutoff+1) for a in range(n+1))
        levels = np.array([a+b for a,b in labels], np.int64)
        spins = np.array([a-b for a,b in labels], np.int64)
        index = np.int32 if size < 2**31 else np.int64
        mode_type = np.uint16 if len(labels) <= 65536 else np.uint32
        ptype = np.int16 if cutoff < 32768 else np.int32
        # First-pass arrays and DP checked before allocation, edges after counting.
        preliminary = size*(4+4+np.dtype(ptype).itemsize + 2*np.dtype(index).itemsize
                            +np.dtype(mode_type).itemsize+8) + (len(labels)+1)*(cutoff+1)*8
        if preliminary > max_bytes:
            raise MemoryError(f'Basis initial arrays need {preliminary} bytes > {max_bytes}')
        counts = _counts(levels, cutoff)
        if counts[0, cutoff] != size:
            raise OverflowError('Rank table overflow or dimension mismatch')
        N=np.zeros(size,np.int32);P=np.zeros(size,ptype);J=np.zeros(size,np.int32)
        tree=np.zeros(size,index);last=np.zeros(size,mode_type);ptr=np.zeros(size+1,np.int64)
        rows, edges = _enumerate(levels,spins,cutoff,N,P,J,tree,last,ptr)
        if rows != size:
            raise AssertionError('Rank / enumeration size mismatch')
        required = preliminary + edges*(np.dtype(index).itemsize+np.dtype(mode_type).itemsize+8)
        if required > max_bytes:
            raise MemoryError(f'Exact bath graph needs approximately {required} bytes > {max_bytes}')
        parent=np.empty(edges,index);mode=np.empty(edges,mode_type);sqocc=np.empty(edges,np.float64)
        mirror=np.zeros(size,index)
        _fill_edges(tree,last,P,ptr,levels,counts,cutoff,parent,mode,sqocc,mirror)
        return cls(cutoff,labels,OccupationView(tree,last,P),N,P,J,ptr,parent,mode,sqocc,
                   mirror,tree,last,counts)

    def rank(self, state):
        path=np.asarray(state,dtype=np.int64)
        levels=np.array([a+b for a,b in self.labels],dtype=np.int64)
        if np.any(path<0) or np.any(path>=len(levels)) or np.any(path[:-1]>path[1:]) or levels[path].sum()>self.cutoff:
            raise ValueError('Invalid occupation state')
        return int(_rank_path(path,len(path),levels,self.counts,self.cutoff))

    def ladders(self, delta):
        if not np.isfinite(delta) or delta <= 0:
            raise ValueError('Positive finite field dimension required')
        v=np.ones(self.cutoff+1)
        for n in range(1,len(v)):
            v[n]=v[n-1]*(delta+n-1)/n
        u=np.array([math.sqrt(v[a]*v[b]) for a,b in self.labels])
        C=csr_matrix((self.sqocc*u[self.mode],self.parent.copy(),self.indptr.copy()),shape=(len(self.N),len(self.N)))
        C.sort_indices();B=C.T.tocsr();B.sort_indices()
        return B,C

    @property
    def nbytes(self):
        return sum(x.nbytes for x in (self.N,self.P,self.J,self.indptr,self.parent,self.mode,
                                      self.sqocc,self.mirror,self.tree,self.last,self.counts))
