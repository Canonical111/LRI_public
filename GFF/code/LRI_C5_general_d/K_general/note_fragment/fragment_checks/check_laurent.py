#!/usr/bin/env python3
"""Fragment check 1 (tag draft, C63d, 2026-10-03): the elementary Laurent algebra of gdk_fragment.

Implements the formulas exactly as typeset in K_d_fragment.tex and checks:
 (a) <t^2 S_tau>_d = C X^2: Laurent coefficients s_k from the Bell form vs direct Taylor of the closed form;
 (b) Delta(tau) = J^Gamma_{2tau} - C^2 X^2 has [tau^-2..0] = 0, [tau^1] = (3/2)U, [tau^2] = A U;
 (c) K_d = (U/8)[psi(1)+psi(2q)+4psi(q)] + (r_3 - s_3)/4 against the 100-digit MB values, using R_part's r_k;
     also r_0 = s_0, r_1 = s_1, r_2 = s_2 + 3U/2;
 (d) exact r_3 at d = 1, 2 from eq:KprovedFinal and gc:K2closed, vs R_part's numerical r_3;
 (e) the position-space polygamma part Gamma_2(q) (for check_barnes.py).
No code is shared with R_part/S_part/position_space; only their stored numbers are read.
"""
import json, os
import mpmath as mp

mp.mp.dps = 60
HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.abspath(os.path.join(HERE, '..', '..'))
MB = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']
RP = json.load(open(os.path.join(KG, 'R_part', 'R_part_results.json')))['6_laurent_of_tR']['values']

psi = lambda m, z: mp.psi(m, z)

def basis(q):
    A = psi(0, 2*q) + psi(0, 1) - 2*psi(0, q)
    R = psi(1, 2*q) - psi(1, 1)
    U = psi(2, q)
    V = psi(2, 1) + psi(2, 2*q)
    X = psi(3, 2*q) - psi(3, 1)
    return A, R, U, V, X

def Cfac(q, tau):
    return mp.gamma(2*q) * mp.gamma(tau) / mp.gamma(2*q - tau)

def Xd(q, tau):
    return (mp.gamma(q - tau/2) / mp.gamma(q + tau/2))**2

def bell_E(xs, m):
    """E_m of fp:BellFinite: exp(sum x_h u^h/h!) = sum E_m u^m"""
    E = [mp.mpf(1)]
    for n in range(1, m+1):
        E.append(mp.fsum(xs[h-1]/mp.factorial(h-1)*E[n-h] for h in range(1, n+1))/n)
    return E[m]

def s_coeffs(q, kmax=3):
    """s_k = [tau^k]<t^2 S_tau>_d, k=-1..kmax, via x_h = psi_{h-1}(1) - (-1)^h psi_{h-1}(2q) - [h odd] 2^{3-h} psi_{h-1}(q)"""
    xs = []
    for h in range(1, kmax+2):
        x = psi(h-1, 1) - (-1)**h * psi(h-1, 2*q)
        if h % 2 == 1:
            x -= mp.mpf(2)**(3-h) * psi(h-1, q)
        xs.append(x)
    return {k: bell_E(xs, k+1) for k in range(-1, kmax+1)}

def laurent(f, kmin, kmax, r=mp.mpf('0.05'), N=96):
    """Laurent coefficients of f at 0 by a Cauchy circle (f meromorphic, pole order <= -kmin)"""
    pts = [r*mp.expj(2*mp.pi*j/N) for j in range(N)]
    vals = [f(z) for z in pts]
    return {k: mp.fsum(v*z**(-k) for v, z in zip(vals, pts))/N for k in range(kmin, kmax+1)}

def JGamma(q, tau):
    """J^Gamma_{2tau} of gs:Kdefinition, written with C and two Gamma ratios"""
    C = Cfac(q, tau)
    g1 = mp.gamma(q - tau)/mp.gamma(q + tau)
    g2 = mp.gamma(q - 2*tau)*mp.gamma(q + tau)/(mp.gamma(q + 2*tau)*mp.gamma(q - tau))
    return C**2*g1**2 + (C/tau)*(g1 - g2)

def Bd(d, a, b):
    """gs:convolution"""
    return (mp.gamma(d/2)*mp.gamma((d-a)/2)*mp.gamma((d-b)/2)*mp.gamma((a+b-d)/2)
            / (mp.gamma(a/2)*mp.gamma(b/2)*mp.gamma((2*d-a-b)/2)))

def JGamma_direct(q, tau):
    d = 4*q
    B1 = Bd(d, 2*q, 4*q - 2*tau)
    B2 = Bd(d, 2*q + 4*tau, 4*q - 2*tau)
    return B1**2 + (B1 - B2)/tau

