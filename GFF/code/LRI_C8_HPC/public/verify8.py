#!/usr/bin/env python3
"""Check the C8(1) replay against the published records and every number the note and the report quote.

Run after replay8.py. Writes a PASS/FAIL table to stdout and to WORK/verify_c8.tsv; exits 1 on any FAIL.

Sections
  A  replay identity: the three replayed combinations against the published files (bitwise, else numeric 1e-12 rel)
  B  quoted numbers of the final result (note at fa71533: abstract, Section 1 table, Section 30; REPORT.md)
  C  the two earlier quoted results (K = 4, A1 interim K = 9)
  D  inputs: nine-vertex inventory counts, exact zeros, affine-map checks, the loop-five degree sequence
  E  cited checks: pilot sampling hazard (the two 64-point pilot campaigns and the 4096-point repetition), kernel
     validation records, cost model
Tolerances: a quoted number passes when the recomputed value rounds to it (|x - q| <= half a unit of the last quoted
digit, stated per row); full-precision values (Section 1 table) pass at 1e-6 absolute (1e-13 relative), because the
last digits depend on the floating-point summation order of the platform's numpy/BLAS.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
ROWS = []


def row(sec, name, where, quoted, value, tol, ok=None):
    if ok is None:
        ok = value is not None and abs(float(value) - float(quoted)) <= tol
    ROWS.append((sec, name, where, str(quoted), 'n/a' if value is None else (f'{value:.10g}' if isinstance(value, float) else str(value)),
                 '' if tol is None else f'{tol:g}', 'PASS' if ok else 'FAIL'))


def info(sec, name, where, text):
    ROWS.append((sec, name, where, text, '', '', 'INFO'))


def skip(sec, name, where, why):
    ROWS.append((sec, name, where, why, '', '', 'SKIP'))


def load(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def deep_close(a, b, path='', rtol=1e-12, atol=1e-9):
    """First difference between two JSON values (floats compared with tolerance), or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys(): return f'{path}: keys differ'
        for k in a:
            d = deep_close(a[k], b[k], f'{path}/{k}', rtol, atol)
            if d: return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): return f'{path}: lengths differ'
        for i, (x, y) in enumerate(zip(a, b)):
            d = deep_close(x, y, f'{path}[{i}]', rtol, atol)
            if d: return d
        return None
    if isinstance(a, float) or isinstance(b, float):
        if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)): return f'{path}: types differ'
        return None if abs(a - b) <= atol + rtol * max(abs(a), abs(b)) else f'{path}: {a!r} != {b!r}'
    return None if a == b else f'{path}: {a!r} != {b!r}'


def diffs(a, b, acc=None):
    """(largest relative difference over float fields with magnitude >= 1e-6, largest absolute difference below it)."""
    acc = acc if acc is not None else [0.0, 0.0]
    if isinstance(a, dict):
        for k in a: diffs(a[k], b[k], acc)
    elif isinstance(a, list):
        for x, y in zip(a, b): diffs(x, y, acc)
    elif isinstance(a, float) and isinstance(b, (int, float)) and not isinstance(b, bool) and a != b:
        m = max(abs(a), abs(b))
        if m >= 1e-6: acc[0] = max(acc[0], abs(a - b) / m)
        else: acc[1] = max(acc[1], abs(a - b))
    return acc


