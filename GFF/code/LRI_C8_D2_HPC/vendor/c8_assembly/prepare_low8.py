#!/usr/bin/env python3
"""Order-8 low-loop inputs: the two-loop jet B2 = b_2(z), z^0..z^6, and the Gamma normalization rows L = 2..8.

Generalizes the two delivered generators to order 8 and to any d:
  d=3  LRI_C7_D3_HPC/reference/code/prepare_low.py (65 digits; radii 0.04, 0.07 with 64, 80 nodes; nstr 60);
  d=2  LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/prepare.py:5-24 (75 digits; radii .05, .08 with 80, 96 nodes;
       nstr 65).
The only changes are the Cauchy range k = 1..7 (was 1..6), the Gamma rows L = 2..8 with label 8-L (was 2..7, 7-L)
and one more Gamma jet j = 6 per row (needed by an L=2 control at K = 6). With order=7 and jmax=5 the generator
reproduces the delivered two_loop.json and gamma_d{2,3}_7.txt byte for byte (checked on every run).

Formulas (condensed note, N: = line): b_2(z) = -6z(S_d(z) - 2/z^2), S_d = [4F_1 - 2W F_2]/z^2 (gd:twoLoopHyper,
N:2515-2532; d3six:twoLoop, N:9205), so b_{2,k-1} = -6 [z^k](4F_1 - 2W F_2); Gamma jets a_{L,j} and n_L as in
d3six:G, d3six:GammaJets, d3six:norm (N:9171-9188) with q = d/4 (d=2: c7d2 l_j, N:10566-10570; n_L = 2(-1)^(L+1)/pi^L).

Independent checks recorded in checks.json (repair round 3):
  B2      the two contours, a reference contour at 95 digits, and a direct Taylor series (mpmath.taylor of the same
          numerator at 130 digits; series_check): per entry, |stored - series| and the significant digits it leaves.
  Gamma   every printed n_L and a_{L,j} against an independent evaluation at dps+35 working digits: the jets by two
          Cauchy contours of log G_{L,d} with 128 and 160 nodes (aliasing from the log Gamma(1+Lz/2) branch point at
          z = -2/L <= 1/4 below 1e-95), n_L by its closed form. Each printed token must be the correctly rounded
          value: |printed - check| <= 1/2 unit of its last printed digit (asserted).

Usage: python3 prepare_low8.py [--d 3|2|all] [--write]
  without --write: regenerate in memory and compare byte for byte with the stored files (exit 1 on a difference).
  The delivered C7 inputs are read under $LRI_ROOT (default: two levels above this file). Without them the order-7
  regression fields of checks.json are null, so checks.json then differs from the stored copy.
Outputs: inputs_d3/{two_loop.json,gamma_d3_8.txt,checks.json}, inputs_d2_check/{two_loop.json,gamma_d2_8.txt,checks.json}.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, sys
from pathlib import Path
import mpmath as m

HERE = Path(__file__).resolve().parent
LRI = Path(os.environ.get('LRI_ROOT', HERE.parents[1]))  # .../Agent_LRI (override for a vendored copy)
SETTINGS = {
    3: dict(dps=65, digits=60, contours=[('0.04', 64), ('0.07', 80)], reference=('0.2', 192, 95), outdir='inputs_d3',
            delivered_two_loop='LRI_C7_D3_HPC/inputs/two_loop.json', delivered_gamma='LRI_C7_D3_HPC/inputs/gamma_d3_7.txt',
            two_loop_keys=True),
    2: dict(dps=75, digits=65, contours=[('.05', 80), ('.08', 96)], reference=('0.2', 192, 95), outdir='inputs_d2_check',
            delivered_two_loop='LRI_C7_D2_HPC/inputs/two_loop.json', delivered_gamma='LRI_C7_D2_HPC/inputs/gamma_d2_7.txt',
            two_loop_keys=False),
}
# C62d's statement (LRI_C8_D2_HPC_loop/RECON.md:31): b_{2,6}(d=2) to the digits it printed.
C62D_B26 = '-266.52096796135938173225219261908980094902'
ORDER, JMAX = 8, 6


def numerator(z, q):
    """4 F_1 - 2 W F_2 (LRI_C7_D3_HPC/reference/code/prepare_low.py:12-18, with q = d/4)."""
    a = q + z / 4; b = q + 3 * z / 4
    F1 = m.hyper([2 * q, z / 2, a], [1 - z / 2, a + m.mpf('.5')], m.mpf('.25'))
    F2 = m.hyper([z, 2 * a, b], [1 + z / 2, b + m.mpf('.5')], m.mpf('.25'))
    r = m.gamma(2 * q + z / 2) / m.gamma(1 + z / 2)
    w = r * r * m.gamma(1 + z) * m.gamma(1 - z / 2) * m.gamma(b) ** 2 / (m.gamma(a) ** 2 * m.gamma(2 * q) * m.gamma(2 * b))
    return 4 * F1 - 2 * w * F2


def cauchy_B2(d: int, dps: int, rad: str, n: int, kmax: int) -> list:
    """b_{2,k-1} = -6 [z^k] numerator, k = 1..kmax, by an n-node Cauchy contour of radius rad (half the nodes, conjugate
    symmetry), as str(mpf) at dps digits."""
    with m.workdps(dps):
        q = m.mpf(d) / 4; r = m.mpf(rad)
        v = [numerator(r * m.exp(2j * m.pi * (j + m.mpf('.5')) / n), q) for j in range(n // 2)]
        cs = [-12 * m.fsum(m.re(v[j] * m.exp(-2j * m.pi * (j + m.mpf('.5')) * k / n)) for j in range(n // 2)) / (n * r ** k) for k in range(1, kmax + 1)]
        return [str(x) for x in cs]


def gamma_rows(d: int, dps: int, digits: int, order: int, jmax: int) -> str:
    """Rows L = 2..order: label order-L, n_L, a_{L,0} = 0, a_{L,1..jmax} (prepare_low.py:6-9 with q = d/4)."""
    out = io.StringIO()
    with m.workdps(dps):
        q = m.mpf(d) / 4
        for L in range(2, order + 1):
            norm = 2 * (-1) ** (L + 1) * m.gamma(2 * q) ** L / m.gamma(q) ** (2 * L)
            logs = [m.mpf(0)] + [(L * (m.polygamma(k - 1, 2 * q) - m.polygamma(k - 1, 1)) / 2 ** k + (m.mpf(L) / 2) ** k * m.polygamma(k - 1, 1)
                                  - 2 * L * m.polygamma(k - 1, q) / 4 ** k) / m.factorial(k) for k in range(1, jmax + 1)]
            print(order - L, m.nstr(norm, digits), *[m.nstr(v, digits) for v in logs], file=out)
    return out.getvalue()


GAMMA_CHECK = dict(contours=[('0.041', 128), ('0.03', 160)], extra_dps=35)  # repair round 3 (was 64 nodes at r = 0.041)
SERIES_DPS = 130  # direct Taylor series of the B2 numerator (repair round 3)


def _ulp(token: str, digits: int):
    """One unit in the last printed digit of an nstr(v, digits) token."""
    return m.mpf(10) ** (int(m.floor(m.log10(abs(m.mpf(token))))) - digits + 1)


def gamma_cauchy_check(d: int, dps: int, digits: int, text: str, order: int) -> dict:
    """Independent check of every printed token of the Gamma rows (repair round 3).
    Jets a_{L,j}, j = 1..6: two Cauchy contours of log G_{L,d}(z) (the function of
    LRI_C7_D3_HPC/reference/code/check_dimension.py:13-19, with q = d/4), radius 0.041 with 128 nodes and radius 0.03
    with 160 nodes, at dps + 35 working digits. The nearest singularity is the log Gamma(1 + L z/2) branch point at
    z = -2/L (|z| >= 1/4), so the aliasing is below 4^6 (0.041 * 4)^128 / 134 ~ 1e-99 and the rounding below
    10^-(dps+35) / 0.03^6 ~ 1e-91 (d=3); the two contours must agree to 1e-80.
    n_L: the closed form 2 (-1)^(L+1) Gamma(d/2)^L / Gamma(d/4)^(2L) (d=2: 2 (-1)^(L+1) / pi^L).
    Every printed token must differ from its (complex) check value by at most half a unit in its last printed digit,
    so it is the correctly rounded value; a relative slack of 1e-20 covers the check's own error. The earlier 64-node
    check certified only 3.3e-49 (aliasing), against the delivered check_dimension.py:19 bound 1e-46."""
    worst_contours = m.mpf(0); worst_abs = m.mpf(0); worst_rel = m.mpf(0); worst_ulp = m.mpf(0); worst_norm_ulp = m.mpf(0); count = 0
    with m.workdps(dps + GAMMA_CHECK['extra_dps']):
        q = m.mpf(d) / 4
        for line in text.splitlines():
            tok = line.split(); L = order - int(tok[0])
            def logG(z): return L * (m.loggamma(2 * q + z / 2) - m.loggamma(1 + z / 2) - m.loggamma(2 * q)) + m.loggamma(1 + L * z / 2) - 2 * L * (m.loggamma(q + z / 4) - m.loggamma(q))
            jets = []
            for rad, n in GAMMA_CHECK['contours']:
                r = m.mpf(rad); vals = [logG(r * m.exp(2j * m.pi * k / n)) for k in range(n)]
                jets.append([m.fsum(vals[k] * m.exp(-2j * m.pi * k * j / n) for k in range(n)) / (n * r ** j) for j in range(1, len(tok) - 2)])
            for j, (v, w) in enumerate(zip(*jets), start=1):
                worst_contours = max(worst_contours, abs(v - w))
                diff = abs(v - m.mpf(tok[2 + j])); count += 1
                worst_abs = max(worst_abs, diff); worst_rel = max(worst_rel, diff / abs(v)); worst_ulp = max(worst_ulp, diff / _ulp(tok[2 + j], digits))
            closed = (2 * (-1) ** (L + 1) / m.pi ** L) if d == 2 else 2 * (-1) ** (L + 1) * m.gamma(m.mpf(d) / 2) ** L / m.gamma(m.mpf(d) / 4) ** (2 * L)
            worst_norm_ulp = max(worst_norm_ulp, abs(closed - m.mpf(tok[1])) / _ulp(tok[1], digits))
        slack = m.mpf('0.5') * (1 + m.mpf('1e-20'))
        assert worst_contours < m.mpf('1e-80'), worst_contours
        assert worst_ulp <= slack and worst_norm_ulp <= slack, (worst_ulp, worst_norm_ulp)
    return dict(method=f"two Cauchy contours of log G (radius/nodes {GAMMA_CHECK['contours']}) at {dps + GAMMA_CHECK['extra_dps']} digits; n_L by closed form",
                jets_checked=count, check_contours_max_abs_difference=m.nstr(worst_contours, 3),
                max_abs_difference=m.nstr(worst_abs, 3), max_rel_difference=m.nstr(worst_rel, 3),
                max_difference_in_last_printed_digit_units=m.nstr(worst_ulp, 4), norm_closed_form_max_difference_in_last_printed_digit_units=m.nstr(worst_norm_ulp, 4),
                printed_digits=digits, all_printed_tokens_correctly_rounded=True)


def series_check(d: int, stored: list, reference: list) -> dict:
    """Independent check of the stored B2 entries by the direct Taylor series of the same numerator (mpmath.taylor at
    SERIES_DPS digits; no contour): b_{2,k-1} = -6 [z^k] numerator. Reports |stored - series| and the significant
    digits that leaves per entry, and the 95-digit reference contour against the series (repair round 3)."""
    with m.workdps(SERIES_DPS):
        q = m.mpf(d) / 4
        co = m.taylor(lambda z: numerator(z, q), 0, len(stored))
        ser = [-6 * co[k] for k in range(1, len(stored) + 1)]
        diff = [abs(m.mpf(x) - y) for x, y in zip(stored, ser)]; ref = max(abs(m.mpf(x) - y) for x, y in zip(reference, ser))
        sig = [m.nstr(-m.log10(e / abs(y)), 3) if e else 'exact' for e, y in zip(diff, ser)]
        assert ref < m.mpf('1e-85'), ref
    return dict(method=f'mpmath.taylor of the numerator at {SERIES_DPS} digits', stored_vs_series_abs_difference=[m.nstr(x, 3) for x in diff],
                stored_significant_digits=sig, reference_vs_series_max=m.nstr(ref, 3))


def build(d: int) -> dict:
    """All files for dimension d as {name: bytes}, plus the order-7 regressions."""
    S = SETTINGS[d]; files = {}
    recs = [dict(radius=rad, nodes=n, dps=S['dps'], B2=cauchy_B2(d, S['dps'], rad, n, ORDER - 1)) for rad, n in S['contours']]
    rrad, rn, rdps = S['reference']; ref = cauchy_B2(d, rdps, rrad, rn, ORDER - 1)
    with m.workdps(rdps):
        two = [abs(m.mpf(x) - m.mpf(y)) for x, y in zip(recs[0]['B2'], recs[1]['B2'])]
        hp = [abs(m.mpf(x) - m.mpf(y)) for x, y in zip(recs[-1]['B2'], ref)]
    tol = m.mpf(10) ** (-(S['dps'] - 10))
    assert max(two) < tol, f'd={d}: the two contours disagree by {m.nstr(max(two), 3)}'
    assert max(hp) < tol, f'd={d}: the stored contour differs from the {rdps}-digit reference by {m.nstr(max(hp), 3)}'
    B2 = recs[-1]['B2']  # delivered convention: the last contour
    body = dict(dimension=d, order=ORDER, B2=B2)
    files['two_loop.json'] = json.dumps(body, indent=2).encode()
    gtext = gamma_rows(d, S['dps'], S['digits'], ORDER, JMAX); files[f'gamma_d{d}_8.txt'] = gtext.encode()
    # Order-7 regressions against the delivered files.
    dl2 = (LRI / S['delivered_two_loop']).read_bytes() if (LRI / S['delivered_two_loop']).exists() else None
    dlg = (LRI / S['delivered_gamma']).read_bytes() if (LRI / S['delivered_gamma']).exists() else None
    seven = dict(dimension=d, order=7, B2=B2[:6]) if S['two_loop_keys'] else dict(B2=B2[:6])
    regen2 = json.dumps(seven, indent=2).encode(); regeng = gamma_rows(d, S['dps'], S['digits'], 7, 5).encode()
    row_tokens = None
    if dlg is not None:
        old = [l.split() for l in dlg.decode().splitlines()]; new = [l.split() for l in gtext.splitlines()]
        row_tokens = all(o[1:8] == nw[1:8] and int(o[0]) + 1 == int(nw[0]) for o, nw in zip(old, new[:6]))
    order7 = dict(delivered_two_loop=S['delivered_two_loop'], delivered_two_loop_sha256=hashlib.sha256(dl2).hexdigest() if dl2 else None,
                  regenerated_order7_two_loop_byte_identical=(regen2 == dl2) if dl2 else None,
                  order8_first_six_B2_strings_identical=(json.loads(dl2)['B2'] == B2[:6]) if dl2 else None,
                  delivered_gamma=S['delivered_gamma'], delivered_gamma_sha256=hashlib.sha256(dlg).hexdigest() if dlg else None,
                  regenerated_order7_gamma_byte_identical=(regeng == dlg) if dlg else None,
                  order8_rows_L2_to_L7_tokens_n_and_a0_to_a5_identical=row_tokens)
    checks = dict(dimension=d, order=ORDER, generator='prepare_low8.py', settings=dict(dps=S['dps'], nstr_digits=S['digits'], contours=S['contours'],
                  reference_contour=dict(radius=rrad, nodes=rn, dps=rdps)),
                  two_loop=dict(records=recs, stored='last contour (delivered convention)',
                                two_contour_abs_difference=[m.nstr(x, 3) for x in two], two_contour_max=m.nstr(max(two), 3),
                                reference_B2=ref, stored_vs_reference_abs_difference=[m.nstr(x, 3) for x in hp], stored_vs_reference_max=m.nstr(max(hp), 3),
                                assert_tolerance=m.nstr(tol, 3), b26=B2[6], series_check=series_check(d, B2, ref)),
                  gamma=dict(rows='L=2..8, label 8-L, then n_L, a_{L,0}=0, a_{L,1..6}', cauchy_check=gamma_cauchy_check(d, S['dps'], S['digits'], gtext, ORDER),
                             L8_row=gtext.splitlines()[-1]),
                  order7_regression=order7)
    if d == 2:
        with m.workdps(80):
            diff = abs(m.mpf(B2[6]) - m.mpf(C62D_B26))
        checks['C62d_b26'] = dict(source='LRI_C8_D2_HPC_loop/RECON.md:31', value=C62D_B26, abs_difference=m.nstr(diff, 3),
                                  agrees_to_printed_digits=bool(diff < m.mpf('0.5e-38')))
        assert checks['C62d_b26']['agrees_to_printed_digits']
    for k, v in order7.items():
        if isinstance(v, bool): assert v, f'd={d}: order-7 regression failed: {k}'
    files['checks.json'] = (json.dumps(checks, indent=1) + '\n').encode()
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--d', default='all', choices=['2', '3', 'all']); p.add_argument('--write', action='store_true'); a = p.parse_args()
    ok = True
    for d in ((3, 2) if a.d == 'all' else (int(a.d),)):
        files = build(d); out = HERE / SETTINGS[d]['outdir']
        for name, data in files.items():
            dest = out / name
            if a.write:
                out.mkdir(exist_ok=True); dest.write_bytes(data); state = 'written'
            else:
                state = 'identical' if dest.exists() and dest.read_bytes() == data else 'DIFFERENT'; ok &= state == 'identical'
            print(f'd={d} {name}: {state} md5 {hashlib.md5(data).hexdigest()}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
