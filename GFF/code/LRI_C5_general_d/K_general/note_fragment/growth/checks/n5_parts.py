#!/usr/bin/env python3
"""N5: the growth estimate on Omega_q, numerically (PROOF.md Theorem 1 and Corollary 4).

For (q, tau) in Omega_q = {Re tau > max(0, 2q-1, 1/2-2q)} and t = x + i y:
  * each part (right / middle / left) of S_R is bounded by C |y|^-eta (1+log|y|), eta = 2 Re tau - max(0, 1-4q)
    (Theorem 1); printed: P(y) = max_x |part| * |y|^eta  (bounded <=> Theorem 1's exponent holds);
  * the total S_R = right + middle + left is O(e^{-2 pi |y|}) (Corollary 4); printed: max_x |S_R| e^{2 pi |y|}
    and max_x |S_R| e^{4 pi |y|} (the latter bounded <=> c_{+-2} = 0, which is NOT proved here);
  * |Xi_R| e^{-6 pi|y|} |y|^eta (Theorem 1 for Xi_R) and |Xi_R| e^{-4 pi |y|} (Corollary 4).
Evaluator: R_part's regularized blocks (validated at complex t against direct.py in n4_crossval.log), two
settings (K, M) = (24, 400) and (32, 560); the printed 'conv' is the relative change of S_R between them.
usage: n5_parts.py case_index
"""
import sys, json, time
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/K_general/R_part')
import mpmath as mp
import rblocks as rb

mp.mp.dps = 60
CASES = [('1.5', '0.3', '0'), ('0.8', '0.3', '0'), ('2.5', '0.45', '0'), ('3', '0.65', '0'), ('1.25', '0.2', '0.15'),
         ('1.5', '0.08', '0.05')]
XS = ['0.05', '0.3', '0.55', '0.8']
YS = ['1', '2', '3', '4', '5', '-1', '-3', '-5']


def evaluate(q, tau, t, K, M):
    Xi, p = rb.sample(q, t, tau, K, M, parts=True)
    g2 = mp.gamma(2 * q) ** 2
    return dict(right=g2 * p['PR'] * p['HR'], middle=g2 * p['PM'] * p['HM'], left=g2 * p['PL'] * p['HL'],
                S=Xi / p['D'], Xi=Xi)


if __name__ == '__main__':
    ci = int(sys.argv[1])
    ds, tr, ti = CASES[ci]
    q = mp.mpf(ds) / 4
    tau = mp.mpc(tr, ti)
    tstar = max(0, 2 * q - 1, mp.mpf(1) / 2 - 2 * q)
    eta = 2 * mp.re(tau) - max(0, 1 - 4 * q)
    print('d = %s, q = %s, tau = %s;  tau_*(q) = %s,  eta = %s' % (ds, mp.nstr(q, 6), mp.nstr(tau, 6), mp.nstr(tstar, 4), mp.nstr(eta, 4)), flush=True)
    rows = []
    for ys in YS:
        y = mp.mpf(ys)
        st = time.time()
        mx = dict(right=0, middle=0, left=0, S=0, Xi=0)
        conv = 0
        for xs in XS:
            t = mp.mpc(mp.mpf(xs), y)
            v = evaluate(q, tau, t, 24, 400)
            if xs == XS[0]:
                w = evaluate(q, tau, t, 32, 560)
                conv = abs(w['S'] - v['S']) / abs(v['S'])
            for k in mx:
                mx[k] = max(mx[k], abs(v[k]))
        Y = abs(y)
        row = dict(y=ys, conv=mp.nstr(conv, 3),
                   right_y_eta=mp.nstr(mx['right'] * Y ** eta, 8), middle_y_eta=mp.nstr(mx['middle'] * Y ** eta, 8),
                   left_y_eta=mp.nstr(mx['left'] * Y ** eta, 8),
                   S=mp.nstr(mx['S'], 6), S_e2piy=mp.nstr(mx['S'] * mp.exp(2 * mp.pi * Y), 8),
                   S_e4piy=mp.nstr(mx['S'] * mp.exp(4 * mp.pi * Y), 8),
                   Xi_e6pi_yeta=mp.nstr(mx['Xi'] * mp.exp(-6 * mp.pi * Y) * Y ** eta, 6),
                   Xi_e4pi=mp.nstr(mx['Xi'] * mp.exp(-4 * mp.pi * Y), 6), Xi_e2pi=mp.nstr(mx['Xi'] * mp.exp(-2 * mp.pi * Y), 8))
        rows.append(row)
        print('  y=%-3s  max_x|right|y^eta=%-11s |middle|y^eta=%-11s |left|y^eta=%-11s | max|S|=%-10s  |S|e^{2pi|y|}=%-11s |S|e^{4pi|y|}=%-11s'
              ' | |Xi|e^{-6pi|y|}|y|^eta=%-9s |Xi|e^{-4pi|y|}=%-9s |Xi|e^{-2pi|y|}=%-10s conv=%s (%.0fs)'
              % (ys, row['right_y_eta'], row['middle_y_eta'], row['left_y_eta'], row['S'], row['S_e2piy'], row['S_e4piy'],
                 row['Xi_e6pi_yeta'], row['Xi_e4pi'], row['Xi_e2pi'], row['conv'], time.time() - st), flush=True)
    json.dump(dict(d=ds, tau=[tr, ti], eta=mp.nstr(eta, 6), rows=rows), open('n5_case%d.json' % ci, 'w'), indent=1)
