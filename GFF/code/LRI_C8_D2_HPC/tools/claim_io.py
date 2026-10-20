#!/usr/bin/env python3
"""The real-Slurm part of A-ORC-13 (R07, J-SMK-4; F9 of Stage 5), evaluated from the 'claim_io {json}' line that every
`production.py run` logs at exit.

  claim_io.py RUN [--logs FILE ...] [--output FILE]

Reads the last claim_io line of each run log: RUN/lanes/logs/idx*.log (lane mode), or the files --logs names (array
mode: the Slurm logs). Only complete runs (status ok) whose rchar was measured (Linux) enter the checks:
  * fingerprint_bytes is identical for every run with the same fingerprint key (R17);
  * the non-own bytes per run agree between the indices of the smallest and of the largest group by tasks.sqlite size,
    which must differ by more than 10x: every pair of runs, one from each group, within max(10% of the smaller value,
    2 MB). Three variants are compared: non_own_bytes, non_own_bytes - fingerprint_bytes (the plan's "without
    fingerprint_bytes"), and non_own_bytes - fingerprint_rchar (the fingerprint with its ldd probe).
non_own_bytes = rchar at exit - the run's own bytes - the rchar of its native launches. The own bytes are the
Python-level reads of the claim's own data, counted by production.py per category (its task file, its checkpoints, the
staged pack members of its blocks, each block's task file and the native outputs read back). The staged members are
the bytes production.stage_graphs actually read from the pack; since the F12 fix it reads each member exactly
(production.read_member: os.pread, no Python buffer), so they equal the members' lengths and no pack byte outside the
claim's members is read. Records of schema c8-d2-claim-io-1 (the tools before that fix) read the pack through a
buffered reader whose buffer is the file system's st_blksize (524,288 bytes on BeeGFS): up to that many neighbouring
pack bytes per member are in their rchar but not in their own bytes, so their non-own bytes grow with the members
staged (0.7 bytes per staged byte at L8, the real-Slurm run of 2026-10-05, docs/HPC.md "F12"). The report counts the
runs per read path ("pack_reads") and names such records in "notes"; their comparison is reported as computed.
Deviation from the plan's wording (docs/HPC.md, "Reads per claim"): the plan subtracts the claim's task file,
checkpoints and staged members once from rchar; production.py also measures each native launch's reads exactly (the
rchar delta across the launch; the claim process reads nothing while it waits), and the comparison subtracts them as
own work: a native launch reads only the claim's job-private copies (its block's members and task file, the gamma
file, the net), the executable and its libraries (on symmetry 1.0008 bytes per staged byte at L8: its staged copies
once). Everything left is what a claim reads besides its own work, which must not grow with the other indices' task
counts. (Stage 5's J-SMK-4 had attributed about 0.7 extra bytes per staged byte to the native re-reading its staged
files; they were the claim process's buffered pack reads, F12.)
The report also gives, per run, the native reads per byte staged (1.0 when the native reads its copies once), and per
group the non-own range.
Exit status: 0 every check passes; 1 a check fails; 2 the data cannot decide (no measured run, or no two groups whose
tasks.sqlite sizes differ by more than 10x)."""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

SCHEMA = 'c8-d2-claim-io-report-1'
TAG = 'claim_io '
EXACT_SCHEMAS = ('c8-d2-claim-io-2',)  # staged members read exactly (F12)
BUFFERED_SCHEMAS = ('c8-d2-claim-io-1',)  # the pack read through Python's buffer (tools before the F12 fix)
REL, ABS = 0.10, 2_000_000
VARIANTS = ('non_own_bytes', 'non_own_minus_fingerprint_bytes', 'non_own_minus_fingerprint_rchar')


def last_record(path: Path) -> dict | None:
    rec = None
    with open(path, errors='replace') as f:
        for line in f:
            if line.startswith(TAG):
                try:
                    rec = json.loads(line[len(TAG):])
                except ValueError:
                    continue
    return rec


