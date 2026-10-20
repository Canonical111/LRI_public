"""Shared helpers of the native test drivers (PLAN.md F: validate.py, class_b.py, check_points.py, sanitize.py,
inspect_check.py, run1_replay.py, archived_stream_replay.py, forced_tiers.py). Expanse-side tools: the workers are
native builds of this package (make gmp decimal c7ref inspect test-builds).

Comparisons parse numbers as Decimal, never binary64 (PLAN F). Records go only to --output.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from common import digest, host_info  # noqa: E402,F401
import libprobe  # noqa: E402
from members import extracted, inventory  # noqa: E402,F401

BIN = ROOT / 'bin'
C8 = {'gmp': BIN / 'c8d3_gmp', 'decimal': BIN / 'c8d3_decimal'}
C7REF = {'gmp': BIN / 'ref/c7d3_gmp', 'decimal': BIN / 'ref/c7d3_decimal'}
INSPECT = BIN / 'c8d3_inspect'
GAMMA = {7: ROOT / 'inputs/order7/gamma_d3_7.txt', 8: ROOT / 'inputs/gamma_d3_8.txt'}
SECTORS = ('free', 'power')
LOOPS7 = (3, 4, 5, 6, 7)
# Every row field the C7(3) worker writes (a6ce987 src/c7d3_integrate.cpp:69), except the wall time "seconds".
C7_ROW_FIELDS = ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'quad', 'mp', 'max_abs', 'values')
# Top-level fields of the C7(3) native JSON that do not depend on timing.
C7_TOP_FIELDS = ('L', 'seed', 'layout', 'bits', 'rate', 'sum_mode', 'long_double_bits', 'mp_backend', 'mp_digits10',
                 'threads', 'graphs_loaded')
CLASS_B_ROW_FIELDS = ('tail_top', 'tail_sum', 'tail_argmax', 'nondirect', 'nonmoderate')
MP_CHECK_ROW_FIELDS = ('mp_checked', 'mp_hist', 'mp_min_log10', 'mp_alarm')


def threads_default() -> int:
    return int(os.environ.get('SLURM_CPUS_PER_TASK') or os.cpu_count() or 4)


def require(*exes: Path) -> None:
    missing = [str(e) for e in exes if not Path(e).exists()]
    if missing:
        raise FileNotFoundError('build first (make gmp decimal c7ref inspect test-builds): missing ' + ', '.join(missing))


def kernels(inv: dict, sector: str, L: int, full: bool, first: int = 8, heaviest: int = 8) -> list[int]:
    """All kernel ids of (sector, L), or the subset: the first `first` and the `heaviest` costliest (PLAN A-RPL-1)."""
    rows = inv[sector][str(L)]
    ids = [r['id'] for r in rows]
    if full:
        return ids
    return sorted(set(ids[:first] + [r['id'] for r in sorted(rows, key=lambda r: -r['cost'])[:heaviest]]))


def write_tasks(path: Path, L: int, rows, order: int | None = None) -> Path:
    """A task file: C8D3TASKS1 <order> <L> <n>, or C7(3)'s C7D3TASKS1 <L> <n> when order is None (HD3)."""
    head = f'C7D3TASKS1 {L} {len(rows)}' if order is None else f'C8D3TASKS1 {order} {L} {len(rows)}'
    Path(path).write_text(head + '\n' + ''.join(' '.join(map(str, r)) + '\n' for r in rows))
    return Path(path)


def task_rows(ids, reps: int = 2, points: int = 64, chunk: int | None = None) -> list[tuple]:
    """(uid, rep, graph, begin, end, total) for every replicate and graph; whole tasks or `chunk`-point pieces."""
    out = []
    for r in range(reps):
        for g in ids:
            for b in range(0, points, chunk or points):
                out.append((len(out), r, g, b, min(points, b + (chunk or points)), points))
    return out


_NETS: dict = {}


