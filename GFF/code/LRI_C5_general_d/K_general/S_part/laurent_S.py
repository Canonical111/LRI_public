#!/usr/bin/env python3
"""Laurent data of the closed-form S family at generic d (route S_part), for the K_d assembly.

  <t_l^2 S_tau>_d = C(tau) X_d(tau)^2,  C = Gamma(2q)Gamma(tau)/Gamma(2q-tau),  X_d = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2
                  = tau^-1 exp(sum_k eps_k tau^k),
  eps_k = [psi_{k-1}(1) - (-1)^k psi_{k-1}(2q) - [k odd] 2^(3-k) psi_{k-1}(q)] / k!.
  s_k  = [tau^k] <t^2 S_tau>_d   (k = -1..3);   g_k = [tau^k] C(tau)^2 X_d(tau)^2   (k = -2..2);   C_k = [tau^k] C(tau).
  K_d = -AU/4 + (F_3 + c* F_2)/4,  F_k = R_k - s_k,  R_k = [tau^k]<t^2 R_tau>_d  (gs:Kspectral)
      = -AU/4 - g_2/4 + (1/4)[tau^2] J_{2 tau},   J_{2 tau} = C(tau) <t^2 R_tau>_d.
  Exact constraints on the R family (F = O(tau^2)):  R_{-1} = 1, R_0 = s_0, R_1 = s_1.
All numbers here are closed-form polygamma values evaluated with mpmath; cross-checked against a Cauchy-circle Taylor
extraction of the closed form (column 'check').
"""
import json, os
import mpmath as mp

mp.mp.dps = 60
DS = ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']


def data(dstr):
    d = mp.mpf(dstr); q = d / 4
    pg = mp.polygamma
    A = pg(0, 2 * q) + pg(0, 1) - 2 * pg(0, q)
    R = pg(1, 2 * q) - pg(1, 1)
    U = pg(2, q)
    V = pg(2, 1) + pg(2, 2 * q)
    X = pg(3, 2 * q) - pg(3, 1)
    cs = pg(0, 1) + pg(0, 2 * q)
    eps = [None] + [(pg(k - 1, 1) - (-1) ** k * pg(k - 1, 2 * q) - (2 ** (3 - k) * pg(k - 1, q) if k % 2 else 0)) / mp.factorial(k)
                    for k in range(1, 6)]
    # Bell polynomials: exp(sum eps_k x^k) = sum b_j x^j
    b = [mp.mpf(1)] + [0] * 5
    for j in range(1, 6):
        b[j] = mp.fsum(k * eps[k] * b[j - k] for k in range(1, j + 1)) / j
    s = {k: b[k + 1] for k in range(-1, 4)}                       # tau^-1 * sum b_j tau^j
    # C(tau) = tau^-1 exp(sum c_k tau^k), c_k = [psi_{k-1}(1) - (-1)^k psi_{k-1}(2q)]/k!
    cc = [None] + [(pg(k - 1, 1) - (-1) ** k * pg(k - 1, 2 * q)) / mp.factorial(k) for k in range(1, 6)]
    bc = [mp.mpf(1)] + [0] * 5
    for j in range(1, 6):
        bc[j] = mp.fsum(k * cc[k] * bc[j - k] for k in range(1, j + 1)) / j
    Ck = {k: bc[k + 1] for k in range(-1, 4)}
    # g = C * (C X^2) = tau^-2 exp(sum (c_k + eps_k) tau^k)
    e2 = [None] + [cc[k] + eps[k] for k in range(1, 6)]
    bg = [mp.mpf(1)] + [0] * 5
    for j in range(1, 6):
        bg[j] = mp.fsum(k * e2[k] * bg[j - k] for k in range(1, j + 1)) / j
    g = {k: bg[k + 2] for k in range(-2, 3)}
    # independent check: Cauchy-circle Taylor coefficients of tau^2 C^2 X^2 and tau C X^2
    Cf = lambda t: mp.gamma(2 * q) * mp.gamma(t) / mp.gamma(2 * q - t)
    Xf = lambda t: (mp.gamma(q - t / 2) / mp.gamma(q + t / 2)) ** 2
    rho = min(mp.mpf('0.1'), q / 2); M = 64
    pts = [rho * mp.expj(2 * mp.pi * j / M) for j in range(M)]
    vg = [t ** 2 * Cf(t) ** 2 * Xf(t) ** 2 for t in pts]
    vs = [t * Cf(t) * Xf(t) ** 2 for t in pts]
    tc = lambda v, n: mp.fsum(v[j] * mp.expj(-2 * mp.pi * j * n / M) for j in range(M)) / M / rho ** n
    chk = max([abs(tc(vg, n + 2) - g[n]) / max(1, abs(g[n])) for n in range(-2, 3)] +
              [abs(tc(vs, n + 1) - s[n]) / max(1, abs(s[n])) for n in range(-1, 4)])
    # the note's [t^2] Gamma-term formula, t = 2 tau:  g_2 = 4 (A^4/6 - A^2 R/2 + R^2/8 + A(2V-U)/12 - X/48)
    g2_note = 4 * (A ** 4 / 6 - A ** 2 * R / 2 + R ** 2 / 8 + A * (2 * V - U) / 12 - X / 48)
    n = lambda x: mp.nstr(x, 45)
    return {
        'q': n(q), 'A': n(A), 'R': n(R), 'U': n(U), 'V': n(V), 'X': n(X), 'c_star': n(cs), 'psi0_q': n(pg(0, q)),
        's_k (= [tau^k] <t^2 S_tau>_d)': {str(k): n(v) for k, v in s.items()},
        'g_k (= [tau^k] C^2 X_d^2)': {str(k): n(v) for k, v in g.items()},
        'C_k (= [tau^k] C(tau))': {str(k): n(v) for k, v in Ck.items()},
        'minus_AU_over_4': n(-A * U / 4),
        'K_Spart (= -AU/4 - g_2/4; K_d = K_Spart + [tau^2]J_{2tau}/4)': n(-A * U / 4 - g[2] / 4),
        'K_Fform_Spart (= -AU/4 - (s_3 + c* s_2)/4; K_d = this + (R_3 + c* R_2)/4)': n(-A * U / 4 - (s[3] + cs * s[2]) / 4),
        'check_g2_vs_note_formula': mp.nstr(abs(g[2] - g2_note), 3),
        'check_cauchy_maxrel': mp.nstr(chk, 3),
    }


