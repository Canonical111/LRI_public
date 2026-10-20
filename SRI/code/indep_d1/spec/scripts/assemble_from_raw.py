#!/usr/bin/env python3
"""Reference ASSEMBLER: raw-moment cutoff coefficients -> 25 beta inputs -> D3, C5, C6, D4, C7.

ARCHIVE-FREE.  Pure implementation of the definitions in spec_definitions.json (note
eq:normalization, eq:subtraction (+h8 with the lambda6 extrapolation), derivative dictionary,
eq:D3assembly, eq:C6assembly, D4 formula, eq:conversion).  It reads only the archive-free
files ../out/normalized_atoms.json, input_definitions.json, invariants.json,
raw_requirements.json (and two_kink_exact.json with --fill-two-kink-exact).  It does not use
any archive code or data.  Intended for the integration pipelines with THEIR OWN coefficients.

Input JSON format (one file, plain layout only):
  { "<raw atom>": { "<p>": { "<k>": "<decimal string>" , ... }, ... }, ... }
  raw atom names: A3_base, A3_v, ..., EA3_vd, Q8_base (spec_definitions.json -> RAW_MOMENT_REQUIREMENTS)
  value = [eps^p log(eps)^k] of the raw moment derivative at (v,delta)=(1,0).
  A missing required coefficient is an ERROR, never zero.  Structural zeros (Z2 outside
  p in {-1,0}, Q2 outside {0,1}) need not be supplied.

Window modes (--windows):
  both (default, strict)  every TIGHT scalar and every BELOW-TIGHT-BOUND safe extra must be
                          supplied; the below-bound extras must vanish (|c| <= --zero-tol);
                          the inputs/invariants are assembled with tight AND safe windows and
                          must agree (<= --agree-tol).  Exit code 1 if a check fails.
  tight                   tight windows only (every tight scalar required).
  safe                    safe windows (tight scalars + below-bound extras required; the genuine
                          positive-power extras are looked up only if their partner is non-zero).

Usage:
  python assemble_from_raw.py raw.json [--dps 60] [--windows both|tight|safe]
                              [--zero-tol 1e-10] [--agree-tol 1e-8] [--fill-two-kink-exact] [--out result.json]
"""
import json, re, sys, argparse
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent.parent / 'out'
INT_RE = re.compile(r'(?<![\w.])(\d+)(?![\w.])')


class MissingCoefficient(Exception):
    pass


def load_raw(path):
    d = json.load(open(path))
    if 'raw' in d and isinstance(d['raw'], dict):
        raise ValueError('this looks like the archive layout (archive_raw_coefficients.json). The production assembler '
                         'accepts only the plain layout {atom: {p: {k: value}}}; archive data are converted by '
                         'comparison/scripts/archive_layout.py in the comparison step only.')
    return d


def structural_zero(atom, p):
    base = atom.split('_')[0]
    return (base == 'Z2' and p not in (-1, 0)) or (base == 'Q2' and p not in (0, 1))


def pmin_tight(atom):
    """tight leading eps power (spec_definitions.json RAW_MOMENT_REQUIREMENTS.tight_bounds)."""
    base = atom.split('_')[0]
    kind = base.rstrip('0123456789'); n = int(base[len(kind):]); m = n // 2
    if kind in ('A', 'Z', 'EA'):
        return -m
    if kind in ('Q', 'EZ'):
        return -(m - 1)
    if kind == 'EQ':
        return 0 if m == 1 else -(m - 1)
    raise ValueError(atom)


def requirements():
    req = json.load(open(HERE / 'raw_requirements.json'))
    tight, below, genuine = [], [], []
    for atom, info in req['total_tight'].items():
        for p, ks in info['log_orders_by_power'].items():
            for k in ks:
                if not structural_zero(atom, int(p)):
                    tight.append((atom, int(p), k))
    tset = set(tight)
    for atom, info in req['total_safe'].items():
        for p, ks in info['log_orders_by_power'].items():
            for k in ks:
                key = (atom, int(p), k)
                if key in tset or structural_zero(atom, int(p)):
                    continue
                (below if int(p) < pmin_tight(atom) else genuine).append(key)
    return tight, below, genuine


def fill_two_kink(raw):
    """fill absent Z2_*/Q2_* coefficients from the exact table (unlisted coefficients are exactly 0);
    report the largest deviation of supplied ones from the exact values."""
    two = json.load(open(HERE / 'two_kink_exact.json'))['atoms']
    tight, below, genuine = requirements()
    keys = {(a, str(p), str(k)) for a, p, k in tight + below + genuine if a in two}
    keys |= {(a, p, k) for a, ps in two.items() for p, ks in ps.items() for k in ks}
    filled, dev = [], mp.mpf(0)
    for atom, p, k in sorted(keys):
        val = two[atom].get(p, {}).get(k, '0')
        nu, _, de = val.partition('/')
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
    norm = json.load(open(HERE / 'normalized_atoms.json'))
    defs = json.load(open(HERE / 'input_definitions.json'))
    inv = json.load(open(HERE / 'invariants.json'))

    def coef(atom, p, k):
        if structural_zero(atom, p):
            return mp.mpf(0)
        try:
            return mp.mpf(raw[atom][str(p)][str(k)])
        except KeyError:
            raise MissingCoefficient(f'{atom} [eps^{p} l^{k}]')

    def product_of(chosen):
        """product of the chosen coefficients.  ORDER-INDEPENDENT strictness (gate-review fix
        2026-10-02): the product is zero if any factor is exactly zero; a missing coefficient is an
        error only if every other factor of the product is non-zero, i.e. only if its value could
        matter.  Previously the lookup was eager for non-last factors, so a genuine safe extra
        (EZ2_base [eps^2 l^0]) ordered before its vanishing below-bound partner was demanded and
        --windows both failed on exactly the documented required set."""
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
    def ev(s_):
        return eval(INT_RE.sub(r'mpf(\1)', s_), dict(env))
    D2, T2, D3, T3, D4 = (ev(inv[k]) for k in ('D2', 'T2', 'D3', 'T3', 'D4'))
    C3 = D2 - mp.mpf(1) / 16
    C5 = 2 * D3 - T2 / 2 + C3**2 / 4
    C6 = 4 * T3
    C7 = 4 * D4 - T3 - T2**2 + C3 * C5 / 2
    inv_vals = {'D2': D2, 'T2': T2, 'C3': C3, 'C4': 2 * T2, 'D3': D3, 'C5': C5, 'T3': T3, 'C6': C6, 'D4': D4, 'C7': C7,
                'B_old_C6': ev(inv['B_old_C6']), 'B_old_D4': ev(inv['B_old_D4'])}
    return nvals, inputs, inv_vals


