#!/usr/bin/env python3
"""tools/margin_probe8.py (the L8 margin re-derivation, RECON "Margin re-derivation" (a)-(e)) on the Mac; about a
minute, two worker processes at most.

  * (a) rate recomputation: on real L3-L6 members of the package inputs (every power graph of L3-L5, a sample of free
    ones and the power L6 graphs with double-lift subsets) the recomputed lifted rate line equals the payload's at
    every subset, the raw line equals the package's prepare_inputs.raw_valuations, the double-lift count equals the
    inventory's, and on the smallest graphs both lines equal gen3/g3common.d3_rates (the line-by-line pure-Python port
    of regenerate_rates.cpp); a payload with one rate changed is reported as exactly that one mismatch;
  * the exact-integer engine against margin_probe's own mpmath evaluation of f (Kern.f, mp_lnf at 80 and 160 digits)
    on real members, single- and multi-scale points: |ln f| differences below 1e-10;
  * synthetic forests with analytic exponents (L = 2, E = 4):
      - one term x3 / (S U^(3/2)), U = x0x1 + x2x3 + x0x2: along x0 the exponent is p4/4 = 3/4; the two-scale flag
        {x0} < {x0, x1} has level exponents 3/4 and 3/2;
      - a subtraction: x3/U_A^(3/2) - x3/U_B^(3/2) with equal leading monomials along {x0, x1, x2}: each term 3/4, the
        difference 7/4;
      - a clamped face (raw -3, lifted rate 1/4) on which two terms combine into x0 / U^(3/2): exponent exactly 1/4.
        No-deficit case: with the recomputed rate 1/4 the verdict is "no deficit"; deficit case: with the payload's
        rate there overstated to 1/2 the verdict is "deficit at single-scale face 0x0007 ... a = 0.400/(0.400 - 0.250)
        = 2.67", and campaign b's a = 0.35/0.10 = 3.5;
  * chains: chain_population(6) = 4,620 = the number all_chains enumerates (margin_probe's 228 count); sampled chains
    are ordered set partitions of the anchor into >= 3 blocks, deterministic per seed, and their block-count
    frequencies follow b! S(n, b) (n = 8, loose chi-square);
  * flag_population on margin_probe's graph-228 anchors reproduces its 1,984 enumerated two-scale flags;
  * select on the committed pilot report (benchmarks/symmetry_2026-10-c8/pilot/evidence/pilot_report.json): per sector
    12 top graphs, all PC-confirmed "possible infinite variance" graphs of that sector, in descending share order, and
    the share recomputed here from sigma_cost.csv; 2 controls per sector, unconfirmed, no double-lift subset; no graph
    twice; every graph in the L8 inventory; a second run into the same file refuses (1) and leaves it unchanged;
  * probe end to end (two workers) on the real power L5 graph 27 (one double-lift subset): (a) no mismatch, (b) every
    clamped subset at or above its table rate, verdict "no deficit", the mpmath check agrees; the same member with one
    clamped rate overstated, in a synthetic inputs directory read through tools/members.py, gives (a) one mismatch and
    the verdict "deficit at single-scale face ..." with a = r/(r - m) from the measured m; an existing result refuses
    (1) and --skip-existing passes; report renders both directories.
Usage: python3 -B tests/margin_probe8_test.py"""
from __future__ import annotations
import collections, hashlib, json, math, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'gen3')]
import margin_probe8 as mp8  # noqa: E402  (first: it sets one BLAS thread per process before numpy loads)
import numpy as np  # noqa: E402
import members  # noqa: E402

RESULTS = []
TOOL = ROOT / 'tools/margin_probe8.py'
PILOT = ROOT / 'benchmarks/symmetry_2026-10-c8/pilot/evidence'


def ok(name):
    RESULTS.append(name)
    print('PASS', name, flush=True)


def run(*args, env=None):
    return subprocess.run([sys.executable, '-B', str(TOOL), *map(str, args)], capture_output=True, text=True,
                          env=dict(os.environ, OPENBLAS_NUM_THREADS='1', **(env or {})))


