#!/usr/bin/env python3
"""Per-size stage-A centres from the stage-0 crossings (SCAN_PLAN.md).

Usage: stageA_centres.py SCAN0_DIR --out centres.csv [--tag fits/quot_c3_deg4.json] [--exclude ds ...]
For each point: U-crossings x(N,2N) of the stage-0 pairs (1024..16384) from the central-three degree-4 quotients (the
crossing positions are robust even where the local χ² is poor; the trend matters here, not the χ²). Centre(N) for the
stage-A sizes 1024..65536: mean of the crossings of the two pairs touching N where measured; for 32768 and 65536 a
linear extrapolation in log2 N of the last three crossings (conservative for a decaying power-law drift). Writes
explicit (s, N, beta) rows and prints the drift diagnostics.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scan0', type=Path); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--tag', default='fits/quot_c3_deg4.json'); p.add_argument('--alt-tag', default='fits/quot_full_deg4.json'); p.add_argument('--exclude', nargs='*', default=[])
    a = p.parse_args(); rows = []
    for d in sorted(a.scan0.glob('ds*')):
        ds = d.name[2:]
        if ds in a.exclude or not (d / a.tag).exists(): print(f'ds={ds}: skipped'); continue
        man = json.loads((d / 'stage0' / 'manifest.json').read_text()); s = man['tasks'][0]['s']
        U = []; used = None
        for tag in (a.tag, a.alt_tag):
            if not (d / tag).exists(): continue
            Q = next(iter(json.load(open(d / tag)).values()))
            U = sorted([(c['N'], c['beta_crossing']) for c in Q['crossings'] if c['crossing_observable'] == 'U'])
            if len(U) >= 2: used = tag; break
        if len(U) < 2: print(f'ds={ds}: fewer than two U crossings in any file; skipped'); continue
        Ns = np.array([u[0] for u in U], float); xs = np.array([u[1] for u in U])   # pairs (N, 2N)
        lg = np.log2(Ns); k = min(3, len(xs)); coef = np.polyfit(lg[-k:], xs[-k:], 1)  # linear in log2 N over the last 3 pairs
        pred = lambda n: float(np.polyval(coef, np.log2(n)))
        cen = {}
        for N in (1024, 2048, 4096, 8192, 16384, 32768, 65536):
            touching = [x for (n, x) in U if n == N or 2 * n == N]
            cen[N] = float(np.mean(touching)) if touching else pred(N / 2 if N > 16384 else N)   # pair (N/2,N)... see below
        # for 32768: pairs (16384,32768) [pred at n=16384] and (32768,65536) [pred at 32768]; for 65536: (32768,65536),(65536,131072)
        cen[32768] = float(np.mean([pred(16384), pred(32768)])); cen[65536] = float(np.mean([pred(32768), pred(65536)]))
        drift = xs[-1] - xs[0]; step = coef[0]
        print(f"ds={ds:>9} s={s:.6f} [{used.split('/')[-1]}]: crossings {[round(x,6) for x in xs]}  drift/doubling {step:+.2e}  centres 1024..65536: {[round(cen[N],6) for N in sorted(cen)]}")
        for N in sorted(cen): rows.append(dict(s=s, N=N, beta=f'{cen[N]:.8f}'))
    with a.out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['s', 'N', 'beta']); w.writeheader(); w.writerows(rows)
    print(f'{len(rows)} rows -> {a.out}')
if __name__ == '__main__': main()
