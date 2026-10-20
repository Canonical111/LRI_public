#!/usr/bin/env python3
"""Archive-free validation of the engine's C8 extension (phase 3).

Data: the engine's own runs only:
  production  runs/prod_6digit/results_final.json (+ framework_input_final.json), all log powers
  poles1, kplus1 (assembly-phase check runs), the phase-1 validation files (through ../assembly/common.py)
  C8 runs     runs/c8val (and any further run directories given with --run; strided runs are skipped)
Normalized jets C_n, K_n are built with the framework module at order C8 (total (v, delta, E) degree 5, logs to
l^KMAX), replicate by replicate (../assembly/common.py NormAssembler, same three error estimators).

Checks (targets from ../spec/out/C8, all archive-free):
  1. raw targets: A3_ddd all log powers against the spec's independent three-kink values (1e-25), the note's
     leading logarithms of d_delta A7 ([eps^0 l^8] = -2362/315, [l^9] = 0);
  2. pole cancellation: every [eps^p l^k], p < 0, of the 74 normalized jets of poles_C8.json that the data allow;
  3. structural zeros: the 12 below-tight-bound scalars (raw_requirements_C8.json) that the engine computes;
  4. normalized higher logs: validation_targets_C8.json (C3 jets with d^3, K4 jets with 3 derivatives: exact or
     closed forms in the beta inputs, incl. the new L3, M21, M12 evaluated from the same data);
  5. RG (Callan-Symanzik) log predictions of rg_logs_C8.json: second-log and all higher-log formulas of the
     C5, C7, C9, K6, K8 jets (incl. d_delta^2 C5, d_delta C7, C9, d_v^2 K6, d_v d_delta K6, d_v K8) and the
     vanishing of [l^(top+1)].
Output: results/validate_C8.json and results/validate_C8.txt.  Runtime: minutes (local, analysis only).
usage: python3 tests/validate_C8.py [--run runs/c8val] [--kmax 11] [--out results/validate_C8]
"""
import argparse, json, math, os, re, sys, time
from fractions import Fraction
from math import factorial
import mpmath as mp
import sympy as s

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(PROJ, 'assembly'))
import common as CM            # noqa: E402  (project assembly helpers; imports ../framework/lri_framework.py)
L = CM.L
SPEC8 = os.path.join(PROJ, 'spec', 'out', 'C8')
INPUTS = ('a p A E V alpha beta gamma b G R Phi Psi J Omega c f q L M Q k N P K '
          'W S U J9 L3 M21 M12 N2 Ndelta Kv').split()
ZV = {'z2': mp.zeta(2), 'z3': mp.zeta(3), 'z4': mp.zeta(4), 'z5': mp.zeta(5), 'z6': mp.zeta(6), 'z7': mp.zeta(7)}
ATOM = re.compile(r'(E?)([CK])(\d)_(\d+)\[v(\d)d(\d)\]')
LOG = []


def log(*a):
    s_ = ' '.join(str(x) for x in a)
    LOG.append(s_)
    print(s_, flush=True)


class C8Assembler(CM.NormAssembler):
    """NormAssembler at framework order C8 (jets of total degree 5, C1..C9, K2..K8)"""

    def __init__(self, data, kmax, dps=30, pcap=6):
        self.fw = L.Framework('C8', dps=dps, kmax=kmax, pcap=pcap)
        self.dps = dps
        self.jobs = None
        with mp.workdps(dps):
            self.inp, _ = self.fw._parse(data, 'raw', None, None, None)
            self.em = self.inp.errmodel
            self.extra = self.em.restricted(keep_sig=self.em.sig, keep_blocks=self.inp.fixed_names, keep_reps=None)
            self.R = self.inp.n_rep
            self.central = self._assemble(self.inp.values, True)
            self.reps = []
            for r in range(self.R or 0):
                vals = dict(self.inp.values)
                for nm, rl in self.inp.reps.items():
                    vals[nm] = rl[r]
                self.reps.append(self._assemble(vals, False))


