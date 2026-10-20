#!/usr/bin/env python3
"""Strict-tolerance re-evaluation of the most-warned sectors of a production run (README section 9, criterion 5;
review test D at production lattices).  2026-10-03.

  strict_recheck.py prepare RUNDIR OUTDIR GROUP:NSEC:SHIFTS [GROUP:NSEC:SHIFTS ...]
      GROUP = manifest moment name (k = the job's eps power; use GROUP@k when a moment has several jobs).
      For each group, the NSEC sectors with the most warned points (engine 'WARN sector S shift R: k of n points
      above the precision target after tails' lines in RUNDIR/<cfg>.log, summed over shifts) are re-run alone
      with the SAME cfg (lattice, N, seed -> identical random shifts, since the shift of (sector s, replicate r)
      depends only on seed, s and r) restricted to the first SHIFTS shifts, with strict numerics
      (errTarget 1e-16, tailTol 1e-16, maxJet 2e6, tailMax 0.05).  Writes OUTDIR/<group>_k<k>_s<sector>_strict.cfg,
      OUTDIR/cfglist.txt (most expensive first) and OUTDIR/strict_manifest.json.
  strict_recheck.py compare RUNDIR OUTDIR
      Compares, for every re-run sector and shift r, the per-sector per-shift value of every channel Laurent
      order (default run vs strict run) and the same difference mapped onto every NEEDED coefficient through the
      exact coefficient map; the coefficient differences are reported relative to the coefficient's replicate
      error E_rep in the production run (tests/production_checks.py definition), to the coefficient's quoted
      error err = stat (+) floor (RUNDIR/results.json from campaign.py collect, when present) and to the sector's
      L1 size.  (The per-Laurent-order relative difference is printed for information; sector values below
      1e-15 of the channel's L1 size for that order, i.e. rounding residues of exactly cancelling orders, are
      treated as zeros.)
"""
import argparse, glob, json, math, os, re, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'py'))
from lri_moments import coefficient_map, atomic_write_json, atomic_write_text
from campaign import decode_job

STRICT = ['errTarget 1e-16', 'tailTol 1e-16', 'maxJet 2000000', 'tailMax 0.05']
WARN_RE = re.compile(r'^WARN sector (\d+) shift (\d+): (\d+) of (\d+) points')


def find_job(manifest, spec):
    name, _, k = spec.partition('@')
    ms = [m for m in manifest if m['moment'] == name and (not k or m['job']['k'] == int(k))]
    if len(ms) != 1:
        sys.exit(f'{spec}: {len(ms)} matching jobs in the manifest (use NAME@k)')
    return ms[0]


def prepare(rundir, outdir, groups):
    manifest = json.load(open(os.path.join(rundir, 'manifest.json')))
    os.makedirs(outdir, exist_ok=True)
    entries, lst = [], []
    for g in groups:
        spec, nsec, nsh = g.split(':')
        nsec, nsh = int(nsec), int(nsh)
        m = find_job(manifest, spec)
        k = m['job']['k']
        warned, chunk_of = {}, {}
        for c, (lo, hi) in zip(m['cfgs'], zip(m['bounds'][:-1], m['bounds'][1:])):
            for s in range(lo, hi):
                chunk_of[s] = c
            lp = os.path.join(rundir, c + '.log')
            if os.path.exists(lp):
                for line in open(lp):
                    mm = WARN_RE.match(line)
                    if mm:
                        s = int(mm.group(1))
                        warned[s] = warned.get(s, 0) + int(mm.group(3))
        top = sorted(warned, key=lambda s: -warned[s])[:nsec]
        for s in top:
            c = chunk_of[s]
            out = json.load(open(os.path.join(rundir, c + '.json')))
            ps = next(iter(out['channels'].values()))['per_sector']
            cpu = next(x['cpu'] for x in ps if x['id'] == s)
            cpu = sum(cpu) if isinstance(cpu, list) else cpu
            lines = []
            for line in open(os.path.join(rundir, c)).read().splitlines():
                key = line.split()[0] if line.strip() else ''
                if key in ('sectors', 'shifts', 'out') or key in [x.split()[0] for x in STRICT]:
                    continue
                lines.append(line)
            name = f"{m['moment']}_k{k}_s{s:05d}_strict.cfg"
            body = lines + [f'sectors {s} {s + 1}', f'shifts {nsh}'] + STRICT + [f'out {name}.json']
            atomic_write_text(os.path.join(outdir, name), '\n'.join(body) + '\n')
            est = cpu * nsh / out['shifts']
            entries.append({'moment': m['moment'], 'k': k, 'sector': s, 'orig_cfg': c, 'cfg': name, 'shifts': nsh,
                            'warned_points': warned[s], 'default_cpu_s': cpu, 'est_default_cpu_s': est})
            lst.append((est, name))
    lst.sort(key=lambda x: -x[0])
    atomic_write_text(os.path.join(outdir, 'cfglist.txt'), ''.join(n + '\n' for _, n in lst))
    atomic_write_json(os.path.join(outdir, 'strict_manifest.json'),
                      {'rundir': os.path.abspath(rundir), 'strict': STRICT, 'entries': entries}, indent=1)
    print(f'{len(entries)} strict cfgs in {outdir}; default-tolerance cpu of the same work '
          f'{sum(e["est_default_cpu_s"] for e in entries) / 3600:.1f} core-h (strict costs ~8-15x)')


def sector_vals(out, sid):
    """{channel: {Laurent order: [value per shift]}} of one sector (orders absent from a cfg are exact zeros:
    a single-sector cfg starts at that sector's own lowest order)"""
    res = {}
    for c, ch in out['channels'].items():
        x = next(p for p in ch['per_sector'] if p['id'] == sid)
        res[c] = {o: [x['rep'][r][i] for r in range(len(x['rep']))] for i, o in enumerate(ch['orders'])}
    return res


