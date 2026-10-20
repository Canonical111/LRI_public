"""Exact L18/L20 graph/rotation counts without constructing the full Fock graph.

Only complete bosonic species characters are used; no mode, particle, or amplitude
is discarded. The census is a planning tool, not a substitute for a projector or
for an on-node setup/eigensolver measurement.
"""
from __future__ import annotations
from functools import lru_cache
from collections import Counter
from itertools import combinations_with_replacement, product
import math
import time
import numpy as np
from scipy.sparse import csr_matrix
from .basis import dimension, graph_requirements


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or int(value) != value or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return int(value)


@lru_cache(maxsize=None)
def symmetric_character(ell, occupancy):
    """Weight multiplicities of Sym^occupancy(V_ell), ordered -ell*q,...,+ell*q."""
    ell = _integer(ell, 'ell')
    q = _integer(occupancy, 'occupancy')
    if math.comb(q+2*ell, 2*ell) > np.iinfo(np.int64).max:
        raise OverflowError('Symmetric-power character exceeds int64')
    off = ell*q
    dp = np.zeros((q+1, 2*off+1), np.int64)
    dp[0, off] = 1
    for m in range(-ell, ell+1):
        for r in range(1, q+1):
            if m > 0:
                dp[r, m:] += dp[r-1, :-m]
            elif m < 0:
                dp[r, :m] += dp[r-1, -m:]
            else:
                dp[r] += dp[r-1]
    a = dp[q].copy()
    if not np.array_equal(a, a[::-1]) or int(a.sum()) != math.comb(q+2*ell, 2*ell):
        raise AssertionError('Invalid symmetric-power character')
    a.flags.writeable = False
    return a


