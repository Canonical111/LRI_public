#!/usr/bin/env python3
"""Stage-0 bracket finder: from the per-point stage-0 quotient files, decide the stage-A centre of every grid point.

Usage: stage0_centres.py SCAN0_DIR --out centres_stageA.csv [--quot-tag quot_c3_deg4]
SCAN0_DIR/ds<Δσ>/fits/<tag>.json are quotients.py outputs for the stage-0 grid (N = 1024 … 16384, 9 temperatures).
Rule: centre = U-crossing of the largest pair (8192–16384) if its two local fits have χ²/dof ≤ 3 and the crossing lies
inside both simulated brackets with margin ≥ 20 % of the half-width; otherwise fall back to the next pair; if no pair
qualifies the point is flagged for a second stage-0 pass (recentred on the best available crossing, wider window).
Also reports the drift β_x(N,2N) across pairs, which sets how far stage-A windows must reach.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scan0', type=Path); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--quot-tag', default='quot_c3_deg4'); p.add_argument('--alt-tag', default='quot_full_deg4')
    p.add_argument('--chi2-max', type=float, default=3.0)
    a = p.parse_args(); rows = []; flagged = []
    for d in sorted(a.scan0.glob('ds*')):
        ds = float(d.name[2:]); s = 1 - 2 * ds
        man = json.loads((d / 'stage0' / 'manifest.json').read_text())
        br = {}
        for t in man['tasks']: br.setdefault(t['N'], []).append(t['beta'])
        br = {N: (min(b), max(b)) for N, b in br.items()}
        best = None; notes = []
        for tag in (a.quot_tag, a.alt_tag):
            qf = d / 'fits' / f'{tag}.json'
            if not qf.exists(): notes.append(f'{tag}: missing'); continue
            Q = json.loads(qf.read_text()); Q = Q.get(str(s)) or Q.get(repr(s)) or next(iter(Q.values()))
            chi = {int(k): v['chi2'] / v['dof'] for k, v in Q['local_fit_diagnostics'].items()}
            U = sorted([c for c in Q['crossings'] if c['crossing_observable'] == 'U'], key=lambda c: -c['N'])
            drift = [round(c['beta_crossing'], 6) for c in sorted(U, key=lambda c: c['N'])]
            notes.append(f'{tag}: chi2/dof {dict(sorted(chi.items()))}, U-crossings by pair {drift}')
            for c in U:
                lo1, hi1 = br[c['N']]; lo2, hi2 = br[c['N2']]; lo, hi = max(lo1, lo2), min(hi1, hi2); h = (hi - lo) / 2
                margin = min(c['beta_crossing'] - lo, hi - c['beta_crossing']) / h if h > 0 else -1
                ok = chi.get(c['N'], 9) <= a.chi2_max and chi.get(c['N2'], 9) <= a.chi2_max and margin >= 0.2
                if ok and best is None:
                    best = dict(ds=ds, s=s, N=c['N'], N2=c['N2'], beta=c['beta_crossing'], err=(c['bootstrap_standard_error'] or [None])[0],
                                margin=margin, tag=tag, chi=[chi.get(c['N']), chi.get(c['N2'])])
            if best: break
        if best is None:
            # fallback: best available crossing of the largest pair for a recentred second pass
            flagged.append(dict(ds=ds, s=s, notes=notes)); print(f'ds={ds:g}: NO qualifying crossing -> second stage-0 pass needed; ' + ' | '.join(notes)); continue
        rows.append(dict(s=s, N='', beta=f"{best['beta']:.8f}"))
        print(f"ds={ds:g} s={s:g}: centre {best['beta']:.6f} ± {best['err'] if best['err'] is None else round(best['err'],6)} from pair {best['N']}-{best['N2']} ({best['tag']}, chi2/dof {[round(x,2) for x in best['chi']]}, bracket margin {best['margin']:.2f}); " + notes[0].split(', ')[-1])
    with a.out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['s', 'N', 'beta']); w.writeheader(); w.writerows(rows)
    (a.out.with_suffix('.flagged.json')).write_text(json.dumps(flagged, indent=1) + '\n')
    print(f'{len(rows)} centres written to {a.out}; {len(flagged)} points flagged')
    raise SystemExit(0 if not flagged else 1)
if __name__ == '__main__': main()