def member(sector, L, gid, inputs=None) -> bytes:
    with members.extracted([(sector, L, gid)], inputs) as root:
        return (root / sector / f'L{L}' / f'G{gid}.txt').read_bytes()


def gfile(L, masks, terms, rates) -> bytes:
    """A C7D3GRAPH1 G-file (the format of regenerate_rates.cpp's output)."""
    lines = [f'C7D3GRAPH1 {L} 17 0.1875 0.03125 {len(masks)} {len(terms)}', ' '.join(map(str, masks)) + ' ']
    for ids, co in terms:
        lines.append(' '.join(map(str, [len(ids), *ids, *co])))
    lines += [str(len(rates)), ' '.join(f'{r:g}' for r in rates)]
    return ('\n'.join(lines) + '\n').encode()


def synthetic(masks, terms, L=2, override=None):
    """A synthetic Graph whose payload rate line is the recomputed one (with `override` {subset: rate} applied)."""
    E = 2 * L
    g0 = mp8.Graph(gfile(L, masks, terms, [0.0] * (1 << E)), 'power', 'synthetic')
    raw, pos = mp8.rate_line(g0)
    tab = pos * 0.25
    tab[0] = tab[-1] = 0.0
    for s, v in (override or {}).items():
        tab[s] = v
    return mp8.Graph(gfile(L, masks, terms, list(tab)), 'power', 'synthetic'), raw


def test_rate_lines():
    inv = members.inventory()
    import g3common
    picks = [('power', L, r['id']) for L in (3, 4, 5) for r in inv['power'][str(L)]]
    picks += [('free', L, r['id']) for L in (3, 4, 5) for r in inv['free'][str(L)][:6]]
    picks += [('power', 6, r['id']) for r in inv['power']['6'] if r['double_lift'] > 0]
    with members.extracted(picks) as root:
        n_port = 0
        for s, L, gid in picks:
            data = (root / s / f'L{L}' / f'G{gid}.txt').read_bytes()
            g = mp8.Graph(data, s, f'{s}:{L}:{gid}')
            row = next(r for r in inv[s][str(L)] if r['id'] == gid)
            res, raw, pos = mp8.check_rate_line(g, row['double_lift'])
            assert res['mismatches'] == 0 and res['package_raw_agrees'] and res['inventory_double_lift_agrees'], (s, L, gid, res)
            if L <= 4:
                gf = g3common.parse_gfile(data, 'x')
                port_pos, port_raw = g3common.d3_rates(gf)
                ALL = (1 << g.E) - 1
                assert list(pos[1:ALL]) == port_pos[1:ALL] and list(raw[1:ALL]) == port_raw[1:ALL], (s, L, gid)
                n_port += 1
        # one changed rate is exactly one mismatch
        s, L, gid = 'power', 6, next(r['id'] for r in inv['power']['6'] if r['double_lift'] > 0)
        data = (root / s / f'L{L}' / f'G{gid}.txt').read_bytes()
        g = mp8.Graph(data, s, 'x')
        raw, _ = mp8.rate_line(g)
        S = int(np.nonzero(raw[1:-1] <= 0)[0][0] + 1)
        g.rates[S] += 0.25
        res, _, _ = mp8.check_rate_line(g)
        assert res['mismatches'] == 1 and res['mismatch_examples'][0]['subset'] == S, res
    ok(f'(a) rate line: {len(picks)} real L3-L6 members reproduce the payload line, the package raw line and the inventory '
       f'double-lift count; {n_port} also equal g3common.d3_rates; one changed rate is exactly one mismatch')


