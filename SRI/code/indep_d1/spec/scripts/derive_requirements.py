#!/usr/bin/env python3
"""Derive the definition chains and the minimal raw-moment requirements for the
25 beta inputs (a..K) of the C6/C7 assembly, from the DEFINITIONS in the
compendium note (Secs. 4-6, eq:normalization, eq:subtraction and its h8
extension, derivative dictionary lines 1120-1137).

Nothing here imports or reads archive code or archive data.  Pure SymPy algebra.

Outputs (in ../out/):
  input_definitions.json   each input -> expression in normalized-response atoms
  normalized_atoms.json    each normalized atom -> Leibniz expansion in raw atoms
  raw_requirements.json    minimal (eps-power, log-order) windows for every raw atom,
                           under 'safe' and 'tight' leading-power bounds, per input
                           and in total.

Atom naming
  normalized atom  "C3_1[v1d0]" = [eps^0 l^1] d_v^1 d_delta^0 C3 at (v,delta)=(1,0)
  raw atom         "A5_vd"      = d_v d_delta A5 at (1,0) (full eps/log expansion)
                   "EA3_v"      = d_v (E A3), E = d/d eta at eta=0 (endpoint source)
"""
import json, itertools, sys, time
from pathlib import Path
import sympy as s

OUT = Path(__file__).resolve().parent.parent / 'out'
OUT.mkdir(exist_ok=True)
v, d = s.symbols('v d')

# ----------------------------------------------------------------------------
# raw moments (functions of v, delta); A1 = 1, E A1 = j1 = -2/(1+delta)
RAW = ['A3', 'A5', 'A7', 'Z2', 'Z4', 'Z6', 'Q2', 'Q4', 'Q6', 'Q8',
       'EA3', 'EA5', 'EZ2', 'EZ4', 'EQ2', 'EQ4', 'EQ6']
R = {n: s.Function(n)(v, d) for n in RAW}
A1 = s.Integer(1)
EA1 = -2 / (1 + d)

A3, A5, A7, Z2, Z4, Z6 = (R[k] for k in ['A3', 'A5', 'A7', 'Z2', 'Z4', 'Z6'])
Q2, Q4, Q6, Q8 = (R[k] for k in ['Q2', 'Q4', 'Q6', 'Q8'])

# Vacuum normalization (note eq:normalization, eq:K8norm): ratio of generating
# functions; the E-versions are obtained by differentiating every factor.
eta, g = s.symbols('eta g')
def with_source(name):
    # raw moment M -> M + eta*EM  (first source derivative only)
    if name in ('A1',):
        return 1 + eta * EA1
    return R[name] + eta * R['E' + name] if ('E' + name) in R else R[name]

def ratio_coeffs(num_names, den_names, order):
    """coefficients of g^(2k) in (sum num g^2k)/(1 + sum den g^2k)"""
    num = sum(with_source(nm) * g**(2 * k) for k, nm in enumerate(num_names))
    den = 1 + sum(with_source(nm) * g**(2 * (k + 1)) for k, nm in enumerate(den_names))
    ser = s.series(num / den, g, 0, 2 * order + 1).removeO()
    return [s.expand(ser.coeff(g, 2 * k)) for k in range(order + 1)]

odd = ratio_coeffs(['A1', 'A3', 'A5', 'A7'], ['Z2', 'Z4', 'Z6'], 3)
# current numerator Q2 g^2 + Q4 g^4 + ... : shift index
evn_num = sum(with_source(nm) * g**(2 * (k + 1)) for k, nm in enumerate(['Q2', 'Q4', 'Q6', 'Q8']))
den = 1 + sum(with_source(nm) * g**(2 * (k + 1)) for k, nm in enumerate(['Z2', 'Z4', 'Z6']))
ser = s.series(evn_num / den, g, 0, 9).removeO()
evn = {2 * k: s.expand(ser.coeff(g, 2 * k)) for k in range(1, 5)}

NORM = {}
for k, n in [(1, 3), (2, 5), (3, 7)]:
    NORM[f'C{n}'] = s.expand(odd[k].subs(eta, 0))
    NORM[f'EC{n}'] = s.expand(odd[k].diff(eta).subs(eta, 0))
