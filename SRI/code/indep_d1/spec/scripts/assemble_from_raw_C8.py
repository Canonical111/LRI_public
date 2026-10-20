#!/usr/bin/env python3
"""Reference ASSEMBLER for C8: raw-moment cutoff coefficients -> all 35 beta inputs -> C3..C7 and C8 = 8 T4.

ARCHIVE-FREE.  Same conventions, input layout and strictness as scripts/assemble_from_raw.py (phase 1), driven by the C8
files: ../out/C8/normalized_atoms_C8.json, input_definitions_C8.json, raw_requirements_C8.json, invariants_C8.json (and
../out/invariants.json for D2..D4, two_kink_exact_C8.json with --fill-two-kink-exact).  It does not read archive data.

  C8 = B_old(25 old inputs) + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta + 1/32 Kv,
  also evaluated as 8 T4 from the literal T4 polynomial (the two must agree to rounding).

Input JSON (plain layout): {"<raw atom>": {"<p>": {"<k>": "<decimal>"}}}; raw atom names as in RAW_MOMENT_REQUIREMENTS
(C8_EXTENSION) e.g. A9_base, Q8_v, EQ6_v, A3_ddd.  A missing required coefficient is an ERROR, never zero.
--fill-two-kink-exact fills Z2_*, Q2_*, EZ2_*, EQ2_* from the exact table (EZ2/EQ2 [eps^0 l^0] from their MZV form).

Usage: python assemble_from_raw_C8.py raw.json [--dps 60] [--windows both|tight|safe] [--zero-tol 1e-10]
                                               [--agree-tol 1e-8] [--fill-two-kink-exact] [--out result.json]
"""
import json, re, sys, argparse
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assemble_from_raw as A1       # noqa: E402   phase-1 assembler (load_raw, structural_zero, pmin_tight, claims)

OUT = HERE.parent / 'out'
OUTC8 = OUT / 'C8'
INT_RE = A1.INT_RE
MissingCoefficient = A1.MissingCoefficient
NEWC = {'W': (4, 1), 'S': (2, 1), 'U': (3, 4), 'J9': (1, 4), 'L3': (3, 32), 'M21': (-1, 4), 'M12': (1, 2), 'N2': (-1, 16),
        'Ndelta': (1, 8), 'Kv': (1, 32)}


def requirements():
    req = json.load(open(OUTC8 / 'raw_requirements_C8.json'))
    tight, below, genuine = [], [], []
    for atom, info in req['total_tight'].items():
        for p, ks in info['log_orders_by_power'].items():
            for k in ks:
                if not A1.structural_zero(atom, int(p)):
                    tight.append((atom, int(p), k))
    tset = set(tight)
    for atom, info in req['total_safe'].items():
        for p, ks in info['log_orders_by_power'].items():
            for k in ks:
                key = (atom, int(p), k)
                if key in tset or A1.structural_zero(atom, int(p)):
                    continue
                (below if int(p) < A1.pmin_tight(atom) else genuine).append(key)
    return tight, below, genuine


def mzv_value(txt):
    z = {f'z{i}': mp.zeta(i) for i in range(2, 8)}
    tot = mp.mpf(0)
    for term in txt.split(' + '):
        cs, bn = term.split(')*', 1)
        nu, _, de = cs[1:].partition('/')
        c = mp.mpf(int(nu)) / int(de or 1)
        val = mp.mpf(1)
        if bn != '1':
            for f in bn.split('*'):
                b, _, e = f.partition('^')
                val *= z[b] ** int(e or 1)
        tot += c * val
    return tot


def fill_two_kink(raw):
    tk = json.load(open(OUTC8 / 'two_kink_exact_C8.json'))
    tight, below, genuine = requirements()
    keys = {(a, str(p), str(k)) for a, p, k in tight + below + genuine if a in tk['atoms']}
    keys |= {(a, p, k) for a, ps in tk['atoms'].items() for p, ks in ps.items() for k in ks}
    filled, dev = [], mp.mpf(0)
    for atom, p, k in sorted(keys):
        if atom in tk['constants'] and (p, k) == ('0', '0'):
            exact = mzv_value(tk['constants'][atom]['eps0_l0_exact'])
        else:
            nu, _, de = tk['atoms'][atom].get(p, {}).get(k, '0').partition('/')
            exact = mp.mpf(int(nu)) / int(de or 1)
        have = raw.get(atom, {}).get(p, {}).get(k)
        if have is None:
            raw.setdefault(atom, {}).setdefault(p, {})[k] = mp.nstr(exact, mp.mp.dps + 5)
            filled.append(f'{atom}[eps^{p} l^{k}]')
        else:
            dev = max(dev, abs(mp.mpf(have) - exact))
    return filled, dev


