#!/usr/bin/env python3
"""Checked Slurm queue queries shared by pack_nodes.py and submit_n2_analysis.py (RV3-004 / IR7-004 / IR9-003).

my_jobs(user=None, account=None): rows of {id, parent, count, name, state, qos, comment, dep, user} for the user's (or the account's) jobs.
A failed squeue call or a malformed line raises SystemExit: a scheduler-query failure is never an empty queue. Array identifiers
(1234_7, 1234_[0-31%8]) are accepted; `count` is the number of tasks a row stands for."""
from __future__ import annotations
import os, re, subprocess

def array_count(jobid: str) -> int:
    m = re.search(r'_\[([0-9,\-]+)(%\d+)?\]', jobid)
    if not m: return 1
    n = 0
    for part in m.group(1).split(','):
        lo, _, hi = part.partition('-'); n += int(hi or lo) - int(lo) + 1
    return n

def my_jobs(user: str | None = None, account: str | None = None) -> list[dict]:
    cmd = ['squeue', '-h', '-o', '%i|%j|%T|%q|%k|%E|%u']
    cmd += ['-A', account] if account else ['-u', user or os.environ.get('USER', '')]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0: raise SystemExit(f'squeue failed ({r.returncode}): {r.stderr.strip()[:200]}')
    rows = []
    for l in r.stdout.strip().splitlines():
        parts = l.split('|', 6)
        if len(parts) != 7 or not re.fullmatch(r'\d+(_(\d+|\[[0-9,%\-]+\]))?', parts[0]): raise SystemExit(f'malformed squeue line: {l!r}')
        i, name, st, q, com, dep, u = parts
        rows.append(dict(id=i, parent=int(i.split('_')[0]), count=array_count(i), name=name, state=st, qos=q, comment=com, dep=dep, user=u))
    return rows