def claims():
    z2, z3, z4, z5, z6 = (mp.zeta(i) for i in range(2, 7))
    C3 = mp.mpf(39) / 16 + 2 * z2
    T2 = 2 - 2 * z2 - 4 * z3
    C5 = mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z2 + 24 * z3 + mp.mpf(49) / 2 * z4
    C6 = 26 - 38 * z2 + 104 * z3 - 80 * z4 - 272 * z5 + 112 * z2 * z3
    D4 = 13 - mp.mpf(179) / 8 * z2 + mp.mpf(47) / 2 * z3 - mp.mpf(493) / 8 * z4 + 289 * z5 - 130 * z2 * z3 + mp.mpf(499) / 4 * z6 - 76 * z3**2
    C7 = 4 * D4 - C6 / 4 - T2**2 + C3 * C5 / 2
    return {'C3': C3, 'C4': 2 * T2, 'C5': C5, 'C6': C6, 'D4': D4, 'C7': C7,
            'D3': mp.mpf(21) / 4 - 13 * z2 + 11 * z3 + 11 * z4}


def run(raw, windows='both', dps=60, zero_tol='1e-10', agree_tol='1e-8', fill_exact=False):
    """Full strict run; returns (result dict, ok flag).  Raises MissingCoefficient listing every
    missing required scalar."""
    mp.mp.dps = dps
    checks = {'windows': windows}
    if fill_exact:
        filled, dev = fill_two_kink(raw)
        checks['two_kink_filled_from_exact'] = filled
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
        checks['below_tight_bound_scalars'] = {k: mp.nstr(v, 5) for k, v in zc.items()}
        checks['below_tight_bound_all_vanish'] = not bad
        checks['genuine_safe_extras_looked_up_on_demand'] = [f'{a} [eps^{p} l^{k}]' for a, p, k in genuine]
        ok &= not bad
    if windows == 'both':
        nt, it, vt = assemble(raw, 'tight', dps)
        try:
            ns, is_, vs = assemble(raw, 'safe', dps)
            diff = max([abs(it[k] - is_[k]) for k in it] + [abs(vt[k] - vs[k]) for k in vt])
            checks['tight_vs_safe_max_abs_diff'] = mp.nstr(diff, 5)
            checks['tight_vs_safe_agree'] = diff <= mp.mpf(agree_tol)
        except MissingCoefficient as e:   # only reachable when a below-bound partner is non-zero
            checks['safe_assembly_error'] = (f'safe assembly needs {e} because a below-tight-bound partner is non-zero; '
                                             'supply it or fix the convention')
            checks['tight_vs_safe_agree'] = False
        ok &= checks['tight_vs_safe_agree']
        nvals, inputs, invv = nt, it, vt
    else:
        nvals, inputs, invv = assemble(raw, windows, dps)
    cl = claims()
    res = {'inputs': {k: mp.nstr(v, dps - 5) for k, v in inputs.items()},
           'invariants': {k: mp.nstr(v, dps - 5) for k, v in invv.items()},
           'minus_claim': {k: mp.nstr(invv[k] - cl[k], 5) for k in cl},
           'normalized_atoms': {k: mp.nstr(v, dps - 5) for k, v in nvals.items()},
           'checks': checks, 'all_checks_pass': bool(ok)}
    return res, ok


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('raw')
    ap.add_argument('--dps', type=int, default=60)
    ap.add_argument('--windows', default='both', choices=['both', 'tight', 'safe'])
    ap.add_argument('--zero-tol', default='1e-10')
    ap.add_argument('--agree-tol', default='1e-8')
    ap.add_argument('--fill-two-kink-exact', action='store_true',
                    help='fill absent Z2_*/Q2_* coefficients from out/two_kink_exact.json (exact) and report deviations')
    ap.add_argument('--out')
    a = ap.parse_args()
    res, ok = run(load_raw(a.raw), a.windows, a.dps, a.zero_tol, a.agree_tol, a.fill_two_kink_exact)
    for k in ('C5', 'C6', 'D4', 'C7'):
        print(k, res['invariants'][k][:40], 'minus claim', res['minus_claim'][k])
    print('checks:', {k: v for k, v in res['checks'].items() if k not in ('below_tight_bound_scalars', 'two_kink_filled_from_exact')})
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    sys.exit(0 if ok else 1)
