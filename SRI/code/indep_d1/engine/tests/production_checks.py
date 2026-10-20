#!/usr/bin/env python3
"""Production run health checks and an independent error cross-check (tier 1, 2026-10-03).

usage: production_checks.py RUNDIR [--json OUT.json] [--grad specs/gradients_C6_C7_D4.json]

1. Per cfg of the manifest (chunks and refinement cfgs):
   completion marker, N, shifts, sector range, wall and cpu seconds, threads, host(s) (header lines of
   <cfg>.log written by slurm/run_list.sh), non-finite numbers anywhere in the output JSON, and the engine's
   WARN lines ('WARN sector S shift R: k of n points above the precision target after tails'): number of
   (sector, shift) tasks with a warning, warned points, warned fraction of all points of the cfg
   (sectors x shifts x N), worst task.  Every other stderr line (not WARN / '===' header / 'sector sample')
   is reported as UNEXPECTED.  README acceptance criterion 5 asks for a warned fraction below 1%.
2. Per needed coefficient (manifest 'need'; refined sectors substituted exactly as campaign.py collect does):
   the replicate error E_rep = sd_r(sum_s x_sr)/sqrt(R) and the sector-pooled error
   E_pool = sqrt(sum_s var_r(x_sr)/R) (hundreds of degrees of freedom; gate-review recommendation (i)),
   their ratio, and the coefficient's weight sens*E_rep with sens = max(|dC6/dx|, |dC7/dx|).
3. Per job (moment, k) and for C6, C7: the same two estimators applied to the job's projection
   D_sr = sum_i dC/dx_i x_{i,s,r} on the signed gradients (exact correlations inside the job), and their sums
   over the independent jobs: sigma_rep_proj (= the statistical part of sigma_cov of tests/e2e_framework.py, up
   to the gradient point) and sigma_pool_proj (sector-pooled, many degrees of freedom).
Exit status 1 if an output is missing/incomplete, holds a non-finite number, or a log has UNEXPECTED lines.
"""
import argparse, json, math, os, re, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'py'))
from lri_moments import coefficient_map
from campaign import decode_job, ROOT

WARN_RE = re.compile(r'^WARN sector (\d+) shift (\d+): (\d+) of (\d+) points above the precision target after tails$')


