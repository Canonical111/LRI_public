#!/usr/bin/env python3
"""Class-B fields and the MP self-check (PLAN.md A-KER-6 (a)-(e), A-KER-7; C.3, C.4). Expanse: needs
`make gmp decimal inspect test-builds`.

  python3 -B tests/class_b.py [--threads N] [--parts deep,a,bcd,e,f] [--d3-payload TREE --d3-pin SHA]
                             [--zero-channel-tails FILE] [--output FILE]

  (a) values, counters (quad, mp) and max_abs are exact between bin/c8d3_gmp with --mp-check off, on and stride16 and
      the test-only build without the tail fields (bin/diag/c8d3_gmp_notail, -DC8_NO_TAIL_FIELDS); and between
      bin/c8d3_decimal with --mp-check off and on. Sample: the L2 graph and the first 4 and 4 heaviest kernels of
      every (sector, L) at L3-L7, and from Stage 3b at L8, 2 replicates x 64 points, order 8, rate .8, layout 0.
  (b) a whole task and its 23-point chunks give the same tail_top and tail_argmax bitwise (merged with tools/tails.py)
      and tail_sum within 1e-15 relative: the 3 heaviest L7 kernels per sector, 2 x 256 points, layouts 0 and 2.
  (c) `c8d3_inspect --point` at a row's tail_argmax reproduces its tail_top[0] bit for bit (every row of (b)).
  (d) the merged graph_tails.csv (tools/tails.tails_csv) equals a hand merge of the chunk rows, written here
      independently; graph_promotions.csv sums the counters.
  (e) zero-channel kernels (s_G = 4, 3 w_B = w_A): for the power-L3 kernel and the zero-channel kernel of the highest
      loop present in the packs, max_abs is 0 while tail_top[0] > 0 and tail_sum is positive and finite. With
      --d3-payload TREE --d3-pin SHA (the published d=3 payload of Stage 1b and the sha256 of its MANIFEST_d3.json, the
      A.5 gate record's pin): the same for one zero-channel NEW L7 kernel per sector (an L7 member of the payload that
      the inventory's C7(3) L7 rows do not hold, |3 w_B - w_A| <= 1e-18 |w_A| from its header, the fewest terms,
      then the lowest id), its bytes verified along the payload's checksum chain (pin -> MANIFEST_d3.json ->
      SHA256SUMS -> MEMBERS_d3.sha256 and the tar -> the member). Before Stage 2b the packs hold no new L7 kernel.
      With --zero-channel-tails FILE (A-DES-3's real-tail part, Stage 3a repair round 2): every kernel of (e) (the
      power-L3 kernel, the top-loop one, and the new L7 ones with --d3-payload) is integrated as a pilot graph would be:
      campaigns a (rate .8, 52-bit net) and b (rate .7, 60-bit net), 8 replicates x 32,768 points with nest [4096],
      i.e. the two tasks [0, 4096) and [4096, 32768) per replicate (production.task_bounds), order 8, layout 0,
      --mp-check on (the plan default). Every row must be zero-channel (max_abs 0, tail_top[0] > 0, tail_sum > 0 and
      finite). FILE (schema c8-d3-zero-channel-tails-1) holds the rows; tests/test_pilot_report.py --zero-channel FILE
      feeds them to pilot_report (tail_stats, screen_graph, confirm_graph), and tests/fixtures/zero_channel_tails.json
      is a pinned copy for the Mac run.
  (f) (Stage 3b) at L8, tail_top[0] x |norm (3 w_B - w_A)| equals max_abs to 1e-18 relative in every row (part_f).
  A-KER-7: the deep-cancellation fixture (tests/fixtures/deep_cancellation) at orders 7 and 8: every point reaches the
      MP tier; with --mp-check on, mp_checked = mp = points, every point raises mp_alarm (gmp350) and sum(mp_hist) =
      mp_checked; with stride16, mp_checked = mp_alarm = the points whose index = 0 mod 16. On the real rows of (a):
      sum(mp_hist) = mp_checked in every row; mp_checked = mp under on; and under stride16 mp_checked equals the
      number of MP points with index = 0 mod 16, counted by one-point tasks at those indices.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
import tails as cb  # noqa: E402  (tools/tails.py)

SEED = 6619043
NOTAIL = nc.BIN / 'diag/c8d3_gmp_notail'
FIXTURE = nc.ROOT / 'tests/fixtures/deep_cancellation'
RESULTS: list[dict] = []


def record(**kw):
    RESULTS.append(kw)
    print(json.dumps(kw, default=str), flush=True)


def core(r):
    return {k: r[k] for k in ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'quad', 'mp', 'max_abs', 'values')}


def check_hist(d: dict, mode: str, what: str):
    for r in d['rows']:
        if sum(r['mp_hist']) != r['mp_checked']:
            raise AssertionError(f'{what}: sum(mp_hist) != mp_checked at uid {r["uid"]}')
        if mode == 'on' and r['mp_checked'] != r['mp']:
            raise AssertionError(f'{what}: mp_checked {r["mp_checked"]} != mp {r["mp"]} under on (uid {r["uid"]})')


def loops_present(inv) -> list[int]:
    """L3..L8 as the inventory holds them (L8 from Stage 2b on)."""
    return [L for L in range(3, 9) if all(str(L) in inv[s] for s in nc.SECTORS)]


def part_a(td, threads, inv):
    groups = [('free', 2, [0])] + [(s, L, nc.kernels(inv, s, L, False, 4, 4)) for s in nc.SECTORS for L in loops_present(inv)]
    sel = [(s, L, g) for s, L, ids in groups for g in ids]
    stats = dict(rows=0, mp_rows=0, mp_points=0, stride_points_checked=0, alarms=0)
    with nc.extracted(sel) as root:
        for s, L, ids in groups:
            netf = nc.net(td, nc.dim_of(L, 0), 52, 7700 + L)
            rows = nc.task_rows(ids)
            t = nc.write_tasks(td / 'a_tasks', L, rows, order=8)
            args = (root / s, nc.GAMMA[8], netf, t)
            runs = {}
            for mode in ('off', 'on', 'stride16'):
                runs[mode], _ = nc.run_worker(nc.C8['gmp'], *args, td / f'a_{mode}.json', SEED, 0, '.8', threads, mp_check=mode)
            runs['notail'], _ = nc.run_worker(NOTAIL, *args, td / 'a_notail.json', SEED, 0, '.8', threads)
            if any('tail_top' in r for r in runs['notail']['rows']) or runs['notail'].get('diagnostic_kind') != 'no_tail_fields':
                raise AssertionError('the no-tail build still writes tail fields')
            ref = [core(r) for r in runs['off']['rows']]
            for k, d in runs.items():
                if [core(r) for r in d['rows']] != ref:
                    raise AssertionError(f'(a) {s} L{L}: values/counters/max_abs differ between off and {k}')
            for mode in ('on', 'stride16'):
                check_hist(runs[mode], mode, f'{s} L{L} {mode}')
            dec = {}
            for mode in ('off', 'on'):
                dec[mode], _ = nc.run_worker(nc.C8['decimal'], *args, td / f'a_dec_{mode}.json', SEED, 0, '.8', threads, mp_check=mode)
            if [core(r) for r in dec['off']['rows']] != [core(r) for r in dec['on']['rows']]:
                raise AssertionError(f'(a) decimal {s} L{L}: on differs from off')
            check_hist(dec['on'], 'on', f'decimal {s} L{L}')
            # stride16: the MP points with index = 0 mod 16, counted by one-point tasks in mode off.
            one = [(i, r, g, p, p + 1, 64) for i, (r, g, p) in enumerate((r, g, p) for r in range(2) for g in ids for p in range(0, 64, 16))]
            t1 = nc.write_tasks(td / 'a_one', L, one, order=8)
            single, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, t1, td / 'a_one.json', SEED, 0, '.8', threads)
            want = {}
            for r in single['rows']:
                want[(r['rep'], r['graph'])] = want.get((r['rep'], r['graph']), 0) + r['mp']
            for r in runs['stride16']['rows']:
                if r['mp_checked'] != want[(r['rep'], r['graph'])]:
                    raise AssertionError(f'(a) stride16 {s} L{L} graph {r["graph"]}: mp_checked {r["mp_checked"]} != {want[(r["rep"], r["graph"])]}')
            stats['rows'] += len(ref)
            stats['mp_rows'] += sum(r['mp'] > 0 for r in ref)
            stats['mp_points'] += sum(r['mp'] for r in ref)
            stats['stride_points_checked'] += sum(r['mp_checked'] for r in runs['stride16']['rows'])
            stats['alarms'] += sum(r['mp_alarm'] for r in runs['on']['rows'])
    record(test='A-KER-6 (a) and A-KER-7 real rows', gate='values, quad, mp, max_abs exact across off/on/stride16/no-tail (gmp) and off/on (decimal); '
           'sum(mp_hist) = mp_checked; on: mp_checked = mp; stride16: mp_checked = MP points with index = 0 mod 16', **stats)


def merged_by_hand(rows):
    """An independent merge of chunk rows: per (rep, graph) the union's 16 largest, its argmax, the exact sum."""
    acc = {}
    for r in rows:
        a = acc.setdefault((r['rep'], r['graph']), {'vals': [], 'arg': [], 'sum': [], 'points': 0})
        a['vals'].extend(r['tail_top'])
        a['arg'].append((D(r['tail_top'][0]), r['tail_argmax']))
        a['sum'].append(D(r['tail_sum']))
        a['points'] += r['end'] - r['begin']
    lines = [','.join(cb.TAIL_HEADER)]
    for (rep, g) in sorted(acc):
        a = acc[(rep, g)]
        vals = sorted(a['vals'], key=lambda x: -D(x))[:16]
        best = max(v for v, _ in a['arg'])
        arg = min(i for v, i in a['arg'] if v == best)
        lines.append(','.join(map(str, [rep, g, a['points'], cb.exact_sum(a['sum']), arg, len(vals), *vals, *([''] * (16 - len(vals)))])))
    return '\n'.join(lines) + '\n'


