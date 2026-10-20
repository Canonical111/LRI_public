#!/usr/bin/env python3
"""Replay of every quoted number of HT_Pert/code/lri_hpc_Hamitonian (d = 1 frozen-cutoff perturbative HT: solver
records, vacuum window through eps^5, extrapolations, identities, engine checks), from the shipped records.

No production rerun. The quoted values (macro text of the paper's numbers.tex \\HTp..., of the HT_Pert note's
note-only macros \\NOne..., or the note's wording; the numbers are quoted in the HT_Pert note) are read from
public/quoted_lri_hpc_Hamitonian.json (= the package's quoted_<pkg>.json; ids = rows of results_map.md). Steps:
  1. Records: data/HT_1d/thermal_expanse (111 Expanse records + campaign/plan.json) and the supplied Lambda <= 50
     thermal rows (analysis_original/prior_c7/C7_completed_runs.json, analysis_original/C7_extension.json).
  2. The analysis is rerun unchanged on a re-pointed copy (public/repoint.py; the shipped scripts hard-code the
     analysis session's paths): table_rc, run_extended, diagnose_systematic, write_updated_results,
     explore_lower_edge, refit_rc, freelead2, refit_corrected, challenge-num/fit, identity A analyze/final_fit,
     desc_profile, fit_phases, ident_data/fit_ident_rc, cmp_ident; plus public/omega3_eff.py and public/engine_agree.py.
     Each rerun output is compared with the shipped one (row a1.reruns): bitwise where the analysis is exact
     arithmetic, otherwise within a stated tolerance (fits with condition numbers up to 1e16 drift across numpy
     versions: measured 1.2e-5 in C4 and 1.1e-3 in C5 between numpy 1.24 and 2.4).
  3. Every quoted number is computed from the SHIPPED outputs (the production analysis stack) by the rule stated in
     its row; the rerun outputs must agree with them within the a1.reruns tolerances.
Verdicts: PASS, FAIL, INFO (judgement, not computed), SKIP (cross-folder input absent). Exit 1 on any FAIL.
Table to stdout and to <work>/replay_lri_hpc_Hamitonian.txt (+ .json).
usage: python3 public/replay_hpcham.py [--data ../../data/HT_1d] [--eh ../lri_eh_hpc] [--work .work]"""
import argparse
import glob
import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import repoint  # noqa: E402

FP = 'c0c30783db5dd9a164fa16cb7ced5627c8dfa2cc2f1d81ab0c47ebc7518da2fb'   # lri_hpc source fingerprint
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703275805, 7: -322550.0}   # numbers.tex Table pt (d = 1)
C2X = (math.pi + 4 * math.log(2)) / 9
A_T2 = -40 / (81 * math.sqrt(math.pi))
STALE_ROOT = {'export_results.py', 'lri_hpc/__main__.py', 'lri_hpc/solver.py', 'tests/run_all.py',
              'tests/test_full_recursion.py'}
BOUND = {   # shared files that other packages' records bind by sha256 (PLAN_d1.md, lri_1d_c4/c5_exact inputs/MANIFEST)
    'analysis/eps5_window/reconcile/dC_reconciled.json': '0250b341048a2da66e313edb7225233b972b25db185f03491aebc6c7483fadd8',
    'analysis/eh_review/physics-impact/d5_all.json': 'bd5211deead53eee77865fd83e829a2fda2d85cf309047c0140e0b86fdc1c076',
    'analysis/eh_review/physics-impact/d7_all.json': '52192e13f35f5f3b6817f10f0877daa29165146b3cbfb30701137286826066ad',
    'analysis/eps5_window/reconcile/dC_reconciled.csv': '4bd9a8b18868d96fbdb6fb33b1fb108aa41624b73bd1fbbc8ca590e98ceed5c0',
    'analysis/eps5_window/reconcile/refit_rc.json': '26d2c3330cd5ec094bddfa7731530f3d70f74691c83765e1a6ef48453d5f91a4',
    'analysis/eps5_window/challenge-theory/freelead2.json': '9dac59e1cdd42d8ff1256850202d5eb7dd579e7c4d19fc96ffec2b600f9b8754',
    'analysis/extended/thermal_new.json': 'abd72c91fa251f83a6cc6cbcac81017889921b2c54d08a0b3fff48f8b1eb5647',
    'analysis/extended/phi6_d5_new.json': '3f209ffa58ea8b4efa05d99ed99dcaddac7256eebc7d92bab9543be5b7dd2605',
    'analysis/extended/phi6_d3_new.json': '48caa7cf559724d35feb4072dc0d1f13d0f63cbe901fcc2ae4a87368c5bd6aff',
    'analysis/extended/extended_summary.json': '1475eb0750acfcfbbc862d70039a3bc8520ef718589bed996dd521e601ae6733',
    'analysis/extended/C7_extension.json': 'd4f50bd02f2ccdb9b548e3fa0fd16ba947f770beaa01f6b50d01c341d132a3dc',
    'analysis/extended/prior_c7/C7_completed_runs.json': 'f8a2b308464d10ef0f48c16f4119156b1b5dca23783cf38959b55423406de1c1',
    'analysis/eps5_window/B/top5.jsonl': '4e474840e6d9ea097e28814b728e67bcda90fc2f2693b8d780f30f61ee4a2e34',
    'analysis/eps5_window/B/exact5_c16.json': 'db744c2b937aa5c45631fc6c132982fb0bfe4ea8312b599e585104da64ac72d2',
    'analysis/eps5_window/B/exact5_c32.json': '274e2ba7ed09389f80bcb4fc0fba6b3a15faef25d94b8d0c41c41605187febdf',
    'analysis/eps5_window/B/exact5_c33.json': '8d88dea3917e7c926be5d021d4f26609375936bdd7f93275115be0cff2ee549b',
    'analysis/eps5_window/B/exact5_c48.json': 'f63b6df25c76acaf4d45897eb500dede0a9045b98b6f83a7bc54beb0f392c94f',
    'analysis/eps5_window/B/exact5_c49.json': '156d349fb9a5595d9833196de2f602b9f976734cd9c707a2a9fa585de0237d57',
    'analysis/eps5_window/B/exact5_c64.json': '2ec63d861210b9b1d86867caa363e44495b8e6ed4daab9f28540ad66d7405a4d',
    'analysis/eps5_window/B/exact5_c65.json': '3362bc3e9638376af1180c4edc85594fff74ec261765cc9ac318294e6e413c19',
    'analysis/eps5_window/reconcile/exactL2/exact5_c8.json': 'f7bcd898c56ad63f4e636e9e1adb87f90ad724c3d7fef80fdb6e131fdaa2b462',
    'analysis/eps5_window/reconcile/exactL2/exact5_c16.json': '8cc434b941a3b2dd2d744d1feba58a62d28ed64d8b3e4ec1fbbd068c91a28a44',
    'analysis/eps5_window/reconcile/exactL2/exact5_c24.json': 'd75f1407d67ba1ebd178fd0757c8eee8464d0a64714bd1300a3d9d2b109bb84c',
    'analysis/eps5_window/reconcile/exactL2/exact5_c35.json': '9690e45c58edf4bb9521fd7f4983f2086b3120fd80483ac658389a5382e9b26f',
    'analysis/eps5_window/reconcile/exactL2/exact5_c43.json': 'eb3d5c114563ff6fb68a3bd14ac8c452a7f2c30430a440da4238c6c6634340f7',
    'analysis/eps5_window/reconcile/exactL2/exact5_c51.json': '1663955cc1bb4e506ad8934bb9a43cae7747da001816ce7fab074bdfcedc0a2b',
}
ROWS = []


