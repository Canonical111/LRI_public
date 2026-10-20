#!/usr/bin/env python3
"""A-INV-3: the L8 gates of the d=2 inventory, with L7 controls, on a J-GEN-2 stage (x86-64 build outputs).

The stage holds L{7,8}_{free,power}/ (G-files and inventory.json from bin/gen/build_*) and the subgraph side files
L{7,8}_{free,power}.subgraphs.txt. Every gate runs (no early stop) and writes gates/<name>.json; gates/summary.json
records the verdicts. All gates are hard; any count mismatch stops Stage 1 until it is explained.

  a zero_dim      gen/zero_dim_check.py on classes1..8: sum wA = 49985915/768 and sum wB = 33994099/6912 at L8,
                  every L passes
  b metadata      the builders' metadata equals C8(1)'s L{7,8}_inventory.txt for every class: key, D_G, s_G and the
                  log- and power-subgraph masks in order (the side files are byte-identical; inventory.json fields
                  agree)
  c zeros         exact-zero kernels = forest_subsets.json free_articulation (2,511) and power_articulation (2,340)
  d primitives    primitive set = free_primitive (248); every L8 primitive is a finite kernel with s_G != 4
  e counts        16,798 free and 4,891 power finite kernels; 734 and 555 of them with s_G = 4; selections 16,064
                  and 4,336 (L7: 2,441 and 709, all selected)
  f coverage      gen/coverage.py: every class in exactly one category, 2,254 / 3,886 / 248 / 15,816 / 4,336
  g edge_forests  bin/gen/check_edge_forests at n=9 on all 7,231 power classes: zero failures (L7: 1,091)
  h kirchhoff     gen/kirchhoff.py exact on 64 free + 64 power L8 kernels and 8 + 8 L7 kernels, two points each
  i sizes         M <= 4,032 and T <= 280 at L8
  j rates         every finite G-file parses completely; for 0 < s < 2^E - 1 every rate entry is a half-integer in
                  [0.5, 50] obeying the parity floor (>= 1 for even |S|); the entries at s = 0 and 2^E - 1 are 0
  k forests       gen/forest_counts.py from C8(1)'s masks: totals 11,254,373 (L8) and 873,108 (L7), and equal to
                  the builder's `forests` for every power-free class

Usage: python3 -B gen/gates.py --stage S --bin BIN [--jobs N] [--inject-fail GATE]
  (also C8_GEN_INJECT_FAIL=GATE; a test hook: the named gate is reported failed and the exit status is 1)
Exit status 0 only when every gate passes."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from decimal import Decimal
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C8D1 = ROOT / 'reference/c8d1_inputs8'
sys.path.insert(0, str(ROOT / 'gen'))
import forest_counts  # noqa: E402  (independent enumerator, same directory)
from regress import builder_env  # noqa: E402  (the controlled OpenMP environment of a generator program)
# W4 (Stage-6 fix round 4): the one G-file reader of regress.py (bytes without newline translation, the loader's bounds)
from regress import INT_RANGE, LMAX, MASK_TOKEN, MAXMASKS, MAXTERMS, TERM_TOKEN, gfile_text  # noqa: E402

EXPECT = {
    8: dict(classes=26540, power_classes=7231, free_classes=19309, free_zero=2511, power_zero=2340, primitives=248,
            free_finite=16798, power_finite=4891, free_finite_sG4=734, power_finite_sG4=555, free_selected=16064,
            power_selected=4336, sG4_classes=2254, forests_total=11254373, M_max_bound=4032, T_max_bound=280,
            partition={'zero_channel_weight': 2254, 'zero_mixed_forest_kernel_at_nonzero_weight': 3886,
                       'retained_primitive': 248, 'retained_powerfree_nonprimitive': 15816,
                       'new_power_containing': 4336}),
    7: dict(classes=3986, power_classes=1091, free_classes=2895, free_zero=454, power_zero=382, primitives=44,
            free_finite=2441, power_finite=709, free_finite_sG4=143, power_finite_sG4=119, free_selected=2441,
            power_selected=709, forests_total=873108,
            partition={'exact_zero_kernel': 836, 'retained_primitive': 44, 'retained_powerfree_nonprimitive': 2397,
                       'new_power_containing': 709}),
}
SUM_WA_L8, SUM_WB_L8 = '49985915/768', '33994099/6912'
GATES = ('a_zero_dim', 'b_metadata', 'c_zeros', 'd_primitives', 'e_counts', 'f_coverage', 'g_edge_forests',
         'h_kirchhoff', 'i_sizes', 'j_rates', 'k_forests')
RATE_TOKEN = re.compile(r'(0|[1-9][0-9]*)(\.5)?')


def load_inv(stage: Path, L: int, sector: str) -> list[dict]:
    """inventory.json with integers exact and floats kept as their printed strings (never binary64)."""
    return json.loads((stage / f'L{L}_{sector}/inventory.json').read_text(), parse_float=str)


def c8d1_rows(L: int) -> list[dict]:
    return forest_counts.read_inventory(C8D1 / f'L{L}_inventory.txt')


def summary_problems(gates_dir: Path) -> list[str]:
    """Why gates_dir (a stage's or a published tree's gates/) is not a complete A-INV-3 pass; [] when it is.

    Used by the publication (gen/publish_inventory.py build) and the H1 handoff (gen/handoff_inventory.py), Stage-6
    finding S6-B-02: summary.json (schema c8-d2-gate-summary-1, gate A-INV-3) records a pass at loops [7, 8] with no
    injected failure and a verdict for exactly the eleven gates of GATES, each true; and every gate has its own record
    gates/<name>.json (schema c8-d2-gate-1, gate 'A-INV-3 <name>') that passed, with no injected failure and no
    exception. A bare summary with fewer gates, or a summary whose gate records are missing or red, is refused."""
    out: list[str] = []
    try:
        summ = json.loads((gates_dir / 'summary.json').read_bytes())
    except (OSError, ValueError) as e:
        return [f'gates/summary.json unreadable ({type(e).__name__})']
    if not isinstance(summ, dict):
        return ['gates/summary.json is not a JSON object']
    if summ.get('schema') != 'c8-d2-gate-summary-1' or summ.get('gate') != 'A-INV-3':
        out.append(f'gates/summary.json is not an A-INV-3 summary (schema {summ.get("schema")!r})')
    if summ.get('passed') is not True or summ.get('loops') != [7, 8] or summ.get('injected_failure'):
        out.append('gates/summary.json does not record a full pass at loops 7 and 8 without an injected failure')
    verdicts = summ.get('gates')
    if not isinstance(verdicts, dict) or set(verdicts) != set(GATES):
        got = sorted(verdicts) if isinstance(verdicts, dict) else verdicts
        out.append(f'gates/summary.json records the gates {got}, not exactly the eleven A-INV-3 gates {list(GATES)}')
    elif not all(verdicts[g] is True for g in GATES):
        out.append(f'gates/summary.json: gates {[g for g in GATES if verdicts[g] is not True]} did not pass')
    for g in GATES:
        try:
            rec = json.loads((gates_dir / f'{g}.json').read_bytes())
        except (OSError, ValueError) as e:
            out.append(f'gates/{g}.json missing or unreadable ({type(e).__name__})')
            continue
        if (not isinstance(rec, dict) or rec.get('schema') != 'c8-d2-gate-1' or rec.get('gate') != f'A-INV-3 {g}'
                or rec.get('passed') is not True or rec.get('injected_failure') or 'exception' in rec):
            out.append(f'gates/{g}.json is not a passed A-INV-3 {g} record')
    return out


# ---- gates ------------------------------------------------------------------------------------------------------
def gate_zero_dim(a) -> dict:
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'gen/zero_dim_check.py'), str(C8D1), '8'],
                       capture_output=True, text=True)
    rows = {}
    for line in r.stdout.splitlines():
        m = re.match(r'L=(\d+) classes=(\d+) sum_wa=(\S+) .*match=(True|False)\s+sum_wb=(\S+)', line)
        if m:
            rows[int(m.group(1))] = dict(classes=int(m.group(2)), sum_wa=m.group(3), wa_match=m.group(4) == 'True',
                                         sum_wb=m.group(5))
    l8 = rows.get(8, {})
    ok = (r.returncode == 0 and 'zero-dimensional identities hold for every L' in r.stdout and len(rows) == 8
          and all(v['wa_match'] for v in rows.values()) and l8.get('sum_wa') == SUM_WA_L8
          and l8.get('sum_wb') == SUM_WB_L8 and l8.get('classes') == EXPECT[8]['classes'])
    return dict(passed=ok, returncode=r.returncode, per_loop=rows, expected_L8=dict(sum_wa=SUM_WA_L8, sum_wb=SUM_WB_L8),
                stdout=r.stdout[-4000:], stderr=r.stderr[-1000:])


def gate_metadata(a) -> dict:
    out, ok = {}, True
    for L in a.loops:
        ref_bytes = (C8D1 / f'L{L}_inventory.txt').read_bytes()
        ref = c8d1_rows(L)
        for sector in ('free', 'power'):
            side = (a.stage / f'L{L}_{sector}.subgraphs.txt').read_bytes()
            inv = load_inv(a.stage, L, sector)
            bad = []
            if len(inv) != len(ref):
                bad.append(f'{len(inv)} classes vs {len(ref)}')
            for g, r in zip(inv, ref):
                if (g['id'] != r['id'] or str(g['key']) != r['key'] or g['denominator'] != r['D_G']
                        or g['mass_numerator'] != r['s_G'] or g['log_subgraphs'] != len(r['logs'])
                        or g['power_subgraphs'] != len(r['powers'])
                        or g['primitive'] != (not r['logs'] and not r['powers'])):
                    bad.append(g['id'])
            row = dict(side_file_identical=side == ref_bytes, side_file_bytes=len(side), inventory_mismatches=len(bad),
                       first_mismatches=bad[:20], classes=len(inv),
                       keys_above_2_64=sum(1 for g in inv if g['key'] >= 2 ** 64))
            ok &= row['side_file_identical'] and not bad
            out[f'L{L}_{sector}'] = row
    return dict(passed=ok, reference='reference/c8d1_inputs8/L{7,8}_inventory.txt', per_build=out)


def gate_zeros_primitives(a) -> tuple[dict, dict]:
    fs = json.loads((C8D1 / 'verification/forest_subsets.json').read_text())
    zeros, prims, okz, okp = {}, {}, True, True
    for L in a.loops:
        sub = fs[str(L)]['subsets']
        free, power = load_inv(a.stage, L, 'free'), load_inv(a.stage, L, 'power')
        fz = sorted(g['id'] for g in free if g['status'] == 'exact-zero-kernel')
        pz = sorted(g['id'] for g in power if g['status'] == 'exact-zero-kernel')
        rz = dict(free_zero=len(fz), power_zero=len(pz),
                  free_equals_free_articulation=fz == sorted(sub['free_articulation']['ids']),
                  power_equals_power_articulation=pz == sorted(sub['power_articulation']['ids']),
                  expected=dict(free=EXPECT[L]['free_zero'], power=EXPECT[L]['power_zero']))
        okz &= (rz['free_equals_free_articulation'] and rz['power_equals_power_articulation']
                and len(fz) == EXPECT[L]['free_zero'] and len(pz) == EXPECT[L]['power_zero'])
        zeros[f'L{L}'] = rz
        pr = sorted(g['id'] for g in free if g['primitive'] is True)
        bad = [g['id'] for g in free if g['primitive'] is True and (g['status'] != 'finite-kernel'
                                                                  or (L == 8 and g['mass_numerator'] == 4))]
        rp = dict(primitives=len(pr), equals_free_primitive=pr == sorted(sub['free_primitive']['ids']),
                  not_finite_or_zero_channel=bad, expected=EXPECT[L]['primitives'])
        okp &= rp['equals_free_primitive'] and not bad and len(pr) == EXPECT[L]['primitives']
        prims[f'L{L}'] = rp
    return dict(passed=okz, per_loop=zeros), dict(passed=okp, per_loop=prims)


def gate_counts(a) -> dict:
    out, ok = {}, True
    for L in a.loops:
        free, power = load_inv(a.stage, L, 'free'), load_inv(a.stage, L, 'power')
        e = EXPECT[L]
        ff = [g for g in free if g['status'] == 'finite-kernel']
        pf = [g for g in power if g['status'] == 'finite-kernel']
        got = dict(classes=len(free), power_classes=sum(1 for g in free if g['power_subgraphs']),
                   free_classes=sum(1 for g in free if not g['power_subgraphs']),
                   free_finite=len(ff), power_finite=len(pf),
                   free_finite_sG4=sum(1 for g in ff if g['mass_numerator'] == 4),
                   power_finite_sG4=sum(1 for g in pf if g['mass_numerator'] == 4),
                   free_selected=sum(1 for g in ff if L < 8 or g['mass_numerator'] != 4),
                   power_selected=sum(1 for g in pf if L < 8 or g['mass_numerator'] != 4),
                   statuses_free=sorted({g['status'] for g in free}), statuses_power=sorted({g['status'] for g in power}),
                   gfiles_free=len(list((a.stage / f'L{L}_free').glob('G*.txt'))),
                   gfiles_power=len(list((a.stage / f'L{L}_power').glob('G*.txt'))))
        if L == 8:
            got['sG4_classes'] = sum(1 for g in free if g['mass_numerator'] == 4)
        mism = {k: (got[k], v) for k, v in e.items() if k in got and got[k] != v}
        if got['gfiles_free'] != got['free_finite'] or got['gfiles_power'] != got['power_finite']:
            mism['gfiles'] = (got['gfiles_free'], got['gfiles_power'])
        ok &= not mism
        out[f'L{L}'] = dict(counts=got, mismatches={k: list(v) for k, v in mism.items()})
    return dict(passed=ok, per_loop=out)


def gate_coverage(a) -> dict:
    outp = a.gates / 'coverage.json'
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'gen/coverage.py'), '--stage', str(a.stage), '--loops',
                        ','.join(map(str, a.loops)), '--top', '8', '--output', str(outp)], capture_output=True, text=True)
    if r.returncode != 0:
        return dict(passed=False, returncode=r.returncode, stderr=r.stderr[-2000:])
    cov = json.loads(outp.read_text())
    ok = all(cov['partitions'][str(L)] == EXPECT[L]['partition'] for L in a.loops)
    sizes = {f'L{L}_{s}': len(cov['selection'][str(L)][s]) for L in a.loops for s in ('free', 'power')}
    ok &= sizes == {f'L{L}_{s}': EXPECT[L][f'{s}_selected'] for L in a.loops for s in ('free', 'power')}
    ok &= all(len(cov['selection'][str(L)]['primitive']) == EXPECT[L]['primitives'] for L in a.loops)
    return dict(passed=ok, partitions=cov['partitions'], expected={str(L): EXPECT[L]['partition'] for L in a.loops},
                selection_sizes=sizes, record='gates/coverage.json (written by gen/coverage.py)')


def gate_edge_forests(a) -> dict:
    out, ok = {}, True
    for L in a.loops:
        rep = a.gates / f'edge_forests_L{L}.json'
        t0 = time.time()
        r = subprocess.run([str(a.bin / 'check_edge_forests'), str(C8D1 / f'classes{L}.txt'),
                            str(a.stage / f'L{L}_power'), str(rep)],
                           env=builder_env(a.jobs), capture_output=True, text=True)
        try:
            j = json.loads(rep.read_text())
        except (OSError, ValueError):
            j = {}
        row = dict(returncode=r.returncode, graphs=j.get('graphs'), failures=j.get('failures'),
                   expected_graphs=EXPECT[L]['power_classes'], seconds=round(time.time() - t0, 1),
                   all_matches_induced=all(x.get('matches_induced') for x in j.get('rows', [])),
                   stderr=r.stderr[-500:])
        ok &= (r.returncode == 0 and j.get('failures') == 0 and j.get('graphs') == EXPECT[L]['power_classes']
               and row['all_matches_induced'])
        out[f'L{L}'] = row
    return dict(passed=ok, per_loop=out, records='gates/edge_forests_L{7,8}.json (written by check_edge_forests)')


def gate_kirchhoff(a) -> dict:
    outp = a.gates / 'kirchhoff.json'
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'gen/kirchhoff.py'), '--stage', str(a.stage), '--loops',
                        ','.join(map(str, a.loops)), '--jobs', str(a.jobs), '--output', str(outp)],
                       capture_output=True, text=True)
    try:
        k = json.loads(outp.read_text())
    except (OSError, ValueError):
        k = {}
    want = {f'L{L}_{s}': (64 if L == 8 else 8) for L in a.loops for s in ('free', 'power')}
    ok = (r.returncode == 0 and k.get('passed') is True and k.get('per_group') == want
          and k.get('count') == sum(want.values()))
    return dict(passed=ok, returncode=r.returncode, count=k.get('count'), per_group=k.get('per_group'),
                expected_per_group=want, failures=k.get('failures'), seconds=k.get('seconds'),
                record='gates/kirchhoff.json', stderr=r.stderr[-1000:])


# Z5 (S6R3-B-01, Stage-6 fix round 3): G-file integers as the native loader (src/kernel.hpp load_graph) reads them.
# Python's int() also takes '-7', '+7', '0_7' (7, where the loader reads 0 and then fails) and non-ASCII digits; the
# gate accepts the builders' plain ASCII decimal tokens only (a mask: digits; a term entry: an optional '-' and
# digits), each mask in [0, 2^E) (an unsigned in the loader, so a negative mask is a huge one there: 'nonhomogeneous
# mask'; bin(-m) has the popcount of m, which hid it) and every term entry within the loader's int (a std::vector<int>:
# a value outside [-2^31, 2^31) fails the stream). MASK_TOKEN, TERM_TOKEN and INT_RANGE live in regress.py (W4).
# W4 (S6R4-B-01, Stage-6 fix round 4): the token checks ran after str.split(), which also splits on U+00A0 and the other
# Unicode separators and on U+001C..U+001F, where the loader's stream extraction stops; and read_text() turned CRLF
# into LF. The file is now read as bytes through regress.gfile_text (LF, spaces and printable ASCII only), and the
# header counts must be within the loader's bounds (2 <= L <= LMAX, 1 <= M <= MAXMASKS, 1 <= T <= MAXTERMS: a header
# and inventory row of M = T = 0 passed the empty mask and term checks, but load_graph refuses it).


def gfile_ints(tokens: list[str], pattern, what: str) -> list[int]:
    """The integers of one G-file line, every token a plain ASCII decimal of `pattern` (Z5); ValueError otherwise."""
    bad = [x for x in tokens if not pattern.fullmatch(x)]
    if bad:
        raise ValueError(f'{what}: token {bad[0][:40]!r} is not a plain decimal integer')
    return [int(x) for x in tokens]


def check_gfile(job) -> dict:
    """Full structural parse of one finite G-file and the A-INV-3(j) rate rules. Z5: every mask is a plain decimal in
    [0, 2^E) of L edges, ascending; every term entry a plain decimal within the native loader's int range. W4: the
    file's bytes are LF, spaces and printable ASCII only (regress.gfile_text, no newline translation) and the header's
    L, M and T within the native loader's bounds."""
    path, L, gid, M, T, wa, wb = job
    E = 2 * L
    ALL = (1 << E) - 1
    res = dict(id=gid, ok=False)
    try:
        text = gfile_text(Path(path).read_bytes())
        lines = text.split('\n')
        if lines[-1] != '':
            raise ValueError('no final newline')
        lines.pop()
        head = lines[0].split()
        if head != ['C7D2GRAPH1', str(L), str(gid), wa, wb, str(M), str(T)]:
            raise ValueError(f'header {head} does not match the inventory')
        if not (2 <= L <= LMAX and 1 <= M <= MAXMASKS and 1 <= T <= MAXTERMS):
            raise ValueError(f'header L={L}, M={M}, T={T} outside the native loader\'s bounds (2 <= L <= {LMAX}, 1 <= M <= {MAXMASKS}, '
                             f'1 <= T <= {MAXTERMS})')
        if len(lines) != 4 + T:
            raise ValueError(f'{len(lines)} lines for T={T}')
        masks = gfile_ints(lines[1].split(), MASK_TOKEN, 'mask line')
        if len(masks) != M or any(not 0 <= m < 1 << E or bin(m).count('1') != L for m in masks) \
                or any(x >= y for x, y in zip(masks, masks[1:])):
            raise ValueError('mask line')
        for line in lines[2:2 + T]:
            t = gfile_ints(line.split(), TERM_TOKEN, f'term line {line[:60]}')
            if not t:
                raise ValueError('empty term line')
            k = t[0]
            basis, co = t[1:1 + k], t[1 + k:]
            if k < 1 or len(co) != E or any(not 0 <= b < M for b in basis) \
                    or any(x >= y for x, y in zip(basis, basis[1:])) or not any(co) \
                    or any(not INT_RANGE[0] <= c < INT_RANGE[1] for c in co):
                raise ValueError(f'term line {line[:60]}')
        if lines[2 + T] != str(ALL + 1):
            raise ValueError('2^E line')
        rate = lines[3 + T].split()
        if len(rate) != ALL + 1:
            raise ValueError(f'{len(rate)} rate entries')
        if rate[0] != '0' or rate[ALL] != '0':
            raise ValueError('rate entries at s=0 or s=2^E-1 are not 0')
        lo, hi, at_floor = 101, 0, 0
        for s in range(1, ALL):
            m = RATE_TOKEN.fullmatch(rate[s])
            if not m:
                raise ValueError(f'rate token {rate[s]!r} at s={s}')
            twice = 2 * int(m.group(1)) + (1 if m.group(2) else 0)
            floor = 1 if bin(s).count('1') % 2 else 2
            if not 1 <= twice <= 100 or twice < floor:
                raise ValueError(f'rate {rate[s]} at s={s} (|S|={bin(s).count("1")})')
            lo, hi = min(lo, twice), max(hi, twice)
            at_floor += twice == floor
        res.update(ok=True, min_twice=lo, max_twice=hi, at_floor=at_floor)
    except (ValueError, OSError, IndexError) as e:
        res['error'] = str(e)[:300]
    return res