def part_bcd(td, threads, inv):
    L = 7
    picks = {s: [r['id'] for r in sorted(inv[s]['7'], key=lambda r: -r['cost'])[:3]] for s in nc.SECTORS}
    checked = 0
    with nc.extracted([(s, L, g) for s, ids in picks.items() for g in ids]) as root:
        for s, ids in picks.items():
            for layout in (0, 2):
                netf = nc.net(td, nc.dim_of(L, layout), 60, 8800 + layout)
                whole_t = nc.write_tasks(td / 'b_whole', L, nc.task_rows(ids, points=256), order=8)
                chunk_t = nc.write_tasks(td / 'b_chunk', L, nc.task_rows(ids, points=256, chunk=23), order=8)
                whole, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, whole_t, td / 'b_w.json', SEED, layout, '.7', threads)
                chunks, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, chunk_t, td / 'b_c.json', SEED, layout, '.7', threads)
                merged = cb.merge_tails(chunks['rows'])
                for r in whole['rows']:
                    m = merged[(r['rep'], r['graph'])]
                    if m['tail_top'] != r['tail_top'] or m['tail_argmax'] != r['tail_argmax'] or m['points'] != 256:
                        raise AssertionError(f'(b) {s} layout {layout} graph {r["graph"]}: chunked tail fields differ from the whole task')
                    rel = abs(m['tail_sum'] - D(r['tail_sum'])) / D(r['tail_sum'])
                    if rel > D('1e-15'):
                        raise AssertionError(f'(b) {s} graph {r["graph"]}: tail_sum differs by {rel}')
                    # (c) the inspector regenerates the argmax point
                    cp = subprocess.run([str(nc.INSPECT), '--point', str(r['graph']), str(r['rep']), str(r['tail_argmax']), '--', str(root / s), str(L),
                                         str(netf), str(SEED), str(layout), '.7', '-'], capture_output=True, text=True)
                    if cp.returncode:
                        raise AssertionError(f'(c) c8d3_inspect --point failed: {cp.stderr[-500:]}')
                    p = json.loads(cp.stdout)
                    if p['abs_t'] != r['tail_top'][0]:
                        raise AssertionError(f'(c) {s} graph {r["graph"]} rep {r["rep"]}: --point |t| {p["abs_t"]} != tail_top[0] {r["tail_top"][0]}')
                    checked += 1
                # (d) graph_tails.csv against a hand merge; graph_promotions.csv sums
                if cb.tails_csv(chunks['rows']) != merged_by_hand(chunks['rows']):
                    raise AssertionError(f'(d) {s} layout {layout}: graph_tails.csv differs from the hand merge')
                pro = cb.merge_promotions(chunks['rows'])
                for r in whole['rows']:
                    m = pro[(r['rep'], r['graph'])]
                    if (m['quad'], m['mp'], m['nondirect'], m['nonmoderate']) != (r['quad'], r['mp'], r['nondirect'], r['nonmoderate']):
                        raise AssertionError(f'(d) {s} graph {r["graph"]}: merged promotion counters differ from the whole task')
    record(test='A-KER-6 (b)(c)(d)', rows_checked=checked, gate='chunked tail_top/argmax bitwise, tail_sum <= 1e-15 rel; --point |t| = tail_top[0]; '
           'graph_tails.csv = hand merge; promotion counters sum to the whole task')


