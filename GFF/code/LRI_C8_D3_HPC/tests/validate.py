#!/usr/bin/env python3
"""The native replay and input gates of C8(3) (PLAN.md A-RPL-1, A-RPL-2, A-KER-1, A-KER-2/3 use-time checks; F row
`validate.py`). Expanse: needs `make gmp decimal c7ref`.

  python3 -B tests/validate.py [--full] [--threads N] [--parts identity,g_c7,g_jet,bad_inputs,orders,splits|none]
                               [--bk8] [--l2-control] [--l8self DIR [--jobs J]] [--output FILE]

Parts:
  identity    A-KER-2/3: --describe of bin/c8d3_{gmp,decimal} (schema c8-d3-build-1, orders [7,8], lmax 8, kmax 6,
              numerics exact, not diagnostic, Boost 1_77, the backend's gmp block: gmp applicable with
              runtime_version = header_version = 6.2.1 and a library path; decimal {"applicable": false}); the reference
              GMP binary's library probe re-run in this environment against its build record (HD9: a different libgmp
              path or version is refused before first use).
  g_c7        A-RPL-1 (G-C7, same toolchain, same node, same job): bin/c8d3_{gmp,decimal} in order-7 mode against
              bin/ref/c7d3_{gmp,decimal} (make c7ref), gmp against gmp and decimal against decimal, on the L2 graph and
              the C7(3) kernels (all 3,511 with --full; else the first 8 and the 8 heaviest per (sector, L)),
              2 replicates x 64 points, native seed 7738251, rates .8 (52-bit nets) and .7 (60-bit nets) at layout 0,
              and at L7 also layouts 1 and 2. Both workers get the same C7D3TASKS1 task file and identical arguments,
              the executable path excepted (HD3). Gate: every row field the C7 worker writes (all but "seconds") and its
              timing-free header fields are exactly equal, mp > 0 rows included. Also (A-KER-1): the same rows under
              C8D3TASKS1 7 give rows identical to the C7D3TASKS1 run in every field but "seconds". The record holds the C8
              rows' nondirect totals (shift != 0 points; none at rates .8/.7). Then the shift case (part_c7_shift): one-
              point tasks at rate .02 on L3/L5/L7 kernels of both sectors and the deep-cancellation fixture, c7ref
              against C8 order 7 (--mp-check off and on), exact, with >= 1 row per (sector, L) whose MP point has
              shift != 0: the A-L18 hunk (kernel.hpp calculate_shared) runs and changes no bit.
  g_jet       A-RPL-2 (G-JET): order 8 against order 7 (C8D3TASKS1 8 with gamma_d3_8.txt against C8D3TASKS1 7 with
              gamma_d3_7.txt) on the same kernels and the layout-0 configurations, both backends: b slots 0..7-L and
              c slots 0..7-L (offset 9-L against 8-L) exact; quad, mp, max_abs and the tail fields identical; the new
              slots 8-L and 2(9-L)-1 finite. (At G3a the L <= 7 kernels are C7(3)'s 3,511; the 262 new L7 kernels join
              in Stage 3b, PLAN G3b.)
  bad_inputs  A-KER-1: every case exits 2 with its file's path and the expected reason (both backends): L = 9, L = 1,
              order 6 and 9, an order-8 task with gamma_d3_7.txt and an order-7 task with gamma_d3_8.txt, a C7D3TASKS1
              task with gamma_d3_8.txt or with L = 8, a trailing gamma token, net dim = 32, a G-file with L = 9 (E = 18;
              E = 2L, so the plan's "E = 17" is reached as an L8 mask with bit 16 set), a G-file truncated after each
              of its 7 header tokens, a term index of M and of -1, a term length of 0 and of M + 1, a rate count of
              2^E - 1, a task file cut after its magic, after the order and after L, a 6-byte net file, and a grid file
              cut before and inside an id.
  orders      A-KER-1/2: L = 2 runs at both orders (K = 5 and 6, row widths 12 and 14), and the native JSON carries
              schema c8-d3-hpc-native-1, order, numerics exact, mp_check, max_rss_kb, the backend's gmp block and
              libraries; the row width is 2(order+1-L)
              at every loop of g_c7/g_jet (checked there); order 7 with L = 8 is refused (bad_inputs).
  bk8         (--bk8; J-VAL-3, G3b) A-RPL-3 G-BK8: decimal against gmp at L7 and L8 (the loops present).
  l2_control  (--l2-control; J-VAL-3, G3b) A-IN-6: the L = 2 control at order 8.
  l8self      (--l8self DIR; Stage 4b, every kernel change after Stage 3) A-RPL-8 G-L8SELF: bin/c8d3_{gmp,decimal}
              against DIR/c8d3_{gmp,decimal} (the c8-stage3 baseline, bin/baseline after `make baseline STORE=...`) on
              the L8 sweep sample (l8self_sample: per sector the 100 costliest kernels plus a random.Random(81113) draw of
              1,500 free and 300 power, 2,000 in all), 2 replicates x 512 points, order 8, rate .8, layout 0, the 52-bit
              net of seed 81121, native seed SEED, --mp-check on: every row field but "seconds" and every header field
              but the run fields exactly equal, both backends. tools/opt_speed.py (A-PERF-2) runs the same sample.
  splits      the inherited random-access gates (C7(3) A-L14), at order 8: the 3 heaviest L7 kernels per sector,
              layouts 0/1/2, whole tasks against 23-point chunks at 1 and 4 threads: rows bitwise across thread counts,
              chunk sums within 1e-12 normalized of the whole tasks, both backends.
Every executable writes a distinct, pre-deleted output in a temporary directory; nothing is written into the
package unless --output.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402

SEED = 7738251
RESULTS: list[dict] = []


def record(**kw):
    RESULTS.append(kw)
    print(json.dumps(kw, default=str), flush=True)


def configs(L: int):
    base = [('.8', 0, 52), ('.7', 0, 60)]
    return base + ([('.8', 1, 52), ('.7', 1, 60), ('.8', 2, 52), ('.7', 2, 60)] if L == 7 else [])


def net_for(td, sector, L, layout, bits):
    return nc.net(td, nc.dim_of(L, layout), bits, 983507 + L + (11255 if sector == 'power' else 0) + 101 * layout + bits)


# ---- identity ---------------------------------------------------------------------------------------------------
def part_identity(td, threads, full):
    out = {}
    for b, exe in nc.C8.items():
        d = nc.describe(exe)
        want = dict(schema='c8-d3-build-1', dimension=3, orders=[7, 8], lmax=8, kmax=6, numerics='exact', diagnostic=False,
                    boost='1_77', mp_backend='gmp350' if b == 'gmp' else 'decimal300')
        bad = {k: d.get(k) for k, v in want.items() if d.get(k) != v}
        g = d.get('gmp') or {}
        if b == 'gmp':
            if not (g.get('applicable') is True and g.get('header_version') == g.get('runtime_version') == '6.2.1' and g.get('library')):
                bad['gmp'] = g
        elif g != {'applicable': False}:
            bad['gmp'] = g
        if not isinstance(d.get('libraries'), list) or not d['libraries']:
            bad['libraries'] = d.get('libraries')
        if bad:
            raise AssertionError(f'{exe} --describe: {bad}')
        out[b] = {'gmp': g, 'libraries': len(d['libraries'])}
    out['ref_probe'] = nc.check_ref_probe(nc.C7REF['gmp'])
    record(test='identity', **out)


# ---- g_c7 and g_jet -----------------------------------------------------------------------------------------------
def part_replay(td, threads, full, do_c7=True, do_jet=True):
    inv = nc.inventory()
    groups = [('free', 2, [0])] + [(s, L, nc.kernels(inv, s, L, full)) for s in nc.SECTORS for L in nc.LOOPS7]
    sel = [(s, L, g) for s, L, ids in groups for g in ids]
    totals = {'c7': {b: dict(rows=0, mp_rows=0, graphs=0, nondirect_points=0, mp_and_nondirect_rows=0) for b in nc.C8},
              'jet': {b: dict(rows=0, graphs=0) for b in nc.C8}}
    with nc.extracted(sel) as root:
        for sector, L, ids in groups:
            src = root / sector
            for b in nc.C8:
                for ci, (rate, layout, bits) in enumerate(configs(L)):
                    netf = net_for(td, sector, L, layout, bits)
                    rows = nc.task_rows(ids)
                    t7 = nc.write_tasks(td / 'tasks_c7', L, rows)
                    args = (src, nc.GAMMA[7], netf, t7)
                    new, _ = nc.run_worker(nc.C8[b], *args, td / f'out_c8_{b}.json', SEED, layout, rate, threads)
                    if any(len(r['values']) != 2 * (8 - L) for r in new['rows']):
                        raise AssertionError(f'{b} {sector} L{L}: order-7 row width is not 2(8-L)')
                    if do_c7:
                        ref, _ = nc.run_worker(nc.C7REF[b], *args, td / f'out_c7_{b}.json', SEED, layout, rate, threads)
                        diff = [k for k in nc.C7_TOP_FIELDS if ref.get(k) != new.get(k)]
                        if diff:
                            raise AssertionError(f'G-C7 {b} {sector} L{L} rate {rate} layout {layout}: header fields differ: {diff}')
                        e = nc.rows_equal(ref, new, nc.C7_ROW_FIELDS)
                        if e:
                            raise AssertionError(f'G-C7 {b} {sector} L{L} rate {rate} layout {layout}: {e}')
                        totals['c7'][b]['rows'] += len(ref['rows'])
                        totals['c7'][b]['mp_rows'] += sum(r['mp'] > 0 for r in ref['rows'])
                        # the C8 rows' shift counter (nondirect: points evaluated with shift != 0, where the A-L18 hunk runs)
                        totals['c7'][b]['nondirect_points'] += sum(r['nondirect'] for r in new['rows'])
                        totals['c7'][b]['mp_and_nondirect_rows'] += sum(1 for r in new['rows'] if r['mp'] > 0 and r['nondirect'] > 0)
                        if ci == 0:
                            totals['c7'][b]['graphs'] += len(ids)
                            # A-KER-1: C7D3TASKS1 and the same rows under C8D3TASKS1 7 give identical rows.
                            t8h = nc.write_tasks(td / 'tasks_c8h7', L, rows, order=7)
                            same, _ = nc.run_worker(nc.C8[b], src, nc.GAMMA[7], netf, t8h, td / f'out_c8h7_{b}.json', SEED, layout, rate, threads)
                            e = nc.rows_equal(new, same, [k for k in new['rows'][0] if k != 'seconds'])
                            if e or same['order'] != 7 or same['task_magic'] != 'C8D3TASKS1' or new['task_magic'] != 'C7D3TASKS1':
                                raise AssertionError(f'C7D3TASKS1 vs C8D3TASKS1 7 ({b} {sector} L{L}): {e}')
                    if do_jet and layout == 0:
                        t8 = nc.write_tasks(td / 'tasks_o8', L, rows, order=8)
                        o8, _ = nc.run_worker(nc.C8[b], src, nc.GAMMA[8], netf, t8, td / f'out_o8_{b}.json', SEED, layout, rate, threads)
                        jet_compare(new, o8, L, f'{b} {sector} L{L} rate {rate}')
                        totals['jet'][b]['rows'] += len(o8['rows'])
                        if ci == 0:
                            totals['jet'][b]['graphs'] += len(ids)
                print(f'{sector} L{L}: {len(ids)} graphs done ({time.strftime("%H:%M:%S")})', flush=True)
    if do_c7:
        record(test='G-C7' if full else 'G-C7 subset', gate='exact in every C7 row field (seconds excepted), both backends',
               kernels_c7d3=sum(len(ids) for s, L, ids in groups if L >= 3), l2_graph=True, totals=totals['c7'],
               configurations={'L3-L6': 'rates .8/.7 at layout 0', 'L7': 'rates .8/.7 at layouts 0/1/2'}, points='2 x 64', seed=SEED,
               note='nondirect_points counts the C8 rows\' shift != 0 points; at rates .8/.7 none occur, so the shift path (the A-L18 hunk, '
                    'src/kernel.hpp calculate_shared) is exercised by the G-C7 shift case below')
    if do_jet:
        record(test='G-JET' if full else 'G-JET subset', gate='slots 0..7-L of b and c exact; quad, mp, max_abs, tail fields identical; new slots finite',
               kernels=sum(len(ids) for s, L, ids in groups), totals=totals['jet'])
    if do_c7:
        part_c7_shift(td, threads, inv)


def part_c7_shift(td, threads, inv):
    """G-C7 on the shift path (Stage 3a repair round 1): the A-L18 hunk (the order-7 default path's only arithmetic edit,
    kernel.hpp calculate_shared) runs only for points evaluated with shift != 0, which the A-RPL-1 rates .8/.7 never
    reach. Here: one-point tasks (2 replicates x 64 points) at rate .02, layout 0, 52-bit nets (seed 1201 + L), on the first
    3 and the 3 heaviest kernels of every (sector, L) at L3, L5 and L7 and on the deep-cancellation fixture; c7ref and
    C8 in order 7 (--mp-check off and on), both backends. Gate: every C7 row field exact, and per (sector, L) at least one
    row whose only point is an MP point with shift != 0 (mp > 0 and nondirect > 0), so the hunk ran and changed no bit."""
    picks = [(s, L, nc.kernels(inv, s, L, False, 3, 3)) for s in nc.SECTORS for L in (3, 5, 7)]
    out = {}
    with nc.extracted([(s, L, g) for s, L, ids in picks for g in ids]) as root:
        cases = [('fixture', 3, [0], nc.ROOT / 'tests/fixtures/deep_cancellation')] + [(s, L, ids, root / s) for s, L, ids in picks]
        for name, L, ids, src in cases:
            netf = nc.net(td, nc.dim_of(L, 0), 52, 1201 + L)
            one = [(i, r, g, q, q + 1, 64) for i, (r, g, q) in enumerate((r, g, q) for r in range(2) for g in ids for q in range(64))]
            tf = nc.write_tasks(td / 'shift_tasks', L, one)
            for b in nc.C8:
                ref, _ = nc.run_worker(nc.C7REF[b], src, nc.GAMMA[7], netf, tf, td / f'shift_c7_{b}.json', SEED, 0, '.02', threads)
                key = f'{name}_L{L}'
                runs = {}
                for mode in ('off', 'on'):
                    runs[mode], _ = nc.run_worker(nc.C8[b], src, nc.GAMMA[7], netf, tf, td / f'shift_c8_{b}.json', SEED, 0, '.02', threads, mp_check=mode)
                    e = nc.rows_equal(ref, runs[mode], nc.C7_ROW_FIELDS)
                    if e:
                        raise AssertionError(f'G-C7 shift {b} {key} --mp-check {mode}: {e}')
                new = runs['on']
                hit = sum(1 for r in new['rows'] if r['mp'] > 0 and r['nondirect'] > 0)
                if name != 'fixture' and hit == 0:
                    raise AssertionError(f'G-C7 shift {b} {key}: no row with mp > 0 and nondirect > 0; the shift path was not reached')
                out.setdefault(key, {})[b] = dict(rows=len(new['rows']), mp_points=sum(r['mp'] for r in new['rows']),
                                                  nondirect_points=sum(r['nondirect'] for r in new['rows']), mp_and_nondirect_rows=hit)
    tot = {b: sum(v[b]['mp_and_nondirect_rows'] for v in out.values()) for b in nc.C8}
    record(test='G-C7 shift path (A-L18 hunk)', gate='every C7 row field exact (c7ref vs C8 order 7, --mp-check off and on, both backends); '
           'per (sector, L) >= 1 one-point row with mp > 0 and nondirect > 0', rate='.02', layout=0, points='2 x 64 one-point tasks',
           seed=SEED, kernels={f'{s}_L{L}': ids for s, L, ids in picks}, cases=out, mp_and_nondirect_rows=tot)


def jet_compare(o7: dict, o8: dict, L: int, what: str):
    if o8['order'] != 8 or o7['order'] != 7:
        raise AssertionError(f'G-JET {what}: orders {o7["order"]}, {o8["order"]}')
    for x, y in zip(o7['rows'], o8['rows'], strict=True):
        if any(x[k] != y[k] for k in ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'quad', 'mp', 'max_abs', 'tail_top', 'tail_sum', 'tail_argmax', 'nondirect', 'nonmoderate')):
            raise AssertionError(f'G-JET {what}: counters, max_abs or tail fields differ at uid {x["uid"]}')
        a, b = x['values'], y['values']
        if len(a) != 2 * (8 - L) or len(b) != 2 * (9 - L):
            raise AssertionError(f'G-JET {what}: widths {len(a)}, {len(b)} (2(order+1-L) expected)')
        for j in range(8 - L):
            if b[j] != a[j] or b[9 - L + j] != a[8 - L + j]:
                raise AssertionError(f'G-JET {what}: slot {j} differs at uid {x["uid"]}: {a[j]}/{b[j]}, {a[8 - L + j]}/{b[9 - L + j]}')
        for k in (8 - L, 2 * (9 - L) - 1):
            if not D(b[k]).is_finite():
                raise AssertionError(f'G-JET {what}: new slot {k} not finite at uid {x["uid"]}')


# ---- bad inputs --------------------------------------------------------------------------------------------------
def gfile_tokens(text: str) -> dict:
    t = text.split()
    L, M, T = int(t[1]), int(t[5]), int(t[6])
    E = 2 * L
    i = 7 + M
    terms = []
    for _ in range(T):
        n = int(t[i])
        terms.append([t[i], t[i + 1:i + 1 + n], t[i + 1 + n:i + 1 + n + E]])
        i += 1 + n + E
    return dict(header=t[:7], masks=t[7:7 + M], terms=terms, count=t[i], rates=t[i + 1:])


def gfile_text(g: dict) -> str:
    lines = [' '.join(g['header']), ' '.join(g['masks'])]
    lines += [' '.join([n, *ids, *co]) for n, ids, co in g['terms']]
    lines += [g['count'], ' '.join(g['rates'])]
    return '\n'.join(lines) + '\n'


def synthetic_l8() -> str:
    """A synthetic L = 8 G-file (E = 16, 2^16 rates): 40 masks of popcount 8, 5 terms (gen3/test_gen3.py's generator,
    magic C7D3GRAPH1). Not a graph; the reader checks counts, ranges and order, which is all it has to satisfy."""
    import random
    rng = random.Random(8814)
    E, L = 16, 8
    masks = sorted({sum(1 << b for b in rng.sample(range(E), L)) for _ in range(60)})[:40]
    lines = [f'C7D3GRAPH1 {L} 17 0.1875 0.03125 {len(masks)} 5', ' '.join(map(str, masks))]
    for _ in range(5):
        idx = sorted(rng.sample(range(len(masks)), rng.randint(1, 12)))
        co = [rng.choice((-1, 0, 0, 1, 2)) for _ in range(E)]
        lines.append(' '.join(map(str, [len(idx), *idx, *co])))
    lines.append(str(1 << E))
    lines.append(' '.join('0' if s in (0, (1 << E) - 1) else rng.choice(('0.5', '1', '1.5')) for s in range(1 << E)))
    return '\n'.join(lines) + '\n'


def bad_cases(td: Path, base_root: Path, base_id: int) -> list[dict]:
    """Each case: the worker's arguments and (path, reason regex). The base is an L3 free kernel."""
    gtext = (base_root / f'L3/G{base_id}.txt').read_text()
    g = gfile_tokens(gtext)
    M, E, n0 = len(g['masks']), 6, len(g['terms'][0][1])
    cases = []
    n = [0]

    def case(name, *, gfile=None, L=3, tasks=None, order=8, gamma=None, netf=None, grid='-', layout=0, path_of=None, reason):
        n[0] += 1
        d = td / f'bad{n[0]}'
        (d / f'L{L}').mkdir(parents=True)
        gp = d / f'L{L}' / f'G{base_id if L == 3 else 17}.txt'
        gp.write_text(gfile if gfile is not None else (gtext if L == 3 else synthetic_l8()))
        tp = d / 'tasks'
        if tasks is None:
            nc.write_tasks(tp, L, [(0, 0, base_id if L == 3 else 17, 0, 64, 64)], order=order)
        else:
            tp.write_text(tasks)
        gm = gamma or nc.GAMMA[order if order in (7, 8) else 8]
        nf = netf or nc.net(td, nc.dim_of(L, layout), 52, 5150 + L)
        paths = {'gfile': gp, 'tasks': tp, 'gamma': gm, 'net': nf, 'grid': Path(grid)}
        cases.append(dict(name=name, args=(d, gm, nf, tp, layout, grid), path=str(paths[path_of]), reason=reason))

    for L in (9, 1):
        case(f'task_L_{L}', tasks=f'C8D3TASKS1 8 {L} 1\n0 0 {base_id} 0 64 64\n', path_of='tasks', reason=rf'L {L} out of range \[2, order = 8\]')
    for o in (6, 9):
        case(f'task_order_{o}', tasks=f'C8D3TASKS1 {o} 3 1\n0 0 {base_id} 0 64 64\n', path_of='tasks', reason=rf'order {o} out of range \[7,8\]')
    case('order8_with_gamma7', order=8, gamma=nc.GAMMA[7], path_of='gamma', reason=r'gamma label mismatch: the row of L=2 has label 5, expected order-L = 6')
    case('order7_with_gamma8', order=7, gamma=nc.GAMMA[8], path_of='gamma', reason=r'gamma label mismatch: the row of L=2 has label 6, expected order-L = 5')
    case('c7tasks_with_gamma8', order=None, gamma=nc.GAMMA[8], path_of='gamma', reason=r'gamma label mismatch: the row of L=2 has label 6, expected order-L = 5')
    case('c7tasks_L_8', tasks=f'C7D3TASKS1 8 1\n0 0 {base_id} 0 64 64\n', path_of='tasks', reason=r'L 8 out of range \[2, order = 7\] \(C7D3TASKS1 is an order-7 task file\)')
    lines = nc.GAMMA[8].read_text().splitlines()
    lines[2] += ' 1.0'
    gt = td / 'gamma_trailing.txt'
    gt.write_text('\n'.join(lines) + '\n')
    case('gamma_trailing_token', gamma=gt, path_of='gamma', reason=r"trailing token '1\.0' in the row of L=4")
    bad_net = td / 'net_dim32.net'
    bad_net.write_bytes((2).to_bytes(4, 'little') + (32).to_bytes(4, 'little') + (52).to_bytes(4, 'little') + bytes(64))
    case('net_dim_32', netf=bad_net, path_of='net', reason=r'net dimension 32 exceeds DIMMAX=31')
    short = td / 'net_6byte.net'
    short.write_bytes(bytes(6))
    case('net_6_bytes', netf=short, path_of='net', reason=r'truncated net header \(6 of 12 bytes\)')
    g9 = dict(g, header=[g['header'][0], '9', *g['header'][2:]])
    case('gfile_L_9', gfile=gfile_text(g9), path_of='gfile', reason=r'L 9 out of range \[2,8\]')
    l8 = gfile_tokens(synthetic_l8())
    l8['masks'][0] = str(1 << 16)
    case('gfile_L8_mask_bit16', L=8, gfile=gfile_text(l8), path_of='gfile', reason=r'mask 0 65536 out of range \[0,65535\]')
    names = ['magic', 'L', 'id', 'wa', 'wb', 'M', 'T', 'mask 0']
    toks = gtext.split()
    for k in range(1, 8):
        case(f'gfile_truncated_after_header_token_{k}', gfile=' '.join(toks[:k]) + '\n', path_of='gfile',
             reason=rf'truncated or malformed {names[k]} \(end of file\)')

    def term_edit(fn):
        x = json.loads(json.dumps(g))
        fn(x)
        return gfile_text(x)
    case('term_index_M', gfile=term_edit(lambda x: x['terms'][0][1].__setitem__(-1, str(M))), path_of='gfile',
         reason=rf'term 0 index {n0 - 1} {M} out of range \[0,{M - 1}\]')
    case('term_index_-1', gfile=term_edit(lambda x: x['terms'][0][1].__setitem__(0, '-1')), path_of='gfile',
         reason=r'term 0 index 0 -1 out of range')
    for v in (0, M + 1):
        case(f'term_length_{v}', gfile=term_edit(lambda x, v=v: x['terms'][0].__setitem__(0, str(v))), path_of='gfile',
             reason=rf'term 0 length {v} out of range \[1,{M}\]')
    case('rate_count_2^E-1', gfile=term_edit(lambda x: x.__setitem__('count', str((1 << E) - 1))), path_of='gfile',
         reason=rf'rate count {(1 << E) - 1} out of range')
    for k, (txt, want) in enumerate((('C8D3TASKS1\n', 'order'), ('C8D3TASKS1 8\n', 'L'), ('C8D3TASKS1 8 3\n', 'task count'))):
        case(f'task_cut_after_{["magic", "order", "L"][k]}', tasks=txt, path_of='tasks', reason=rf'truncated or malformed task header \({want}\)')
    for k, txt in enumerate(('1 5 32\n', f'1 5 32\n{base_id}')):
        gp = td / f'grid_cut{k}.txt'
        gp.write_text(txt)
        case(f'grid_cut_{"before" if k == 0 else "inside"}_id', grid=str(gp), path_of='grid', reason=r'truncated or malformed grid row 0')
    return cases