def val(v, c, o, r):
    return v[c][o][r] if o in v[c] else 0.0


def compare(rundir, outdir):
    sm = json.load(open(os.path.join(outdir, 'strict_manifest.json')))
    manifest = json.load(open(os.path.join(rundir, 'manifest.json')))
    pc = os.path.join(rundir, 'production_checks.json')
    Erep, Err = {}, {}
    rj = os.path.join(rundir, 'results.json')
    if os.path.exists(rj):
        for grp, co in json.load(open(rj))['errors'].items():
            for key, ex in co.items():
                kk, jj = (int(x) for x in key.split(','))
                Err[(grp, kk, jj)] = math.hypot(ex['stat'], ex['floor'])
    if os.path.exists(pc):
        for c in json.load(open(pc))['coefficients']:
            Erep[(c['moment'], c['k'], c['j'])] = c['E_rep']
    rows, worst_rel, worst_pull, worst_err, missing = [], 0.0, 0.0, 0.0, []
    for e in sm['entries']:
        p = os.path.join(outdir, e['cfg'] + '.json')
        if not os.path.exists(p):
            missing.append(e['cfg'])
            continue
        b = json.load(open(p))
        if not b.get('complete'):
            missing.append(e['cfg'])
            continue
        a = json.load(open(os.path.join(rundir, e['orig_cfg'] + '.json')))
        va, vb = sector_vals(a, e['sector']), sector_vals(b, e['sector'])
        m = next(x for x in manifest if x['moment'] == e['moment'] and x['job']['k'] == e['k'])
        job = decode_job(m['job'])
        orders = {c: sorted(va[c]) for c in va}
        cmap, _ = coefficient_map(job, orders)
        R = e['shifts']
        maxrel = 0.0
        for c in va:
            l1 = dict(zip(a['channels'][c]['orders'], a['channels'][c]['abs']))
            for o in sorted(set(va[c]) | set(vb[c])):
                for r in range(R):
                    x, y = val(va, c, o, r), val(vb, c, o, r)
                    # rounding residues of exactly cancelling orders (< 1e-15 of the channel's L1 size) are zeros
                    if x == y or max(abs(x), abs(y)) < 1e-15 * l1.get(o, 0.0) or max(abs(x), abs(y)) < 1e-20:
                        continue
                    rel = abs(x - y) / max(abs(x), abs(y), 1e-300)
                    maxrel = max(maxrel, rel)
        coefd = {}
        for jj in (m.get('need') or []):
            lst = cmap.get((e['k'], jj))
            if not lst:
                continue
            d, size = [], []
            for r in range(R):
                xa = sum(w * val(va, c, o2, r) for c, o2, w in lst)
                xb = sum(w * val(vb, c, o2, r) for c, o2, w in lst)
                sz = sum(abs(w * val(va, c, o2, r)) for c, o2, w in lst)
                d.append(xa - xb)
                size.append(sz)
            E = Erep.get((e['moment'], e['k'], jj))
            dm = max(abs(x) for x in d)
            rel = dm / max(max(size), 1e-300)
            pull = dm / E if E else None
            ET = Err.get((e['moment'], e['k'], jj))
            coefd[jj] = {'max_abs_diff': dm, 'rel_to_sector_size': rel, 'diff_over_Erep': pull,
                         'diff_over_err': dm / ET if ET else None}
            if ET:
                worst_err = max(worst_err, dm / ET)
            worst_rel = max(worst_rel, rel)
            if pull is not None:
                worst_pull = max(worst_pull, pull)
        rows.append(dict(e, max_rel_diff_laurent=maxrel, coef=coefd, strict_cpu_s=b['cpu_seconds'],
                         strict_wall_s=b['wall_seconds']))
        cs = '; '.join(f"l^{jj}: |d| {v['max_abs_diff']:.2e} = {v['rel_to_sector_size']:.1e} rel, "
                       + (f"{v['diff_over_Erep']:.1e} E_rep" if v['diff_over_Erep'] is not None else 'E_rep n/a')
                       + (f", {v['diff_over_err']:.1e} err" if v['diff_over_err'] is not None else '')
                       for jj, v in coefd.items())
        print(f"{e['moment']:8s} k={e['k']} sector {e['sector']:5d} ({e['warned_points']} warned pts): "
              f"max rel diff (Laurent orders) {maxrel:.1e}; {cs}; cpu default {e['est_default_cpu_s']:.0f}s "
              f"strict {b['cpu_seconds']:.0f}s")
    print(f'{len(rows)} sectors compared, {len(missing)} missing; worst coefficient difference '
          f'{worst_rel:.1e} of the sector size, {worst_pull:.1e} x E_rep, {worst_err:.1e} x err (stat+floor)')
    atomic_write_json(os.path.join(outdir, 'strict_compare.json'),
                      {'rows': rows, 'missing': missing, 'worst_rel': worst_rel, 'worst_over_Erep': worst_pull,
                       'worst_over_err': worst_err},
                      indent=1)
    return 0 if not missing else 2


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare'); p.add_argument('rundir'); p.add_argument('outdir'); p.add_argument('groups', nargs='+')
    p = sub.add_parser('compare'); p.add_argument('rundir'); p.add_argument('outdir')
    a = ap.parse_args()
    if a.cmd == 'prepare':
        prepare(a.rundir, a.outdir, a.groups)
    else:
        sys.exit(compare(a.rundir, a.outdir))
