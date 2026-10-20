import sys
import mpmath as mp
sys.path.insert(0, '../foundation')
import hypsums as H0
import hypsums_jet as HJ
from jet import J
mp.mp.dps = 40
q = mp.mpf('1.5') / 4
muD = [mp.mpc((-1) ** (k + 1) / (4 * q)) for k in range(41)]
def conv_found(p):
    X = H0.GammaSeq([(1 + p, 1 + 2 * q + p / 5, 4)])
    Y = H0.GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
    Z = H0.GammaSeq([(1 - 2 * q + p, 1 + p / 2, 4)])
    return H0.conv_sum(X, Y, Z, M=90, N=45, K=40, muY=muD)
def cauchy_d1(f, x0, rho=mp.mpf('0.02'), M=24):
    pts = [x0 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / M) for k in range(M)]
    vals = [f(p) for p in pts]
    return mp.fsum(vals[k] * mp.expjpi(-2 * (k + mp.mpf(1) / 2) / M) for k in range(M)) / M / rho
p0 = mp.mpf('0.2')
pj = J(p0, 1)
X = HJ.GammaSeq([(1 + pj, 1 + 2 * q + pj / 5, 4)])
Y = HJ.GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
Z = HJ.GammaSeq([(1 - 2 * q + pj, 1 + pj / 2, 4)])
cj = HJ.conv_sum(X, Y, Z, M=90, N=45, K=40, muY=muD)
dc = cauchy_d1(conv_found, p0)
print('conv derivative: jet', mp.nstr(cj.d, 30), ' cauchy', mp.nstr(dc, 30), ' rel diff', mp.nstr(abs(cj.d - dc) / abs(cj.d), 3))
