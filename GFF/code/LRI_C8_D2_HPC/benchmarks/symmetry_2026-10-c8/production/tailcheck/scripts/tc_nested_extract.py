#!/usr/bin/env python3
"""Compact per-replicate prefix data of nested-N runs (tc_nested.py outputs), and the production's per-replicate jets
of the same graphs, for the joint-resampling analysis (tc_nested_joint.py). Read-only on the runs and the production.

  tc_nested_extract.py --run NAME=RUNDIR [--run NAME=RUNDIR ...] --prod PRODRUN --final C8_final.json --two-loop two_loop.json
                       --select SELECT_DATA.csv(.gz) --tools PKG/tools --out OUT.json.gz

Per graph-campaign of each run (out/<c>_<s>_L<L>_G<g>.json; sha256 recorded): for every prefix N = chunk * 2^j and
replicate r, the prefix means of the two jets m0, m1 (prefix mean = (nmax / N) * sum of the rows' values below N), the
Hill estimate from the 16 largest |t| of the prefix (exact: the union of its rows' top-16), the largest |t| over sum
|t| of the prefix, and ln(16th largest |t|). The replicates of one (run, campaign, sector) share the R scrambles of
that net (net_<c>_<s>.bin), which the joint resampling must preserve.

Production: for every graph of the runs, the per-replicate jets (Y0, Y1) of groups/<c>_<s>_L<L>/graph_replicates.csv
(128 replicates at the production's own point count), the point count, and select_data's variance share.

C8 projection: J8[8] from the vendored assembly's Jacobians at the result's means (free + power per loop, as
design.pilot_means), and the check that 0.25 * Var(Y . J8) / 128 reproduces select_data's v for every graph read
(relative difference recorded; the run fails above 1e-6)."""
import argparse, csv, gzip, hashlib, json, math, sys
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--run', action='append', required=True)
ap.add_argument('--prod', type=Path, required=True)
ap.add_argument('--final', type=Path, required=True)
ap.add_argument('--two-loop', type=Path, required=True)
ap.add_argument('--select', type=Path, required=True)
ap.add_argument('--tools', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.tools))
import assemble as asm  # noqa: E402

