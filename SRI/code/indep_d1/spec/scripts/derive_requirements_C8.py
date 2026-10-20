#!/usr/bin/env python3
"""C8 extension of the definitions-only spec: definition chains and raw-moment requirements for
ALL 35 beta inputs of C8 = 8 T4 (the 25 C6/C7 inputs a..K and the 10 new inputs
W, S, U, J9, L3, M21, M12, N2, Ndelta, Kv), written from the note alone:
  * eq:normalization + eq:K8norm + eq:C9norm (l.392-412, 1139-1147), E differentiating every factor;
  * eq:subtraction (l.427-444) and its ninth-order extension (h8, b9, j7; l.1148-1156);
  * lambda6 = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0 (pattern extension, see EXTRAPOLATIONS; the note writes
    +lambda6 in h8 but does not define it);
  * the derivative dictionary (l.1120-1137) incl. the ten new inputs.

ARCHIVE-FREE: no archive file is read, no archive code imported, no archive number used.
It does not import the phase-1 script either (independent re-implementation); the 25 old inputs are
regenerated and must coincide with ../out/input_definitions.json (regression check).

Outputs (../out/C8/):
  input_definitions_C8.json   35 inputs -> expansion in normalized atoms (+ chains, raw leading terms)
  normalized_atoms_C8.json    every normalized atom -> Leibniz expansion in raw atoms, tight/safe windows
  raw_requirements_C8.json    tight/safe windows: total for C8 (35 inputs), per input, and NEW relative to C7
  definition_chain_C8.json    normalized responses, recurrence through 9th order, insertions, symbolic checks

Atom naming (as in phase 1):
  normalized atom  "C9_1[v0d0]" = [eps^0 l^1] d_v^0 d_delta^0 C9 at (v,delta) = (1,0)
  raw atom         "A7_d"       = d_delta A7 at (1,0) (FULL derivative, full eps/log expansion)
                   "EQ6_v"      = d_v (E Q6), E = d/d eta at eta = 0 (first endpoint-source derivative)
  derivative tag   'base' or 'v'*a + 'd'*b  (a d_v's then b d_delta's; e.g. vvd, vdd, ddd, vvvv, vvdd)
"""
import json, time
from math import comb, factorial
from pathlib import Path
import sympy as s

SPEC = Path(__file__).resolve().parent.parent
OUT = SPEC / 'out' / 'C8'
OUT.mkdir(parents=True, exist_ok=True)
v, d = s.symbols('v d')
t0 = time.time()

# ------------------------------------------------------------------------------------------ raw moments
RAW = ['A3', 'A5', 'A7', 'A9', 'Z2', 'Z4', 'Z6', 'Z8', 'Q2', 'Q4', 'Q6', 'Q8',
       'EA3', 'EA5', 'EA7', 'EZ2', 'EZ4', 'EZ6', 'EQ2', 'EQ4', 'EQ6']
R = {n: s.Function(n)(v, d) for n in RAW}
EA1 = -2 / (1 + d)                      # E A1 = j1 = int_0^1 [f(X)+f(1-X)] dX (analytic, v-independent)
A3, A5, A7, A9 = (R[k] for k in ('A3', 'A5', 'A7', 'A9'))
Z2, Z4, Z6, Z8 = (R[k] for k in ('Z2', 'Z4', 'Z6', 'Z8'))
Q2, Q4, Q6, Q8 = (R[k] for k in ('Q2', 'Q4', 'Q6', 'Q8'))
EA3, EA5, EA7 = (R[k] for k in ('EA3', 'EA5', 'EA7'))
EZ2, EZ4, EZ6 = (R[k] for k in ('EZ2', 'EZ4', 'EZ6'))
EQ2, EQ4, EQ6 = (R[k] for k in ('EQ2', 'EQ4', 'EQ6'))

# vacuum normalization from generating functions, E differentiating every factor (note l.402-405)
eta, g = s.symbols('eta g')
def src(name):
    if name == 'A1':
        return 1 + eta * EA1
    return R[name] + eta * R['E' + name] if ('E' + name) in R else R[name]

