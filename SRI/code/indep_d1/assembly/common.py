#!/usr/bin/env python3
"""Shared helpers of the assembly phase (assembly/README.md).

Everything here works on the project's own data: the engine's production results, the framework module
(`framework/lri_framework.py`), and the archive-free spec targets (`spec/out/validation_targets.json`).
No archive file is read by this module.
"""
import json
import math
import os
import re
import sys

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
FW_DIR = os.path.join(ROOT, 'framework')
ENG_DIR = os.path.join(ROOT, 'engine')
SPEC_DIR = os.path.join(ROOT, 'spec')
DIRECT_DIR = os.path.join(ROOT, 'direct')
OUT = os.path.join(HERE, 'out')
sys.path.insert(0, FW_DIR)
import lri_framework as L  # noqa: E402

PROD = os.path.join(ENG_DIR, 'runs', 'prod_6digit')
TOPUP = os.path.join(ENG_DIR, 'runs', 'prod_6digit_topup1')
FINAL_CANON = os.path.join(PROD, 'framework_input_final.json')     # tier 1 + top-up, 116 needed scalars
TIER1_CANON = os.path.join(PROD, 'framework_input.json')           # tier 1 alone
FINAL_RESULTS = os.path.join(PROD, 'results_final.json')           # all 439 coefficients (all log powers)
POLES = os.path.join(ENG_DIR, 'runs', 'poles1')                    # assembly-phase negative-power run
POLES_RESULTS = os.path.join(POLES, 'results.json')
KPLUS1 = os.path.join(ENG_DIR, 'runs', 'kplus1')                   # assembly-phase eps^1 run (direct test only)
KPLUS1_RESULTS = os.path.join(KPLUS1, 'results.json')
VALIDATION_FILES = [os.path.join(ENG_DIR, 'results', 'validation_d_inputs.json'),
                    os.path.join(ENG_DIR, 'results', 'validation_c.json')]

BETA_D4 = ['a', 'p', 'A', 'E', 'c', 'f', 'b', 'G', 'q', 'k', 'V', 'R', 'J', 'L', 'M', 'N',
           'alpha', 'beta', 'gamma', 'Phi', 'Psi', 'Omega', 'Q', 'P', 'K']
INVARIANTS = ['D2', 'T2', 'D3', 'T3', 'D4']
CS = ['C3', 'C4', 'C5', 'C6', 'C7']
OUTPUTS = BETA_D4 + INVARIANTS + CS


def nstr(x, d=20):
    return None if x is None else mp.nstr(x, d)


def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------------------------------
# closed-form strings of the archive-free spec targets
# ----------------------------------------------------------------------------------------------------
def constants(dps=60):
    with mp.workdps(dps + 10):
        c = {'z2': mp.zeta(2), 'z3': mp.zeta(3), 'z4': mp.zeta(4), 'z5': mp.zeta(5), 'z6': mp.zeta(6),
             'L2': mp.log(2), 'L3': mp.log(3), 'Li2h': mp.polylog(2, mp.mpf(-1) / 2),
             'Li4h': mp.polylog(4, mp.mpf(1) / 2), 'Li4': mp.polylog(4, mp.mpf(1) / 2)}
    return c


def eval_closed(expr, dps=50):
    """evaluate a closed-form string of spec/out/validation_targets.json (symbols z2..z6, L2, L3, Li2h, Li4h)"""
    cst = constants(dps)
    syms = {k: sp.Symbol(k) for k in cst}
    e = sp.sympify(expr, locals=syms)
    free = {str(s) for s in e.free_symbols}
    unknown = free - set(cst)
    if unknown:
        raise ValueError(f'unknown symbols {unknown} in {expr!r}')
    with mp.workdps(dps + 10):
        f = sp.lambdify([syms[k] for k in cst], e, 'mpmath')
        return +f(*[cst[k] for k in cst])


def spec_targets():
    return json.load(open(os.path.join(SPEC_DIR, 'out', 'validation_targets.json')))['targets']


