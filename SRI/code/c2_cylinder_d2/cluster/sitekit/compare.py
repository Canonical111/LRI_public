#!/usr/bin/env python3
"""Compare output trees and raw cutoff sequences; no fitting, no continuum claim.

  outputs A B       file-by-file comparison of two output directories. Every
                    JSON leaf and CSV cell must be identical except for the
                    volatile keys (timings, timestamps). Used for the
                    old-code/new-code regression.
  raw-overlap NEW REF...
                    partial-sum differences of one raw solver record against
                    reference records of the same (order, lambda) on their
                    overlapping coefficient boxes. Used for the Expanse pilot.
  archive-overlaps ROOT ARCHIVE
                    raw-overlap for every cluster record under ROOT against the
                    archived records in ARCHIVE (data/hamiltonian/raw).

Standard library only, so it also runs outside the scientific environment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys

VOLATILE = {'seconds', 'elapsed', 'completed_utc', 'created_utc'}
SKIP_FILES = {'run_receipt.json', 'task_receipt.json'}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def leaves(value, prefix=''):
    """Yield (path, leaf) pairs of a parsed JSON value in a stable order."""
    if isinstance(value, dict):
        for key in sorted(value):
            yield from leaves(value[key], f'{prefix}/{key}')
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from leaves(item, f'{prefix}[{i}]')
    else:
        yield prefix, value


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def compare_values(a, b, ignore: set[str]) -> dict:
    la = dict(leaves(a))
    lb = dict(leaves(b))

    def volatile(path: str) -> bool:
        last = path.rsplit('/', 1)[-1].split('[', 1)[0]
        return last in ignore

    keys = sorted(set(la) | set(lb))
    structural = [k for k in keys if (k in la) != (k in lb) and not volatile(k)]
    differing, max_abs, max_rel, ignored = [], 0.0, 0.0, 0
    for k in keys:
        if k not in la or k not in lb:
            continue
        if volatile(k):
            ignored += la[k] != lb[k]
            continue
        x, y = la[k], lb[k]
        if x == y and type(x) is type(y):
            continue
        differing.append(k)
        if is_number(x) and is_number(y) and math.isfinite(x) and math.isfinite(y):
            d = abs(x - y)
            max_abs = max(max_abs, d)
            scale = max(abs(x), abs(y))
            if scale:
                max_rel = max(max_rel, d / scale)
    return {'leaves': len(keys), 'structural_differences': structural[:20],
            'n_structural_differences': len(structural), 'n_differing_leaves': len(differing),
            'differing_examples': differing[:20], 'max_abs_difference': max_abs,
            'max_rel_difference': max_rel, 'volatile_leaves_differing': ignored}


def parse(path: Path):
    if path.suffix == '.json':
        return json.loads(path.read_text())
    if path.suffix == '.csv':
        rows = list(csv.reader(io.StringIO(path.read_text())))
        out = []
        for row in rows:
            cells = []
            for cell in row:
                try:
                    cells.append(float(cell))
                except ValueError:
                    cells.append(cell)
            out.append(cells)
        return out
    return None


def compare_outputs(a: Path, b: Path, ignore: set[str]) -> dict:
    names_a = {p.name for p in a.iterdir() if p.is_file()}
    names_b = {p.name for p in b.iterdir() if p.is_file()}
    files = []
    for name in sorted((names_a | names_b) - SKIP_FILES):
        row = {'file': name}
        if name not in names_a or name not in names_b:
            row['status'] = 'only_in_' + ('a' if name in names_a else 'b')
            files.append(row)
            continue
        pa, pb = a / name, b / name
        if sha256(pa) == sha256(pb):
            row['status'] = 'identical_bytes'
        else:
            va, vb = parse(pa), parse(pb)
            if va is None or vb is None:
                row['status'] = 'different_bytes_unparsed'
            else:
                detail = compare_values(va, vb, ignore)
                row.update(detail)
                ok = detail['n_differing_leaves'] == 0 and detail['n_structural_differences'] == 0
                row['status'] = 'identical_except_volatile' if ok else 'different'
        files.append(row)
    identical = all(f['status'] in ('identical_bytes', 'identical_except_volatile') for f in files)
    return {'a': str(a), 'b': str(b), 'ignored_keys': sorted(ignore), 'skipped_files': sorted(SKIP_FILES),
            'files': files, 'all_identical': identical and bool(files)}


def raw_record(path: Path) -> dict:
    value = json.loads(path.read_text())
    if isinstance(value, dict) and isinstance(value.get('data'), dict) and 'raw' in value['data']:
        value = value['data']
    if not all(k in value for k in ('raw', 'order', 'lam', 'N')):
        raise ValueError(f'{path} is not a raw solver record')
    return value


def compare_raw(new: Path, refs: list[Path]) -> dict:
    a = raw_record(new)
    out = []
    for ref in refs:
        b = raw_record(ref)
        if (a['order'], a['lam']) != (b['order'], b['lam']):
            out.append({'reference': str(ref), 'skipped': 'different (order, lambda)'})
            continue
        n = min(a['N'], b['N'])
        xa, xb = a['raw']['Xchain'][:n], b['raw']['Xchain'][:n]
        diff = [abs(x - y) for x, y in zip(xa, xb)]
        rel = [d / max(abs(y), 1e-300) for d, y in zip(diff, xb)]
        checkpoints = sorted({c for c in (16, 32, 64, 128, 192, 256, 288, 320, 384, 512) if c <= n} | {n})
        parts = {}
        for pa in a['raw']['parts']:
            for pb in b['raw']['parts']:
                if pa['pairing'] == pb['pairing']:
                    parts[pa['pairing']] = max(abs(x - y) for x, y in zip(pa['X'][:n], pb['X'][:n]))
        out.append({'reference': str(ref), 'reference_N': b['N'], 'overlap_N': n,
                    'max_abs_difference': max(diff), 'max_rel_difference': max(rel),
                    'argmax_cutoff': 1 + diff.index(max(diff)),
                    'last_overlap_difference': xa[n - 1] - xb[n - 1],
                    'last_overlap_value_reference': xb[n - 1],
                    'differences_at_cutoffs': {str(c): xa[c - 1] - xb[c - 1] for c in checkpoints},
                    'max_abs_difference_by_pairing': parts,
                    'reference_grid': b.get('coefficient_file'),
                    'reference_cauchy_grid_comparison': b.get('cauchy_grid_comparison')})
    return {'record': str(new), 'order': a['order'], 'lam': a['lam'], 'N': a['N'],
            'coefficient_file': a.get('coefficient_file'), 'comparisons': out,
            'interpretation': 'Same regulated observable on overlapping finite boxes computed from different '
                              'coefficient grids. Differences measure Cauchy-grid/roundoff consistency only; '
                              'they are not a tail or continuum error bound.'}


def archive_overlaps(root: Path, archive: Path, paths: list[Path] | None = None) -> dict:
    """Compare every new cluster record under root with the archived records
    (data/hamiltonian/raw) of the same (order, lambda)."""
    refs = []
    for path in sorted(archive.glob('*.json')):
        try:
            r = raw_record(path)
        except (ValueError, KeyError):
            continue
        refs.append((r['order'], r['lam'], path))
    rows = []
    candidates = sorted(paths) if paths is not None else sorted(root.glob('**/cluster_k*_a*_N*.json'))
    for path in candidates:
        if path.name.endswith('_analysis.json'):
            continue
        rec = raw_record(path)
        match = [p for (k, lam, p) in refs if (k, lam) == (rec['order'], rec['lam'])]
        rows.append(compare_raw(path, match) if match else
                    {'record': str(path), 'order': rec['order'], 'lam': rec['lam'], 'N': rec['N'], 'comparisons': [],
                     'note': 'no archived record with this (order, lambda)'})
    return {'root': str(root), 'archive': str(archive), 'records': rows}


def regression_summary(out: Path, expect_old_vs_new: list[str], expect_shipped: list[str], runs_ok: bool,
                       meta: dict) -> dict:
    """Summarise regression.sh's reports. Missing expected reports count as failures."""
    import datetime
    import platform
    comparisons, missing = {}, []
    expected = [f'old_vs_new_{x}' for x in expect_old_vs_new] + [f'shipped_{x}' for x in expect_shipped]
    for name in expected:
        path = out / f'compare_{name}.json'
        if not path.is_file():
            missing.append(name)
            continue
        c = json.loads(path.read_text())
        comparisons[name] = {
            'all_identical': c['all_identical'], 'files': {f['file']: f['status'] for f in c['files']},
            'max_abs_difference': max([f.get('max_abs_difference', 0.0) for f in c['files']] + [0.0]),
            'max_rel_difference': max([f.get('max_rel_difference', 0.0) for f in c['files']] + [0.0])}
    old_vs_new = [comparisons[f'old_vs_new_{x}']['all_identical'] for x in expect_old_vs_new
                  if f'old_vs_new_{x}' in comparisons]
    identical = bool(expect_old_vs_new) and not missing and len(old_vs_new) == len(expect_old_vs_new) and all(old_vs_new)
    return dict(meta, created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), platform=platform.platform(),
                runs_succeeded=runs_ok, expected_reports=expected, missing_reports=missing,
                comparisons=comparisons, old_vs_new_identical=identical,
                passed=bool(runs_ok and identical and not missing))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    o = sub.add_parser('outputs', help='Compare two output directories file by file.')
    o.add_argument('a', type=Path)
    o.add_argument('b', type=Path)
    o.add_argument('--ignore', nargs='*', default=[], help='Extra volatile key names.')
    o.add_argument('--require-identical', action='store_true', help='Exit 1 unless all files match.')
    r = sub.add_parser('raw-overlap', help='Compare one raw record with references on overlapping boxes.')
    r.add_argument('new', type=Path)
    r.add_argument('refs', type=Path, nargs='+')
    g = sub.add_parser('regression-summary', help='Summarise regression.sh reports (fails on missing ones).')
    g.add_argument('out', type=Path)
    g.add_argument('--expect-old-vs-new', nargs='+', required=True)
    g.add_argument('--expect-shipped', nargs='*', default=[])
    g.add_argument('--runs-status', type=int, required=True, help='0 if every run and comparison succeeded')
    g.add_argument('--old', default='')
    g.add_argument('--new', default='')
    g.add_argument('--python', default='')
    v = sub.add_parser('archive-overlaps', help='Compare all new records under ROOT with archived records.')
    v.add_argument('root', type=Path)
    v.add_argument('archive', type=Path)
    v.add_argument('--records-from', type=Path, help='Compare exactly the record paths listed in this file.')
    for q in (o, r, v):
        q.add_argument('--out', type=Path)
    a = p.parse_args()
    if a.action == 'regression-summary':
        summary = regression_summary(a.out, a.expect_old_vs_new, a.expect_shipped, a.runs_status == 0,
                                     {'old_root': a.old, 'new_root': a.new, 'python': a.python})
        (a.out / 'regression_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('old_vs_new_identical =', summary['old_vs_new_identical'])
        for name in summary['missing_reports']:
            print(f'{name:34s} MISSING')
        for k, v in summary['comparisons'].items():
            print(f"{k:34s} identical={v['all_identical']!s:5s} max_abs={v['max_abs_difference']:.3g} "
                  f"max_rel={v['max_rel_difference']:.3g}")
        print('REGRESSION PASSED' if summary['passed'] else 'REGRESSION FAILED')
        sys.exit(0 if summary['passed'] else 1)
    if a.action == 'outputs':
        result = compare_outputs(a.a, a.b, VOLATILE | set(a.ignore))
    elif a.action == 'raw-overlap':
        result = compare_raw(a.new, a.refs)
    else:
        listed = None
        if a.records_from:
            listed = [Path(line) for line in a.records_from.read_text().splitlines() if line.strip()]
        result = archive_overlaps(a.root, a.archive, listed)
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)
    if a.action == 'outputs':
        for f in result['files']:
            extra = '' if f['status'].startswith('identical') or 'max_abs_difference' not in f else \
                f" (max abs {f['max_abs_difference']:.3g}, max rel {f['max_rel_difference']:.3g}, {f['n_differing_leaves']} leaves)"
            print(f"{f['status']:28s} {f['file']}{extra}")
        print('ALL IDENTICAL' if result['all_identical'] else 'DIFFERENCES FOUND')
        if a.require_identical and not result['all_identical']:
            sys.exit(1)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
