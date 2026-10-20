#!/usr/bin/env python3
"""Batch front end for cluster runs of the engine (v2, 2026-10-03).

  campaign.py plan      <spec.json> <rundir> [--tier T] [--force]
        one engine cfg per (moment, eps power, sector chunk) + manifest.json + cfglist.txt (longest first).
        * seeds: hash of (tier, moment, k, chunk) -> no two cfgs of a campaign, and no two tiers, share shifts
          (checked with `seedcheck`); an explicit "seed" in a moment entry is honoured only for replays.
        * chunks: contiguous sector ranges of equal ESTIMATED cost (engine --sectors-info), not equal counts.
        * refuses to re-plan a run directory that already holds outputs (restart safety; --force overrides).
  campaign.py collect   <rundir> [--floor F] [--partial] [--need specs/production_D4.json]
        merge the per-shift replicates of all chunks (and refined sectors), assemble every eps^k log^j
        coefficient PER REPLICATE, write results.json (atomic): value, err = stat (+) floor, the replicate
        values themselves, covariance blocks, explicit structural zeros.  Exit status 2 if any output or any
        needed coefficient is missing (unless --partial).
  campaign.py refine    <rundir> <flags.json> [--factor 4] [--transform r]
        extra cfgs for flagged sectors (py/outliers.py --json) at >= factor x N with fresh seeds; collect
        substitutes them per replicate.
  campaign.py seedcheck <rundir> [<rundir> ...]
        verify that no two (cfg, sector, shift) triples of the given campaigns use overlapping random streams.

spec.json:  {"tier": "6digit", "defaults": {"N":..., "shifts":..., "transform":3, "prec":"auto", "chunks":1},
             "moments": [{"name":"Q8_base","kind":"Q","n":8,"nv":0,"nd":0,"ne":0,"powers":[0],"jmin":1,
                          "coeffs": {"0": [1]}, "N":..., "chunks":..., "sectors":[a,b] (optional)}, ...]}
Each cfg is run as   lri_engine <cfg>   (writes <cfg>.json atomically).  See ../slurm/ for the Slurm wrappers.
"""
import argparse, glob, hashlib, json, math, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lri_moments import (plan_moment, job_cfg, assemble_job, merge_outputs, merge_replicates, assemble_replicates,
                         korobov, next_prime, atomic_write_json, atomic_write_text, ENGINE, FLOOR_REL)
from fractions import Fraction
from math import factorial

ROOT = os.path.dirname(HERE)
MASK = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15     # splitmix64 increment (engine)
SEED_A, SEED_B = 0x1234567, 0x9876543   # engine: st = seed ^ A*(sector+1) ^ B*(shift+1)


def nsectors(n, geom):
    M = n + 1 if geom == 'full' else n - 1
    return factorial(M) // 2 if M >= 2 else 1


def seed_for(tier, name, k, chunk):
    h = hashlib.sha256(f'lri-engine-v2|{tier}|{name}|k={k}|c={chunk}'.encode()).digest()
    return int.from_bytes(h[:8], 'little') & ((1 << 63) - 1)


def encode_job(job):
    jj = dict(job)
    jj['pre'] = [(j, {str(k): str(v) for k, v in pr.items()}) for j, pr in job['pre']]
    jj['chans'] = [(nm, [(t[0], t[1], str(t[2])) for t in terms]) for nm, terms in job['chans']]
    return jj


def decode_job(jj):
    job = dict(jj)
    job['pre'] = [(j, {int(k): Fraction(v) for k, v in pr.items()}) for j, pr in jj['pre']]
    return job


def sector_costs(job, extra):
    """estimated relative cost per sector (engine --sectors-info; no lattice needed)"""
    cfg = job_cfg(job, N=1, shifts=1, korobov_a=1, extra=extra)
    fd, path = tempfile.mkstemp(suffix='.cfg', prefix='lri_info_')
    os.write(fd, cfg.encode())
    os.close(fd)
    try:
        r = subprocess.run([ENGINE, path, '--sectors-info'], capture_output=True, text=True, check=True)
    finally:
        os.remove(path)
    info = json.loads(r.stdout)
    return [s['est_cost'] for s in info['sectors']]


