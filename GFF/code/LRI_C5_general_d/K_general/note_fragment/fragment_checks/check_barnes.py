#!/usr/bin/env python3
"""Fragment check 3: independent double-precision evaluation of the position-space Barnes integral I_d
of gdk:positionSpace, written from the typeset formula (no code shared with position_space/kmb_flint.py).

I_d = N (2 pi i)^-2 \int\int dz1 dz2 Phi_0 (l1^2 + l2)/2,  N = Gamma(2q)^2/Gamma(q)^4,
Phi_0 = G(-z1)^2 G(z1)/G(2q-z1) * G(-z2)^2 G(q+z2)/G(q-z2) * G(q+w) G(q-w),  w = z1+z2,
l1 = [psi(z1)+psi(2q-z1)-psi(q-w)-psi(q+w)]/2,  l2 = [psi1(z1)-psi1(2q-z1)+psi1(q-w)-psi1(q+w)]/4,
contour Re z1 = Re z2 = -q/3; trapezoid steps h = s*2*pi*(q/3)/36 with s = 0.6 and 0.45.  Also checks the two Barnes identities (orders t^0, t^1).
Compares K_d = Gamma_2(q) + I_d with the 100-digit MB values (check_laurent.json supplies Gamma_2).
"""
import json, os, sys
import numpy as np
from scipy.special import loggamma, psi as digamma, gammaln

HERE = os.path.dirname(os.path.abspath(__file__))
CL = json.load(open(os.path.join(HERE, 'check_laurent.json')))['position_space']
MB = json.load(open(os.path.join(HERE, '..', '..', 'position_space', 'K_d_values_mb_D100.json')))['values']

B2K = [1/6, -1/30, 1/42, -1/30, 5/66, -691/2730, 7/6]
def trigamma(z):
    z = np.asarray(z, dtype=complex)
    acc = np.zeros_like(z)
    w = z.copy()
    for _ in range(12):                       # shift to Re w >= 12
        acc += 1/w**2
        w = w + 1
    s = 1/w + 1/(2*w**2)
    wp = w**3
    for k, b in enumerate(B2K):
        s += b/wp
        wp = wp*w**2
    return acc + s

def run(d, h_scale=1.0, Y=9.0, chunk=256):
    q = d/4
    c = -q/3
    h = h_scale*2*np.pi*(q/3)/36.0
    n = int(np.ceil(Y/h))
    y = h*np.arange(-n, n+1)
    N = np.exp(2*gammaln(2*q) - 4*gammaln(q))
    pref = N*h*h/(4*np.pi**2)                 # (2 pi i)^-2 dz1 dz2 = dy1 dy2/(4 pi^2)
    I0 = I1 = Id = 0j
    edge = 0.0
    z2 = c + 1j*y
    base2 = 2*loggamma(-z2) + loggamma(q + z2) - loggamma(q - z2)
    for i0 in range(0, len(y), chunk):         # rows of z1, processed in chunks
        z1 = (c + 1j*y[i0:i0+chunk])[:, None]
        w = z1 + z2[None, :]
        lg = (2*loggamma(-z1) + loggamma(z1) - loggamma(2*q - z1)) + base2[None, :] + loggamma(q + w) + loggamma(q - w)
        Phi = np.exp(lg)
        l1 = (digamma(z1) + digamma(2*q - z1) - digamma(q - w) - digamma(q + w))/2
        l2 = (trigamma(z1) - trigamma(2*q - z1) + trigamma(q - w) - trigamma(q + w))/4
        I0 += np.sum(Phi); I1 += np.sum(Phi*l1); Id += np.sum(Phi*(l1**2 + l2)/2)
        edge = max(edge, np.max(np.abs(Phi[:, 0])), np.max(np.abs(Phi[:, -1])))
        if i0 == 0:
            edge = max(edge, np.max(np.abs(Phi[0, :])))
    return pref*I0, pref*I1, pref*Id, edge, 2*n+1

res = {}
for ds in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    d = float(ds)
    out = []
    for hs in (0.6, 0.45):
        out.append(run(d, hs))
    (I0, I1, Id, edge, npts), (I0b, I1b, Idb, _, _) = out
    pp = CL[ds]
    K = float(pp['Gamma2']) + Id.real
    Kmb = float(MB[ds]['K'])
    r = {'npts_per_dim': npts,
         'id0_dev': abs(I0 - float(pp['id0_rhs'])), 'id1_dev': abs(I1 - float(pp['id1_rhs'])),
         'I_d': Id.real, 'Im_I_d': Id.imag, 'I_d_vs_K-Gamma2': abs(Id.real - float(pp['I_d=K-Gamma2'])),
         'K_rel_dev_vs_MB': abs(K - Kmb)/abs(Kmb), 'h_change': abs(Id - Idb), 'edge_size': edge}
    res[ds] = r
    print(ds, {k: ('%.3e' % v if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
json.dump({k: {kk: (float(vv) if not isinstance(vv, int) else vv) for kk, vv in v.items()} for k, v in res.items()},
          open(os.path.join(HERE, 'check_barnes.json'), 'w'), indent=1)