def assemble(raw, windows='tight', dps=60):
    mp.mp.dps = dps
    norm = json.load(open(OUTC8 / 'normalized_atoms_C8.json'))
    defs = json.load(open(OUTC8 / 'input_definitions_C8.json'))
    inv = json.load(open(OUT / 'invariants.json'))
    inv8 = json.load(open(OUTC8 / 'invariants_C8.json'))

    def coef(atom, p, k):
        if A1.structural_zero(atom, p):
            return mp.mpf(0)
        try:
            return mp.mpf(raw[atom][str(p)][str(k)])
        except KeyError:
            raise MissingCoefficient(f'{atom} [eps^{p} l^{k}]')

    def product_of(chosen):            # order-independent strictness (phase-1 gate fix)
        acc, missing = mp.mpf(1), None
        for f, p, k in chosen:
            try:
                c = coef(f, p, k)
            except MissingCoefficient as e:
                missing = missing or e
                continue
            if c == 0:
                return mp.mpf(0)
            acc *= c
        if missing is not None:
            raise missing
        return acc

    def conv(factors, m, win):
        wl = [[(int(p), k) for p, ks in win[f].items() for k in ks] for f in factors]
        total = mp.mpf(0)
        def rec(i, psum, ksum, chosen):
            nonlocal total
            last = i == len(factors) - 1
            for p, k in wl[i]:
                if ksum + k > m or (last and (psum + p != 0 or ksum + k != m)):
                    continue
                ch = chosen + [(factors[i], p, k)]
                if last:
                    total += product_of(ch)
                else:
                    rec(i + 1, psum + p, ksum + k, ch)
        rec(0, 0, 0, [])
        return total

    nvals = {}
    for at, info in norm.items():
        win = info['raw_windows_' + windows]
        val = mp.mpf(0)
        for term in info['leibniz_expansion'].split(' + '):
            cs, prod = term.split(')*', 1)
            c = eval(INT_RE.sub(r'mpf(\1)', cs[1:]), {'mpf': mp.mpf})
            val += c * conv(prod.split('*'), info['log_order_m'], win)
        nvals[at] = val
    inputs = {}
    for nm, info in defs.items():
        names = {}
        def rep(mo):
            names.setdefault(mo.group(0), f'X{len(names)}')
            return names[mo.group(0)]
        code = INT_RE.sub(r'mpf(\1)', re.sub(r'[A-Z]+\d_\d\[v\dd\d\]', rep, info['expansion_in_normalized_atoms']))
        env = {'mpf': mp.mpf}
        env.update({var: nvals[key] for key, var in names.items()})
        inputs[nm] = eval(code, env)
    env = {'mpf': mp.mpf}
    env.update(inputs)
    ev = lambda s_: eval(INT_RE.sub(r'mpf(\1)', s_), dict(env))
    D2, T2, D3, T3, D4 = (ev(inv[k]) for k in ('D2', 'T2', 'D3', 'T3', 'D4'))
    C3 = D2 - mp.mpf(1) / 16
    C5 = 2 * D3 - T2 / 2 + C3**2 / 4
    B_old = ev(inv8['B_old_C8'])
    C8 = B_old + sum(mp.mpf(a) / b * inputs[n] for n, (a, b) in NEWC.items())
    T4 = ev(inv8['T4'])
    vals = {'D2': D2, 'T2': T2, 'C3': C3, 'C4': 2 * T2, 'D3': D3, 'C5': C5, 'T3': T3, 'C6': 4 * T3, 'D4': D4,
            'C7': 4 * D4 - T3 - T2**2 + C3 * C5 / 2, 'B_old_C8': B_old, 'T4': T4, 'C8': C8, 'C8_minus_8T4': C8 - 8 * T4,
            'B_done_C8': B_old + sum(mp.mpf(a) / b * inputs[n] for n, (a, b) in NEWC.items() if n in ('W', 'S', 'L3', 'M21', 'M12', 'N2'))}
    return nvals, inputs, vals