def c8_input(kmax, runs):
    """production (+ poles1 + validation) extended input, then the C8 runs (production has priority; every C8-run
    block is renamed '<run>:<block>' so that no two independent runs pair replicates), then exact zeros for the
    log powers above each computed (atom, eps power) range"""
    d, info = CM.extended_input(kmax, with_validation=True, with_poles=True)
    sc = d['scalars']
    for extra in [os.path.join(ROOT, 'runs', 'kplus1')] + runs:
        tag = os.path.basename(os.path.normpath(extra))
        man = json.load(open(os.path.join(extra, 'manifest.json')))
        strided = {m['moment'] for m in man if any('sectorstride' in str(e) for e in (m.get('extra') or []))}
        R = json.load(open(os.path.join(extra, 'results.json')))
        # one entry per (group, coefficient): pilot runs hold the same job at several N (suffix _N<N>); keep the one
        # with the smallest error; sector-sampled entries are partial sums and never used
        res2, rep2, err2 = {}, {}, {}
        for g, co in R['results'].items():
            if g in strided:
                continue
            base = re.sub(r'_N\d+$', '', g)
            for key, (v, e) in co.items():
                if key in res2.get(base, {}) and res2[base][key][1] <= e:
                    continue
                res2.setdefault(base, {})[key] = [v, e]
                err2.setdefault(base, {})[key] = R['errors'][g][key]
                if key in R['replicates'].get(g, {}):
                    rep2.setdefault(base, {})[key] = R['replicates'][g][key]
                else:
                    rep2.get(base, {}).pop(key, None)
        R = {**R, 'results': res2, 'replicates': rep2, 'errors': err2}
        tmp = os.path.join(ROOT, 'results', f'.tmp_{tag}_results.json')
        json.dump(R, open(tmp, 'w'))
        pd = L.load_inputs(tmp)
        os.remove(tmp)
        n_add = 0
        for nm, ent in pd['scalars'].items():
            cn = L.canonical_raw_name(nm)
            if cn in sc:
                continue
            if isinstance(ent, dict) and 'block' in ent:
                ent = dict(ent)
                ent['block'] = f'{tag}:{ent["block"]}'
            sc[cn] = ent
            n_add += 1
        info.setdefault('added', {})[tag] = n_add
    have = {}
    for nm, ent in sc.items():
        M, n, i, j, e, p, k = L.parse_raw_name(nm)
        key = (M, n, i, j, e, p)
        have[key] = max(have.get(key, -1), k)
    nz = 0
    for (M, n, i, j, e, p), km in have.items():
        for k in range(km + 1, kmax + 1):
            nm = L.raw_name(M, n, i, j, e, p, k)
            if nm not in sc:
                sc[nm] = {'value': '0', 'sigma': '0', 'exact': True}
                nz += 1
    info['log_zeros_total'] = nz
    info['n_scalars'] = len(sc)
    return d, info


def atom_val(a, name):
    m = ATOM.fullmatch(name)
    E, X, n, k, i, j = m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
    src = a['c'] if X == 'C' else a['kk']
    x = src.get(n, {}).get(k, {}).get((i, j, 1 if E else 0))
    if x is None:
        return L.Val.missing({f'<{name} not in the jets>'})
    return x * (factorial(i) * factorial(j))            # Taylor -> full derivative


def evaluate(expr, a):
    if expr.is_Number:
        return L.Val(mp.mpf(expr.p) / expr.q) if expr.is_Rational else L.Val(mp.mpf(str(expr)))
    if expr.is_Symbol:
        nm = str(expr)
        if nm in ZV:
            return L.Val(ZV[nm])
        if nm in INPUTS:
            return CM.beta_of(a, nm)
        return atom_val(a, nm)
    if expr.is_Add:
        acc = L.Val(mp.mpf(0))
        for t in expr.args:
            acc = acc + evaluate(t, a)
        return acc
    if expr.is_Mul:
        acc = L.Val(mp.mpf(1))
        for t in expr.args:
            acc = acc * evaluate(t, a)
        return acc
    if expr.is_Pow and expr.exp.is_Integer and expr.exp > 0:
        b = evaluate(expr.base, a)
        acc = b
        for _ in range(int(expr.exp) - 1):
            acc = acc * b
        return acc
    raise ValueError(expr)