def run_bad(exe: Path, c: dict, td: Path, threads: int = 1):
    d, gm, nf, tp, layout, grid = c['args']
    data, cp = nc.run_worker(exe, d, gm, nf, tp, td / 'bad_out.json', SEED, layout, '.8', threads, grid=grid, check=False)
    ok = data is None and cp.returncode == 2 and re.search(re.escape(c['path']) + r'.*' + c['reason'], cp.stderr)
    return bool(ok), cp


def part_bad_inputs(td, threads, full):
    inv = nc.inventory()
    base_id = min(inv['free']['3'], key=lambda r: r['length'])['id']
    with nc.extracted([('free', 3, base_id)]) as root:
        cases = bad_cases(td, root / 'free', base_id)
    failures = []
    for b, exe in nc.C8.items():
        for c in cases:
            ok, cp = run_bad(exe, c, td)
            if not ok:
                failures.append((b, c['name'], cp.returncode, cp.stderr[-400:]))
    if failures:
        raise AssertionError(f'bad_inputs: {failures}')
    record(test='bad_inputs', cases=[c['name'] for c in cases], backends=list(nc.C8), gate='exit 2 with the file path and the reason')


def part_orders(td, threads, full):
    with nc.extracted([('free', 2, 0)]) as root:
        out = {}
        for b, exe in nc.C8.items():
            for order in (7, 8):
                netf = nc.net(td, nc.dim_of(2, 0), 52, 4242)
                t = nc.write_tasks(td / 'l2tasks', 2, nc.task_rows([0]), order=order)
                d, _ = nc.run_worker(exe, root / 'free', nc.GAMMA[order], netf, t, td / 'l2.json', SEED, 0, '.8', threads)
                w = {len(r['values']) for r in d['rows']}
                if w != {2 * (order + 1 - 2)}:
                    raise AssertionError(f'L2 at order {order}: widths {w}')
                # A-KER-2: the native JSON's identity fields
                g = d.get('gmp') or {}
                gmp_ok = (g.get('applicable') is True and g.get('runtime_version') == g.get('header_version') == '6.2.1') if b == 'gmp' else g == {'applicable': False}
                if (d.get('schema'), d.get('order'), d.get('numerics'), d.get('mp_check')) != ('c8-d3-hpc-native-1', order, 'exact', 'off') \
                        or not (isinstance(d.get('max_rss_kb'), int) and d['max_rss_kb'] > 0) or not gmp_ok or not d.get('libraries'):
                    raise AssertionError(f'{b} order {order}: native JSON identity fields {[d.get(k) for k in ("schema", "order", "numerics", "mp_check", "max_rss_kb", "gmp")]}')
                out[f'{b}_order{order}'] = sorted(w)
    record(test='L2_both_orders', widths=out, K={'order7': 5, 'order8': 6})


