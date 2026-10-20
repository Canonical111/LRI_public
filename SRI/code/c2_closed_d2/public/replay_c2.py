#!/usr/bin/env python3
"""Replay of c_2 in d = 2 (new tool, 2026-10-15). Run from code/c2_closed_d2/ (make -f public.mk replay); about 1 min.

1. Verbatim pipeline. code/ and inputs/ of the study are copied into <work>/run with an empty outputs/ (the study's
   own self-containment procedure) and code/reproduce.py runs its eight stages (about 1 min). Compared with the shipped
   files: outputs/raw/*.json, outputs/summary.json (the value read by other folders, pointer /C2) and
   outputs/tables/*.csv; equal bytes, or equal numbers (decimal strings to 1e-40, floats from numpy quadrature to
   1e-9 relative), with the keys elapsed_seconds and environment ignored. The receipt's result_sha256 of the rerun
   equals the shipped one for every raw file except convergence.json and independent_c2_80dps.json (they record
   timings and the software environment; compared numerically).
2. Closed form (appendix "Crossover in two dimensions", label cf:sec:cr2), mpmath at 50 digits: the exact relations
   of eq. cf:cr-expansion and the text (s_* = 7/4, Delta_chi = 15/8 - delta, delta = Delta_sigma - 1/8, c_1 = 0 from
   the vanishing first-order integral), R_Gamma, P, Q, T with the printed parameters (and an independent
   Richardson summation), their parameter excess 2, c_2 of eq. cf:cr-c2, and the constants of the study (SRI note,
   Sec. 3.5 and App. E)
   (b_0, against Behan-Rastelli-Rychkov-Zan's 1.268404; I; B_31; z_41; J(0); Omega_4(0); the two contributions;
   c_2/4) against outputs/summary.json.
3. Monte Carlo (mc/, review of 2026-10-08). The verbatim mc/summ.py, rerun on the shipped chunks of each
   configuration (A, B on symmetry; C on a personal desktop), prints the lines of the production job logs
   (public/mc_production_logs.json). The recombination (public/c2lib.py): Omega_4(0) at the cut Lambda > -15 per
   configuration (summ.py's batch means), inverse-variance mean of the three, J(0) = Omega_4/(2 pi),
   z_41 = pi J/16 + b0 B_31, c_2 = -4 z_41/b0^2. Checked: the review's printed numbers (Omega_4 66.34 +- 0.24,
   chi^2 1.29 on 2 dof, J 10.559 +- 0.039, z_41 1.6391 +- 0.0076, source-shape test 16.185 +- 0.053 against the
   predicted 16.150, here recomputed), the frozen public/mc_combined.json, and \\SRtwoCtwoMC. INFO: the plateau over
   cuts -15..-8, the pull against the closed form, and the value without the desktop configuration C.
4. Quoted numbers (../../results/quoted_numbers.json, package c2_closed_d2): \\SRtwoCtwo, \\SRtwoCtwoMC and the d = 2
   row of tab:sr.
Usage: python3 public/replay_c2.py [--work DIR] [--freeze]   (--freeze rewrites public/mc_combined.json; maintenance)
"""
import argparse, csv, json, math, re, shutil, subprocess, sys
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
sys.path.insert(0, str(HERE))
import sri_lib as L
import c2lib as C
import mpmath as mp

IGNORE = ('elapsed_seconds', 'environment')


def num_equal(a, b):
    """Leaves of two JSON documents: equal, or numerically equal (decimal strings 1e-40 abs+rel; floats 1e-9 rel)."""
    if a == b:
        return True
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= 1e-12 + 1e-9*abs(float(a))
        except (TypeError, ValueError):
            return False
    if isinstance(a, str) and isinstance(b, str):
        try:
            with mp.workdps(120):
                x, y = mp.mpf(a), mp.mpf(b)
                return abs(x - y) <= mp.mpf('1e-40')*(1 + abs(x))
        except (ValueError, TypeError):
            return False
    return False