fin = json.loads(a.final.read_bytes())
B2 = np.asarray(json.loads(a.two_loop.read_bytes())['B2'], float)
means = {int(L): np.asarray(fin['means']['free'][L]) + np.asarray(fin['means']['power'][L]) for L in fin['means']['free']}
J = asm.vendored().jacobians(means, B2, 8, 1)
J8 = np.asarray(J[8])[8].real.astype(float)
print('J8[8] =', J8.tolist(), flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def hill16(t):
    lt = np.log(t)
    return float(np.mean(lt[:15] - lt[15]))


out = dict(schema='c8-d2-tailcheck-nested-extract-1', J8=J8.tolist(), runs={}, graphs={}, production={})
need = set()
for spec in a.run:
    name, rundir = spec.split('=', 1); rundir = Path(rundir)
    setup = json.loads((rundir / 'setup.json').read_text())
    chunk, R = setup['chunk'], setup['reps']
    out['runs'][name] = dict(rundir=str(rundir), seed=setup['seed'], reps=R, chunk=chunk, executable_sha256=setup['executable_sha256'],
                             nets={k: v['seeds'] for k, v in setup['nets'].items()})
    for f in sorted((rundir / 'out').glob('*.json')):
        c, s, L, G = f.stem.split('_'); g = int(G[1:]); L = int(L[1:])
        doc = json.loads(f.read_text()); rows = doc['rows']
        nmax = rows[0]['total']; K = nmax // chunk
        v = np.zeros((R, K, 2)); tops = [[None] * K for _ in range(R)]; tsum = np.zeros((R, K))
        seen = np.zeros((R, K), bool)
        for r in rows:
            k = r['begin'] // chunk; rep = r['rep']
            if r['end'] - r['begin'] != chunk or r['total'] != nmax or seen[rep, k]:
                raise SystemExit(f'{f}: inconsistent row {r["uid"]}')
            seen[rep, k] = True
            v[rep, k] = [float(r['values'][0]), float(r['values'][1])]
            tsum[rep, k] = float(r['tail_sum']); tops[rep][k] = np.array([float(x) for x in r['tail_top']])
        if not seen.all():
            raise SystemExit(f'{f}: missing rows')
        levels = [chunk << j for j in range(int(math.log2(K)) + 1)]
        cs = np.cumsum(v, axis=1)
        m = {N: cs[:, N // chunk - 1, :] * (nmax / N) for N in levels}
        H = np.zeros((R, len(levels))); S = np.zeros((R, len(levels))); Q = np.zeros((R, len(levels)))
        for i, N in enumerate(levels):
            k = N // chunk
            for rep in range(R):
                t = np.sort(np.concatenate(tops[rep][:k]))[::-1][:16]
                H[rep, i] = hill16(t); S[rep, i] = t[0] / tsum[rep, :k].sum(); Q[rep, i] = math.log(t[15])
        key = f'{name}:{f.stem}'
        out['graphs'][key] = dict(run=name, campaign=c, sector=s, L=L, graph=g, nmax=nmax, reps=R, levels=levels, native_sha256=sha(f),
                                  m0=[[float(m[N][r, 0]) for N in levels] for r in range(R)], m1=[[float(m[N][r, 1]) for N in levels] for r in range(R)],
                                  hill=H.tolist(), share=S.tolist(), ln_t16=Q.tolist())
        need.add((c, s, L, g))
        print(f'{key}: nmax {nmax}, {len(levels)} levels', flush=True)

sel = {}
op = gzip.open if str(a.select).endswith('.gz') else open
with op(a.select, 'rt') as f:
    for r in csv.DictReader(f):
        sel[(r['campaign'], r['sector'], int(r['L']), int(r['graph']))] = r
worst = 0.
for (c, s, L) in sorted({k[:3] for k in need}):
    want = {k[3] for k in need if k[:3] == (c, s, L)}
    gdir = a.prod / 'groups' / f'{c}_{s}_L{L}'
    Y = {}
    with open(gdir / 'graph_replicates.csv') as f:
        next(f)
        for line in f:
            x = line.rstrip('\n').split(',')
            g = int(x[1])
            if g in want:
                Y.setdefault(g, {})[int(x[0])] = [float(x[2]), float(x[3])]
    for g in sorted(want):
        reps = sorted(Y[g]); y = np.array([Y[g][r] for r in reps])
        srow = sel[(c, s, L, g)]
        vproj = 0.25 * float(np.var(y @ J8, ddof=1)) / len(reps)
        rel = abs(vproj / float(srow['v']) - 1); worst = max(worst, rel)
        out['production'][f'{c}_{s}_L{L}_G{g}'] = dict(points=int(srow['points']), reps=len(reps), Y0=y[:, 0].tolist(), Y1=y[:, 1].tolist(),
                                                     share=float(srow['share']), v=float(srow['v']), v_recomputed=vproj, rel_diff=rel,
                                                     kurtosis=float(srow['kurtosis']), xi_hat=float(srow['xi_hat']))
out['production_check'] = dict(max_rel_diff_v=worst, graphs=len(out['production']), graph_replicates_sha256={
    f'{c}_{s}_L{L}': sha(a.prod / 'groups' / f'{c}_{s}_L{L}' / 'graph_replicates.csv') for (c, s, L) in sorted({k[:3] for k in need})})
with gzip.open(a.out, 'wt') as f:
    json.dump(out, f)
print(f'{len(out["graphs"])} graph-campaigns, {len(out["production"])} production graph-campaigns; J8 check: max relative difference of v {worst:.2e}', flush=True)
if worst > 1e-6:
    raise SystemExit('J8 projection does not reproduce select_data v')
