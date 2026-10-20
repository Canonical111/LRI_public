#!/usr/bin/env python3
"""N8: the explicit constant of Theorem 4.1 at the six N5 points, against the observed parts.

Per part: |S^->| (and |S^<-|) <= Gamma(2q)^2 c_T e^{pi|Im tau|} C_q c(Y)^2 C_A |y|^-eta (1+log|y|),
          |S^|| <= Gamma(2q)^2 2^max(beta,0) C_q c(Y)^2 C_B |y|^-2Re tau,
with c(Y) = 2^alpha exp(3 kappa(rho)/Y + pi|Im tau|/2), valid for |y| >= Y >= Y_K (Lemma 3.1 used at |z| >= Y).
Prints: kappa(rho_K), Y_K, the constant at Y = Y_K (astronomical: kappa ~ 11 rho^3/3), the Y -> infinity
limit C_inf (c -> 2^alpha e^{pi|Im tau|/2}), and the observed max over the N5 grid of
|part| |y|^eta / (1+log|y|) for comparison.
"""
import json
import mpmath as mp

mp.mp.dps = 20


def dlist(q, L):
    d = [mp.mpf(1)]
    c = 4 * q
    for k in range(L):
        d.append(c)
        c = c * (2 * q + 1 + k) * (4 * q - 1 + k) / ((2 * q + k) * (2 + k))
    return d


def Cq(q, L=20000):
    d = dlist(q, L)
    return max(abs(d[l]) * (1 + l) ** (2 - 4 * q) for l in range(L + 1))


def C1(beta, alpha):
    return 1 + 2 ** (alpha - beta - 1) / (alpha - beta - 1)


def CA_CB(q, alpha):
    beta = 4 * q - 2
    gam = 2 * alpha - max(beta + 1, 0)
    CA = C1(beta, alpha) * (1 + 1 / (gam - 1) + 1 / (gam - 1) ** 2)
    if beta >= 0:
        CB = 2 ** (beta + 1) * C1(beta, alpha) * (1 + 1 / (alpha - 1))
    else:
        CB = (1 / (beta / 2 + 1) + 2 ** (alpha - beta / 2 - 1) / (alpha - beta / 2 - 1)) ** 2
    return CA, CB


def kappa(r):
    return r + mp.mpf(3) / 2 * r ** 2 + mp.mpf(11) / 3 * r ** 3 + mp.mpf(4) / 3


cT = 8 / (1 - mp.exp(-2 * mp.pi)) ** 3
for c in range(6):
    rec = json.load(open('n5_case%d.json' % c))
    q = mp.mpf(rec['d']) / 4
    tau = mp.mpc(rec['tau'][0], rec['tau'][1])
    alpha = 2 * q + mp.re(tau)
    beta = 4 * q - 2
    eta = 2 * mp.re(tau) - max(0, 1 - 4 * q)
    rho = 2 + abs(tau)
    YK = max(2 * rho, 1 + abs(mp.im(tau)))
    CA, CB = CA_CB(q, alpha)
    cq = Cq(q)
    pre = mp.gamma(2 * q) ** 2 * cq

    def const(Y):
        cY = 2 ** alpha * mp.exp(3 * kappa(rho) / Y + mp.pi * abs(mp.im(tau)) / 2)
        return pre * cY ** 2 * (cT * mp.exp(mp.pi * abs(mp.im(tau))) * CA + 2 ** max(beta, 0) * CB)

    obs = 0
    for r in rec['rows']:
        y = abs(mp.mpf(r['y']))
        for key in ('right_y_eta', 'middle_y_eta', 'left_y_eta'):
            obs = max(obs, mp.mpf(r[key]) / (1 + mp.log(y)))
    print('d=%-5s tau=%-10s  kappa(rho_K)=%-8s Y_K=%-6s C(Y_K)=%-10s C_inf=%-9s  observed max |part||y|^eta/(1+log|y|) = %-8s  C_inf/observed = %s'
          % (rec['d'], mp.nstr(tau, 4), mp.nstr(kappa(rho), 5), mp.nstr(YK, 4), mp.nstr(const(YK), 3),
             mp.nstr(const(mp.inf), 4), mp.nstr(obs, 4), mp.nstr(const(mp.inf) / obs, 3)))