def json_diff(x, y, path=''):
    """Paths at which two JSON documents differ beyond num_equal (keys in IGNORE skipped)."""
    if isinstance(x, dict) and isinstance(y, dict):
        out = []
        for k in sorted(set(x) | set(y)):
            if k in IGNORE:
                continue
            if k not in x or k not in y:
                out.append(path + '/' + k + ' (missing)')
            else:
                out += json_diff(x[k], y[k], path + '/' + k)
        return out
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return [path + ' (length)']
        return [d for i, (u, w) in enumerate(zip(x, y)) for d in json_diff(u, w, '%s[%d]' % (path, i))]
    return [] if num_equal(x, y) else [path]


def pipeline(T, work):
    run = work/'run'
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    for d in ('code', 'inputs'):
        shutil.copytree(PKG/d, run/d, ignore=shutil.ignore_patterns('__pycache__'))
    r = subprocess.run([sys.executable, '-B', 'code/reproduce.py'], cwd=run, capture_output=True, text=True)
    (work/'reproduce.log').write_text(r.stdout + r.stderr)
    T.check('reproduce.py (8 stages)', r.returncode == 0, 'exit %d; %s' % (r.returncode, ', '.join(
        l.split()[1] + ' ' + l.split()[2] for l in r.stdout.splitlines() if l.startswith('PASS'))[:58]),
        'exit 0', 'verbatim runner in a copy of code/ and inputs/ (empty outputs/)')
    if r.returncode:
        return
    same = 0
    raws = sorted(p.name for p in (PKG/'outputs'/'raw').glob('*.json'))
    for name in raws:
        a, b = PKG/'outputs'/'raw'/name, run/'outputs'/'raw'/name
        if not b.exists():
            T.check('raw/' + name, False, 'missing', 'regenerated', 'rerun output'); continue
        ident = a.read_bytes() == b.read_bytes()
        same += ident
        bad = [] if ident else json_diff(json.loads(a.read_text()), json.loads(b.read_text()))
        T.check('raw/' + name, not bad, 'byte-identical' if ident else ('numerically equal' if not bad else
                'differs at %s' % bad[:3]), 'shipped outputs/raw/' + name,
                'rerun vs shipped (elapsed_seconds, environment ignored)')
    bad = json_diff(json.loads((PKG/'outputs'/'summary.json').read_text()), json.loads((run/'outputs'/'summary.json').read_text()))
    ident = (PKG/'outputs'/'summary.json').read_bytes() == (run/'outputs'/'summary.json').read_bytes()
    T.check('summary.json', not bad, 'byte-identical' if ident else ('numerically equal' if not bad else 'differs at %s' % bad[:3]),
            'shipped outputs/summary.json', 'rerun vs shipped; /C2 is the value other folders read')
    for name in ('final_constants.csv', 'validation.csv', 'convergence.csv'):
        ok, how, _ = L.compare_csv(PKG/'outputs'/'tables'/name, run/'outputs'/'tables'/name, atol=1e-40, rtol=1e-40,
                                   ignore=('elapsed_seconds',))
        T.check('tables/' + name, ok, how[:58], 'shipped outputs/tables/' + name, 'rerun vs shipped (timings ignored)')
    rm = json.loads((run/'outputs'/'run_manifest.json').read_text())
    sm = json.loads((PKG/'outputs'/'run_manifest.json').read_text())
    keys = [k for k in sm['result_sha256'] if not k.endswith(('convergence.json', 'independent_c2_80dps.json'))]
    ok = rm['status'] == 'complete' and all(s['status'] == 'passed' for s in rm['steps']) and \
        all(rm['result_sha256'].get(k) == sm['result_sha256'][k] for k in keys)
    T.check('run_manifest result_sha256', ok, '%d of %d raw hashes equal the shipped receipt' % (
        sum(rm['result_sha256'].get(k) == sm['result_sha256'][k] for k in keys), len(keys)),
        'all but 2 (timings, environment)', 'rerun receipt vs shipped receipt; convergence.json records timings, independent_c2_80dps.json the environment')
    T.add('raw outputs byte-identical', 'INFO', '%d of %d' % (same, len(raws)), '-',
          'convergence.json and independent_c2_80dps.json carry timings / the environment; compared numerically')


