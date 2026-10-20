"""Sharper negative-result bounds: BKZ-reduce the same relation lattice with fpylll, then the Gram-Schmidt bound."""
import mpmath as mp, json, sys, time
from fpylll import IntegerMatrix, LLL, BKZ, GSO
from fpylll.algorithms.bkz2 import BKZReduction
def bkz_bound(vec, dig, block=20):
    with mp.workdps(dig + 20):
        n = len(vec); xm = max(abs(x) for x in vec); C = mp.mpf(10) ** dig / xm / 10
        A = IntegerMatrix(n, n + 1)
        for i, x in enumerate(vec):
            A[i, i] = 1; A[i, n] = int(mp.nint(C * x))
    LLL.reduction(A)
    par = BKZ.Param(block_size=block, strategies=BKZ.DEFAULT_STRATEGY, max_loops=8, flags=BKZ.AUTO_ABORT | BKZ.MAX_LOOPS)
    M = GSO.Mat(A, float_type='mpfr'); M.update_gso()
    BKZReduction(M)(par)
    M.update_gso()
    r = [M.get_r(i, i) for i in range(n)]
    gsmin = mp.sqrt(min(r))
    first = [A[0, j] for j in range(n + 1)]
    return gsmin / mp.sqrt(n * (1 + mp.mpf(n) / 4)), max(abs(c) for c in first[:n])
if __name__ == '__main__':
    from lllrel import tens
    dig = 155
    mp.mp.dps = dig + 20
    v = {k: mp.mpf(x) for k, x in json.load(open('L3_final_values.json'))['values'].items()}
    pi = mp.pi; r2 = mp.sqrt(2); l2 = mp.log(2); ls = mp.log(1 + r2); G = mp.catalan
    Ups = v['U40_34'] * v['U41_34']
    blocks = [v['X0'], v['Xh'], v['a4'] * v['b4'], Ups]
    E8 = [1, r2, pi, pi * r2, l2, l2 * r2, ls, ls * r2]
    cases = {
      'dH ~ blocks x E8 (n=33)': [v['dH']] + [b * e for b in blocks for e in E8],
      'L3 ~ blocks x {1,r2,pi,pir2,pi2,pi2r2,pil2,pil2r2,pils,pilsr2,G,Gr2} (n=49)': [v['L3']] + [b * e for b in blocks for e in [1, r2, pi, pi * r2, pi ** 2, pi ** 2 * r2, pi * l2, pi * l2 * r2, pi * ls, pi * ls * r2, G, G * r2]],
      'da ~ {U40(1/4),U40(3/4),U41(3/4),c4,b4} x E8 (n=41)': [v['da']] + [b * e for b in [v['U40_14'], v['U40_34'], v['U41_34'], v['c4'], v['b4']] for e in E8],
    }
    res = {}
    for name, vec in cases.items():
        t = time.time(); bnd, first = bkz_bound(vec, dig)
        res[name] = dict(bound=mp.nstr(bnd, 4), first_vector_maxcoeff=int(first), seconds=round(time.time() - t, 1))
        print(name, res[name], flush=True)
    json.dump(res, open('bkz_bounds_dig155.json', 'w'), indent=1)