def part_splits(td, threads, full):
    inv = nc.inventory()
    L = 7
    picks = {s: [r['id'] for r in sorted(inv[s]['7'], key=lambda r: -r['cost'])[:3]] for s in nc.SECTORS}
    with nc.extracted([(s, L, g) for s, ids in picks.items() for g in ids]) as root:
        for b, exe in nc.C8.items():
            for s, ids in picks.items():
                for layout in (0, 1, 2):
                    netf = nc.net(td, nc.dim_of(L, layout), 52, 273845 + layout)
                    whole_t = nc.write_tasks(td / 'whole', L, nc.task_rows(ids), order=8)
                    split_t = nc.write_tasks(td / 'split', L, nc.task_rows(ids, chunk=23), order=8)
                    whole, _ = nc.run_worker(exe, root / s, nc.GAMMA[8], netf, whole_t, td / 'w.json', 741987, layout, '.9', 1)
                    many, _ = nc.run_worker(exe, root / s, nc.GAMMA[8], netf, split_t, td / 'm.json', 741987, layout, '.9', 4)
                    one, _ = nc.run_worker(exe, root / s, nc.GAMMA[8], netf, split_t, td / 'o.json', 741987, layout, '.9', 1)
                    if [nc.scientific(r) for r in many['rows']] != [nc.scientific(r) for r in one['rows']]:
                        raise AssertionError(f'{b} {s} layout {layout}: thread-dependent rows')
                    sums = {}
                    for r in one['rows']:
                        k = (r['rep'], r['graph'])
                        sums[k] = [a + D(v) for a, v in zip(sums.get(k, [D(0)] * len(r['values'])), r['values'])]
                    e = max(nc.normalized(v, str(z)) for r in whole['rows'] for v, z in zip(r['values'], sums[(r['rep'], r['graph'])]))
                    if e > D('1e-12'):
                        raise AssertionError(('split', b, s, layout, e))
                    record(test='random_access_threads', backend=b, sector=s, layout=layout, order=8, max_normalized_difference=str(e), threads=[1, 4], chunk_size=23)


