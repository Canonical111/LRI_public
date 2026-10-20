#!/usr/bin/env python3
"""Driver for the independent Mellin/Hepp-sector engine (bin/lri_engine).

A raw moment is specified by
    kind   : 'A' (odd, n kinks), 'Z' (even), 'Q' (even, with D_{2m} insertion)
    n      : number of kinks
    nv,nd,ne : derivative orders  d^nv/dv^nv d^nd/ddelta^nd d^ne/deta^ne at v=1, delta=0, eta=0
               (raw derivatives, NOT Taylor coefficients; eta = endpoint source, ne<=1 supported)
The integrand is  W_n(v,delta) U_n(eta,delta) [D_n]  on Omega_n(eps)  (note eqs. 4.1-4.3, 3.x).

Output: coefficients c[(k,j)] of eps^k * log(eps)^j in the small-eps expansion of the raw moment,
for the requested powers k, with QMC standard errors.

Conventions (checked against the note, see README):
  f_delta(r) = (r^delta-1)/delta = sum_k delta^{k-1} L^k/k!,  L = log r
  W/W0 = exp[2(v-1)S1 + 2v sum_{k>=2} delta^{k-1} S_k/k!],  S_k = sum_{i<j} q_i q_j log^k(X_j-X_i)
  U    = exp[eta sum_{k>=1} delta^{k-1} E_k/k!],  E_k = sum_i q_i [log^k X_i +- log^k (1-X_i)]
         (+ for odd n = U^odd, - for even n = U^even)
"""
import json, math, os, subprocess, sys, tempfile, hashlib
from fractions import Fraction
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE = os.environ.get('LRI_ENGINE', os.path.join(ROOT, 'bin', 'lri_engine'))
LATTICE_DB = os.environ.get('LRI_LATTICE_DB', os.path.join(ROOT, 'py', 'korobov_db_g01.json'))

S = sp.symbols('S1:5')
E = sp.symbols('E1:4')
_v, _dl, _eta = sp.symbols('v delta eta')


def insertion_poly(nv, nd, ne):
    """Polynomial P(S,E) with  d^nv_v d^nd_delta d^ne_eta [W U] = P * W0  at v=1,delta=0,eta=0."""
    expo = 2 * (_v - 1) * S[0] + 2 * _v * sum(_dl ** (k - 1) * S[k - 1] / sp.factorial(k) for k in range(2, 5))
    expo += _eta * sum(_dl ** (k - 1) * E[k - 1] / sp.factorial(k) for k in range(1, 4))
    f = sp.exp(expo)
    g = f
    if nv: g = sp.diff(g, _v, nv)
    if nd: g = sp.diff(g, _dl, nd)
    if ne: g = sp.diff(g, _eta, ne)
    g = sp.expand(sp.simplify(g.subs({_v: 1, _dl: 0, _eta: 0})))
    return sp.expand(g)


def S0const(n):
    Q = 1 if n % 2 else 0
    return sp.Rational(Q * Q - n, 2)


def Dshift(poly, n):
    """Uniform shift derivative D = sum_I d/dL_I acting on a polynomial in S_k (no E's): D S_k = k S_{k-1}."""
    out = 0
    for k in range(1, 5):
        prev = S0const(n) if k == 1 else S[k - 2]
        out += sp.diff(poly, S[k - 1]) * k * prev
    return sp.expand(out)


def poly_terms(poly):
    """-> list of (coef(float), exps[7]) for engine input."""
    poly = sp.expand(poly)
    if poly == 0:
        return []
    P = sp.Poly(poly, *S, *E)
    out = []
    for mon, co in P.terms():
        out.append((float(co), list(mon), sp.Rational(co)))
    return out


# ---------------------------------------------------------------- Laurent series helpers (exact coefficients)
def laurent_inv_power(c, p, lo_needed, hi):
    """(c+e)^{-p} as dict order->Fraction, orders up to hi."""
    out = {}
    if c == 0:
        if -p <= hi:
            out[-p] = Fraction(1)
        return out
    b = Fraction(1)
    for i in range(0, hi + 1):
        out[i] = b * Fraction(c) ** (-(p + i))
        b = b * Fraction(-p - i, i + 1)
    return out


def lmul(a, b, hi):
    out = {}
    for i, x in a.items():
        for j, y in b.items():
            if i + j <= hi:
                out[i + j] = out.get(i + j, 0) + x * y
    return out


def ladd(a, b, s=1):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + s * v
    return out


