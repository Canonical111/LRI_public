"""Independent evaluation of the retained-spectrum a0, b0, C1 from the note's
Eqs. (Is), (Ie), (AC) and kernels, using indep_blocks (own Casimir recursion) and
own quadrature in (r, theta) with subtraction radius r0 (default 0.25, not 0.2).
Does not import any package module.  Usage: python indep_a0b0.py SPECTRUM_JSON [n] [r0] [K]
"""
import json, sys, time
import numpy as np
from scipy.special import roots_legendre, gammaln
import indep_blocks as ib

spec = json.load(open(sys.argv[1]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 64
r0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
K = int(sys.argv[4]) if len(sys.argv) > 4 else 36
S = next(p['Delta'] for p in spec if p['sector'] == 'odd' and p['ell'] == 0 and p['Delta'] < 1)
E = next(p['Delta'] for p in spec if p['sector'] == 'even' and p['ell'] == 0 and 1 < p['Delta'] < 2)
CHI = 3 - S
print('S,E', S, E, 'n', n, 'r0', r0, 'K', K, flush=True)

def wl(l):  # ell!/(1/2)_ell
    return float(np.exp(gammaln(l + 1) + gammaln(0.5) - gammaln(l + 0.5)))

# ---- quadrature nodes in (r, theta) ----
q, w = roots_legendre(n)
u = (q + 1) / 2; wu = w / 2
pieces = []
for lo, hi, small in [(0, r0, True), (r0, .5, False), (.5, 1., False)]:
    if small:
        r = r0 * u ** 6; wr = 6 * r0 * u ** 5 * wu
    else:
        r = lo + (hi - lo) * u; wr = (hi - lo) * wu
    tlo = np.where(r > .5, np.arccos(np.minimum(1, 1 / (2 * r))), 0.0)
    th = tlo[:, None] + (np.pi - tlo[:, None]) * u[None, :]
    wt = (np.pi - tlo[:, None]) * wu[None, :]
    R = np.broadcast_to(r[:, None], th.shape)
    zz = R * np.exp(1j * th)
    dmu = 2 * np.pi * R ** 2 * np.sin(th) * wr[:, None] * wt
    v = np.abs(1 - zz) ** 2
    pieces.append(dict(z=zz, r=R, v=v, dmu=dmu, small=small))

# nonspectral constants (integrand pieces without blocks)
cb_ = sum(np.sum(p['dmu'] * 2 * p['v'] ** (-CHI) * (p['r'] ** (-2 * S) - p['v'] ** (-S))) for p in pieces)
ca_ = sum(np.sum(p['dmu'] * (-2) * p['v'] ** (-3.0)) for p in pieces)

def ang_avg(k):  # int_{-1}^{1} d eta cos(k theta)
    k = abs(k)
    if k == 1: return 0.0
    return (1 + np.cos(k * np.pi)) / (1 - k * k)

def even_kernels(De, l, Kz=40):
    """Return (Kb, Ke): Kb = AC int dmu [2 v^-chi r^-2S + r^-6] g ; Ke = AC int dmu r^-6 g.
    For Delta<3.5 the small ball r<r0 uses the block's own z-series: the terms with r-exponent
    e=2al+m+n<3.5 are integrated analytically (AC), the rest directly (no cancellation)."""
    al = (De - l) / 2
    ac = 0.0; cz = None
    if De < 3.5:
        cz, _ = ib.coefficients(float(De), int(l), 0.0, 0.0, 3, 'z', Kz)
        for kk in range(Kz + 1):
            e = 2 * al + kk
            if e >= 3.5: break
            terms = [ang_avg(2 * m - kk) * cz[m, kk - m] for m in range(kk + 1)]
            a = sum(terms)
            if abs(a) <= 1e-13 * (sum(abs(t) for t in terms) + 1e-300): continue
            if abs(e - 3) < 1e-12: raise ValueError('log resonance')
            ac += 2 * np.pi * a * r0 ** (e - 3) / (e - 3)
        mask = np.add.outer(np.arange(Kz + 1), np.arange(Kz + 1))
        crem = np.where(2 * al + mask >= 3.5, cz, 0.0)
    Kb = ac; Ke = ac
    for p in pieces:
        g = ib.evaluate(De, l, p['z'], 0, 0, 3, 'rho', K)
        Kb += np.sum(p['dmu'] * 2 * p['v'] ** (-CHI) * p['r'] ** (-2 * S) * g)
        if p['small'] and cz is not None:
            zz = p['z']
            pw = zz[..., None] ** np.arange(Kz + 1); pwb = np.conj(zz)[..., None] ** np.arange(Kz + 1)
            grem = (np.abs(zz) ** (2 * al) * np.einsum('...m,mn,...n->...', pw, crem, pwb)).real
            t = np.sum(p['dmu'] * p['r'] ** (-6.0) * grem)
        else:
            t = np.sum(p['dmu'] * p['r'] ** (-6.0) * g)
        Kb += t; Ke += t
    return np.array([Kb, Ke])

def odd_kernel(De, l):
    return sum(np.sum(p['dmu'] * 2 * p['v'] ** (-CHI) * p['r'] ** (-S - E) * ib.evaluate(De, l, p['z'], E - S, S - E, 3, 'rho', K)) for p in pieces)

t0 = time.time()
ib.recursion('rho'); ib.recursion('z'); print('recursions derived', time.time()-t0, flush=True)
bsum = cb_; asum = ca_; parts = []
for p in spec:
    De, l = p['Delta'], p['ell']
    if p['sector'] == 'even':
        try:
            Kv = even_kernels(De, l)
        except ValueError:
            # null-state (conserved T): block regular at Delta; symmetric average + Richardson in h
            kav = lambda h: 0.5 * (even_kernels(De + h, l) + even_kernels(De - h, l))
            Kv = (4 * kav(2e-4) - kav(4e-4)) / 3
        cbv = wl(l) * p['f'] ** 2 * Kv[0]; cav = wl(l) * p['f'] * p['h'] * Kv[1]
        parts.append(dict(name=p['name'], kernel=(-2 * np.pi * wl(l) * Kv).tolist(), b=-2 * np.pi * cbv, a=-2 * np.pi * cav))
    else:
        Ko = odd_kernel(De, l)
        cbv = 0.0; cav = wl(l) * p['f'] ** 2 * Ko
        parts.append(dict(name=p['name'], kernel=[0.0, -2 * np.pi * wl(l) * Ko], b=0.0, a=-2 * np.pi * cav))
    bsum += cbv; asum += cav
    print('  done', p['name'], round(time.time() - t0, 2), flush=True)
b0 = -2 * np.pi * bsum; a0 = -2 * np.pi * asum
out = dict(n=n, r0=r0, K=K, a0=a0, b0=b0, C1=a0 / b0, const_b=-2 * np.pi * cb_, const_a=-2 * np.pi * ca_, parts=parts, seconds=time.time() - t0)
print(json.dumps({k: v for k, v in out.items() if k != 'parts'}), flush=True)
json.dump(out, open(f'indep_a0b0_n{n}_r{r0}_K{K}.json', 'w'), indent=1)