def balanced_bounds(costs, lo, hi, ch):
    """contiguous chunks of [lo,hi) with (nearly) equal summed estimated cost; every chunk non-empty"""
    import bisect
    ch = max(1, min(ch, hi - lo))
    cum = [0.0]
    for s in range(lo, hi):
        cum.append(cum[-1] + costs[s])
    tot = cum[-1]
    b = [lo]
    for i in range(1, ch):
        t = tot * i / ch
        j = bisect.bisect_left(cum, t)
        j = min(j, len(cum) - 1)
        if j > 0 and abs(cum[j - 1] - t) <= abs(cum[j] - t):
            j -= 1
        s = max(lo + j, b[-1] + 1)
        s = min(s, hi - (ch - i))
        b.append(s)
    b.append(hi)
    return b


def plan(specfile, rundir, tier=None, force=False):
    spec = json.load(open(specfile))
    tier = tier or spec.get('tier') or os.path.basename(os.path.normpath(rundir))
    dfl = spec.get('defaults', {})
    os.makedirs(rundir, exist_ok=True)
    if not force and (glob.glob(os.path.join(rundir, '*.cfg.json')) or os.path.exists(os.path.join(rundir, 'manifest.json'))):
        sys.exit(f'{rundir} already holds a manifest or outputs; refusing to re-plan (use --force only if you '
                 'really want to replace the cfgs; finished outputs would no longer match them)')
    manifest, allcfg = [], []
    for m in spec['moments']:
        o = dict(dfl)
        o.update(m)
        jobs = plan_moment(o['kind'], o['n'], o.get('nv', 0), o.get('nd', 0), o.get('ne', 0), o.get('powers', [0]),
                           o.get('geom'), o.get('jmin', 0))
        for job in jobs:
            costs = sector_costs(job, o.get('extra'))
            ns = len(costs)
            lo, hi = o.get('sectors', [0, ns])
            hi = min(hi, ns)
            bounds = balanced_bounds(costs, lo, hi, int(o.get('chunks', 1)))
            files, seeds, est = [], [], []
            for c in range(len(bounds) - 1):
                name = f"{o['name']}_k{job['k']}_c{c:03d}"
                if 'seed' in o and c == 0:
                    print(f"WARNING: explicit seed {o['seed']} for {o['name']} (replays only; seeds are normally "
                          "hashed from tier, group, k, chunk)")
                seed = int(o['seed']) if 'seed' in o else seed_for(tier, o['name'], job['k'], c)
                cfg = job_cfg(job, N=o['N'], shifts=o['shifts'], transform=o.get('transform', 3),
                              prec=o.get('prec', 'auto'), threads=0, seed=seed,
                              sectors=(bounds[c], bounds[c + 1]), extra=o.get('extra'))
                atomic_write_text(os.path.join(rundir, name + '.cfg'), cfg + f'out {name}.cfg.json\n')
                e = sum(costs[bounds[c]:bounds[c + 1]]) * o['N'] * o['shifts']
                files.append(name + '.cfg')
                seeds.append(seed)
                est.append(e)
                allcfg.append((e, name + '.cfg'))
            coeffs = o.get('coeffs')
            need = sorted(coeffs.get(str(job['k']), coeffs.get(job['k'], []))) if coeffs else None
            manifest.append({'moment': o['name'], 'job': encode_job(job), 'cfgs': files, 'seeds': seeds,
                             'est_cost': est, 'sectors': [lo, hi], 'bounds': bounds, 'nsec_total': ns,
                             'N': o['N'], 'shifts': o['shifts'], 'extra': o.get('extra'), 'tier': tier,
                             'need': need, 'refine': []})
    atomic_write_json(os.path.join(rundir, 'manifest.json'), manifest, indent=1)
    allcfg.sort(key=lambda x: -x[0])          # longest first: array task i runs the i-th most expensive cfg
    atomic_write_text(os.path.join(rundir, 'cfglist.txt'), ''.join(c + '\n' for _, c in allcfg))
    print(f'{len(allcfg)} cfgs written to {rundir} (tier {tier}); cfglist.txt is sorted by estimated cost')
    seedcheck([rundir])