for n in [2, 4, 6, 8]:
    NORM[f'K{n}'] = s.expand(evn[n].subs(eta, 0))
    NORM[f'EK{n}'] = s.expand(evn[n].diff(eta).subs(eta, 0))
# EC7 and EK8 are not needed for C6/C7 (they enter j7, lambda8 at C8 order only)
del NORM['EC7'], NORM['EK8']

# Check against the explicit formulas of the note / stage notes
chk = {
    'C3': A3 - Z2,
    'C5': A5 - A3 * Z2 + Z2**2 - Z4,
    'C7': A7 - A5 * Z2 + A3 * (Z2**2 - Z4) - Z2**3 + 2 * Z2 * Z4 - Z6,
    'K2': Q2, 'K4': Q4 - Q2 * Z2, 'K6': Q6 - Q4 * Z2 + Q2 * (Z2**2 - Z4),
    'K8': Q8 - Q6 * Z2 + Q4 * (Z2**2 - Z4) + Q2 * (-Z2**3 + 2 * Z2 * Z4 - Z6),
    'EC3': R['EA3'] - EA1 * Z2 - R['EZ2'],
    'EC5': R['EA5'] - R['EA3'] * Z2 - A3 * R['EZ2'] + EA1 * (Z2**2 - Z4) + 2 * Z2 * R['EZ2'] - R['EZ4'],
    'EK2': R['EQ2'],
    'EK4': R['EQ4'] - R['EQ2'] * Z2 - Q2 * R['EZ2'],
    'EK6': R['EQ6'] - R['EQ4'] * Z2 - Q4 * R['EZ2'] + R['EQ2'] * (Z2**2 - Z4) + Q2 * (2 * Z2 * R['EZ2'] - R['EZ4']),
}
for k, ex in chk.items():
    assert s.simplify(NORM[k] - ex) == 0, k

# ----------------------------------------------------------------------------
# Finite-response recurrence (note eq:subtraction lines 427-444, h8 at 1149-1151)
def N(name, m):
    return s.Function(f'{name}_{m}')(v, d)

C30, C31, C50, C51, C71 = N('C3', 0), N('C3', 1), N('C5', 0), N('C5', 1), N('C7', 1)
Q20 = N('K2', 0)
K40, K41, K60, K61, K81 = N('K4', 0), N('K4', 1), N('K6', 0), N('K6', 1), N('K8', 1)
EC30, EC50 = N('EC3', 0), N('EC5', 0)
EQ20, EK40, EK60 = N('EK2', 0), N('EK4', 0), N('EK6', 0)

j1 = -2 / (1 + d)                                    # = E A1 = int_0^1 [f(X)+f(1-X)] dX
j3 = -2 * s.diff(C30, v) + EC30
j5 = -2 * s.diff(C50, v) + EC50
l2 = -2 * Q20 - 4 * v * s.diff(Q20, v) + 2 * v * EQ20
l4 = -2 * K40 - 4 * v * s.diff(K40, v) + 2 * v * EK40
l6 = -2 * K60 - 4 * v * s.diff(K60, v) + 2 * v * EK60
b3 = C31 + 2 * v * j1
h4 = K41 - 2 * Q20 * b3 + l2
b5 = C51 - 3 * C30 * b3 - 2 * v * j1 * h4 + 2 * v * j3
h6 = K61 - 2 * Q20 * b5 - 4 * K40 * b3 - l2 * h4 + l4
b7 = C71 - 3 * C30 * b5 - 5 * C50 * b3 - 2 * v * j1 * h6 - 2 * v * j3 * h4 + 2 * v * j5
h8 = K81 - 2 * Q20 * b7 - 4 * K40 * b5 - 6 * K60 * b3 - l2 * h6 - l4 * h4 + l6

INPUTS = [  # name, sympy definition, string definition, group
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
]

