#!/usr/bin/env python3
"""SEALED COMPARISON STEP -- COMPARISON-ONLY extraction of archived numbers (read-only access to
the compendium).  Production code never imports this module or reads its outputs.

What this does
  1. Collects the archived numerical values of all 25 beta inputs (>=60 digits) and of
     C6, T3, D4, C7, Omega-free pieces, B_old (C6) and B_old^{D4}.
  2. Evaluates archived per-moment cutoff series files (series/*.expr = coefficient of
     eps^p as a polynomial in l=log eps with regularized periods R_w) NUMERICALLY by
     substituting archived period values (final_periods*.json etc.).  The evaluator is
     written here from scratch (string -> mpmath); the archive's evaluation engine is
     NOT imported or called.  Numbers obtained this way are archive data, to be used
     only as comparison targets for our own independent integrations.
  3. Spec self-test: (a) re-assembles every normalized-response atom from the archived
     RAW per-moment coefficients using ONLY the eps-power/log-order windows derived by
     derive_requirements.py, and compares with the archived normalized series;
     (b) evaluates the 25 input definitions (derive_requirements.py) on the archived
     normalized atoms and compares with the archived input values.  Agreement proves
     that our definitions + minimal windows reproduce the archive's.

Nothing is written inside the compendium.  Reads the archive-free definitions in ../../out/;
writes ../archive_inputs.json, ../archive_raw_coefficients.json, ../archive_normalized_atoms.json,
../spec_selftest.json (all inside spec/comparison/).
"""
import json, re, sys, time
from pathlib import Path
import mpmath as mp

COMP = Path('<PROJECT>/LRI_SRI_research_compendium')
SPEC = Path(__file__).resolve().parent.parent.parent
DEFS = SPEC / 'out'                 # archive-free definitions (read)
OUT = SPEC / 'comparison'           # sealed archive data (write)
mp.mp.dps = 110

LAYOUT = {f['path']: COMP / f['stored'] for f in json.load(open(COMP / 'reproduction/layout.json'))['files']}

def stored(orig):
    return LAYOUT[orig]

# ---------------------------------------------------------------------------- periods
PERIOD_TABLES = [  # (original path, label)   later entries do not override earlier ones
    'C7_completion/engine/final_periods_C7_second.json',
    'LRI_1d_complete/stages/C6_integrals/reproducibility/final_periods_run2.json',
    'F2_F3_delivery/F2/verification/run110dfs.periods.json',
    'F1c_completion/data/periods_full100.json',
    'F1b_completion/data/periods_check100.json',
    'C8_full_numerical_completion/data/F3_final_100.periods.json',
    'C8_full_numerical_completion/data/F4_data_100.periods.json',
    'C8_P6_exact_sources/P6_full/P6_eval100.periods.json',
    'F2_F3_delivery/F3/verification/F3_100.periods.json',
    'C8_P6_exact_sources/P6_full/control/divergences90.periods.json',
    'F3_six_kink_completion/data/XE_second90.periods.json',
    'F3_six_kink_completion/data/Xvv_second90.periods.json',
    'C7_completion/engine/final_periods_rebuilt_eight.json',
    'C7_completion/engine/final_periods_C7_first.json',
    'C7_completion/engine/final_periods_Q4dd_log_residuals_corrected.json',
    'P8_final_run/F3_six_kink_completion/P8_terminal_fibration/positive_divergence/eval90.periods.json',
    'P8_final_run/F3_six_kink_completion/F4_data/endpoint70.periods.json',
    'P8_final_run/F3_six_kink_completion/F4_data/early70.periods.json',
    'C7_completion/engine/final_periods_Knew_fresh.json',
    'C7_completion/engine/final_periods_new_three_kink.json',
]
PERIODS = {}      # key 'a,b,c' -> (string value, source)
CONFLICTS = []
def load_periods():
    for orig in PERIOD_TABLES:
        if orig not in LAYOUT:
            continue
        d = json.load(open(LAYOUT[orig]))
        for k, val in d.items():
            if k in PERIODS:
                a = mp.mpf(PERIODS[k][0]); b = mp.mpf(str(val))
                if abs(a - b) > mp.mpf(10)**(-55) * (1 + abs(a)):
                    CONFLICTS.append((k, PERIODS[k][1], orig))
            else:
                PERIODS[k] = (str(val), orig)

class Missing(Exception):
    pass

def rkey(name):
    return ','.join(t[1:] if t.startswith('m') else t for t in name.split('_')[1:])