# ----------------------------------------------------------------------------------------------------
# extended input: all engine coefficients, structural log zeros, optional validation-run slices
# ----------------------------------------------------------------------------------------------------
def extended_input(kmax, with_validation=False, with_poles=False, results=FINAL_RESULTS):
    """canonical input with every coefficient of the production results (not only the 116 needed),
    plus exact zeros for log powers above the engine's computed range at each computed (moment, eps power)
    (the engine computes each Laurent expansion from the lowest order that can occur, so higher log powers
    are structural zeros; collect writes the same zeros when they are needed), up to l^kmax.
    Priority per coefficient [eps^p l^k]: production, then
      with_poles       the assembly-phase engine run engine/runs/poles1 (negative eps powers, all logs, R = 6,
                       fresh seeds; its replicate blocks are renamed 'poles1:<block>' so that they never pair
                       with a production block of the same name),
      with_validation  the engine's earlier validation runs (engine/results/validation_d_inputs.json,
                       validation_c.json; phase-1 format [mean, err], no replicates; err floored at 1e-15
                       relative).
    Returns (canonical dict, info)."""
    d = L.load_inputs(results)
    sc = d['scalars']
    # the 116 needed scalars exactly as in the canonical deliverable (same replicates; its means are the
    # producer's string means, which differ from the float means of results_final.json at double rounding)
    if results == FINAL_RESULTS:
        for nm, ent in json.load(open(FINAL_CANON))['scalars'].items():
            sc[L.canonical_raw_name(nm)] = ent
    info = {'production_coefficients': len(sc), 'log_zeros': [], 'poles1_coefficients': [],
            'validation_coefficients': [], 'validation_slices': {}}
    if with_poles:
        pd = L.load_inputs(POLES_RESULTS)
        for nm, ent in pd['scalars'].items():
            cn = L.canonical_raw_name(nm)
            if cn in sc:
                continue
            if isinstance(ent, dict) and 'block' in ent:
                ent = dict(ent)
                ent['block'] = 'poles1:' + str(ent['block'])
            sc[cn] = ent
            info['poles1_coefficients'].append(cn)
    if with_validation:
        for vf in VALIDATION_FILES:
            vd = json.load(open(vf))
            vr = vd.get('results', vd)
            for grp, ser in vr.items():
                try:
                    pref = L.group_to_prefix(grp)
                except ValueError:
                    continue
                M, n, i, j, e, _, _ = L.parse_raw_name(f'{pref}[eps^0 l^0]')
                if (M == 'Z' or M == 'Q') and n == 2 or (M == 'A' and n == 1):
                    continue            # exact internal sector of the framework
                for kj, ve in ser.items():
                    if ',' not in kj:
                        continue
                    p, k = (int(x) for x in kj.split(','))
                    cn = L.raw_name(M, n, i, j, e, p, k)
                    if cn in sc:
                        continue                     # production / poles1 / an earlier validation file has it
                    v, err = (ve if isinstance(ve, (list, tuple)) else (ve, 0.0))
                    err = max(float(err), 1e-15 * max(1.0, abs(float(v))))
                    sc[cn] = {'value': repr(float(v)), 'sigma': repr(err)}
                    info['validation_coefficients'].append(cn)
                    info['validation_slices'][f'{pref}[eps^{p}]'] = os.path.basename(vf)
    have = {}
    for nm in sc:
        M, n, i, j, e, p, k = L.parse_raw_name(nm)
        key = (M, n, i, j, e, p)
        have[key] = max(have.get(key, -1), k)
    for (M, n, i, j, e, p), km in have.items():
        for k in range(km + 1, kmax + 1):
            nm = L.raw_name(M, n, i, j, e, p, k)
            sc[nm] = {'value': '0', 'sigma': '0', 'exact': True}
            info['log_zeros'].append(nm)
    info['n_scalars'] = len(sc)
    return d, info


