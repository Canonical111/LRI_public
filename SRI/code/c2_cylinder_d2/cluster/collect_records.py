#!/usr/bin/env python3
"""Index arbitrary-N raw records without historical file-name routing.

No tail fitting, highest-cutoff selection or continuum conversion is performed.
Every numerical/grid variant is retained. Optional overlap differences are
finite-box diagnostics, not bounds on the physical coefficient.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

# <prefix>_k<order>_a<lambda>[_N<N>].json, e.g. cluster_k1_a0.1_N512.json, extended_k1_a0.1.json
RECORD_NAME = re.compile(r'_k(\d+)_a([0-9.eE+-]+?)(?:_N(\d+))?\.json$')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sequence_problems(label: str, seq: object, n: object) -> list[str]:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return [f'{label}: declared length {n!r} is not a positive integer']
    if not isinstance(seq, list):
        return [f'{label}: missing or not a list']
    if len(seq) != n:
        return [f'{label}: {len(seq)} values, declared {n}']
    for i, x in enumerate(seq):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            return [f'{label}: non-finite or non-numeric value at index {i}']
    return []


def validate_record(path: Path, value: object) -> list[str]:
    """Semantic checks of one raw solver record, shared by collect_records.py and
    cluster/sitekit/merge_records.py: finite numeric sequences of the declared
    length (raw.Xchain and every raw part: N; mixed.Xmixed: mixed.Nmax),
    embedded cutoffs, order and lambda consistent with the record and with its
    file name."""
    if not isinstance(value, dict):
        return ['not a JSON object']
    missing = [k for k in ('raw', 'order', 'lam', 'N', 'mixed', 'two_point') if not isinstance(value.get(k), (dict, int, float)) or isinstance(value.get(k), bool)]
    if missing:
        return [f'missing or invalid fields: {missing}']
    n, order, lam = value['N'], value['order'], value['lam']
    problems = []
    if order not in (1, 2, 3):
        problems.append(f'order {order!r} is not 1, 2 or 3')
    if isinstance(lam, bool) or not isinstance(lam, (int, float)) or not math.isfinite(lam) or lam <= 0:
        problems.append(f'lambda {lam!r} is not a positive number')
    raw, mixed, two = value['raw'], value['mixed'], value['two_point']
    if not all(isinstance(x, dict) for x in (raw, mixed, two)):
        return problems + ['raw, mixed and two_point must be objects']
    problems += _sequence_problems('raw.Xchain', raw.get('Xchain'), n)
    if raw.get('Nmax') != n:
        problems.append(f"raw.Nmax {raw.get('Nmax')!r} differs from N {n!r}")
    parts = raw.get('parts')
    if not isinstance(parts, list) or not parts:
        problems.append('raw.parts missing')
    else:
        for part in parts:
            label = f"raw.parts[{part.get('pairing') if isinstance(part, dict) else '?'}]"
            problems += _sequence_problems(label, part.get('X') if isinstance(part, dict) else None, n)
    problems += _sequence_problems('mixed.Xmixed', mixed.get('Xmixed'), mixed.get('Nmax'))
    for name, sub in (('raw', raw), ('mixed', mixed), ('two_point', two)):
        if 'lam' in sub and sub['lam'] != lam:
            problems.append(f'{name}.lam {sub["lam"]!r} differs from lambda {lam!r}')
        if 'order' in sub and sub['order'] != order:
            problems.append(f'{name}.order {sub["order"]!r} differs from order {order!r}')
    m = RECORD_NAME.search(path.name)
    if not m:
        problems.append(f'file name {path.name} carries no _k<order>_a<lambda>')
    else:
        try:
            name_lam = float(m.group(2))
        except ValueError:
            name_lam = None
        if int(m.group(1)) != order or name_lam != lam or (m.group(3) is not None and int(m.group(3)) != n):
            problems.append(f'file name {path.name} does not match order {order}, lambda {lam}, N {n}')
    return problems


def index_records(roots: list[Path], pattern: str, overlaps: bool, paths: list[Path] | None = None) -> dict:
    """Index the records found by pattern under roots, or exactly the given paths."""
    if paths is None:
        paths = sorted({p.resolve() for root in roots for p in root.glob(pattern) if p.is_file()})
    else:
        paths = sorted({Path(p).resolve() for p in paths})
    result: list[dict] = []
    arrays: dict[str, list[float]] = {}
    rejected = []
    for path in paths:
        try:
            value = json.loads(path.read_text())
        except (ValueError, OSError) as exc:
            raise ValueError(f'Cannot read {path}: {exc}') from exc
        if isinstance(value, dict) and isinstance(value.get('data'), dict) and 'raw' in value['data']:
            value = value['data']
        if not isinstance(value, dict) or not all(k in value for k in ['raw', 'order', 'lam', 'N']):
            rejected.append({'path': str(path), 'reason': 'not a raw solver record'})
            continue
        invalid = validate_record(path, value)
        if invalid:
            raise ValueError(f'Invalid record {path}: {"; ".join(invalid)}')
        import numpy as np
        x = np.asarray(value['raw']['Xchain'], dtype=float)
        receipt_path = path.parent / 'task_receipt.json'
        receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        job = receipt.get('job', {})
        if job and (job['order'] != value['order'] or job['cutoff'] != value['N'] or value['lam'] not in job['lambda']):
            raise ValueError(f'Record does not match task receipt: {path}')
        grid = {k: job[k] for k in ['oversample', 'radius_cost'] if k in job}
        grid['coefficient_file'] = value.get('coefficient_file')
        row = {'path': str(path), 'sha256': sha256(path), 'order': value['order'], 'lam': value['lam'],
               'N': value['N'], 'grid': grid, 'mixed_cutoff': value.get('mixed', {}).get('Nmax'),
               'collapsed_cutoff': job.get('collapsed_cutoff'), 'task_receipt': str(receipt_path) if receipt else None,
               'raw_chain_at_N': float(x[-1]), 'physical_C2_claimed': False}
        sidecar = path.with_name(path.stem + '_analysis.json')
        if sidecar.is_file():
            an = json.loads(sidecar.read_text())
            tail = an.get('leading_tail')
            row['analysis_sidecar'] = str(sidecar)
            row['leading_tail_cutoff'] = tail.get('N') if isinstance(tail, dict) else None
        result.append(row)
        arrays[str(path)] = x.tolist()
    comparisons = []
    if overlaps:
        import numpy as np
        for i, a in enumerate(result):
            for b in result[i+1:]:
                if (a['order'], a['lam']) != (b['order'], b['lam']):
                    continue
                n = min(a['N'], b['N'])
                difference = np.asarray(arrays[a['path']][:n]) - np.asarray(arrays[b['path']][:n])
                comparisons.append({'a': a['path'], 'b': b['path'], 'overlap_N': n,
                                    'max_abs_raw_chain_difference': float(np.max(np.abs(difference))),
                                    'interpretation': 'Same regulated observable on overlapping finite boxes. Not a tail or continuum error bound; check grid metadata before calling this independent.'})
    return {'records': result, 'overlap_comparisons': comparisons, 'ignored_files': rejected,
            'scope': 'Index only. No records silently replaced, and no continuum estimate or precision claimed.'}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-root', type=Path, nargs='+', default=[])
    p.add_argument('--pattern', default='**/cluster_k*_a*_N*.json')
    p.add_argument('--records-from', type=Path,
                   help='Index exactly the record paths listed in this file (one per line) instead of globbing.')
    p.add_argument('--compare-overlaps', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        paths = None
        if a.records_from:
            paths = [Path(line) for line in a.records_from.read_text().splitlines() if line.strip()]
        elif not a.input_root:
            raise ValueError('Give --input-root or --records-from.')
        if any(not path.is_dir() for path in a.input_root):
            raise ValueError('Every input root must be an existing directory.')
        out = index_records(a.input_root, a.pattern, a.compare_overlaps, paths)
        if not out['records']:
            raise ValueError('No raw solver records match this input and pattern.')
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
        print(f'INDEXED {len(out["records"])} raw records; {len(out["overlap_comparisons"])} overlap comparisons -> {a.output}')
    except (OSError, ValueError, KeyError) as exc:
        p.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
