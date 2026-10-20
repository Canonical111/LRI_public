#!/usr/bin/env python3
"""Measure the cost of the auxiliary cutoffs at one (lambda, order); no physics changes.

For each mixed thermal cutoff N_mix and each leading-tail two-index cutoff, run the
unmodified solver functions (mixed_sequence.run/extrapolate and
exact_leading_tail.evaluate) in a fresh subprocess and record wall time, peak
RSS of that subprocess and the resulting numbers, so that the cutoffs of the
Expanse plan can be chosen from measured cost and convergence. The collapsed
two-point sums are computed once and reused by the tail evaluations, exactly as
reproduce.py does. This is a benchmark, not a production record.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

PKG = Path(__file__).resolve().parents[2]
SCIENCE = PKG / 'code' / 'hamiltonian'


def peak_rss_bytes() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)


def one(kind: str, lam: float, order: int, cutoff: int, two_point: str | None) -> dict:
    sys.path.insert(0, str(SCIENCE))
    import numpy as np
    import resummed_improved as ri
    ri.ORDER = order
    t0 = time.time()
    if kind == 'mixed':
        from mixed_sequence import run, extrapolate
        mix = run(lam, order, cutoff)
        fits = extrapolate(mix['Xmixed'])
        # Same selection as analyze_fine.py (fits with >= 3 powers and Nmin >= 2048).
        sel = [f['limit'] for f in fits if len(f['powers']) >= 3 and f['Nmin'] >= 2048]
        out = {'last_partial_sum': mix['Xmixed'][-1], 'n_selected_fits': len(sel),
               'selected_median': float(np.median(sel)) if sel else None,
               'selected_spread': float(max(sel) - min(sel)) if sel else None,
               'all_fits': fits}
    elif kind == 'tail':
        from exact_leading_tail import evaluate
        tp = json.loads(Path(two_point).read_text())
        out = evaluate(lam, order, cutoff, tp)
    else:
        from resummed_improved import two_point as tp_run
        out = tp_run(lam, cutoff)
        Path(two_point).write_text(json.dumps(out))
        out = {'Xdisc': out['Xdisc'], 'X2': out['X2'], 'Dmixed': out['Dmixed']}
    return {'kind': kind, 'lam': lam, 'order': order, 'cutoff': cutoff, 'seconds': time.time() - t0,
            'peak_rss_bytes': peak_rss_bytes(), 'result': out}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--lam', type=float, required=True)
    p.add_argument('--order', type=int, choices=[1, 2, 3], required=True)
    p.add_argument('--collapsed-cutoff', type=int, default=800000)
    p.add_argument('--mixed', type=int, nargs='*', default=[4096, 8192, 16384])
    p.add_argument('--tail', type=int, nargs='*', default=[2048, 4096, 8192])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--one', nargs=3, metavar=('KIND', 'CUTOFF', 'TWO_POINT'), help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.one:
        kind, cutoff, tp = a.one
        print(json.dumps(one(kind, a.lam, a.order, int(cutoff), tp)))
        return
    rows = []
    with tempfile.TemporaryDirectory() as d:
        tp = str(Path(d) / 'two_point.json')
        jobs = [('two_point', a.collapsed_cutoff)] + [('mixed', n) for n in a.mixed] + [('tail', n) for n in a.tail]
        for kind, cutoff in jobs:
            cmd = [sys.executable, __file__, '--lam', str(a.lam), '--order', str(a.order), '--out', '/dev/null',
                   '--one', kind, str(cutoff), tp]
            t0 = time.time()
            res = subprocess.run(cmd, capture_output=True, text=True)
            row = None
            if res.returncode == 0:
                try:
                    row = json.loads(res.stdout.strip().splitlines()[-1])
                    row['wall_seconds_including_imports'] = time.time() - t0
                except (ValueError, IndexError):
                    row = None
            if row is None:      # failed or unparsable: keep the diagnostics, fail at the end
                row = {'kind': kind, 'cutoff': cutoff, 'error': True, 'returncode': res.returncode,
                       'stderr_tail': res.stderr[-2000:], 'wall_seconds': time.time() - t0}
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != 'result'}), flush=True)
            a.out.write_text(json.dumps({'lam': a.lam, 'order': a.order, 'rows': rows}, indent=2) + '\n')
    failed = [f"{r['kind']} {r['cutoff']}" for r in rows if r.get('error')]
    a.out.write_text(json.dumps({'lam': a.lam, 'order': a.order, 'collapsed_cutoff': a.collapsed_cutoff,
                                 'status': 'failed' if failed else 'ok', 'failed': failed,
                                 'rows': rows, 'scope': __doc__.strip().splitlines()[0]}, indent=2) + '\n')
    if failed:
        print(f'FAILED: {", ".join(failed)} (diagnostics kept in {a.out})', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