def net(td: Path, dim: int, bits: int, seed: int, B: int = 2) -> Path:
    """A scrambled Sobol net file through production.make_net (SciPy), cached per (dim, bits, seed, B)."""
    key = (dim, bits, seed, B)
    p = Path(td) / f'net_{dim}_{bits}_{seed}_{B}.net'
    if key not in _NETS or not p.exists():
        from production import make_net
        p.unlink(missing_ok=True)
        make_net(p, B, dim, bits, seed)
        _NETS[key] = p
    return p


def dim_of(L: int, layout: int) -> int:
    return 2 * L if layout == 2 else 4 * L - 1


def run_worker(exe, root, gamma, netf, tasks, out: Path, seed, layout, rate, threads, mode='compensated', grid='-',
               mp_check: str | None = None, env=None, check=True):
    """Runs one worker invocation (a pre-deleted output) and returns (json or None, CompletedProcess)."""
    out = Path(out)
    out.unlink(missing_ok=True)
    cmd = [str(exe), str(root), str(gamma), str(netf), str(tasks), str(out), str(seed), str(layout), str(rate),
           str(threads), mode, str(grid)]
    if mp_check is not None:
        cmd += ['--mp-check', mp_check]
    cp = subprocess.run(cmd, capture_output=True, text=True, errors='replace', env=env)
    if cp.returncode:
        if check:
            raise RuntimeError(f'{exe} failed ({cp.returncode}): {cp.stderr[-3000:]}')
        return None, cp
    d = json.loads(out.read_text())
    out.unlink()
    return d, cp


def scientific(r: dict, fields=None) -> dict:
    return {k: v for k, v in r.items() if k != 'seconds' and (fields is None or k in fields)}


def rows_equal(a: dict, b: dict, fields) -> str | None:
    """None if every row agrees exactly (as JSON values) in `fields`, else a description of the first difference."""
    if len(a['rows']) != len(b['rows']):
        return f'row counts {len(a["rows"])} vs {len(b["rows"])}'
    for x, y in zip(a['rows'], b['rows']):
        for k in fields:
            if x.get(k) != y.get(k):
                return f'row uid {x.get("uid")} graph {x.get("graph")} field {k}: {str(x.get(k))[:200]} vs {str(y.get(k))[:200]}'
    return None


def normalized(u: str, v: str) -> D:
    return abs(D(u) - D(v)) / max(D(1), abs(D(u)))


def describe(exe: Path) -> dict:
    cp = subprocess.run([str(exe), '--describe'], capture_output=True, text=True, timeout=120)
    if cp.returncode:
        raise RuntimeError(f'{exe} --describe failed ({cp.returncode}): {cp.stderr[-1000:]}')
    return json.loads(cp.stdout)


def buildinfo(exe: Path) -> dict:
    p = Path(str(exe) + '.buildinfo.json')
    if not p.exists():
        raise FileNotFoundError(f'{p}: no build record (make writes it)')
    return json.loads(p.read_text())


def check_ref_probe(exe: Path) -> dict:
    """A-KER-3 / HD9 refusal at use time: re-run the library probe on a reference GMP binary in this job's
    environment and refuse a libgmp path or version that differs from its build record."""
    rec = buildinfo(exe)
    if digest(exe) != rec['sha256']:
        raise RuntimeError(f'{exe}: sha256 differs from its build record')
    now = libprobe.probe(exe)
    if now.get('skipped'):
        return {'skipped': now['skipped']}
    old = rec.get('libprobe') or {}
    keys = ('ldd_realpath', 'loader_realpath', 'version')
    a = {k: (now.get('libgmp') or {}).get(k) for k in keys} if isinstance(now.get('libgmp'), dict) else now.get('libgmp')
    b = {k: (old.get('libgmp') or {}).get(k) for k in keys} if isinstance(old.get('libgmp'), dict) else old.get('libgmp')
    if a != b:
        raise RuntimeError(f'{exe}: the probed libgmp {a} differs from its build record {b}; refusing to use it')
    return {'libgmp': a}


def dump(path: Path | None, obj) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(obj, indent=2, default=str) + '\n')