def test_engine_vs_mpmath():
    worst = 0.0
    n = 0
    for s, L, gid in (('power', 5, 27), ('power', 6, 421), ('free', 5, 1)):
        g = mp8.Graph(member(s, L, gid), s, 'x')
        F = mp8.Forest(g, 3)
        raw, _ = mp8.rate_line(g)
        ALL = (1 << g.E) - 1
        cl = [int(x) for x in np.nonzero(raw[1:ALL] <= 0)[0] + 1]
        probes = [((cl[0],), (10,)), ((cl[-1],), (14,)), ((cl[0], ALL ^ (1 << (g.E - 1))), (13, 11)),
                  ((1, 3, 7, 15), (8, 4, 4, 6))]
        for sets, a in probes:
            if not all(x & y == x for x, y in zip(sets, sets[1:])):
                continue
            fi = F.lnf(F.prepare(sets), a)[0]
            m1, m2 = mp8.mp_lnf(g, F.y, sets, a, 80), mp8.mp_lnf(g, F.y, sets, a, 160)
            worst = max(worst, abs(fi - m2))
            assert abs(fi - m2) < 1e-10 and abs(m1 - m2) < 1e-10, (s, L, gid, sets, a, fi, m1, m2)
            n += 1
    ok(f'engine: ln|f| of the exact-integer engine equals margin_probe\'s mpmath Kern.f (80 and 160 digits) at {n} '
       f'single- and multi-scale points of real L5/L6 members (max |diff| {worst:.1e})')


def test_synthetic():
    # one term: U = x0x1 + x0x2 + x2x3 (masks 3, 5, 12), N = x3
    g, raw = synthetic([3, 5, 12], [([0, 1, 2], [0, 0, 0, 1])])
    F = mp8.Forest(g, 3)
    e = F.level(F.prepare([1]), 0, 10, 14, 0)[0]
    assert abs(e - 0.75) < 1e-6 and g.rates[1] == 0.75, (e, g.rates[1])
    prep = F.prepare([1, 3])
    e0, e1 = F.level(prep, 0, 9, 13, 11)[0], F.level(prep, 1, 9, 13, 11)[0]
    assert abs(e0 - 0.75) < 1e-6 and abs(e1 - 1.5) < 1e-6, (e0, e1)
    # a subtraction: x3/U_A^(3/2) - x3/U_B^(3/2), U_A = x0x3 + x0x1, U_B = x0x3 + x0x2 (masks 3, 5, 9)
    for terms, want in ((([0, 2], [0, 0, 0, 1]),), 0.75), ((([0, 2], [0, 0, 0, 1]), ([1, 2], [0, 0, 0, -1])), 1.75):
        g, raw = synthetic([3, 5, 9], list(terms))
        F = mp8.Forest(g, 3)
        e = F.level(F.prepare([7]), 0, 10, 14, 0)[0]
        assert abs(e - want) < 1e-6, (terms, e, want)
    # a clamped face: U = x0x1 + x1x2 (masks 3, 6), terms x3/U^(3/2) and (x0 - x3)/U^(3/2): raw -3 at {x0,x1,x2},
    # lifted 1/4; their sum x0/U^(3/2) has exponent 3 - 3/4 - 3 + 1 = 1/4
    terms = [([0, 1], [0, 0, 0, 1]), ([0, 1], [1, 0, 0, -1])]
    g, raw = synthetic([3, 6], terms)
    assert raw[7] == -3 and g.rates[7] == 0.25, (raw[7], g.rates[7])
    F = mp8.Forest(g, 3)
    m = F.level(F.prepare([7]), 0, 10, 14, 0)[0]
    assert abs(m - 0.25) < 1e-6, m
    v = mp8.verdict([('single', (7,), 0, m, float(g.rates[7]))], 0.02)
    assert v['status'] == 'no_deficit' and v['text'] == 'no deficit found within the probed flags (finite-variance, peaked)', v
    g2, _ = synthetic([3, 6], terms, override={7: 0.5})
    res, _, _ = mp8.check_rate_line(g2, package_raw=False)
    assert res['mismatches'] == 1 and res['mismatch_examples'][0]['subset'] == 7, res
    v = mp8.verdict([('single', (7,), 0, m, float(g2.rates[7]))], 0.02)
    wa = v['campaigns']['a']['worst'][0]
    wb = v['campaigns']['b']['worst'][0]
    assert v['status'] == 'deficit' and v['text'].startswith('deficit at single-scale face 0x0007 (edges [0, 1, 2]) (level exponent 0.250 '
                                                              '< proposal rate 0.400'), v['text']
    assert 'a = 0.400/(0.400 - 0.250) = 2.67' in v['text'] and 'infinite variance' not in v['text'], v['text']
    assert abs(wa['tail_index'] - 0.4 / 0.15) < 1e-4 and abs(wb['tail_index'] - 3.5) < 1e-4, (wa, wb)
    # a level below half its proposal rate: infinite variance (r >= 2m)
    v = mp8.verdict([('two', (1, 3), 1, 0.15, 1.0)], 0.02)
    assert v['status'] == 'deficit' and 'infinite variance (r >= 2m)' in v['text'] and 'level 2 = 0x0003' in v['text'], v
    ok('synthetic forests: exponents 3/4 (one term), 3/4 and 3/2 (two-scale levels), 3/4 -> 7/4 (subtraction), 1/4 on a '
       'clamped face (raw -3); no deficit at the recomputed rate 1/4, "deficit at single-scale face 0x0007 ... a = 2.67" '
       '(campaign b 3.5) at an overstated rate 1/2, which (a) reports as the one mismatch; r >= 2m is infinite variance')