if __name__ == '__main__':
    out = {
        'producer': 'C63d subagent S_part, K_general/S_part/laurent_S.py',
        'formula': '<t_l^2 S_tau>_d = C(tau) X_d(tau)^2 exactly (0<tau<2q), C = Gamma(2q)Gamma(tau)/Gamma(2q-tau), X_d = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2',
        'conventions': 'gs:RS, gs:trace, gs:Kspectral, gs:psiBasis of the condensed note; q = d/4',
        'values': {('d=' + ds): data(ds) for ds in DS},
    }
    # d = 2 sanity: g_2 = 512 log^4 2/3 + 8 zeta3 log 2  (C62d K2_parseval_proof Sec. 6)
    l2 = mp.log(2)
    out['d2_sanity_g2_minus_512log2^4/3-8zeta3log2'] = mp.nstr(mp.mpf(out['values']['d=2']['g_k (= [tau^k] C^2 X_d^2)']['2'])
                                                              - (512 * l2 ** 4 / 3 + 8 * mp.zeta(3) * l2), 3)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laurent_S.json'), 'w'), indent=1)
    for ds, v in out['values'].items():
        print(ds, 's2 =', v['s_k (= [tau^k] <t^2 S_tau>_d)']['2'][:22], ' s3 =', v['s_k (= [tau^k] <t^2 S_tau>_d)']['3'][:22],
              ' g2 =', v['g_k (= [tau^k] C^2 X_d^2)']['2'][:22], ' chk', v['check_g2_vs_note_formula'], v['check_cauchy_maxrel'])
    print('d=2 sanity', out['d2_sanity_g2_minus_512log2^4/3-8zeta3log2'])