num_odd = sum(src(nm) * g**(2 * k) for k, nm in enumerate(['A1', 'A3', 'A5', 'A7', 'A9']))
num_evn = sum(src(nm) * g**(2 * (k + 1)) for k, nm in enumerate(['Q2', 'Q4', 'Q6', 'Q8']))
den = 1 + sum(src(nm) * g**(2 * (k + 1)) for k, nm in enumerate(['Z2', 'Z4', 'Z6', 'Z8']))
ser_o = s.expand(s.series(num_odd / den, g, 0, 9).removeO())
ser_e = s.expand(s.series(num_evn / den, g, 0, 9).removeO())
NORM = {}
for k, n in [(1, 3), (2, 5), (3, 7), (4, 9)]:
    c = s.expand(ser_o.coeff(g, 2 * k))
    NORM[f'C{n}'] = s.expand(c.subs(eta, 0))
    NORM[f'EC{n}'] = s.expand(c.diff(eta).subs(eta, 0))
for n in (2, 4, 6, 8):
    c = s.expand(ser_e.coeff(g, n))
    NORM[f'K{n}'] = s.expand(c.subs(eta, 0))
    NORM[f'EK{n}'] = s.expand(c.diff(eta).subs(eta, 0))
del NORM['EC9'], NORM['EK8']          # needed only for j9, lambda8 (C10 order)

NOTE_FORMS = {   # typed in from the note (eq:normalization l.398-405, eq:K8norm l.1142-1143, eq:C9norm l.1144-1146)
    'C3': A3 - Z2,
    'C5': A5 - A3 * Z2 + Z2**2 - Z4,
    'C7': A7 - A5 * Z2 + A3 * (Z2**2 - Z4) - Z2**3 + 2 * Z2 * Z4 - Z6,
    'C9': A9 - A7 * Z2 + A5 * (Z2**2 - Z4) + A3 * (-Z2**3 + 2 * Z2 * Z4 - Z6) + Z2**4 - 3 * Z2**2 * Z4 + Z4**2 + 2 * Z2 * Z6 - Z8,
    'K2': Q2, 'K4': Q4 - Q2 * Z2, 'K6': Q6 - Q4 * Z2 + Q2 * (Z2**2 - Z4),
    'K8': Q8 - Q6 * Z2 + Q4 * (Z2**2 - Z4) + Q2 * (-Z2**3 + 2 * Z2 * Z4 - Z6),
}
# E-responses written out by hand here (product rule on the note forms, EA1 included) -- independent of the series above
EXPLICIT_E = {
    'EC3': EA3 - EA1 * Z2 - EZ2,
    'EC5': EA5 - EA3 * Z2 - A3 * EZ2 + EA1 * (Z2**2 - Z4) + 2 * Z2 * EZ2 - EZ4,
    'EC7': (EA7 - EA5 * Z2 - A5 * EZ2 + EA3 * (Z2**2 - Z4) + A3 * (2 * Z2 * EZ2 - EZ4)
            + EA1 * (-Z2**3 + 2 * Z2 * Z4 - Z6) - 3 * Z2**2 * EZ2 + 2 * EZ2 * Z4 + 2 * Z2 * EZ4 - EZ6),
    'EK2': EQ2, 'EK4': EQ4 - EQ2 * Z2 - Q2 * EZ2,
    'EK6': EQ6 - EQ4 * Z2 - Q4 * EZ2 + EQ2 * (Z2**2 - Z4) + Q2 * (2 * Z2 * EZ2 - EZ4),
}
norm_checks = {}
for k, ex in list(NOTE_FORMS.items()) + list(EXPLICIT_E.items()):
    norm_checks[k] = s.expand(NORM[k] - ex) == 0
    assert norm_checks[k], k
print('normalization checks OK', time.time() - t0, flush=True)

NEW = ['W', 'S', 'U', 'J9', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'Kv']
NORM_FUNCS = ('C3', 'C5', 'C7', 'C9', 'K2', 'K4', 'K6', 'K8', 'EC3', 'EC5', 'EC7', 'EK2', 'EK4', 'EK6')


def atomize(ex):
    """normalized-response functions/derivatives -> symbols 'X_m[vadb]', then (v,delta) = (1,0)"""
    rep = {}
    for at in ex.atoms(s.Derivative):
        cnt = dict(at.variable_count)
        rep[at] = s.Symbol(f'{at.expr.func}[v{int(cnt.get(v, 0))}d{int(cnt.get(d, 0))}]')
    ex = ex.xreplace(rep)
    rep = {at: s.Symbol(f'{at.func}[v0d0]') for at in ex.atoms(s.Function)
           if str(at.func).rsplit('_', 1)[0] in NORM_FUNCS}
    ex = ex.xreplace(rep)
    return s.expand(ex.subs({v: 1, d: 0}))