def closed_form_rows(T):
    S = json.loads((PKG/'outputs'/'summary.json').read_text())
    K = {c['quantity']: c['value'] for c in S['constants']}
    v = C.closed_form(50)
    tol = mp.mpf('1e-45')

    def row(name, x, ref, label, rule, t=tol):
        with mp.workdps(90):
            d = abs(x - mp.mpf(ref))
        return T.check(name, d < t, '%s |diff| %s' % (mp.nstr(x, 16), mp.nstr(d, 2)), label, rule)

    d, s_star = Fr(2), 2 - 2*Fr(1, 8)
    T.check('cf: s_* = 2 - 2 Delta_sigma^SR', s_star == Fr(7, 4), str(s_star), '7/4', 'exact, Delta_sigma^SR = 1/8')
    # s = 7/4 - 2 delta: Delta_chi = (d + s)/2 and Delta_sigma = (d - s)/2, as (constant, slope in delta)
    T.check('cf: Delta_chi = 15/8 - delta', ((d + s_star)/2, Fr(-1)) == (Fr(15, 8), Fr(-1)),
            '(%s) - delta' % ((d + s_star)/2), '15/8 - delta', 'exact: (d + s)/2 at s = 7/4 - 2 delta')
    T.check('cf: delta = Delta_sigma - 1/8', ((d - s_star)/2, Fr(1)) == (Fr(1, 8), Fr(1)),
            'Delta_sigma = %s + delta' % ((d - s_star)/2), '1/8 + delta', 'exact: (d - s)/2 at s = 7/4 - 2 delta')
    i2 = C.i2_zero(50)
    T.check('cf: first-order integral = 0', abs(i2) < tol, mp.nstr(i2, 3), '0 (c_1 = 0)',
            "I_2(0) = (pi/2) int |r-1|/(1+r)^3 dr - pi/4 (radial finite-part identity, SRI note App. E), mpmath 50 digits")
    row('cf: R_Gamma', v['R'], K['Gamma_ratio'], 'summary Gamma_ratio', 'Gamma(1/4)/Gamma(3/4), 50 digits')
    for k in ('P', 'Q', 'T'):
        a, b = C.PQT_PARAMS[k]
        row('cf: ' + k, v[k], K[k], 'summary ' + k, 'mpmath hyper with the parameters printed in eq. cf:cr-PQT')
        row('cf: %s (nsum)' % k, C.nsum_4f3(a, b, 50), K[k], 'summary ' + k,
            'independent: Richardson-extrapolated partial sums of the printed series; |diff| < 1e-40', mp.mpf('1e-40'))
    exc = {k: sum(b) - sum(a) for k, (a, b) in C.PQT_PARAMS.items()}
    T.check('cf: parameter excess', all(x == 2 for x in exc.values()), ', '.join('%s %s' % kv for kv in exc.items()),
            '2, 2, 2', 'sum b_j - sum a_i (exact): terms decay as n^-3')
    row('cf: c_2 (eq. cf:cr-c2)', v['C2'], S['C2'], 'summary /C2', 'printed formula and coefficients, 50 digits')
    row('note: c_2/4 (s convention)', v['C2_s'], S['C2_in_s_convention'], 'summary', 'c_2/4, coefficient of (7/4-s)^2')
    row('note: b_0 = 9 pi^2/(8 R^2)', v['b0'], K['b0'], 'summary b0', 'SRI note, Sec. 3.2 and App. E')
    T.check('note: b_0 vs BRRZ', round(float(v['b0']), 6) == 1.268404, '%.8f' % float(v['b0']), '1.268404',
            'Behan-Rastelli-Rychkov-Zan beta_3 (6 decimals)')
    row('note: I (elliptic finite part)', v['I'], K['I_from_closed_expression'], 'summary', 'I = -4 b0^2 c_2/pi - pi b0')
    row('note: I vs Carlson quadrature', v['I'], K['I_from_independent_Carlson_periods'], 'summary (independent periods)',
        'the study\'s independent endpoint-subtracted Carlson quadrature (its own agreement with the 80-digit value: 3e-61)')
    row('note: B_31', v['B31'], K['B31'], 'summary B31', 'pi^2 (12 - pi sqrt 3 - 9 log 3)/96')
    row('note: z_41', v['z41'], K['z41'], 'summary z41', '(pi I + pi^2 b0)/16 = -c_2 b0^2/4')
    row('note: period term', v['period'], K['period_contribution_to_C2'], 'summary', '-pi I/(4 b0^2)')
    row('note: contact term', v['contact'], K['contact_contribution_to_C2'], 'summary', '-pi^2/(4 b0)')
    for name, x, text in (('J(0)', v['J0'], '10.5404'), ('Omega_4(0)', v['Omega4'], '66.2273')):
        ok, how = L.matches([float(x)], text)
        T.check('review: package ' + name, ok, '%.8f [%s]' % (float(x), how), text,
                'J(0) = I - 16 b0 B_31/pi + pi b0, Omega_4 = 2 pi J(0): the values the review compares the MC with')
    return v