# ------------------------------------------------------------------------------------------- seeds
def _cfg_streams(path):
    """(weyl index, d, label) of every (sector, shift) random stream used by one cfg"""
    kv = {}
    for line in open(path):
        p = line.split()
        if p and p[0] in ('n', 'geom', 'seed', 'shifts', 'sectors', 'sectorstride'):
            kv[p[0]] = p[1:]
    n = int(kv['n'][0])
    M = n + 1 if kv.get('geom', ['angular'])[0] == 'full' else n - 1
    d = M - 1
    if d <= 0:
        return []
    seed = int(kv.get('seed', ['1234567'])[0]) & MASK
    sh = int(kv.get('shifts', ['4'])[0])
    ns = factorial(M) // 2 if M >= 2 else 1
    if 'sectorstride' in kv:
        st_, off = int(kv['sectorstride'][0]), int(kv['sectorstride'][1]) if len(kv['sectorstride']) > 1 else 0
        ns = len([s for s in range(ns) if s % st_ == off])
    s0, s1 = (int(kv['sectors'][0]), int(kv['sectors'][1])) if 'sectors' in kv else (0, ns)
    s1 = ns if s1 < 0 else min(s1, ns)
    ginv = pow(GAMMA, -1, 1 << 64)
    out = []
    for s in range(max(0, s0), s1):
        for r in range(sh):
            st = seed ^ ((SEED_A * (s + 1)) & MASK) ^ ((SEED_B * (r + 1)) & MASK)
            out.append(((st * ginv) & MASK, d, f'{os.path.basename(path)} sector {s} shift {r}'))
    return out


def seedcheck(rundirs):
    streams = []
    for rd in rundirs:
        mf = os.path.join(rd, 'manifest.json')
        cfgs = []
        if os.path.exists(mf):
            for m in json.load(open(mf)):
                cfgs += m['cfgs'] + [x['cfg'] for x in m.get('refine', [])]
        else:
            cfgs = [os.path.basename(c) for c in glob.glob(os.path.join(rd, '*.cfg'))]
        for c in cfgs:
            streams += [(w, d, rd, lab) for w, d, lab in _cfg_streams(os.path.join(rd, c))]
    streams.sort()
    bad, cross = 0, 0
    for a, b in zip(streams, streams[1:] + streams[:1]):
        gap = (b[0] - a[0]) & MASK
        if gap < max(a[1], b[1]) and a is not b:
            bad += 1
            cross += a[2] != b[2]
            if bad <= 10:
                print(f'OVERLAP: {a[2]}/{a[3]}  <->  {b[2]}/{b[3]}')
    print(f'seedcheck: {len(streams)} random streams in {len(rundirs)} run dir(s): '
          + ('all disjoint' if bad == 0 else f'{bad} overlapping pairs ({cross} between different run dirs)'))
    return bad == 0


# ------------------------------------------------------------------------------------------- collect
def _need_lookup(need_file):
    if not need_file or not os.path.exists(need_file):
        return {}
    out = {}
    for g in json.load(open(need_file)):
        out[g['name']] = {int(p): js for p, js in g['coeffs'].items()}
    return out


def _load_out(rundir, cfg):
    p = os.path.join(rundir, cfg + '.json')
    if not os.path.exists(p):
        return None
    try:
        r = json.load(open(p))
    except ValueError:
        return None
    return r


def flat_name(group, key):
    """campaign group + 'k,j' -> the framework's raw name, e.g. ('A5_vE', '0,1') -> 'A5_vE[eps^0 l^1]'"""
    k, j = key.split(',')
    return f"{re.sub(r'_N[0-9]+$', '', group).replace('_base', '')}[eps^{k} l^{j}]"


def framework_input(out, needs, rundir):
    """canonical 'lri-framework-raw/1' input for ../framework (INPUT_FORMAT.md 3a): replicated scalars with
    their systematic floor ('sys') and replicate block (one block per independent job), exact zeros;
    restricted to the coefficients the production list needs when that list knows the group"""
    scal, Rs = {}, set()
    for grp, co in out['results'].items():
        base = re.sub(r'_N[0-9]+$', '', grp)
        need = needs.get(grp, needs.get(base))
        for key, (v, e) in co.items():
            k, j = (int(x) for x in key.split(','))
            if need is not None and j not in need.get(k, []):
                continue
            ex = out['errors'][grp][key]
            nm = flat_name(grp, key)
            if ex.get('zero'):
                scal[nm] = {'value': '0', 'sigma': '0', 'exact': True}
            else:
                reps = out['replicates'][grp][key]
                Rs.add(len(reps))
                scal[nm] = {'reps': [repr(x) for x in reps], 'mean': repr(v), 'sys': repr(ex['floor']),
                            'block': ex['block']}
    d = {'format': 'lri-framework-raw/1', 'convention': 'derivative',
         'producer': {'component': 'engine', 'run': os.path.abspath(rundir), 'floor_rel': out['floor_rel'],
                      'note': 'blocks = independent jobs (moment, eps power); seeds hashed per (tier, moment, k, chunk)'},
         'scalars': scal}
    if len(Rs) == 1:
        d['n_replicates'] = Rs.pop()
    return d


