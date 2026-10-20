#!/usr/bin/env python3
"""A-ASM-3: tools/assemble.py combine(order=7), the vendored order-8 assembly at order 7, applied to the 20 merged
replicate arrays of the 2026 symmetry C7(2) production (reference/c7d2_production_2026, byte copies) reproduces its
C7_result.json to relative 1e-12: C7 = -3876.1260927949925, SE 0.5244496690956952, the power correction and its SE,
the power-free C7 and its SE, and every coefficient. Each merged.json must be the one C7_result.json was assembled
from (its sha256). Read-only; no bootstrap. The CPU- and numpy-dependent last bits (2 ulp on the C63d Mac) are what
the 1e-12 bound absorbs. Usage: python3 -B tests/compat_2026.py [--run DIR] [--output FILE]"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from assemble import check_combination, combine  # noqa: E402
from common import object_hash  # noqa: E402

RUN = ROOT / 'reference/c7d2_production_2026'
FIELDS = ('C7_full', 'sampling_standard_error', 'power_correction', 'power_correction_se', 'power_free_C7', 'power_free_se')


def run(directory: Path, rel: float = 1e-12) -> dict:
    m = json.loads((directory / 'manifest.json').read_bytes())
    res = json.loads((directory / 'C7_result.json').read_bytes())
    if m['schema'] != 'c7-d2-production-1':
        raise ValueError('expected the version-1 C7(2) production plan')
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
    for g in m['groups']:
        p = directory / 'groups' / g['name']
        cfg = json.loads((p / 'config.json').read_bytes())
        raw = (p / 'merged.json').read_bytes()
        d = json.loads(raw)
        if hashlib.sha256(raw).hexdigest() != res['merged_sha256'][g['name']]:
            raise ValueError(f'{g["name"]}: merged.json is not the one C7_result.json was assembled from')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d['payload_sha256']:
            raise ValueError(f'{g["name"]}: merged payload corruption')
        ar[cfg['sector']][cfg['campaign']][cfg['L']] = np.asarray(d['batches'], float)
    if m['primitive_mode'] != 'recompute':
        raise ValueError('the 2026 production recomputed the primitives (no retained offset)')
    r = combine(ar, order=7, bootstrap=0)
    check_combination(r)
    pairs = {k: (r[k], res[k]) for k in FIELDS}
    pairs.update({f'coefficients[{i}]': (x, y) for i, (x, y) in enumerate(zip(r['coefficients'], res['coefficients']))})
    relerr = {k: (abs(x - y) / abs(y) if y else abs(x)) for k, (x, y) in pairs.items()}
    bad = {k: v for k, v in relerr.items() if v > rel}
    out = dict(schema='c8-d2-gate-1', gate='A-ASM-3 compat_2026', passed=not bad, run=str(directory.relative_to(ROOT)),
               manifest_sha256=hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest(),
               relative_tolerance=rel, max_relative_difference=max(relerr.values()), relative_differences=relerr,
               C7_full=r['C7_full'], published_C7_full=res['C7_full'], bitwise_identical_C7=r['C7_full'] == res['C7_full'],
               ulp_offset_C7=abs(r['C7_full'] - res['C7_full']) / float(np.spacing(abs(res['C7_full']))),
               sampling_standard_error=r['sampling_standard_error'], gates=r['gates'],
               lower_order_checks=r['lower_order_checks'], power_null_checks=r['power_null_checks'],
               numpy=np.__version__, failures=bad)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', type=Path, default=RUN)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    out = run(a.run.resolve())
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(out, indent=1, default=str) + '\n')
    print(json.dumps({k: out[k] for k in ('passed', 'C7_full', 'published_C7_full', 'ulp_offset_C7',
                                           'max_relative_difference', 'numpy')}, indent=1))
    return 0 if out['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