def atomize(ex):
    """replace normalized-response functions/derivatives by symbols, then set v=1,d=0"""
    rep = {}
    for at in ex.atoms(s.Derivative):
        f = at.expr
        cnt = dict(at.variable_count)
        rep[at] = s.Symbol(f'{f.func}[v{int(cnt.get(v, 0))}d{int(cnt.get(d, 0))}]')
    ex = ex.xreplace(rep)
    rep = {}
    for at in ex.atoms(s.Function):
        if at.func.__name__.split('_')[0] in ('C3', 'C5', 'C7', 'K2', 'K4', 'K6', 'K8', 'EC3', 'EC5', 'EK2', 'EK4', 'EK6'):
            rep[at] = s.Symbol(f'{at.func}[v0d0]')
    ex = ex.xreplace(rep)
    return s.expand(ex.subs({v: 1, d: 0}))

def parse_norm_atom(sym):
    nm = str(sym)
    base, der = nm.split('[')
    name, m = base.rsplit('_', 1)
    iv = int(der[1:der.index('d')]); idd = int(der[der.index('d') + 1:-1])
    return name, int(m), iv, idd

t0 = time.time()
defs = {}
norm_atoms_all = set()
for name, ex, txt, grp in INPUTS:
    e = atomize(ex)
    atoms = sorted(e.free_symbols, key=str)
    norm_atoms_all |= set(atoms)
    defs[name] = {'group': grp, 'definition': txt + '  at (v,delta)=(1,0)',
                  'expansion_in_normalized_atoms': s.sstr(e),
                  'n_terms': len(s.Add.make_args(e)),
                  'normalized_atoms': [str(a) for a in atoms],
                  'constant_part': s.sstr(e.subs({a: 0 for a in atoms}))}
print('inputs expanded', time.time() - t0, flush=True)

# ----------------------------------------------------------------------------
# Normalized atom -> raw Leibniz expansion and requirement windows.
DERNAME = {(0, 0): 'base', (1, 0): 'v', (2, 0): 'vv', (3, 0): 'vvv', (0, 1): 'd', (1, 1): 'vd',
           (2, 1): 'vvd', (0, 2): 'dd', (1, 2): 'vdd'}
NORMNAME = {'C3': 'C3', 'C5': 'C5', 'C7': 'C7', 'K2': 'K2', 'K4': 'K4', 'K6': 'K6', 'K8': 'K8',
            'EC3': 'EC3', 'EC5': 'EC5', 'EK2': 'EK2', 'EK4': 'EK4', 'EK6': 'EK6'}

def nkinks(raw):
    return int(''.join(ch for ch in raw if ch.isdigit()))

def kind(raw):
    return raw.rstrip('0123456789')

