#!/usr/bin/env python3
"""Exact precision budget of the C8-new raw scalars (archive-free).

The 114 tight scalars that C8 adds to the C7 set enter ONLY the ten new inputs (they are not in the C7 windows), and
C8 is affine in the new inputs (eq:C8assembly, reproduced by derive_invariants_C8.py).  So dC8/dx = sum_I c_I dI/dx with
the exact c_I.  The normalized atoms are built symbolically from the raw scalars by the same Leibniz convolution as the
assembler (tight windows), with the exact two-kink coefficients (out/C8/two_kink_exact_C8.json) substituted; for every
new scalar the derivative is reported exactly when it is a constant (the scalar enters linearly against exact
coefficients only) and flagged otherwise.  'abs_sigma_for_1e-4_in_C8' = 1e-4/|dC8/dx|.
Output: ../out/C8/budget_C8.json
"""
import json, re, sys, time
from pathlib import Path
import sympy as s

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'out' / 'C8'
t0 = time.time()
norm = json.load(open(OUT / 'normalized_atoms_C8.json'))
defs = json.load(open(OUT / 'input_definitions_C8.json'))
req = json.load(open(OUT / 'raw_requirements_C8.json'))
tk = json.load(open(OUT / 'two_kink_exact_C8.json'))
NEWC = {'W': 4, 'S': 2, 'U': s.Rational(3, 4), 'J9': s.Rational(1, 4), 'L3': s.Rational(3, 32), 'M21': -s.Rational(1, 4),
        'M12': s.Rational(1, 2), 'N2': -s.Rational(1, 16), 'Ndelta': s.Rational(1, 8), 'Kv': s.Rational(1, 32)}
z2, z3, z4, z5, z6, z7 = s.symbols('z2 z3 z4 z5 z6 z7')
ZL = {'z2': z2, 'z3': z3, 'z4': z4, 'z5': z5, 'z6': z6, 'z7': z7}


def parse_mzv(txt):
    tot = s.Integer(0)
    for term in txt.split(' + '):
        cs, bn = term.split(')*', 1)
        base = s.Integer(1) if bn == '1' else s.Mul(*[ZL[x] if '^' not in x else ZL[x.split('^')[0]]**int(x.split('^')[1])
                                                       for x in bn.split('*')])
        tot += s.Rational(cs[1:]) * base
    return tot


def raw_symbol(atom, p, k):
    if atom in tk['atoms']:                                   # exact two-kink coefficient (or exact zero)
        if atom in tk['constants'] and p == 0 and k == 0:
            return parse_mzv(tk['constants'][atom]['eps0_l0_exact'])
        return s.Rational(tk['atoms'][atom].get(str(p), {}).get(str(k), '0'))
    return s.Symbol(f'{atom}[{p},{k}]')


def conv(factors, m, win):
    wl = [[(int(p), k) for p, ks in win[f].items() for k in ks] for f in factors]
    total = s.Integer(0)
    def rec(i, psum, ksum, acc):
        nonlocal total
        last = i == len(factors) - 1
        for p, k in wl[i]:
            if ksum + k > m or (last and (psum + p != 0 or ksum + k != m)):
                continue
            x = raw_symbol(factors[i], p, k)
            if x == 0:
                continue
            if last:
                total += acc * x
            else:
                rec(i + 1, psum + p, ksum + k, acc * x)
    rec(0, 0, 0, s.Integer(1))
    return total


natom = {}
need = {at for nm in NEWC for at in defs[nm]['normalized_atoms']}
for at in sorted(need):
    info = norm[at]
    val = s.Integer(0)
    for term in info['leibniz_expansion'].split(' + '):
        cs, prod = term.split(')*', 1)
        val += s.Rational(cs[1:]) * conv(prod.split('*'), info['log_order_m'], info['raw_windows_tight'])
    natom[at] = s.expand(val)
print('normalized atoms built', len(natom), round(time.time() - t0, 1), 's', flush=True)


def to_expr(sx):
    loc = {}
    def rep(mo):
        nm = 'Y' + str(len(loc))
        loc[nm] = natom.get(mo.group(0), s.Symbol(mo.group(0)))
        return nm
    code = re.sub(r'[A-Z]+\d_\d\[v\dd\d\]', rep, sx)
    return s.sympify(code, locals=loc)


C8new = s.expand(sum(c * to_expr(defs[nm]['expansion_in_normalized_atoms']) for nm, c in NEWC.items()))
print('C8 new part built', round(time.time() - t0, 1), 's', flush=True)
rows = {}
new_scalars = req['new_tight_scalars_relative_to_C7']
for lbl in new_scalars:
    m = re.match(r'(\w+) \[eps\^(-?\d+) l\^(\d+)\]', lbl)
    atom, p, k = m.group(1), int(m.group(2)), int(m.group(3))
    if atom in tk['atoms']:
        continue                                            # exact
    x = s.Symbol(f'{atom}[{p},{k}]')
    dx = s.expand(s.diff(C8new, x))
    const = not any(str(y).endswith(']') and '[' in str(y) for y in dx.free_symbols)
    row = {'dC8_dx': s.sstr(dx) if const else 'value-dependent', 'constant': const}
    if const:
        v_ = abs(float(s.N(dx.subs({z2: s.zeta(2), z3: s.zeta(3), z4: s.zeta(4), z5: s.zeta(5), z6: s.zeta(6), z7: s.zeta(7)}))))
        row['abs_dC8_dx'] = float(f'{v_:.6g}')
        row['abs_sigma_for_1e-4_in_C8'] = float(f'{1e-4 / v_:.3g}') if v_ > 0 else None
    else:
        row['depends_on'] = sorted(str(y) for y in dx.free_symbols)[:8]
    rows[lbl] = row
top = sorted(((r['abs_dC8_dx'], k) for k, r in rows.items() if r.get('constant') and r.get('abs_dC8_dx')), reverse=True)
json.dump({
    'note': 'ARCHIVE-FREE exact sensitivities of C8 to the scalars that C8 adds to the C7 set (scripts/budget_C8.py). The '
            'sizes of the cancelling pieces (e.g. A9_1 ~ 1e5-1e6) are not known archive-free before production; the engine '
            'should quote relative precision with its own magnitudes. Exact two-kink scalars are not listed.',
    'C8_coefficients_of_new_inputs': {k: str(v) for k, v in NEWC.items()},
    'scalars': rows,
    'largest_constant_sensitivities': [{'scalar': k, 'abs_dC8_dx': v} for v, k in top[:30]],
}, open(OUT / 'budget_C8.json', 'w'), indent=1)
print('scalars', len(rows), 'constant', sum(r['constant'] for r in rows.values()), round(time.time() - t0, 1), 's')
for v, k in top[:15]:
    print(f'  {k:28s} |dC8/dx| = {v:.6g}')