def census(cutoff, spins=(0,1,2), nz=16, largest=10):
    """Exact complete-space counts and block shapes at each natural inversion.

    graph_array_bytes is an exact representation count, NOT a peak-RSS bound.
    Projector COO/dense workspace figures are labelled estimates/upper bounds.
    The number of nonzero vertex entries is NOT inferred from state counts.
    """
    L = _integer(cutoff, 'cutoff')
    nz = _integer(nz, 'nz', 1)
    largest = _integer(largest, 'largest', 1)
    spins = tuple(dict.fromkeys(_integer(j, 'spin') for j in spins))
    req = graph_requirements(L)
    if req['states'] >= np.iinfo(np.int64).max:
        raise OverflowError('Complete Fock-space count exceeds int64')
    species = [(n, k-2*n) for k in range(1, L+1) for n in range(k//2+1)]
    stats = {J:dict(spin=J, inversion=J%2, blocks=0, nonempty_blocks=0,
                   magnetic_sources=0, magnetic_targets=0, highest_weights=0,
                   dense_null_entries_upper=0, dense_jplus_entries_sum=0,
                   dense_svd_work_proxy=0, source_size_histogram={}, largest_blocks=[])
             for J in spins}
    total = 0
    nblocks = 0
    start = time.perf_counter()
    def visit(first, level, chars, spec):
        nonlocal total, nblocks
        nblocks += 1
        total += int(chars.sum())
        mid = len(chars)//2
        for J in spins:
            if level%2 != J%2:
                continue
            ns = int(chars[mid+J]) if mid >= J else 0
            nt = int(chars[mid+J+1]) if mid >= J+1 else 0
            if ns < nt:
                raise AssertionError('SU(2) weight monotonicity violated')
            if not ns:
                continue
            a = stats[J]
            a['blocks'] += 1
            a['nonempty_blocks'] += int(ns > nt)
            a['magnetic_sources'] += ns
            a['magnetic_targets'] += nt
            a['highest_weights'] += ns-nt
            a['dense_null_entries_upper'] += ns*(ns-nt)
            a['dense_jplus_entries_sum'] += ns*nt
            a['dense_svd_work_proxy'] += ns*nt*min(ns, nt)
            bucket = str(1 << (ns-1).bit_length())
            a['source_size_histogram'][bucket] = a['source_size_histogram'].get(bucket,0)+1
            blocks = a['largest_blocks']
            if len(blocks) < largest or ns > blocks[-1]['sources']:
                blocks.append(dict(level=level, species=[list(s) for s in spec],
                    sources=ns, targets=nt, nullity=ns-nt, dense_matrix_bytes=8*ns*nt,
                    # J_- J_+ on M=J has positive eigenvalues j(j+1)-J(J+1).
                    nonzero_sigma_lower_bound=math.sqrt(2*(J+1)),
                    nonzero_sigma_upper_bound=math.sqrt(max(0,level*(level+1)-J*(J+1)))))
                blocks.sort(key=lambda b:b['sources'], reverse=True)
                del blocks[largest:]
        for i in range(first, len(species)):
            n, ell = species[i]
            e = 2*n+ell
            if level+e > L:
                break
            for q in range(1, (L-level)//e+1):
                visit(i+1, level+q*e, np.convolve(chars, symmetric_character(ell,q)),
                      spec+((n,ell,q),))
    visit(0,0,np.array([1],np.int64),())
    if total != req['states']:
        raise AssertionError(f'Character/Fock count mismatch: {total} != {req["states"]}')
    for J, a in stats.items():
        a['dimension_per_field_parity'] = nz*a['highest_weights']
        a['dimension_both_field_parities'] = 2*nz*a['highest_weights']
        # State-column COO indices are int64 during assembly; CSR may downcast.
        a['typed_COO_payload_bytes_upper'] = 24*a['dense_null_entries_upper']
        a['largest_dense_input_bytes'] = max(b['dense_matrix_bytes'] for b in a['largest_blocks']) if a['blocks'] else 0
    return dict(cutoff=L, nz_per_parity=nz, graph=req, species_configurations=nblocks,
                character_total_states=total, sectors={str(j):a for j,a in stats.items()},
                elapsed_seconds=time.perf_counter()-start,
                scope='Exact counts and block shapes only; no graph, SVD, vertices or eigensolve allocated')


def species_jplus(spec, spin, max_states=2_000_000):
    """Construct one actual complete species J+ block without a full bath graph.

    Local mode ordering is the same radial/ell ordering as the production graph.
    This independent enumeration is for isolated-block failure replay/validation.
    """
    J = _integer(spin, 'spin')
    spec = tuple(tuple(_integer(a,'species entry') for a in s) for s in spec)
    if any(len(s)!=3 or s[2]==0 or 2*s[0]+s[1]==0 for s in spec):
        raise ValueError('Species entries must be positive-mode (n,ell,occupancy) triples')
    if len({s[:2] for s in spec}) != len(spec):
        raise ValueError('Combine duplicate species before block construction')
    spec = tuple(sorted(spec, key=lambda s:(2*s[0]+s[1],s[0])))
    count = math.prod(math.comb(q+2*ell,2*ell) for n,ell,q in spec)
    if count > max_states:
        raise MemoryError(f'Isolated species block enumeration needs {count} states; cap={max_states}')
    labels = []
    occupations = []
    for n,ell,q in spec:
        offset = len(labels)
        labels += [(n,ell,m) for m in range(-ell,ell+1)]
        occupations.append(tuple(combinations_with_replacement(range(offset, len(labels)),q)))
    src=[];dst=[]
    for parts in product(*occupations):
        state=sum(parts,())
        M=sum(labels[k][2] for k in state)
        if M==J:src.append(state)
        elif M==J+1:dst.append(state)
    src.sort();dst.sort()
    lookup={s:i for i,s in enumerate(dst)}
    rr=[];cc=[];dd=[]
    for c,state in enumerate(src):
        occ=Counter(state)
        for k,q in occ.items():
            n,ell,m=labels[k]
            if m==ell:continue
            out=list(state);out.remove(k);out.append(k+1);out.sort()
            rr.append(lookup[tuple(out)]);cc.append(c)
            dd.append(math.sqrt((ell-m)*(ell+m+1)*q*(occ.get(k+1,0)+1)))
    A=csr_matrix((np.array(dd,np.float64),(np.array(rr,np.int64),np.array(cc,np.int64))),
                 shape=(len(dst),len(src)))
    return A, src, dst