class NS(dict):
    """locals mapping for eval: resolves R_ symbols lazily"""
    def __missing__(self, name):
        if name.startswith('R_'):
            k = rkey(name)
            if k not in PERIODS:
                raise Missing(k)
            val = mp.mpf(PERIODS[k][0])
            self[name] = val
            return val
        raise KeyError(name)

class EllPow:
    """c * ell**j"""
    __slots__ = ('c', 'j')
    def __init__(self, c, j):
        self.c, self.j = c, j
    def __mul__(self, o):
        if isinstance(o, EllPow):
            return EllPow(self.c * o.c, self.j + o.j)
        return EllPow(self.c * o, self.j)
    __rmul__ = __mul__
    def __truediv__(self, o):
        return EllPow(self.c / o, self.j)
    def __neg__(self):
        return EllPow(-self.c, self.j)
    def __pos__(self):
        return self
    def __pow__(self, n):
        n = int(n)
        return EllPow(self.c**n, self.j * n)

BASE_NS = {'mpf': mp.mpf, 'log': mp.log, 'pi': mp.pi,
           'polylog': lambda s_, z: mp.polylog(int(s_), z), 'sqrt': mp.sqrt,
           'zeta': mp.zeta, 'Rational': lambda a, b: mp.mpf(a) / b}
for k_ in range(2, 10):
    BASE_NS[f'Z{k_}'] = mp.zeta(k_)

INT_RE = re.compile(r'(?<![\w.])(\d+)(?![\w.])')

