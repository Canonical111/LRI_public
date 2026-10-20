#!/usr/bin/env python3
"""Auxiliary inputs for the arbitrary-N continuum analysis (PLAN_ANALYSIS.md M1, M2, M2b).

For every regulator point (order r, lambda) of the archived and new records this
recomputes, with the UNCHANGED functions of code/hamiltonian (imported read-only):

  archived (r, lambda) (the N=256/384/128 records, which used mixed cutoff 4096,
  tail cutoff 2048 and partly collapsed cutoff 200000):
    * mixed_sequence.run at Nmix = 16384, its full Xmixed sequence and the
      mixed_sequence.extrapolate fits of the full sequence and of its first
      Nmix/2 = 8192 entries (M1);
  every (r, lambda), archived and new:
    * resummed_improved.two_point at collapsed cutoffs 400000 and 800000 (M2b);
    * exact_leading_tail.evaluate at tail cutoff 8192 with the 800000 and with
      the 400000 collapsed norms, and at tail cutoff 2048 with the 800000 norms
      (M2, M2b).

The new records already contain mixed 16384, two_point 800000 and A_face
(8192, 800000 norms); recomputing the latter two here is a reproducibility
check. Nothing here fits h(lambda) or uses any proposed value of C2.

This is a cluster job (each mixed sum at 16384 takes ~150 s and ~11 GB); see
code/continuum/aux_job.sbatch. Do not run the full list on a laptop.

  python code/continuum/aux_inputs.py list
  python code/continuum/aux_inputs.py run --out DIR [--workers W] [--only k:lam ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True                  # never write bytecode next to the science sources
PKG = Path(__file__).resolve().parents[2]
SCIENCE = PKG / 'code' / 'hamiltonian'

MIXED_CUTOFF = 16384
COLLAPSED_CUTOFFS = (400000, 800000)
TAIL_CUTOFF = 8192
TAIL_CUTOFF_COARSE = 2048

# Archived regulator points (data/hamiltonian/raw: fine N=256, extended N=384, large_lambda N=128).
ARCHIVED = [(1, 0.075), (1, 0.1), (1, 0.125), (1, 0.15), (1, 0.2), (1, 0.25),
            (2, 0.125), (2, 0.175), (2, 0.25), (2, 0.35),
            (3, 0.2), (3, 0.25), (3, 0.35), (3, 0.5)]
# Regulator points of the 16 production records (cluster/production_plan.json).
NEW = [(1, 0.05), (1, 0.0625), (1, 0.075), (1, 0.0875), (1, 0.1),
       (2, 0.0625), (2, 0.075), (2, 0.1), (2, 0.125), (2, 0.15),
       (3, 0.1), (3, 0.125), (3, 0.15), (3, 0.175)]


def items() -> list[dict]:
    """One item per distinct (order, lambda); archived items first (they carry the long mixed sums)."""
    out = [dict(order=k, lam=a, archived=True, new=(k, a) in NEW) for k, a in ARCHIVED]
    out += [dict(order=k, lam=a, archived=False, new=True) for k, a in NEW if (k, a) not in ARCHIVED]
    return out


def file_name(order: int, lam: float) -> str:
    return f'aux_k{order}_a{lam!r}.json'


def science():
    """Import the unchanged science modules from code/hamiltonian (read-only)."""
    if str(SCIENCE) not in sys.path:
        sys.path.insert(0, str(SCIENCE))
    import resummed_improved as ri                  # noqa: E402
    from mixed_sequence import run as mixed_run, extrapolate as mixed_extrap   # noqa: E402
    from exact_leading_tail import evaluate as leading_tail                     # noqa: E402
    return ri, mixed_run, mixed_extrap, leading_tail


def peak_rss_gb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e9 if sys.platform == 'darwin' else r * 1024 / 1e9


def compute(item: dict) -> dict:
    ri, mixed_run, mixed_extrap, leading_tail = science()
    k, lam = item['order'], item['lam']
    t0 = time.time()
    out = dict(order=k, lam=lam, archived=item['archived'], new=item['new'], timings={})
    if item['archived']:
        t = time.time()
        mix = mixed_run(lam, k, MIXED_CUTOFF)
        xm = mix['Xmixed']
        out['mixed'] = dict(Nmax=mix['Nmax'], Xmixed=xm, fits=mixed_extrap(xm),
                            prefix_Nmax=MIXED_CUTOFF // 2, prefix_fits=mixed_extrap(xm[:MIXED_CUTOFF // 2]))
        del mix
        out['timings']['mixed'] = time.time() - t
    tp = {}
    for nc in COLLAPSED_CUTOFFS:
        t = time.time()
        ri.ORDER = k                                # two_point reads the regulator order from this global
        tp[nc] = ri.two_point(lam, nc)
        out['timings'][f'two_point_{nc}'] = time.time() - t
    out['two_point'] = {str(nc): tp[nc] for nc in COLLAPSED_CUTOFFS}
    faces = {}
    lo, hi = min(COLLAPSED_CUTOFFS), max(COLLAPSED_CUTOFFS)
    for tail, nc in [(TAIL_CUTOFF, hi), (TAIL_CUTOFF, lo), (TAIL_CUTOFF_COARSE, hi)]:
        t = time.time()
        faces[f'tail{tail}_collapsed{nc}'] = leading_tail(lam, k, tail, two_point=tp[nc])
        out['timings'][f'a_face_{tail}_{nc}'] = time.time() - t
    out['a_face'] = faces
    out['timings']['total'] = time.time() - t0
    out['peak_rss_GB_process'] = peak_rss_gb()
    return out


def write_atomic(path: Path, obj: object) -> None:
    tmp = path.with_name('.' + path.name + '.writing')
    tmp.write_text(json.dumps(obj, indent=1, allow_nan=False) + '\n')
    os.replace(tmp, path)


def worker(args: tuple[dict, str]) -> tuple[str, float, float]:
    item, out_dir = args
    res = compute(item)
    path = Path(out_dir) / file_name(item['order'], item['lam'])
    write_atomic(path, res)
    return path.name, res['timings']['total'], res['peak_rss_GB_process']


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def source_hashes() -> dict[str, str]:
    return {p.name: sha256(p) for p in sorted(SCIENCE.glob('*.py'))}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    r = sub.add_parser('run')
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--workers', type=int, default=1)
    r.add_argument('--only', nargs='*', default=None, help='k:lam items (testing)')
    a = p.parse_args(argv)
    todo = items()
    if a.cmd == 'list':
        for it in todo:
            print(it['order'], it['lam'], 'archived' if it['archived'] else 'new',
                  'mixed16384' if it['archived'] else '')
        return
    if a.only is not None:
        want = {(int(x.split(':')[0]), float(x.split(':')[1])) for x in a.only}
        todo = [it for it in todo if (it['order'], it['lam']) in want]
        if not todo:
            p.error('no items selected')
    if a.workers < 1:
        p.error('--workers must be >= 1')
    a.out.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    t0 = time.time()
    done = []
    if a.workers == 1:
        for it in todo:
            done.append(worker((it, str(a.out))))
            print('DONE', *done[-1], flush=True)
    else:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.workers, maxtasksperchild=1) as pool:
            for res in pool.imap_unordered(worker, [(it, str(a.out)) for it in todo], chunksize=1):
                done.append(res)
                print('DONE', *res, flush=True)
    import numpy, scipy, sympy, mpmath
    receipt = dict(
        kind='c2aux', started_utc=started, completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        wall_seconds=time.time() - t0, workers=a.workers, host=platform.node(), platform=platform.platform(),
        python=sys.version, versions=dict(numpy=numpy.__version__, scipy=scipy.__version__,
                                          sympy=sympy.__version__, mpmath=mpmath.__version__),
        cutoffs=dict(mixed=MIXED_CUTOFF, collapsed=list(COLLAPSED_CUTOFFS), tail=TAIL_CUTOFF,
                     tail_coarse=TAIL_CUTOFF_COARSE),
        science_source_hashes=source_hashes(),
        science_sources_sha256=hashlib.sha256(json.dumps(source_hashes(), sort_keys=True).encode()).hexdigest(),
        items=[dict(order=it['order'], lam=it['lam'], archived=it['archived'], new=it['new'],
                    file=file_name(it['order'], it['lam'])) for it in todo],
        per_item=[dict(file=f, seconds=s, peak_rss_GB_process=m) for f, s, m in sorted(done)],
        outputs_sha256={f: sha256(a.out / f) for f, _, _ in sorted(done)},
        scope='Auxiliary inputs (mixed, collapsed, leading-tail cutoffs) recomputed with the unchanged '
              'code/hamiltonian functions; no fit of h(lambda), no C2.')
    write_atomic(a.out / 'aux_receipt.json', receipt)
    print('RECEIPT', a.out / 'aux_receipt.json', flush=True)


if __name__ == '__main__':
    main()