def nonfinite(x, path='', out=None):
    out = [] if out is None else out
    if isinstance(x, float):
        if not math.isfinite(x):
            out.append(path)
    elif isinstance(x, dict):
        for k, v in x.items():
            nonfinite(v, f'{path}.{k}', out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            nonfinite(v, f'{path}[{i}]', out)
    return out


def load_sens(path):
    g = json.load(open(path))
    g = g.get('gradients', g)
    return {nm: max(abs(float(g.get('C6', {}).get(nm, 0))), abs(float(g.get('C7', {}).get(nm, 0))))
            for nm in set(g.get('C6', {})) | set(g.get('C7', {}))}


def load_grad(path):
    g = json.load(open(path))
    g = g.get('gradients', g)
    return {o: {nm: float(v) for nm, v in g.get(o, {}).items()} for o in ('C6', 'C7')}


def raw_name(group, k, j):
    return f"{re.sub(r'_N[0-9]+$', '', group).replace('_base', '')}[eps^{k} l^{j}]"


def cfg_health(rundir, cfg):
    p = os.path.join(rundir, cfg + '.json')
    h = {'cfg': cfg, 'ok': True}
    if not os.path.exists(p):
        h.update(ok=False, problem='missing output')
        return h, None
    r = json.load(open(p))
    if not r.get('complete', False):
        h.update(ok=False, problem='output without "complete": true')
    nf = nonfinite(r)
    if nf:
        h.update(ok=False, problem=f'{len(nf)} non-finite numbers, e.g. {nf[:3]}')
    s0, s1 = r['sector_range']
    npts = (s1 - s0) * r['shifts'] * r['N']
    h.update(N=r['N'], shifts=r['shifts'], sectors=[s0, s1], wall_s=r['wall_seconds'], cpu_s=r['cpu_seconds'],
             threads=r['threads'], points=npts, nonfinite=len(nf))
    warned, wpts, worst, hosts, unexpected = 0, 0, None, [], []
    lp = os.path.join(rundir, cfg + '.log')
    if os.path.exists(lp):
        for line in open(lp):
            line = line.rstrip('\n')
            if not line.strip():
                continue
            m = WARN_RE.match(line)
            if m:
                k, n = int(m.group(3)), int(m.group(4))
                warned += 1
                wpts += k
                if worst is None or k / n > worst[0]:
                    worst = (k / n, int(m.group(1)), int(m.group(2)), k, n)
            elif line.startswith('=== '):
                hosts.append(' '.join(line.split()[1:]))
            elif line.startswith('sector sample:'):
                pass
            else:
                unexpected.append(line)
    else:
        unexpected.append('(no log file)')
    h.update(warn_tasks=warned, warn_points=wpts, warn_frac=wpts / npts if npts else 0.0,
             worst_task=None if worst is None else {'frac': worst[0], 'sector': worst[1], 'shift': worst[2],
                                                    'points': worst[3], 'of': worst[4]},
             runs=hosts, unexpected=unexpected[:20], n_unexpected=len(unexpected))
    if unexpected:
        h['ok'] = False
        h.setdefault('problem', f'{len(unexpected)} unexpected log lines')
    return h, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rundir')
    ap.add_argument('--json')
    ap.add_argument('--grad', default=os.path.join(ROOT, 'specs', 'gradients_C6_C7_D4.json'))
    a = ap.parse_args()
    sens = load_sens(a.grad)
    grad = load_grad(a.grad)
    proj = []
    manifest = json.load(open(os.path.join(a.rundir, 'manifest.json')))
    health, coeffs, bad = [], [], 0
    tot_cpu = tot_wall = 0.0
    for m in manifest:
        job = decode_job(m['job'])
        k = job['k']
        refined = {}
        for x in m.get('refine', []):
            refined[x['sector']] = x['cfg']          # latest refinement of a sector wins (as in collect)
        outs = {}
        for c in m['cfgs'] + [x['cfg'] for x in m.get('refine', [])]:
            h, r = cfg_health(a.rundir, c)
            h['moment'], h['k'] = m['moment'], k
            health.append(h)
            bad += not h['ok']
            tot_cpu += h.get('cpu_s', 0.0)
            tot_wall += h.get('wall_s', 0.0)
            outs[c] = r
        need = m.get('need') or []
        if not need or any(outs[c] is None for c in m['cfgs']):
            continue
        persec = {}
        for cfg, only in [(c, None) for c in m['cfgs']] + [(c, s) for s, c in refined.items()]:
            r = outs.get(cfg)
            if r is None:
                continue
            orders = {c: ch['orders'] for c, ch in r['channels'].items()}
            cmap, _ = coefficient_map(job, orders)
            chans = r['channels']
            first = next(iter(chans.values()))
            for i, sec in enumerate(first['per_sector']):
                sid = sec['id']
                if (only is None and sid in refined) or (only is not None and sid != only):
                    continue
                R = len(sec['rep'])
                vals = {}
                for jj in need:
                    lst = cmap.get((k, jj))
                    if not lst:
                        continue
                    x = [0.0] * R
                    for c, o2, w in lst:
                        io = orders[c].index(o2)
                        rep = chans[c]['per_sector'][i]['rep']
                        for t in range(R):
                            x[t] += w * rep[t][io]
                    vals[jj] = x
                persec[sid] = vals
        if persec:
            R = len(next(iter(next(iter(persec.values())).values()), [0, 0]))
            pj = {'moment': m['moment'], 'k': k}
            for o in ('C6', 'C7'):
                Ds = []
                for v in persec.values():
                    Ds.append([sum(grad[o].get(raw_name(m['moment'], k, jj), 0.0) * x[t] for jj, x in v.items())
                               for t in range(R)])
                tot = [sum(x[t] for x in Ds) for t in range(R)]
                pj[f'{o}_rep'] = st.stdev(tot) / math.sqrt(R) if R > 1 else 0.0
                pj[f'{o}_pool'] = math.sqrt(sum(st.variance(x) for x in Ds) / R) if R > 1 else 0.0
            proj.append(pj)
        for jj in need:
            secs = [v[jj] for v in persec.values() if jj in v]
            if not secs:
                continue
            R = len(secs[0])
            tot = [sum(x[t] for x in secs) for t in range(R)]
            E = st.stdev(tot) / math.sqrt(R)
            Ep = math.sqrt(sum(st.variance(x) for x in secs) / R)
            nm = raw_name(m['moment'], k, jj)
            coeffs.append({'coef': nm, 'moment': m['moment'], 'k': k, 'j': jj, 'R': R, 'nsec': len(secs),
                           'E_rep': E, 'E_pool': Ep, 'ratio': E / Ep if Ep > 0 else None,
                           'sens': sens.get(nm, 0.0), 'weight': sens.get(nm, 0.0) * E})
    # report
    print(f'{len(health)} cfg outputs; {bad} with problems; total engine cpu {tot_cpu / 3600:.1f} core-h, '
          f'summed wall {tot_wall / 3600:.2f} h')
    for h in health:
        if not h['ok']:
            print(f"PROBLEM {h['cfg']}: {h.get('problem')}  {h.get('unexpected', [])[:3]}")
    print('%-28s %9s %4s %11s %9s %8s %7s %10s %10s %s' % ('cfg', 'N', 'R', 'sectors', 'wall_s', 'cpu_h',
                                                           'thr', 'warn_tasks', 'warn_frac', 'worst task'))
    for h in sorted(health, key=lambda h: -h.get('cpu_s', 0)):
        w = h.get('worst_task')
        print('%-28s %9s %4s %11s %9.0f %8.2f %7s %10d %10.2e %s' % (
            h['cfg'], h.get('N'), h.get('shifts'), h.get('sectors'), h.get('wall_s', 0), h.get('cpu_s', 0) / 3600,
            h.get('threads'), h.get('warn_tasks', 0), h.get('warn_frac', 0),
            '' if w is None else f"sector {w['sector']} shift {w['shift']}: {w['points']}/{w['of']} = {w['frac']:.2e}"))
    maxfrac = max((h.get('warn_frac', 0) for h in health), default=0)
    allw = sum(h.get('warn_points', 0) for h in health)
    allp = sum(h.get('points', 0) for h in health)
    print(f'WARN: max warned fraction per cfg {maxfrac:.2e}; overall {allw}/{allp} = {allw / max(allp, 1):.2e} '
          f'(criterion 5: < 1e-2)')
    print('\nneeded coefficients: replicate vs sector-pooled error (gate-review cross-check (i))')
    print('%-24s %5s %4s %11s %11s %7s %10s' % ('coefficient', 'nsec', 'R', 'E_rep', 'E_pool', 'ratio', 'sens*E'))
    for c in sorted(coeffs, key=lambda c: -c['weight']):
        print('%-24s %5d %4d %11.3e %11.3e %7s %10.2e' % (c['coef'], c['nsec'], c['R'], c['E_rep'], c['E_pool'],
                                                        'n/a' if c['ratio'] is None else f"{c['ratio']:.2f}",
                                                        c['weight']))
    rats = [c['ratio'] for c in coeffs if c['ratio'] is not None and c['nsec'] >= 10]
    if rats:
        print(f'ratio E_rep/E_pool over {len(rats)} coefficients with >= 10 sectors: median {st.median(rats):.2f}, '
              f'rms {math.sqrt(sum(x * x for x in rats) / len(rats)):.2f}, min {min(rats):.2f}, max {max(rats):.2f}')
    print('\nprojection on C6, C7 per job (signed gradients ' + os.path.relpath(a.grad, ROOT) + '): replicate vs '
          'sector-pooled error')
    print('%-14s %3s %11s %11s %11s %11s' % ('job', 'k', 'C6 rep', 'C6 pool', 'C7 rep', 'C7 pool'))
    for pj in sorted(proj, key=lambda x: -max(x['C7_rep'], x['C7_pool'], x['C6_rep'], x['C6_pool'])):
        if max(pj['C7_rep'], pj['C7_pool'], pj['C6_rep'], pj['C6_pool']) < 1e-7:
            continue
        print('%-14s %3d %11.3e %11.3e %11.3e %11.3e' % (pj['moment'], pj['k'], pj['C6_rep'], pj['C6_pool'],
                                                         pj['C7_rep'], pj['C7_pool']))
    tot_proj = {}
    for o in ('C6', 'C7'):
        for e in ('rep', 'pool'):
            tot_proj[f'{o}_{e}'] = math.sqrt(sum(pj[f'{o}_{e}'] ** 2 for pj in proj))
    print('sum over jobs (statistical only): sigma(C6) rep %.3e pool %.3e; sigma(C7) rep %.3e pool %.3e' % (
        tot_proj['C6_rep'], tot_proj['C6_pool'], tot_proj['C7_rep'], tot_proj['C7_pool']))
    if a.json:
        with open(a.json + '.tmp', 'w') as f:
            json.dump({'rundir': os.path.abspath(a.rundir), 'cfgs': health, 'coefficients': coeffs,
                       'projections': proj, 'sigma_proj': tot_proj,
                       'total_cpu_core_hours': tot_cpu / 3600, 'warn_max_frac': maxfrac,
                       'warn_overall_frac': allw / max(allp, 1), 'n_problems': bad}, f, indent=1)
        os.replace(a.json + '.tmp', a.json)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
