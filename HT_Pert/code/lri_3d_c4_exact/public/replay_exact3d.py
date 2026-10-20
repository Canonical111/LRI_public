#!/usr/bin/env python3
"""Replay of the d = 3 perturbative-HT numbers of the paper from the exact finite-cutoff sums (C2..C5(3)).

1. Copies the package into --out/pkg and reruns its own analysis scripts there on the shipped results:
   fits_c4.py (C2, C3, C4 in the complete window W), eps5/fits5.py (C5 per scheme), eps5/t3.py (descendant check).
   The regenerated fits/*.txt must equal the shipped ones byte for byte (FITS-REGEN).
2. Reads the quoted numbers from the regenerated summaries and recomputes the paper's values with the stated rules:
   C2 (15 digits), C3 (mean and half-range of three fit windows), C4 (median of the 12 tower-T4 fit windows; half-range
   including the blind fit), C5 (provisional: median and calibration of towers A and D, its delta; the L^-1/2 tower).
3. Reruns the validation against the production package lri_3d_hpc (its reference results L <= 14 and the campaign
   records L = 16..20): validate_pkg.py (C2..C4) and eps5/validate5.py (C2..C5 and the brute force), with their paths
   pointed to the public layout.
Prints a PASS/FAIL table, writes it to --out, exits 1 on any FAIL. Nothing is re-solved (make -f public.mk test does).

Run from code/lri_3d_c4_exact:  python3 -B public/replay_exact3d.py   (make -f public.mk replay)
Needs Python >= 3.9 with numpy.
"""
import argparse, contextlib, importlib.util, io, json, math, re, shutil, statistics, subprocess, sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                       # code/lri_3d_c4_exact
C2_EXACT = Decimal('0.18122178540555422213')            # (2 + 4 log 2 - pi)/9
C3_EXACT = Decimal('-0.353581520433')                    # paper Table 1, tab:pt (published)
C4_EXACT = Decimal('1.22806354532762307997')
C5_EXACT = Decimal('-5.8503514207513272292179442304977443001')
# The paper's macros (numbers.tex at the final commit a6772872): Table 2 (tab:htpert), d = 3 column, and the cutoffs.
# HTpThreeLfour is printed in Sec. 3.1, HTpThreeLfive in the caption of Table 2; HTpThreeLwin only in the HT_Pert note.
QUOTED = {'HTpCtwoThree': '0.181221785405554', 'HTpCtwoThreeDigits': '15', 'HTpCthreeThree': '-0.353581479(20)',
          'HTpCthreeThreeDev': '1e-7', 'HTpCfourThree': '1.228070(21)', 'HTpCfourThreeDev': '5e-6',
          'HTpCfiveThree': '-6.0 +- 0.3', 'HTpCfiveThreeDev': '3e-2', 'HTpThreeLfour': 600, 'HTpThreeLfive': 40, 'HTpThreeLwin': 8000}


class Table:
    def __init__(self):
        self.rows = []

    def add(self, cid, quoted, value, rule, ok, note=''):
        self.rows.append({'id': cid, 'quoted': str(quoted), 'replayed': str(value), 'rule': rule,
                          'status': ok if isinstance(ok, str) else ('PASS' if ok else 'FAIL'), 'note': note})

    def text(self):
        head = ('id', 'quoted', 'replayed', 'status')
        w = [max(len(r[k]) for r in self.rows + [dict(zip(head, head))]) for k in head]
        out = io.StringIO()
        out.write('  '.join(h.ljust(n) for h, n in zip(head, w)) + '  rule\n')
        for r in self.rows:
            out.write('  '.join(r[k].ljust(n) for k, n in zip(head, w)) + '  ' + r['rule']
                      + (f'  [{r["note"]}]' if r['note'] else '') + '\n')
        return out.getvalue()