def run(raw, windows='both', dps=60, zero_tol='1e-10', agree_tol='1e-8', fill_exact=False):
    mp.mp.dps = dps
    checks = {'windows': windows}
    if fill_exact:
        filled, dev = fill_two_kink(raw)
        checks['two_kink_filled_from_exact'] = len(filled)
        checks['two_kink_supplied_max_dev_from_exact'] = mp.nstr(dev, 5)
    tight, below, genuine = requirements()
    need = tight + (below if windows in ('both', 'safe') else [])
    missing = [f'{a} [eps^{p} l^{k}]' for a, p, k in need if raw.get(a, {}).get(str(p), {}).get(str(k)) is None]
    if missing:
        raise MissingCoefficient(f'{len(missing)} required scalars missing (windows={windows}): ' + ', '.join(missing))
    ok = True
    if windows in ('both', 'safe'):
        zc = {f'{a} [eps^{p} l^{k}]': mp.mpf(raw[a][str(p)][str(k)]) for a, p, k in below}
        bad = {k: mp.nstr(v, 5) for k, v in zc.items() if abs(v) > mp.mpf(zero_tol)}
        checks['below_tight_bound_all_vanish'] = not bad
        if bad:
            checks['below_tight_bound_nonzero'] = bad
        ok &= not bad
    if windows == 'both':
        nt, it, vt = assemble(raw, 'tight', dps)
        try:
            ns, is_, vs = assemble(raw, 'safe', dps)
            diff = max([abs(it[k] - is_[k]) for k in it] + [abs(vt[k] - vs[k]) for k in vt])
            checks['tight_vs_safe_max_abs_diff'] = mp.nstr(diff, 5)
            checks['tight_vs_safe_agree'] = diff <= mp.mpf(agree_tol)
        except MissingCoefficient as e:
            checks['safe_assembly_error'] = f'safe assembly needs {e} (a below-tight-bound partner is non-zero)'
            checks['tight_vs_safe_agree'] = False
        ok &= checks['tight_vs_safe_agree']
        nvals, inputs, vals = nt, it, vt
    else:
        nvals, inputs, vals = assemble(raw, windows, dps)
    checks['C8_equals_8T4'] = abs(vals['C8_minus_8T4']) <= mp.mpf(10)**(-(dps - 15)) * (1 + abs(vals['C8']))
    ok &= checks['C8_equals_8T4']
    # the invariant algebra assumes the tree normalization b3(1,0) = C3_1[v0d0] - 4 = 1 (note l.550: C3_1 = 5)
    c31 = nvals['C3_1[v0d0]']
    checks['C3_1[v0d0] = 5 (tree normalization b3(1,0) = 1)'] = mp.nstr(c31 - 5, 5)
    checks['tree_normalization_ok'] = abs(c31 - 5) <= mp.mpf(agree_tol)
    ok &= checks['tree_normalization_ok']
    cl = A1.claims()
    res = {'inputs': {k: mp.nstr(v, dps - 5) for k, v in inputs.items()},
           'invariants': {k: mp.nstr(v, dps - 5) for k, v in vals.items()},
           'C3_C7_minus_claim': {k: mp.nstr(vals[k] - cl[k], 5) for k in cl},
           'normalized_atoms': {k: mp.nstr(v, dps - 5) for k, v in nvals.items()},
           'checks': checks, 'all_checks_pass': bool(ok),
           'remark': 'C8 is compared with no number here; the C8 claims are sealed (comparison step only).'}
    return res, ok


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('raw')
    ap.add_argument('--dps', type=int, default=60)
    ap.add_argument('--windows', default='both', choices=['both', 'tight', 'safe'])
    ap.add_argument('--zero-tol', default='1e-10')
    ap.add_argument('--agree-tol', default='1e-8')
    ap.add_argument('--fill-two-kink-exact', action='store_true')
    ap.add_argument('--out')
    a = ap.parse_args()
    res, ok = run(A1.load_raw(a.raw), a.windows, a.dps, a.zero_tol, a.agree_tol, a.fill_two_kink_exact)
    for k in ('C6', 'C7', 'C8'):
        print(k, res['invariants'][k][:40])
    print('checks:', {k: v for k, v in res['checks'].items() if k not in ('below_tight_bound_nonzero',)})
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    sys.exit(0 if ok else 1)