# leading cutoff power bounds pmin (coefficients of eps^p vanish for p < pmin)
def pmin_safe(raw):
    n = nkinks(raw); k = kind(raw)
    if k == 'Q' and n == 2:
        return 0
    return -(n // 2)

def pmin_tight(raw):
    n = nkinks(raw); k = kind(raw); m = n // 2
    if k in ('A', 'Z', 'EA'):
        return -m
    if k == 'Q':
        return -(m - 1)
    if k == 'EZ':
        return -(m - 1)
    if k == 'EQ':
        return 0 if m == 1 else -(m - 1)
    raise ValueError(raw)

INF = 10**6
def pmax(raw):
    # exact supports: Z2 in {-1,0}, Q2 in {0,1} (all v/delta derivatives): elementary
    if raw == 'Z2':
        return 0
    if raw == 'Q2':
        return 1
    return INF

def raw_atom_name(at):
    if isinstance(at, s.Derivative):
        cnt = dict(at.variable_count)
        return f'{at.expr.func}_' + DERNAME[(int(cnt.get(v, 0)), int(cnt.get(d, 0)))], str(at.expr.func)
    return f'{at.func}_base', str(at.func)

def leibniz_terms(name, iv, idd):
    ex = s.expand(s.diff(NORM[name], v, iv, d, idd))
    terms = []
    for term in s.Add.make_args(ex):
        factors = []; coef = s.Integer(1)
        for fac in s.Mul.make_args(term):
            base, ex_ = fac.as_base_exp()
            if isinstance(base, s.Derivative) or (isinstance(base, s.Function) and str(base.func) in R):
                factors += [base] * int(ex_)
            else:
                coef *= fac
        coef = coef.subs({v: 1, d: 0})
        if coef != 0:
            terms.append((coef, factors))
    return terms

def windows(factors, m, pmin):
    """for a product, return {raw_atom: {p: set(k)}} of coefficients [eps^p l^k] that can
    contribute to [eps^0 l^m] of the product (other factors: p in [pmin,pmax], any k>=0)"""
    info = [(raw_atom_name(f)) for f in factors]
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

def merge(dst, src):
    for atom, w in src.items():
        dd = dst.setdefault(atom, {})
        for p, ks in w.items():
            dd.setdefault(p, set()).update(ks)

norm_info = {}
req_by_input = {key: {} for key in ('safe', 'tight')}
total = {'safe': {}, 'tight': {}}
for sym in sorted(norm_atoms_all, key=str):
    name, m, iv, idd = parse_norm_atom(sym)
    terms = leibniz_terms(NORMNAME[name], iv, idd)
    w_s, w_t = {}, {}
    for coef, facs in terms:
        merge(w_s, windows(facs, m, pmin_safe))
        merge(w_t, windows(facs, m, pmin_tight))
    norm_info[str(sym)] = {
        'normalized_response': name, 'log_order_m': m, 'd_v_order': iv, 'd_delta_order': idd,
        'meaning': f'[eps^0 l^{m}] d_v^{iv} d_delta^{idd} {name} at (v,delta)=(1,0)',
        'leibniz_expansion': ' + '.join(f'({s.sstr(c)})*' + '*'.join(raw_atom_name(f)[0] for f in fs)
                                        for c, fs in terms),
        'raw_windows_safe': {a: {str(p): sorted(k) for p, k in sorted(w.items())} for a, w in sorted(w_s.items())},
        'raw_windows_tight': {a: {str(p): sorted(k) for p, k in sorted(w.items())} for a, w in sorted(w_t.items())},
    }
for name in defs:
    for key in ('safe', 'tight'):
        acc = {}
        for at in defs[name]['normalized_atoms']:
            w = norm_info[at]['raw_windows_' + key]
            merge(acc, {a: {int(p): set(k) for p, k in ww.items()} for a, ww in w.items()})
        req_by_input[key][name] = acc
        merge(total[key], acc)

def fmt(acc):
    out = {}
    for a, w in sorted(acc.items(), key=lambda x: (nkinks(x[0].split('_')[0]), x[0])):
        out[a] = {'kinks': nkinks(a.split('_')[0]), 'type': kind(a.split('_')[0]),
                  'endpoint_source': a.startswith('E'), 'derivative': a.split('_', 1)[1],
                  'eps_powers': sorted(w), 'log_orders_by_power': {str(p): sorted(w[p]) for p in sorted(w)}}
    return out

for name in defs:
    defs[name]['raw_requirements_safe'] = fmt(req_by_input['safe'][name])
    defs[name]['raw_requirements_tight'] = fmt(req_by_input['tight'][name])
    defs[name]['max_kinks'] = max(v_['kinks'] for v_ in defs[name]['raw_requirements_safe'].values())

json.dump(defs, open(OUT / 'input_definitions.json', 'w'), indent=1)
json.dump(norm_info, open(OUT / 'normalized_atoms.json', 'w'), indent=1)
json.dump({'safe_bounds': 'pmin=-floor(n/2) for every raw moment except Q2 (0); Z2 support {-1,0}, Q2 support {0,1}',
           'tight_bounds': 'pmin: A_{2m+1},Z_{2m},EA_{2m+1}: -m; Q_{2m},EZ_{2m}: -(m-1); EQ2: 0, EQ_{2m>=4}: -(m-1); same Z2/Q2 supports',
           'log_orders': 'only l^0 and l^1 of any raw coefficient can reach [eps^0 l^0], [eps^0 l^1] of a product; a raw moment entering linearly needs only l^m',
           'total_safe': fmt(total['safe']), 'total_tight': fmt(total['tight'])},
          open(OUT / 'raw_requirements.json', 'w'), indent=1)
print('normalized atoms', len(norm_info), 'raw atoms safe', len(total['safe']), 'tight', len(total['tight']))
print('done', time.time() - t0)
