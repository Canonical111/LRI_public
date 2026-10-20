"""Shared validation of merged level records (PLAN.md rev 7). Used by levelcheck.py, assemble.py and rounding.py.

validate_level(path) checks, and raises LevelError otherwise:
  - the file parses and has header, subset, sectors, per_sector and totals;
  - the file name is exactly the canonical name for its header and subset (tools/merge.py level_name);
  - sectors_total = L!/2; the sector set is exactly all sectors (subset all, mod 1) or {s : s mod 10 = 0}
    (subset mod10, mod 10); the per_sector keys equal the sector list;
  - every vector has width 2*(L + [mode = J]) and finite values, totals included (NaN/inf rejected explicitly);
  - totals equal the sum of the per-sector values (50-digit mpmath, relative 1e-30).
Returns the parsed record (and, with with_sha=True, the SHA256 of exactly the bytes that were parsed).
"""
import json, math, hashlib
from pathlib import Path
import mpmath as mp

KIND_TAG = {'double8': 'dbl', 'reference-longdouble': 'ld'}


class LevelError(Exception):
    pass


def level_name(header, subset):
    name = f"L{header['L']}_{header['mode']}_{header['stratum']}_N{header['N']}.{KIND_TAG[header['kind']]}"
    if int(header['perturb']):
        name += f".pert{header['perturb']}"
    if int(header['comp']) != 1:
        name += f".comp{header['comp']}"
    if subset == 'mod10':
        name += '.mod10'
    return name + '.json'


def validate_level(path, with_sha=False):
    p = Path(path)
    try:
        raw = p.read_bytes(); rec = json.loads(raw)
        h = rec['header']; subset = rec['subset']; secs = rec['sectors']; per = rec['per_sector']; tot = rec['totals']
        L = int(h['L']); mode = h['mode']
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise LevelError(f'{p.name}: unreadable or malformed ({e})')
    if h.get('kind') not in KIND_TAG or L not in (5, 6) or mode not in ('H', 'J'):
        raise LevelError(f'{p.name}: unsupported kind/L/mode')
    if p.name != level_name(h, subset):
        raise LevelError(f'{p.name}: file name does not match header/subset (expected {level_name(h, subset)})')
    total = math.factorial(L) // 2
    if int(h['sectors_total']) != total:
        raise LevelError(f'{p.name}: sectors_total {h["sectors_total"]} != {total}')
    if subset == 'all' and int(h['mod']) == 1:
        expected = list(range(total))
    elif subset == 'mod10' and int(h['mod']) == 10:
        expected = [s for s in range(total) if s % 10 == 0]
    else:
        raise LevelError(f'{p.name}: subset {subset} with header mod {h["mod"]}')
    if sorted(secs) != expected or sorted(int(k) for k in per) != expected:
        raise LevelError(f'{p.name}: sector coverage differs from the required set ({len(secs)} sectors listed, {len(per)} vectors)')
    width = 2 * (L + (1 if mode == 'J' else 0))
    if len(tot) != width:
        raise LevelError(f'{p.name}: totals width {len(tot)} != {width}')
    with mp.workdps(50):
        acc = [mp.mpf(0)] * width
        for s in expected:
            v = per[str(s)]
            if len(v) != width:
                raise LevelError(f'{p.name}: sector {s} width {len(v)} != {width}')
            for j, x in enumerate(v):
                try:
                    y = mp.mpf(x)
                except (ValueError, TypeError):
                    raise LevelError(f'{p.name}: sector {s} value {j} is not a number')
                if not mp.isfinite(y):
                    raise LevelError(f'{p.name}: non-finite value in sector {s}')
                acc[j] += y
        for j in range(width):
            try:
                t = mp.mpf(tot[j])
            except (ValueError, TypeError):
                raise LevelError(f'{p.name}: totals[{j}] is not a number')
            if not mp.isfinite(t):
                raise LevelError(f'{p.name}: non-finite totals[{j}]')
            if not abs(t - acc[j]) <= mp.mpf('1e-30') * max(abs(acc[j]), mp.mpf(1)):
                raise LevelError(f'{p.name}: totals[{j}] inconsistent with the per-sector values')
    return (rec, hashlib.sha256(raw).hexdigest()) if with_sha else rec