def part_bk8(td, threads, full):
    """A-RPL-3 (G-BK8; J-VAL-3): decimal against gmp at L7 and L8 (the loops present), 400 kernels per sector (the 100
    heaviest and 300 random, seed 81113), 2 x 256 points, order 8, rate .8, layout 0: counters identical; rows exact
    where mp = 0; normalized |x - y| / max(1, |x|) <= 1e-13 where mp > 0 (a6ce987 tests/validate.py:7-9)."""
    import random
    inv = nc.inventory()
    rng = random.Random(81113)
    for L in [L for L in (7, 8) if str(L) in inv['free']]:
        for s in nc.SECTORS:
            rows = inv[s][str(L)]
            heavy = [r['id'] for r in sorted(rows, key=lambda r: -r['cost'])[:100]]
            rest = [r['id'] for r in rows if r['id'] not in heavy]
            ids = sorted(heavy + rng.sample(rest, min(300, len(rest))))
            netf = nc.net(td, nc.dim_of(L, 0), 52, 81113 + L)
            t = nc.write_tasks(td / 'bk8_tasks', L, nc.task_rows(ids, points=256), order=8)
            with nc.extracted([(s, L, g) for g in ids]) as root:
                out = {b: nc.run_worker(exe, root / s, nc.GAMMA[8], netf, t, td / f'bk8_{b}.json', SEED, 0, '.8', threads)[0] for b, exe in nc.C8.items()}
            err, mp_rows = D(0), 0
            for x, y in zip(out['gmp']['rows'], out['decimal']['rows'], strict=True):
                if (x['uid'], x['quad'], x['mp']) != (y['uid'], y['quad'], y['mp']):
                    raise AssertionError(f'G-BK8 {s} L{L} graph {x["graph"]}: counters differ ({x["quad"]},{x["mp"]} vs {y["quad"]},{y["mp"]})')
                if x['mp'] == 0:
                    if x['values'] != y['values']:
                        raise AssertionError(f'G-BK8 {s} L{L} graph {x["graph"]}: values differ on a row with mp = 0')
                else:
                    mp_rows += 1
                    err = max(err, max(nc.normalized(u, v) for u, v in zip(x['values'], y['values'])))
            if err > D('1e-13'):
                raise AssertionError(f'G-BK8 {s} L{L}: normalized difference {err} on mp > 0 rows')
            record(test='G-BK8', sector=s, L=L, graphs=len(ids), points='2 x 256', rows=len(out['gmp']['rows']), mp_rows=mp_rows,
                   max_normalized_on_mp_rows=str(err), gate='counters identical; exact where mp = 0; <= 1e-13 normalized where mp > 0')