def parse_expr(pred_str):
    names = {}

    def rep(m_):
        names.setdefault(m_.group(0), f'ATOM{len(names)}')
        return names[m_.group(0)]
    code = re.sub(r'E?[CK]\d_\d+\[v\dd\d\]', rep, pred_str)
    loc = {nm: s.Symbol(nm) for nm in INPUTS + list(ZV)}
    loc.update({v_: s.Symbol(k_) for k_, v_ in names.items()})
    return s.sympify(code, locals=loc)


def structural_zero(group, pk):
    """engine pole analysis without integration: lowest Laurent order over all sectors (engine --sectors-info) and
    the exact coefficient map; [eps^k l^j] is a structural zero iff its Laurent order -j-1 lies below it"""
    sys.path.insert(0, os.path.join(ROOT, 'py'))
    from lri_moments import plan_moment, coefficient_map
    from campaign import sector_costs
    import subprocess, tempfile
    m = re.match(r'([AZQ])(\d+)_(\w+)', group)
    kind, n, der = m.group(1), int(m.group(2)), ('' if m.group(3) == 'base' else m.group(3))
    k, j = (int(x) for x in re.match(r'\[eps\^(-?\d+) l\^(\d+)\]', pk).groups())
    job = plan_moment(kind, n, der.count('v'), der.count('d'), der.count('E'), [k], None, 0)[0]
    from lri_moments import job_cfg, ENGINE
    cfg = job_cfg(job, N=1, shifts=1, korobov_a=1)
    fd, path = tempfile.mkstemp(suffix='.cfg')
    os.write(fd, cfg.encode()); os.close(fd)
    info = json.loads(subprocess.run([ENGINE, path, '--sectors-info'], capture_output=True, text=True, check=True).stdout)
    os.remove(path)
    lo = min(sc['lo'] for sc in info['sectors'])
    cmap, olo = coefficient_map(job, {c: list(range(lo, job['etarget'] + 1)) for c, _ in job['chans']})
    zero = (k, j) not in cmap and (olo is None or -j - 1 < olo)
    return {'status': None, 'engine_structural_zero': zero, 'lowest_order': olo, 'value': '0' if zero else None,
            'diff': 0.0 if zero else None, 'sigma': 0.0, 'pull': 0.0 if zero else None,
            'note': 'engine pole analysis (exact): below the lowest Laurent order of every sector'}


def raw_deriv(name):
    """raw coefficient in the DERIVATIVE convention (the framework holds Taylor coefficients internally:
    divide-by i! j! undone)"""
    M, n, i, j, e, p, k = L.parse_raw_name(L.canonical_raw_name(name))
    fac = factorial(i) * factorial(j)
    f = CM.raw_coef(name)
    return lambda asm: f(asm) * fac


def fnum(x):
    return None if x is None else float(mp.nstr(x, 17))


def row_from(NA, label, fn, target=None, extra=None, floor=mp.mpf('1e-25')):
    """value of fn (minus target) with the three error estimators; pull = (value - target) / sigma"""
    st = NA.stats(fn)
    if 'missing' in st:
        return {'check': label, 'status': 'MISSING', 'missing': st['missing'][:3], **(extra or {})}
    tgt = mp.mpf(0) if target is None else target
    sig = mp.sqrt(st['sigma'] ** 2 + floor ** 2)
    d = st['value'] - tgt
    r = {'check': label, 'value': mp.nstr(st['value'], 20), 'target': mp.nstr(tgt, 20), 'diff': fnum(d),
         'sigma': fnum(sig), 'pull': fnum(d / sig), 'l1': fnum(st['l1']),
         'sigma_parts': {k: fnum(st[k]) for k in ('sigma_lin', 'sigma_rep') if k in st}, **(extra or {})}
    return r


