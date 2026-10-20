"""Verify L3 = 4 pi P4(3) - 2 pi^2 X0 + dPhat/db and compute the two derivative constants (session L3).
Phat(b) = -2 pi N(b) [4 c0(b) + 5 c2(b)] + 6 sqrt2 pi N(b) c1(b),  N(b) = [Gamma(3/2-b/2)/Gamma(b/2)]^4,
c_k(b) the Fourier coefficients of the b-deformed sample Xi_4(t;b) = sum_k c_k cos(2 pi k (t + b/4)), c1 = 2 a b.
dH := d/db [N (4 c0 + 5 c2)],  da := d/db [N^(1/2) a],  (N^(1/2) b)' = (pi/2 - log2) b4 exactly (Dougall)."""
import mpmath as mp, sys, json
from load import load
fn = sys.argv[1] if len(sys.argv) > 1 else 'pA_dps170.json'
d, V, D, D2, cen = load(fn, 0)
mp.mp.dps = d['dps']
pi = mp.pi; r2 = mp.sqrt(2); l2 = mp.log(2)
db = lambda k: -D[k] / 2            # d/db = -(1/2) d/dgamma
p4 = (pi ** 2 / 16)                 # pref^4 at b=3/2 ; C_k = p4 N c_k
c0, c1, c2 = V['C0'] / p4, V['C1'] / p4, V['C2'] / p4
a4, b4 = V['A'] / (pi / 4), V['B'] / (pi / 4)
X0 = c0 - c1 / r2
Xh = c0 - c1 + c2
P4 = V['W']
L3 = db('W')
dH = (4 * db('C0') + 5 * db('C2')) / p4
da = db('A') / (pi / 4)
dbb = db('B') / (pi / 4)
Phat_d = -2 * pi * dH + 6 * r2 * pi * 2 * (da * b4 + a4 * dbb)
chk = dict(
    P4_vs_td=P4 - (2 * pi * X0 - 10 * pi * Xh + (14 * r2 - 20) * pi * a4 * b4),
    b4_closed=b4 - mp.gamma(mp.mpf(1) / 4) ** 6 / (16 * pi ** mp.mpf(2.5)),
    Ndb_over_b=dbb / b4 - (pi / 2 - l2),
    L3_formula=L3 - (4 * pi * P4 - 2 * pi ** 2 * X0 + Phat_d),
    L3_formula2=L3 - (4 * pi * P4 - 2 * pi ** 2 * X0 + 6 * r2 * pi * (pi - 2 * l2) * a4 * b4 - 2 * pi * dH + 12 * r2 * pi * b4 * da),
    L3_vs_spectral43=L3 - mp.mpf('-62.710584968387669347296173433534847460001469735251813569'))
for k, v in chk.items():
    print('%-18s %s' % (k, mp.nstr(v, 3)))
vals = dict(L3=L3, P4=P4, X0=X0, Xh=Xh, a4=a4, b4=b4, c0=c0, c1=c1, c2=c2, dH=dH, da=da, Phat_prime=Phat_d,
            U40_34=V['V0q'] / (pi / 4), U41_34=V['V1q'] / (pi / 4), U40_14=V['V0p'] / (pi / 4), U41_14=V['V1p'] / (pi / 4), c4=V['C'] / (pi / 4))
for k, v in vals.items():
    print(k, mp.nstr(v, 60))
json.dump(dict(source=fn, note='values at b=3/2; ~158 established digits (two Cauchy runs agree to <=2e-160)',
               checks={k: mp.nstr(v, 5) for k, v in chk.items()}, values={k: mp.nstr(v, 165) for k, v in vals.items()}),
          open(sys.argv[2] if len(sys.argv) > 2 else 'L3_final_values.json', 'w'), indent=1)
