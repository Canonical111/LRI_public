#!/usr/bin/env python3
"""C8 production planner (phase 3): three tiers on the framework's signed C8 gradients.

Inputs
  specs/production_C8.json   66 jobs (group, eps power) with the 85 beyond-D4 coefficients, their tier and dC8/dx
  --src RUNDIR ...           pilot run directories (campaign.py layout, collected: results.json + per-cfg outputs):
                             runs/c8conv (production configuration, sector samples, two N per job) and runs/c8val
                             (all sectors, one N, all log powers); sector-sampled entries carry 'sectorstride'
  --speed F                  cpu time on the production machine / cpu time on the pilot machine (calibration
                             runs/calib_personal-desktop: same cfgs on the personal desktop and on symmetry amdq)
  --src-speed DIR=F          per-source speed factor (overrides --speed for the references of DIR; e.g. a probe run
                             on symmetry amdq itself: DIR=1.0, while the personal-desktop pilots keep --speed 0.667)
  --n-floor lower            (with a probe as reference) the greedy may start at the lower measured size instead of
                             the reference size, so a budget can lower N below the probe's N
  --budget-BC X              cap for tiers B + C together (production core-hours): if the B and C targets cost more,
                             both targets are relaxed by the smallest common factor f >= 1 (TB -> f TB, T -> f T;
                             --budget-priority B or C relaxes only the other tier first) whose plan fits in X
Error model per job (the planner of the C6/C7 production, tests on C8):
  var(N) = max(var_rep, var_pool) * stride * (N/N_ref)^(-2 alpha) + (stride * floor)^2 projected on dC8/dx
    var_rep  = sum_r D_r^2/(R(R-1)),  D_r = sum_i g_i (x_{i,r} - mean_i)  (replicates of the whole job)
    var_pool = sum_s var_r(D_{s,r}) / R                                  (sector-pooled, hundreds of dof)
  alpha: conservative per dimension (7D 2.0, 6D 2.0, 5D 2.8, 4D 2.3, <=3D 3.0), lowered to the measured rate between
  the two pilot sizes of the same sector sample when that is slower and the smaller size is >= --rate-min-N
  (measured on the larger of the replicate and pooled variances).  --alpha7 overrides the 7D rate (scenarios).
  Cost(N) = (cpu per point and sector at the reference) * N * shifts * sectors * speed.
Allocation (greedy: largest variance reduction per added core-hour, prime ladder):
  tier A: jobs of W, S, L3, M21, M12, N2, Ndelta until sigma_A <= --TA, then on to the 'best affordable' target
          --TA-best as long as the tier-A total stays below --A-budget core-hours;
  tier B: U and Kv jobs until sigma(C8 without the J9 term) = sqrt(sA^2 + sB^2 + sB_old^2) <= --TB (0.005, leaving
          sqrt(T^2 - TB^2) for tier C); alternatives --alt-B;
  tier C: J9 jobs, on top of A and B, until the total sigma(C8) <= --T (0.01); alternatives --alt.
Output: results/plan_C8.json, results/plan_C8.md; tier specs with py/make_spec_C8.py tier.
"""
import argparse, glob, json, math, os, re, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lri_moments import coefficient_map            # noqa: E402
from campaign import decode_job                    # noqa: E402

# prime ladder with ~sqrt(2) steps (the C6/C7 ladder plus the primes next to the geometric means)
LADDER = [1009, 1423, 2003, 2833, 4001, 5669, 8009, 11321, 16001, 22637, 32003, 45259, 64007, 91621, 131071, 185363,
          262139, 370759, 524287, 741457, 1048573, 1482907, 2097143, 2965819, 4194301]