def summarize(rows, title):
    ok = [r for r in rows if r.get('pull') is not None]
    miss = [r for r in rows if r.get('status') == 'MISSING']
    if ok:
        pulls = [abs(r['pull']) for r in ok]
        rms = math.sqrt(sum(p * p for p in pulls) / len(pulls))
        worst = max(ok, key=lambda r: abs(r['pull']))
        log(f'  {title}: {len(ok)} checks, max |pull| {max(pulls):.2f} ({worst["check"]}), rms {rms:.2f}, '
            f'{sum(p > 3 for p in pulls)} above 3; {len(miss)} not computable from these data')
    else:
        log(f'  {title}: no computable check; {len(miss)} missing')
    return {'n': len(ok), 'max_abs_pull': max((abs(r['pull']) for r in ok), default=None),
            'rms_pull': math.sqrt(sum(r['pull'] ** 2 for r in ok) / len(ok)) if ok else None,
            'n_above_3': sum(abs(r['pull']) > 3 for r in ok), 'n_missing': len(miss)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='append', default=None)
    ap.add_argument('--kmax', type=int, default=11)
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'validate_C8'))
    ap.add_argument('--only', default='raw,poles,zeros,targets,rg')
    a = ap.parse_args()
    runs = [os.path.abspath(x) for x in (a.run or [os.path.join(ROOT, 'runs', 'c8val')]) if x != 'none']
    only = set(a.only.split(','))
    t0 = time.time()
    dat, info = c8_input(a.kmax, runs)
    log(f'input: {info["n_scalars"]} scalars (production {info["production_coefficients"]}, poles1 '
        f'{len(info["poles1_coefficients"])}, validation files {len(info["validation_coefficients"])}, added '
        f'{info.get("added")}, structural log zeros {info["log_zeros_total"]})')
    NA = C8Assembler(dat, a.kmax)
    log(f'C8 normalized jets assembled (kmax {a.kmax}, R = {NA.R}): {time.time() - t0:.0f} s')
    out = {'runs': runs, 'kmax': a.kmax, 'input_info': {k: v for k, v in info.items() if not isinstance(v, list)}}

    # 1. raw targets ---------------------------------------------------------------------------------
    if 'raw' in only:
        vt = json.load(open(os.path.join(SPEC8, 'validation_targets_C8.json')))
        rows = []
        for t in vt['independent_values']:
            m = re.fullmatch(r'A3_ddd\.(\d+)\.l(\d+)', t['id'])
            if not m:
                continue
            nm = f'A3_ddd[eps^{m.group(1)} l^{m.group(2)}]'
            rows.append(row_from(NA, nm, raw_deriv(nm), mp.mpf(t['value']), {'source': t['source']}))
        for t in vt['targets']:
            if t['kind'] == 'raw' and t['series'] == 'A7_d':
                nm = f"A7_d[eps^{t['eps_power']} l^{t['log_power']}]"
                ex = mp.mpf(Fraction(t['exact']).numerator) / Fraction(t['exact']).denominator
                rows.append(row_from(NA, nm, raw_deriv(nm), ex, {'source': t['source']}))
        for r in rows:
            log('   %-24s %s' % (r['check'], 'MISSING' if r.get('status') else
                                 f"value {r['value'][:22]:>24s} target {r['target'][:22]:>24s} diff {r['diff']:+.2e} "
                                 f"sigma {r['sigma']:.1e} pull {r['pull']:+.2f}"))
        out['raw'] = {'rows': rows, 'summary': summarize(rows, 'raw targets')}

    # 2. poles ---------------------------------------------------------------------------------------
    if 'poles' in only:
        P = json.load(open(os.path.join(SPEC8, 'poles_C8.json')))
        rows = []
        for jet, jd in P['jets'].items():
            m = re.fullmatch(r'(E?)([CK])(\d)\[v(\d)d(\d)\]', jet)
            E, X, n, i, j = m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(5))
            if (X == 'K' and n == 2):
                continue                       # exact two-kink sector
            mon = (i, j, 1 if E else 0)
            fac = factorial(i) * factorial(j)
            for p in jd['eps_powers_to_check']:
                for k in range(0, a.kmax + 1):
                    def fn(asm, X=X, n=n, mon=mon, p=p, k=k):
                        jj = (asm['C'] if X == 'C' else asm['K'])[n].get(mon)
                        return jj.coef(p, k) if jj is not None else L.Val.missing({'<no jet>'})
                    x = fn(NA.central)
                    if x.is_missing:
                        rows.append({'check': f'{jet}[eps^{p} l^{k}]', 'status': 'MISSING', 'missing': sorted(x.miss)[:3],
                                     'new_for_C8': jd.get('new_for_C8')})
                        continue
                    if x.is_exact_zero:
                        continue
                    r = row_from(NA, f'{jet}[eps^{p} l^{k}]', fn, None, {'new_for_C8': jd.get('new_for_C8')})
                    if r.get('pull') is not None:
                        r['value_fullderiv'] = r['diff'] * fac
                        r['nontrivial'] = (r['l1'] or 0) > 1e-12
                    rows.append(r)
        new = [r for r in rows if r.get('new_for_C8')]
        log('pole cancellation (poles_C8.json):')
        out['poles'] = {'rows': rows, 'summary_all': summarize(rows, 'all jets'),
                        'summary_new': summarize(new, 'jets new for C8'),
                        'summary_new_nontrivial': summarize([r for r in new if r.get('nontrivial')],
                                                            'new jets, non-trivial (L1 > 1e-12)')}
        mj = sorted({r['check'].split('[eps')[0] for r in rows if r.get('status') == 'MISSING'})
        log(f'  jets with a missing coefficient: {mj}')
        worst = sorted([r for r in rows if r.get('pull') is not None], key=lambda r: -abs(r['pull']))[:6]
        for r in worst:
            log(f"    worst {r['check']:28s} value {r['diff']:+.3e} sigma {r['sigma']:.1e} pull {r['pull']:+.2f} L1 {r['l1']:.1e}")

    # 3. structural zeros below the tight bound -------------------------------------------------------
    if 'zeros' in only:
        RQ = json.load(open(os.path.join(SPEC8, 'raw_requirements_C8.json')))
        rows = []
        for sname in RQ['safe_minus_tight']['below_tight_bound_must_vanish']:
            atom, pk = sname.split(' ', 1)
            g = atom
            E = g.startswith('E')
            if E:
                b, der = re.match(r'E([AZQ]\d+)_(\w+)', g).groups()
                g = f"{b}_{('' if der == 'base' else der) + 'E'}"
            if re.match(r'[ZQ]2', g.lstrip('E')):
                continue                      # two-kink: exact (spec two_kink_exact_C8.json)
            pref = g.replace('_base', '')
            nm = f'{pref}{pk}'
            r = row_from(NA, nm, CM.raw_coef(nm), None)
            if r.get('status') == 'MISSING':
                r = structural_zero(g, pk) | {'check': nm}
            rows.append(r)
        # below the tight bound but inside the framework's (safe) structural range of an endpoint Z moment: the
        # EC5_d and EC7 pole checks need Z4_dE[eps^-2] and Z6_E[eps^-3]; the spec's tight bounds (EZ_{2m} from
        # eps^-(m-1)) say they vanish
        for k in range(0, 4):
            for nm, what in ((f'Z4_dE[eps^-2 l^{k}]', 'EZ4_d'), (f'Z6_E[eps^-3 l^{k}]', 'EZ6')):
                rows.append(row_from(NA, nm, CM.raw_coef(nm), None,
                                     {'note': f'{what} below the tight bound (spec tight bounds EZ_2m from eps^-(m-1))'}))
        for r in rows:
            if 'engine_structural_zero' in r:
                log('   zero %-22s engine structural zero: %s (lowest Laurent order %s)' % (
                    r['check'], r['engine_structural_zero'], r['lowest_order']))
                continue
            log('   zero %-22s %s' % (r['check'], 'MISSING' if r.get('status') else
                                      f"value {r['diff']:+.2e} sigma {r['sigma']:.1e} pull {r['pull']:+.2f}"))
        out['zeros'] = {'rows': rows, 'summary': summarize(rows, 'below-tight-bound zeros')}

    # 4. normalized higher-log targets ------------------------------------------------------------------
    if 'targets' in only:
        vt = json.load(open(os.path.join(SPEC8, 'validation_targets_C8.json')))
        rows = []
        for t in vt['targets']:
            m = re.fullmatch(r'([CK])(\d)\[(\w+)\]\.l(\d+)', t['id'])
            if not m:
                continue
            X, n, tg, k = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            i, j = (0, 0) if tg == 'base' else (tg.count('v'), tg.count('d'))
            target_atom = f'{X}{n}_{k}[v{i}d{j}]'
            ex = parse_expr(t['exact'])
            rows.append(row_from(NA, t['id'], lambda asm, ex=ex, ta=target_atom: atom_val(asm, ta) - evaluate(ex, asm),
                                 None, {'closed_form': t['exact']}))
        log('normalized higher-log targets (validation_targets_C8.json):')
        out['targets'] = {'rows': rows, 'summary': summarize(rows, 'C3/K4 higher logs')}
        for r in sorted([r for r in rows if r.get('pull') is not None], key=lambda r: -abs(r['pull']))[:5]:
            log(f"    worst {r['check']:14s} diff {r['diff']:+.2e} sigma {r['sigma']:.1e} pull {r['pull']:+.2f}")

    # 5. RG log predictions --------------------------------------------------------------------------------
    if 'rg' in only:
        RG = json.load(open(os.path.join(SPEC8, 'rg_logs_C8.json')))
        rows = []
        for key, r in RG['second_log_formulas']['formulas'].items():
            ex = parse_expr(r['prediction'])
            rows.append(row_from(NA, f'{key} (second log)',
                                 lambda asm, ex=ex, ta=key: atom_val(asm, ta) - evaluate(ex, asm), None))
        for key, jet in RG['higher_log_formulas']['jets'].items():
            m_ = re.match(r'([CK])(\d)\[v(\d)d(\d)\]', key)
            X, n, i, j = m_.group(1), m_.group(2), m_.group(3), m_.group(4)
            for k, r in jet['logs'].items():
                if int(k) > a.kmax:
                    continue
                ex = parse_expr(r['prediction'])
                ta = f'{X}{n}_{k}[v{i}d{j}]'
                rows.append(row_from(NA, f'{key} l^{k}', lambda asm, ex=ex, ta=ta: atom_val(asm, ta) - evaluate(ex, asm),
                                     None))
        log('RG log predictions (rg_logs_C8.json):')
        out['rg'] = {'rows': rows, 'summary': summarize(rows, 'RG second and higher logs')}
        for r in sorted([r for r in rows if r.get('pull') is not None], key=lambda r: -abs(r['pull']))[:6]:
            log(f"    worst {r['check']:28s} diff {r['diff']:+.2e} sigma {r['sigma']:.1e} pull {r['pull']:+.2f}")
        mj = sorted({r['check'].split(' ')[0] for r in rows if r.get('status') == 'MISSING'})
        log(f'  not computable yet (need full-sector eps^0 data of the 6-9 kink atoms): {mj}')
    out['runtime_s'] = round(time.time() - t0, 1)
    json.dump(out, open(a.out + '.json', 'w'), indent=1, default=str)
    open(a.out + '.txt', 'w').write('\n'.join(LOG) + '\n')
    log(f'wrote {a.out}.json/.txt ({out["runtime_s"]} s)')


if __name__ == '__main__':
    main()