def _sha(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _sums(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        h, _, name = line.partition('  ')
        out[name] = h
    return out


def new_l7_zero_channel(tree: Path, pin: str, inv: dict, dest: Path) -> list:
    """One zero-channel new L7 kernel per sector from the published d=3 payload TREE, verified along its checksum chain
    and written as dest/<sector>/L7/G<id>.txt; returns [(sector, id, record)]."""
    import tarfile
    tree = Path(tree)
    man_bytes = (tree / 'MANIFEST_d3.json').read_bytes()
    if _sha(man_bytes) != pin:
        raise AssertionError(f'{tree}/MANIFEST_d3.json: sha256 {_sha(man_bytes)} is not the pin {pin}')
    man = json.loads(man_bytes)
    sums_bytes = (tree / 'SHA256SUMS').read_bytes()
    if _sha(sums_bytes) != man['sha256sums_sha256']:
        raise AssertionError(f'{tree}/SHA256SUMS differs from MANIFEST_d3.json')
    sums = _sums(sums_bytes.decode())
    mem_bytes = (tree / 'MEMBERS_d3.sha256').read_bytes()
    if _sha(mem_bytes) != sums.get('MEMBERS_d3.sha256'):
        raise AssertionError(f'{tree}/MEMBERS_d3.sha256 differs from SHA256SUMS')
    members = _sums(mem_bytes.decode())
    out = []
    for s in nc.SECTORS:
        tar = tree / f'payload/L7_{s}.tar'
        if nc.digest(tar) != sums.get(f'payload/L7_{s}.tar') or nc.digest(tar) != man['payload'][f'L7_{s}']['sha256']:
            raise AssertionError(f'{tar} differs from SHA256SUMS / MANIFEST_d3.json')
        old = {r['id'] for r in inv[s]['7']}
        cands = []
        with tarfile.open(tar) as tf:
            for m in tf:
                gid = int(m.name.split('/G')[1][:-4])
                if gid in old:
                    continue
                tok = tf.extractfile(m).readline().decode().split()
                wa, wb, T = D(tok[3]), D(tok[4]), int(tok[6])
                if abs(3 * wb - wa) <= D('1e-18') * abs(wa):
                    cands.append((T, gid, m.name))
            if not cands:
                raise AssertionError(f'{tar}: no new zero-channel L7 kernel')
            T, gid, name = min(cands)
            data = tf.extractfile(name).read()
        if _sha(data) != members.get(name):
            raise AssertionError(f'{name}: sha256 differs from MEMBERS_d3.sha256')
        f = dest / s / 'L7' / f'G{gid}.txt'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        out.append((s, gid, {'member': name, 'sha256': _sha(data), 'terms': T, 'header': data.split(b'\n', 1)[0].decode(),
                             'new_zero_channel_candidates': len(cands)}))
    return out


def zero_row(r, what):
    if not (D(r['max_abs']) == 0 and D(r['tail_top'][0]) > 0 and D(r['tail_sum']) > 0 and D(r['tail_sum']).is_finite()):
        raise AssertionError(f'(e) {what}: max_abs {r["max_abs"]}, tail_top[0] {r["tail_top"][0]}, tail_sum {r["tail_sum"]}')


# A-DES-3's real-tail part (--zero-channel-tails): the pilot shape of one graph-campaign (E.6, D.3): R = 8 replicates of
# 32,768 points nested at 4,096, so two tasks per replicate (production.task_bounds cuts at the nest point).
ZC_POINTS, ZC_NEST, ZC_REPS = 32768, 4096, 8
ZC_CAMPAIGNS = {'a': ('.8', 52, 1), 'b': ('.7', 60, 2)}   # production.RATES and NET_BITS (HD12); a seed offset per campaign
ZC_FIELDS = ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'quad', 'mp', 'max_abs', 'values', 'tail_top', 'tail_sum', 'tail_argmax')


def zero_channel_tails(td, threads, kernels) -> list:
    """kernels: [(sector, L, graph, sector root, record)] -> one c8-d3-zero-channel-tails-1 kernel entry each."""
    out = []
    for s, L, g, root, rec in kernels:
        f = Path(root) / f'L{L}' / f'G{g}.txt'
        camps = {}
        for c, (rate, bits, off) in ZC_CAMPAIGNS.items():
            seed, nseed = SEED + off, 9950 + 100 * off + L
            netf = nc.net(td, nc.dim_of(L, 0), bits, nseed, B=ZC_REPS)   # one scrambled matrix per replicate, as production.make_net
            rows = []
            for r in range(ZC_REPS):
                for lo, hi in ((0, ZC_NEST), (ZC_NEST, ZC_POINTS)):
                    rows.append((len(rows), r, g, lo, hi, ZC_POINTS))
            t = nc.write_tasks(td / 'zc_tasks', L, rows, order=8)
            d, _ = nc.run_worker(nc.C8['gmp'], root, nc.GAMMA[8], netf, t, td / 'zc.json', seed, 0, rate, threads, mp_check='on')
            if len(d['rows']) != len(rows):
                raise AssertionError(f'zero-channel tails {s} L{L} G{g} {c}: {len(d["rows"])} rows for {len(rows)} tasks')
            for x in d['rows']:
                zero_row(x, f'zero-channel tails {s} L{L} G{g} campaign {c}')
            camps[c] = {'rate': rate, 'bits': bits, 'seed': seed, 'net_seed': nseed, 'layout': 0, 'mp_check': 'on',
                        'rows': [{k: x[k] for k in ZC_FIELDS} for x in sorted(d['rows'], key=lambda x: (x['rep'], x['begin']))]}
        out.append({'sector': s, 'L': L, 'graph': g, 'member_sha256': nc.digest(f), **rec, 'campaigns': camps})
    return out


def part_e(td, threads, inv, d3=None, tails_out=None):
    zero = {(s, int(L)): [r['id'] for r in rows if r['s_G'] == 4] for s in nc.SECTORS for L, rows in inv[s].items()}
    picks = [('power', 3, zero[('power', 3)][0])]
    top = max((L for (s, L), ids in zero.items() if ids), default=None)
    sector = 'free' if zero.get(('free', top)) else 'power'
    picks.append((sector, top, zero[(sector, top)][0]))
    out = []
    zc = []
    with nc.extracted(picks) as root:
        for s, L, g in picks:
            netf = nc.net(td, nc.dim_of(L, 0), 52, 9900 + L)
            t = nc.write_tasks(td / 'e_tasks', L, nc.task_rows([g]), order=8)
            d, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, t, td / 'e.json', SEED, 0, '.8', threads)
            for r in d['rows']:
                zero_row(r, f'{s} L{L} G{g}')
            out.append({'sector': s, 'L': L, 'graph': g, 'tail_top0': d['rows'][0]['tail_top'][0]})
        if tails_out:
            zc += zero_channel_tails(td, threads, [(s, L, g, root / s, {'source': 'inventory'}) for s, L, g in picks])
    new = []
    if d3 is not None:
        root = td / 'd3_new_l7'
        for s, g, rec in new_l7_zero_channel(d3[0], d3[1], inv, root):
            netf = nc.net(td, nc.dim_of(7, 0), 52, 9907)
            t = nc.write_tasks(td / 'e_new_tasks', 7, nc.task_rows([g]), order=8)
            d, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, t, td / 'e_new.json', SEED, 0, '.8', threads)
            for r in d['rows']:
                zero_row(r, f'new L7 {s} G{g}')
            new.append({'sector': s, 'L': 7, 'graph': g, **rec, 'rows': len(d['rows']), 'tail_top0': [r['tail_top'][0] for r in d['rows']],
                        'tail_sum': [r['tail_sum'] for r in d['rows']], 'max_abs': [r['max_abs'] for r in d['rows']]})
            if tails_out:
                zc += zero_channel_tails(td, threads, [(s, 7, g, root / s, {'source': 'd3_payload', 'payload_member': rec['member']})])
    record(test='A-KER-6 (e) zero channel', kernels=out, new_l7=new, d3_payload=({'tree': str(d3[0]), 'pin': d3[1]} if d3 else None),
           note=('one zero-channel NEW L7 kernel per sector from the published d=3 payload (pin above)' if d3 else
                 'no --d3-payload: the new L7 kernels are not checked here'))
    if tails_out:
        doc = {'schema': 'c8-d3-zero-channel-tails-1', 'order': 8, 'points': ZC_POINTS, 'nest': [ZC_NEST], 'replicates': ZC_REPS,
               'task_bounds': [[0, ZC_NEST], [ZC_NEST, ZC_POINTS]], 'worker': {'path': 'bin/c8d3_gmp', 'sha256': nc.digest(nc.C8['gmp'])},
               'gamma': str(nc.GAMMA[8].relative_to(nc.ROOT)), 'host': nc.host_info(), 'slurm_job': os.environ.get('SLURM_JOB_ID'),
               'd3_payload': ({'tree': str(d3[0]), 'pin': d3[1]} if d3 else None), 'kernels': zc,
               'use': 'tests/test_pilot_report.py --zero-channel FILE (A-DES-3: pilot_report on real zero-channel tail fields)'}
        Path(tails_out).parent.mkdir(parents=True, exist_ok=True)
        Path(tails_out).write_text(json.dumps(doc, indent=1) + '\n')
        record(test='A-DES-3 zero-channel tails (rows for pilot_report)', file=str(tails_out), sha256=nc.digest(Path(tails_out)),
               kernels=[f'{k["sector"]} L{k["L"]} G{k["graph"]}' for k in zc], rows=sum(len(c['rows']) for k in zc for c in k['campaigns'].values()))