# conservative QMC error rates per dimension (sigma ~ N^-alpha): 6D = 2.0 is the full-sector rate of the tier-1 Q8
# (N = 1009 -> 262139: 2.06; README section 10), 7D has no asymptotic measurement (the 1009 -> 4001 pilot is
# pre-asymptotic) and gets the same 2.0; 5D/4D as in the C6/C7 planner (measured 2.6-4.6 between 16001 and 64007)
ALPHA = {7: 2.0, 6: 2.0, 5: 2.8, 4: 2.3}
SHIFTS = 6
CORES = 64
# smallest production N per dimension: the 1-3 dimensional jobs are never extrapolated below the validation-run size
# (their cost is minutes at any N); 4D from 4001; 5-7D from the bottom of the ladder
START = {0: 262139, 1: 262139, 2: 262139, 3: 262139, 4: 4001}
LOWER_REF = 'last'
N_FLOOR = 'ref'            # 'lower': with a measured rate, the greedy may start at the lower reference size
SIGMA_BOLD = 1.16e-5        # framework c8_production: B_old from the tier-1 production (largest of 3 estimators)


def base_group(name):
    return re.sub(r'(_N\d+)?(_S\d+)?$', '', name)


INPUTS_NEW = ['W', 'S', 'U', 'J9', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'Kv']


def load_refs(srcs, src_speed=None):
    """{(group, k): [ref, ...]} with ref = dict(src, N, stride, R, nsec, us_pt (per point, sector, shift), var_rep,
    var_pool, floor2, jmin) for the C8 projection, and var_in = {input: variance at the reference} for the ten new
    inputs (larger of replicate and pooled projection on d input / dx); src_speed = {abs src dir: speed factor}
    adds 'speed' to the references of that source (cost model of a source measured on another machine)"""
    src_speed = src_speed or {}
    prod = json.load(open(os.path.join(ROOT, 'specs', 'production_C8.json')))['groups']
    sens = json.load(open(os.path.join(ROOT, 'specs', 'framework_sensitivities_C8.json')))['signed']
    G = {(o['name'], int(p)): {int(kj.split(',')[1]): g for kj, g in o['grad_C8'].items()
                               if int(kj.split(',')[0]) == int(p)} for o in prod for p in o['powers']}
    refs = {}
    for src in srcs:
        res = json.load(open(os.path.join(src, 'results.json')))
        man = json.load(open(os.path.join(src, 'manifest.json')))
        for m in man:
            g, k = base_group(m['moment']), m['job']['k']
            if (g, k) not in G:
                continue
            pref = g.replace('_base', '')
            grads = {'C8': G[(g, k)]}
            for inp in INPUTS_NEW:
                grads[inp] = {j: float(sens.get(inp, {}).get(f'{pref}[eps^{k} l^{j}]', 0.0)) for j in G[(g, k)]}
            job = decode_job(m['job'])
            stride = 1
            for e in (m.get('extra') or []):
                if str(e).startswith('sectorstride'):
                    stride = int(str(e).split()[1])
            outs = []
            for c in m['cfgs']:
                p = os.path.join(src, c + '.json')
                if not os.path.exists(p):
                    outs = None
                    break
                outs.append(json.load(open(p)))
            if not outs:
                continue
            nsec = sum(o['sector_range'][1] - o['sector_range'][0] for o in outs)
            cpu = sum(o['cpu_seconds'] for o in outs)
            N, R = outs[0]['N'], outs[0]['shifts']
            name = m['moment']
            reps = res['replicates'].get(name, {})
            errs = res['errors'].get(name, {})
            keys = [f'{k},{j}' for j in G[(g, k)] if f'{k},{j}' in reps]
            persec = []
            vrep = {o: 0.0 for o in grads}
            vpool = {o: 0.0 for o in grads}
            fl2 = {o: 0.0 for o in grads}
            if not keys:
                # all needed coefficients are structural zeros (or missing): no variance
                if not all(errs.get(f'{k},{j}', {}).get('zero') for j in G[(g, k)]):
                    continue
            else:
                mean = {kk: sum(reps[kk]) / R for kk in keys}
                for o, gr in grads.items():
                    D = [sum(gr[int(kk.split(',')[1])] * (reps[kk][r] - mean[kk]) for kk in keys) for r in range(R)]
                    vrep[o] = sum(x * x for x in D) / (R * (R - 1))
                    fl2[o] = sum((gr[int(kk.split(',')[1])] * errs[kk]['floor']) ** 2 for kk in keys)
                # sector-pooled projections
                for oo in outs:
                    orders = {c: ch['orders'] for c, ch in oo['channels'].items()}
                    cmap, _ = coefficient_map(job, orders)
                    chans = oo['channels']
                    first = next(iter(chans.values()))
                    for isec in range(len(first['per_sector'])):
                        xc = {}
                        for kk in keys:
                            j = int(kk.split(',')[1])
                            x = [0.0] * R
                            for c, o2, w in cmap.get((k, j), []):
                                ps = chans[c]['per_sector'][isec]
                                io = chans[c]['orders'].index(o2)
                                for r in range(R):
                                    x[r] += w * ps['rep'][r][io]
                            xc[j] = x
                        for o, gr in grads.items():
                            y = [sum(gr[j] * xc[j][r] for j in xc) for r in range(R)]
                            vs = statistics.variance(y) / R
                            vpool[o] += vs
                            if o == 'C8':
                                persec.append((vs, first['per_sector'][isec]['cpu']))
            refs.setdefault((g, k), []).append({
                **({'speed': src_speed[src]} if src in src_speed else {}),
                'src': os.path.relpath(src, ROOT), 'entry': name, 'N': N, 'stride': stride, 'R': R, 'nsec': nsec,
                'jmin': int(job['jmin']),
                'us_pt': 1e6 * cpu / (N * R * nsec), 'cpu_h': cpu / 3600, 'var_rep': vrep['C8'],
                'var_pool': vpool['C8'], 'floor2': fl2['C8'], 'persec': persec,
                'var_in': {o: max(vrep[o], vpool[o]) for o in INPUTS_NEW}, 'floor2_in': {o: fl2[o] for o in INPUTS_NEW}})
    return prod, G, refs