def identity(sec, name, replayed: Path, published: Path):
    if not replayed.is_file():
        row(sec, name, str(published.name), 'replayed file', None, None, ok=False); return None
    if replayed.read_bytes() == published.read_bytes():
        ROWS.append((sec, name, '/'.join(published.parts[-3:]), 'sha256 ' + sha(published)[:16], 'bitwise identical', 'bytes', 'PASS'))
    else:
        d = deep_close(load(replayed), load(published))
        ra, pa = load(replayed), load(published)
        ROWS.append((sec, name, '/'.join(published.parts[-3:]), 'sha256 ' + sha(published)[:16],
                     'numeric match, max rel diff {:.1e} (abs {:.1e} below 1e-6)'.format(*diffs(ra, pa)) if d is None else d[:120],
                     'rel 1e-12', 'PASS' if d is None else 'FAIL'))
    return load(replayed)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', type=Path, default=Path('.work'))
    ap.add_argument('--data', type=Path, default=Path('../../data/C8_1'))
    ap.add_argument('--results', type=Path, default=Path('../../results/C8_1'))
    ap.add_argument('--c7-final', type=Path, default=Path('../../results/C7_1/C7_final.json'),
                    help='published C7(1) record (for the 16372.8 of the pilot check); SKIP if absent')
    a = ap.parse_args()
    W = a.work.resolve(); T = W / 'c8_hpc'; R = a.results.resolve(); D = a.data.resolve()

    # ---------------------------------------------------------------- A: identity with the published records
    k4 = identity('A', 'K=4 C8_final.json', T / 'results/C8_final/C8_final.json', R / '2026-10_expanse/C8_final.json')
    identity('A', 'K=4 combined_assembly.json', T / 'results/C8_final/combined_assembly.json', R / '2026-10_expanse/combined_assembly.json')
    a1 = identity('A', 'A1 C8_interim.json', T / 'results/C8_A1_close/combination/C8_interim.json', R / '2026-10_ext1/C8_A1_close/combination/C8_interim.json')
    identity('A', 'A1 combined_assembly.json', T / 'results/C8_A1_close/combination/combined_assembly.json', R / '2026-10_ext1/C8_A1_close/combination/combined_assembly.json')
    f = identity('A', 'K=14 C8_final.json', T / 'results/C8_final_A3/C8_final.json', R / '2026-10_ext1/C8_final_A3/C8_final.json')
    identity('A', 'K=14 combined_assembly.json', T / 'results/C8_final_A3/combined_assembly.json', R / '2026-10_ext1/C8_final_A3/combined_assembly.json')
    row('A', 'K=14 published sha256 (REPORT, note comment)', 'REPORT.md Files', '115d614f', None, None,
        ok=sha(R / '2026-10_ext1/C8_final_A3/C8_final.json').startswith('115d614f'))
    if f is None:
        f = load(R / '2026-10_ext1/C8_final_A3/C8_final.json'); info('A', 'fallback', '', 'sections B-E use the PUBLISHED K=14 record (replay missing)')

    # ---------------------------------------------------------------- B: quoted numbers of the final result
    C8, SE = f['C8_full'], f['sampling_se']; cand = f['allowance']['candidates']
    row('B', 'estimator (Sec 1 table)', 'Sec 1', 8059766.723129955, C8, 1e-6)
    row('B', 'sampling SE (Sec 1 table)', 'Sec 1', 4209.576151, SE, 1e-6)
    row('B', 'C8(1) rounded', 'Sec 30.1 box', 8059767, C8, 0.5)
    row('B', 'allowance (pre-registered rule)', 'Sec 30.1 box, abstract', 17000, f['allowance']['headline_2sf'], 0)
    row('B', 'C8 in units of 1e6, 3 decimals', 'abstract', 8.060, C8 / 1e6, 5e-4)
    row('B', 'SE rounded', 'Sec 30.1', 4210, SE, 5)
    row('B', 'bootstrap SE', 'Sec 30.1', 4140, f['bootstrap_se'], 5)
    pb = f['batches']['per_batch']; vals = [x['C8_full'] for x in pb]; ses = [x['sampling_se'] for x in pb]
    row('B', 'number of batches', 'Sec 30.1', 14, f['batches']['count'], 0)
    row('B', 'smallest batch value', 'Sec 30.1', 8041935, min(vals), 0.5)
    row('B', 'largest batch value', 'Sec 30.1', 8089624, max(vals), 0.5)
    row('B', 'smallest batch SE', 'Sec 30.1', 15090, min(ses), 0.5)
    row('B', 'largest batch SE', 'Sec 30.1', 16343, max(ses), 0.5)
    row('B', 'inter-batch chi2', 'Sec 30.1', 8.49, f['batches']['chi2_about_combined'], 0.005)
    row('B', 'chi2 degrees of freedom', 'Sec 30.1', 13, f['batches']['dof'], 0)
    row('B', 'four-SE candidate (largest)', 'Sec 30.1', 16838.3, cand['4SE'], 0.05,
        ok=abs(cand['4SE'] - 16838.3) <= 0.05 and max(cand, key=cand.get) == '4SE')
    row('B', 'half-split candidate', 'REPORT', 4316, cand['half_split_shift'], 0.5)
    row('B', '2|R8|+4SE_R8 candidate', 'REPORT', 524, cand['refine8'], 0.5)
    row('B', '2|R9|+4SE_R9 candidate', 'REPORT', 499, cand['refine9'], 0.5)
    row('B', '2 x loop-5 degree step candidate', 'REPORT', 5.5, cand['L5_degree_step'], 0.05)
    c7 = f['lower_order_checks'][-1]
    row('B', 'ratio C8/C7', 'Sec 30.1', -25.0, C8 / c7['reference'], 0.05)
    row('B', 'final, closed, nothing omitted', 'REPORT checks', 'True', None, None,
        ok=f['final'] is True and f['extension']['closed'] is True and f['extension']['omitted_incomplete'] == [] and f['flags'] == [])
    row('B', 'loop-5 contribution at degree 14', 'Sec 30.2', -1297392.1, f['loop5_exact']['contribution'][8], 0.05)
    row('B', 'loop-5 last degree step', 'Sec 30.2', 2.8, f['loop5_exact']['last_degree_step'][8], 0.05)
    comp = [('free (power-free sector)', f['free_level'], 7879086.8, 790.7)]
    for lev, q, qs in (('coarse', 316544.2, 1690.3), ('refine3', -364981.8, 2887.4), ('refine5', -4590.2, 2346.3),
                       ('refine6', -26.5, 528.4), ('refine7', -202.2, 321.0), ('refine8', 26.3, 117.8)):
        comp.append((lev, f['power_levels'][lev], q, qs))
    comp.append(('check refine9 (not added)', f['check_levels']['refine9'], -113.3, 68.1))
    for name, lv, q, qs in comp:
        row('B', f'composition {name}', 'Sec 30.4 table', q, lv['mean'][8], 0.05)
        row('B', f'composition {name} SE', 'Sec 30.4 table', qs, lv['sampling_se'][8], 0.05)
    res = {x['degree']: x['mean'][8] for x in f['resolution_sequence']}
    for N, q in ((1, 8429541), (3, 8064559), (5, 8059969), (6, 8059943), (7, 8059740), (8, 8059767)):
        row('B', f'resolution sequence degree {N}', 'REPORT', q, res[N], 0.5)
    unc = f['raw_uncontrolled']
    row('B', 'uncontrolled estimator', 'Sec 30.4', 8048689, unc['C8'], 0.5)
    row('B', 'uncontrolled SE', 'Sec 30.4', 23730, unc['sampling_se'], 0.5)
    corr = C8 - unc['C8']; corr_se = math.sqrt(sum(v['sampling_se'][8] ** 2 for v in f['zero_pole_control'].values()))
    row('B', 'control correction (controlled - uncontrolled)', 'Sec 30.4', 11078, corr, 0.5)
    row('B', 'control correction SE (per-loop terms)', 'Sec 30.4', 24734, corr_se, 0.5)
    row('B', 'SE reduction by the controls', 'REPORT', 5.6, unc['sampling_se'] / SE, 0.05)
    for L, q, qs in (('6', -663, 316), ('7', 2506, 4037), ('8', -12920, 24400)):
        v = f['zero_pole_control'][L]
        row('B', f'control term L{L} (raw - controlled)', 'REPORT / review', q, v['mean'][8], 0.5)
        row('B', f'control term L{L} SE', 'REPORT / review', qs, v['sampling_se'][8], 0.5)
    z = [p['z_score'] for p in f['spurious_pole_checks']]
    row('B', 'pole columns', 'Sec 30.4', 30, len(z), 0)
    row('B', 'max |z| of the pole columns', 'Sec 30.4', 2.18, max(map(abs, z)), 0.005)
    row('B', 'pole columns with |z| > 2', 'Sec 30.4 (two pairs)', 4, sum(abs(x) > 2 for x in z), 0)
    pairs = sorted((p['L'], p['column']) for p in f['spurious_pole_checks'] if abs(p['z_score']) > 2)
    row('B', 'the two pairs: L7 cols 12/13, L8 cols 1/9', 'REPORT', str([(7, 12), (7, 13), (8, 1), (8, 9)]), str(pairs), None,
        ok=pairs == [(7, 12), (7, 13), (8, 1), (8, 9)])
    row('B', 'sum of z^2 (descriptive)', 'Sec 30.4', 39.8, sum(x * x for x in z), 0.05)
    row('B', 'half split 1', 'Sec 30.4', 8055451, f['half_splits'][0][8], 0.5)
    row('B', 'half split 2', 'Sec 30.4', 8064082, f['half_splits'][1][8], 0.5)
    lo = {c['n']: c for c in f['lower_order_checks']}
    row('B', 'C3 - exact', 'Sec 30.2', -1.3e-12, lo[3]['difference'], 5e-14)
    row('B', 'C4 - exact', 'Sec 30.2', 1.1e-9, lo[4]['difference'], 5e-11)
    row('B', 'C5 (deterministic)', 'Sec 30.4 table', -731.140052, lo[5]['value'], 5e-7)
    row('B', 'C5 - exact', 'Sec 30.4 table', -5.8e-4, lo[5]['difference'], 5e-6)
    row('B', 'C6 estimate', 'Sec 30.4 table', 14332.8222, lo[6]['value'], 5e-5)
    row('B', 'C6 SE', 'Sec 30.4 table', 2.52, lo[6]['sampling_se'], 0.005)
    row('B', 'C6 pull', 'Sec 30.4 table', 0.45, lo[6]['difference_over_sampling_se'], 0.005)
    row('B', 'C7 estimate', 'Sec 30.4 table', -322495.6, lo[7]['value'], 0.05)
    row('B', 'C7 SE', 'Sec 30.4 table', 74.4, lo[7]['sampling_se'], 0.05)
    row('B', 'C7 pull (combined SE)', 'Sec 30.4 table', 0.72, lo[7]['difference_over_combined_se'], 0.005)
    tw = (-322524, 38)  # truncation-aware C7(1) of Section 29 (eq. c7f:truncationAware), as quoted there
    t1 = -322549.88881298894 + 10.40 + 15.59; s1 = math.sqrt(10.087912951713953 ** 2 + 0.43 ** 2 + 15.59 ** 2)  # Sec 29: estimate + step7 + tail; 1 sigma (+-38 is twice it)
    row('B', 'C7 vs truncation-aware C7 (combined standard errors)', 'Sec 30.4 (public edition 97dd353)', 0.4,
        (lo[7]['value'] - t1) / math.hypot(lo[7]['sampling_se'], s1), 0.05)
    amd = [x for x in pb if x['label'] in ('b1', 'b2', 'b3', 'b4', 'b12', 'b13', 'b14')]
    intel = [x for x in pb if x['label'] in ('b5', 'b6', 'b7', 'b8', 'b9', 'b10', 'b11')]

    def ivw(xs):
        w = [1 / x['sampling_se'] ** 2 for x in xs]; return sum(wi * x['C8_full'] for wi, x in zip(w, xs)) / sum(w), 1 / math.sqrt(sum(w))
    (ma, sa), (mi, si) = ivw(amd), ivw(intel)
    row('B', 'vendor split: AMD group (b1-b4, b12-b14)', 'REPORT (post hoc)', 8063282, ma, 0.5)
    row('B', 'vendor split: AMD SE', 'REPORT', 5975, sa, 0.5)
    row('B', 'vendor split: Intel group (b5-b11)', 'REPORT (post hoc)', 8056245, mi, 0.5)
    row('B', 'vendor split: Intel SE', 'REPORT', 5918, si, 0.5)
    row('B', 'vendor split: difference', 'Sec 30.3', 7037, ma - mi, 0.5)
    row('B', 'vendor split: difference SE', 'Sec 30.3', 8410, math.hypot(sa, si), 0.5)
    ht = (8.0655e6, 5000)  # external: HT extrapolation (HT package), REPORT comparison only
    row('B', 'HT comparison: C8 - HT (external HT input 8.0655(50)e6)', 'REPORT', -5700, C8 - ht[0], 50)
    row('B', 'HT comparison: pull', 'REPORT', -0.88, (C8 - ht[0]) / math.hypot(ht[1], SE), 0.005)
    cov = f['coverage']
    row('B', 'coverage guard: active L8 classes', 'REPORT checks', 21143, cov['8']['active'], 0)

    # ---------------------------------------------------------------- C: the two earlier quoted results
    for tag, r, q, qs, qa, k, where in (('K=4', k4, 8066723, 8015, 33000, 4, 'Sec 30.3; REPORT'), ('A1 (K=9)', a1, 8061480, 5300, 22000, 9, 'Sec 30.3; REPORT')):
        if r is None: row('C', f'{tag} replay', where, 'replayed record', None, None, ok=False); continue
        row('C', f'{tag} estimator', where, q, r['C8_full'], 0.5)
        row('C', f'{tag} SE', where, qs, r['sampling_se'], 0.5 if tag == 'K=4' else 50)
        row('C', f'{tag} allowance', where, qa, r['allowance']['headline_2sf'], 0)
        row('C', f'{tag} batches', where, k, r['batches']['count'], 0)
    if a1 is not None:
        row('C', 'A1 is an interim (not final), b5-b9 included', 'REPORT', 'interim', None, None,
            ok=a1['final'] is False and a1['extension']['included_extension'] == ['b5', 'b6', 'b7', 'b8', 'b9'])
        snap = load(R / '2026-10_ext1/C8_A1_close/a1_close_snapshot.json')
        info('C', 'A1-close snapshot', '2026-10_ext1/C8_A1_close/a1_close_snapshot.json', 'inclusion set recorded at the A1 close: ' +
             json.dumps({k: v for k, v in snap.items() if k in ('deadline', 'snapshot_time', 'included', 'complete')})[:200])

    # ---------------------------------------------------------------- D: inputs and the affine map
    from campaign import inventory
    inp = W / 'inputs_shared'
    rows8 = inventory(inp, 8)
    row('D', 'nine-vertex classes (L8)', 'Sec 30.2', 26540, len(rows8), 0)
    row('D', 'classes with a power-divergent subgraph', 'Sec 30.2', 7231, sum(r['power'] for r in rows8), 0)
    row('D', 'primitive and power-free classes (the raw primitive flag counts 338)', 'Sec 30.2', 248,
        sum(1 for r in rows8 if r['primitive'] and not r['power']), 0)
    row('D', 'coordinate terms', 'Sec 30.2', 2507176, sum(r['terms'] for r in rows8), 0)
    zt = (inp / 'exact_zero_L8.txt').read_text().split()
    row('D', 'identically vanishing forest polynomials', 'Sec 30.2', 3908, len(zt) - 1, 0, ok=int(zt[0]) == len(zt) - 1 == 3908)
    aff = load(T / 'analysis/v1/full_affine8.json')
    row('D', 'K reproduces C2 exactly', 'Sec 30.2', 0.0, aff['lower_order_checks'][0]['difference'], 0)
    row('D', 'K: C3 - exact', 'Sec 30.2', -1.3e-12, aff['lower_order_checks'][1]['difference'], 5e-14)
    row('D', 'K: C4 - exact', 'Sec 30.2', 1.1e-9, aff['lower_order_checks'][2]['difference'], 5e-11)
    row('D', 'K[C8] (loops one to four)', 'Sec 30.4 table', 1531302.35, aff['K'][8], 0.005)
    row('D', 'top-loop channel ratio', 'Sec 30.2', -3.0, aff['top_loop_channel_rule']['ratio_B_over_A'], 1e-12)
    K = np.array(aff['K']); J5 = np.array(aff['loops']['5']['J']); ref5 = -731.13947662454
    for N, q, tol in ((6, -0.94, 0.005), (8, -0.13, 0.005), (10, -0.019, 5e-4), (12, -0.0032, 5e-5), (14, -5.8e-4, 5e-6)):
        v5 = np.array(load(T / f'runs/exact8_L5/exact_L5/merged/N{N}.json')['batches'], dtype=float)[0]
        c5 = float((K + J5 @ v5)[5])
        row('D', f'C5 at loop-5 degree {N} minus exact (recomputed)', 'Sec 30.2', q, c5 - ref5, tol)
    # ---------------------------------------------------------------- E: cited checks
    import campaign, design8
    _orig = campaign.campaign_inputs
    campaign.campaign_inputs = lambda d, m: (_orig(d, m) if _orig(d, m).is_dir() else inp)
    prim = {r['id'] for r in inventory(inp, 7) if r['primitive'] and not r['power']}
    P7 = None
    if a.c7_final.is_file():
        ag = load(a.c7_final)['campaign_aggregates']
        P7 = ag['tprodA_L7']['mean_C7'] + ag['tprodB_L7']['mean_C7']
        row('E', 'pilot hazard: C7 production value', 'Sec 30.3', 16372.8, P7, 0.05)
    else:
        skip('E', 'pilot hazard: C7 production value', 'Sec 30.3', f'{a.c7_final} absent')
    # (campaign, label, quoted replicates, mean, SE, distance below the C7 production, in its own SEs)
    for c, label, nrep, qm, qs, qd, qz in (
            ('runs/pilot8/tprodA_L7', 'pilot campaign A, 64 points per graph', 16, -16793.9, 9359.6, 33166.7, 3.5),
            ('runs/pilot8/tprodB_L7', 'pilot campaign B, 64 points per graph', 16, -13230.8, 7406.2, 29603.7, 4.0),
            ('runs/tailtest_L7/tprodA_L7', 'repetition of A, 4096 points per graph', 32, 16838.1, 724.1, None, None)):
        tt = T / c
        if not tt.is_dir():
            skip('E', f'pilot hazard: {label}', 'Sec 30.3', f'{c} not in data'); continue
        y, n, _ = design8.per_graph(tt, np.array(aff['loops']['7']['J'])[7])  # verbatim production function, full verification
        reps = max(r for r, g in y) + 1
        N7 = np.array([sum(v for (r, g), v in y.items() if r == rr and g not in prim) for rr in range(reps)])
        se = N7.std(ddof=1) / reps ** .5
        row('E', f'pilot hazard: {label}, replicates', 'Sec 30.3', nrep, reps, 0)
        row('E', f'pilot hazard: {label}, non-primitive C7 row', 'Sec 30.3', qm, N7.mean(), 0.05)
        row('E', f'pilot hazard: {label}, its SE', 'Sec 30.3', qs, se, 0.05)
        if qd is not None and P7 is not None:
            row('E', f'pilot hazard: {label}, below the C7 production', 'Sec 30.3', qd, P7 - N7.mean(), 0.05)
            row('E', f'pilot hazard: {label}, in its own SEs', 'Sec 30.3', qz, (P7 - N7.mean()) / se, 0.05)
    V = PKG / 'validation/expanse_2026-10-02'
    v = load(V / 'c8_vs_c7_T1-T5_job54592375.json')
    row('E', 'kernel: power mode bitwise vs C7 (L5-L7, deg 1-6)', 'Sec 30.3', 0, sum(c['mismatched_values'] for c in v['T2_power_bitwise']['cases'].values()), 0)
    row('E', 'kernel: QMC max relative difference', 'Sec 30.3', 8e-17, max(float(c['max_relative']) for c in v['T3_qmc']['cases'].values()), 5e-18)
    row('E', 'kernel: binary128 replay at L8 (row scale)', 'Sec 30.3', 2.5e-17, float(v['T5_binary128_replay']['cases']['L8_N6']['max_relative_to_row_scale']), 5e-19)
    b = load(V / 'bench8_job54591957.json')['power_L8']['degrees']
    row('E', 'cost model: one L8 power replicate, degree 6 (core-h)', 'Sec 30.2', 5, b['6']['per_replicate_all_graphs_core_hours'], 0.5)
    row('E', 'cost model: degree 7 (core-h)', 'Sec 30.2', 14, b['7']['per_replicate_all_graphs_core_hours'], 0.5)
    info('E', 'cost model: degrees 8, 9 (32, 67 core-h)', 'Sec 30.2; PLAN.md', 'extrapolations stated in PLAN.md, not measurements')
    info('E', 'core-hours of the calculation', 'Sec 30.3', 'about 9e4 physical core-hours (1.4e5 as charged): Slurm accounting, not replayed')

    # ---------------------------------------------------------------- report
    W.mkdir(parents=True, exist_ok=True)
    head = ('sec', 'check', 'where', 'quoted / expected', 'recomputed', 'tolerance', 'status')
    lines = ['\t'.join(head)] + ['\t'.join(r) for r in ROWS]
    (W / 'verify_c8.tsv').write_text('\n'.join(lines) + '\n')
    wid = [max(len(r[i]) for r in [head] + ROWS) for i in range(7)]
    for r in [head] + ROWS: print('  '.join(c.ljust(min(w, 60))[:60] for c, w in zip(r, wid)))
    nf = sum(r[6] == 'FAIL' for r in ROWS); np_ = sum(r[6] == 'PASS' for r in ROWS)
    print(f'\nC8(1) verify: {np_} PASS, {nf} FAIL, {sum(r[6] == "SKIP" for r in ROWS)} SKIP, {sum(r[6] == "INFO" for r in ROWS)} INFO')
    return 1 if nf else 0


if __name__ == '__main__':
    sys.exit(main())