def test_chains_flags():
    el = [0, 2, 3, 5, 8, 9]
    allc = list(mp8.all_chains(el))
    assert mp8.chain_population(6) == 4620 == len(allc) == len({mp8.chain_sets(p) for p in allc})
    assert all(len(p) >= 3 and sorted(e for b in p for e in b) == el for p in allc)
    rng1, rng2 = np.random.default_rng(5), np.random.default_rng(5)
    a1 = [mp8.sample_chain(list(range(8)), rng1) for _ in range(3000)]
    a2 = [mp8.sample_chain(list(range(8)), rng2) for _ in range(3000)]
    assert a1 == a2 and all(len(p) >= 3 and sorted(e for b in p for e in b) == list(range(8)) for p in a1)
    cnt = collections.Counter(len(p) for p in a1)
    w = {b: math.factorial(b) * mp8.stirling2(8, b) for b in range(3, 9)}
    tot = sum(w.values())
    chi2 = sum((cnt[b] - 3000 * w[b] / tot) ** 2 / (3000 * w[b] / tot) for b in w)
    assert chi2 < 30, (chi2, cnt)
    # margin_probe's graph-228 anchors (E = 14): 1,984 enumerated two-scale flags
    anchors = [0x3f00, 0x3f18, 0x3f44, 0x3f5c]
    pop, enum, per = mp8.flag_population(anchors, 14)
    assert enum == 1984 and len(pop) < enum and all(v in anchors for v in pop.values()), (enum, len(pop))
    ok(f'chains and flags: chain_population(6) = 4,620 = all_chains (margin_probe\'s 228 count); 3,000 sampled 8-edge '
       f'chains are valid, deterministic and follow b! S(8, b) (chi2 {chi2:.1f}, 5 dof); graph 228\'s anchors give '
       f'margin_probe\'s 1,984 enumerated flags ({len(pop)} unique)')