def gamma_norm(L: int, order: int = 8) -> D:
    """The normalization of loop L in the order-8 gamma file (the row labelled order - L), as its decimal token."""
    for line in nc.GAMMA[order].read_text().splitlines():
        tok = line.split()
        if tok and int(tok[0]) == order - L:
            return D(tok[1])
    raise AssertionError(f'{nc.GAMMA[order]}: no row for L = {L}')


def part_f(td, threads, inv):
    """A-KER-6 (f) (Stage 3b): at L8, tail_top[0] * |norm * (3 w_B - w_A)| equals max_abs to 1e-18 relative in every row
    (both are the per-point quantity |v_0 jac| up to the constant factor; max_abs = max |norm (3 w_B - w_A) v_0 jac|,
    src/c8d3_integrate.cpp). norm is the L8 row of inputs/gamma_d3_8.txt and w_A, w_B the G-file header tokens, all
    exact decimals here; the worker's long-double roundings of them (each <= 2^-64 relative, the subtraction's
    amplified by kappa = (3|w_B| + |w_A|)/|3 w_B - w_A| <= 3 at L8) and of the two products stay below 1e-18. Sample:
    the first 4 and the 4 heaviest L8 kernels per sector, 2 replicates x 64 points, order 8, --mp-check on, at
    (rate .8, layout 0, 52-bit net) and (rate .7, layout 2, 60-bit net). Zero-channel L8 rows (3 w_B = w_A; none in
    the inventory) would need max_abs = 0."""
    if '8' not in inv['free']:
        record(test='A-KER-6 (f)', skipped='no L8 kernels in the inventory')
        return
    L = 8
    norm = gamma_norm(L)
    picks = {s: nc.kernels(inv, s, L, False, 4, 4) for s in nc.SECTORS}
    worst, rows_checked, kappa_max, out = D(0), 0, D(0), {}
    with nc.extracted([(s, L, g) for s, ids in picks.items() for g in ids]) as root:
        for s, ids in picks.items():
            head = {}
            for g in ids:
                tok = (root / s / f'L{L}' / f'G{g}.txt').read_text().split(maxsplit=7)
                head[g] = (D(tok[3]), D(tok[4]))
            for rate, layout, bits in (('.8', 0, 52), ('.7', 2, 60)):
                netf = nc.net(td, nc.dim_of(L, layout), bits, 7800 + layout)
                t = nc.write_tasks(td / 'f_tasks', L, nc.task_rows(ids), order=8)
                d, _ = nc.run_worker(nc.C8['gmp'], root / s, nc.GAMMA[8], netf, t, td / 'f.json', SEED, layout, rate, threads, mp_check='on')
                for r in d['rows']:
                    wa, wb = head[r['graph']]
                    c = abs(norm * (3 * wb - wa))
                    m = D(r['max_abs'])
                    if c == 0:
                        if m != 0:
                            raise AssertionError(f'(f) {s} G{r["graph"]}: zero channel with max_abs {m}')
                        continue
                    kappa_max = max(kappa_max, (3 * abs(wb) + abs(wa)) / abs(3 * wb - wa))
                    want = D(r['tail_top'][0]) * c
                    rel = abs(want - m) / m
                    worst = max(worst, rel)
                    rows_checked += 1
                    if rel > D('1e-18'):
                        raise AssertionError(f'(f) {s} L8 G{r["graph"]} rep {r["rep"]} rate {rate}: tail_top[0] x |norm (3 w_B - w_A)| = {want} vs max_abs {m} '
                                             f'(relative {rel:.3e} > 1e-18)')
                out[f'{s}_rate{rate}_layout{layout}'] = len(d['rows'])
    record(test='A-KER-6 (f) tail_top[0] x |norm (3 w_B - w_A)| = max_abs at L8', gate='<= 1e-18 relative in every row', rows=rows_checked,
           max_relative=f'{worst:.3e}', kappa_max=str(kappa_max), norm=str(norm), kernels={s: ids for s, ids in picks.items()}, runs=out)