def part_l2_control(td, threads, full):
    """A-IN-6 (J-VAL-3): the L2 graph at order 8 (K = 6), campaigns a (rate .8, 52-bit net) and b (rate .7, 60-bit),
    32 replicates x 2^16 points each, native seeds L2_SEED + 52 / + 60 and net seeds 220052 / 220060 (all registered in
    $C8_SEEDS with the base L2_SEED, Stage 3a repair round 3; mirrored in designs/forbidden_seeds.json): each b slot
    j = 0..6 within 4 SE of B2[j] (inputs/two_loop.json, 7 strings) per campaign and combined; wb/wa = 1/6 exactly as
    Fractions of the header tokens; |b_j - 6 c_j| <= 2^-60 |b_j| per row and for the merged Decimal sums (the separate
    roundings of the value assignment)."""
    from fractions import Fraction
    two = json.loads((nc.ROOT / 'inputs/two_loop.json').read_text())
    B2 = [D(x) for x in two['B2']]
    if (two.get('order'), len(B2)) != (8, 7):
        raise AssertionError('inputs/two_loop.json is not the order-8 jet with 7 B2 strings')
    tol = D(2) ** -60
    out = {}
    with nc.extracted([('free', 2, 0)]) as root:
        head = (root / 'free/L2/G0.txt').read_text().split()
        if Fraction(head[4]) / Fraction(head[3]) != Fraction(1, 6):
            raise AssertionError(f'L2 graph: wb/wa = {head[4]}/{head[3]} is not 1/6')
        means = {}
        for camp, rate, bits in (('a', '.8', 52), ('b', '.7', 60)):
            netf = nc.net(td, nc.dim_of(2, 0), bits, 220000 + bits, B=32)
            t = nc.write_tasks(td / 'l2c_tasks', 2, nc.task_rows([0], reps=32, points=1 << 16), order=8)
            d, _ = nc.run_worker(nc.C8['gmp'], root / 'free', nc.GAMMA[8], netf, t, td / 'l2c.json', L2_SEED + bits, 0, rate, threads)
            vals = [[D(v) for v in r['values']] for r in d['rows']]
            for r in vals:
                for j in range(7):
                    if abs(r[j] - 6 * r[7 + j]) > tol * abs(r[j]):
                        raise AssertionError(f'L2 control {camp}: |b_{j} - 6 c_{j}| > 2^-60 |b_{j}| in a row')
            n = D(len(vals))
            mean = [sum(r[j] for r in vals) / n for j in range(14)]
            se = [(sum((r[j] - mean[j]) ** 2 for r in vals) / (n - 1) / n).sqrt() for j in range(14)]
            sums = [sum(r[j] for r in vals) for j in range(14)]
            for j in range(7):
                if abs(sums[j] - 6 * sums[7 + j]) > tol * abs(sums[j]):
                    raise AssertionError(f'L2 control {camp}: merged |b_{j} - 6 c_{j}| > 2^-60 |b_{j}|')
            pulls = [(mean[j] - B2[j]) / se[j] for j in range(7)]
            if any(abs(p) > 4 for p in pulls):
                raise AssertionError(f'L2 control {camp}: pulls {[f"{p:.2f}" for p in pulls]} (|pull| <= 4 required)')
            means[camp] = (mean, se)
            out[camp] = {'pulls': [f'{p:.3f}' for p in pulls], 'mean': [str(m) for m in mean[:7]], 'se': [f'{e:.3e}' for e in se[:7]]}
        comb = [(means['a'][0][j] + means['b'][0][j]) / 2 for j in range(7)]
        cse = [((means['a'][1][j] ** 2 + means['b'][1][j] ** 2).sqrt()) / 2 for j in range(7)]
        cp = [(comb[j] - B2[j]) / cse[j] for j in range(7)]
        if any(abs(p) > 4 for p in cp):
            raise AssertionError(f'L2 control combined: pulls {[f"{p:.2f}" for p in cp]}')
        out['combined'] = {'pulls': [f'{p:.3f}' for p in cp]}
    record(test='A-IN-6 L2 control (order 8, K = 6)', replicates=32, points=1 << 16, seed=L2_SEED, **out,
           gate='|pull| <= 4 for b_0..b_6 per campaign and combined; wb/wa = 1/6; |b_j - 6 c_j| <= 2^-60 |b_j| per row and merged')


