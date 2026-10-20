"""int64 state-ID path (review LRI-005): thermal caps at cutoff 112 have 2,192,747,656 > 2^31-1 states.

(a) Build one small row shard located above 2^31 (a stand-in communicator only selects the row range; no MPI and
    no halo are involved) and check: int64 edge arrays; exact rank/unrank round trips; every creation and
    annihilation edge target is the expected neighbouring state (one particle of that mode removed/added, with
    the recorded occupation).
(b) The fused ladder kernel gives bitwise identical output with int64 and int32 index arrays on a small basis.
This covers the storage and indexing path of the largest thermal runs at small memory; it is not a full-scale run.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, numba
numba.set_num_threads(2)
from lri_hpc.basis import RankedBasis, count_tables, unrank, rank_seq
from lri_hpc.kernels import ladder
from lri_hpc.operators import Space


class RowRange:
    def __init__(self, rank, size): self.r, self.n = rank, size
    def Get_rank(self): return self.r
    def Get_size(self): return self.n


L, PM, QM = 112, 15, 12
G, Z = count_tables(L, PM, QM)
D = int(Z[PM, QM, 4 * L])
assert D == 2192747656 and D > 2**31 - 1, D
size = 20000
rank = (2**31 + 12345) * size // D + 1
b = RankedBasis(L, PM, QM, comm=RowRange(rank, size))
assert b.begin > 2**31 - 1 and b.dim > 1000, (b.begin, b.dim)
assert b.creation.index.dtype == np.int64 and b.annihilation.index.dtype == np.int64
seq = np.empty(PM + 1, np.int32); tgt = np.empty(PM + 1, np.int32)
rng = np.random.default_rng(7)
checked = 0
for i in rng.choice(b.dim, 300, replace=False):
    gid = b.begin + int(i)
    p, q, N = unrank(gid, G, Z, L, PM, QM, seq)
    assert rank_seq(seq, p, G, Z, L, PM, QM) == gid
    s = list(seq[:p])
    for e in range(b.creation.ptr[i], b.creation.ptr[i + 1]):          # remove one particle of mode m
        t = int(b.creation.index[e]); m = int(b.creation.mode[e]); o = int(b.creation.occ[e])
        pt, _, _ = unrank(t, G, Z, L, PM, QM, tgt)
        exp = list(s); exp.remove(m)
        assert list(tgt[:pt]) == exp and s.count(m) == o, (gid, t, m, o)
        checked += 1
    for e in range(b.annihilation.ptr[i], b.annihilation.ptr[i + 1]):  # add one particle of mode m
        t = int(b.annihilation.index[e]); m = int(b.annihilation.mode[e]); o = int(b.annihilation.occ[e])
        pt, _, _ = unrank(t, G, Z, L, PM, QM, tgt)
        exp = sorted(s + [m])
        assert list(tgt[:pt]) == exp and exp.count(m) == o, (gid, t, m, o)
        checked += 1
print('int64 shard: begin', b.begin, 'rows', b.dim, 'edges checked', checked, flush=True)
# (b) kernel specialization with int64 indices
sp = Space(12, 15, 12, 6)
x = np.random.default_rng(1).standard_normal((sp.dim, 7))
for e in (sp.creation, sp.annihilation):
    y32 = ladder(e.ptr, e.index, e.mode, e.occ, sp.weights, x, np.empty((0, 7)), 6, sp.P, -1)
    y64 = ladder(e.ptr, e.index.astype(np.int64), e.mode, e.occ, sp.weights, x, np.empty((0, 7)), 6, sp.P, -1)
    assert np.array_equal(y32, y64)
print('PASS test_int64', flush=True)