def collect(rundir, floor_rel=None, partial=False, need_file=None, legacy=False):
    floor_rel = FLOOR_REL if floor_rel is None else floor_rel
    manifest = json.load(open(os.path.join(rundir, 'manifest.json')))
    needs = _need_lookup(need_file or os.path.join(ROOT, 'specs', 'production_D4.json'))
    results, replicates, errors, zeros, blocks, costs, problems = {}, {}, {}, [], {}, {}, []
    for m in manifest:
        name = m['moment']
        job = decode_job(m['job'])
        k = job['k']
        outs, missing = [], []
        for c in m['cfgs']:
            r = _load_out(rundir, c)
            if r is None or (not legacy and not r.get('complete', False)):
                missing.append(c)
            else:
                outs.append(r)
        subs = []
        latest = {}
        for x in m.get('refine', []):
            latest[x['sector']] = x
        for sec, x in sorted(latest.items()):
            ref = _load_out(rundir, x['cfg'])
            orig = _load_out(rundir, x['orig_cfg'])
            if ref is None or not ref.get('complete', False) or orig is None:
                missing.append(x['cfg'])
            else:
                subs.append((orig, sec, ref))
        if missing:
            problems.append(f'{name} k={k}: missing {len(missing)} outputs: {missing[:4]}')
            continue
        need = m.get('need')
        if need is None:
            base = re.sub(r'_N\d+$', '', name)
            need = needs.get(name, needs.get(base, {})).get(k)
        res = results.setdefault(name, {})
        if legacy:
            tmp = {}
            assemble_job(job, merge_outputs(outs), tmp)
            for (kk, j), v in tmp.items():
                res[f'{kk},{j}'] = list(v)
            continue
        merged = merge_replicates(outs, subs)
        try:
            coeffs = assemble_replicates(job, merged, floor_rel, need)
        except ValueError as e:
            problems.append(str(e))
            continue
        bid = f'{name}|k={k}'
        blocks[bid] = {'R': merged['R'], 'keys': []}
        for (kk, j), v in sorted(coeffs.items()):
            key = f'{kk},{j}'
            res[key] = [v['value'], v['err']]
            errors.setdefault(name, {})[key] = {'stat': v['stat'], 'floor': v['floor'], 'l1': v['l1'],
                                                'block': bid, 'zero': v['zero']}
            if v['zero']:
                zeros.append(flat_name(name, key))       # exact structural zero: no replicates
            else:
                replicates.setdefault(name, {})[key] = v['reps']
                blocks[bid]['keys'].append(f'{name}:{key}')
        c = costs.setdefault(name, {'cpu_seconds': 0.0})
        c['cpu_seconds'] += merged['cpu_seconds']
        c['N'] = outs[0]['N']
        c['shifts'] = outs[0]['shifts']
        c['sectors_done'] = m['sectors'][1] - m['sectors'][0]
        c['sectors_total'] = m['nsec_total']
        c.setdefault('refined_sectors', {})[str(k)] = sorted(latest)
        c.setdefault('laurent', {})[str(k)] = {
            ch: {'orders': sorted(v['rep']), 'R': merged['R']} for ch, v in merged['channels'].items()}
    out = {'engine_pipeline': 'v2', 'floor_rel': floor_rel, 'complete': not problems, 'problems': problems,
           'results': results, 'replicates': replicates, 'errors': errors, 'blocks': blocks,
           'zeros': zeros, 'costs': costs}
    atomic_write_json(os.path.join(rundir, 'results.json'), out, indent=1)
    atomic_write_json(os.path.join(rundir, 'framework_input.json'),
                      framework_input(out, needs, rundir), indent=1)
    for name in results:
        print(name, '%.0f cpu-s' % costs.get(name, {}).get('cpu_seconds', 0))
        for key in sorted(results[name], key=lambda s: tuple(int(x) for x in s.split(','))):
            v, e = results[name][key]
            ex = errors.get(name, {}).get(key, {})
            print('   eps^%s log^%s : %.15g +- %.2g' % (*key.split(','), v, e)
                  + ('   (stat %.2g, floor %.2g)' % (ex['stat'], ex['floor']) if ex else '')
                  + ('   STRUCTURAL ZERO' if flat_name(name, key) in zeros else ''))
    for p in problems:
        print('PROBLEM:', p)
    if problems and not partial:
        sys.exit(2)


# ------------------------------------------------------------------------------------------- refine
LADDER = [1009, 4001, 16001, 32003, 64007, 131071, 262139, 524287, 1048573, 2097143, 4194301]


