#!/usr/bin/env python3
"""Shared validator of chain independence across the active union (FIT_MODEL_V3.md §4.7, V3-015; IR5-001).

check_independence(tasks) takes the task records of the completion evidence (dicts with campaign, task, N, beta, seed, samples_sha256; s is
informational) and returns a list of problems: chains sharing (N, beta, seed) — the §4.7 key, applied identically to legacy records without
s and to new records with s (IR6-001) — a missing seed, or a shared samples.bin SHA-256. Used by
select_model_v3.verify_lineage (production eligibility) and union_check.py (finalize gate), so both apply the same rule."""
from collections import defaultdict

def check_independence(tasks):
    by_seed = defaultdict(list); by_hash = defaultdict(list); problems = []
    for t in tasks:
        k = (t['campaign'], int(t['task']))
        if t.get('seed') is None: problems.append(f'{k}: evidence record without seed'); continue
        by_seed[(int(t['N']), round(float(t['beta']), 12), int(t['seed']))].append(k)
        if t.get('samples_sha256'): by_hash[t['samples_sha256']].append(k)
        else: problems.append(f'{k}: evidence record without samples_sha256')
    dup_seed = [v for v in by_seed.values() if len(v) > 1]; dup_hash = [v for v in by_hash.values() if len(v) > 1]
    if dup_seed: problems.append(f'{len(dup_seed)} (N, beta, seed) shared by several chains, e.g. {dup_seed[:2]}')
    if dup_hash: problems.append(f'{len(dup_hash)} samples.bin archives shared by several chains, e.g. {dup_hash[:2]}')
    return problems