out = {}
# ---------------------------------------------------------------- (a), (b)
worst_a = worst_b = mp.mpf(0)
for qs in ['0.17', '0.2', '0.3125', '0.41', '0.5', '0.6875', '0.75', '0.9']:
    q = mp.mpf(qs)
    A, R, U, V, X = basis(q)
    # (a) Bell form vs direct Laurent of C X^2, and W_2 identity B_d(d-b',2b') = C X_d at b'=d/2-tau
    sk = s_coeffs(q, 3)
    lS = laurent(lambda z: Cfac(q, z)*Xd(q, z)**2, -1, 3)
    worst_a = max(worst_a, max(abs(sk[k]-lS[k])/max(1, abs(lS[k])) for k in sk))
    tau0 = mp.mpf('0.137')
    w2 = Bd(4*q, 2*q + tau0, 4*q - 2*tau0)        # B_d(d-b', 2b') with b' = 2q - tau
    worst_a = max(worst_a, abs(w2/(Cfac(q, tau0)*Xd(q, tau0)) - 1))
    # (b) Delta = J^Gamma - C^2 X^2
    lD = laurent(lambda z: JGamma(q, z) - (Cfac(q, z)*Xd(q, z))**2, -2, 2)
    lD2 = laurent(lambda z: JGamma_direct(q, z) - (Cfac(q, z)*Xd(q, z))**2, -2, 2)
    target = {-2: 0, -1: 0, 0: 0, 1: mp.mpf(3)/2*U, 2: A*U}
    dev = max(abs(lD[k]-target[k])/max(1, abs(target[k])) for k in target)
    dev2 = max(abs(lD2[k]-lD[k]) for k in target)
    worst_b = max(worst_b, dev, dev2)
    out['q=%s' % qs] = {'Bell_vs_Taylor_and_W2': mp.nstr(worst_a, 3), 'Delta_Laurent_dev': mp.nstr(dev, 3),
                        'JGamma_two_forms': mp.nstr(dev2, 3)}
print('(a) s_k Bell form and W_2 = B_d identity: worst', mp.nstr(worst_a, 3))
print('(b) Delta Laurent [-2..2] = (0,0,0,3U/2,AU): worst', mp.nstr(worst_b, 3))

# ---------------------------------------------------------------- (c), (d)
EG = mp.euler
G = mp.catalan
z3 = mp.zeta(3)
L2 = mp.log(2)
K1 = 128*G**2 + 24*mp.pi**2*G - 4*mp.pi**3*L2 - 28*(mp.pi + 4*L2)*z3       # eq:KprovedFinal
K2 = 32*G**2 - 28*z3*L2                                                     # gc:K2closed
rows = []
for ds in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    d = mp.mpf(ds); q = d/4
    A, R, U, V, X = basis(q)
    sk = s_coeffs(q, 3)
    rk = {int(k.replace('tau^', '')): mp.mpf(v) for k, v in RP['d=' + ds].items()}
    Kmb = mp.mpf(MB[ds]['K'])
    elem = U/8*(psi(0, 1) + psi(0, 2*q) + 4*psi(0, q))
    Kform = elem + (rk[3] - sk[3])/4
    r3_from_K = sk[3] + 4*(Kmb - elem)          # r_3 implied by the 100-digit K
    row = {'d': ds,
           'K_formula_rel_dev': mp.nstr((Kform - Kmb)/Kmb, 3),
           'r0-s0': mp.nstr(rk[0]-sk[0], 3), 'r1-s1': mp.nstr(rk[1]-sk[1], 3),
           'r2-s2-3U/2': mp.nstr(rk[2]-sk[2]-mp.mpf(3)/2*U, 3),
           'r3_from_MB': mp.nstr(r3_from_K, 45), 'r3_Rpart': mp.nstr(rk[3], 34),
           's3': mp.nstr(sk[3], 40), 'elem': mp.nstr(elem, 40),
           'U': mp.nstr(U, 30)}
    if ds == '1':
        row['MB_vs_KprovedFinal'] = mp.nstr(Kmb - K1, 3)
        row['r3_exact'] = mp.nstr(sk[3] + 4*(K1 - elem), 45)
        row['elem_closed_check'] = mp.nstr(elem - (mp.pi**3 + 28*z3)*(3*EG + 7*L2 + mp.pi)/2, 3)
    if ds == '2':
        row['MB_vs_K2closed'] = mp.nstr(Kmb - K2, 3)
        row['r3_exact'] = mp.nstr(sk[3] + 4*(K2 - elem), 45)
        row['elem_closed_check'] = mp.nstr(elem - z3*(21*EG/2 + 14*L2), 3)
    rows.append(row)
    print(row)
out['K_rows'] = rows

# ---------------------------------------------------------------- (e) position-space polygamma part
def Gamma2(q):
    A, R, U, V, X = basis(q)
    th = 2*psi(1, q) - psi(1, 2*q)
    return A**2*th/2 + A*(psi(2, 2*q) - psi(2, q))/2 - R*th/4 + th**2/8 + (2*psi(3, q) - 7*psi(3, 2*q))/48
pp = {}
for ds in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    q = mp.mpf(ds)/4
    A, R, U, V, X = basis(q)
    th = 2*psi(1, q) - psi(1, 2*q)
    pp[ds] = {'Gamma2': mp.nstr(Gamma2(q), 30), 'I_d=K-Gamma2': mp.nstr(mp.mpf(MB[ds]['K']) - Gamma2(q), 30),
              'id0_rhs': mp.nstr(psi(1, 2*q) - 2*psi(1, q), 30),
              'id1_rhs': mp.nstr(-(A*th + psi(2, 2*q)/2 - psi(2, q)), 30)}
out['position_space'] = pp
print(json.dumps(pp, indent=1))
json.dump(out, open(os.path.join(HERE, 'check_laurent.json'), 'w'), indent=1)
