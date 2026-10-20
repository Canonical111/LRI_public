#!/usr/bin/env python3
"""Validation step (c): compare engine results (results/validation_c.json) with the archive's exact
per-moment series polynomials (COMPARISON ONLY; nothing archived is used as an input of the engine).

The archive expressions are written in regularized hyperlogarithm words R_<letters> (letter m<k> = -k);
for the numerical comparison only, their values are read from the archived period table
final_periods_run1.json (key 'k1,k2,...').  Z2 = zeta(2).
"""
import json, os, re, sys
import mpmath as mp
import sympy as sp

mp.mp.dps = 30
COMP = '<PROJECT>/LRI_SRI_research_compendium'
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(COMP, 'reproduction/layout.json')))['files']
stored = {r['path'].split('reproducibility/')[1]: r['stored'] for r in rows
          if 'c6_integrals/reproducibility/' in r['path'].lower()}
periods = json.load(open(os.path.join(COMP, stored['final_periods_run1.json'])))
# words missing from the C6-stage table: merged archived period tables (numbers only, comparison only)
import glob
_rows_all = [r['stored'] for r in rows] if False else None
_layout = json.load(open(os.path.join(COMP, 'reproduction/layout.json')))['files']
for r in _layout:
    pth = r['path']
    if ('final_periods' in pth or pth.endswith('.periods.json') or 'periods_full' in pth or 'periods_known' in pth) and pth.endswith('.json'):
        try:
            dd_ = json.load(open(os.path.join(COMP, r['stored'])))
        except Exception:
            continue
        if isinstance(dd_, dict) and 'periods' in dd_:
            dd_ = dd_['periods']
        if isinstance(dd_, dict):
            for k_, v_ in dd_.items():
                if isinstance(v_, (str, float, int)) and re.fullmatch(r'[0-9,]+', k_):
                    periods.setdefault(k_, str(v_))
mine = json.load(open(os.path.join(HERE, '..', 'results', 'validation_c.json')))
ell = sp.Symbol('ell')


def rword(name):
    toks = name[2:].split('_')
    key = ','.join(t[1:] if t.startswith('m') else t for t in toks)
    if key not in periods:
        raise KeyError(key)
    return sp.Float(periods[key], 40)


def archive_poly(name):
    p = stored.get('series/' + name + '.expr')
    if p is None:
        return None
    p = os.path.join(COMP, p)
    if not os.path.exists(p):
        return None
    txt = open(p).read()
    syms = set(re.findall(r'R_[A-Za-z0-9_]+', txt))
    loc = {s: sp.Symbol(s) for s in syms}
    loc.update({'ell': ell, 'Z2': sp.Symbol('Z2'), 'polylog': sp.polylog, 'log': sp.log, 'pi': sp.pi})
    ex = sp.sympify(txt, locals=loc)
    sub = {sp.Symbol(s): rword(s) for s in syms}
    sub[sp.Symbol('Z2')] = sp.zeta(2)
    ex = sp.expand(ex.subs(sub))
    P = sp.Poly(ex, ell)
    return {int(m[0]): complex(sp.N(c, 25)).real for m, c in P.terms()}


worst = 0
lines = []
for name, data in mine.items():
    ks = sorted({int(k.split(',')[0]) for k in data})
    for k in ks:
        arch = archive_poly(f'{name}_p{-k}' if False else f'{name}_p{k}')
        if arch is None:
            lines.append(f'{name} eps^{k}: no archive file')
            continue
        for j in sorted(set(arch) | {int(kk.split(",")[1]) for kk in data if int(kk.split(",")[0]) == k}):
            v, e = data.get(f'{k},{j}', [0.0, 0.0])
            a = arch.get(j, 0.0)
            diff = v - a
            sig = abs(diff) / max(e, 1e-300) if e > 0 else (0 if abs(diff) < 1e-12 * max(1, abs(a)) else float('inf'))
            rel = abs(diff) / max(abs(a), 1e-30)
            flag = 'OK' if (abs(diff) <= 5 * e + 1e-11 * max(1, abs(a))) else 'MISMATCH'
            if flag != 'OK':
                worst = max(worst, rel)
            lines.append(f'{name:8s} eps^{k:<2d} log^{j}: engine {v: .15e} +- {e:.1e}  archive {a: .15e}  diff {diff: .2e}  {flag}')
print('\n'.join(lines))
print('worst relative mismatch:', worst)
