"""Checked Sobol export, adapted from the supplied C7 production.py.

The worker adds independent per-graph digital shifts. One full graph-summed
randomized replicate is a statistical unit; points and chunks are not.
"""
from __future__ import annotations

import struct
import numpy as np
import scipy
from scipy.stats import qmc

from io_utils import digest


def leading_blocks_nonsingular(matrices, bits):
    x = np.asarray(matrices, dtype=np.uint64).copy()
    one = np.uint64(1)
    if x.ndim != 2 or x.shape[1] != bits:
        return False
    for k in range(bits):
        shift = np.uint64(bits - 1 - k)
        if not (((x[:, k] >> shift) & one) == one).all():
            return False
        x[:, k + 1:] ^= ((x[:, k + 1:] >> shift) & one) * x[:, k:k + 1]
    return True


def make_net(path, replicates, dimensions, bits, seed):
    if replicates < 2 or not 1 <= dimensions <= 31 or not 32 <= bits <= 60:
        raise ValueError("Invalid Sobol dimensions, precision, or replicate count")
    rng = np.random.default_rng(seed)
    power = 10
    count = 1 << power
    with path.open("xb") as stream:
        stream.write(struct.pack("<III", replicates, dimensions, bits))
        for _ in range(replicates):
            engine = qmc.Sobol(
                d=dimensions, scramble=True, bits=bits,
                seed=int(rng.integers(1, 2**32 - 1)),
            )
            matrices = engine._sv.copy()
            state = engine._shift.copy()
            points = np.empty((count, dimensions), dtype=np.uint64)
            for i in range(count):
                if i:
                    state ^= matrices[:, (i & -i).bit_length() - 1]
                points[i] = state
            if not np.array_equal(
                points.astype(np.float64) / 2**bits, engine.random_base2(power)
            ):
                raise ArithmeticError("Sobol public-API reconstruction failed")
            if not leading_blocks_nonsingular(matrices, bits):
                raise ArithmeticError("Sobol GF(2) stratification check failed")
            stream.write(matrices.astype("<u8").tobytes())
    return {
        "scipy": scipy.__version__, "replicates": replicates,
        "dimensions": dimensions, "bits": bits, "seed": seed,
        "public_api_points_checked": count * replicates,
        "all_leading_generator_blocks_nonsingular": True,
        "sha256": digest(path),
        "limit": "Columns >=10 and bits below 2^-53 are not compared pointwise with the public API.",
    }