def test_select(td: Path):
    out = td / 'sel.json'
    cp = run('select', '--out', out)
    assert cp.returncode == 0, cp.stderr[-2000:]
    sel = json.loads(out.read_text())
    rep = json.loads((PILOT / 'pilot_report.json').read_text())
    piv = {(x['sector'], x['graph']) for x in rep['action2_confirm']['possible_infinite_variance']}
    conf = {(x['sector'], x['graph']): x for x in rep['action2_confirm']['confirmations']}
    inv = json.loads((ROOT / 'inputs/inventory.json').read_text())
    inv8 = {s: {r['id']: r for r in inv[s]['8']} for s in ('free', 'power')}
    # the share recomputed here from sigma_cost.csv (PF sigma, upgraded by sqrt(V_ratio) where action 3 used 32,768)
    import csv
    sig = {}
    with open(PILOT / 'sigma_cost.csv', newline='') as f:
        for r in csv.DictReader(f):
            if r['L'] == '8':
                sig[(r['campaign'], r['sector'], int(r['graph']))] = (float(r['sigma']), float(r['cost_per_point']))
    sup = {(x['sector'], x['graph']): x.get('supporting') or {} for x in
           rep['action2_confirm']['confirmations'] + rep['action2b']['p1c']['confirmations'] if x.get('supporting')}
    share = collections.defaultdict(float)
    for s in ('free', 'power'):
        src = set(rep['action3_hold'][s]['sigma_from_32768'])
        val = {}
        for k in sig:
            if k[1] != s:
                continue
            v = sig[k][0]
            vr = (sup.get((s, k[2])) or {}).get(k[0], {}).get('V_ratio')
            if f'{k[0]}:{k[2]}' in src and vr and vr > 1:
                v *= math.sqrt(vr)
            val[k] = v * math.sqrt(sig[k][1])
        tot = sum(val.values())
        for k, v in val.items():
            share[(s, k[2])] += v / tot
    seen = set()
    for s in ('free', 'power'):
        top = [r for r in sel['graphs'] if r['sector'] == s and r['role'] == 'top']
        ctl = [r for r in sel['graphs'] if r['sector'] == s and r['role'] == 'control']
        assert len(top) == 12 and len(ctl) == 2, (s, len(top), len(ctl))
        want = sorted([g for (ss, g) in piv if ss == s], key=lambda g: (-share[(s, g)], g))[:12]
        assert [r['id'] for r in top] == want, (s, [r['id'] for r in top], want)
        assert all(abs(r['share'] - share[(s, r['id'])]) < 1e-12 and r['L'] == 8 and r['possible_infinite_variance']
                   and r['why'] and r['xi_a'] == conf[(s, r['id'])]['cross_campaign_shift']['xi_a'] for r in top)
        for r in ctl:
            x = conf[(s, r['id'])]
            assert not x['confirmed'] and x['xi_mean_32768'] <= 0.44 and inv8[s][r['id']]['double_lift'] == 0, r
        for r in top + ctl:
            assert r['id'] in inv8[s] and (s, r['id']) not in seen
            seen.add((s, r['id']))
    assert sel['schema'] == mp8.SCHEMA_SELECTION and sel['sources']['pilot_report']['sha256'] == \
        hashlib.sha256((PILOT / 'pilot_report.json').read_bytes()).hexdigest()
    before = out.read_bytes()
    cp = run('select', '--out', out)
    assert cp.returncode == 1 and 'never overwritten' in cp.stderr and out.read_bytes() == before, cp.stderr
    ok('select on the committed pilot report: 12 top PC-confirmed graphs per sector in descending share order (share '
       'recomputed from sigma_cost.csv), 2 unconfirmed controls without double-lift subsets, no duplicate, all in the L8 '
       'inventory, the report\'s sha256 recorded; a second run refuses (1) and leaves the file unchanged')


def synthetic_inputs(td: Path, sector: str, L: int, gid: int, data: bytes) -> Path:
    """An inputs directory holding one member (manifest -> inventory -> member), read through tools/members.py."""
    d = td / f'inputs_{gid}'
    (d / 'packs').mkdir(parents=True)
    (d / 'packs' / f'{sector}_L{L}.pack').write_bytes(data)
    row = dict(next(r for r in json.loads((ROOT / 'inputs/inventory.json').read_text())[sector][str(L)] if r['id'] == gid))
    row.update(offset=0, length=len(data), sha256=hashlib.sha256(data).hexdigest())
    inv = json.dumps({'inspect_complete': False, sector: {str(L): [row]}}).encode()
    (d / 'inventory.json').write_bytes(inv)
    (d / 'manifest.json').write_text(json.dumps({'sha256': {'inventory.json': hashlib.sha256(inv).hexdigest()}}))
    return d


