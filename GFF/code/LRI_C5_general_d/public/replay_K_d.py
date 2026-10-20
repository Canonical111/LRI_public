#!/usr/bin/env python3
"""Public replay of the K_d numbers of the condensed note, Section 21 (gdk:section), from the stored records of
LRI_C5_general_d/K_general.

Added for the public release (2026-10-13, session C63d, which wrote K_general); not part of the research package.
Run from the package folder GFF/code/LRI_C5_general_d (or through C62d's public.mk):

    python3 public/replay_K_d.py [--work .work] [--recompute]

No production run is repeated. The script
  T  re-derives the values table of 21.10: K_d to 32 digits (correct rounding of the 100-digit position-space
     values, K_general/position_space/K_d_values_mb_D100.json) and r3 to 34 digits through gdk:Kr3, with
     s3 the Bell polynomial gdk:sk (checked against a Taylor expansion of gdk:Sclosed);
  S  checks the d = 1, 2, 3 values of 21.8: r3(1) and r3(2) from the closed forms eq:KprovedFinal and gc:K2closed,
     r3(3) and K3 from the 430-digit K3 of ../LRI_C5_d3/wf_K3/K3_value.json;
  R  recomputes the routes table of 21.10: spectral reference (references/reference_values.json), Abel-Plana
     (K_general/refcheck/refcheck_values.json), the five-node and three-node tau-jets extracted through gdk:Ktau
     from the stored 72-digit circles (K_general/R_part/prod/prod_B_d*.json,
     K_general/note_fragment/topmode/results/kjet3_B_d*.json, review/joint/numerics-end-to-end/k3_jets.json), and
     the position-space values against the closed forms and K3;
  C  checks the 'Consistency' and 'Further checks' statements that rest on stored numbers (Laurent tables of
     K_general/R_part/R_part_results.json, |F2 - 3U/2| of the circles, the vanishing t^0, t^1 orders and the
     second-contour runs of position_space/, the double-precision Barnes check fragment_checks/check_barnes.json).
With --recompute it also reruns the position-space code K_general/position_space/kmb_flint.py (unchanged, in a
copy) at 40 digits for d = 1, 2, 3 and compares with the stored 40-digit and 100-digit values (about 15 s;
needs python-flint). Writes <work>/replay_K_d/REPLAY_K_d.md; exits 1 on any FAIL.
Inputs outside K_general: references/reference_values.json, review/joint/numerics-end-to-end/k3_jets.json (this
package) and ../LRI_C5_d3/wf_K3/K3_value.json (sibling package; the rows that need it are SKIPped if it is absent).
Nothing is read from foundation/.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]                 # LRI_C5_general_d
KG = PKG / 'K_general'
DS = ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']


class Report:
    def __init__(self):
        self.rows = []

    def add(self, group, name, status, value, expected, tol, source):
        self.rows.append([group, name, status, str(value), str(expected), str(tol), source])
        print('%-3s %-5s %-44s %-28s %s' % (group, status, name, str(value)[:28], expected), flush=True)

    def check(self, group, name, ok, value, expected, tol, source):
        self.add(group, name, 'PASS' if ok else 'FAIL', value, expected, tol, source)

    def nfail(self):
        return sum(r[2] == 'FAIL' for r in self.rows)


def load(p):
    return json.load(open(p))


def sig(x, n):
    return mp.nstr(x, n, min_fixed=-mp.inf, max_fixed=mp.inf, strip_zeros=False)


def two(x):
    return '%.1e' % float(x)


def one(x):
    return '%.0e' % float(x)


def xh(q, h):
    x = mp.psi(h - 1, 1) - (-1) ** h * mp.psi(h - 1, 2 * q)
    if h % 2:
        x -= mp.mpf(2) ** (3 - h) * mp.psi(h - 1, q)
    return x


def s3_bell(q):
    x1, x2, x3, x4 = (xh(q, h) for h in (1, 2, 3, 4))
    return (x1 ** 4 + 6 * x1 ** 2 * x2 + 4 * x1 * x3 + 3 * x2 ** 2 + x4) / 24


def s3_taylor(q):
    f = lambda t: mp.gamma(2 * q) * mp.gamma(1 + t) * mp.gamma(q - t / 2) ** 4 / (mp.gamma(2 * q - t) * mp.gamma(q + t / 2) ** 4)
    return mp.taylor(f, 0, 4)[4]


def pref(q):
    return mp.psi(2, q) / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q))


def circle(pts, N, r, kre, kim):
    taus, f = {}, {}
    for s in range(N // 2 + 1):
        t = r * mp.expj(2 * mp.pi * s / N)
        if s == 0 or s == N // 2:
            t = mp.mpf(mp.re(t))
        taus[s] = t
        f[s] = mp.mpc(pts[str(s)][kre], pts[str(s)][kim])
    for s in range(N // 2 + 1, N):
        taus[s] = mp.conj(taus[N - s]); f[s] = mp.conj(f[N - s])
    return taus, f


def coef(taus, f, N, k):
    return mp.re(mp.fsum(f[s] * taus[s] ** (-k) for s in range(N)) / N)


def jet_routes(dk, pts, N, r):
    """K_d from one stored tau-circle of <t^2 R_tau>_d: gdk:Ktau and gdk:Kr3 (as in check_k3_routes.py)."""
    with mp.workdps(72):
        q = mp.mpf(dk) / 4
        A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
        U = mp.psi(2, q)
        taus, tR = circle(pts, N, mp.mpf(r), 'Re_tR', 'Im_tR')
        F = {}
        for s in range(N):
            t = taus[s]
            C = mp.gamma(2 * q) * mp.gamma(t) / mp.gamma(2 * q - t)
            Xd = (mp.gamma(q - t / 2) / mp.gamma(q + t / 2)) ** 2
            F[s] = C * tR[s] - C ** 2 * Xd ** 2
        Ktau = -A * U / 4 + coef(taus, F, N, 2) / 4
        r3 = coef(taus, tR, N, 3)
        with mp.workdps(110):
            s3 = s3_taylor(q)
        Kr3 = pref(q) + (r3 - s3) / 4
        return +Ktau, +Kr3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG / '.work'))
    ap.add_argument('--k3', default=str(PKG.parent / 'LRI_C5_d3' / 'wf_K3' / 'K3_value.json'))
    ap.add_argument('--recompute', action='store_true')
    a = ap.parse_args()
    W = Path(a.work).resolve() / 'replay_K_d'
    shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
    t0 = time.time()
    E = load(Path(__file__).resolve().parent / 'expected_K_d.json')
    rep = Report()
    mp.mp.dps = 120
    mb = load(KG / 'position_space/K_d_values_mb_D100.json')['values']
    K = {d: mp.mpf(mb[d]['K']) for d in DS}
    G, z3, gE, l2, pi = mp.catalan, mp.zeta(3), mp.euler, mp.log(2), mp.pi
    K1 = 128 * G ** 2 + 24 * pi ** 2 * G - 4 * pi ** 3 * l2 - 28 * (pi + 4 * l2) * z3
    K2 = 32 * G ** 2 - 28 * z3 * l2
    have_k3 = Path(a.k3).exists()
    K3 = mp.mpf(load(a.k3)['K3']) if have_k3 else None
    src_mb = 'K_general/position_space/K_d_values_mb_D100.json'

    # T: values table
    worst_p, worst_m, worst_bt = 0, 0, 0
    for d in DS:
        q = mp.mpf(d) / 4
        Kp, rp = E['values_table']['rows'][d]
        rep.check('T', 'K_d(%s) 32 digits' % d, sig(K[d], 32) == Kp, sig(K[d], 34), Kp, 'correct rounding', src_mb)
        s3 = s3_bell(q)
        worst_bt = max(worst_bt, abs(s3 - s3_taylor(q)))
        r3 = s3 + 4 * (K[d] - pref(q))
        rep.check('T', 'r3(%s) 34 digits' % d, sig(r3, 34) == rp, sig(r3, 36), rp, 'correct rounding', 'gdk:Kr3 with ' + src_mb)
        Kback = pref(q) + (mp.mpf(rp) - s3) / 4
        worst_p = max(worst_p, abs(Kback - mp.mpf(Kp)) / K[d])
        worst_m = max(worst_m, abs(Kback - K[d]) / K[d])
    rep.check('T', 's3 Bell polynomial = Taylor of gdk:Sclosed', worst_bt <= mp.mpf('1e-100'), mp.nstr(worst_bt, 3), '0',
              '1e-100 abs', 'gdk:sk vs gdk:Sclosed')
    rep.check('T', 'Kr3(printed r3) vs printed K', worst_p <= mp.mpf(E['values_table']['text']['Kr3_printed_vs_printed_K']),
              mp.nstr(worst_p, 3), E['values_table']['text']['Kr3_printed_vs_printed_K'], 'relative, max over d', 'note 21.10 text')
    rep.check('T', 'Kr3(printed r3) vs 100-digit K', worst_m <= mp.mpf(E['values_table']['text']['Kr3_printed_vs_100digit_K']),
              mp.nstr(worst_m, 3), E['values_table']['text']['Kr3_printed_vs_100digit_K'], 'relative, max over d', 'note 21.10 text')

    # S: d = 1, 2, 3 of 21.8
    sp_ = E['special']
    r3c = {'1': s3_bell(mp.mpf(1) / 4) + 4 * K1 - 2 * (pi ** 3 + 28 * z3) * (3 * gE + 7 * l2 + pi),
           '2': s3_bell(mp.mpf(1) / 2) + 128 * G ** 2 - 168 * z3 * l2 - 42 * gE * z3}
    for d in ('1', '2'):
        rep.check('S', 'r3(%s) closed form' % d, sig(r3c[d], 34) == sp_['r3_' + d], sig(r3c[d], 36), sp_['r3_' + d],
                  'correct rounding', 'note 21.8 (closed form %s)' % ('eq:KprovedFinal' if d == '1' else 'gc:K2closed'))
    idd = abs(pref(mp.mpf(1) / 4) - (pi ** 3 + 28 * z3) * (3 * gE + 7 * l2 + pi) / 2)
    rep.check('S', 'd=1 prefactor identity', idd <= mp.mpf('1e-100'), mp.nstr(idd, 3), '0', '1e-100 abs',
              '(U/8)[psi(1)+psi(1/2)+4psi(1/4)] = (pi^3+28z3)(3gE+7log2+pi)/2')
    if have_k3:
        r33 = s3_bell(mp.mpf(3) / 4) + 4 * (K3 - pref(mp.mpf(3) / 4))
        rep.check('S', 'r3(3) from 430-digit K3', sig(r33, 34) == sp_['r3_3'], sig(r33, 36), sp_['r3_3'], 'correct rounding',
                  'note 21.8; ../LRI_C5_d3/wf_K3/K3_value.json')
        unit = mp.mpf(10) ** -38
        rep.check('S', 'K3 39 digits', abs(K3 - mp.mpf(sp_['K3'])) <= unit, sig(K3, 41), sp_['K3'],
                  'one unit in the last digit', 'note 21.8; ../LRI_C5_d3/wf_K3/K3_value.json')
        rep.check('S', 'K3 position space vs 430-digit', two((K['3'] - K3) / K3) == sp_['K3_vs_MB'], two((K['3'] - K3) / K3),
                  sp_['K3_vs_MB'], 'two significant digits', 'note 21.8, 21.10')
    else:
        for n in ('r3(3) from 430-digit K3', 'K3 39 digits', 'K3 position space vs 430-digit'):
            rep.add('S', n, 'SKIP', 'LRI_C5_d3 absent', '-', '-', a.k3)

    # R: routes table
    rows = E['routes_table']['rows']
    ref = load(PKG / 'references/reference_values.json')['values']
    rc = load(KG / 'refcheck/refcheck_values.json')['values']
    k3j = load(PKG / 'review/joint/numerics-end-to-end/k3_jets.json')
    H5, H3 = {}, {}
    for d in DS:
        exp_ref, exp_ap, exp5, exp3, exp_pos = rows[d]
        if exp_ref != '-':
            x = (mp.mpf(ref['d=' + d]['K']['value']) - K[d]) / K[d]
            rep.check('R', 'spectral reference d=%s' % d, two(x) == exp_ref, two(x), exp_ref, 'two significant digits',
                      'references/reference_values.json')
        if exp_ap != '-':
            x = (mp.mpf(rc['d=' + d]['K']['value']) - K[d]) / K[d]
            rep.check('R', 'Abel-Plana d=%s' % d, two(x) == exp_ap, two(x), exp_ap, 'two significant digits',
                      'K_general/refcheck/refcheck_values.json')
        js = load(KG / ('R_part/prod/prod_B_d%s.json' % d))
        Kt, _ = jet_routes(d, js['points'], int(js['N']), js['r'])
        H5[d] = Kt
        x = (Kt - K[d]) / K[d]
        xs = (mp.mpf(js['K_d']) - K[d]) / K[d]
        rep.check('R', 'five-node jet d=%s' % d, two(x) == exp5 and two(xs) == exp5, two(x), exp5,
                  'two significant digits (recomputed and stored K_d)', 'K_general/R_part/prod/prod_B_d%s.json, gdk:Ktau' % d)
        if exp3 != '-':
            if d in ('0.8', '1.25', '2.75'):
                js = load(KG / ('note_fragment/topmode/results/kjet3_B_d%s.json' % d))
                Kt, _ = jet_routes(d, js['points'], int(js['N']), js['r'])
                srcf = 'K_general/note_fragment/topmode/results/kjet3_B_d%s.json' % d
            else:
                Kt, Kr = jet_routes(d, k3j['points'][d], int(k3j['N']), k3j['r'])
                srcf = 'review/joint/numerics-end-to-end/k3_jets.json'
                er = E['routes_table']['three_node_Kr3_route'][d]
                xr = (Kr - K[d]) / K[d]
                rep.check('R', 'three-node jet d=%s via gdk:Kr3' % d, two(xr) == er, two(xr), er, 'two significant digits',
                          srcf + ' (note 21.10 Routes)')
            H3[d] = Kt
            x = (Kt - K[d]) / K[d]
            rep.check('R', 'three-node jet d=%s' % d, two(x) == exp3, two(x), exp3, 'two significant digits', srcf + ', gdk:Ktau')
        if exp_pos != '-':
            exact = {'1': K1, '2': K2, '3': K3}[d]
            if exact is None:
                rep.add('R', 'position space vs exact d=%s' % d, 'SKIP', 'LRI_C5_d3 absent', exp_pos, '-', a.k3)
            else:
                x = (K[d] - exact) / exact
                rep.check('R', 'position space vs exact d=%s' % d, two(x) == exp_pos, two(x), exp_pos, 'two significant digits',
                          src_mb + ' vs eq:KprovedFinal / gc:K2closed / K3')

    # C: consistency and further checks
    cons = E['consistency']
    for d in ('1', '2', '3'):
        exact = {'1': K1, '2': K2, '3': K3}[d]
        if exact is None:
            continue
        x = abs(H5[d] - exact) / exact
        e = cons['five_node_vs_closed'][d]
        got = one(x) if len(e.split('e')[0].replace('.', '')) == 1 else two(x)
        rep.check('C', 'five-node vs closed form d=%s' % d, got == e, got, e, 'printed significant digits', 'note 21.8 Consistency')
    lau = load(KG / 'R_part/R_part_results.json')['6_laurent_of_tR']['values']
    dev = max(abs(mp.mpf(lau['d=1']['tau^3']) - r3c['1']), abs(mp.mpf(lau['d=2']['tau^3']) - r3c['2']))
    rep.check('C', 'sampled r3(1), r3(2) vs closed forms', dev <= mp.mpf(cons['sampled_r3_vs_closed_d12']), mp.nstr(dev, 3),
              cons['sampled_r3_vs_closed_d12'], 'abs', 'K_general/R_part/R_part_results.json')
    fu = E['further']
    lo, kr = 0, 0
    for d in DS:
        q = mp.mpf(d) / 4
        L = lau['d=' + d]
        x1, x2 = xh(q, 1), xh(q, 2)
        s0, s1 = x1, (x1 ** 2 + x2) / 2
        s2 = (x1 ** 3 + 3 * x1 * x2 + xh(q, 3)) / 6
        lo = max(lo, abs(mp.mpf(L['tau^0']) - s0), abs(mp.mpf(L['tau^1']) - s1),
                 abs(mp.mpf(L['tau^2']) - s2 - mp.mpf(3) / 2 * mp.psi(2, q)))
        kr = max(kr, abs(pref(q) + (mp.mpf(L['tau^3']) - s3_bell(q)) / 4 - K[d]) / K[d])
    rep.check('C', 'low orders r0-s0, r1-s1, r2-s2-3U/2', lo <= mp.mpf(fu['low_orders_max']), mp.nstr(lo, 3), fu['low_orders_max'],
              'abs, max over 8 d', 'K_general/R_part/R_part_results.json (34-digit Laurent tables)')
    rep.check('C', 'gdk:Kr3 with Laurent r3 vs K_d', kr <= mp.mpf(fu['Kr3_laurent_vs_K']), mp.nstr(kr, 3), fu['Kr3_laurent_vs_K'],
              'relative, max over 8 d', 'K_general/R_part/R_part_results.json')
    f2 = []
    for d in DS:
        js = load(KG / ('R_part/prod/prod_B_d%s.json' % d))
        f2.append(abs(mp.mpf(js['tE2']) - mp.mpf(3) / 2 * mp.psi(2, mp.mpf(d) / 4)))
    lo_, hi_ = fu['F2_minus_3U2_range']
    rep.check('C', '|F2 - 3U/2| range in the 72-digit jets', one(min(f2)) == lo_ and one(max(f2)) == hi_,
              '%s .. %s' % (one(min(f2)), one(max(f2))), '%s .. %s' % (lo_, hi_), 'one significant digit',
              'K_general/R_part/prod/prod_B_d*.json (tE2)')
    t01 = max(max(abs(mp.mpf(mb[d]['check_t0'])), abs(mp.mpf(mb[d]['check_t1']))) for d in DS)
    rep.check('C', 'MB orders t^0, t^1 vanish', t01 <= mp.mpf(fu['MB_orders_t0_t1']), mp.nstr(t01, 3), fu['MB_orders_t0_t1'],
              'abs, max over 8 d', src_mb + ' (check_t0, check_t1)')
    for d, e in fu['three_vs_five_node'].items():
        x = abs(H3[d] - H5[d]) / K[d]
        rep.check('C', 'three-node vs five-node d=%s' % d, two(x) == two(mp.mpf(e)) or one(x) == e, two(x), e,
                  'printed significant digits', 'note 21.10 Three nodes')
    cont = 0
    for f in sorted(glob.glob(str(KG / 'position_space/K_mb_d*_D50_c*.json'))):
        dd = load(f)
        cont = max(cont, abs(mp.mpf(dd['K']) - K[dd['d']]) / K[dd['d']])
    rep.check('C', 'second contour and step (D50 runs)', 0 < cont <= mp.mpf(fu['contours_and_steps']), mp.nstr(cont, 3),
              fu['contours_and_steps'], 'relative, max over d = 0.8, 1.25, 1.5, 2.5',
              'K_general/position_space/K_mb_d*_D50_c*.json vs D100')
    cb = load(KG / 'note_fragment/fragment_checks/check_barnes.json')
    cl = load(KG / 'note_fragment/fragment_checks/check_laurent.json')['position_space']
    kmax = max(v['K_rel_dev_vs_MB'] for v in cb.values())
    idrel = max(max(v['id0_dev'] / abs(float(cl[d]['id0_rhs'])), v['id1_dev'] / abs(float(cl[d]['id1_rhs']))) for d, v in cb.items())
    idabs = max(max(v['id0_dev'], v['id1_dev']) for v in cb.values())
    bp = fu['barnes_double_precision']
    rep.check('C', 'double-precision Barnes check: K_d', one(kmax) == bp['K'], '%.2e' % kmax, bp['K'], 'relative, max over 8 d, one digit',
              'K_general/note_fragment/fragment_checks/check_barnes.json (stored)')
    rep.check('C', 'double-precision Barnes check: identities', idrel <= float(bp['identities']),
              'rel %.1e (abs %.1e)' % (idrel, idabs), bp['identities'], 'relative to the right side, max over 8 d',
              'check_barnes.json (fa71533 wording; holds only as a relative bound)')
    rep.check('C', 'identities, corrected wording', idabs <= float(bp['identities_abs_corrected']) and
              one(idrel) == bp['identities_rel_corrected'], 'abs %.1e, rel %s' % (idabs, one(idrel)),
              '%s abs, %s rel' % (bp['identities_abs_corrected'], bp['identities_rel_corrected']),
              'abs bound; relative to one digit', 'check_barnes.json (proposed body-text correction of 21.10)')

    if a.recompute:
        try:
            import flint  # noqa: F401
            ok_flint = True
        except ImportError:
            ok_flint = False
        if not ok_flint:
            rep.add('X', 'kmb_flint.py rerun', 'SKIP', 'python-flint missing', '-', '-', 'pip install python-flint')
        else:
            d0 = W / 'kmb'; d0.mkdir()
            shutil.copy2(KG / 'position_space/kmb_flint.py', d0)
            for d in ('1', '2', '3'):
                t = time.time()
                p = subprocess.run([sys.executable, 'kmb_flint.py', d, '40'], cwd=str(d0), capture_output=True, text=True)
                if p.returncode:
                    rep.check('X', 'kmb_flint.py d=%s 40 digits' % d, False, 'rc=%d' % p.returncode, '-', '-', p.stderr[-200:])
                    continue
                new = load(d0 / ('K_mb_d%s_D40.json' % d))
                old = load(KG / ('position_space/K_mb_d%s_D40.json' % d))
                dv = abs(mp.mpf(new['K']) - K[d]) / K[d]
                rep.check('X', 'kmb_flint.py d=%s 40 digits' % d, new['K'] == old['K'] and dv <= mp.mpf('1e-38'),
                          'stored D40 %s; vs D100 %s' % ('identical' if new['K'] == old['K'] else 'differs', mp.nstr(dv, 3)),
                          'identical; 1e-38', 'string; relative', 'position_space/kmb_flint.py %s 40 (%.0f s)' % (d, time.time() - t))

    n = {s: sum(r[2] == s for r in rep.rows) for s in ('PASS', 'FAIL', 'SKIP')}
    lines = ['# K_d replay (LRI_C5_general_d/K_general, note Section 21)', '',
             'Python %s, mpmath %s, %.1f s.' % (sys.version.split()[0], mp.__version__, time.time() - t0), '',
             'Result: **%s** (%d PASS, %d FAIL, %d SKIP)' % ('FAIL' if n['FAIL'] else 'PASS', n['PASS'], n['FAIL'], n['SKIP']), '',
             '| group | check | status | value | expected | tolerance | source |', '|---|---|---|---|---|---|---|']
    lines += ['| ' + ' | '.join(c.replace('|', '/') for c in r) + ' |' for r in rep.rows]
    (W / 'REPLAY_K_d.md').write_text('\n'.join(lines) + '\n')
    print('%s: %d checks, %d FAIL, %d SKIP; table in %s' % ('FAIL' if n['FAIL'] else 'PASS', len(rep.rows), n['FAIL'], n['SKIP'],
                                                            W / 'REPLAY_K_d.md'))
    sys.exit(1 if n['FAIL'] else 0)


if __name__ == '__main__':
    main()
