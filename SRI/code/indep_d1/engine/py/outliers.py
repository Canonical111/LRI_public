#!/usr/bin/env python3
"""Outlier / acceptance check (v2, 2026-10-03).

For every job of a campaign (RUNDIR/manifest.json) and every NEEDED coefficient [eps^k l^j] (manifest 'need',
else specs/production_D4.json), the contribution of each sector is assembled per shift replicate from the
engine's per-sector per-shift values (v2 output 'per_sector[].rep') through the exact coefficient map, so only
Laurent orders that actually feed a needed coefficient enter, with their correlations.  Refined sectors
(campaign.py refine) replace the original ones.  With e_s the replicate error of sector s and E the replicate
error of the whole coefficient, a sector is
  FLAGGED   if  e_s > fac * median_s(e_s)  and  e_s > share * E          (one sector dominates the error)
  RELEVANT  if  max(|dC6/dx|, |dC7/dx|) * E > rel * T                    (the coefficient's error matters)
            (C8 runs: --grad specs/gradients_C8.json, |dC8/dx|; the need list comes from the manifest)
Acceptance: no flagged sector of a relevant coefficient (exit status 1 otherwise).  Flagged sectors are
handled with more lattice points (campaign.py refine RUNDIR flags.json), then re-checked.

usage: outliers.py RUNDIR [--fac 30] [--share 0.5] [--T 5e-5] [--rel 1e-3] [--grad FILE] [--json flags.json]
"""
import argparse, json, math, os, re, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lri_moments import coefficient_map
from campaign import decode_job, _need_lookup, ROOT


def raw_name(group, k, j):
    base = re.sub(r'_N\d+$', '', group).replace('_base', '')
    return f'{base}[eps^{k} l^{j}]'


def load_sens(path):
    if path and os.path.exists(path):
        g = json.load(open(path))
        g = g.get('gradients', g.get('sens', g))
        outs = [o for o in ('C6', 'C7', 'C8') if o in g] or ['C6', 'C7']      # C8: phase-3 gradient files
        return {nm: max(abs(float(g.get(o, {}).get(nm, 0))) for o in outs)
                for nm in set().union(*(set(g.get(o, {})) for o in outs))}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rundir')
    ap.add_argument('--fac', type=float, default=30)
    ap.add_argument('--share', type=float, default=0.5)
    ap.add_argument('--T', type=float, default=5e-5)
    ap.add_argument('--rel', type=float, default=1e-3)
    ap.add_argument('--grad', default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    grad = a.grad or os.path.join(ROOT, 'specs', 'gradients_C6_C7_D4.json')
    if not os.path.exists(grad):
        grad = os.path.join(ROOT, 'specs', 'framework_sensitivities_C6_C7_D4.json')
    sens = load_sens(grad)
    needs = _need_lookup(os.path.join(ROOT, 'specs', 'production_D4.json'))
    manifest = json.load(open(os.path.join(a.rundir, 'manifest.json')))
    flagged, nrel, nchecked = [], 0, 0
    for m in manifest:
        job = decode_job(m['job'])
        k = job['k']
        need = m.get('need')
        if need is None:
            base = re.sub(r'_N\d+$', '', m['moment'])
            need = needs.get(m['moment'], needs.get(base, {})).get(k, [])
        if not need:
            continue
        refined = {}
        for x in m.get('refine', []):
            refined[x['sector']] = x['cfg']
        persec = {}   # sector -> (cfg, {jj: [R values]})
        srcs = [(c, None) for c in m['cfgs']] + [(c, s) for s, c in refined.items()]
        legacy = False
        for cfg, only in srcs:
            p = os.path.join(a.rundir, cfg + '.json')
            if not os.path.exists(p):
                continue
            r = json.load(open(p))
            orders = {c: ch['orders'] for c, ch in r['channels'].items()}
            cmap, _ = coefficient_map(job, orders)
            chans = r['channels']
            first = next(iter(chans.values()))
            if not first.get('per_sector') or 'rep' not in first['per_sector'][0]:
                legacy = True
                break
            for i, sec in enumerate(first['per_sector']):
                sid = sec['id']
                if only is None and sid in refined:
                    continue
                if only is not None and sid != only:
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
                persec[sid] = (cfg, vals)
        if legacy:
            print(f"{m['moment']} k={k}: phase-1 output without per-sector replicates; skipped")
            continue
        for jj in need:
            secs = [(sid, cfg, v[jj]) for sid, (cfg, v) in persec.items() if jj in v]
            if not secs:
                continue
            R = len(secs[0][2])
            if R < 2:
                continue
            nchecked += 1
            tot = [sum(x[2][t] for x in secs) for t in range(R)]
            E = st.stdev(tot) / math.sqrt(R)
            es = [(st.stdev(v) / math.sqrt(R), sid, cfg) for sid, cfg, v in secs]
            med = st.median([e for e, _, _ in es])
            nm = raw_name(m['moment'], k, jj)
            s_i = sens.get(nm, 0.0)
            relevant = s_i * E > a.rel * a.T
            nrel += relevant
            for e, sid, cfg in es:
                if med > 0 and e > a.fac * med and e > a.share * E:
                    flagged.append({'moment': m['moment'], 'k': k, 'sector': sid, 'cfg': cfg, 'coef': nm,
                                    'err_sector': e, 'err_total': E, 'median': med, 'sens': s_i,
                                    'relevant': bool(relevant)})
                    print(f"FLAG {'RELEVANT ' if relevant else 'minor    '}{nm:24s} sector {sid:5d} ({cfg}) "
                          f"err {e:.2e} of total {E:.2e} (median {med:.1e}), sens {s_i:.3g} -> "
                          f"contribution {s_i * E:.1e} vs {a.rel:g}*T = {a.rel * a.T:.1e}")
    nbad = sum(f['relevant'] for f in flagged)
    print(f'checked {nchecked} needed coefficients ({nrel} relevant at T={a.T:g}); flagged sectors: '
          f'{len(flagged)} ({nbad} on relevant coefficients)')
    if a.json:
        json.dump({'flagged': flagged, 'T': a.T, 'rel': a.rel, 'fac': a.fac, 'share': a.share}, open(a.json, 'w'),
                  indent=1)
    sys.exit(1 if nbad else 0)


if __name__ == '__main__':
    main()