# ---- A-RPL-8 G-L8SELF (Stage 4b) -----------------------------------------------------------------------------------
# The L8 sweep sample (PLAN A-RPL-8, A-PERF-2): 2,000 L8 kernels, 2 replicates x 512 points. Seeds (HD6): both are
# registered test seeds of G-BK8 (the kernel draw 81113 and its L8 net seed 81113 + 8), reused here by name.
L8SELF_DRAW = 81113
L8SELF_NET_SEED = 81121
L8SELF_POINTS = 512
L8SELF_SIZES = {'heavy': 100, 'free': 1500, 'power': 300}
# Native header fields that describe the run (threads excepted), not the science: timing, memory, loaded-graph count.
RUN_FIELDS = {'load_seconds', 'integration_seconds', 'graphs_loaded', 'max_rss_kb', 'max_rss_source', 'rusage_maxrss_kb'}


def l8self_sample(inv: dict | None = None, sizes: dict | None = None) -> dict:
    """The L8 sweep sample: per sector the `heavy` costliest kernels (inventory cost, stable order as G-BK8) and a draw of
    random.Random(L8SELF_DRAW) from the rest (free first, then power), ids ascending. 100 + 1,500 free and 100 + 300
    power by default (the L8 population is 16,064 free : 4,336 power)."""
    import random
    inv = inv or nc.inventory()
    z = {**L8SELF_SIZES, **(sizes or {})}
    rng = random.Random(L8SELF_DRAW)
    out = {}
    for s in nc.SECTORS:
        rows = inv[s]['8']
        heavy = [r['id'] for r in sorted(rows, key=lambda r: -r['cost'])[:z['heavy']]]
        hs = set(heavy)
        rest = [r['id'] for r in rows if r['id'] not in hs]
        out[s] = sorted(heavy + rng.sample(rest, min(z[s], len(rest))))
    return out