def model(prod, refs, speed, rate_min_N=16001):
    jobs = []
    for o in prod:
        for p in o['powers']:
            k, p = int(p), str(p)
            rs = refs.get((o['name'], k), [])
            j = {'group': o['name'], 'k': k, 'tier': o['tier'][p], 'dim': o['dim'], 'sectors': o['sectors'],
                 'jmin': o['jmin'][p], 'coeffs': o['coeffs'][p],
                 'grad': {jj: o['grad_C8'][f'{k},{jj}'] for jj in o['coeffs'][p]}}
            # prefer references in the production configuration (same jmin), then the largest N
            prodcfg = [r for r in rs if r['jmin'] <= o['jmin'][p]]
            cands = sorted(prodcfg or rs, key=lambda r: (r['jmin'] == o['jmin'][p], r['N'], -r['stride']))
            if not cands:
                j['nodata'] = True
                jobs.append(j)
                continue
            ref = cands[-1]
            alpha = ALPHA.get(o['dim'], 3.0)
            meas = None
            lo = [r for r in rs if r['N'] < ref['N'] and r['stride'] == ref['stride'] and r['jmin'] == ref['jmin']]
            if lo:
                # 'last': the last listed smaller-N reference (phase-3 plans); 'largest': the largest smaller N
                # (needed once a probe at production N adds a third size to the 1009/4001 pilot pair)
                lo = sorted(lo, key=lambda r: r['N'])[-1] if LOWER_REF == 'largest' else lo[-1]
                v0 = max(lo['var_pool'], lo['var_rep'])
                v1 = max(ref['var_pool'], ref['var_rep'])
                if v0 > 0 and v1 > 0:
                    meas = 0.5 * math.log(v0 / v1) / math.log(ref['N'] / lo['N'])
            # a measured rate is used (when slower than the default) only if both sizes are asymptotic enough:
            # 1009 -> 4001 in 6-7 dimensions is pre-asymptotic (README section 4), so there it is only reported
            if meas is not None and meas < alpha - 0.3 and lo['N'] >= rate_min_N:
                alpha = max(meas, 0.75)
            if lo and N_FLOOR == 'lower' and lo['N'] >= rate_min_N and 'speed' in ref:
                # the reference is a probe at production N (a --src-speed source): N may go down to the lower
                # measured size, interpolating with the measured rate
                j['n_floor'] = lo['N']
            j.update({'ref': ref, 'alpha': alpha, 'alpha_meas': meas,
                      'var_ref': max(ref['var_rep'], ref['var_pool']) * ref['stride'] * ref['R'] / SHIFTS,
                      'floor2': ref['floor2'] * ref['stride'] ** 2,
                      'var_in_ref': {o: v * ref['stride'] * ref['R'] / SHIFTS for o, v in ref['var_in'].items()},
                      'floor2_in': {o: v * ref['stride'] ** 2 for o, v in ref['floor2_in'].items()},
                      # cost per point (all sectors, all shifts) in production core-hours
                      'cph': ref['us_pt'] * 1e-6 * SHIFTS * o['sectors'] * ref.get('speed', speed) / 3600})
            jobs.append(j)
    return jobs