def row(rid, verdict, what, quoted, computed):
    ROWS.append(dict(id=rid, verdict=verdict, what=what, quoted=quoted, computed=computed))


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scrubbed():
    p = os.path.join(HERE, 'SCRUBBED.txt')
    return {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith('#')} if os.path.exists(p) else set()


def tex_num(s):
    """'3.5\\times10^{9}' -> 3.5e9, '10^{-11}' -> 1e-11, '{-730.97}' -> -730.97."""
    s = s.strip().strip('{}')
    m = re.fullmatch(r'([-0-9.]+)?\\?(?:times)?\s*10\^\{(-?\d+)\}', s.replace('\\times', '*').replace('*', ''))
    if m:
        return (float(m.group(1)) if m.group(1) else 1.0) * 10 ** int(m.group(2))
    return float(s)


def tex_range(s):
    a, b = re.split(r'\\text\{--\}|\\text\{ to \}', s)
    return tex_num(a), tex_num(b)


def rnd(x, ref):
    """x rounded to the decimals of the quoted string ref (fixed point)."""
    d = len(ref.split('.')[1]) if '.' in ref else 0
    return f'{x:.{d}f}'


def sig1(x):
    """one significant figure in the macro style: 2e-3 -> 2\\times10^{-3}, 1e-11 -> 10^{-11}."""
    m, e = f'{x:.0e}'.split('e')
    e = int(e)
    return f'10^{{{e}}}' if m == '1' else f'{m}\\times10^{{{e}}}'


def leaves(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, path + (str(k),))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, path + (i,))
    else:
        yield path, x


DIAG = re.compile(r'^(cond|gain)\d*$')   # condition numbers and intercept gains of near-singular design matrices


def cmp_json(new, ref, rtol):
    """Numeric leaves: |new - ref| <= rtol max(1, |ref|) (relative above 1, absolute below); leaves whose key is a
    fit diagnostic (cond*, gain*: condition numbers and intercept gains of near-singular design matrices, themselves
    unstable across BLAS/numpy builds) within 50 % (relative 0.5), except that a diagnostic at or above 1e15
    (beyond the float64 resolution 1/eps = 4.5e15 to within a few) only has to stay >= 1e14 (measured: 1.8e17 on the
    production stack, 3.7e17 with numpy 1.26); keys, strings and booleans equal.
    Returns (ok, worst relative diff of non-diagnostic leaves, worst diagnostic diff below 1e15, n, first bad)."""
    A, B = dict(leaves(new)), dict(leaves(ref))
    if A.keys() != B.keys():
        return False, float('inf'), float('inf'), len(B), ['key sets differ']
    worst, wdiag, bad = 0.0, 0.0, []
    for k, b in B.items():
        a = A[k]
        if isinstance(b, bool) or not isinstance(b, (int, float)) or b is None:
            if a != b:
                bad.append(k)
            continue
        if not isinstance(a, (int, float)) or isinstance(a, bool):
            bad.append(k)
            continue
        if math.isnan(b) and math.isnan(a):
            continue
        last = next((x for x in reversed(k) if isinstance(x, str)), '')
        if DIAG.match(last):
            if abs(b) >= 1e15:
                if abs(a) < 1e14:
                    bad.append(k)
                continue
            d = abs(a - b) / max(abs(b), 1e-300)
            wdiag = max(wdiag, d)
            if d > 0.5:
                bad.append(k)
            continue
        d = abs(a - b) / max(1.0, abs(b))
        worst = max(worst, d)
        if d > rtol:
            bad.append(k)
    return not bad, worst, wdiag, len(B), bad[:3]


