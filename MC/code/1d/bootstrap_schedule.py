#!/usr/bin/env python3
"""Deterministic block-bootstrap schedule shared by fit_fss.py and quotients.py (FIT_PLAN.md §3.6).

block_indices(seed, s, N, beta, replica, draw, nblocks) returns the resampled block indices for one chain (identified by
its group coordinates and replica number) in bootstrap draw `draw`. Two programs calling it with the same arguments get
identical indices, so estimators computed from them are evaluated on the same resamples and can be compared draw by draw.
The key is built from integers only (s and beta are quantised to 1e-6 and 1e-12) to avoid floating-point representation
differences between machines.
"""
from __future__ import annotations
import hashlib
import numpy as np

def campaign_code(campaign) -> int:
    """Stable non-negative integer for a campaign name (None or '' -> 0). Two independent campaigns at identical
    (s, N, beta, replica) coordinates thereby get independent resampling streams (FITV3-003); the same measurement keeps
    the same indices in every estimator."""
    if not campaign: return 0
    return int.from_bytes(hashlib.blake2b(str(campaign).encode(), digest_size=4).digest(), 'little')

def block_indices(seed: int, s: float, N: int, beta: float, replica: int, draw: int, nblocks: int, campaign=None) -> np.ndarray:
    key = [int(seed), int(round(float(s) * 1e6)), int(N), int(round(float(beta) * 1e12)), int(replica), int(draw), campaign_code(campaign)]
    if any(k < 0 for k in key): raise ValueError(f'schedule key must be non-negative: {key}')
    rng = np.random.default_rng(np.random.SeedSequence(key))
    return rng.integers(nblocks, size=nblocks)
