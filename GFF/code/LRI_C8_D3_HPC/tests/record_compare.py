#!/usr/bin/env python3
"""Stage 4b (PLAN A-PERF-2 "exact", A-RPL-4 for #4): a gate record of a candidate binary against the Stage-3 record of
the same test, with the run-specific fields removed (timing, host, environment, build commands, executable digests).
Equal records mean the candidate gave every value, count, maximum, position and histogram of the Stage-3 run.

  python3 -B tests/record_compare.py --kind forced_tiers NEW.json STAGE3.json [--output FILE]

Kinds:
  forced_tiers  tests/forced_tiers.py records (A-RPL-4): status, findings, counts_status, count_shortfalls, bounds,
                conversion_bound, sampling (max_seconds excepted) and every results entry (per sector and loop: points,
                graphs, levels, decision mismatches, the per-tier maxima with their points and histograms, breaches,
                graph levels, rounds without their seconds, counts) must be equal. S1-03's added fields
                ("breach_counts" per entry, "full_precision" per tier) are compared when both records hold them; a
                Stage-3 record made before them lacking them is no difference (a record lacking them against one that
                holds them still is).
Exit 0 when equal, 1 with the first differences otherwise. Python standard library only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DROP = {'seconds', 'wall_seconds', 'host', 'build', 'environment', 'utc', 'executables', 'sha256', 'command', 'max_seconds'}
KEEP = {'forced_tiers': ('status', 'findings', 'counts_status', 'count_shortfalls', 'bounds', 'conversion_bound', 'sampling', 'results')}
ADDED = {'forced_tiers': frozenset({'breach_counts', 'full_precision'})}   # S1-03: absent from records made before them


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in DROP}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def diff(a, b, path='', out=None, limit=20, added=frozenset()):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in a and k not in b and k in added:
                continue
            if k not in a or k not in b:
                out.append(f'{path}/{k}: only in {"new" if k in a else "stage3"}')
            else:
                diff(a[k], b[k], f'{path}/{k}', out, limit, added)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'{path}: lengths {len(a)} vs {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f'{path}[{i}]', out, limit, added)
    elif a != b:
        out.append(f'{path}: {str(a)[:120]} vs {str(b)[:120]}')
    return out


def compare(kind: str, new: dict, old: dict) -> list[str]:
    keys = KEEP[kind]
    a = strip({k: new.get(k) for k in keys})
    b = strip({k: old.get(k) for k in keys})
    return diff(a, b, added=ADDED.get(kind, frozenset()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kind', choices=sorted(KEEP), required=True)
    ap.add_argument('new', type=Path)
    ap.add_argument('stage3', type=Path)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    d = compare(a.kind, json.loads(a.new.read_text()), json.loads(a.stage3.read_text()))
    rec = {'schema': 'c8-d3-record-compare-1', 'kind': a.kind, 'new': str(a.new), 'stage3': str(a.stage3), 'compared': list(KEEP[a.kind]),
           'dropped': sorted(DROP), 'equal': not d, 'differences': d, 'status': 'passed' if not d else 'failed'}
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))
    return 0 if not d else 1


if __name__ == '__main__':
    sys.exit(main())
