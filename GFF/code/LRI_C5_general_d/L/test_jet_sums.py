"""Unit tests of jet.py / hypsums_jet.py (session L): values vs foundation hypsums, derivatives vs closed forms
and vs numerical differentiation of the foundation's (non-jet) sums."""
import sys, time
import mpmath as mp
sys.path.insert(0, '../foundation')
import hypsums as H0
import hypsums_jet as HJ
from jet import J

mp.mp.dps = 40
# 1. Gauss 2F1(a,b;c;1) with jet a
a0, b, c = mp.mpf('0.3'), mp.mpf('0.45'), mp.mpf('1.9')
a = J(a0, 1)
T = HJ.GammaSeq([(a, c, 1), (b, 1, 1)])
v = HJ.single_sum(T, 0, 60, 40)
ex = mp.gamma(c) * mp.gamma(c - a0 - b) / (mp.gamma(c - a0) * mp.gamma(c - b))
dex = ex * (-mp.psi(0, c - a0 - b) + mp.psi(0, c - a0))
print('Gauss value err', mp.nstr(abs(v.v - ex) / abs(ex), 3), ' deriv err', mp.nstr(abs(v.d - dex) / abs(dex), 3))
# 2. Dixon-type check of a 4th-power sequence derivative vs mp.diff of foundation single_sum
def f_found(p):
    T = H0.GammaSeq([(p, p + mp.mpf('0.6'), 4), (1 - mp.mpf('0.6') + p / 3, 1 + p / 3, 4)])
    return H0.single_sum(T, 0, 60, 40)
p0 = mp.mpf('0.37')
pj = J(p0, 1)
Tj = HJ.GammaSeq([(pj, pj + mp.mpf('0.6'), 4), (1 - mp.mpf('0.6') + pj / 3, 1 + pj / 3, 4)])
vj = HJ.single_sum(Tj, 0, 60, 40)
print('single 4th power: value diff', mp.nstr(abs(vj.v - f_found(p0)), 3),
      ' deriv vs mp.diff', mp.nstr(abs(vj.d - mp.diff(f_found, p0)) / abs(vj.d), 3))
# 3. conv_sum (two-variable Horn) with generic multiplicity: value vs foundation, derivative vs mp.diff
q = mp.mpf('1.5') / 4
def conv_found(p):
    X = H0.GammaSeq([(1 + p, 1 + 2 * q + p / 5, 4)])
    Y = H0.GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
    Z = H0.GammaSeq([(1 - 2 * q + p, 1 + p / 2, 4)])
    muD = [mp.mpc((-1) ** (k + 1) / (4 * q)) for k in range(41)]
    return H0.conv_sum(X, Y, Z, M=90, N=45, K=40, muY=muD)
pj = J(mp.mpf('0.2'), 1)
X = HJ.GammaSeq([(1 + pj, 1 + 2 * q + pj / 5, 4)])
Y = HJ.GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
Z = HJ.GammaSeq([(1 - 2 * q + pj, 1 + pj / 2, 4)])
muD = [mp.mpc((-1) ** (k + 1) / (4 * q)) for k in range(41)]
st = time.time()
cj = HJ.conv_sum(X, Y, Z, M=90, N=45, K=40, muY=muD)
t1 = time.time() - st
cf = conv_found(mp.mpf('0.2'))
with mp.workdps(30):
    dnum = mp.diff(conv_found, mp.mpf('0.2'))
print('conv: value diff', mp.nstr(abs(cj.v - cf), 3), ' deriv vs mp.diff', mp.nstr(abs(cj.d - dnum) / abs(cj.d), 3),
      ' (jet time %.1fs)' % t1)
