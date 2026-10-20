"""td-sample form:  L3 = 4 pi P4 - 2 pi^2 Xh + (3 r2 - 4) pi^2 a4 b4 + d/db P(b),
P(b) = N(b)[2 pi X0(b) - 10 pi Xh(b) + (14 r2 - 20) pi a4(b) b4(b)],  X0(b)=Xi_4(t=0;b), Xh(b)=Xi_4(t=1/8;b) (fixed Barnes shift t),
N(b) = [Gamma(3/2-b/2)/Gamma(b/2)]^4.  Equivalently, with ds := d/db[N(2 X0 - 10 Xh)] and da := d/db[N^(1/2) a4]:
L3 = 4 pi P4 - 2 pi^2 Xh + (3 r2 - 4) pi^2 a4 b4 + pi ds + (14 r2 - 20) pi b4 [da + (pi/2 - log 2) a4]."""
import mpmath as mp, sys, json
from load import load
fn = sys.argv[1] if len(sys.argv) > 1 else 'pA_dps170.json'
d, V, D, D2, cen = load(fn, 0)
mp.mp.dps = d['dps']
pi = mp.pi; r2 = mp.sqrt(2); l2 = mp.log(2)
p4 = pi ** 2 / 16
c = [V['C%d' % k] / p4 for k in range(3)]
cd = [-D['C%d' % k] / 2 / p4 for k in range(3)]          # d/db (N c_k)
a4, b4 = V['A'] / (pi / 4), V['B'] / (pi / 4)
da = -D['A'] / 2 / (pi / 4)
X0 = c[0] - c[1] / r2; Xh = c[0] - c[1] + c[2]
P4 = V['W']; L3 = -D['W'] / 2
# fixed-t sample derivatives: Xi(t;b) = sum c_k cos(2 pi k (t + b/4))
def sdot(t):
    return mp.fsum(cd[k] * mp.cos(2 * pi * k * (t + mp.mpf(3) / 8)) - c[k] * (pi * k / 2) * mp.sin(2 * pi * k * (t + mp.mpf(3) / 8)) for k in range(3))
NX0d, NXhd = sdot(0), sdot(mp.mpf(1) / 8)
ds = 2 * NX0d - 10 * NXhd
Pd = pi * ds + (14 * r2 - 20) * pi * (da * b4 + a4 * (pi / 2 - l2) * b4)
res = L3 - (4 * pi * P4 - 2 * pi ** 2 * Xh + (3 * r2 - 4) * pi ** 2 * a4 * b4 + Pd)
print('td-form residual', mp.nstr(res, 3))
print('NX0dot', mp.nstr(NX0d, 50)); print('NXhdot', mp.nstr(NXhd, 50)); print('ds', mp.nstr(ds, 50)); print('dP/db', mp.nstr(Pd, 50))
vals = json.load(open('L3_final_values.json'))
vals['values'].update(NX0dot=mp.nstr(NX0d, 165), NXhdot=mp.nstr(NXhd, 165), ds=mp.nstr(ds, 165), dPdb_tdform=mp.nstr(Pd, 165))
vals['checks']['td_form_residual'] = mp.nstr(res, 5)
json.dump(vals, open('L3_final_values.json', 'w'), indent=1)
