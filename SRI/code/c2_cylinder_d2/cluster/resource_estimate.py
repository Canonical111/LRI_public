#!/usr/bin/env python3
"""Estimate two large array allocations, not peak RAM, total disk or runtime."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import scipy
from scipy.fft import next_fast_len


def estimate(cutoff: int, oversample: int) -> dict:
    if cutoff < 4 or oversample < 3:
        raise ValueError('cutoff must be >=4; oversample must be >=3.')
    k = cutoff + 1
    m = next_fast_len(oversample * k)
    if m % 2:
        m = next_fast_len(m + 1)
    final = 6 * k**3 * 8
    temporary = 6 * (m // 2 + 1) * k**2 * 16
    return {'N': cutoff, 'K': k, 'M': m, 'oversample': oversample,
            'coefficient_bytes': final, 'temporary_bytes': temporary,
            'coefficient_GB_decimal': final / 1e9, 'temporary_GB_decimal': temporary / 1e9,
            'coefficient_GiB': final / 2**30, 'temporary_GiB': temporary / 2**30,
            'N_cubed_relative_to_384': (cutoff / 384)**3}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cutoff', nargs='+', type=int, default=[384, 512, 768, 1024])
    p.add_argument('--oversample', type=int, default=4)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    try:
        result = {'scipy_version': scipy.__version__, 'allocation_estimates': [estimate(n, a.oversample) for n in a.cutoff],
                  'scope': 'Array storage only. Excludes array headers, FFT work, per-worker temporaries, convolutions, smaller grids and operating-system overhead. Not a peak-RAM, total-disk, benchmark or wall-time prediction.'}
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2) + '\n'
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