def gate_sizes_rates(a) -> tuple[dict, dict]:
    sizes, rates, oks, okr = {}, {}, True, True
    for L in a.loops:
        for sector in ('free', 'power'):
            inv = [g for g in load_inv(a.stage, L, sector) if g['status'] == 'finite-kernel']
            Mmax, Tmax = max(g['masks'] for g in inv), max(g['terms'] for g in inv)
            sizes[f'L{L}_{sector}'] = dict(M_max=Mmax, T_max=Tmax, kernels=len(inv))
            if L == 8:
                oks &= Mmax <= EXPECT[8]['M_max_bound'] and Tmax <= EXPECT[8]['T_max_bound']
            jobs = [(str(a.stage / f'L{L}_{sector}' / f'G{g["id"]}.txt'), L, g['id'], g['masks'], g['terms'],
                     g['wa'] if isinstance(g['wa'], str) else str(g['wa']),
                     g['wb'] if isinstance(g['wb'], str) else str(g['wb'])) for g in inv]
            with Pool(a.jobs) as pool:
                res = pool.map(check_gfile, jobs, chunksize=16)
            bad = [r for r in res if not r['ok']]
            good = [r for r in res if r['ok']]
            rates[f'L{L}_{sector}'] = dict(files=len(res), failures=len(bad), first_failures=bad[:20],
                                            min_rate=str(Decimal(min(r['min_twice'] for r in good)) / 2) if good else None,
                                            max_rate=str(Decimal(max(r['max_twice'] for r in good)) / 2) if good else None,
                                            entries_at_parity_floor=sum(r['at_floor'] for r in good))
            okr &= not bad and len(res) > 0
    return (dict(passed=oks, bounds_L8=dict(M=EXPECT[8]['M_max_bound'], T=EXPECT[8]['T_max_bound']), per_build=sizes),
            dict(passed=okr, rule='0 < s < 2^E-1: half-integer in [0.5, 50], >= 1 when |S| is even; s = 0 and '
                                  's = 2^E-1: 0; every G-file parses completely and matches its inventory row',
                 per_build=rates))


