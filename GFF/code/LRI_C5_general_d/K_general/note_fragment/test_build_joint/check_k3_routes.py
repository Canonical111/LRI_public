#!/usr/bin/env python3
"""Repair round 1, item K6 (routes table): which extraction route each jet entry of gdk:numerics uses.

For every stored tau-circle (|tau| = r, N points, 72 digits) of <t^2 R_tau>_d this script extracts K_d in two ways,
written here from the formulas as typeset in K_d_fragment.tex (no code shared with e2e.py, R_part or topmode):
  Ktau route (gdk:Ktau, first line of gdk:Ksample):
      F(tau) = C(tau) <t^2 R_tau> - C(tau)^2 X_d(tau)^2,  C = Gamma(2q)Gamma(tau)/Gamma(2q-tau),
      X_d = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2,  K = -A U/4 + [tau^2]F / 4;
  Kr3 route (gdk:Kr3):
      r3 = [tau^3]<t^2 R_tau>,  K = (U/8)[psi(1)+psi(2q)+4psi(q)] + (r3 - s3)/4,
      s3 = [tau^3] of gdk:Sclosed, from the Taylor series of tau*C(tau)X_d(tau)^2 (not the Bell form).
Laurent coefficients by the discrete Cauchy formula on the stored circle (conjugate symmetry for the lower half).
Both are compared with the 100-digit position-space values (position_space/K_d_values_mb_D100.json).
Circles:
  five-node   K_general/R_part/prod/prod_B_d*.json              (the five-node column; stored F also checked)
  three-node  K_general/note_fragment/topmode/results/kjet3_B_d{0.8,1.25,2.75}.json   (job 569317)
  three-node  LRI_C5_general_d/review/joint/numerics-end-to-end/k3_jets.json (d = 1.5, 2.5, 3; job 569482)
usage: python3 check_k3_routes.py > check_k3_routes.log
"""
import os, json
import mpmath as mp

mp.mp.dps = 72
HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.abspath(os.path.join(HERE, '..', '..'))                      # K_general
ROOT = os.path.abspath(os.path.join(KG, '..'))                            # LRI_C5_general_d
mb = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']


def circle(pts, N, r, key_re, key_im):
    taus, f = {}, {}
    for s in range(N // 2 + 1):
        t = r * mp.expj(2 * mp.pi * s / N)
        if s == 0 or s == N // 2:
            t = mp.mpf(mp.re(t))
        taus[s] = t
        f[s] = mp.mpc(pts[str(s)][key_re], pts[str(s)][key_im])
    for s in range(N // 2 + 1, N):
        taus[s] = mp.conj(taus[N - s]); f[s] = mp.conj(f[N - s])
    return taus, f


def coef(taus, f, N, k):
    return mp.re(mp.fsum(f[s] * taus[s] ** (-k) for s in range(N)) / N)


def routes(dk, pts, N, r, check_stored_F=False):
    q = mp.mpf(dk) / 4
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    U = mp.psi(2, q)
    taus, tR = circle(pts, N, r, 'Re_tR', 'Im_tR')
    F, dF = {}, mp.mpf(0)
    for s in range(N):
        t = taus[s]
        C = mp.gamma(2 * q) * mp.gamma(t) / mp.gamma(2 * q - t)
        Xd = (mp.gamma(q - t / 2) / mp.gamma(q + t / 2)) ** 2
        F[s] = C * tR[s] - C ** 2 * Xd ** 2
    if check_stored_F:
        _, Fst = circle(pts, N, r, 'Re_F', 'Im_F')
        dF = max(abs(F[s] - Fst[s]) / max(abs(Fst[s]), 1) for s in range(N))
    Ktau = -A * U / 4 + coef(taus, F, N, 2) / 4
    r3 = coef(taus, tR, N, 3)
    g = lambda t: mp.gamma(2 * q) * mp.gamma(1 + t) / mp.gamma(2 * q - t) * (mp.gamma(q - t / 2) / mp.gamma(q + t / 2)) ** 4
    with mp.workdps(110):
        s3 = mp.taylor(g, 0, 4)[4]
    Kr3 = U / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q)) + (r3 - s3) / 4
    KM = mp.mpf(mb[dk]['K'])
    return (Ktau - KM) / KM, (Kr3 - KM) / KM, dF


print('relative deviation from the position-space K_d; Ktau = gdk:Ktau route, Kr3 = gdk:Kr3 route')
print('five-node circles (R_part/prod/prod_B_d*.json); max |F(recomputed) - F(stored)|/max(|F|,1) shown')
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    js = json.load(open(os.path.join(KG, 'R_part', 'prod', 'prod_B_d%s.json' % dk)))
    a, b, dF = routes(dk, js['points'], int(js['N']), mp.mpf(js['r']), True)
    print('  five-node  d=%-4s r=%s  Ktau %10s   Kr3 %10s   stored-F check %s' % (dk, js['r'], mp.nstr(a, 3), mp.nstr(b, 3), mp.nstr(dF, 3)))
print('three-node circles, job 569317 (topmode/results/kjet3_B_d*.json)')
for dk in ['0.8', '1.25', '2.75']:
    js = json.load(open(os.path.join(KG, 'note_fragment', 'topmode', 'results', 'kjet3_B_d%s.json' % dk)))
    a, b, dF = routes(dk, js['points'], int(js['N']), mp.mpf(js['r']), True)
    KM = mp.mpf(mb[dk]['K'])
    stored = (mp.mpf(js['K_d']) - KM) / KM
    print('  three-node d=%-4s r=%s  Ktau %10s   Kr3 %10s   stored-F check %s   stored K_d (Ktau route) %s' % (
        dk, js['r'], mp.nstr(a, 3), mp.nstr(b, 3), mp.nstr(dF, 3), mp.nstr(stored, 3)))
print('three-node circles, job 569482 (review/joint/numerics-end-to-end/k3_jets.json)')
js = json.load(open(os.path.join(ROOT, 'review', 'joint', 'numerics-end-to-end', 'k3_jets.json')))
for dk in ['1.5', '2.5', '3']:
    a, b, _ = routes(dk, js['points'][dk], int(js['N']), mp.mpf(js['r']))
    print('  three-node d=%-4s r=%s  Ktau %10s   Kr3 %10s' % (dk, js['r'], mp.nstr(a, 3), mp.nstr(b, 3)))
