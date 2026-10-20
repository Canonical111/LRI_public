#!/usr/bin/env python3
"""Checks of SRI/code/closure_d1 (new tool, 2026-10-15; standard library only).

Two arguments by OpenAI GPT-6 astra bear on the d = 1 dual: the two-coupling counterterm closure and the equivalence
of the archive's prescription with a local subtraction. Both were supplied as notes on 2026-10-15; since 2026-10-16
their content is in the SRI note (appendix "The two-coupling closure and the prescription") and the two notes are not
shipped. The package holds, in prescription/, the second argument's supplementary checker archive (verbatim, without
its note; public/NOT_SHIPPED.txt) and this tool. It carries no quoted number. This tool
  1. checks the dated snapshot public/SNAPSHOT.sha256 (files listed in public/SCRUBBED.txt: presence only);
  2. checks the closure argument's finite claims independently of its own companion script (which is not shipped):
     - every nonzero matrix word of length 1..9 in sigma_+, sigma_-, sigma_3 has charge Q in {0, +1, -1} and
       [sigma_3, M] = 2 Q M; the number of words is 3 + 9 + ... + 3^9 = 29,523;
     - the radial-power identity 2 sum_{i<j} q_i q_j = Q^2 - n for alternating charges (n = 1..11);
     - the pair product O_g(X + r/2) O_g(X - r/2) = r^-2 [1 + i r sigma_3 dphi - r^2/2 :(dphi)^2: + O(r^3)], i.e.
       1/r^2 + (sqrt 2/r) O_h + :chi^2: with chi = (i/sqrt 2) dphi, O_h = sigma_3 chi (coefficients 1, sqrt 2, 1);
  3. checks the prescription archive: its MANIFEST.json (SCRUBBED.txt entries: presence only; NOT_SHIPPED.txt entries:
     must be absent), its own checker
     prescription/code/check_prescription.py rerun (needs sympy; every boolean must be true and equal to the shipped
     verification/checks.json), and, independently of that checker, the beta recurrence b3..b9, h4..h8 re-derived
     from J beta = R_1 and compared with the archive's formulas (sympy).
Usage: python3 public/check_closure.py [--out FILE]
"""
import argparse, cmath, hashlib, itertools, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent / 'verify'))
import sri_lib as L  # noqa: E402


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


SP, SM, S3, ID = [[0, 1], [0, 0]], [[0, 0], [1, 0]], [[1, 0], [0, -1]], [[1, 0], [0, 1]]
MAT, CHG = {'+': SP, '-': SM, '3': S3}, {'+': 1, '-': -1, '3': 0}


def snapshot(T):
    scr = set()
    f = HERE / 'SCRUBBED.txt'
    if f.exists():
        scr = {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}
    bad, n = [], 0
    for line in (HERE / 'SNAPSHOT.sha256').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        h, rel = line.split(None, 1)
        n += 1
        p = PKG / rel
        if not p.exists():
            bad.append(rel + ' (missing)')
        elif rel not in scr and hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(rel)
    T.check('verbatim snapshot', not bad, '%d files%s' % (n, '; differ: %s' % bad if bad else ''), 'all sha256 equal',
            'public/SNAPSHOT.sha256 (the prescription archive as supplied, without its note)')


def words(T):
    n = nz = bad = 0
    for k in range(1, 10):
        for w in itertools.product('+-3', repeat=k):
            n += 1
            M = ID
            for c in w:
                M = mul(M, MAT[c])
            if not any(any(r) for r in M):
                continue
            nz += 1
            Q = sum(CHG[c] for c in w)
            comm = [[mul(S3, M)[i][j] - mul(M, S3)[i][j] for j in range(2)] for i in range(2)]
            if Q not in (0, 1, -1) or comm != [[2 * Q * M[i][j] for j in range(2)] for i in range(2)]:
                bad += 1
    T.check('matrix-word charges', n == 29523 and bad == 0, '%d words, %d nonzero, %d violations' % (n, nz, bad),
            '29,523 words; Q in {0,+-1}; [s3,M] = 2QM', 'SRI note, App. D.5 "Matrix algebra and the local operators below threshold"')


def radial(T):
    ok = all(2 * sum(a * b for a, b in itertools.combinations(q, 2)) == sum(q) ** 2 - len(q)
             for m in range(1, 12) for q in [[(-1) ** i for i in range(m)]])
    T.check('radial-power identity', ok, 'holds for n = 1..11', '2 sum q_i q_j = Q^2 - n',
            'SRI note, App. D.7 "Power counting in the bulk and at the endpoints"')


