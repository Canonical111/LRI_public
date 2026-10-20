#!/usr/bin/env python3
"""Replay of the large-order (instanton) numbers (new tool, 2026-10-14). Run from code/instanton/.

1. Reruns the verbatim scripts in a copy under <work>/run: lri_instanton_amplitude.py (the d = 1 one-loop amplitude;
   it rewrites results.json, compared with the shipped one), the d = 4 phi^4 benchmark step1_d4_validation.py (McKane's
   MS beta-function constant C_beta and the nu^{-1} amplitude must be reproduced exactly, ratio 1, once the
   constrained-profile shift -9/2 is included; without it the ratio is e^{9/2}), the phi^6 benchmark step1c_phi6_d3.py
   (McKane's general phi^N formula for N = 6, d = 3, ratio 1; the simplified form printed in his Appendix A, Eq. (A10),
   is smaller by a factor 64/pi, checked here exactly), and the convention and spectral-sum checks (step0, step1b,
   step2b, step2c) and the independent re-derivation (independent_verification/c*.py), which must exit 0.
2. Quoted numbers (../../results/quoted_numbers.json, package "instanton"):
   \\RSKI     K_I from the rerun results.json;
   \\RSKIalt  100 (1 - e^{-2 delta_p}): the alternative treatments of the order-z step are K_I e^{-delta_p} (no profile
             shift, 5.681e-3) and K_I e^{-2 delta_p} (opposite sign, 5.167e-3); the larger reduction is quoted;
   \\RSfracLow, \\RSfracEight  100 C_n / [K_I (-1/A_eps)^n Gamma(n+4)] for n = 3..8 with the final C8(1), the smallest
             value and the value at n = 8; C_n from the d = 1 chain record (../resum_d1/.../instanton_mismatch/analysis.json),
             cross-checked against its ratio_table_KI.csv;
   \\RSratioExcess  100 (r_8 A_eps - 1) with r_n = -C_n/[(n + b_I) C_{n-1}] in d = 2 and 3 (../resum_d23/{2d,3d}/results/
             ratios.csv); the paper says "about 16%" for both, so the rule is |value - 16| < 1 for each (16.1 and 16.6).
3. A_eps(1, 2, 3) in closed form against the values used by the resummations (results.json; 2d/3d protocol.json).
Usage: python3 public/replay_instanton.py [--work DIR]
"""
import argparse, csv, json, math, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
CODE = PKG.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import rsum_lib as L
import mpmath as mp

STEPS = ['step0_zero_dim.py', 'step1_d4_validation.py', 'step1b_bubble_check.py', 'step1c_phi6_d3.py', 'step2b_Lsub_check.py',
         'step2c_Lsub_asymptotic.py']