def test_probe(td: Path):
    small = ['--workers', '2', '--max-flags', '200', '--max-chains', '150', '--mp-check', '3']
    o1 = td / 'p27'
    cp = run('probe', '--graphs', 'power:5:27', '--out', o1, *small)
    assert cp.returncode == 0, cp.stderr[-3000:]
    d = json.loads((o1 / 'power_L5_G27.json').read_text())
    a, b, c = d['a_rate_line'], d['b_single_scale'], d['c_multi_scale']
    assert d['schema'] == mp8.SCHEMA_GRAPH and a['mismatches'] == 0 and a['package_raw_agrees'] and a['double_lift'] == 1
    assert b['resolved'] == b['clamped'] > 0 and b['compat']['below_table'] == 0 and not b['below_table_rate'], b['compat']
    assert d['verdict']['status'] == 'no_deficit' and d['mp_cross_check']['agrees'], (d['verdict'], d['mp_cross_check'])
    assert c['two']['levels'] == 2 * c['plan']['two_scale']['probed'] > 0 and c['chain']['levels'] > 0
    assert len(b['double_lift']) == 1 and (o1 / 'probe_run.json').exists()
    cp = run('probe', '--graphs', 'power:5:27', '--out', o1, *small)
    assert cp.returncode == 1 and 'never overwritten' in cp.stderr, cp.stderr
    cp = run('probe', '--graphs', 'power:5:27', '--out', o1, '--skip-existing', *small)
    assert cp.returncode == 0 and 'skipped' in cp.stderr, cp.stderr
    # the deficit case: one clamped rate overstated in the payload (a synthetic inputs directory)
    data = member('power', 5, 27)
    g = mp8.Graph(data, 'power', 'x')
    rows = [r for r in b['per_subset'] if r[1] > 0]
    S, al, m = int(rows[0][0], 16), rows[0][1], min(x for x in rows[0][2:4] if x is not None)
    lines = data[:-1].split(b'\n')
    rates = lines[3 + g.T].split()
    rates[S] = b'2'
    lines[3 + g.T] = b' '.join(rates)
    bad = b'\n'.join(lines) + b'\n'
    inp = synthetic_inputs(td, 'power', 5, 27, bad)
    o2 = td / 'p27bad'
    cp = run('probe', '--graphs', 'power:5:27', '--out', o2, '--inputs', inp, *small)
    assert cp.returncode == 0, cp.stderr[-3000:]
    d2 = json.loads((o2 / 'power_L5_G27.json').read_text())
    r = 1.6
    assert d2['a_rate_line']['mismatches'] == 1 and d2['a_rate_line']['mismatch_examples'][0]['subset'] == S
    assert d2['verdict']['status'] == 'deficit' and d2['verdict']['text'].startswith(f'deficit at single-scale face {S:#06x}'), d2['verdict']['text']
    w = d2['verdict']['campaigns']['a']['worst'][0]
    assert abs(w['proposal_rate'] - r) < 1e-12 and abs(w['tail_index'] - r / (r - w['exponent'])) < 1e-9 and abs(w['exponent'] - m) < 1e-5, w
    rep = td / 'rep.md'
    cp = run('report', o1, o2, '--out', rep, '--json', td / 'rep.json')
    assert cp.returncode == 0 and '**Deficits: 1 of 2 graphs.**' in rep.read_text(), (cp.stderr, rep.read_text()[:2000])
    ok(f'probe end to end (2 workers) on power L5 graph 27: no mismatch, {b["clamped"]} clamped subsets at or above the '
       f'table rate, {c["plan"]["two_scale"]["probed"]} flags and {sum(p["probed"] for p in c["plan"]["chains"])} chains, '
       f'"no deficit", mpmath check agrees; with rate {al:g} at {S:#06x} overstated to 2 in a synthetic inputs directory: one '
       f'mismatch and "deficit at single-scale face {S:#06x}" with a = 1.6/(1.6 - {w["exponent"]:.3f}); an existing result '
       'refuses, --skip-existing passes; the report counts 1 deficit of 2')


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix='c8d3_margin8_'))
    try:
        test_rate_lines()
        test_engine_vs_mpmath()
        test_synthetic()
        test_chains_flags()
        test_select(td)
        test_probe(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print(json.dumps({'status': 'passed', 'tests': len(RESULTS)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