# ---------------------------------------------------------------- lattice
def atomic_write_text(path, text):
    """write text to path atomically (tmp file in the same directory + os.replace)"""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.' + os.path.basename(path) + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def atomic_write_json(path, obj, **kw):
    atomic_write_text(path, json.dumps(obj, **kw) + '\n')


def korobov(N, d, ncand=2000):
    """weighted-P2 Korobov generator for (N, d), cached in LATTICE_DB (locked read-modify-write, atomic replace)"""
    key = f'{N}_{d}'
    if os.path.exists(LATTICE_DB):
        try:
            db = json.load(open(LATTICE_DB))
            if key in db:
                return db[key]
        except ValueError:
            pass
    out = subprocess.run([ENGINE, '--korobov', str(N), str(d), str(ncand)], capture_output=True, text=True, check=True)
    a = int(out.stdout.split()[2])
    import fcntl
    with open(LATTICE_DB + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        db = json.load(open(LATTICE_DB)) if os.path.exists(LATTICE_DB) else {}
        db[key] = a
        atomic_write_json(LATTICE_DB, db, indent=1, sort_keys=True)
    return a


def next_prime(x):
    def isp(m):
        if m < 2: return False
        if m % 2 == 0: return m == 2
        r = int(m ** 0.5)
        for p in range(3, r + 1, 2):
            if m % p == 0: return False
        return True
    while not isp(x):
        x += 1
    return x


# ---------------------------------------------------------------- engine call
def run_engine(n, kind, geom, s0, etarget, channels, N=10007, shifts=8, transform=3, prec='auto', threads=0,
               seed=1234567, sectors=None, extra=None, keep=None, korobov_a=None):
    M = n + 1 if geom == 'full' else n - 1
    d = max(M - 1, 0)
    lines = [f'n {n}', f'type {kind}', f'geom {geom}', f's0 {s0}', f'etarget {etarget}', f'prec {prec}',
             f'transform {transform}', f'N {N}', f'shifts {shifts}', f'seed {seed}', f'threads {threads}']
    if d >= 1:
        a = korobov_a if korobov_a is not None else (korobov(N, d) if N > 3 else 1)
        lines.append(f'korobov {a}')
    else:
        lines.append('z 1')
    if sectors is not None:
        lines.append(f'sectors {sectors[0]} {sectors[1]}')
    if extra:
        lines += extra
    for name, terms in channels:
        lines.append(f'channel {name}')
        for co, ex, _ in terms:
            lines.append('term %.17e %s' % (co, ' '.join(str(x) for x in ex)))
    cfg = '\n'.join(lines) + '\n'
    fd, path = tempfile.mkstemp(suffix='.cfg', prefix='lri_')
    os.write(fd, cfg.encode())
    os.close(fd)
    outp = path + '.json'
    with open(path, 'a') as f:
        f.write(f'out {outp}\n')
    r = subprocess.run([ENGINE, path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr + r.stdout)
    res = json.load(open(outp))
    if keep:
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        open(keep + '.cfg', 'w').write(cfg)
        json.dump(res, open(keep + '.json', 'w'), indent=1)
    os.remove(path)
    os.remove(outp)
    return res


# ---------------------------------------------------------------- moment assembly
def plan_moment(kind, n, nv=0, nd=0, ne=0, powers=(0,), geom=None, jmin=0):
    """Return a list of engine jobs: dict(k, s0, geom, etarget, chans, pre) where pre[j] is the exact
    Laurent prefactor multiplying channel j."""
    P = insertion_poly(nv, nd, ne)
    hasE = any(P.has(e) for e in E)
    if geom is None:
        geom = 'full' if hasE else 'angular'
    if hasE and geom != 'full':
        raise ValueError('endpoint moments need geom=full')
    jobs = []
    jmin_all = jmin
    for k in powers:
        s0 = -k
        jmin = (jmin_all.get(str(k), jmin_all.get(k, 0)) if isinstance(jmin_all, dict) else jmin_all)
        if geom == 'full':
            pre = [(0, laurent_inv_power(s0, 1, 0, 60))]
            chans = [('P0', poly_terms(P))]
        else:
            M = n - 1
            dF = sum(2 * (1 if (i % 2) else -1) * (1 if (j % 2) else -1) for i in range(1, n + 1) for j in range(i + 1, n + 1))
            if kind == 'Q':
                dF += 1
            kappa = M + dF
            chans, pre = [], []
            Pj, j = P, 0
            while Pj != 0:
                chans.append((f'D{j}', poly_terms(Pj)))
                a1 = laurent_inv_power(kappa + s0, j + 1, 0, 60)
                a2 = laurent_inv_power(kappa + s0 + 1, j + 1, 0, 60)
                rad = {o: v * (-1) ** j for o, v in ladd(a1, a2, -1).items()}
                pre.append((j, lmul(laurent_inv_power(s0, 1, 0, 60), rad, 60)))
                Pj = Dshift(Pj, n)
                j += 1
        et = -10 ** 9
        chet = []
        for j, pr in pre:
            lo = min(o for o, v in pr.items() if v != 0) if pr else 0
            chet.append(-1 - jmin - lo)
            et = max(et, -1 - jmin - lo)
        jobs.append(dict(k=k, s0=s0, geom=geom, etarget=et, chans=chans, pre=pre, n=n, kind=kind, jmin=jmin,
                         chet=chet))
    return jobs


def assemble_job(job, res, result):
    """LEGACY (phase 1; kept only so that the phase-1 review scripts reproduce): combine engine output res for
    one job into result {(k,j): (v,e)} with the (channel, Laurent order) errors added IN QUADRATURE.  This is
    wrong for correlated combinations (review test C: ratios 0.05-2.3); the pipeline uses assemble_replicates."""
    k, jmin = job['k'], job['jmin']
    Ival, Ierr = {}, {}
    for (j, pr), (cname, _) in zip(job['pre'], job['chans']):
        ch = res['channels'][cname]
        for o1, c1 in pr.items():
            for o2, v2, e2 in zip(ch['orders'], ch['value'], ch['err']):
                o = o1 + o2
                if o > -1 - jmin:
                    continue
                Ival[o] = Ival.get(o, 0.0) + float(c1) * v2
                Ierr[o] = Ierr.get(o, 0.0) + (float(c1) * e2) ** 2
    for o in sorted(Ival):
        jj = -o - 1
        if jj < 0:
            continue
        fac = (-1) ** jj / math.factorial(jj)
        result[(k, jj)] = (fac * Ival[o], abs(fac) * math.sqrt(Ierr[o]))
    return result


# ---------------------------------------------------------------- v2: replicate-based assembly
# Error floor (relative to the L1 scale of the assembled coefficient):
#   sigma_floor(k,j) = FLOOR_REL * sum_{channel, order} |w| * abs[channel][order],
# abs = (1/N) sum_points |f| summed over sectors (engine output 'abs').  Calibrated without archive data in
# results/floor_calibration.txt (tests/floor_calibration.py, README section 3b): independent runs need
# f >= 2e-17; strict tolerances change nothing; 1e-15 (~10 ulp of the L1 scale) also covers the systematic
# double rounding (prefactor weights, pole factors) that no run comparison can see.  Override: LRI_FLOOR_REL.
FLOOR_REL = float(os.environ.get('LRI_FLOOR_REL', '1e-15'))


def coefficient_map(job, orders_by_channel):
    """Exact linear map from channel Laurent coefficients to eps^k log^j coefficients of one job:
    returns ({(k,jj): [(channel, order, weight)]}, lowest available Laurent order of I~)."""
    k, jmin = job['k'], job['jmin']
    terms = {}
    olo = None
    for (j, pr), (cname, _) in zip(job['pre'], job['chans']):
        o1min = min((o1 for o1, c1 in pr.items() if c1 != 0), default=None)
        if o1min is None or not orders_by_channel.get(cname):
            continue
        cand = o1min + min(orders_by_channel[cname])
        olo = cand if olo is None else min(olo, cand)
        for o1, c1 in pr.items():
            if c1 == 0:
                continue
            for o2 in orders_by_channel[cname]:
                o = o1 + o2
                if o > -1 - jmin:
                    continue
                terms.setdefault(o, []).append((cname, o2, c1))
    out = {}
    for o, lst in terms.items():
        jj = -o - 1
        if jj < 0:
            continue
        fac = Fraction((-1) ** jj, math.factorial(jj))
        out[(k, jj)] = [(c, o2, float(fac * Fraction(c1))) for c, o2, c1 in lst]
    return out, olo


def _add_series(acc, orders, rep, absv, sign=1.0):
    """acc: {'rep': {o: [R values]}, 'abs': {o: value}}; add (sign *) one output's per-replicate values"""
    R = len(rep)
    for io, o in enumerate(orders):
        r = acc['rep'].setdefault(o, [0.0] * R)
        if len(r) != R:
            raise ValueError(f'inconsistent number of shifts ({len(r)} vs {R})')
        for i in range(R):
            r[i] += sign * rep[i][io]
        if absv is not None:
            acc['abs'][o] = acc['abs'].get(o, 0.0) + abs(absv[io])


def merge_replicates(outs, substitutions=()):
    """Merge v2 engine outputs of disjoint sector ranges of one job (and optional sector substitutions
    [(orig_output, sector_id, refined_output)], which replace one sector's per-shift values by those of a
    refined run with the same number of shifts).  Returns
      {'R': R, 'channels': {c: {'rep': {o: [R]}, 'abs': {o: L1}}}, 'cpu_seconds': ...}"""
    for r in outs:
        if 'rep' not in next(iter(r['channels'].values())):
            raise ValueError('engine output without per-shift replicates (phase-1 format); rerun with the v2 engine')
        if not r.get('complete', False):
            raise ValueError('incomplete engine output')
    R = len(next(iter(outs[0]['channels'].values()))['rep'])
    m = {'R': R, 'channels': {}, 'cpu_seconds': sum(r['cpu_seconds'] for r in outs)}
    for r in outs:
        for c, ch in r['channels'].items():
            acc = m['channels'].setdefault(c, {'rep': {}, 'abs': {}})
            if len(ch['rep']) != R:
                raise ValueError('outputs of one job have different numbers of shifts')
            _add_series(acc, ch['orders'], ch['rep'], ch['abs'])
    for orig, sec, ref in substitutions:
        m['cpu_seconds'] += ref['cpu_seconds']
        for c, ch in orig['channels'].items():
            ps = [x for x in ch['per_sector'] if x['id'] == sec]
            if len(ps) != 1 or 'rep' not in ps[0]:
                raise ValueError(f'sector {sec} has no per-shift values in the original output')
            acc = m['channels'][c]
            _add_series(acc, ch['orders'], ps[0]['rep'], None, -1.0)
            rc = ref['channels'][c]
            if len(rc['rep']) != R:
                raise ValueError('refined run must use the same number of shifts')
            # L1 scale: the refined sector's abs is added on top (conservative; the original sector's share stays)
            _add_series(acc, rc['orders'], rc['rep'], rc['abs'])
    return m


def assemble_replicates(job, merged, floor_rel=None, need=None):
    """eps^k log^j coefficients of one job from per-replicate channel Laurent coefficients.
    Returns {(k,jj): dict(value, err, stat, floor, reps, zero)}:
      reps  = the coefficient assembled separately in each of the R replicates (i.i.d.),
      value = mean(reps), stat = std(reps)/sqrt(R), floor = floor_rel * L1 scale, err = sqrt(stat^2+floor^2).
    need: list of jj required at this k.  A required jj whose Laurent order lies below the lowest order that
    can occur (no pole that deep) is an exact structural zero (value 0, err 0, zero=True); a required jj that
    was not computed (jj < jmin) raises ValueError (genuinely missing)."""
    if floor_rel is None:
        floor_rel = FLOOR_REL
    R = merged['R']
    orders = {c: sorted(ch['rep']) for c, ch in merged['channels'].items()}
    cmap, olo = coefficient_map(job, orders)
    out = {}
    for key, lst in cmap.items():
        reps = [0.0] * R
        l1 = 0.0
        for c, o2, w in lst:
            rr = merged['channels'][c]['rep'][o2]
            for i in range(R):
                reps[i] += w * rr[i]
            l1 += abs(w) * merged['channels'][c]['abs'].get(o2, 0.0)
        mean = sum(reps) / R
        stat = math.sqrt(sum((x - mean) ** 2 for x in reps) / (R - 1) / R) if R > 1 else 0.0
        fl = floor_rel * l1
        out[key] = {'value': mean, 'err': math.hypot(stat, fl), 'stat': stat, 'floor': fl, 'l1': l1,
                    'reps': reps, 'zero': False}
    k = job['k']
    for jj in (need or []):
        if (k, jj) in out:
            continue
        if jj < job['jmin']:
            raise ValueError(f"{job.get('kind')}{job.get('n')} k={k}: log^{jj} needed but not computed (jmin={job['jmin']})")
        if olo is not None and -jj - 1 < olo:
            out[(k, jj)] = {'value': 0.0, 'err': 0.0, 'stat': 0.0, 'floor': 0.0, 'l1': 0.0, 'reps': [0.0] * R,
                            'zero': True}
        else:
            raise ValueError(f"{job.get('kind')}{job.get('n')} k={k}: log^{jj} missing from the engine output")
    return out


def job_cfg(job, N=10007, shifts=8, transform=3, prec='auto', threads=0, seed=1234567, sectors=None, extra=None,
            korobov_a=None):
    n, kind, geom = job['n'], job['kind'], job['geom']
    M = n + 1 if geom == 'full' else n - 1
    d = max(M - 1, 0)
    lines = [f'n {n}', f'type {kind}', f'geom {geom}', f's0 {job["s0"]}', f'etarget {job["etarget"]}', f'prec {prec}',
             f'transform {transform}', f'N {N}', f'shifts {shifts}', f'seed {seed}', f'threads {threads}']
    if d >= 1:
        a = korobov_a if korobov_a is not None else (korobov(N, d) if N > 3 else 1)
        lines.append(f'korobov {a}')
    else:
        lines.append('z 1')
    if sectors is not None:
        lines.append(f'sectors {sectors[0]} {sectors[1]}')
    if extra:
        lines += extra
    for ic, (name, terms) in enumerate(job['chans']):
        lines.append(f'channel {name}')
        if 'chet' in job:
            lines.append(f"chet {job['chet'][ic]}")
        for co, ex, _ in terms:
            lines.append('term %.17e %s' % (co, ' '.join(str(x) for x in ex)))
    return '\n'.join(lines) + '\n'


def run_cfg(cfg, keep=None):
    fd, path = tempfile.mkstemp(suffix='.cfg', prefix='lri_')
    os.write(fd, cfg.encode())
    os.close(fd)
    outp = path + '.json'
    with open(path, 'a') as f:
        f.write(f'out {outp}\n')
    r = subprocess.run([ENGINE, path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr + r.stdout)
    res = json.load(open(outp))
    if keep:
        os.makedirs(os.path.dirname(keep) or '.', exist_ok=True)
        open(keep + '.cfg', 'w').write(cfg)
        json.dump(res, open(keep + '.json', 'w'), indent=1)
    os.remove(path)
    os.remove(outp)
    return res


def merge_outputs(outs):
    """Merge engine JSON outputs of disjoint sector ranges of the same job (values add, variances add)."""
    base = json.loads(json.dumps(outs[0]))
    for c in base['channels']:
        ch = base['channels'][c]
        lo = base['lo']
        vals = {o: 0.0 for o in ch['orders']}
        var = {o: 0.0 for o in ch['orders']}
        for r in outs:
            cc = r['channels'][c]
            for o, v, e in zip(cc['orders'], cc['value'], cc['err']):
                vals[o] = vals.get(o, 0.0) + v
                var[o] = var.get(o, 0.0) + e * e
        orders = sorted(vals)
        ch['orders'] = orders
        ch['value'] = [vals[o] for o in orders]
        ch['err'] = [math.sqrt(var[o]) for o in orders]
        ch.pop('per_sector', None)
    base['cpu_seconds'] = sum(r['cpu_seconds'] for r in outs)
    return base


def moment(kind, n, nv=0, nd=0, ne=0, powers=(0,), geom=None, N=10007, shifts=8, transform=3, prec='auto',
           threads=0, verbose=False, keep=None, seed=1234567, extra=None, jmin=0):
    """Return dict {(k,j): (value, err)} for eps^k log^j eps coefficients of the raw moment, k in powers."""
    result, meta = {}, {}
    for job in plan_moment(kind, n, nv, nd, ne, powers, geom, jmin):
        cfg = job_cfg(job, N=N, shifts=shifts, transform=transform, prec=prec, threads=threads, seed=seed,
                      extra=extra)
        res = run_cfg(cfg, keep=(keep + f"_k{job['k']}" if keep else None))
        meta[job['k']] = {'wall': res['wall_seconds'], 'cpu': res['cpu_seconds'], 'sectors': res['sectors_total']}
        for key, v in assemble_replicates(job, merge_replicates([res])).items():
            result[key] = (v['value'], v['err'])
    if verbose:
        for key in sorted(result):
            print(key, '%.15g +- %.2g' % result[key])
    return result, meta


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('kind')
    ap.add_argument('n', type=int)
    ap.add_argument('--nv', type=int, default=0)
    ap.add_argument('--nd', type=int, default=0)
    ap.add_argument('--ne', type=int, default=0)
    ap.add_argument('--powers', default='0')
    ap.add_argument('--geom', default=None)
    ap.add_argument('--N', type=int, default=10007)
    ap.add_argument('--shifts', type=int, default=8)
    ap.add_argument('--transform', type=int, default=3)
    ap.add_argument('--prec', default='auto')
    ap.add_argument('--jmin', type=int, default=0)
    ap.add_argument('--threads', type=int, default=0)
    a = ap.parse_args()
    r, m = moment(a.kind, a.n, a.nv, a.nd, a.ne, powers=[int(x) for x in a.powers.split(',')], geom=a.geom, N=a.N,
                  shifts=a.shifts, transform=a.transform, prec=a.prec, verbose=True, jmin=a.jmin, threads=a.threads)
    print(m)