def var_at(j, N):
    if j.get('nodata'):
        return 0.0
    return j['var_ref'] * (N / j['ref']['N']) ** (-2 * j['alpha']) + j['floor2']


def var_in_at(j, N, o):
    if j.get('nodata'):
        return 0.0
    return j['var_in_ref'][o] * (N / j['ref']['N']) ** (-2 * j['alpha']) + j['floor2_in'][o]


def cost_at(j, N):
    return 0.0 if j.get('nodata') else j['cph'] * N


def greedy(jobs, sel, target2, fixed2=0.0, budget=None):
    """raise N of `sel` jobs until sum var + fixed2 <= target2 (or the budget is spent)"""
    def start(j):
        # never below the dimension's minimum, nor below the pilot reference size (no downward extrapolation:
        # below the reference the lattice rules may be pre-asymptotic)
        n0 = START.get(j['dim'], LADDER[0])
        if not j.get('nodata'):
            n0 = max(n0, max(x for x in LADDER if x <= max(j.get('n_floor', j['ref']['N']), LADDER[0])))
        return n0
    Ns = {id(j): start(j) for j in sel}
    def tot():
        return sum(var_at(j, Ns[id(j)]) for j in sel) + fixed2
    def cst():
        return sum(cost_at(j, Ns[id(j)]) for j in sel)
    while tot() > target2:
        best, bv = None, -1
        for j in sel:
            if j.get('nodata'):
                continue
            n0 = Ns[id(j)]
            i = LADDER.index(n0) if n0 in LADDER else None
            if i is None or i + 1 >= len(LADDER):
                continue
            n1 = LADDER[i + 1]
            gain = var_at(j, n0) - var_at(j, n1)
            dc = max(cost_at(j, n1) - cost_at(j, n0), 1e-9)
            if gain / dc > bv:
                best, bv = j, gain / dc
        if best is None or bv <= 0:
            break
        if budget is not None and cst() + cost_at(best, LADDER[LADDER.index(Ns[id(best)]) + 1]) - \
                cost_at(best, Ns[id(best)]) > budget:
            break
        Ns[id(best)] = LADDER[LADDER.index(Ns[id(best)]) + 1]
    return Ns, math.sqrt(max(tot() - fixed2, 0.0)), cst()


def neyman_gain(persec, alpha):
    """cost(sector-adaptive N) / cost(uniform N) for the same variance, from per-sector variances v_s and cpu t_s of
    a reference run (optimal N_s ~ (v_s/t_s)^(1/(2 alpha+1))):  (sum a)^(1+1/2alpha) / ((sum v)^(1/2alpha) sum t),
    a_s = t_s^(2alpha/(2alpha+1)) v_s^(1/(2alpha+1)).  The sample of sectors is taken as representative."""
    ps = [(v, t) for v, t in persec if t > 0]
    if not ps or sum(v for v, _ in ps) <= 0:
        return None
    e = 2 * alpha
    a = sum(t ** (e / (e + 1)) * v ** (1 / (e + 1)) for v, t in ps)
    return a ** (1 + 1 / e) / (sum(v for v, _ in ps) ** (1 / e) * sum(t for _, t in ps))