def pair_ope(T):
    # sigma_+ sigma_- = (1 + s3)/2 multiplies exp(+i r dphi), sigma_- sigma_+ = (1 - s3)/2 multiplies exp(-i r dphi)
    # (midpoint expansion of phi(X + r/2) - phi(X - r/2) = r dphi + O(r^3)); Taylor coefficients in r up to r^2:
    #   identity part: (e^{ia} + e^{-ia})/2 = 1 - a^2/2,   sigma_3 part: (e^{ia} - e^{-ia})/2 = i a,   a = r dphi.
    c_id = [1, 0, -0.5]          # coefficients of a^0, a^1, a^2 in the identity part
    c_s3 = [0, 1j, 0]            # in the sigma_3 part
    ok_taylor = all(abs(((cmath.exp(1j * a) + cmath.exp(-1j * a)) / 2) - (c_id[0] + c_id[2] * a * a)) < a ** 3 / 5 + 1e-15
                    and abs(((cmath.exp(1j * a) - cmath.exp(-1j * a)) / 2) - c_s3[1] * a) < a ** 3 / 5 + 1e-15
                    for a in (1e-3, 2e-3, 5e-3))
    # with chi = (i/sqrt2) dphi:  i r s3 dphi = sqrt2 r s3 chi = sqrt2 r O_h;  -r^2/2 (dphi)^2 = r^2 chi^2
    dphi_of_chi = -1j * math.sqrt(2)          # dphi = -i sqrt2 chi
    coef_Oh = 1j * dphi_of_chi                # coefficient of r O_h
    coef_chi2 = -0.5 * dphi_of_chi ** 2       # coefficient of r^2 chi^2
    ok = ok_taylor and abs(coef_Oh - math.sqrt(2)) < 1e-15 and abs(coef_chi2 - 1) < 1e-15
    T.check('pair product O_g O_g', ok, '1/r^2 + %.6f/r O_h + %.6f :chi^2:' % (coef_Oh.real, coef_chi2.real),
            '1/r^2 + sqrt2/r O_h + :chi^2:', 'SRI note, App. D.6: the current-squared term is generated (finite)')


def prescription_archive(T):
    import json, subprocess
    A = PKG / 'prescription'
    scr = set()
    f = HERE / 'SCRUBBED.txt'
    if f.exists():
        scr = {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}
    absent = set()
    f = HERE / 'NOT_SHIPPED.txt'
    if f.exists():
        absent = {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}
    man = json.loads((A / 'MANIFEST.json').read_text())
    nabs = sum(('prescription/' + k) in absent for k in man)
    bad = [k + (' (listed as not shipped, but present)' if (A / k).exists() else '') for k in man
           if ('prescription/' + k) in absent and (A / k).exists()]
    bad += [k for k, v in man.items() if ('prescription/' + k) not in absent and (not (A / k).exists() or (
            ('prescription/' + k) not in scr and hashlib.sha256((A / k).read_bytes()).hexdigest() != v['sha256']))]
    bad += ['NOT_SHIPPED.txt names unlisted %s' % k for k in sorted(absent) if k[len('prescription/'):] not in man]
    T.check('prescription archive manifest', not bad, '%d files, %d not shipped%s' % (len(man), nabs,
            '; differ: %s' % bad if bad else ''), 'all shipped sha256 equal',
            'prescription/MANIFEST.json (the supplied archive, verbatim; public/NOT_SHIPPED.txt: left out)')
    try:
        import sympy  # noqa: F401
    except ImportError:
        T.add('prescription checker', 'SKIP', 'sympy not installed', 'sympy >= 1.12', 'prescription/requirements.txt')
        return
    out = subprocess.run([sys.executable, str(A / 'code' / 'check_prescription.py')], cwd=A, capture_output=True,
                         text=True, timeout=600)
    def bools(x, p='', acc=None):
        acc = {} if acc is None else acc
        if isinstance(x, dict):
            for k, v in x.items():
                bools(v, p + '/' + k, acc)
        elif isinstance(x, bool):
            acc[p] = x
        return acc
    try:
        txt = out.stdout
        got = bools(json.loads(txt[txt.index('{'):]))
    except (ValueError, json.JSONDecodeError):
        got = {}
    shipped = bools(json.loads((A / 'verification' / 'checks.json').read_text()))
    ok = out.returncode == 0 and got and all(got.values()) and got == shipped
    T.check('prescription checker (rerun)', bool(ok), '%d checks, %d true, exit %d' % (len(got), sum(got.values()),
            out.returncode), 'all true; equal to verification/checks.json', 'prescription/code/check_prescription.py')