def parse_norm_atom(sym):
    nm = str(sym)
    base, der = nm.split('[')
    name, m = base.rsplit('_', 1)
    return name, int(m), int(der[1:der.index('d')]), int(der[der.index('d') + 1:-1])


# ------------------------------------------------------------------------------------------ Leibniz + windows
def dername(a, b):
    return 'base' if (a, b) == (0, 0) else 'v' * a + 'd' * b


def nkinks(raw):
    return int(''.join(ch for ch in raw.split('_')[0] if ch.isdigit()))


def kind(raw):
    return raw.split('_')[0].rstrip('0123456789')


def pmin_safe(raw):
    return 0 if raw.split('_')[0] == 'Q2' else -(nkinks(raw) // 2)


def pmin_tight(raw):
    n, k, m = nkinks(raw), kind(raw), nkinks(raw) // 2
    if k in ('A', 'Z', 'EA'):
        return -m
    if k in ('Q', 'EZ'):
        return -(m - 1)
    if k == 'EQ':
        return 0 if m == 1 else -(m - 1)
    raise ValueError(raw)


INF = 10**6
def pmax(base):
    return {'Z2': 0, 'Q2': 1}.get(base, INF)


def raw_atom_name(at):
    if isinstance(at, s.Derivative):
        cnt = dict(at.variable_count)
        return f'{at.expr.func}_' + dername(int(cnt.get(v, 0)), int(cnt.get(d, 0))), str(at.expr.func)
    return f'{at.func}_base', str(at.func)


def leibniz_terms(name, iv, idd):
    ex = s.expand(s.diff(NORM[name], v, iv, d, idd))
    terms = []
    for term in s.Add.make_args(ex):
        factors, coef = [], s.Integer(1)
        for fac in s.Mul.make_args(term):
            base, e_ = fac.as_base_exp()
            if isinstance(base, s.Derivative) or (isinstance(base, s.Function) and str(base.func) in R):
                factors += [base] * int(e_)
            else:
                coef *= fac
        coef = coef.subs({v: 1, d: 0})
        if coef != 0:
            terms.append((coef, factors))
    return terms


def windows(factors, m, pmin):
    """{raw_atom: {p: set(k)}} of coefficients [eps^p l^k] that can reach [eps^0 l^m] of the product"""
    info = [raw_atom_name(f) for f in factors]
    out = {}
    for j, (atom, base) in enumerate(info):
        others = [b for i, (_, b) in enumerate(info) if i != j]
        hi = -sum(pmin(b) for b in others)
        rest_hi = sum(pmax(b) for b in others)
        lo = pmin(base) if rest_hi >= INF else max(pmin(base), -rest_hi)
        ks = {m} if not others else set(range(m + 1))
        for p in range(lo, hi + 1):
            if base == 'Z2' and p not in (-1, 0):
                continue
            if base == 'Q2' and p not in (0, 1):
                continue
            out.setdefault(atom, {}).setdefault(p, set()).update(ks)
    return out


def merge(dst, src_):
    for atom, w in src_.items():
        dd = dst.setdefault(atom, {})
        for p, ks in w.items():
            dd.setdefault(p, set()).update(ks)


def fmt(acc):
    out = {}
    for a, w in sorted(acc.items(), key=lambda x: (nkinks(x[0]), x[0])):
        out[a] = {'kinks': nkinks(a), 'type': kind(a), 'endpoint_source': a.startswith('E'), 'derivative': a.split('_', 1)[1],
                  'eps_powers': sorted(w), 'log_orders_by_power': {str(p): sorted(w[p]) for p in sorted(w)}}
    return out


def scalars(acc):
    return {(a, p, k) for a, w in acc.items() for p, ks in w.items() for k in ks}


def struct_zero(a, p):
    b = a.split('_')[0]
    return (b == 'Z2' and p not in (-1, 0)) or (b == 'Q2' and p not in (0, 1))



def main():
    # ------------------------------------------------------------------------------------------ recurrence
    def N(name, m):
        return s.Function(f'{name}_{m}')(v, d)

    C30, C50, C70 = N('C3', 0), N('C5', 0), N('C7', 0)
    C31, C51, C71, C91 = N('C3', 1), N('C5', 1), N('C7', 1), N('C9', 1)
    Q20 = N('K2', 0)
    K40, K41, K60, K61, K81 = N('K4', 0), N('K4', 1), N('K6', 0), N('K6', 1), N('K8', 1)
    EC30, EC50, EC70 = N('EC3', 0), N('EC5', 0), N('EC7', 0)
    EQ20, EK40, EK60 = N('EK2', 0), N('EK4', 0), N('EK6', 0)

    j1 = -2 / (1 + d)
    j3 = -2 * s.diff(C30, v) + EC30
    j5 = -2 * s.diff(C50, v) + EC50
    j7 = -2 * s.diff(C70, v) + EC70                                         # note l.1156
    l2 = -2 * Q20 - 4 * v * s.diff(Q20, v) + 2 * v * EQ20
    l4 = -2 * K40 - 4 * v * s.diff(K40, v) + 2 * v * EK40
    l6 = -2 * K60 - 4 * v * s.diff(K60, v) + 2 * v * EK60                    # EXTRAPOLATION (pattern)
    b3 = C31 + 2 * v * j1
    h4 = K41 - 2 * Q20 * b3 + l2
    b5 = C51 - 3 * C30 * b3 - 2 * v * j1 * h4 + 2 * v * j3
    h6 = K61 - 2 * Q20 * b5 - 4 * K40 * b3 - l2 * h4 + l4
    b7 = C71 - 3 * C30 * b5 - 5 * C50 * b3 - 2 * v * j1 * h6 - 2 * v * j3 * h4 + 2 * v * j5
    h8 = K81 - 2 * Q20 * b7 - 4 * K40 * b5 - 6 * K60 * b3 - l2 * h6 - l4 * h4 + l6            # note l.1149-1151
    b9 = (C91 - 3 * C30 * b7 - 5 * C50 * b5 - 7 * C70 * b3
          - 2 * v * j1 * h8 - 2 * v * j3 * h6 - 2 * v * j5 * h4 + 2 * v * j7)                   # note eq:b9 l.1152-1155

    INPUTS = [  # name, sympy definition, string definition, group  (note derivative dictionary l.1122-1137)
        ('a', s.diff(b3, v), 'd_v b3', 'old'),
        ('p', s.diff(b3, d), 'd_delta b3', 'old'),
        ('A', s.diff(b3, v, 2) / 2, 'd_v^2 b3 / 2', 'old'),
        ('E', s.diff(b3, v, d), 'd_v d_delta b3', 'old'),
        ('c', -4 * h4, '-4 h4', 'old'),
        ('f', -4 * s.diff(h4, v), '-4 d_v h4', 'old'),
        ('b', b5, 'b5', 'old'),
        ('G', s.diff(b5, v), 'd_v b5', 'C5/D3'),
        ('q', -4 * s.diff(h4, d), '-4 d_delta h4', 'C5/D3'),
        ('k', -4 * h6, '-4 h6', 'C5/D3'),
        ('V', s.diff(b3, d, 2) / 2, 'd_delta^2 b3 / 2', 'C6'),
        ('R', s.diff(b5, d), 'd_delta b5', 'C6'),
        ('J', b7, 'b7', 'C6'),
        ('L', -2 * s.diff(h4, v, 2), '-2 d_v^2 h4', 'C6'),
        ('M', -4 * s.diff(h4, v, d), '-4 d_v d_delta h4', 'C6'),
        ('N', -4 * s.diff(h6, v), '-4 d_v h6', 'C6'),
        ('alpha', s.diff(b3, v, 3) / 6, 'd_v^3 b3 / 6', 'C7'),
        ('beta', s.diff(b3, v, 2, d) / 2, 'd_v^2 d_delta b3 / 2', 'C7'),
        ('gamma', s.diff(b3, v, d, 2) / 2, 'd_v d_delta^2 b3 / 2', 'C7'),
        ('Phi', s.diff(b5, v, 2) / 2, 'd_v^2 b5 / 2', 'C7'),
        ('Psi', s.diff(b5, v, d), 'd_v d_delta b5', 'C7'),
        ('Omega', s.diff(b7, v), 'd_v b7', 'C7'),
        ('Q', -2 * s.diff(h4, d, 2), '-2 d_delta^2 h4', 'C7'),
        ('P', -4 * s.diff(h6, d), '-4 d_delta h6', 'C7'),
        ('K', -4 * h8, '-4 h8', 'C7'),
        # ---- the ten new C8 inputs (note l.1131-1135)
        ('W', s.diff(b3, d, 3) / 6, 'd_delta^3 b3 / 6', 'C8'),
        ('S', s.diff(b5, d, 2) / 2, 'd_delta^2 b5 / 2', 'C8'),
        ('U', s.diff(b7, d), 'd_delta b7', 'C8'),
        ('J9', b9, 'b9', 'C8'),
        ('L3', -s.Rational(2, 3) * s.diff(h4, v, 3), '-(2/3) d_v^3 h4', 'C8'),
        ('M21', -2 * s.diff(h4, v, 2, d), '-2 d_v^2 d_delta h4', 'C8'),
        ('M12', -2 * s.diff(h4, v, d, 2), '-2 d_v d_delta^2 h4', 'C8'),
        ('N2', -2 * s.diff(h6, v, 2), '-2 d_v^2 h6', 'C8'),
        ('Ndelta', -4 * s.diff(h6, v, d), '-4 d_v d_delta h6', 'C8'),
        ('Kv', -4 * s.diff(h8, v), '-4 d_v h8', 'C8'),
    ]
    defs, norm_atoms_all = {}, set()
    for name, ex, txt, grp in INPUTS:
        e = atomize(ex)
        atoms = sorted(e.free_symbols, key=str)
        norm_atoms_all |= set(atoms)
        defs[name] = {'group': grp, 'definition': txt + '  at (v,delta)=(1,0)', 'expansion_in_normalized_atoms': s.sstr(e),
                      'n_terms': len(s.Add.make_args(e)), 'normalized_atoms': [str(a) for a in atoms],
                      'constant_part': s.sstr(e.subs({a: 0 for a in atoms}))}
        defs[name]['_expr'] = e
    print('35 inputs expanded', time.time() - t0, flush=True)

    # lambda6 dependence: which inputs change if lambda6 is altered (exact test: perturb lambda6 by a free symbol)
    lam = s.Symbol('LAMBDA6_SHIFT')
    h8x = h8 + lam * (1 + (v - 1) + (v - 1)**2)          # arbitrary (v)-dependent shift of lambda6
    b9x = (C91 - 3 * C30 * b7 - 5 * C50 * b5 - 7 * C70 * b3 - 2 * v * j1 * h8x
           - 2 * v * j3 * h6 - 2 * v * j5 * h4 + 2 * v * j7)
    lam_dep = {'K': s.expand((-4 * h8x).subs({v: 1, d: 0}) - (-4 * h8).subs({v: 1, d: 0})) != 0,
               'Kv': s.expand(s.diff(-4 * h8x, v).subs({v: 1, d: 0}) - s.diff(-4 * h8, v).subs({v: 1, d: 0})) != 0,
               'J9': s.expand(b9x.subs({v: 1, d: 0}) - b9.subs({v: 1, d: 0})) != 0}
    for nm in defs:
        defs[nm]['depends_on_lambda6'] = lam_dep.get(nm, False)
    assert lam_dep == {'K': True, 'Kv': True, 'J9': True}

    # regression: the 25 old inputs must equal the phase-1 definitions
    old = json.load(open(SPEC / 'out' / 'input_definitions.json'))
    regress = {}
    for nm in old:
        regress[nm] = s.expand(s.sympify(old[nm]['expansion_in_normalized_atoms'].replace('[', '__').replace(']', '__'))
                               - s.sympify(defs[nm]['expansion_in_normalized_atoms'].replace('[', '__').replace(']', '__'))) == 0
    assert all(regress.values()), regress
    print('phase-1 regression OK', flush=True)

    norm_info = {}
    for sym in sorted(norm_atoms_all, key=str):
        name, m, iv, idd = parse_norm_atom(sym)
        terms = leibniz_terms(name, iv, idd)
        w_s, w_t = {}, {}
        for coef, facs in terms:
            merge(w_s, windows(facs, m, pmin_safe))
            merge(w_t, windows(facs, m, pmin_tight))
        norm_info[str(sym)] = {
            'normalized_response': name, 'log_order_m': m, 'd_v_order': iv, 'd_delta_order': idd,
            'meaning': f'[eps^0 l^{m}] d_v^{iv} d_delta^{idd} {name} at (v,delta)=(1,0)',
            'leibniz_expansion': ' + '.join(f'({s.sstr(c)})*' + '*'.join(raw_atom_name(f)[0] for f in fs) for c, fs in terms),
            'n_leibniz_terms': len(terms),
            'raw_windows_safe': {a: {str(p): sorted(k) for p, k in sorted(w.items())} for a, w in sorted(w_s.items())},
            'raw_windows_tight': {a: {str(p): sorted(k) for p, k in sorted(w.items())} for a, w in sorted(w_t.items())},
            'used_by_inputs': sorted(nm for nm in defs if str(sym) in defs[nm]['normalized_atoms']),
            'new_for_C8': None,
        }
    old_norm = json.load(open(SPEC / 'out' / 'normalized_atoms.json'))
    for k_, inf in norm_info.items():
        inf['new_for_C8'] = k_ not in old_norm
        if k_ in old_norm:                      # regression: identical Leibniz expansion and windows
            for key in ('leibniz_expansion', 'raw_windows_safe', 'raw_windows_tight'):
                assert old_norm[k_][key] == inf[key], (k_, key)
    print('normalized atoms', len(norm_info), '(new', sum(i['new_for_C8'] for i in norm_info.values()), ')', time.time() - t0, flush=True)

    req_by_input = {key: {} for key in ('safe', 'tight')}
    total = {'safe': {}, 'tight': {}, 'safe_C7': {}, 'tight_C7': {}}
    for name in defs:
        for key in ('safe', 'tight'):
            acc = {}
            for at in defs[name]['normalized_atoms']:
                w = norm_info[at]['raw_windows_' + key]
                merge(acc, {a: {int(p): set(k) for p, k in ww.items()} for a, ww in w.items()})
            req_by_input[key][name] = acc
            merge(total[key], acc)
            if name not in NEW:
                merge(total[key + '_C7'], acc)


    for name in defs:
        defs[name]['raw_requirements_safe'] = fmt(req_by_input['safe'][name])
        defs[name]['raw_requirements_tight'] = fmt(req_by_input['tight'][name])
        defs[name]['max_kinks'] = max(r['kinks'] for r in defs[name]['raw_requirements_safe'].values())

    # regression: phase-1 total requirements = C7 part here
    old_req = json.load(open(SPEC / 'out' / 'raw_requirements.json'))
    assert fmt(total['tight_C7']) == old_req['total_tight'] and fmt(total['safe_C7']) == old_req['total_safe']

    # ------------------------------------------------------------------------------------------ raw leading terms (note F1-F4 structure)
    def raw_coefficient_in_input(name, raw_atom, p, k):
        """exact coefficient of a raw scalar that enters LINEARLY (through a single-factor Leibniz term) in an input:
        sum over normalized atoms X of dInput/dX * (coefficient of the lone raw factor in X's Leibniz expansion, if X has m == k
        and p == 0).  Only meaningful for scalars that occur in no product (checked)."""
        e = defs[name]['_expr']
        tot = s.Integer(0)
        for at in defs[name]['normalized_atoms']:
            inf = norm_info[at]
            if p != 0 or inf['log_order_m'] != k:
                continue
            dX = s.diff(e, s.Symbol(at))
            for term in inf['leibniz_expansion'].split(' + '):
                cs, prod = term.split(')*', 1)
                if prod == raw_atom:
                    tot += dX * s.Rational(cs[1:])
        tot = s.expand(tot)
        return tot


    LEAD = {  # note Secs. 16 (F1-F4): leading raw scalars of the new inputs with the coefficients the note implies
        'Ndelta': [('Q6_vd', 0, 1, -4, 'N_delta = -4 P6 + ..., P6 = [eps^0 l] Q6_vd (eq:NdP6, l.1328-1331)'),
                   ('Q4_vvd', 0, 0, 16, '(lambda4)_vd = -6 k_vd - 4 k_vvd + 2 e_d + 2 e_vd (l.1319-1321): -4 * (-4) = +16 on (Q4_vvd)_0'),
                   ('EQ4_vd', 0, 0, -8, 'same line: -4 * 2 = -8 on (EE Q4_vd)_0')],
        'U': [('A7_d', 0, 1, 1, 'U = A7_d_1 - Z6_d_1 + 2 (EE A5_d)_0 - 2 (EE Z4_d)_0 + D_lower (l.1344-1347)'),
              ('Z6_d', 0, 1, -1, 'same'), ('EA5_d', 0, 0, 2, 'same'), ('EZ4_d', 0, 0, -2, 'same')],
        'Kv': [('Q8_v', 0, 1, -4, 'K_v = -4 P8 + 16 X_vv - 8 X_E + S3, P8 = [eps^0 l] Q8_v (l.1363-1366)'),
               ('Q6_vv', 0, 0, 16, 'same, X_vv = [eps^0 l^0] Q6_vv (via lambda6_v)'),
               ('EQ6_v', 0, 0, -8, 'same, X_E = [eps^0 l^0] d_v (EE Q6) (via lambda6_v)')],
        'J9': [('A9_base', 0, 1, 1, 'J9 = A9_1 - Z8_1 + 2 (EE A7)_0 - 2 (EE Z6)_0 + D9_lower (l.1388-1391)'),
               ('Z8_base', 0, 1, -1, 'same'), ('EA7_base', 0, 0, 2, 'same'), ('EZ6_base', 0, 0, -2, 'same')],
    }
    lead_checks = {}
    for nm, rows in LEAD.items():
        for raw_atom, p, k, expect, src_ in rows:
            got = raw_coefficient_in_input(nm, raw_atom, p, k)
            lead_checks[f'{nm}: coefficient of {raw_atom}[eps^{p} l^{k}]'] = {'derived': str(got), 'note_implied': str(expect),
                                                                             'agree': got == expect, 'note': src_}
            assert got == expect, (nm, raw_atom, got, expect)
    # the 13 Leibniz terms of D_norm (note l.1306-1309): d_v d_delta (-Q4 Z2 + Q2 Z2^2 - Q2 Z4), distinct terms
    Dn = s.expand(s.diff(-Q4 * Z2 + Q2 * Z2**2 - Q2 * Z4, v, d))
    n_dnorm = len(s.Add.make_args(Dn))
    lead_checks['D_norm has 13 distinct Leibniz terms (note l.1309)'] = {'derived': n_dnorm, 'agree': n_dnorm == 13}
    assert n_dnorm == 13
    # (lambda4)_vd formula of the note l.1319-1321
    k_, e_ = s.Function('k')(v, d), s.Function('e')(v, d)
    lam4 = -2 * k_ - 4 * v * s.diff(k_, v) + 2 * v * e_
    lam4_vd = s.diff(lam4, v, d).subs(v, 1)
    note_l4 = (-6 * s.diff(k_, v, d) - 4 * s.diff(k_, v, v, d) + 2 * s.diff(e_, d) + 2 * s.diff(e_, v, d)).subs(v, 1)
    lead_checks['(lambda4)_vd = -6 k_vd - 4 k_vvd + 2 e_d + 2 e_vd (note l.1319-1321)'] = {'agree': s.simplify(lam4_vd - note_l4) == 0}
    assert s.simplify(lam4_vd - note_l4) == 0
    print('note F1-F4 structure checks OK', time.time() - t0, flush=True)

    # ------------------------------------------------------------------------------------------ outputs
    for nm in defs:
        defs[nm].pop('_expr')
    json.dump(defs, open(OUT / 'input_definitions_C8.json', 'w'), indent=1)
    json.dump(norm_info, open(OUT / 'normalized_atoms_C8.json', 'w'), indent=1)

    tight_all, safe_all = scalars(total['tight']), scalars(total['safe'])
    tight_C7, safe_C7 = scalars(total['tight_C7']), scalars(total['safe_C7'])
    tight_new = sorted(tight_all - tight_C7)
    safe_new = sorted(safe_all - safe_C7)
    def lbl(x):
        a, p, k = x
        return f'{a} [eps^{p} l^{k}]'
    extras = sorted(safe_all - tight_all)
    json.dump({
        'note': 'ARCHIVE-FREE raw requirements for C8 = 8 T4 (all 35 inputs). Generated by scripts/derive_requirements_C8.py.',
        'safe_bounds': 'pmin = -floor(n/2) for every raw moment except Q2 (0); Z2 support {-1,0}, Q2 support {0,1}',
        'tight_bounds': 'pmin: A_{2m+1}, Z_{2m}, EA_{2m+1}: -m; Q_{2m}, EZ_{2m}: -(m-1); EQ2: 0, EQ_{2m>=4}: -(m-1); same Z2/Q2 supports '
                        '(new here: A9, Z8 -> -4; Q8, EA7 -> -3; EZ6, EQ6 -> -2)',
        'log_orders': 'only l^0 and l^1 of any raw coefficient can reach [eps^0 l^0], [eps^0 l^1] of a product; a raw moment entering '
                      'linearly needs only l^m',
        'counts': {'atoms_tight_C8': len(total['tight']), 'atoms_tight_C7': len(total['tight_C7']),
                   'scalars_tight_C8': len(tight_all), 'scalars_tight_C7': len(tight_C7), 'scalars_tight_new': len(tight_new),
                   'scalars_safe_C8': len(safe_all), 'scalars_safe_C7': len(safe_C7), 'scalars_safe_new': len(safe_new),
                   'safe_minus_tight_C8': len(extras),
                   'below_tight_bound_C8': sum(1 for a, p, k in extras if p < pmin_tight(a)),
                   'two_kink_scalars_tight_C8': sum(1 for a, p, k in tight_all if nkinks(a) == 2 and not a.startswith('E')),
                   'new_atoms': sorted(set(total['tight']) - set(total['tight_C7']))},
        'total_tight': fmt(total['tight']), 'total_safe': fmt(total['safe']),
        'new_tight_scalars_relative_to_C7': [lbl(x) for x in tight_new],
        'new_safe_scalars_relative_to_C7': [lbl(x) for x in safe_new],
        'safe_minus_tight': {'below_tight_bound_must_vanish': [lbl(x) for x in extras if x[1] < pmin_tight(x[0])],
                             'genuine_positive_power_extras': [lbl(x) for x in extras if x[1] >= pmin_tight(x[0])]},
        'by_input_tight': {nm: {a: r['log_orders_by_power'] for a, r in defs[nm]['raw_requirements_tight'].items()} for nm in NEW},
    }, open(OUT / 'raw_requirements_C8.json', 'w'), indent=1)

    json.dump({
        'note': 'ARCHIVE-FREE definition chain for C8 (scripts/derive_requirements_C8.py); all symbolic checks asserted.',
        'normalized_responses': {k: s.sstr(v_) for k, v_ in NOTE_FORMS.items()} | {k: s.sstr(v_).replace('-2/(d + 1)', 'EA1')
                                                                                  for k, v_ in EXPLICIT_E.items()},
        'normalized_response_checks': {'generating_function_equals_note_and_explicit_product_rule': norm_checks},
        'recurrence_9th_order': {
            'j1': '-2/(1+delta)', 'j3': '-2 d_v C3_0 + EC3_0', 'j5': '-2 d_v C5_0 + EC5_0', 'j7': '-2 d_v C7_0 + EC7_0  (note l.1156)',
            'lambda2': '-2 Q2_0 - 4 v d_v Q2_0 + 2 v EQ2_0', 'lambda4': '-2 K4_0 - 4 v d_v K4_0 + 2 v EK4_0',
            'lambda6': '-2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0  [pattern extension; EXTRAPOLATIONS]',
            'b3': 'C3_1 + 2 v j1', 'h4': 'K4_1 - 2 Q2_0 b3 + lambda2', 'b5': 'C5_1 - 3 C3_0 b3 - 2 v j1 h4 + 2 v j3',
            'h6': 'K6_1 - 2 Q2_0 b5 - 4 K4_0 b3 - lambda2 h4 + lambda4',
            'b7': 'C7_1 - 3 C3_0 b5 - 5 C5_0 b3 - 2 v j1 h6 - 2 v j3 h4 + 2 v j5',
            'h8': 'K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6  (note l.1149-1151)',
            'b9': 'C9_1 - 3 C3_0 b7 - 5 C5_0 b5 - 7 C7_0 b3 - 2 v j1 h8 - 2 v j3 h6 - 2 v j5 h4 + 2 v j7  (note eq:b9, l.1152-1155)',
            'rules': 'all quantities functions of (v,delta), v = b0^2; derivatives act on the FULL recurrence (explicit v, j1(delta), '
                     'lambda_n, j_n) before (v,delta) = (1,0); normalized products are formed with full eps/log expansions before '
                     'extraction (note l.1157-1158: an unavailable raw scalar is an error, not a zero)'},
        'lambda6_dependence': {nm: defs[nm]['depends_on_lambda6'] for nm in defs if defs[nm]['depends_on_lambda6']},
        'note_F1_F4_structure_checks': lead_checks,
        'regression_vs_phase1': {'25_old_input_expansions_identical': all(regress.values()),
                                 'common_normalized_atoms_identical_leibniz_and_windows': True,
                                 'C7_part_of_requirements_identical_to_out/raw_requirements.json': True},
    }, open(OUT / 'definition_chain_C8.json', 'w'), indent=1)

    print('C8 tight: atoms', len(total['tight']), 'scalars', len(tight_all), '(C7 part', len(tight_C7), ', new', len(tight_new), ')')
    print('C8 safe : scalars', len(safe_all), '(new', len(safe_new), '), safe-tight', len(extras))
    print('new atoms:', sorted(set(total['tight']) - set(total['tight_C7'])))
    print('done', round(time.time() - t0, 1), 's')



if __name__ == '__main__':
    main()
