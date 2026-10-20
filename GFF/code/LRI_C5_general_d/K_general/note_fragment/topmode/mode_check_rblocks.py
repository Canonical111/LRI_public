#!/usr/bin/env python3
"""Spin-summed mode check of the R-family sample Xi_R(t;tau) with the R_part Horn-block code (tag topmode).

Uses K_general/R_part/rblocks.py UNCHANGED (copied next to this script at run time; md5 recorded in the output).
For each (d, tau): samples at the five nodes t0 + j/5 (t0 = 0.0917), discrete Fourier transform -> c_k, |k| <= 2,
reconstruction test at two off-grid nodes, and the three-node rule (t0 + j/3) against the five-node rule.
Two truncation settings (K, M) show that |c_{+-2}| sits at the truncation floor while c_0, c_{+-1} are stable.
usage: mode_check_rblocks.py d tau dps out.json
"""
import sys, json, time, hashlib, os
import mpmath as mp
import rblocks as rb


def one(q, tau, K, M, t0=mp.mpf('0.0917')):
    st = time.time()
    n5 = [t0 + mp.mpf(j) / 5 for j in range(5)]
    x5 = [rb.sample(q, t, tau, K, M) for t in n5]
    c = {k: mp.fsum(x * mp.expj(-2 * mp.pi * k * t) for x, t in zip(x5, n5)) / 5 for k in range(-2, 3)}
    rec = []
    for tx in (mp.mpf('0.3331'), mp.mpf('0.7777')):
        x = rb.sample(q, tx, tau, K, M)
        pred = mp.fsum(c[k] * mp.expj(2 * mp.pi * k * tx) for k in c)
        rec.append(abs(pred / x - 1))
    n3 = [t0 + mp.mpf(j) / 3 for j in range(3)]
    x3 = [x5[0]] + [rb.sample(q, t, tau, K, M) for t in n3[1:]]
    v5 = mp.fsum(w * x for w, x in zip(rb.weights(q, tau, n5), x5))
    v3 = mp.fsum(w * x for w, x in zip(rb.weights3(q, tau, n3), x3))
    return c, rec, v5, v3, time.time() - st


if __name__ == '__main__':
    ds, ts, dps, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    mp.mp.dps = dps
    d = mp.mpf(ds); q = d / 4; tau = mp.mpmathify(ts)
    tmin = max(0, mp.re(2 * q - 1), mp.re(mp.mpf(1) / 2 - 2 * q))
    res = dict(d=ds, tau=ts, dps=dps, rblocks_md5=hashlib.md5(open(rb.__file__, 'rb').read()).hexdigest(),
               region=dict(tau_min=mp.nstr(tmin, 6), residue_strip_upper_3q_over_2=mp.nstr(3 * q / 2, 6),
                           in_convergence_region=bool(mp.re(tau) > tmin), in_residue_strip=bool(tmin < mp.re(tau) < 3 * q / 2)),
               settings={})
    for K, M in ((14, 160), (20, 240)):
        c, rec, v5, v3, sec = one(q, tau, K, M)
        scale = max(abs(c[k]) for k in (-1, 0, 1))
        res['settings']['K%d_M%d' % (K, M)] = dict(
            c={str(k): mp.nstr(c[k], 25) for k in c}, abs_c={str(k): mp.nstr(abs(c[k]), 4) for k in c},
            rel_top={'-2': mp.nstr(abs(c[-2]) / scale, 3), '2': mp.nstr(abs(c[2]) / scale, 3)},
            reconstruction_rel_err=[mp.nstr(e, 3) for e in rec],
            tR_5node=mp.nstr(v5, 30), tR_3node=mp.nstr(v3, 30), rel_diff_3_vs_5=mp.nstr(abs(v3 / v5 - 1), 3),
            seconds=round(sec, 1))
        print(json.dumps(res['settings']['K%d_M%d' % (K, M)]), flush=True)
    a, b = (res['settings'][k]['c'] for k in ('K14_M160', 'K20_M240'))
    res['setting_change'] = {k: mp.nstr(abs(mp.mpmathify(a[k]) - mp.mpmathify(b[k])), 3) for k in a}
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'settings'}, indent=1))