def part_deep(td, threads):
    out = {}
    netf = nc.net(td, nc.dim_of(3, 0), 52, 3131)
    for b, exe in nc.C8.items():
        for order in (7, 8):
            t = nc.write_tasks(td / 'deep_tasks', 3, nc.task_rows([0]), order=order)
            for mode in ('on', 'stride16'):
                d, _ = nc.run_worker(exe, FIXTURE, nc.GAMMA[order], netf, t, td / 'deep.json', SEED, 0, '.8', threads, mp_check=mode)
                for r in d['rows']:
                    n = r['end'] - r['begin']
                    want = n if mode == 'on' else len([i for i in range(r['begin'], r['end']) if i % 16 == 0])
                    if r['mp'] != n or r['mp_checked'] != want or sum(r['mp_hist']) != want:
                        raise AssertionError(f'A-KER-7 deep {b} order {order} {mode}: mp {r["mp"]}, mp_checked {r["mp_checked"]}, want {want}')
                    if b == 'gmp' and r['mp_alarm'] != want:
                        raise AssertionError(f'A-KER-7 deep gmp order {order} {mode}: mp_alarm {r["mp_alarm"]} != {want} (min log10 {r["mp_min_log10"]})')
                out[f'{b}_order{order}_{mode}'] = {'mp_checked': sum(r['mp_checked'] for r in d['rows']), 'mp_alarm': sum(r['mp_alarm'] for r in d['rows']),
                                                   'min_log10': min((r['mp_min_log10'] for r in d['rows']), key=D)}
    record(test='A-KER-7 deep-cancellation fixture (worker)', results=out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--threads', type=int, default=nc.threads_default())
    ap.add_argument('--parts', default='deep,a,bcd,e,f', help='comma list of deep (A-KER-7 fixture), a, bcd, e, f')
    ap.add_argument('--d3-payload', type=Path, help='a published d=3 payload tree (Stage 1b): adds the new zero-channel L7 kernels to (e)')
    ap.add_argument('--d3-pin', help='sha256 of the tree\'s MANIFEST_d3.json (the A.5 gate record\'s pin)')
    ap.add_argument('--zero-channel-tails', type=Path, help='(e): also integrate every zero-channel kernel in the pilot shape and write its rows here')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    parts = [x for x in a.parts.split(',') if x]
    if set(parts) - {'deep', 'a', 'bcd', 'e', 'f'} or (a.d3_payload is None) != (a.d3_pin is None):
        ap.error('--parts takes deep, a, bcd, e, f; --d3-payload and --d3-pin go together')
    if a.zero_channel_tails and 'e' not in parts:
        ap.error('--zero-channel-tails needs part e')
    nc.require(*nc.C8.values(), nc.INSPECT, NOTAIL)
    inv = nc.inventory()
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='c8d3_classb_') as td:
        td = Path(td)
        if 'deep' in parts:
            part_deep(td, a.threads)
        if 'a' in parts:
            part_a(td, a.threads, inv)
        if 'bcd' in parts:
            part_bcd(td, a.threads, inv)
        if 'e' in parts:
            part_e(td, a.threads, inv, (a.d3_payload, a.d3_pin) if a.d3_payload else None, a.zero_channel_tails)
        if 'f' in parts:
            part_f(td, a.threads, inv)
    res = dict(status='passed', parts=parts, tests=RESULTS, host=nc.host_info(), sha256={str(e): nc.digest(e) for e in (*nc.C8.values(), nc.INSPECT, NOTAIL)},
               wall_seconds=round(time.time() - t0, 1))
    nc.dump(a.output, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'tests'}, indent=2))


if __name__ == '__main__':
    main()