def run_py(args, cwd, env):
    r = subprocess.run([sys.executable] + args, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(args)} (in {cwd}) failed:\n{r.stderr[-1500:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(PKG, '..', '..', 'data', 'HT_1d'))
    ap.add_argument('--eh', default=os.path.join(PKG, '..', 'lri_eh_hpc'))
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    Q = {q['id']: q for q in json.load(open(os.path.join(HERE, 'quoted_lri_hpc_Hamitonian.json')))}
    qv = lambda rid: Q[rid]['quoted']
    AN = os.path.join(PKG, 'analysis')
    DX = os.path.join(a.data, 'thermal_expanse')
    scr = scrubbed()

    # ---------------------------------------------------------------- records and code binding
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(PKG, 'lri_hpc', '*.py'))):
        h.update(os.path.basename(p).encode())
        h.update(open(p, 'rb').read())
    fp = h.hexdigest()
    lri_scr = sorted(x for x in scr if x.startswith('lri_hpc/'))
    root_man = json.load(open(os.path.join(PKG, 'MANIFEST_SHA256.json')))
    root_bad = {k for k, v in root_man.items() if k not in scr and (not os.path.exists(os.path.join(PKG, k))
                                                                     or sha(os.path.join(PKG, k)) != v)}
    orig_man = json.load(open(os.path.join(PKG, 'analysis_original', 'MANIFEST_SHA256.json')))
    orig_bad = [k for k, v in orig_man.items() if 'analysis_original/' + k not in scr
                and sha(os.path.join(PKG, 'analysis_original', k)) != v]
    ref_man = json.load(open(os.path.join(PKG, 'original_source_hashes.json')))
    ref_bad = [k for k, v in ref_man.items() if 'reference/' + k not in scr and sha(os.path.join(PKG, 'reference', k)) != v]
    bound_bad = [k for k, v in BOUND.items() if k not in scr and sha(os.path.join(PKG, k)) != v]
    ok = (fp == FP or bool(lri_scr)) and root_bad == STALE_ROOT - scr and not orig_bad and not ref_bad and not bound_bad
    row('a1.code', 'PASS' if ok else 'FAIL', 'code and record binding: lri_hpc source fingerprint; checksum lists; '
        'shared files bound by other packages', f'fingerprint {FP[:16]}...',
        f'fingerprint {fp[:16]}... ({"scrubbed: " + str(lri_scr) if lri_scr else "unscrubbed"}); root MANIFEST_SHA256 '
        f'(as received, stale) mismatches exactly the 5 known review-fix files: {root_bad == STALE_ROOT - scr}; '
        f'analysis_original manifest {len(orig_man) - len(orig_bad)}/{len(orig_man)}; reference/ originals '
        f'{len(ref_man) - len(ref_bad)}/{len(ref_man)}; {len(BOUND) - len(bound_bad)}/{len(BOUND)} bound shared files '
        f'(dC_reconciled, d5_all, d7_all, refit_rc, freelead2, extended inputs, top5, exact5_c*): {bound_bad or "ok"}')

    recs = {}
    for task, deg in (('thermal', 7), ('phi6', 5), ('phi6', 3)):
        for f in sorted(glob.glob(os.path.join(DX, f'{task}_d{deg}', f'{task}_d{deg}_L*.json'))):
            r = json.load(open(f))
            if os.path.basename(f) != f"{r['task']}_d{r['degree']}_L{r['cutoff']}.json":
                raise SystemExit(f'record name mismatch {f}')
            recs[(task, deg, r['cutoff'])] = r
    plan = json.load(open(os.path.join(DX, 'campaign', 'plan.json')))
    supplied = []
    for f in ('analysis_original/prior_c7/C7_completed_runs.json', 'analysis_original/C7_extension.json'):
        supplied += json.load(open(os.path.join(PKG, f)))
    thermal = {r['cutoff']: r for r in supplied}
    thermal.update({k[2]: r for k, r in recs.items() if k[0] == 'thermal'})
    n_t = sum(k[0] == 'thermal' for k in recs)
    d5 = sorted(k[2] for k in recs if k[1] == 5)
    d3 = sorted(k[2] for k in recs if k[1] == 3)
    same_new = True
    for name, (task, deg) in (('thermal_new', ('thermal', 7)), ('phi6_d5_new', ('phi6', 5)), ('phi6_d3_new', ('phi6', 3))):
        rows_ = json.load(open(os.path.join(AN, 'extended', f'{name}.json')))
        same_new &= len(rows_) == sum(k[:2] == (task, deg) for k in recs) and all(
            r == recs[(task, deg, r['cutoff'])] for r in rows_)
    a1 = max(max(abs(r['C'][0] - 0.5), abs(r['C'][1] + 1 / 6), abs(r['r'][1]), abs(r['g'][1] - 1 / 3))
             for r in thermal.values())
    ok = (len(recs) == 111 and n_t == 34 and len(d5) == 44 and len(d3) == 33 and
          all(r['source_sha256'] == FP for r in recs.values()) and plan['source'] == FP and same_new and a1 <= 1e-15
          and (d5[0], d5[-1]) == (52, 160) and (d3[0], d3[-1]) == (136, 832) and 608 not in d3)
    row('a1.records', 'PASS' if ok else 'FAIL', 'records: 111 Expanse records carry the shipped fingerprint (as does '
        'plan.json); analysis/extended/*_new.json are copies; exact low orders (HT_Pert note) at every thermal cutoff',
        'C0 = 1/2, C1 = -1/6, r1 = 0, g1 = 1/3', f'{len(recs)} records ({n_t} thermal d7, {len(d5)} phi6 d5 '
        f'{d5[0]}..{d5[-1]}, {len(d3)} phi6 d3 {d3[0]}..{d3[-1]} without 608); fingerprints equal; exports equal: '
        f'{same_new}; max |C0-1/2|,|C1+1/6|,|r1|,|g1-1/3| over {len(thermal)} cutoffs = {a1:.1e} (<= 1e-15)')

    # cross-check with the independent C8 code's input table (other package; SKIP when absent)
    cdata = os.path.join(a.data, 'c8', 'extrapolation', 'data.json')
    if os.path.exists(cdata):
        cd = json.load(open(cdata))
        eq = sorted(int(k) for k in cd['thermal_d7']) == sorted(thermal) and all(
            cd['thermal_d7'][str(L)] == thermal[L]['C'] for L in thermal)
        rel = max(abs(c - thermal[int(L)]['C'][k]) / max(abs(thermal[int(L)]['C'][k]), 1e-300)
                  for L, cc in cd['raw'].items() if int(L) in thermal for k, c in enumerate(cc[:8]) if k >= 2)
        row('a1.xcheck', 'PASS' if eq and rel <= 1e-12 else 'FAIL', 'C8 package input table (data/HT_1d/c8/'
            'extrapolation/data.json): thermal_d7 = these records bitwise; independent lri_c8 raw C2..C7 agree', '-',
            f'thermal_d7 bitwise equal: {eq}; lri_c8 raw vs records max rel diff {rel:.1e} (<= 1e-12)')
    else:
        row('a1.xcheck', 'SKIP', 'C8 package input table data/HT_1d/c8/extrapolation/data.json', '-', 'absent')

    full = sorted(thermal) == list(range(2, 119, 2))
    rej = sorted(r['cutoff'] for r in plan['rejected'] if r['task'] == 'thermal')
    lam = max(L for L in thermal if all(l in thermal for l in range(2, L + 1, 2)))
    row('a1.lam', 'PASS' if full and str(lam) == qv('a1.lam') else 'FAIL', Q['a1.lam']['what'], qv('a1.lam'),
        f'thermal C0..C7 at every even Lambda 2..{lam} ({len(thermal)} cutoffs: {len(supplied)} supplied <= 50, '
        f'{n_t} Expanse); thermal cutoffs memory-rejected in plan.json: >= {rej[0] if rej else "-"}')

    # independent pure-Python count of the frozen-cutoff basis (zero mode 1 quarter unit, mode s costs 4s+1)
    sys.path.insert(0, HERE)
    from count_states import table, count  # noqa: E402
    CAPS = {('thermal', 7): (15, 12), ('phi6', 5): (14, 8), ('phi6', 3): (10, 4)}
    dims_ok = 0
    for (task, deg), (P, Qc) in CAPS.items():
        rs = [r for k, r in recs.items() if k[:2] == (task, deg)]
        t = table(max(r['cutoff'] for r in rs), Qc)
        dims_ok += sum(count(t, r['cutoff'], P, Qc) == r['basis_dimension'] for r in rs)
    prior = {r['cutoff'] for r in json.load(open(os.path.join(PKG, 'analysis_original/prior_c7/C7_completed_runs.json')))}
    t15, t12 = table(50, 15), table(50, 12)
    dims_ok += sum(count(t15 if r['cutoff'] in prior else t12, r['cutoff'], 15, 15 if r['cutoff'] in prior else 12)
                   == r['basis_dimension'] for r in supplied)
    n118 = thermal[118]['basis_dimension']
    m_, e_ = f'{n118:.1e}'.split('e+')
    fmt = f'{m_}\\times10^{{{int(e_)}}}'
    row('a1.states', 'PASS' if dims_ok == 136 and n118 == 3528133673 and fmt == qv('a1.states') else 'FAIL',
        Q['a1.states']['what'], qv('a1.states'), f'basis_dimension(118) = {n118:,} -> {fmt}; independent count '
        f'(public/count_states.py) reproduces {dims_ok}/136 record dimensions (supplied prior_c7 rows ran without the '
        f'nonzero-mode cap: Q = 15)')

    C118 = thermal[118]['C']
    pct = {k: 100 * C118[k] / REF[k] for k in (4, 5, 6, 7)}
    for rid, k in (('a1.frac4', 4), ('a1.frac7', 7)):
        row(rid, 'PASS' if str(round(pct[k])) == qv(rid) else 'FAIL', Q[rid]['what'], qv(rid),
            f'100 C{k}(118)/C{k} = {pct[k]:.3f} -> {round(pct[k])} (C{k} = {REF[k]}); all: ' +
            ', '.join(f'C{j} {pct[j]:.2f}%' for j in pct))

    import numpy as np
    Ls = np.array(sorted(thermal), float)
    y = np.array([thermal[int(L)]['C'][2] - C2X for L in Ls]) * np.sqrt(Ls)
    ratio = y / A_T2
    big = Ls >= 52
    mono = all(x > z > 1 for x, z in zip(ratio[big], ratio[big][1:]))
    fits = []
    for basis in ([(0.5, 0), (1, 0), (1, 1)], [(0.5, 0), (0.5, 1), (1, 0), (1, 1)], [(0.5, 0), (1, 0), (1.5, 0)],
                  [(0.5, 0), (0.5, 1), (1, 0), (1, 1), (1.5, 0)]):
        m = Ls >= 40
        X = np.column_stack([np.ones(m.sum())] + [Ls[m] ** -p * np.log(Ls[m]) ** q for p, q in basis])
        c = np.linalg.lstsq(X, y[m], rcond=None)[0]
        fits.append(c[0] / A_T2 - 1)
    ok = abs(ratio[-1] - 1) < 5e-3 and mono and max(abs(x) for x in fits) <= 1e-3
    row('a1.T2', 'PASS' if ok else 'FAIL', Q['a1.T2']['what'], qv('a1.T2'),
        f'(C2(L) - C2) sqrt(L) / (-40/(81 sqrt pi)) = {ratio[-1]:.5f} at 118 (within 0.5%), decreasing to 1 over '
        f'52..118: {mono}; fitted amplitude (4 bases in L^-1/2, L^-1 [log], L^-3/2; L >= 40) / -40/(81 sqrt pi) - 1 '
        f'in [{min(fits):+.1e}, {max(fits):+.1e}] (<= 1e-3)')

    def subrecs(r):
        return [r] if r['task'] == 'thermal' else [r['raw'], r['vacuum_subtracted']]
    wshell = max(abs(r['second_order_shell_residual']) for r in recs.values())
    wtune = max(abs(s['tuning_residual']) for r in recs.values() for s in subrecs(r))
    finite = all(len(s[k]) == r['degree'] + 1 and all(math.isfinite(x) for x in s[k])
                 for r in recs.values() for s in subrecs(r) for k in (('C', 'r', 'g') + (('D6',) if r['task'] == 'phi6' else ())))
    mq = re.search(r'shell <= ([0-9.e-]+).*tuning <= ([0-9.e-]+)', qv('a1.gates'))
    bs, bt = float(mq.group(1)), float(mq.group(2))
    ok = finite and wshell <= bs and wtune <= bt
    row('a1.gates', 'PASS' if ok else 'FAIL', Q['a1.gates']['what'], qv('a1.gates'),
        f'worst |second-order shell residual| {wshell:.3g} (-> {wshell:.0e}), worst |tuning residual| {wtune:.3g} '
        f'(-> {wtune:.0e}) over the 111 records (package gates 1e-10, 1e-6); all arrays finite: {finite}')

    # ---------------------------------------------------------------- reruns on the re-pointed copy
    tree, changed, left, notes = repoint.make(work, a.eh, a.data, quiet=True)
    env = repoint.env(tree, os.path.abspath(a.eh))
    env.setdefault('NUMBA_CACHE_DIR', os.path.join(work, 'numba_cache'))
    T = os.path.join(tree, 'analysis')
    err = {}

    def step(name, args, cwd):
        try:
            return run_py(args, cwd, env)
        except Exception as e:  # noqa: BLE001
            err[name] = str(e)[-400:]
            return None
    step('table_rc', ['table_rc.py'], os.path.join(T, 'eps5_window', 'reconcile'))
    step('run_extended', ['run_extended.py'], os.path.join(T, 'extended'))
    step('diagnose', ['analysis/diagnose_systematic.py', '--thermal-extra', 'analysis/extended/thermal_new.json',
                      '--phi6-extra', 'analysis/extended/phi6_d5_new.json', 'analysis/extended/phi6_d3_new.json',
                      '--out', 'analysis/diagnosis_extended.json'], tree)
    step('updated', ['write_updated_results.py'], os.path.join(T, 'extended'))
    step('lower_edge', ['explore_lower_edge.py'], os.path.join(T, 'extended'))
    step('refit_rc', ['refit_rc.py'], os.path.join(T, 'eps5_window', 'reconcile'))
    step('freelead2', ['freelead2.py'], os.path.join(T, 'eps5_window', 'challenge-theory'))
    step('refit_corrected', ['refit_corrected.py'], os.path.join(T, 'identity_checks', 'reconcile'))
    fit_out = step('fit', ['fit.py', 'top_a.jsonl'], os.path.join(T, 'identity_checks', 'challenge-num'))
    step('analyze_A', ['analyze.py'], os.path.join(T, 'identity_checks', 'A'))
    step('final_fit_A', ['final_fit.py'], os.path.join(T, 'identity_checks', 'A'))
    step('desc_profile', ['desc_profile.py'], os.path.join(T, 'identity_checks', 'reconcile'))
    step('fit_phases', ['fit_phases.py'], os.path.join(T, 'identity_checks', 'challenge-theory'))
    step('ident_data', ['ident_data.py'], os.path.join(T, 'eps5_window', 'reconcile'))
    step('fit_ident_rc', ['fit_ident_rc.py'], os.path.join(T, 'eps5_window', 'reconcile'))
    cmp_out = step('cmp_ident', ['cmp_ident.py'], os.path.join(T, 'eps5_window', 'reconcile'))
    om_json = os.path.join(work, 'omega3_eff.json')
    step('omega3_eff', [os.path.join(HERE, 'omega3_eff.py'), '--tree', tree, '--out', om_json], work)
    ea_json = os.path.join(work, 'engine_agree.json')
    step('engine_agree', [os.path.join(HERE, 'engine_agree.py'), '--pkg', PKG, '--out', ea_json], work)

    # rerun outputs vs shipped (tolerances: REPRODUCE "Decisions"; about 10-50 times the drift measured between the
    # production stack, Python 3.10 / numpy 1.24 on arm64, and Python 3.12 / numpy 2.3.5 on Intel Xeon 6148)
    TOL = [  # (path under analysis/, rtol on max(1, |ref|), why)
        ('eps5_window/reconcile/dC_reconciled.json', 1e-13, 'exact closed forms and sums: bitwise'),
        ('extended/extended_summary.json', 1e-5, 'gap and thermal fits (measured 5.7e-7)'),
        ('diagnosis_extended.json', 1e-4, 'D1-D4 diagnostic fits, condition numbers up to 1e15 (measured 3.1e-6)'),
        ('extended/explore_lower_edge.json', 1e-4, 'post hoc tail variants (measured 5.8e-6)'),
        ('eps5_window/reconcile/refit_rc.json', 5e-5, 'C5 fits with intercept gain up to 2e10 (measured 4.1e-6)'),
        ('eps5_window/challenge-theory/freelead2.json', 5e-5, 'freed-tail C5 fits (measured 2.2e-6)'),
        ('identity_checks/reconcile/refit_corrected.json', 1e-5, 'corrected C4/C5 refits (measured 2.4e-7)'),
        ('identity_checks/A/analysis_extrap.json', 1e-9, 'identity tail fits (measured 4.3e-11)'),
        ('identity_checks/A/analysis_table.json', 1e-12, 'finite-L identity table (measured 3.6e-15)'),
        ('identity_checks/A/final_fit.json', 1e-9, 'identity tail fits (measured 4.3e-11)'),
        ('identity_checks/reconcile/desc_profile.json', 1e-4, 'identity tail-fit ensemble, ill-conditioned members '
         '(measured 9.7e-6)'),
        ('identity_checks/challenge-theory/fit_phases.json', 1e-5, 'phase-test tail fits (measured 2.3e-7)'),
        ('eps5_window/reconcile/ident_union.json', 1e-12, 'merged finite-L identity data: bitwise'),
        ('eps5_window/reconcile/fit_ident_rc.json', 1e-6, 'eps^5 identity tail fits (measured 6.4e-8)'),
    ]
    rer, worst, wdg, bitw = [], {}, 0.0, []
    for rel, rtol, why in TOL:
        p_new, p_ref = os.path.join(T, rel), os.path.join(AN, rel)
        try:
            okc, wd, wdi, n, bad = cmp_json(json.load(open(p_new)), json.load(open(p_ref)), rtol)
        except Exception as e:  # noqa: BLE001
            okc, wd, wdi, n, bad = False, float('inf'), 0.0, 0, [str(e)[:80]]
        worst[rel] = wd
        wdg = max(wdg, wdi)
        if sha(p_new) == sha(p_ref):
            bitw.append(os.path.basename(rel))
        if not okc:
            rer.append(f'{rel}: max {wd:.1e} (tolerance {rtol:g}; diagnostics {wdi:.1e}) {bad}')
    csv_same = open(os.path.join(T, 'eps5_window/reconcile/dC_reconciled.csv')).read() == \
        open(os.path.join(AN, 'eps5_window/reconcile/dC_reconciled.csv')).read()
    ur_new = open(os.path.join(T, 'UPDATED_RESULTS.md'), encoding='utf-8').read().split('\n')
    ur_ref = open(os.path.join(AN, 'UPDATED_RESULTS.md'), encoding='utf-8').read().split('\n')
    ur_same = [x for x in ur_new if not x.startswith('Snapshot generated')] == \
        [x for x in ur_ref if not x.startswith('Snapshot generated')]
    ok = not err and not rer and csv_same
    row('a1.reruns', 'PASS' if ok else 'FAIL', 'shipped analysis rerun unchanged on the re-pointed copy; outputs vs '
        'shipped within the stated tolerances', '-',
        f'{len(TOL)} JSON outputs ({len(bitw)} bitwise: {", ".join(bitw)}); worst rel diffs ' +
        ', '.join(f'{os.path.basename(k)} {v:.0e}' for k, v in worst.items() if v > 0) +
        f'; fit diagnostics (cond*, gain*) below 1e15 within {100 * wdg:.0f} % (<= 50 %), those above stay >= 1e14; '
        f'dC_reconciled.csv identical: '
        f'{csv_same}; UPDATED_RESULTS.md identical apart from the timestamp: {ur_same}'
        + (f'; repoint notes {notes}' if notes else '') + (f'; FAILED steps {err}' if err else '') +
        (f'; out of tolerance {rer}' if rer else ''))

    # ---------------------------------------------------------------- window shift
    dC = {int(k): v for k, v in json.load(open(os.path.join(AN, 'eps5_window/reconcile/dC_reconciled.json'))).items()}
    dCn = json.load(open(os.path.join(T, 'eps5_window/reconcile/dC_reconciled.json')))
    for rid, key in (('a1.win4', 'dC4_Dconn'), ('a1.win5', 'dC5_Dconn')):
        v = dC[118][key]
        row(rid, 'PASS' if rnd(v, qv(rid)) == qv(rid) and abs(dCn['118'][key] - v) <= 1e-13 else 'FAIL',
            Q[rid]['what'], qv(rid), f'dC_reconciled.json row 118: {key} = {v:.10f} -> {rnd(v, qv(rid))}; '
            f'rerun {dCn["118"][key]:.13f}')

    shift, spread = None, []
    if fit_out:
        sec = fit_out.split('== Yc')[0]
        for ln in sec.split('\n'):
            m = re.match(r'lo=\s*(\d+) hi=\s*(\d+) n=\s*\d+ (\w) .*c0=([0-9.]+) res=([0-9.e+-]+)', ln)
            if m:
                lo_, hi_, b, c0, res = int(m.group(1)), int(m.group(2)), m.group(3), float(m.group(4)), float(m.group(5))
                if (lo_, hi_, b) == (24, 96, 'g'):
                    shift = c0
                if hi_ == 96 and lo_ == 24:
                    spread.append(c0)
        ref_fit = open(os.path.join(AN, 'identity_checks/challenge-num/fit_out.txt')).read()
        m = re.search(r'lo= 24 hi= 96 n= 37 g \{[^}]*\}\s+c0=([0-9.]+)', ref_fit)
        shift_ref = float(m.group(1)) if m else None
    eh_exact = os.path.join(a.eh, 'lri_eh', 'exact.py')
    if os.path.exists(eh_exact) and shift is not None:
        spec = importlib.util.spec_from_file_location('lri_eh_exact', eh_exact)
        ex = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(ex)
        K = float(ex.renormalized_constant())
        tot = K + shift
        ok = (abs(K - 0.0616119308426799) <= 1e-15 and abs(shift - shift_ref) <= 1e-9 and rnd(tot, qv('a1.win4inf'))
              == qv('a1.win4inf') and all(rnd(K + s, qv('a1.win4inf')) == qv('a1.win4inf') for s in spread)
              and abs(float(ex.fast(118)) - dC[118]['dC4_g2D']) <= 1e-15)
        row('a1.win4inf', 'PASS' if ok else 'FAIL', Q['a1.win4inf']['what'], qv('a1.win4inf'),
            f'K = {K!r} (lri_eh exact.renormalized_constant, 60 digits) + shift4 limit {shift:.10f} (challenge-num/'
            f'fit.py rerun on top_a.jsonl, basis g, Lambda 24..96; shipped fit_out.txt {shift_ref}) = {tot:.7f} -> '
            f'{rnd(tot, qv("a1.win4inf"))}; every basis at 24..96 ({min(spread):.7f}..{max(spread):.7f}) gives the same; '
            f'exact delta C4(g2D, 118) = dC_reconciled dC4_g2D: {abs(float(ex.fast(118)) - dC[118]["dC4_g2D"]):.0e}')
    else:
        row('a1.win4inf', 'SKIP' if shift is not None else 'FAIL', Q['a1.win4inf']['what'], qv('a1.win4inf'),
            'lri_eh_hpc (../lri_eh_hpc) absent' if shift is not None else 'fit.py rerun failed')

    # ---------------------------------------------------------------- readings of the fit outputs
    # Each reading is evaluated on the SHIPPED outputs (production stack) and again on the RERUN outputs of this
    # machine (.work/tree); the row passes only if both give the quoted value by its rule (the detail shows the
    # shipped numbers; a rerun that changes the reading is reported).
    def readings(R):
        out = {}
        rr = json.load(open(os.path.join(R, 'eps5_window/reconcile/refit_rc.json')))['rows']
        pre = [x for x in rr if x['cls'] == 'pre' and 40 <= x['lo'] <= 70]
        off = [100 * (1 - x['raw']['C4'] / REF[4]) for x in pre]
        qo = qv('a1.offset4')
        lo_r, hi_r = rnd(min(off), qo), rnd(max(off), qo)
        out['a1.offset4'] = (len(pre) == 24 and float(lo_r) <= float(qo) <= float(hi_r),
            f'raw C4 of the pre-registered bases A-F, lo 40, 50, 60, 70 (24 fits, refit_rc.json): '
            f'{min(x["raw"]["C4"] for x in pre):.5f}..{max(x["raw"]["C4"] for x in pre):.5f}, i.e. {min(off):.3f}..'
            f'{max(off):.3f} % below exact (median {statistics.median(off):.3f}); rounded to the quoted decimals '
            f'{lo_r}..{hi_r} contains {qo}')
        c4 = [x['Dconn_full']['C4'] for x in pre]
        q4 = tex_range(qv('a1.c4AF'))
        dev4 = max(abs(c / REF[4] - 1) for c in c4)
        out['a1.c4AF'] = (f'{min(c4):.3f}' == f'{q4[0]:.3f}' and max(c4) <= q4[1] and all(c < REF[4] for c in c4),
            f'Dconn_full C4, bases A-F, lo 40-70 (refit_rc.json): {min(c4):.5f}..{max(c4):.5f} (all below exact; '
            f'misses {min(c4) - REF[4]:+.4f}..{max(c4) - REF[4]:+.4f}, max relative {dev4:.1e}); lower end -> '
            f'{min(c4):.3f} = the range\'s lower end; upper end within it (the upper end 45.420 is the floor ensemble '
            f'of the S1B refit, other package)')
        m5 = [x['Dconn_full']['C5'] - REF[5] for x in pre]
        rel5 = max(abs(v) for v in m5) / abs(REF[5])
        out['a1.c5pre'] = (sig1(rel5) == qv('a1.c5pre'),
            f'pre-registered bases A-F, lo 40-70: Dconn_full C5 misses {min(m5):+.3f}..{max(m5):+.3f}, max relative '
            f'{rel5:.3e} -> {sig1(rel5)}')
        out['a1.c4AF.range'] = (f'{min(c4):.3f}\\text{{--}}{max(c4):.3f}' == qv('a1.c4AF.range'),
            f'Dconn_full C4, bases A-F, lo 40-70: {min(c4):.5f}..{max(c4):.5f} -> both ends to 3 decimals')
        out['a1.c5pre.miss'] = (f'{min(m5):.2f}\\text{{ to }}{{{max(m5):.2f}}}' == qv('a1.c5pre.miss'),
            f'pre-registered bases A-F, lo 40-70: C5 misses {min(m5):+.4f}..{max(m5):+.4f} -> both ends to 2 decimals')
        fl = json.load(open(os.path.join(R, 'eps5_window/challenge-theory/freelead2.json')))
        fi = [x for x in fl if x['fam'].startswith('(i)')]
        c5i = [x['C5'] for x in fi]
        q5 = tex_range(qv('a1.c5freed'))
        out['a1.c5freed'] = (len(fi) == 18 and f'{min(c5i):.2f}' == f'{q5[0]:.2f}' and max(c5i) <= q5[1],
            f'freed leading tail (family (i): L^-1/2, L^-1/2 log L free at k = 4, 5), bases A-F, lo 50-70 '
            f'(freelead2.json): C5 {min(c5i):.3f}..{max(c5i):.3f} (miss {min(c5i) - REF[5]:+.3f}..'
            f'{max(c5i) - REF[5]:+.3f}; C4 miss {min(x["C4"] for x in fi) - REF[4]:+.4f}..'
            f'{max(x["C4"] for x in fi) - REF[4]:+.4f}); lower end -> {min(c5i):.2f} = the range\'s lower end; max '
            f'|miss|/|C5| = {max(abs(c - REF[5]) for c in c5i) / abs(REF[5]):.2e}; upper end -730.97 is the S1B floor '
            f'ensemble (other package)')
        mi = [c - REF[5] for c in c5i]
        out['a1.c5freed.miss'] = (f'{min(mi):+.2f}\\text{{ to }}{{{max(mi):+.2f}}}' == qv('a1.c5freed.miss'),
            f'freed leading tail, family (i), lo 50-70: C5 misses {min(mi):+.4f}..{max(mi):+.4f} -> both ends to 2 '
            f'decimals')
        ff = json.load(open(os.path.join(R, 'identity_checks/A/final_fit.json')))
        dp = json.load(open(os.path.join(R, 'identity_checks/reconcile/desc_profile.json')))
        # eps^3: every sector of engine A's final fits (W from the record) except dphi3, dphi4 (not extrapolable at
        # Lambda <= 72: their fits scatter by O(1-10)) and the 2x2 block P2N2desc (reported separately).
        sect = [k.split('|')[0] for k in ff if k.endswith('|e3|Dconn')]
        single = [x for x in sect if x not in ('dphi3', 'dphi4', 'P2N2desc')]
        a3 = {x: ff[f'{x}|e3|Dconn']['central'] / ff[f'{x}|e3|Dconn']['W'] for x in single}
        r3 = {x: dp[f'{x}|e3|Dconn']['median'] for x in ('dphi1', 'd2phi')}
        v3 = [abs(v) for v in a3.values()] + [abs(v) for v in r3.values()]
        b3 = float(qv('a1.ident3'))
        blk = ff.get('P2N2desc|e3|Dconn')
        hi_ = {x: ff[f'{x}|e3|Dconn'] for x in ('dphi3', 'dphi4')}
        out['a1.ident3'] = (len(a3) == 7 and max(v3) <= b3,
            'reading (single-state sectors) of "within 0.003 W" (the source\'s "within about 0.003 W in every sector '
            'tested"); the PASS covers the single-state sectors only: extrapolated [eps^3] v_n/W with Dconn, engine A '
            'final fits (final_fit.json: ' +
            ', '.join(f'{x} {v:+.5f}' for x, v in a3.items()) + ') and reconciler medians (desc_profile.json: ' +
            ', '.join(f'{x} {v:+.5f}' for x, v in r3.items()) + f'); max = {max(v3):.4f} <= {b3}. Printed as reported, '
            f'NOT in the bound: the degenerate 2x2 block P = 2, N = 2 (Bloch RS), engine A '
            f'{blk["central"] / blk["W"]:+.4f} W, fit range [{blk["lo"]:+.3f}, {blk["hi"]:+.3f}] (the source quotes '
            f'+0.004 from its reconciler); ' + ', '.join(
                f'{x} {v["central"] / v["W"]:+.4f} W [{v["lo"] / v["W"]:+.3f}, {v["hi"] / v["W"]:+.3f}]'
                for x, v in hi_.items()) + ' (engine A; not extrapolable at Lambda <= 72)')
        rem = {x: 100 * (1 - abs(dp[f'{x}|e4|Dconn']['median']) / abs(dp[f'{x}|e4|g2D']['median']))
               for x in ('dphi1', 'd2phi', 'dphi2', 'd3phi')}
        remA = {x: 100 * (1 - abs(ff[f'{x}|e4|Dconn']['central']) / abs(ff[f'{x}|e4|g2D']['central']))
                for x in ('dphi1', 'dphi2', 'd2phi', 'd3phi', 'a4', 'a5', 'a6')}
        q4r = tex_range(qv('a1.ident4'))
        out['a1.ident4'] = (all(q4r[0] <= round(v) <= q4r[1] for v in rem.values()),
            'rule: removed fraction 1 - |v4(Dconn)|/|v4(g2D)| of the eps^4 violation, from the medians of the '
            'reconciler\'s tail-fit ensembles (desc_profile.json, fits with max residual < 1e-7): ' +
            ', '.join(f'{x} {v:.1f}%' for x, v in rem.items()) + f'; each rounded to an integer lies in '
            f'{qv("a1.ident4")}. For comparison, engine A\'s final fits (bases a, b at Lambda >= 24; final_fit.json) '
            'give ' + ', '.join(f'{x} {v:.1f}%' for x, v in remA.items()) + ' (basis-dependent tails)')
        fr = json.load(open(os.path.join(R, 'eps5_window/reconcile/fit_ident_rc.json')))
        W5 = {'v_dphi1': 1, 'v_d2phi': 1, 'v_d3phi': 2}
        v5 = {(ph, s): fr[f'{ph}|Dconn|{s}|5']['median'] / W5[s] for ph in ('0.0', '0.25', '0.75') for s in W5}
        g5 = [fr[f'0.0|g2D|{s}|5']['median'] / W5[s] for s in W5]
        r5 = [fr[f'0.0|raw|{s}|5']['median'] / W5[s] for s in W5]
        top = max(v5, key=lambda k: abs(v5[k]))
        q5r = tex_range(qv('a1.ident5'))
        out['a1.ident5'] = (q5r[0] <= abs(v5[top]) <= q5r[1],
            f'rule: largest |median [eps^5] v_n|/W with Dconn over dphi, d2phi, d3phi and phases 0, 1/4, 3/4 '
            f'(fit_ident_rc.json) = {abs(v5[top]):.3f} ({top[1]}, phase {top[0]}) lies in {qv("a1.ident5")}; the '
            f'other sectors are within {max(abs(v) for k, v in v5.items() if k[1] != "v_dphi1"):.3f}; raw '
            f'{min(r5):+.2f}..{max(r5):+.2f} W, g2D {min(g5):+.2f}..{max(g5):+.2f} W; the dphi residual about -0.1 '
            f'is unconverged (the fit ranges, e.g. phase 0 [{fr["0.0|Dconn|v_dphi1|5"]["lo"]:+.3f}, '
            f'{fr["0.0|Dconn|v_dphi1|5"]["hi"]:+.3f}], are a judgement of resolution)')
        g = fr['0.25|g2D|v_dphi1|4']
        d = fr['0.25|Dconn|v_dphi1|4']
        req = 3 * 0.0186909946
        out['a1.phase.g2D'] = (True,
            f'judgement ("agrees"): with g2D alone [eps^4] v1(dphi) at Lambda = L + 1/4 extrapolates to median '
            f'{g["median"]:+.4f}, range [{g["lo"]:+.4f}, {g["hi"]:+.4f}] (fit_ident_rc.json) against the required '
            f'3 x 0.0186910 = {req:.4f}, i.e. a C4 window shift of {g["median"] / 3:.4f} [{g["lo"] / 3:.4f}, '
            f'{g["hi"] / 3:.4f}] vs 0.0187; with Dconn {d["median"]:+.4f} [{d["lo"]:+.4f}, {d["hi"]:+.4f}]')
        out['a1.phase.g2D.value'] = (f'{g["median"]:+.4f}' == qv('a1.phase.g2D.value') and f'{req:.4f}' == '0.0561',
            f'g2D-only [eps^4] v1(dphi) at Lambda = L + 1/4: median {g["median"]:+.6f} -> 4 decimals; required '
            f'{req:.6f}')
        ae = json.load(open(os.path.join(R, 'identity_checks/A/analysis_extrap.json')))
        w2 = ae['dphi1|2|raw']
        w2c = w2[0] if isinstance(w2, list) else w2['central']
        w2r = (w2[1], w2[2]) if isinstance(w2, list) else (w2['lo'], w2['hi'])
        e3 = ae['dphi1|3|raw']
        out['a1.W54'] = (abs(w2c - 1 / 54) <= 1e-5 and w2r[0] <= 1 / 54 <= w2r[1],
            f'raw [eps^2] v1(dphi), W = 1, extrapolated (identity_checks/A/analysis_extrap.json): {w2c:.7f} '
            f'[{w2r[0]:.5f}, {w2r[1]:.5f}] vs 1/54 = {1 / 54:.7f} (|diff| {abs(w2c - 1 / 54):.1e} <= 1e-5; 1/54 '
            f'inside the range); eps^3 raw {e3[0] if isinstance(e3, list) else e3["central"]:.5f} vs predicted '
            f'(2A+3)/81 - 1/27 = {(2 * (math.pi + 4 * math.log(2)) + 3) / 81 - 1 / 27:.5f}')
        return out

    RS = readings(AN)
    try:
        RN = readings(T)
    except Exception as e:  # noqa: BLE001
        RN = {k: (False, f'rerun outputs unreadable: {e}') for k in RS}

    def emit(rid, verdict=None):
        oks, det = RS[rid]
        okn, detn = RN[rid]
        if verdict == 'INFO':
            row(rid, 'INFO', Q[rid]['what'], qv(rid), det + ('' if detn == det else f'; on the rerun outputs: '
                                                                  f'{detn.split(": ", 1)[1]}'))
            return
        tail = '; rerun outputs give the same reading' + ('' if detn == det else ' (numbers differ in late digits)') \
            if okn else f'; RERUN OUTPUTS FAIL the rule: {detn}'
        row(rid, 'PASS' if oks and okn else 'FAIL', Q[rid]['what'], qv(rid), det + tail)

    for rid in ('a1.offset4', 'a1.c4AF', 'a1.c4AF.range', 'a1.c5pre', 'a1.c5pre.miss', 'a1.c5freed', 'a1.c5freed.miss'):
        emit(rid)

    ex_ = json.load(open(os.path.join(AN, 'extended/extended_summary.json')))
    w3 = ex_['gap_reference']['extended']['3']
    w3n = json.load(open(os.path.join(T, 'extended/extended_summary.json')))['gap_reference']['extended']['3']
    row('a1.omega3', 'PASS' if str(round(w3)) == qv('a1.omega3') and abs(w3n - w3) <= 0.05 else 'FAIL',
        Q['a1.omega3']['what'], qv('a1.omega3'),
        f'extended_summary.json gap_reference.extended omega3 = {w3:.4f} (cubic phi6 gap fit to Lambda 832; original '
        f'Lambda <= 128: {ex_["gap_reference"]["original"]["3"]:.4f}) -> {round(w3)}; rerun {w3n:.4f}')

    if os.path.exists(om_json):
        om = json.load(open(om_json))
        q = tex_range(qv('a1.omega3eff'))
        ok = om['range_rounded'] == [int(q[0]), int(q[1])]
        row('a1.omega3eff', 'PASS' if ok else 'FAIL', Q['a1.omega3eff']['what'], qv('a1.omega3eff'),
            f'public/omega3_eff.py: {len(om["selected"])} fits (free-exponent A, B, D, E and E+zh; lo 40-70) with '
            f'|C5 miss| <= 0.25: omega3_eff {om["range"][0]:.1f}..{om["range"][1]:.1f} -> {om["range_rounded"][0]}--'
            f'{om["range_rounded"][1]} (nearest 10); excluded {om["excluded"]}')
    else:
        row('a1.omega3eff', 'FAIL', Q['a1.omega3eff']['what'], qv('a1.omega3eff'), f'omega3_eff.py failed {err.get("omega3_eff")}')

    # protocol verdict (rerun of the generator; section 6 of UPDATED_RESULTS.md)
    def verdicts(lines):
        out = {}
        for ln in lines:
            for key, pat in (('stable', 'Window stability'), ('heldout', 'Held-out prediction'),
                             ('tail4', 'Tail insensitivity of C4'), ('tail5', 'Tail insensitivity of C5'),
                             ('tail', 'Tail insensitivity overall')):
                if ln.startswith('- ' + pat):
                    out[key] = re.search(r'\): (yes|no)', ln).group(1)
        return out
    vr, vn = verdicts(ur_ref), verdicts(ur_new)
    claim = all(vr.get(k) == 'yes' for k in ('stable', 'heldout', 'tail'))
    verdict = 'matching offset claimed' if claim else 'unresolved'
    sec6 = lambda L_: [x for x in L_[L_.index('## 6. Automatic criteria'):] if x.strip()] if '## 6. Automatic criteria' in L_ else []
    ok = vr == vn and verdict == qv('a1.protocol') and vr == dict(stable='no', heldout='yes', tail4='yes', tail5='no', tail='no')
    row('a1.protocol', 'PASS' if ok else 'FAIL', Q['a1.protocol']['what'], qv('a1.protocol'),
        f'UPDATED_RESULTS.md section 6 (write_updated_results.py, thresholds fixed at Lambda = 84): window stability '
        f'{vr.get("stable")}, held-out {vr.get("heldout")}, C4 tail {vr.get("tail4")}, C5 tail {vr.get("tail5")} -> '
        f'overall tail {vr.get("tail")}; an offset is claimed only if all three hold -> {verdict}; rerun verdicts equal: '
        f'{vr == vn}; section 6 text identical: {sec6(ur_new) == sec6(ur_ref)}')

    # ---------------------------------------------------------------- engine agreement
    if os.path.exists(ea_json) and cmp_out:
        ea = json.load(open(ea_json))
        m = re.search(r'numbers compared (\d+)', cmp_out)
        n2 = int(m.group(1)) if m else -1
        stats = {k: float(v) for k, v in re.findall(r"^(\('[^']+', \d\)) ([0-9.e+-]+)$", cmp_out, re.M)}
        ii = max(stats.values()) if stats else float('nan')
        i_, iii = ea['i']['max_absdiff'], ea['iii']['max_absdiff']
        mx = max(i_, ii, iii)
        ok = n2 == 3808 and sig1(mx) == qv('a1.engine') and i_ <= 1.5e-11 and ii <= 1e-11 and iii <= 3e-12
        row('a1.engine', 'PASS' if ok else 'FAIL', Q['a1.engine']['what'], qv('a1.engine'),
            f'(i) engine B full basis vs pipeline, Lambda <= 60 (the analysis\' scope): {i_:.2e} (Lambda '
            f'{ea["i"]["at_L"]}; printed, not in the bound: Lambda 64 '
            f'{ea["i"]["beyond_60"].get("64", float("nan")):.1e}); (ii) cmp_ident.py engine A vs B: {n2} numbers, max '
            f'rel {ii:.2e}; (iii) ht5.py vs reconciled, Lambda 2..28: {iii:.2e} (Lambda {ea["iii"]["at_L"]}); max '
            f'{mx:.1e} -> {sig1(mx)}')
    else:
        row('a1.engine', 'FAIL', Q['a1.engine']['what'], qv('a1.engine'), f'{err.get("engine_agree")} {err.get("cmp_ident")}')

    # ---------------------------------------------------------------- identities (readings; rules stated)
    for rid in ('a1.ident3', 'a1.ident4', 'a1.ident5'):
        emit(rid)

    # cutoff-placement test
    mx_ex, ncut = 0.0, 0
    for ph in ('0.25', '0.5'):
        for r in json.load(open(os.path.join(AN, f'identity_checks/challenge-theory/offset_ph{ph}.json'))):
            ncut += 1
            mx_ex = max(mx_ex, max(abs(x) for x in r['raw']['v_dphi'][1:4]))
    row('a1.phase', 'PASS' if mx_ex <= 1e-14 and ncut == 58 else 'FAIL', Q['a1.phase']['what'], qv('a1.phase'),
        f'raw v1..v3 of E(dphi) - E(phi) - 1 at Lambda = L + 1/4 and L + 1/2 (offset_ph0.25/0.5.json, {ncut} cutoffs '
        f'8.25..64.5): max |.| = {mx_ex:.1e} (<= 1e-14)')
    emit('a1.phase.g2D', 'INFO')
    emit('a1.phase.g2D.value')
    emit('a1.W54')

    # ---------------------------------------------------------------- output
    for r in ROWS:   # macro name (paper \HTp..., note-only \NOne...) from the quoted json; None when there is none
        r['macro'] = Q.get(r['id'], {}).get('macro')
    w = max(len(r['id']) for r in ROWS)
    lines = [f"{r['id']:{w}s}  {r['verdict']:4s}  {r['what']}\n{'':{w}s}        quoted: "
             f"{(r['macro'] + ' = ') if r['macro'] else ''}{r['quoted']}\n"
             f"{'':{w}s}        computed: {r['computed']}" for r in ROWS]
    cnt = {v: sum(r['verdict'] == v for r in ROWS) for v in ('PASS', 'FAIL', 'INFO', 'SKIP')}
    summ = f"# replay lri_hpc_Hamitonian: {cnt['PASS']} PASS, {cnt['FAIL']} FAIL, {cnt['INFO']} INFO" + \
        (f", {cnt['SKIP']} SKIP" if cnt['SKIP'] else '')
    txt = '\n'.join(lines + [summ])
    print(txt)
    open(os.path.join(work, 'replay_lri_hpc_Hamitonian.txt'), 'w').write(txt + '\n')
    json.dump(dict(rows=ROWS, summary=summ), open(os.path.join(work, 'replay_lri_hpc_Hamitonian.json'), 'w'), indent=1)
    sys.exit(1 if cnt['FAIL'] else 0)


if __name__ == '__main__':
    main()