class NormAssembler:
    """normalized Laurent-log jets C_n, K_n (all eps powers, logs to kmax) with gradients, and the
    per-replicate re-assemblies (same pairing of replicates as Framework.from_replicates)."""

    def __init__(self, data, kmax, dps=30, pcap=6, jobs=None):
        self.fw = L.Framework('D4', dps=dps, kmax=kmax, pcap=pcap)
        self.dps = dps
        self.jobs = jobs            # per-sector replicate data (pooled_errors) for the sector-pooled error
        with mp.workdps(dps):
            self.inp, _ = self.fw._parse(data, 'raw', None, None, None)
            self.em = self.inp.errmodel
            fixed = self.inp.fixed_names
            self.extra = self.em.restricted(keep_sig=self.em.sig, keep_blocks=fixed, keep_reps=None)
            self.R = self.inp.n_rep
            self.central = self._assemble(self.inp.values, True)
            self.reps = []
            for r in range(self.R or 0):
                vals = dict(self.inp.values)
                for nm, rl in self.inp.reps.items():
                    vals[nm] = rl[r]
                self.reps.append(self._assemble(vals, False))

    def _assemble(self, values, track):
        vals = {nm: L.Val.input(nm, x, track) for nm, x in values.items()}
        jets = self.fw._raw_jets(vals, True, compare=False, fill_missing=True)
        C, K = self.fw._normalize(jets)
        out = {'C': C, 'K': K, 'raw': vals}
        c, kk = self.fw._extract(C, K)
        out['c'], out['kk'] = c, kk
        out['bh'] = self.fw._bh_from_normalized(c, kk)
        return out

    def stats(self, fn):
        """fn(assembly) -> Val.  Returns dict(value, sigma_lin, rep_mean, rep_se, sigma_extra, sigma_rep,
        sigma_pool_stat, sigma_pool_tot, sigma (= the largest of sigma_lin, sigma_rep, sigma_pool_tot), l1) or
        {'missing': [...]}"""
        with mp.workdps(self.dps):
            x = fn(self.central)
            if x.is_missing:
                return {'missing': sorted(x.miss)[:6]}
            res = {'value': x.v, 'sigma_lin': mp.sqrt(self.em.variance(x.g)),
                   'l1': sum((abs(g * self.inp.values[nm]) for nm, g in x.g.items() if nm in self.inp.values),
                             mp.mpf(0))}
            if self.R:
                xs = [fn(a).v for a in self.reps]
                m = sum(xs) / self.R
                se = mp.sqrt(sum((v - m) ** 2 for v in xs) / (self.R - 1)) / mp.sqrt(self.R)
                sx = mp.sqrt(self.extra.variance(x.g))
                res.update(rep_mean=m, rep_se=se, sigma_extra=sx, sigma_rep=mp.sqrt(se ** 2 + sx ** 2))
            if self.jobs:
                import pooled_errors as PE
                _, pst, _ = PE.pooled_projection(self.jobs, PE.input_gradient(x, self.inp))
                res['sigma_pool_stat'] = mp.mpf(pst)
                res['sigma_pool_tot'] = mp.sqrt(mp.mpf(pst) ** 2 + res.get('sigma_extra', mp.mpf(0)) ** 2)
            res['sigma'] = quote_sigma(res)
            return res


def coef(series_getter, p, k):
    """helper: a function of an assembly returning the coefficient [eps^p l^k] of a normalized jet entry"""
    def fn(a):
        s = series_getter(a)
        return s.coef(p, k)
    return fn


def raw_coef(name):
    def fn(a):
        cn = L.canonical_raw_name(name)
        v = a['raw'].get(cn)
        return v if v is not None else L.Val.missing({cn})
    return fn


def beta_of(a, name):
    """beta input `name` from an assembly's auxiliary jets (framework dictionary DICT)"""
    w, i, j, fac = L.DICT[name]
    return fac * a['bh'][w][(i, j)]


def quote_sigma(st):
    """conservative error: the largest available estimator"""
    c = [st.get(k) for k in ('sigma_lin', 'sigma_rep', 'sigma_pool_tot') if st.get(k) is not None]
    return max(c) if c else None