def mc_rows(T, v, work, freeze):
    mc = PKG/'mc'
    logs = json.loads((HERE/'mc_production_logs.json').read_text())
    shutil.copy(mc/'summ.py', work/'summ.py')
    est, dif, per = {}, {}, {}
    for k in C.RUNS:
        files = C.mc_files(mc, k)
        r = subprocess.run([sys.executable, '-B', str(work/'summ.py')] + [str(f) for f in files], capture_output=True, text=True)
        got = [l for l in r.stdout.splitlines() if l.startswith(('nbatches', 'Lambda >', 'delta '))]
        want = logs['runs'][k]['summ_py_lines']
        exact = got == want
        nums = lambda s: [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', s)]
        close = len(got) == len(want) and all(
            len(nums(g)) == len(nums(w)) and all(abs(a - b) <= 1.01e-4 for a, b in zip(nums(g), nums(w)))
            for g, w in zip(got, want))
        T.check('summ.py run %s' % k, r.returncode == 0 and (exact or close), '%d lines, %s' % (
            len(got), 'identical' if exact else ('within the last digit' if close else 'differ')),
            'job %d log (%d lines)' % (logs['runs'][k]['job'], len(want)), 'verbatim mc/summ.py on the shipped chunks')
        heads, H, HS, BD = C.mc_load(files)
        est[k] = C.mc_est(H, C.CUT)
        dif[k] = C.mc_est(C.mc_diff(H, HS), C.CUT)
        per[k] = dict(chunks=len(files), samples=sum(nb for nb, _ in H), batches=len(H), Omega4=est[k][0],
                      Omega4_se=est[k][1], quartic_minus_gauss=dif[k][0], quartic_minus_gauss_se=dif[k][1])
        line = [l for l in want if l.startswith('Lambda > -15.0')][0]
        nums = [float(x) for x in re.findall(r'-?\d+\.\d+', line.split(':', 1)[1])]
        T.check('run %s Omega_4 at -15' % k, abs(est[k][0] - nums[0]) < 6e-5 and abs(est[k][1] - nums[1]) < 6e-5,
                '%.4f +- %.4f' % est[k], '%.4f +- %.4f (log)' % (nums[0], nums[1]), 'public/c2lib.py estimator = summ.py')
    b0, B31 = float(v['b0']), float(v['B31'])
    m, se, chi2 = C.mc_combine(list(est.values()))
    res = C.mc_to_c2(m, se, b0, B31)
    dm, dse, dchi2 = C.mc_combine(list(dif.values()))
    pred = float(C.source_shape_prediction(30))
    plateau = {}
    for cut in range(-15, -7):
        e = [C.mc_est(C.mc_load(C.mc_files(mc, k))[1], cut) for k in C.RUNS]
        mm, ss, _ = C.mc_combine(e)
        plateau[str(cut)] = C.mc_to_c2(mm, ss, b0, B31)['C2']
    mab, seab, _ = C.mc_combine([est['A'], est['B']])
    resab = C.mc_to_c2(mab, seab, b0, B31)
    pull = (res['C2'] - float(v['C2']))/res['C2_se']
    out = dict(about='Recombination of the review Monte Carlo (written by public/replay_c2.py --freeze; replay compares).',
               cut=C.CUT, cut_rule=C.mc_cut_rule(), runs=per,
               combined=dict(Omega4=m, Omega4_se=se, chi2=chi2, dof=2, **res),
               source_shape=dict(quartic_minus_gauss=dm, se=dse, chi2=dchi2, predicted=pred),
               plateau_C2=plateau, without_C=dict(Omega4=mab, Omega4_se=seab, C2=resab['C2'], C2_se=resab['C2_se']),
               b0=b0, B31=B31)
    (work/'mc_combined.json').write_text(json.dumps(out, indent=1) + '\n')
    if freeze:
        (HERE/'mc_combined.json').write_text(json.dumps(out, indent=1) + '\n')
    for name, vals, text, rule in (
            ('review: Omega_4(0)', [m, se], '66.34\\pm0.24', 'inverse-variance mean of A, B, C at Lambda > -15'),
            ('review: chi^2 (2 dof)', [chi2], '1.29', 'agreement of the three configurations'),
            ('review: J(0)', [res['J'], res['J_se']], '10.559\\pm0.039', 'Omega_4/(2 pi)'),
            ('review: z_41', [res['z41'], res['z41_se']], '1.6391\\pm0.0076', 'pi J/16 + b0 B_31'),
            ('review: source-shape test', [dm, dse], '16.185\\pm0.053', 'Omega_4(quartic) - Omega_4(Gaussian), same cut'),
            ('review: predicted shift', [pred], '16.150', '32 b0 (B_Gauss - B_quartic), radial finite-part identity')):
        ok, how = L.matches(vals, text)
        T.check(name, ok, '%s [%s]' % (', '.join('%.6g' % x for x in vals), how), text, rule)
    T.check('source-shape test vs prediction', abs(dm - pred) < 3*dse, 'pull %+.2f' % ((dm - pred)/dse), '|pull| < 3',
            'z_41 is source independent')
    ok, how, bad = L.compare_json(HERE/'mc_combined.json', work/'mc_combined.json', rtol=1e-12, atol=1e-12)
    T.check('mc_combined.json', ok, how[:58], 'public/mc_combined.json', 'frozen recombination vs this replay')
    T.check('MC vs closed form', abs(pull) < 2, 'pull %+.2f' % pull, '|pull| < 2 (review: 0.5 sigma)',
            '(c_2(MC) - c_2(closed form))/sigma')
    T.add('MC plateau over cuts', 'INFO', ', '.join('%s: %.4f' % kv for kv in plateau.items())[:58],
          'stable within ~1 sigma', 'c_2 at Lambda > -15 .. -8 (summ.py grid); the quoted value uses -15 (c2lib.mc_cut_rule)')
    T.add('MC without the desktop run', 'INFO', '%.4f +- %.4f' % (resab['C2'], resab['C2_se']), '-',
          'configurations A and B only (symmetry): the quoted value needs C as well')
    T.add('MC source-shape chi^2', 'INFO', '%.2f on 2 dof' % dchi2, '-', 'agreement of A, B, C on the quartic-minus-Gaussian shift')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--freeze', action='store_true')
    a = ap.parse_args()
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    T = L.Table('c2_closed_d2 replay')
    Q, whole = L.quoted(PKG.parent.parent/'results'/'quoted_numbers.json')
    L.verify_snapshot(PKG, T)
    pipeline(T, work)
    v = closed_form_rows(T)
    res = mc_rows(T, v, work, a.freeze)
    T.quoted(Q['\\SRtwoCtwo'], [float(v['C2'])], 'closed form (appendix eq. cf:cr-c2), mpmath 50 digits')
    T.quoted(Q['\\SRtwoCtwoMC'], [res['C2'], res['C2_se']], 'MC recombination: value and standard error')
    row = [r for r in whole['tab_sr'] if (r.get('d') == 2 or r['row'].startswith('$d=2$'))][0]
    T.check('tab:sr d=2 cells', row['cells'][:2] == ['\\ptPub{0}', '\\ptClosed{\\SRtwoCtwo}'] and not any(row['cells'][2:]),
            ' | '.join(row['cells'][:2]), '\\ptPub{0} | \\ptClosed{\\SRtwoCtwo}', 'n = 1: published c_1 = 0; n = 2: \\SRtwoCtwo (row above)')
    T.add('tab:sr d=2 c_1', 'INFO', '0 (first-order integral %s)' % mp.nstr(C.i2_zero(30), 2), '\\ptPub{0}',
          'literature value (Behan, Rastelli, Rychkov, Zan 2017), cited; consistency: row cf: first-order integral')
    return T.report(work/'replay_c2_closed_d2.txt')


if __name__ == '__main__':
    sys.exit(main())