def makespan(rows, nodes=8):
    """wall hours of the cfgs (chunks) of `rows` on `nodes` whole 64-core nodes, longest first (LPT)"""
    tasks = []
    for r in rows:
        tasks += [r['core_h'] / r['chunks'] / CORES] * r['chunks']
    load = [0.0] * nodes
    for t in sorted(tasks, reverse=True):
        i = load.index(min(load))
        load[i] += t
    return max(load) if tasks else 0.0, max(tasks) if tasks else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', action='append', required=True)
    ap.add_argument('--speed', type=float, default=1.0)
    ap.add_argument('--alpha7', type=float, default=None, help='7D convergence rate (scenario)')
    ap.add_argument('--alpha6', type=float, default=None, help='6D convergence rate (scenario)')
    ap.add_argument('--rate-min-N', type=int, default=4001,
                    help='use a measured convergence rate only if the smaller pilot N is >= this')
    ap.add_argument('--TA', type=float, default=1e-4)
    ap.add_argument('--TA-best', type=float, default=1e-6)
    ap.add_argument('--A-budget', type=float, default=200.0)
    ap.add_argument('--T', type=float, default=0.01, help='tier C: total sigma(C8)')
    ap.add_argument('--TB', type=float, default=0.005,
                    help='tier B: sigma of C8 without the J9 term (leaves sqrt(T^2-TB^2) for tier C)')
    ap.add_argument('--alt-B', default='0.001,0.0025,0.01')
    ap.add_argument('--alt', default='0.003,0.03,0.1')
    ap.add_argument('--node-hours-per-cfg', type=float, default=3.0)
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'plan_C8'))
    ap.add_argument('--src-speed', action='append', default=[], help='DIR=F: speed factor of one source')
    ap.add_argument('--lower-ref', choices=['last', 'largest'], default='last',
                    help='smaller-N reference for the measured rate: last listed (default, phase-3 plans) or largest N')
    ap.add_argument('--n-floor', choices=['ref', 'lower'], default='ref',
                    help="smallest N of a job: the reference size (default) or, when a measured rate between the lower "
                         "reference (>= --rate-min-N) and the reference exists, the lower reference size (re-plans from "
                         "a probe at production N, which may then lower N to fit a budget)")
    ap.add_argument('--budget-BC', type=float, default=None, help='cap for tiers B + C (production core-hours)')
    ap.add_argument('--budget-priority', choices=['equal', 'B', 'C'], default='equal',
                    help='under --budget-BC: relax both targets by one factor (equal), or keep B (C) and relax the '
                         'other tier first')
    a = ap.parse_args()
    global LOWER_REF, N_FLOOR
    LOWER_REF = a.lower_ref
    N_FLOOR = a.n_floor
    if a.alpha7:
        ALPHA[7] = a.alpha7
    if a.alpha6:
        ALPHA[6] = a.alpha6
    src_speed = {os.path.abspath(x.split('=')[0]): float(x.split('=')[1]) for x in a.src_speed}
    prod, G, refs = load_refs([os.path.abspath(s) for s in a.src], src_speed)
    jobs = model(prod, refs, a.speed, a.rate_min_N)
    nodata = [f"{j['group']} k={j['k']}" for j in jobs if j.get('nodata')]
    if nodata:
        print('WARNING: no pilot data (not in the error budget):', nodata, file=sys.stderr)
    A = [j for j in jobs if j['tier'] == 'A']
    BC = [j for j in jobs if j['tier'] in 'BC']
    # tier A: mandatory target, then best affordable
    NA1, sA1, cA1 = greedy(jobs, A, a.TA ** 2)
    NA, sA, cA = greedy(jobs, A, a.TA_best ** 2, budget=max(a.A_budget, cA1))
    if sA > a.TA:
        NA, sA, cA = NA1, sA1, cA1
    curveA = []
    for TA in (1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7):
        _, sx, cx = greedy(jobs, A, TA ** 2)
        curveA.append({'target': TA, 'sigma': sx, 'core_h': cx, 'reached': sx <= TA * 1.0001})
    for j in A:
        j['N'] = NA[id(j)]
    # tier B on its own: C8 without the J9 term (C8_partial) to sigma <= TB, leaving room for tier C
    B = [j for j in jobs if j['tier'] == 'B']
    C = [j for j in jobs if j['tier'] == 'C']
    fixedA = sA ** 2 + SIGMA_BOLD ** 2
    budget = None
    if a.budget_BC is not None:
        # cap for tiers B + C: relax the targets (TB -> fB TB, T -> fC T) by the first factor pair, in the order of
        # --budget-priority, whose greedy plan fits in the cap (the cheapest-first ladder of the greedy allocation)
        grid = [1.05 ** i for i in range(0, 95)]                  # 1 ... ~100
        if a.budget_priority == 'equal':
            pairs = [(f, f) for f in grid]
        elif a.budget_priority == 'B':
            pairs = [(1.0, f) for f in grid] + [(f, grid[-1]) for f in grid[1:]]
        else:
            pairs = [(f, 1.0) for f in grid] + [(grid[-1], f) for f in grid[1:]]
        chosen = None
        for fB, fC in pairs:
            _, sBx, cBx = greedy(jobs, B, (fB * a.TB) ** 2, fixed2=fixedA)
            _, sCx, cCx = greedy(jobs, C, (fC * a.T) ** 2, fixed2=fixedA + sBx ** 2)
            if cBx + cCx <= a.budget_BC:
                chosen = (fB, fC, cBx, cCx)
                break
        budget = {'cap_BC': a.budget_BC, 'priority': a.budget_priority, 'TB_requested': a.TB, 'T_requested': a.T,
                  'fits': chosen is not None}
        if chosen is None:
            print(f'WARNING: even the relaxed targets (factor {grid[-1]:.0f}) exceed --budget-BC {a.budget_BC}',
                  file=sys.stderr)
        else:
            budget.update({'fB': chosen[0], 'fC': chosen[1], 'cost_B': chosen[2], 'cost_C': chosen[3]})
            a.TB, a.T = chosen[0] * a.TB, chosen[1] * a.T
            budget.update({'TB_used': a.TB, 'T_used': a.T})
    NB, sB, cB = greedy(jobs, B, a.TB ** 2, fixed2=fixedA)
    for j in B:
        j['N'] = NB[id(j)]
    # tier C on top of A and B: the full C8 to sigma <= T (main) and the alternatives
    plans = {}
    for T in [a.T] + [float(x) for x in a.alt.split(',') if x]:
        NC, sC, cC = greedy(jobs, C, T ** 2, fixed2=fixedA + sB ** 2)
        plans[T] = {'N': {**{f"{j['group']}|{j['k']}": NB[id(j)] for j in B},
                          **{f"{j['group']}|{j['k']}": NC[id(j)] for j in C}},
                    'sigma_B': sB, 'sigma_C': sC, 'cost_B': cB, 'cost_C': cC,
                    'reached': math.sqrt(sC ** 2 + fixedA + sB ** 2) <= T * 1.0001}
    # tier B alternatives (C8_partial)
    altB = []
    for TBx in [float(x) for x in a.alt_B.split(',') if x]:
        _, sBx, cBx = greedy(jobs, B, TBx ** 2, fixed2=fixedA)
        altB.append({'target': TBx, 'sigma_B': sBx, 'core_h': cBx})
    main_plan = plans[a.T]
    rows = []
    for j in jobs:
        N = j['N'] if j['tier'] == 'A' else main_plan['N'][f"{j['group']}|{j['k']}"]
        ch = 1
        if not j.get('nodata'):
            ch = max(1, min(j['sectors'], math.ceil(cost_at(j, N) / CORES / a.node_hours_per_cfg)))
        r = {'group': j['group'], 'k': j['k'], 'tier': j['tier'], 'dim': j['dim'], 'sectors': j['sectors'],
             'jmin': j['jmin'], 'coeffs': j['coeffs'], 'grad_C8': j['grad'], 'N': N, 'shifts': SHIFTS, 'chunks': ch,
             'core_h': cost_at(j, N), 'sigma_C8': math.sqrt(var_at(j, N)), 'nodata': bool(j.get('nodata'))}
        if not j.get('nodata'):
            g = neyman_gain(j['ref'].get('persec', []), j['alpha'])
            top = sorted((v for v, _ in j['ref'].get('persec', [])), reverse=True)
            r['neyman_cost_factor'] = g
            r['variance_share_top3_sectors'] = (sum(top[:3]) / sum(top)) if top and sum(top) > 0 else None
            r.update({'ref': {kk: vv for kk, vv in j['ref'].items() if kk != 'persec'}, 'alpha': j['alpha'],
                      'alpha_meas': j['alpha_meas'],
                      'sigma_C8_at_ref_full': math.sqrt(j['var_ref'] + j['floor2'])})
        rows.append(r)
    jN = {(j['group'], j['k']): (j, (j['N'] if j['tier'] == 'A' else main_plan['N'][f"{j['group']}|{j['k']}"]))
          for j in jobs}
    sig_in = {o: math.sqrt(sum(var_in_at(j, N, o) for j, N in jN.values())) for o in INPUTS_NEW}
    tiers = {}
    for t in 'ABC':
        rr = [r for r in rows if r['tier'] == t]
        wall, longest = makespan(rr)
        tiers[t] = {'core_h': sum(r['core_h'] for r in rr), 'sigma_C8': math.sqrt(sum(r['sigma_C8'] ** 2 for r in rr)),
                    'n_jobs': len(rr), 'n_cfgs': sum(r['chunks'] for r in rr), 'wall_h_8_nodes': wall,
                    'longest_cfg_node_h': longest}
    out = {'note': 'C8 production plan (py/plan_C8.py); costs in production (symmetry amdq) core-hours via --speed',
           'tiers': tiers,
           'sigma_inputs_main_plan': sig_in,
           'speed': a.speed, 'sources': a.src, 'sigma_B_old': SIGMA_BOLD,
           'tierA': {'sigma': sA, 'core_h': cA, 'target': a.TA, 'best_target': a.TA_best, 'budget': a.A_budget,
                     'mandatory_plan': {'sigma': sA1, 'core_h': cA1}, 'curve': curveA},
           'tierB': {'sigma': sB, 'core_h': cB, 'target': a.TB, 'alternatives': altB},
           **({'budget_BC': budget} if budget is not None else {}),
           'tierC_by_target': {str(T): {k: v for k, v in p.items() if k != 'N'} | {'N': p['N']} for T, p in plans.items()},
           'jobs': rows, 'nodata': nodata}
    json.dump(out, open(a.out + '.json', 'w'), indent=1)
    L = ['# C8 production plan (py/plan_C8.py)', '',
         f'Pilot sources: {", ".join(a.src)}; costs in production core-hours (speed factor {a.speed}). Error model: '
         'replicate and sector-pooled projections of each job on the signed dC8/dx (the larger), scaled by sector '
         'stride and (N/N_ref)^-alpha, plus the floor. Greedy lattice allocation on the prime ladder.', '',
         f"**Tier A** (W, S, L3, M21, M12, N2, Ndelta): sigma(C8 contribution) = {sA:.2e}, {cA:.1f} core-h "
         f"(the mandatory 1e-4 target alone: {sA1:.1e}, {cA1:.1f} core-h).", '']
    if budget is not None:
        L.append(f"**Budget (tiers B + C <= {budget['cap_BC']:.0f} core-h, priority {budget['priority']}):** "
                 + (f"targets relaxed by fB = {budget['fB']:.3g}, fC = {budget['fC']:.3g} to TB = {budget['TB_used']:.4g}, "
                    f"T = {budget['T_used']:.4g} (cost B {budget['cost_B']:.0f} + C {budget['cost_C']:.0f})"
                    if budget['fits'] else 'NOT REACHABLE even with the targets relaxed 100x'))
        L.append('')
    L.append('Tier-A cost curve: ' + '; '.join(f"{c['target']:.0e}: {c['core_h']:.1f} core-h"
                                             + ('' if c['reached'] else ' (not reached)') for c in curveA))
    L.append('')
    for t, v in tiers.items():
        L.append(f"* tier {t}: {v['n_jobs']} jobs, {v['n_cfgs']} cfgs, {v['core_h']:.1f} core-h, sigma(C8 part) "
                 f"{v['sigma_C8']:.2e}, wall on 8 amdq nodes {v['wall_h_8_nodes']:.2f} h (longest cfg "
                 f"{v['longest_cfg_node_h']:.2f} node-h)")
    L.append('Predicted sigma of the new inputs (main plan; engine scalars only): ' +
             ', '.join(f'{o} {v:.1e}' for o, v in sig_in.items()))
    L.append('')
    L.append('Tier-B alternatives (sigma of C8 without J9): ' + '; '.join(
        f"{x['target']:g}: sigma {x['sigma_B']:.1e}, {x['core_h']:.0f} core-h" for x in altB))
    L.append('')
    for T, p in plans.items():
        tot = math.sqrt(sA ** 2 + SIGMA_BOLD ** 2 + p['sigma_B'] ** 2 + p['sigma_C'] ** 2)
        L.append(f"* target sigma(C8) = {T:g}: tier B sigma {p['sigma_B']:.2e} ({p['cost_B']:.0f} core-h), tier C sigma "
                 f"{p['sigma_C']:.2e} ({p['cost_C']:.0f} core-h); total sigma(C8) {tot:.2e}, total cost "
                 f"{cA + p['cost_B'] + p['cost_C']:.0f} core-h{'' if p['reached'] else ' (TARGET NOT REACHED on the ladder)'}")
    L += ['', '| group | k | tier | d | sectors | jmin | ref (src, N, stride) | alpha (meas.) | us/pt | sigma_C8 @ref (full) | N | chunks | core-h | sigma_C8 | top-3 sector share | Neyman cost factor |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (-r['core_h'])):
        if r['nodata']:
            L.append(f"| {r['group']} | {r['k']} | {r['tier']} | {r['dim']} | {r['sectors']} | {r['jmin']} | NO DATA |||||||")
            continue
        ref = r['ref']
        L.append(f"| {r['group']} | {r['k']} | {r['tier']} | {r['dim']} | {r['sectors']} | {r['jmin']} | "
                 f"{os.path.basename(ref['src'])} {ref['N']} /{ref['stride']} | {r['alpha']:.2f} "
                 f"({'-' if r['alpha_meas'] is None else '%.2f' % r['alpha_meas']}) | {ref['us_pt']:.0f} | "
                 f"{r['sigma_C8_at_ref_full']:.1e} | {r['N']} | {r['chunks']} | {r['core_h']:.1f} | {r['sigma_C8']:.1e} | "
                 f"{'-' if r['variance_share_top3_sectors'] is None else '%.2f' % r['variance_share_top3_sectors']} | "
                 f"{'-' if r['neyman_cost_factor'] is None else '%.2f' % r['neyman_cost_factor']} |")
    open(a.out + '.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(l for l in L if not l.startswith('|')))


if __name__ == '__main__':
    main()