def recurrence(T):
    try:
        import sympy as sp
    except ImportError:
        T.add('beta recurrence (independent)', 'SKIP', 'sympy not installed', '-', '-'); return
    g, v = sp.symbols('g v', positive=True)
    b0, s2 = sp.sqrt(v), sp.sqrt(2)
    C30, C50, C70, C31, C51, C71, C91 = sp.symbols('C30 C50 C70 C31 C51 C71 C91')
    Q20, K40, K60, K41, K61, K81 = sp.symbols('Q20 K40 K60 K41 K61 K81')
    j1, j3, j5, j7, l2, l4, l6 = sp.symbols('j1 j3 j5 j7 l2 l4 l6')
    b3, b5, b7, b9, h4, h6, h8 = sp.symbols('b3 b5 b7 b9 h4 h6 h8')
    J = sp.Matrix([[1 + 3*C30*g**2 + 5*C50*g**4 + 7*C70*g**6, s2*b0*(j1*g + j3*g**3 + j5*g**5 + j7*g**7)],
                   [s2*b0*(2*Q20*g + 4*K40*g**3 + 6*K60*g**5), 1 + l2*g**2 + l4*g**4 + l6*g**6]])
    beta = sp.Matrix([b3*g**3 + b5*g**5 + b7*g**7 + b9*g**9, s2*b0*(-g**2 + h4*g**4 + h6*g**6 + h8*g**8)])
    R1 = sp.Matrix([C31*g**3 + C51*g**5 + C71*g**7 + C91*g**9, s2*b0*(-g**2 + K41*g**4 + K61*g**6 + K81*g**8)])
    E = (J * beta - R1).applyfunc(sp.expand)
    E1 = sp.expand(E[1] / (s2 * b0))
    # the system is triangular: the coefficient of g^k is linear in the k-th unknown, whose coefficient is 1
    sol = {}
    for k, x, row in ((3, b3, E[0]), (4, h4, E1), (5, b5, E[0]), (6, h6, E1), (7, b7, E[0]), (8, h8, E1), (9, b9, E[0])):
        eq = sp.expand(row.coeff(g, k).subs(sol))
        assert sp.expand(eq.coeff(x, 1)) == 1 and sp.expand(eq.coeff(x, 2)) == 0, (k, x)
        sol[x] = sp.expand(x - eq)
    archive = {  # the compendium's recurrence (b3..b7, h4, h6; SRI note App. A) and its continuation (h8, b9; App. C)
        b3: C31 + 2*v*j1, h4: K41 - 2*Q20*sol[b3] + l2,
        b5: C51 - 3*C30*sol[b3] - 2*v*j1*sol[h4] + 2*v*j3,
        h6: K61 - 2*Q20*sol[b5] - 4*K40*sol[b3] - l2*sol[h4] + l4,
        b7: C71 - 3*C30*sol[b5] - 5*C50*sol[b3] - 2*v*j1*sol[h6] - 2*v*j3*sol[h4] + 2*v*j5,
        h8: K81 - 2*Q20*sol[b7] - 4*K40*sol[b5] - 6*K60*sol[b3] - l2*sol[h6] - l4*sol[h4] + l6,
        b9: C91 - 3*C30*sol[b7] - 5*C50*sol[b5] - 7*C70*sol[b3] - 2*v*j1*sol[h8] - 2*v*j3*sol[h6] - 2*v*j5*sol[h4] + 2*v*j7}
    ok = all(sp.expand(sol[k] - e) == 0 for k, e in archive.items())
    b3v = archive[b3].subs({v: 1, C31: 5, j1: -2})
    T.check('beta recurrence (independent)', ok and b3v == 1, 'b3..b9, h4..h8 from J beta = R_1; b3(v=1) = %s' % b3v,
            'equal to the archive formulas; b3 = 1', 'solves the finite-response system order by order (sympy)')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out')
    a = ap.parse_args()
    T = L.Table('closure_d1: finite checks of the two-coupling closure and prescription arguments')
    snapshot(T); words(T); radial(T); pair_ope(T); prescription_archive(T); recurrence(T)
    T.add('quoted numbers', 'INFO', 'none', '-', 'the package carries no quoted number; the arguments are in the SRI note')
    sys.exit(T.report(a.out))


if __name__ == '__main__':
    main()