def l8self_net(td: Path) -> Path:
    """The sample's net: 2 scrambled 52-bit matrices of dimension 31 (L8, layout 0), seed L8SELF_NET_SEED."""
    return nc.net(td, nc.dim_of(8, 0), 52, L8SELF_NET_SEED)


def part_l8self(td, threads, full, base: Path | None = None, jobs: int = 1, sizes: dict | None = None):
    """A-RPL-8 (G-L8SELF; Stage 4b): bin/c8d3_{gmp,decimal} against the Stage-3 baseline base/c8d3_{gmp,decimal} (tag
    c8-stage3, `make baseline`) on the L8 sweep sample, 2 replicates x 512 points per kernel, order 8, rate .8, layout 0,
    native seed SEED, --mp-check on (the production mode): every row field but "seconds" and every header field but the
    run fields (timing, memory, loaded-graph count; the executable's own path in "libraries") exactly equal, both
    backends. Blocks of 25 kernels (50 tasks) run `jobs` at a time with `threads` threads each."""
    import concurrent.futures
    import shutil
    if base is None:
        raise ValueError('l8self needs the baseline directory (--l8self DIR)')
    base = Path(base)
    old = {b: base / f'c8d3_{b}' for b in nc.C8}
    nc.require(*nc.C8.values(), *old.values())
    inv = nc.inventory()
    if '8' not in inv['free']:
        raise AssertionError('G-L8SELF: no L8 kernels in the inventory (Stage 2b inputs needed)')
    sample = l8self_sample(inv, sizes)
    netf = l8self_net(td)
    stats = {(s, b): dict(graphs=0, rows=0, quad_points=0, mp_points=0, mp_rows=0, mp_checked=0) for s in nc.SECTORS for b in nc.C8}
    t0 = time.time()
    with nc.extracted([(s, 8, g) for s in nc.SECTORS for g in sample[s]]) as root:
        items = [(s, sample[s][k:k + 25]) for s in nc.SECTORS for k in range(0, len(sample[s]), 25)]

        def one(it):
            s, ids = it
            d = Path(tempfile.mkdtemp(prefix='l8self_', dir=td))
            t = nc.write_tasks(d / 'tasks', 8, nc.task_rows(ids, reps=2, points=L8SELF_POINTS), order=8)
            res = {}
            for b in nc.C8:
                x, _ = nc.run_worker(old[b], root / s, nc.GAMMA[8], netf, t, d / 'base.json', SEED, 0, '.8', threads, mp_check='on')
                y, _ = nc.run_worker(nc.C8[b], root / s, nc.GAMMA[8], netf, t, d / 'new.json', SEED, 0, '.8', threads, mp_check='on')
                # 'libraries' lists the loaded objects, the executable itself first: compared without the two executables
                hx = {k: v for k, v in x.items() if k not in RUN_FIELDS and k != 'rows'}
                hy = {k: v for k, v in y.items() if k not in RUN_FIELDS and k != 'rows'}
                hx['libraries'] = [q for q in x.get('libraries') or [] if q != str(old[b].resolve())]
                hy['libraries'] = [q for q in y.get('libraries') or [] if q != str(nc.C8[b].resolve())]
                if hx != hy:
                    raise AssertionError(f'G-L8SELF {b} {s} graphs {ids[0]}..{ids[-1]}: header fields differ: '
                                         f'{sorted(k for k in set(hx) | set(hy) if hx.get(k) != hy.get(k))}')
                e = nc.rows_equal(x, y, [k for k in x['rows'][0] if k != 'seconds'])
                if e:
                    raise AssertionError(f'G-L8SELF {b} {s}: {e}')
                res[b] = (len(y['rows']), sum(r['quad'] for r in y['rows']), sum(r['mp'] for r in y['rows']),
                          sum(r['mp'] > 0 for r in y['rows']), sum(r.get('mp_checked', 0) for r in y['rows']))
            shutil.rmtree(d, ignore_errors=True)
            return s, len(ids), res

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            for k, (s, n, res) in enumerate(pool.map(one, items)):
                for b, (rows, q, mp, mpr, chk) in res.items():
                    st = stats[(s, b)]
                    st['graphs'] += n
                    st['rows'] += rows
                    st['quad_points'] += q
                    st['mp_points'] += mp
                    st['mp_rows'] += mpr
                    st['mp_checked'] += chk
                print(f'G-L8SELF {k + 1}/{len(items)} blocks ({time.time() - t0:.0f} s)', flush=True)
    for (s, b), st in sorted(stats.items()):
        record(test='G-L8SELF', sector=s, backend=b, **st, points_per_task=L8SELF_POINTS, replicates=2, order=8, rate='.8', layout=0,
               mp_check='on', seed=SEED, net_seed=L8SELF_NET_SEED, draw_seed=L8SELF_DRAW,
               baseline={bb: nc.digest(e) for bb, e in old.items()}, candidate={bb: nc.digest(e) for bb, e in nc.C8.items()},
               gate='every row field but seconds and every header field but timing, memory and graphs_loaded exactly equal')


