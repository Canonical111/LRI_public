#!/usr/bin/env python3
"""Gate 5 (c)-(e): the forest identity on the builder's actual subgraph masks (PLAN.md A.3 gate 5; round-1 R02).

Port of the C63d recon's pre-check (LRI_C8_D3_HPC_loop/recon/cost_d3/forest_check.py, byte copy at c8-rb), which
compared size_probe.cpp's masks with C8(1)'s inventories. The gate reads instead the side files that H1's pinned
builders write when J-GEN-D3 regenerates them (A.2 step 2a: L{7,8}_{free,power}.subgraphs.txt; build_free.cpp:15,33,
build_power.cpp:15,34), with a strict reader: header "n NG"; per class three lines, "gi key aut orbit D_G s_G nlog
npow", the nlog log-subgraph vertex masks, the npow power-subgraph vertex masks; list lengths equal to the header
counts; no trailing data.

  (c) each side file is byte-identical to C8(1)'s L<L>_inventory.txt (reference/c8d1_inputs8; sha256 and bytes
      recorded); per (L, sector) 0 id, key, D_G or s_G mismatches and 0 differing log- or power-subgraph lists
      against that file parsed; per class nlog, npow, key, D_G and s_G equal H1's published `log_subgraphs`,
      `power_subgraphs`, `key`, `denominator` and `mass_numerator`;
  (d) the compatible log-subgraph families (nested, or at most one common vertex; the empty family included) are
      counted from the side-file masks by this file's own recursion (as size_probe.cpp:38, not H1's
      forest_counts.py): the totals equal C8(1)'s L<L>_summary.json `forests` (873,108 at L7, 11,254,373 at L8), and
      per power-free class the count equals H1's published free-sector `forests` field;
  (e) supplementary, with --probe DIR: size_probe's masks_L<L>.txt lists equal the side files' for every class.
Usage: forest_check.py --side DIR --c8d1 reference/c8d1_inputs8 --inventory H1_TREE [--probe DIR] [--loops 7,8]
       --output FILE
Exit 0 when (c) and (d) pass (and (e) when given), 1 otherwise, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

FORESTS = {7: 873108, 8: 11254373}
SECTORS = ('free', 'power')


class Bad(Exception):
    pass


def read_side(p: Path, n_fields: int = 8) -> tuple[int, list[dict]]:
    """Strict reader of a side file or of C8(1)'s L<L>_inventory.txt (8 header fields per class), or of size_probe's
    masks_L<L>.txt (n_fields = 4: gi nlog npow forests_log)."""
    data = p.read_bytes()
    if not data.endswith(b'\n'):
        raise Bad(f'{p}: no final newline')
    lines = data[:-1].split(b'\n')
    head = lines[0].split()
    if len(head) != 2:
        raise Bad(f'{p}: header {lines[0][:60]!r} is not "n NG"')
    n, ng = int(head[0]), int(head[1])
    if len(lines) != 1 + 3 * ng:
        raise Bad(f'{p}: {len(lines) - 1} lines after the header for {ng} classes (3 per class expected)')
    rows = []
    for i in range(ng):
        h = [int(x) for x in lines[1 + 3 * i].split()]
        subs = [int(x) for x in lines[2 + 3 * i].split()]
        pw = [int(x) for x in lines[3 + 3 * i].split()]
        if len(h) != n_fields:
            raise Bad(f'{p}: class {i}: {len(h)} header fields, expected {n_fields}')
        if n_fields == 8:
            r = dict(gi=h[0], key=h[1], aut=h[2], orbit=h[3], den=h[4], sg=h[5], nlog=h[6], npow=h[7])
        else:
            r = dict(gi=h[0], nlog=h[1], npow=h[2], forests=h[3])
        if len(subs) != r['nlog'] or len(pw) != r['npow']:
            raise Bad(f'{p}: class {i}: list lengths {len(subs)}, {len(pw)} differ from the header counts {r["nlog"]}, {r["npow"]}')
        r['subs'], r['pw'] = subs, pw
        rows.append(r)
    return n, rows


def popcount(x: int) -> int:
    return bin(x).count('1')


def forests(subs: list[int]) -> int:
    """Number of families of pairwise compatible log subgraphs (nested or sharing at most one vertex), the empty family
    included; own recursion over candidate bitsets with memoization."""
    n = len(subs)
    comp = [0] * n
    for i in range(n):
        a = subs[i]
        for j in range(i + 1, n):
            b = subs[j]
            if (a & b) == a or (a & b) == b or popcount(a & b) <= 1:
                comp[i] |= 1 << j
    memo: dict[int, int] = {}

    def rec(cand: int) -> int:
        v = memo.get(cand)
        if v is not None:
            return v
        total = 1
        m = cand
        while m:
            low = m & -m
            i = low.bit_length() - 1
            m ^= low
            total += rec(m & comp[i])
        memo[cand] = total
        return total
    return rec((1 << n) - 1)


def check(a) -> dict:
    loops = [int(x) for x in a.loops.split(',')]
    out = {}
    for L in loops:
        ref = Path(a.c8d1) / f'L{L}_inventory.txt'
        n1, d1 = read_side(ref)
        summary = json.loads((Path(a.c8d1) / f'L{L}_summary.json').read_text())
        inv = json.loads((Path(a.inventory) / f'inventory_L{L}.json').read_text())
        res = {}
        counted: dict[str, tuple[int, list[int]]] = {}
        for s in SECTORS:
            e = []
            p = Path(a.side) / f'L{L}_{s}.subgraphs.txt'
            try:
                n2, rows = read_side(p)
            except (OSError, ValueError, Bad) as ex:
                res[s] = dict(passed=False, errors=[str(ex)], error_count=1)
                continue
            data = p.read_bytes()
            identical = data == ref.read_bytes()
            if not identical:
                e.append(f'{p}: not byte-identical to {ref.name}')
            if n2 != L + 1 or n1 != L + 1 or len(rows) != len(d1):
                e.append(f'{p}: n {n2} / classes {len(rows)} differ from {ref.name} (n {n1}, {len(d1)} classes)')
            mism = dict(id=0, key=0, D_G=0, s_G=0, log_lists=0, power_lists=0)
            pub = dict(nlog=0, npow=0, key=0, D_G=0, s_G=0)
            rows_inv = inv[s]
            for i, (r, q) in enumerate(zip(rows, d1)):
                mism['id'] += r['gi'] != q['gi'] or r['gi'] != i
                mism['key'] += r['key'] != q['key']
                mism['D_G'] += r['den'] != q['den']
                mism['s_G'] += r['sg'] != q['sg']
                mism['log_lists'] += r['subs'] != q['subs']
                mism['power_lists'] += r['pw'] != q['pw']
                if i < len(rows_inv):
                    t = rows_inv[i]
                    pub['nlog'] += r['nlog'] != t['log_subgraphs']
                    pub['npow'] += r['npow'] != t['power_subgraphs']
                    pub['key'] += r['key'] != t['key']
                    pub['D_G'] += r['den'] != t['denominator']
                    pub['s_G'] += r['sg'] != t['mass_numerator']
            if len(rows_inv) != len(rows):
                e.append(f'inventory_L{L}.json {s}: {len(rows_inv)} classes, side file {len(rows)}')
            if any(mism.values()):
                e.append(f'{p}: mismatches against {ref.name}: {mism}')
            if any(pub.values()):
                e.append(f'{p}: mismatches against inventory_L{L}.json {s}: {pub}')
            # (d) forests, counted once per distinct side-file content
            h = c.sha256_bytes(data)
            if h not in counted:
                per = [forests(r['subs']) for r in rows]
                counted[h] = (sum(per), per)
            total, per = counted[h]
            fe = []
            if total != summary['forests'] or (L in FORESTS and total != FORESTS[L]):
                fe.append(f'L{L}: {total} forests; C8(1) summary {summary["forests"]}, expected {FORESTS.get(L)}')
            free_rows = inv['free']
            pf = [i for i, r in enumerate(rows) if r['npow'] == 0]
            bad_pc = [i for i in pf if i < len(free_rows) and free_rows[i].get('forests') != per[i]]
            if bad_pc:
                fe.append(f'L{L}: {len(bad_pc)} power-free classes whose count differs from the published forests (first {bad_pc[:5]})')
            # (e) the size probe's lists
            probe = None
            if a.probe:
                pp = Path(a.probe) / f'masks_L{L}.txt'
                try:
                    _, pr = read_side(pp, n_fields=4)
                    pdiff = sum(r['subs'] != q['subs'] or r['pw'] != q['pw'] or r['gi'] != q['gi'] for r, q in zip(rows, pr))
                    pdiff += abs(len(pr) - len(rows))
                    pfor = sum(q['forests'] != x for q, x in zip(pr, per))
                    probe = dict(passed=pdiff == 0 and pfor == 0, classes=len(pr), list_mismatches=pdiff, forest_mismatches=pfor)
                except (OSError, ValueError, Bad) as ex:
                    probe = dict(passed=False, error=str(ex))
            res[s] = dict(passed=not e and not fe and (probe is None or probe['passed']), c_passed=not e, d_passed=not fe,
                          side_file=dict(bytes=len(data), sha256=h, identical_to_c8d1=identical),
                          c8d1_file=dict(bytes=ref.stat().st_size, sha256=c.sha256_file(ref)),
                          classes=len(rows), mismatches_vs_c8d1=mism, mismatches_vs_published=pub,
                          forests_total=total, power_free_classes=len(pf), power_free_forest_mismatches=len(bad_pc),
                          max_log_subgraphs=max((r['nlog'] for r in rows), default=0), e_size_probe=probe,
                          errors=(e + fe)[:50], error_count=len(e) + len(fe))
        out[f'L{L}'] = res
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--side', required=True, help='directory with L{7,8}_{free,power}.subgraphs.txt')
    ap.add_argument('--c8d1', required=True, help='reference/c8d1_inputs8')
    ap.add_argument('--inventory', required=True, help='the verified H1 copy (inventory_L*.json)')
    ap.add_argument('--probe', help='directory with size_probe masks_L{7,8}.txt (supplementary (e))')
    ap.add_argument('--loops', default='7,8')
    ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    c.refuse_c62d(a.output, 'output')
    try:
        res = check(a)
    except (OSError, ValueError, KeyError, Bad) as ex:
        c.die(f'forest_check: {ex}')
    flat = [v for L in res.values() for v in L.values()]
    c_ok = all(v.get('c_passed') for v in flat)
    d_ok = all(v.get('d_passed') for v in flat)
    e_ok = all((v.get('e_size_probe') or {}).get('passed', True) for v in flat)
    passed = bool(flat) and c_ok and d_ok and e_ok
    c.write_json(a.output, dict(schema='c8-d3-forest-check-1', gate='5 (c)-(e) forest identity on the builder masks',
                                passed=passed, c_masks=c_ok, d_forests=d_ok, e_probe=e_ok if a.probe else None, loops=res))
    for L, v in res.items():
        for s, r in v.items():
            print(f'{L} {s}: {"PASS" if r["passed"] else "FAIL"} forests {r.get("forests_total")}' + ('' if r['passed'] else f' {r["errors"][:3]}'))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