def evaluate(run: Path, logs: list[Path] | None = None) -> dict:
    run = Path(run).resolve()
    m = json.loads((run / 'manifest.json').read_text())
    group_of = {j['id']: j['group'] for j in m['jobs']}
    files = sorted(logs) if logs else sorted((run / 'lanes/logs').glob('idx*.log'))
    runs, skipped = [], {'no record': 0, 'not ok': 0, 'unmeasured': 0}
    for f in files:
        r = last_record(f)
        if r is None:
            skipped['no record'] += 1
            continue
        if r.get('status') != 'ok':
            skipped['not ok'] += 1
            continue
        if r.get('non_own_bytes') is None:
            skipped['unmeasured'] += 1
            continue
        r = dict(r, log=f.name, group=group_of.get(r.get('index')))
        runs.append(r)
    out = dict(schema=SCHEMA, run=str(run), logs=len(files), measured=len(runs), skipped=skipped,
               rule=f'every pair within max({REL:.0%} of the smaller, {ABS / 1e6:g} MB); tasks.sqlite sizes > 10x apart')
    # fingerprint_bytes identical per fingerprint key
    fps: dict = {}
    for r in runs:
        fps.setdefault(r.get('fingerprint_key') or 'none', set()).add(r.get('fingerprint_bytes'))
    out['fingerprint'] = {k: sorted(v, key=lambda x: (x is None, x)) for k, v in sorted(fps.items())}
    fp_ok = all(len(v) == 1 for v in fps.values())
    # the pack read path, per run (F12)
    paths = {'exact': 0, 'buffered (pre-F12)': 0, 'unknown schema': 0}
    for r in runs:
        sch = r.get('schema')
        k = 'exact' if sch in EXACT_SCHEMAS else 'buffered (pre-F12)' if sch in BUFFERED_SCHEMAS else 'unknown schema'
        paths[k] += 1
    out['pack_reads'] = paths
    notes = []
    if paths['buffered (pre-F12)']:
        notes.append(f"{paths['buffered (pre-F12)']} run(s) of schema c8-d2-claim-io-1 read the pack through Python's "
                     'buffer (tools before the F12 fix): their non-own bytes include up to st_blksize of neighbouring '
                     'pack data per staged member (docs/HPC.md, F12)')
    if paths['unknown schema']:
        notes.append(f"{paths['unknown schema']} run(s) with a claim_io schema other than {EXACT_SCHEMAS + BUFFERED_SCHEMAS}")
    out['notes'] = notes
    # the native read factor (native rchar per staged byte), per run
    for r in runs:
        staged = ((r.get('own') or {}).get('staged_members') or {}).get('bytes') or 0
        r['native_rchar_per_staged_byte'] = round(r['native']['rchar'] / staged, 4) if staged else None
    sizes = {}
    for g in {r['group'] for r in runs if r['group']}:
        p = run / 'groups' / g / 'tasks.sqlite'
        sizes[g] = p.stat().st_size if p.exists() else None
    by_group = {g: [r for r in runs if r['group'] == g] for g in sizes if sizes[g] is not None}
    out['groups'] = {g: dict(tasks_sqlite_bytes=sizes[g], runs=len(rs), **{v: [min(r[v] for r in rs), max(r[v] for r in rs)]
                                                                           for v in VARIANTS if all(r.get(v) is not None for r in rs)})
                     for g, rs in sorted(by_group.items())}
    out['native_rchar_per_staged_byte'] = {g: [r['native_rchar_per_staged_byte'] for r in rs] for g, rs in sorted(by_group.items())}
    if not runs or len(by_group) < 2:
        out.update(verdict='undecided', reason='no measured run' if not runs else 'fewer than two groups with measured runs',
                   fingerprint_bytes_identical=fp_ok)
        return out
    small = min(by_group, key=lambda g: (sizes[g], g))
    large = max(by_group, key=lambda g: (sizes[g], g))
    ratio = sizes[large] / max(sizes[small], 1)
    out.update(smallest=small, largest=large, tasks_sqlite_ratio=round(ratio, 2), fingerprint_bytes_identical=fp_ok)
    if ratio <= 10:
        out.update(verdict='undecided', reason=f'the tasks.sqlite sizes of {small} and {large} differ by {ratio:.2f}x, not more than 10x')
        return out
    comp, ok = {}, fp_ok
    for v in VARIANTS:
        a = [r[v] for r in by_group[small] if r.get(v) is not None]
        b = [r[v] for r in by_group[large] if r.get(v) is not None]
        if not a or not b:
            comp[v] = dict(passed=None, reason='not measured')
            continue
        worst = max(((abs(x - y), max(REL * min(x, y), ABS)) for x, y in itertools.product(a, b)), key=lambda t: t[0] / t[1])
        comp[v] = dict(small=[min(a), max(a)], large=[min(b), max(b)], largest_difference=worst[0], tolerance=worst[1],
                       passed=worst[0] <= worst[1])
        ok = ok and comp[v]['passed']
    out['comparison'] = comp
    out['verdict'] = 'pass' if ok else 'fail'
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', type=Path)
    ap.add_argument('--logs', type=Path, nargs='+', help='run logs (array mode); default RUN/lanes/logs/idx*.log')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    rep = evaluate(a.run, a.logs)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rep, indent=1) + '\n')
    keys = ('verdict', 'reason', 'measured', 'pack_reads', 'notes', 'smallest', 'largest', 'tasks_sqlite_ratio',
            'fingerprint_bytes_identical', 'comparison')
    print(json.dumps({k: rep.get(k) for k in keys if k in rep}, indent=1))
    return {'pass': 0, 'fail': 1}.get(rep['verdict'], 2)


if __name__ == '__main__':
    sys.exit(main())