L2_SEED = 6602215
PARTS = {'identity': part_identity, 'g_c7': lambda td, t, f: part_replay(td, t, f, True, True), 'bad_inputs': part_bad_inputs,
         'orders': part_orders, 'splits': part_splits, 'bk8': part_bk8, 'l2_control': part_l2_control}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--threads', type=int, default=nc.threads_default())
    ap.add_argument('--parts', default='identity,g_c7,bad_inputs,orders,splits',
                    help='comma list of identity, g_c7 (runs G-C7 and G-JET together), g_jet (G-JET alone), bad_inputs, orders, splits, '
                         'bk8, l2_control')
    ap.add_argument('--bk8', action='store_true', help='add the G-BK8 part (A-RPL-3; J-VAL-3)')
    ap.add_argument('--l2-control', action='store_true', help='add the L=2 control (A-IN-6; J-VAL-3)')
    ap.add_argument('--l8self', type=Path, metavar='DIR', help='add G-L8SELF (A-RPL-8; Stage 4b): DIR holds the Stage-3 baseline '
                    'c8d3_gmp and c8d3_decimal (bin/baseline after `make baseline STORE=...`)')
    ap.add_argument('--jobs', type=int, default=1, help='G-L8SELF blocks run concurrently (each with --threads threads)')
    ap.add_argument('--l8self-sizes', help='SMOKE ONLY (never the gate): HEAVY,FREE,POWER kernels instead of 100,1500,300')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    parts = [p for p in a.parts.split(',') if p and p != 'none'] + (['bk8'] if a.bk8 else []) + (['l2_control'] if a.l2_control else []) \
        + (['l8self'] if a.l8self else [])
    if not parts:
        ap.error('no part selected (--parts none needs --bk8, --l2-control or --l8self)')
    unknown = [p for p in parts if p not in PARTS and p not in ('g_jet', 'l8self')]
    if unknown:
        ap.error(f'unknown parts {unknown}')
    a.parts = ','.join(parts)
    nc.require(*nc.C8.values(), *([] if parts == ['l8self'] else nc.C7REF.values()))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='c8d3_validate_') as td:
        td = Path(td)
        for p in parts:
            if p == 'g_jet':
                part_replay(td, a.threads, a.full, do_c7=False, do_jet=True)
            elif p == 'l8self':
                sz = dict(zip(('heavy', 'free', 'power'), map(int, a.l8self_sizes.split(',')))) if a.l8self_sizes else None
                part_l8self(td, a.threads, a.full, a.l8self.resolve(), a.jobs, sz)
            else:
                PARTS[p](td, a.threads, a.full)
    res = dict(status='passed', full=a.full, parts=parts, smoke=bool(a.l8self_sizes), tests=RESULTS, threads=a.threads, host=nc.host_info(),
               executables={k: str(v) for k, v in {**{f'c8d3_{b}': e for b, e in nc.C8.items()}, **{f'ref/c7d3_{b}': e for b, e in nc.C7REF.items()}}.items()},
               sha256={str(e): nc.digest(e) for e in (*nc.C8.values(), *nc.C7REF.values()) if Path(e).exists()}, wall_seconds=round(time.time() - t0, 1))
    nc.dump(a.output, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'tests'}, indent=2))


if __name__ == '__main__':
    main()