def refine(rundir, flags_file, factor=4, transform=None, include_minor=False):
    manifest = json.load(open(os.path.join(rundir, 'manifest.json')))
    flags = json.load(open(flags_file))
    flags = flags.get('flagged', flags) if isinstance(flags, dict) else flags
    if not include_minor:
        flags = [f for f in flags if f.get('relevant', True)]
    seen = set()
    flags = [f for f in flags if not ((f['moment'], f['k'], int(f['sector'])) in seen
                                      or seen.add((f['moment'], f['k'], int(f['sector']))))]
    new = []
    for f in flags:
        m = next(x for x in manifest if x['moment'] == f['moment'] and x['job']['k'] == f['k'])
        job = decode_job(m['job'])
        sec = int(f['sector'])
        # the chunk cfg that holds this sector, and its N / shifts / extra lines (also for phase-1 manifests)
        chunk, kv = None, None
        for i, c in enumerate(m['cfgs']):
            lines = open(os.path.join(rundir, c)).read().splitlines()
            d = {l.split()[0]: l.split()[1:] for l in lines if l.strip() and not l.startswith('#')}
            lo, hi = (int(d['sectors'][0]), int(d['sectors'][1])) if 'sectors' in d else (0, 10 ** 9)
            if lo <= sec < hi:
                chunk, kv = i, (d, [l for l in lines if l.startswith(('sectorstride', 'fold'))])
                break
        if chunk is None:
            sys.exit(f"sector {sec} of {m['moment']} k={job['k']} is in none of its cfgs")
        d, extra0 = kv
        N0, shifts = int(d['N'][0]), int(d['shifts'][0])
        prevN = max([x['N'] for x in m.get('refine', []) if x['sector'] == sec] + [N0])
        Nn = next((x for x in LADDER if x >= factor * prevN), next_prime(factor * prevN))
        tier = m.get('tier', os.path.basename(os.path.normpath(rundir)))
        seed = seed_for(tier, m['moment'] + f'|refine|s{sec}|N{Nn}', job['k'], 0)
        extra = extra0 + ([f'transform {transform}'] if transform else [])
        name = f"{m['moment']}_k{job['k']}_s{sec:05d}_N{Nn}"
        cfg = job_cfg(job, N=Nn, shifts=shifts, seed=seed, sectors=(sec, sec + 1), extra=extra)
        atomic_write_text(os.path.join(rundir, name + '.cfg'), cfg + f'out {name}.cfg.json\n')
        m.setdefault('refine', []).append({'sector': sec, 'cfg': name + '.cfg', 'orig_cfg': m['cfgs'][chunk],
                                           'N': Nn, 'seed': seed})
        new.append(name + '.cfg')
    atomic_write_json(os.path.join(rundir, 'manifest.json'), manifest, indent=1)
    lst = os.path.join(rundir, 'cfglist_refine.txt')
    old = open(lst).read() if os.path.exists(lst) else ''
    atomic_write_text(lst, old + ''.join(c + '\n' for c in new))
    print(f'{len(new)} refinement cfgs appended to {lst}')
    seedcheck([rundir])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan'); p.add_argument('spec'); p.add_argument('rundir'); p.add_argument('--tier')
    p.add_argument('--force', action='store_true')
    p = sub.add_parser('collect'); p.add_argument('rundir'); p.add_argument('--floor', type=float)
    p.add_argument('--partial', action='store_true'); p.add_argument('--need'); p.add_argument('--legacy', action='store_true')
    p = sub.add_parser('refine'); p.add_argument('rundir'); p.add_argument('flags')
    p.add_argument('--factor', type=int, default=4); p.add_argument('--transform', type=int)
    p.add_argument('--all', action='store_true', help='also refine flagged sectors of non-relevant coefficients')
    p = sub.add_parser('seedcheck'); p.add_argument('rundirs', nargs='+')
    p = sub.add_parser('korobov'); p.add_argument('N', type=int); p.add_argument('d', type=int)
    a = ap.parse_args()
    if a.cmd == 'plan':
        plan(a.spec, a.rundir, a.tier, a.force)
    elif a.cmd == 'collect':
        collect(a.rundir, a.floor, a.partial, a.need, a.legacy)
    elif a.cmd == 'refine':
        refine(a.rundir, a.flags, a.factor, a.transform, a.all)
    elif a.cmd == 'seedcheck':
        sys.exit(0 if seedcheck(a.rundirs) else 1)
    elif a.cmd == 'korobov':
        print(korobov(a.N, a.d))