def gate_forests(a) -> dict:
    out, ok = {}, True
    for L in a.loops:
        rows = c8d1_rows(L)
        with Pool(a.jobs) as pool:
            counts = dict(pool.map(forest_counts._count, rows, chunksize=64))
        total = sum(counts.values())
        summ = json.loads((C8D1 / f'L{L}_summary.json').read_text())
        free = load_inv(a.stage, L, 'free')
        compared = [g for g in free if g['status'] != 'power-sector-not-integrated']
        mism = [g['id'] for g in compared if g.get('forests') != counts[g['id']]]
        row = dict(total=total, c8d1_summary_forests=summ['forests'], classes=len(rows),
                   power_free_classes_compared=len(compared), mismatches=len(mism), first_mismatches=mism[:20],
                   expected_total=EXPECT[L]['forests_total'], expected_power_free=EXPECT[L]['free_classes'])
        ok &= (total == summ['forests'] == EXPECT[L]['forests_total'] and not mism
               and len(compared) == EXPECT[L]['free_classes'])
        out[f'L{L}'] = row
    return dict(passed=ok, per_loop=out, method='gen/forest_counts.py: compatible log-subgraph families (nested or '
                                               'sharing at most one vertex, empty family included) from C8(1) masks')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stage', type=Path, required=True)
    ap.add_argument('--bin', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--inject-fail', default=os.environ.get('C8_GEN_INJECT_FAIL') or None)
    ap.add_argument('--loops', default='7,8', help='7,8 for the gate; a subset only for tool tests (never publishable)')
    a = ap.parse_args()
    a.loops = tuple(sorted(int(v) for v in a.loops.split(',')))
    if not set(a.loops) <= {7, 8}:
        raise SystemExit('--loops must be a subset of 7,8')
    if a.inject_fail and a.inject_fail not in GATES:
        raise SystemExit(f'unknown gate {a.inject_fail!r}: one of {GATES}')
    a.stage = a.stage.resolve()
    a.gates = a.stage / 'gates'
    a.gates.mkdir(exist_ok=False)
    t0 = time.time()
    recs: dict[str, dict] = {}

    def run(name: str, fn) -> None:
        t = time.time()
        try:
            recs[name] = fn(a)
        except Exception as e:  # a crashing gate is a failed gate, never a pass
            recs[name] = dict(passed=False, exception=f'{type(e).__name__}: {e}')
        recs[name]['seconds'] = round(time.time() - t, 1)
        print(f'gate {name}: {"PASS" if recs[name]["passed"] else "FAIL"} ({recs[name]["seconds"]} s)', flush=True)

    run('a_zero_dim', gate_zero_dim)
    run('b_metadata', gate_metadata)
    try:
        zr, pr = gate_zeros_primitives(a)
    except Exception as e:
        zr = pr = dict(passed=False, exception=f'{type(e).__name__}: {e}')
    recs['c_zeros'], recs['d_primitives'] = zr, pr
    print(f'gate c_zeros: {"PASS" if zr["passed"] else "FAIL"}; gate d_primitives: {"PASS" if pr["passed"] else "FAIL"}')
    run('e_counts', gate_counts)
    run('f_coverage', gate_coverage)
    run('g_edge_forests', gate_edge_forests)
    run('h_kirchhoff', gate_kirchhoff)
    try:
        sr, rr = gate_sizes_rates(a)
    except Exception as e:
        sr = rr = dict(passed=False, exception=f'{type(e).__name__}: {e}')
    recs['i_sizes'], recs['j_rates'] = sr, rr
    print(f'gate i_sizes: {"PASS" if sr["passed"] else "FAIL"}; gate j_rates: {"PASS" if rr["passed"] else "FAIL"}')
    run('k_forests', gate_forests)
    assert tuple(recs) == GATES, tuple(recs)
    if a.inject_fail:
        recs[a.inject_fail] = dict(recs[a.inject_fail], passed=False, injected_failure=True)
    for name, rec in recs.items():
        (a.gates / f'{name}.json').write_text(json.dumps(dict(schema='c8-d2-gate-1', gate=f'A-INV-3 {name}', **rec),
                                                         indent=1) + '\n')
    summary = dict(schema='c8-d2-gate-summary-1', gate='A-INV-3', stage=str(a.stage), loops=list(a.loops),
                   passed=all(r['passed'] for r in recs.values()) and not a.inject_fail and a.loops == (7, 8),
                   gates={k: r['passed'] for k, r in recs.items()}, injected_failure=a.inject_fail,
                   expected={str(k): v for k, v in EXPECT.items()}, seconds=round(time.time() - t0, 1))
    (a.gates / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print('A-INV-3', 'PASSED' if summary['passed'] else 'FAILED', json.dumps(summary['gates']))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