def run(script, cwd):
    r = subprocess.run([sys.executable, '-B', script], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def floats(line):
    return [float(x) for x in re.findall(r'=\s*([-+0-9.eE]+)', line)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    run_dir = work/'run'
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(PKG, run_dir, ignore=shutil.ignore_patterns('public', '.work', '__pycache__'))
    T = L.Table('instanton replay')
    Q, _ = L.quoted(PKG.parent.parent/'results'/'quoted_numbers.json')

    rc, out = run('lri_instanton_amplitude.py', run_dir)
    T.check('lri_instanton_amplitude.py', rc == 0, 'exit %d' % rc, 'exit 0', 'verbatim, in a copy')
    ok, how, bad = L.compare_json(PKG/'results.json', run_dir/'results.json', rtol=1e-12)
    T.check('results.json regenerated', ok, how, 'within 1e-12 relative', 'rerun vs shipped results.json')
    R = json.loads((run_dir/'results.json').read_text())
    logs = {}
    for s in STEPS:
        rc, out = run(s, run_dir)
        logs[s] = out
        T.check(s, rc == 0, 'exit %d' % rc, 'exit 0', 'verbatim check script')
    l1 = [l for l in logs['step1_d4_validation.py'].splitlines() if l.startswith('with profile shift')]
    l0 = [l for l in logs['step1_d4_validation.py'].splitlines() if l.startswith('without profile shift')]
    v1 = floats(l1[0]) if l1 else []
    T.check('d=4 phi^4 benchmark', len(v1) == 2 and all(abs(v - 1) < 1e-10 for v in v1), ', '.join(map(str, v1)), '1, 1',
            "ratios to McKane's C_beta (Eq. 33) and nu^{-1} amplitude (Eq. 50), with the profile shift -9/2")
    v0 = floats(l0[0]) if l0 else []
    T.check('d=4 without profile shift', len(v0) == 2 and abs(v0[0]/math.exp(4.5) - 1) < 1e-10, ', '.join(map(str, v0)),
            'e^{9/2} = %.10g' % math.exp(4.5), 'the shift accounts for exactly e^{9/2}')
    lr = [l for l in logs['step1c_phi6_d3.py'].splitlines() if 'ratio =' in l]
    vr = floats(lr[0]) if lr else []
    T.check('phi^6 d=3 benchmark', len(vr) == 2 and abs(vr[1] - 1) < 1e-12, ', '.join(map(str, vr)), 'ratio 1',
            "pipeline vs McKane's general phi^N formula (App. A, Eqs. A8-A9), N = 6, d = 3")
    mp.mp.dps = 30
    C2 = 4/mp.pi**2*mp.exp(-mp.quad(lambda x: x*mp.log(mp.sin(x)), [0, mp.pi/2])/mp.pi**2)
    general = (2/(mp.pi*16))**2*C2/(2*mp.pi)*mp.mpf(4)/120*8**6
    simplified = 2**(mp.mpf(49)/8)*mp.exp(-7*mp.zeta(3)/(16*mp.pi**2))/(15*mp.pi**4)
    fac = general/simplified
    T.check('McKane Eq. (A10) factor', abs(fac/(64/mp.pi) - 1) < 1e-20, mp.nstr(fac, 15), '64/pi = %s' % mp.nstr(64/mp.pi, 15),
            'general formula / simplified Eq. (A10): the simplified form misses 2^6/pi (not used by the benchmark)')
    for f in sorted((PKG/'independent_verification').glob('c*.py')):
        rc, out = run(str(Path('independent_verification')/f.name), run_dir)
        T.check('independent ' + f.name, rc == 0, 'exit %d' % rc, 'exit 0', 'independent re-derivation script (prints its checks)')

    KI, dp = R['K_I'], R['profile_shift']
    T.quoted(Q['\\RSKI'], [KI], 'K_I of the rerun (C_n ~ K_I (-1/A_eps)^n Gamma(n+4))')
    alt1, alt2 = KI*math.exp(-dp), KI*math.exp(-2*dp)
    T.check('variant without profile shift', abs(alt1/R['K_I_disfavored_variant_without_profile_shift'] - 1) < 1e-12,
            '%.4e' % alt1, '%.4e (results.json)' % R['K_I_disfavored_variant_without_profile_shift'], 'K_I e^{-delta_p}')
    T.quoted(Q['\\RSKIalt'], [100*(1 - alt2/KI)], 'larger reduction among the alternatives: 1 - e^{-2 delta_p} (opposite sign, K_I = %.4e)' % alt2)
    an = json.loads((CODE/'resum_d1'/'update_2026-10-13'/'C8_1_ext'/'instanton_mismatch'/'analysis.json').read_text())
    C = an['inputs']['C']
    A = 9*mp.pi**2/mp.gamma(mp.mpf(1)/4)**4
    frac = {n: float(mp.mpf(C[n])/(KI*(-1/A)**n*mp.gamma(n + 4))) for n in range(3, 9)}
    tab = {int(r['n']): float(r['C_n_over_KI_minus_a_pow_n_Gamma_n_plus_4']) for r in
           csv.DictReader((CODE/'resum_d1'/'update_2026-10-13'/'C8_1_ext'/'instanton_mismatch'/'ratio_table_KI.csv').open())}
    d = max(abs(frac[n]/tab[n] - 1) for n in frac)
    T.check('mismatch ratios vs chain record', d < 1e-9 and abs(C[8] - 8059766.723129955) < 1e-6, '%.1e' % d, '< 1e-9',
            'C_n/[K_I(-1/A)^n Gamma(n+4)], n = 3..8, recomputed vs ratio_table_KI.csv (final C8(1))')
    nmin = min(frac, key=frac.get)
    T.quoted(Q['\\RSfracLow'], [100*frac[nmin]], 'smallest of 100 C_n/[K_I(-1/A)^n Gamma(n+4)], n = 3..8 (n = %d)' % nmin)
    T.quoted(Q['\\RSfracEight'], [100*frac[8]], 'the same at n = 8')
    exc = {}
    for dd in ('2d', '3d'):
        r8 = [r for r in csv.DictReader((CODE/'resum_d23'/dd/'results'/'ratios.csv').open()) if r['n'] == '8'][0]
        exc[dd] = 100*(float(r8['power_corrected'])/float(r8['candidate_limit']) - 1)
    ok = all(abs(v - 16) < 1 for v in exc.values())
    st = 'PASS' if ok else 'FAIL'
    if Q['\\RSratioExcess']['status'] != 'printed':
        st = 'INFO'
    T.add('\\RSratioExcess', st, '2d %.2f, 3d %.2f' % (exc['2d'], exc['3d']), Q['\\RSratioExcess']['text'],
          '100 (r_8 A_eps - 1), r_n = -C_n/[(n+b_I)C_{n-1}] (ratios.csv); "about 16": |value - 16| < 1 in both dimensions')
    A1 = float(9*mp.pi**2/mp.gamma(mp.mpf(1)/4)**4)
    A3 = float(mp.mpf(9)/4*(mp.gamma(mp.mpf(9)/4)/mp.gamma(mp.mpf(3)/4))**2)
    P2 = json.loads((CODE/'resum_d23'/'2d'/'inputs'/'protocol.json').read_text())['A_epsilon']
    P3 = json.loads((CODE/'resum_d23'/'3d'/'inputs'/'protocol.json').read_text())['A_epsilon']
    T.check('A_eps(1)', abs(A1 - R['A_eps']) < 1e-15, '%.15g' % A1, '%.15g (results.json)' % R['A_eps'], '9 pi^2/Gamma(1/4)^4')
    T.check('A_eps(2), A_eps(3)', P2 == '9/8' and P3 == '9/4*(Gamma(9/4)/Gamma(3/4))**2', '9/8, %.12g' % A3, '%s, %s' % (P2, P3),
            'closed forms of eq:Aeps = the strings evaluated by the 2d/3d resummations')
    return T.report(work/'replay_instanton.txt')


if __name__ == '__main__':
    sys.exit(main())
