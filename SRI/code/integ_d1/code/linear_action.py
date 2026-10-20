"""Linearised action of residual z-shifts on F in the exact-H gauge (beta_z = 4u(1+z), beta_u = 2uF)."""
import sympy as sp
u, z = sp.symbols('u z')
D = 4
F = z
Fs = {}
for m in range(1, D + 1):
    for n in range(0, D + 1 - m):
        s = sp.Symbol(f'F{m}{n}'); Fs[(m, n)] = s; F += s * u**m * z**n
bu, bz = 2 * u * F, 4 * u * (1 + z)
def trunc(e, d):
    p = sp.Poly(sp.expand(e), u, z)
    return sp.Add(*[c * u**i * z**j for (i, j), c in p.terms() if i + j <= d])
def geom(x, d):  # 1/(1+x) truncated
    return sum((-x)**k for k in range(d + 1))
res = {}
for a in range(0, D + 1):
    for b in range(0, D + 1):
        if a + b + 1 > D + 1: continue
        Yz = u * u**a * z**b
        # gauge: z-component of [Y,V] must vanish -> solve for eta
        # [Y,V]_z = eta*d_u bz + Yz*d_z bz - (bu*d_u Yz + bz*d_z Yz)
        eta = sp.expand((bu * sp.diff(Yz, u) + bz * sp.diff(Yz, z) - Yz * sp.diff(bz, z)) * geom(z, D + 2) / 4)
        eta = trunc(eta, D + 2)
        Lu = eta * sp.diff(bu, u) + Yz * sp.diff(bu, z) - (bu * sp.diff(eta, u) + bz * sp.diff(eta, z))
        dF = trunc(sp.expand(Lu / (2 * u)), D)
        P = sp.Poly(dF, u, z)
        res[(a, b)] = {mon: sp.factor(cc) for mon, cc in P.terms() if sum(mon) <= D and cc != 0}
for key in sorted(res, key=lambda t: (t[0] + t[1], t)):
    lead = {m: c for m, c in res[key].items() if all(v not in c.free_symbols for v in Fs.values())}
    print('chi=u^%d z^%d (z-shift degree %d):' % (key[0], key[1], key[0] + key[1] + 1), dict(sorted(lead.items(), key=lambda t: (sum(t[0]), t[0]))))