def split_terms(txt):
    terms, depth, start = [], 0, 0
    i = 0
    n = len(txt)
    while i < n:
        ch = txt[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif depth == 0 and ch in '+-' and i > 0 and txt[i - 1] == ' ' and i + 1 < n and txt[i + 1] == ' ':
            terms.append(txt[start:i].strip())
            start = i
        i += 1
    terms.append(txt[start:].strip())
    return [t.replace('+ ', '', 1) if t.startswith('+ ') else t.replace('- ', '-', 1) for t in terms if t]

def eval_poly(txt, kmax=12):
    """evaluate an expanded sympy string, polynomial in ell; returns list of
    (value or None) for ell^0..ell^kmax (None = needs a period not archived)"""
    txt = txt.strip()
    coeffs = [mp.mpf(0)] * (kmax + 1)
    bad = [set() for _ in range(kmax + 1)]
    ns = NS()
    for term in split_terms(txt):
        code = INT_RE.sub(r'mpf(\1)', term)
        ns2 = ns
        try:
            val = eval(code, dict(BASE_NS, ell=EllPow(mp.mpf(1), 1)), ns2)
        except Missing as e:
            # find the ell power of this term without the period value
            m = re.search(r'ell\*\*(\d+)', term)
            j = int(m.group(1)) if m else (1 if re.search(r'(?<![\w])ell(?![\w*])', term) or re.search(r'(?<![\w])ell\*(?!\*)', term) else 0)
            if j <= kmax:
                bad[j].add(str(e))
            continue
        if isinstance(val, EllPow):
            if val.j <= kmax:
                coeffs[val.j] += val.c
        else:
            coeffs[0] += val
    return [None if bad[k] else coeffs[k] for k in range(kmax + 1)], [sorted(b) for b in bad]

def nstr(x, n=60):
    return None if x is None else mp.nstr(x, n)

# ---------------------------------------------------------------------------- archived inputs
def archived_inputs():
    c6 = json.load(open(stored('LRI_1d_complete/stages/C6_integrals/reproducibility/final_evaluation_run2.json')))['coefficients']
    c6r1 = json.load(open(stored('LRI_1d_complete/stages/C6_integrals/reproducibility/final_evaluation_run1.json')))['coefficients']
    c7 = json.load(open(stored('C7_completion/engine/final_evaluation_C7_second.json')))['coefficients']
    c7f = json.load(open(stored('C7_completion/engine/final_evaluation_C7_first.json')))['coefficients']
    reb = json.load(open(stored('C7_completion/engine/final_evaluation_rebuilt_eight.json')))['coefficients']
    src6 = 'data/archived/LRI_1d_complete/stages/C6_integrals/reproducibility/final_evaluation_run2.json (dps 100; run1 dps 80 agrees)'
    src7 = 'data/archived/C7_completion/engine/final_evaluation_C7_second.json (dps 115; C7_first dps 95 agrees)'
    out = {}
    for nm in ['a', 'p', 'A', 'E', 'c', 'f', 'b', 'G', 'q', 'k']:
        out[nm] = {'value': c6[nm + '_check'], 'source': src6, 'run1_value': c6r1[nm + '_check']}
    for nm in ['V', 'R', 'J', 'L', 'M', 'N']:
        out[nm] = {'value': c6[nm], 'source': src6, 'run1_value': c6r1[nm]}
    for nm, key in [('alpha', 'alpha'), ('beta', 'beta'), ('gamma', 'gamma'), ('Phi', 'Phi'), ('Psi', 'Psi'),
                    ('Omega', 'Omega'), ('Q', 'Qnew'), ('P', 'Pnew'), ('K', 'Knew')]:
        out[nm] = {'value': c7[key], 'source': src7, 'first_run_value': c7f[key]}
    extra = {
        'C6': {'value': c6['C6'], 'source': src6},
        'T3': {'value': c6['T3'], 'source': src6},
        'B_old_C6': {'value': c6['B_old'], 'source': src6},
        'C7': {'value': c7['C7'], 'source': src7},
        'D4': {'value': c7['D4_value'], 'source': src7},
        'C7_without_Omega': {'value': c7['C7_without_Omega'], 'source': src7},
        'D4_without_Omega': {'value': c7['D4_without_Omega'], 'source': src7},
        'B_old_D4': {'value': reb['B4_old'], 'source': 'data/archived/C7_completion/engine/final_evaluation_rebuilt_eight.json (dps 85)'},
    }
    return out, extra

# ---------------------------------------------------------------------------- series files
STAGES = {'C7': 'C7_completion/engine/series/', 'C6': 'LRI_1d_complete/stages/C6_integrals/reproducibility/series/'}

def series_path(stem):
    for st in ('C7', 'C6'):
        p = STAGES[st] + stem + '.expr'
        if p in LAYOUT:
            return p
    return None

def main():
    t0 = time.time()
    load_periods()
    print('periods loaded', len(PERIODS), 'conflicts', len(CONFLICTS), round(time.time() - t0, 1), flush=True)
    req = json.load(open(DEFS / 'raw_requirements.json'))
    defs = json.load(open(DEFS / 'input_definitions.json'))
    norm = json.load(open(DEFS / 'normalized_atoms.json'))
    inputs, extra = archived_inputs()

    # --- raw per-moment coefficients needed (safe windows) + all archived p files of those atoms
    rawvals = {}
    for atom, info in req['total_safe'].items():
        rawvals[atom] = {}
        allp = sorted(set(info['eps_powers']) | set(range(-4, 5)))
        for p in allp:
            sp = series_path(f'{atom}_p{p}')
            if sp is None:
                continue
            txt = open(LAYOUT[sp]).read()
            vals, bad = eval_poly(txt)
            deg = max([k for k, v_ in enumerate(vals) if v_ is None or v_ != 0] or [0])
            rawvals[atom][str(p)] = {'archive_file': str(LAYOUT[sp].relative_to(COMP)), 'original_path': sp,
                                     'needed': p in info['eps_powers'],
                                     'needed_log_orders': info['log_orders_by_power'].get(str(p)),
                                     'coefficients_by_log_power': {str(k): nstr(vals[k]) for k in range(deg + 1)},
                                     'missing_periods_by_log_power': {str(k): bad[k][:5] for k in range(deg + 1) if bad[k]}}
        print('raw', atom, 'powers', sorted(rawvals[atom]), round(time.time() - t0, 1), flush=True)

    # Z2, Q2 exact supports: series files outside the support are absent in the archive
    # --- normalized atoms from archive norm files
    NMAP = {'K2': 'Q2', 'EK2': 'EQ2'}
    normvals = {}
    for at, info in norm.items():
        name = info['normalized_response']; iv = info['d_v_order']; idd = info['d_delta_order']; m = info['log_order_m']
        stem = f"norm_{NMAP.get(name, name)}_{iv}_{idd}"
        sp = series_path(stem)
        rec = {'archive_file': None}
        if sp is not None:
            vals, bad = eval_poly(open(LAYOUT[sp]).read(), kmax=12)
            rec = {'archive_file': str(LAYOUT[sp].relative_to(COMP)), 'value': nstr(vals[m]),
                   'missing': bad[m][:5]}
        normvals[at] = rec
    print('normalized atoms read', round(time.time() - t0, 1), flush=True)

    # --- (a) recompute normalized atoms from raw windows (convolution) and compare
    def rawcoef(atom, p, k):
        base = atom.split('_')[0]
        if base == 'Z2' and p not in (-1, 0):
            return mp.mpf(0)
        if base == 'Q2' and p not in (0, 1):
            return mp.mpf(0)
        rec = rawvals.get(atom, {}).get(str(p))
        if rec is None:
            raise KeyError((atom, p))
        v_ = rec['coefficients_by_log_power'].get(str(k), '0')
        if v_ is None:
            raise Missing(f'{atom} p{p} l{k}')
        return mp.mpf(v_)

    def conv(factors, m, key):
        # [eps^0 l^m] of product of raw atoms, using only the derived windows
        windows = [[(int(p), k) for p, ks in norm_windows[f].items() for k in ks] for f in factors]
        total = mp.mpf(0)
        def rec(i, psum, ksum, acc):
            nonlocal total
            last = (i == len(factors) - 1)
            for p, k in windows[i]:
                if ksum + k > m:
                    continue
                if last and (psum + p != 0 or ksum + k != m):
                    continue
                c = rawcoef(factors[i], p, k)
                if c == 0:
                    continue
                if last:
                    total += acc * c
                else:
                    rec(i + 1, psum + p, ksum + k, acc * c)
        rec(0, 0, 0, mp.mpf(1))
        return total

    selftest_norm = {}
    for at, info in norm.items():
        norm_windows = info['raw_windows_tight']
        m = info['log_order_m']
        val = mp.mpf(0)
        try:
            for term in info['leibniz_expansion'].split(' + '):
                coef_s, prod = term.split(')*', 1)
                coef = mp.mpf(eval(INT_RE.sub(r'mpf(\1)', coef_s[1:]), {'mpf': mp.mpf}))
                val += coef * conv(prod.split('*'), m, at)
            got = val
        except (Missing, KeyError) as e:
            got = None
            print('cannot recompute', at, e)
        ref = normvals[at].get('value')
        diff = None if (got is None or ref is None) else mp.nstr(got - mp.mpf(ref), 5)
        selftest_norm[at] = {'from_raw_windows': nstr(got), 'archive_normalized': ref, 'difference': diff}
    print('self-test (a) done', round(time.time() - t0, 1), flush=True)

    # --- (b) evaluate input definitions on archive normalized atoms
    selftest_inputs = {}
    for nm, info in defs.items():
        expr = info['expansion_in_normalized_atoms']
        names = {}
        def rep(mo):
            key = mo.group(0)
            names.setdefault(key, f'X{len(names)}')
            return names[key]
        code = re.sub(r'[A-Z]+\d_\d\[v\dd\d\]', rep, expr)
        code = INT_RE.sub(r'mpf(\1)', code)
        env = {'mpf': mp.mpf}
        ok = True
        for key, var in names.items():
            v_ = normvals[key].get('value')
            if v_ is None:
                ok = False
                break
            env[var] = mp.mpf(v_)
        got = eval(code, env) if ok else None
        ref = mp.mpf(inputs[nm]['value'])
        selftest_inputs[nm] = {'from_definition_on_archive_normalized_atoms': nstr(got),
                               'archive_value': inputs[nm]['value'][:70],
                               'difference': None if got is None else mp.nstr(got - ref, 5)}
        print('input', nm, selftest_inputs[nm]['difference'], flush=True)

    json.dump({'inputs': inputs, 'derived': extra}, open(OUT / 'archive_inputs.json', 'w'), indent=1)
    json.dump({'note': 'ARCHIVE DATA, COMPARISON ONLY. [eps^p l^k] coefficients of archived raw moments, '
                       'evaluated numerically with archived period tables (60 digits printed).',
               'period_conflicts': CONFLICTS[:20], 'raw': rawvals},
              open(OUT / 'archive_raw_coefficients.json', 'w'), indent=1)
    json.dump({'note': 'ARCHIVE DATA, COMPARISON ONLY. normalized-response atoms', 'atoms': normvals},
              open(OUT / 'archive_normalized_atoms.json', 'w'), indent=1)
    json.dump({'normalized_from_raw_windows': selftest_norm, 'inputs_from_definitions': selftest_inputs},
              open(OUT / 'spec_selftest.json', 'w'), indent=1)
    print('done', round(time.time() - t0, 1))

if __name__ == '__main__':
    main()