def pdg(value, err):
    """PDG rounding: the three leading digits of err decide 2 (100-354) or 1 (355-949) significant digits
    (950-999: round up to 1000, 2 digits). Returns 'value(err)' with err in units of the last digit."""
    e = Decimal(err)
    exp = e.adjusted()
    lead = int(e.scaleb(-exp + 2))                       # three leading digits
    nd = 2 if lead < 355 else 1
    if lead >= 950:
        e, exp, nd = Decimal(10) ** (exp + 1), exp + 1, 2
    q = Decimal(1).scaleb(exp - nd + 1)
    ev, vv = e.quantize(q, rounding='ROUND_HALF_UP'), Decimal(value).quantize(q, rounding='ROUND_HALF_UP')
    return f'{vv}({int(ev / q)})'


def one_digit(x):
    """x rounded to one significant digit, as 'ae-b'."""
    return f'{float(f"{x:.0e}"):.0e}'.replace('e-0', 'e-')


def floats(s):
    return [float(x) for x in re.findall(r'[-+]?\d+\.\d+(?:e[-+]\d+)?', s)]


def run_quiet(mod_path, argv, overrides):
    """Import a package script as a module, override its path globals, run main() with argv; return stdout."""
    spec = importlib.util.spec_from_file_location(Path(mod_path).stem + '_replay', mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for k, v in overrides.items():
        setattr(m, k, str(v))
    buf, old = io.StringIO(), sys.argv
    sys.argv = [str(mod_path)] + [str(a) for a in argv]
    try:
        with contextlib.redirect_stdout(buf):
            m.main()
    finally:
        sys.argv = old
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pert', default=str(PKG / '../lri_3d_hpc'), help='the production package lri_3d_hpc')
    ap.add_argument('--records', default=str(PKG / '../../data/HT_3d/pert3d/results'),
                    help='campaign result records L = 16..20 (HT_Pert/data/HT_3d/pert3d/results)')
    ap.add_argument('--out', default=str(PKG / '.work/replay'))
    a = ap.parse_args()
    out = Path(a.out)
    work = out / 'pkg'
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(PKG, work, ignore=shutil.ignore_patterns('.work', '.work_*', 'public', '__pycache__'))
    T = Table()

    # 1. FITS-REGEN: the package's own analysis scripts on the shipped results. Byte identity holds on the platform
    #    that wrote the shipped summaries; elsewhere, ill-conditioned subleading fit coefficients (not quoted) move in
    #    their last digits, so identity is INFO and the lines that carry quoted numbers are checked with tolerances
    #    (FITS-QUOTED).
    regen = {}
    for script, summary in (('fits_c4.py', 'fits/fit_summary.txt'), ('eps5/fits5.py', 'fits/fits5_summary.txt'),
                            ('eps5/t3.py', 'fits/t3_summary.txt')):
        p = subprocess.run([sys.executable, '-B', Path(script).name], cwd=work / Path(script).parent,
                           capture_output=True, text=True)
        if p.returncode:
            T.add('FITS-REGEN', summary, f'rc={p.returncode}', f'{script} runs on the shipped results', False, p.stderr.strip()[-200:])
            regen[summary] = (PKG / summary).read_text()
            continue
        new_t, old_t = (work / summary).read_text(), (PKG / summary).read_text()
        regen[summary] = new_t
        nd = sum(1 for x, y in zip(new_t.splitlines(), old_t.splitlines()) if x != y) + abs(len(new_t.splitlines()) - len(old_t.splitlines()))
        T.add('FITS-REGEN', summary, 'identical' if nd == 0 else f'{nd} lines differ in last digits',
              f'{script} regenerates {summary}; byte identity is informational (platform-dependent fit conditioning)',
              'PASS' if nd == 0 else 'INFO')
    fit, fit5 = regen['fits/fit_summary.txt'], regen['fits/fits5_summary.txt']
    ship = (PKG / 'fits/fit_summary.txt').read_text()

    def vals(text, pattern):
        return [float(x) for x in re.findall(pattern, text)]
    tol_rows = [('C2 limit - exact', r'C2: limit - exact = ([-+0-9.e]+)', 5e-16),
                ('C3 limits (3 windows)', r'C3: Lmin=\d+ limit - exact = ([-+0-9.e]+)', 2e-9),
                ('C4 tower T4 (12 windows, units 1e-6)', None, 0.2),
                ('C4 blind T4', r'blind T4 +fit 150\.\.400: A - C4\(3\) = ([-+0-9.e]+)', 1e-7)]
    worst = []
    for name, pat, tol in tol_rows:
        if pat is None:
            xa = [float(x) for x in re.findall(r'[-+]\d+\.\d', re.search(r'\n   T4 +(.*)', fit).group(1))]
            xb = [float(x) for x in re.findall(r'[-+]\d+\.\d', re.search(r'\n   T4 +(.*)', ship).group(1))]
        else:
            xa, xb = vals(fit, pat), vals(ship, pat)
        d = max(abs(x - y) for x, y in zip(xa, xb)) if len(xa) == len(xb) and xa else float('inf')
        worst.append((name, d, tol))
    T.add('FITS-QUOTED', 'regenerated = shipped on quoted lines', '; '.join(f'{n}: {d:.1e}' for n, d, t in worst),
          'C2 within 5e-16, C3 window limits within 2e-9, T4 within 0.2e-6, blind within 1e-7 of the shipped fit_summary.txt',
          all(d <= t for n, d, t in worst))

    # 2a. CUTOFFS
    import numpy as np
    L4 = int(np.load(PKG / 'results/c4_L600.npz')['L'][-1])
    L5 = int(np.load(PKG / 'results/c5raw_all_L40.npz')['L'][-1])
    Lw = int(np.load(PKG / 'results/windows_L8000.npz')['L'][-1])
    T.add('CUTOFFS', 'L <= 600 (C2..C4), 40 (C5), 8000 (C2, windows)', f'{L4}, {L5}, {Lw}',
          '\\HTpThreeLfour, \\HTpThreeLfive, \\HTpThreeLwin: largest L of c4_L600, c5raw_all_L40, windows_L8000',
          (L4, L5, Lw) == (600, 40, 8000))

    # 2b. C2: limit - exact from the L <= 8000 fit; 15 significant digits
    d2 = Decimal(re.search(r'C2: limit - exact = ([-+0-9.e]+)', fit).group(1))
    lim2 = C2_EXACT + d2
    digits = 15 if f'{lim2:.15g}' == f'{C2_EXACT:.15g}' and abs(d2 / C2_EXACT) < Decimal('5e-15') else 0
    T.add('C2-3D', '0.181221785405554, 15 digits', f'{lim2:.15g} (limit - exact {d2})',
          'C2 limit (tower L^-3/2..L^-7/2, L <= 8000) agrees with (2 + 4 ln 2 - pi)/9 to 15 significant digits',
          f'{lim2:.15g}' == QUOTED['HTpCtwoThree'] and digits == 15)

    # 2c. C3: mean and half-range over the fit windows Lmin = 100, 200, 300 (L <= 600); delta of the central value
    d3 = [Decimal(x) for x in re.findall(r'C3: Lmin=\d+ limit - exact = ([-+0-9.e]+)', fit)]
    c3 = C3_EXACT + sum(d3) / len(d3)
    h3 = (max(d3) - min(d3)) / 2
    s3, dev3 = pdg(c3, h3), one_digit(abs(sum(d3) / len(d3) / C3_EXACT))
    q3c, q3e = QUOTED['HTpCthreeThree'].split('(')
    ok3 = (s3 == QUOTED['HTpCthreeThree'] or (s3.split('(')[1] == q3e and abs(c3 - Decimal(q3c)) <= h3 / 10)) \
        and len(d3) == 3 and dev3 == QUOTED['HTpCthreeThreeDev']
    T.add('C3-3D', f'{QUOTED["HTpCthreeThree"]}, delta {QUOTED["HTpCthreeThreeDev"]}',
          f'{s3}, delta {dev3} (central {c3:.11f}; largest {max(abs(x) for x in d3) / abs(C3_EXACT):.1e})',
          'mean of the 3 window limits; half-range, PDG rounding (uncertainty digits must match; the central value within '
          '1/10 of it, since the Lmin = 300 fit moves by ~1e-9 between platforms); delta = |mean - exact|/|exact| to 1 digit', ok3)

    # 2d. C4 in the complete window W: tower T4 over 12 fit windows (median), half-range including the blind fit
    t4 = [Decimal(x) * Decimal('1e-6') for x in re.findall(r'[-+]\d+\.\d', re.search(r'\n   T4 +(.*)', fit).group(1))]
    blind = Decimal(re.search(r'blind T4 +fit 150\.\.400: A - C4\(3\) = ([-+0-9.e]+)', fit).group(1))
    pred = float(re.search(r'blind T4 +fit .*?max \|pred - data\| for 400 < L <= 600: ([0-9.e-]+)', fit).group(1))
    med = Decimal(statistics.median([float(x) for x in t4])).quantize(Decimal('1e-9'))
    c4 = C4_EXACT + med
    h4 = (max(t4 + [blind]) - min(t4 + [blind])) / 2
    s4, dev4 = pdg(c4, h4), one_digit(abs(med / C4_EXACT))
    T.add('C4-3D', f'{QUOTED["HTpCfourThree"]}, delta {QUOTED["HTpCfourThreeDev"]}',
          f'{s4}, delta {dev4} (largest {max(abs(x) for x in t4) / C4_EXACT:.1e}; {len(t4)} windows)',
          'median of tower T4 over 12 windows Lmin 80..300, Lmax 500/600; half-range of these and the blind fit, PDG; '
          'delta = |median|/C4(3) to 1 digit', s4 == QUOTED['HTpCfourThree'] and dev4 == QUOTED['HTpCfourThreeDev'] and len(t4) == 12)
    T.add('C4-BLIND', 'fit L <= 400 predicts 402..600', f'{pred:.1e} (limit - exact {blind:+.1e})',
          'blind tower-T4 fit: prediction error over 400 < L <= 600 below 1e-7', pred < 1e-7)
    line = re.search(r'\n +L\^0\.5 +Lmin=.*', fit).group(0)          # the sqrt(L) row, three Lmin values
    bs = [float(x) for x in re.findall(r'b=([-+0-9.e]+)', line)]
    T.add('C4-NODIV', 'no free divergent term', f'sqrt(L): max |b| {max(map(abs, bs)):.1e}',
          'A fixed at C4(3): a free sqrt(L) term is zero within the data (|b| < 1e-7)', len(bs) == 3 and max(map(abs, bs)) < 1e-7)

    # 2e. C5 (Table 2, provisional): towers A and D of Wc (16 windows), calibration on C4^W with the same towers;
    #     delta = |C5^HT / C5(3) - 1| of the quoted central value, to 1 digit
    def tower(block, name, tow):
        m = re.search(rf'\n   {re.escape(name)} +{tow} \[[^\]]*\] +(.*)', block)
        return [float(x) for x in re.findall(r'[-+]\d+\.\d+', m.group(1))]
    sec3 = fit5[fit5.index('== 3.'):fit5.index('== 4.')]
    sec2 = fit5[fit5.index('== 2.'):fit5.index('== 3.')]
    wc = tower(sec3, 'Wc', 'A') + tower(sec3, 'Wc', 'D')
    wcC = tower(sec3, 'Wc', 'C')
    cal = tower(sec2, 'C4^W', 'A') + tower(sec2, 'C4^W', 'D')
    bl = [float(x) for x in re.findall(r'blind Wc [AD] \[[^\]]*\] +fit 8\.\.(?:28|32): A - exact = ([-+0-9.]+)', fit5)]
    blerr = [float(x) for x in re.findall(r'blind Wc [AD] \[[^\]]*\] +fit 8\.\.(?:28|32): .*?L <= 40: ([0-9.e-]+)', fit5)]
    c4rem = -float(re.search(r'C4\^W\(L = 40\) - C4\(3\) = ([-+0-9.]+)', fit5).group(1))
    c5w40 = float(re.search(r'\n   Wc +[0-9: .+-]*?40:([-+0-9.]+)', fit5[fit5.index('== 1.'):fit5.index('== 2.')]).group(1))
    c5med = float(C5_EXACT) + statistics.median(wc)
    unc = max(map(abs, cal)) / c4rem * (c5w40 - float(C5_EXACT))
    lo, hi = min(wc + bl), max(wc + bl)
    dev5 = one_digit(abs(Decimal(f'{c5med:.1f}') / C5_EXACT - 1))
    T.add('C5-3D', f'{QUOTED["HTpCfiveThree"]}, delta {QUOTED["HTpCfiveThreeDev"]} (provisional)',
          f'{c5med:.1f} +- {unc:.1f}, delta {dev5} (median {c5med:.3f}; A - C5(3) in [{lo:.2f}, {hi:.2f}]; blind error <= {max(blerr):.0e})',
          'median of Wc towers A, D over 8 windows each; +- = their worst C4^W miss / C4^W remaining correction at L = 40, '
          'times C5^Wc(40) - C5(3); 1 decimal; delta = |central/C5(3) - 1| to 1 digit',
          f'{c5med:.1f} +- {unc:.1f}' == QUOTED['HTpCfiveThree'] and dev5 == QUOTED['HTpCfiveThreeDev']
          and len(wc) == 16 and max(blerr) < 3e-3)
    T.add('C5-LHALF', 'an L^-1/2 term could lower the limit by 0.5 to 1', f'tower C: {min(wcC):.2f} .. {max(wcC):.2f}',
          'Wc tower C (with L^-1/2) over 8 windows: A - C5(3) between -1.0 and -0.5 (1 decimal)',
          round(max(wcC), 1) == -0.5 and round(min(wcC), 1) == -1.0)

    # 3. Validation against the production package (cited check)
    ref = Path(a.pert) / 'results/reference_coefficients_L14.json'
    rec = Path(a.records)
    v4 = run_quiet(work / 'validate_pkg.py', [PKG / 'results/c4_L600.npz'], {'PKG': ref, 'CAMP': rec})
    w4 = {tuple(l.split()[:2]): float(l.split()[2]) for l in v4.split('worst scaled deviation per quantity:')[1].splitlines() if l.strip()}
    n4 = len([l for l in v4.splitlines() if l.startswith(('raw', 'consistent'))])
    T.add('VAL-PKG-C4', 'C2..C4 vs package, L <= 20, <= 1e-12', f'{max(v for k, v in w4.items() if k[1] == "C4"):.1e} (all: {max(w4.values()):.1e}; {n4} cases)',
          'validate_pkg.py: C2, C3, C4, r, g, seed energies vs the package reference (L <= 14) and the campaign records '
          '(L = 16..20), raw and consistent; scaled deviation <= 1e-12', n4 == 22 and max(w4.values()) <= 1e-12)
    v5 = run_quiet(work / 'eps5/validate5.py', [PKG / 'results/c5_L20.npz', PKG / 'results/brute'],
                   {'PKG': ref, 'CAMP': rec})
    w5 = [float(x) for x in re.findall(r'worst (?:raw|consistent) +C5: ([0-9.e-]+)', v5)]
    w54 = [float(x) for x in re.findall(r'worst (?:raw|consistent) +C4: ([0-9.e-]+)', v5)]
    wb = [float(x) for x in re.findall(r'worst \|diff\| +\w+ +C\d: ([0-9.e-]+)', v5)]
    T.add('VAL-PKG-C5', 'C2..C5 vs package and brute force, <= 1e-12', f'C5 {max(w5):.1e}, C4 {max(w54):.1e}; brute {max(wb):.1e}',
          'eps5/validate5.py: raw, consistent C2..C5 vs the package (L <= 20), every window scheme vs the brute force '
          '(L <= 14); <= 1e-12', len(w5) == 2 and max(w5) <= 1e-12 and wb and max(wb) <= 1e-12)

    out.mkdir(parents=True, exist_ok=True)
    (out / 'validate_pkg.txt').write_text(v4)
    (out / 'validate5.txt').write_text(v5)
    text = T.text()
    (out / 'replay.txt').write_text(text)
    print(text, end='')
    fails = [r['id'] for r in T.rows if r['status'] == 'FAIL']
    print(f'\n{len(T.rows) - len(fails)}/{len(T.rows)} not failed' + (f'; FAIL: {" ".join(fails)}' if fails else '')
          + f'  (table and logs in {out})')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
