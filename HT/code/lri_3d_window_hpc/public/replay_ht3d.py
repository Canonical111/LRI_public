#!/usr/bin/env python3
"""Replay of every d = 3 finite-coupling HT number quoted in the paper (main.tex) and in the HT note.

Reads the shipped production records (HT/data/HT_3d/campaigns), checks their integrity, rebuilds the finite-cutoff
table Delta_E(x, L), L = 8..20, and recomputes each quoted number. Prints a PASS/FAIL table, writes it with the
table to --out, and exits 1 on any FAIL. Nothing is re-solved: a production rerun is described in REPRODUCE.md.

Run from code/lri_3d_window_hpc:  python3 -B public/replay_ht3d.py   (make -f public.mk replay)
Needs Python >= 3.10, numpy and scipy (the Borel-Pade check); no numba, no compiler.

Check ids are the names used in results_map.md and in the HT note's reproduction table.
"""
import argparse, csv, hashlib, io, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                   # code/lri_3d_window_hpc
sys.path.insert(0, str(HERE))

X_GRID = [0.7499, 0.745, 0.74, 0.725, 0.7, 0.675, 0.65, 0.625, 0.6, 0.575, 0.55, 0.535, 0.525, 0.52, 0.518149]
LADDER = [8, 10, 12, 14, 16, 18, 20]
# where each (x, L) record lives: the L8-L18 ladder in grid18 (grid18sri at the SR end), L20 in grid20/grid20sri/l20x06
def record_path(root, x, L):
    xs = f'x{x:g}' if x != 0.518149 else 'x0.518149'
    if L <= 18:
        camp = 'grid18sri' if x == 0.518149 else 'grid18'
        return root / camp / 'results' / 't16' / xs / f'window_L{L}.json'
    if x == 0.6:
        return root / 'l20x06' / 'results' / 'ls32' / xs / 'window_L20.json'
    camp = 'grid20sri' if x == 0.518149 else 'grid20'
    return root / camp / 'results' / 's32' / xs / 'window_L20.json'

# --- the package's own definitions (code/ht3d/hpc.py: canonical_json, digest, source_hash), copied so that the
#     replay needs no numba import; check REC-SRC compares with the shipped code itself.
def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(data): return hashlib.sha256(canonical_json(data)).hexdigest()
def source_hash(root):
    h = hashlib.sha256()
    paths = sorted((root / 'code').rglob('*.py')) + [root / 'inputs/prior_3d_points.json']
    for p in paths:
        h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()
def sha256_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def shipped(campaigns, original):
    """Map a production path (<SCRATCH>/ht3d/campaigns/<campaign>/...) to the shipped copy."""
    s = str(original); i = s.find('/campaigns/')
    return campaigns / s[i + len('/campaigns/'):] if i >= 0 else None

def fmt_sig(v, n):
    """v rounded to n significant digits, as a float."""
    return float(f'{v:.{n - 1}e}')

class Table:
    def __init__(self): self.rows = []
    def add(self, cid, quoted, value, rule, ok, note=''):
        self.rows.append({'id': cid, 'quoted': quoted, 'replayed': value, 'rule': rule,
                          'status': ok if isinstance(ok, str) else ('PASS' if ok else 'FAIL'), 'note': note})
    def text(self):
        w = [max(len(str(r[k])) for r in self.rows + [{k: k for k in self.rows[0]}]) for k in ('id', 'quoted', 'replayed', 'status')]
        out = io.StringIO()
        head = ('id', 'quoted', 'replayed', 'status')
        out.write('  '.join(h.ljust(n) for h, n in zip(head, w)) + '  rule\n')
        for r in self.rows:
            out.write('  '.join(str(r[k]).ljust(n) for k, n in zip(head, w)) + '  ' + r['rule']
                      + (f'  [{r["note"]}]' if r['note'] else '') + '\n')
        return out.getvalue()

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--campaigns', default=str(PKG / '../../data/HT_3d/campaigns'))
    ap.add_argument('--manifest', default=str(PKG / '../../data/HT_3d/MANIFEST.sha256'))
    ap.add_argument('--expected-table', default=str(PKG / '../../results/HT_3d/finite_L_table.csv'))
    ap.add_argument('--pert-summary', default=str(PKG / '../../../HT_Pert/results/HT_3d/SUMMARY.md'),
                    help='HT_Pert record with C4(L=20) (lri_ht3d_pert, SUMMARY.md); if the file is absent the C4-RATIO row is SKIP')
    ap.add_argument('--out', default=str(PKG / '.work/replay'))
    a = ap.parse_args()
    root = Path(a.campaigns).resolve(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    T = Table()

    # ---------------- REC: integrity of the shipped records ----------------
    man = Path(a.manifest)
    if man.exists():
        bad = []; n = 0
        for line in man.read_text().splitlines():
            if not line.strip(): continue
            h, rel = line.split(None, 1); n += 1
            p = man.parent / rel.strip()
            if not p.exists() or sha256_file(p) != h: bad.append(rel)
        T.add('REC-MANIFEST', f'{n} files', f'{n - len(bad)} match', 'sha256 of every file in data/HT_3d/MANIFEST.sha256', not bad,
              ', '.join(bad[:3]))
    else:
        T.add('REC-MANIFEST', '-', 'missing', 'data/HT_3d/MANIFEST.sha256 present', False, str(man))
    rec = {}; problems = []
    for x in X_GRID:
        for L in LADDER:
            p = record_path(root, x, L)
            if not p.exists(): problems.append(f'missing {p.relative_to(root)}'); continue
            try:
                check_record(root, p, x, L, rec, problems)
            except (KeyError, TypeError, ValueError) as exc:
                problems.append(f'malformed {p.relative_to(root)}: {exc!r}')
    T.add('REC-RECORDS', f'{len(X_GRID) * len(LADDER)} records', f'{len(rec)} read',
          'all present; record_sha256 = sha256(canonical JSON); accepted; tuning gate; eigenpair residual <= 1e-8; targets x, 3-x to 1e-9; '
          'seed/basis sha256 chain', not problems, '; '.join(problems[:4]))
    try:
        rows_from_records(a, root, out, T, rec, problems)
    except Exception as exc:                          # a malformed input is a FAIL with a table, never a bare crash
        T.add('REPLAY-ERROR', '-', type(exc).__name__, 'the replay could not finish', False, repr(exc)[:200])
    finish(T, out)

def check_record(root, p, x, L, rec, problems):
    r = json.loads(p.read_text()); rec[x, L] = (p, r)
    body = dict(r); sig = body.pop('record_sha256', None)
    c = r['configuration']
    if sig != digest(body): problems.append(f'record_sha256 {p.relative_to(root)}')
    if not r.get('accepted') or not r.get('request_digest'): problems.append(f'not accepted {p.relative_to(root)}')
    if abs(r['delta'] - x) > 1e-12 or r['bath_cut'] != L or c['L'] != L: problems.append(f'x/L {p.relative_to(root)}')
    if r['tuning_residual'] > max(1e-10, 5 * c['tuning_tol']): problems.append(f'tuning gate {p.relative_to(root)}')
    if not r['max_eigenvector_residual'] <= c['residual_tol']: problems.append(f'eigen residual {p.relative_to(root)}')
    if abs(r['Delta_sigma_measured'] - x) > 1e-9 or abs(r['Delta_shadow_measured'] - (3 - x)) > 1e-9:
        problems.append(f'targets {p.relative_to(root)}')
    if c['window'] != 'vacuum' or c['window_mode'] != 'consistent' or c['nz'] != 16: problems.append(f'scheme {p.relative_to(root)}')
    for key in ('seed', 'basis'):                     # the continuation chain: inputs hashed byte for byte
        if c.get(key):
            q = shipped(root, c[key])
            if q is None or not q.exists() or sha256_file(q) != c[key + '_sha256']:
                problems.append(f'{key} chain {p.relative_to(root)}')

def rows_from_records(a, root, out, T, rec, problems):
    srcs = {r['configuration']['source_sha256'] for _, r in rec.values()}
    code_hash = source_hash(PKG)
    T.add('REC-SRC', 'one numerical source', f'{len(srcs)} hash(es); code {code_hash[:12]}',
          'every record has the source_sha256 of the shipped code/ (ht3d.hpc.source_hash)', srcs == {code_hash})
    if len(rec) < len(X_GRID) * len(LADDER):
        return                                        # without every record the quoted numbers cannot be rebuilt

    D = {(x, L): r['Delta_thermal'] for (x, L), (_, r) in rec.items()}
    step = lambda x, L: D[x, L] - D[x, L - 2]

    # ---------------- CONFIG and SIZE: the setup the note states ----------------
    teach = [json.loads((record_path(root, x, 8).parent / 'teacher_L6.json').read_text()) for x in X_GRID]
    tc = {(t['configuration']['L'], t['configuration']['nz'], t['configuration']['osc'], t['configuration']['train_keep']) for t in teach}
    wc = {(r['configuration']['nz'], r['configuration']['osc'], r['configuration']['backend'], r['configuration']['tuning_tol'],
           r['basis_input']['retained']) for _, r in rec.values()}
    lim = {L: {rec[x, L][1]['configuration']['max_bath_states'] for x in X_GRID} for L in (16, 18, 20)}
    ok = (tc == {(6, 24, 192, 20)} and wc == {(16, 192, 'tensor', 3e-11, 16)}
          and lim == {16: {10_000_000}, 18: {50_000_000}, 20: {200_000_000}})
    T.add('CONFIG', 'teacher N=6, n_z=24, osc 192, keep 20; n_z=16; tol 3e-11',
          f'teacher {sorted(tc)}; window {sorted(wc)}', 'note: teacher and window-step configuration from the records; '
          'bath-state limits 1e7 (N=16), 5e7 (18), 2e8 (20)', ok)
    nB = {L: {rec[x, L][1]['dimension'] // (2 * rec[x, L][1]['nz_per_parity']) for x in X_GRID} for L in LADDER}
    want = {8: 110, 10: 371, 12: 1285, 14: 4486, 16: 15815, 18: 55859, 20: 196585}
    T.add('SIZE', 'J=0 bath states 110 ... 196585', ', '.join(f'{L}:{min(v)}' for L, v in nB.items()),
          'note: scalar (J=0, inversion-even) bath states = dimension/(2 n_z), the same at every Ds; product dimension '
          'per field parity at N=20 = 196585 x 16', all(v == {want[L]} for L, v in nB.items()))

    # ---------------- TABLE: the finite-cutoff table (its L = 20 row: paper Table num3 and Fig. cmp2d3d) ----------------
    buf = io.StringIO(); wr = csv.writer(buf, lineterminator='\n')
    wr.writerow(['Delta_sigma', 'L', 'Delta_E', 'r', 'g', 'tuning_residual', 'elapsed_s', 'peak_rss_gib', 'record', 'record_sha256'])
    for x in X_GRID:
        for L in LADDER:
            p, r = rec[x, L]
            wr.writerow([repr(x), L, repr(r['Delta_thermal']), repr(r['r']), repr(r['g']), repr(r['tuning_residual']),
                         f"{r['elapsed_total_seconds']:.1f}", f"{r['peak_rss_kib'] / 2**20:.2f}",
                         str(p.relative_to(root.parent)), r['record_sha256']])
    (out / 'finite_L_table.csv').write_text(buf.getvalue())
    exp = Path(a.expected_table)
    if exp.exists():
        same = exp.read_text() == buf.getvalue()
        T.add('TABLE', 'results/HT_3d/finite_L_table.csv', 'identical' if same else 'differs',
              'rebuilt table equals the shipped one byte for byte', same)
    else:
        T.add('TABLE', 'results/HT_3d/finite_L_table.csv', 'not shipped', 'rebuilt table equals the shipped one', 'INFO')

    # ---------------- the quoted numbers ----------------
    T.add('NMAX', '20', str(max(L for (_, L) in D)), r'\HTnpDthreeNmax: largest cutoff, every x accepted', max(L for (_, L) in D) == 20)
    # main.tex Table tab:num3, column "HT, N = 20", as printed (the value at 0.518149 is \HTnpDthreeSR)
    NUM3 = {0.7499: '1.49993', 0.745: '1.49674', 0.74: '1.49360', 0.725: '1.48486', 0.7: '1.47192', 0.675: '1.46053',
            0.65: '1.45062', 0.625: '1.44218', 0.6: '1.43511', 0.575: '1.42923', 0.55: '1.42435', 0.535: '1.42182',
            0.525: '1.42026', 0.52: '1.41951', 0.518149: '1.41924'}
    bad = [x for x in X_GRID if f'{D[x, 20]:.5f}' != NUM3[x]]
    T.add('NUM3', '15 values 1.41924 ... 1.49993', f'{len(X_GRID) - len(bad)} of {len(X_GRID)} equal',
          'Table tab:num3, HT column: D(x, 20) rounded to 5 decimals equals the printed value at every x', not bad,
          ', '.join(f'differs at x={x}' for x in bad))
    weak = [x for x in X_GRID if x >= 0.74]
    conv = max(abs(step(x, 20)) for x in weak)
    T.add('CONV-STEP', '< 1e-7', f'{conv:.2e}', r'\HTnpDthreeConvStep: max |D(20)-D(18)| at x >= 0.74 below 1e-7', conv < 1e-7)
    mono = [x for x in X_GRID if x <= 0.625]
    d20 = [step(x, 20) for x in mono]
    lo, hi = min(d20), max(d20)
    T.add('MONO-STEPS', '(2.2-6.1)e-4', f'{lo:.3e} .. {hi:.3e}',
          r'\HTnpDthreeMonoSteps: D(20)-D(18) at 0.518 <= x <= 0.625, range to 2 significant digits',
          fmt_sig(lo, 2) == 2.2e-4 and fmt_sig(hi, 2) == 6.1e-4)
    rises = all(D[x, L] > D[x, L - 2] for x in mono for L in LADDER[1:])
    T.add('MONO-RISE', 'rises', 'strictly increasing L8..L20' if rises else 'not monotone',
          'D(x, L) increases at every step at 0.518 <= x <= 0.625', rises)
    shrink = {x: 100 * (1 - step(x, 20) / step(x, 18)) for x in mono}
    smin, smax = min(shrink.values()), max(shrink.values())
    T.add('MONO-SHRINK', '8 to 19 %', f'{smin:.1f} .. {smax:.1f} %', r'\HTnpDthreeMonoShrink: 100(1 - d20/d18), rounded to integers',
          round(smin) == 8 and round(smax) == 19, f'x={min(shrink, key=shrink.get)} .. x={max(shrink, key=shrink.get)}')
    ratios = {x: step(x, 20) / step(x, 18) for x in (0.65, 0.675)}
    T.add('NO-SHRINK', 'steps do not yet shrink', ', '.join(f'{x}: {v:.3f}' for x, v in ratios.items()),
          'note: d20/d18 > 0.99 at x = 0.65 and 0.675', all(v > 0.99 for v in ratios.values()))
    sr = D[0.518149, 20]
    T.add('SR-L20', '1.41924', f'{sr:.8f}', r'\HTnpDthreeSR (Table tab:num3 and note): D(20) at x = 0.518149 to 5 decimals, still rising (d20 > 0)',
          round(sr, 5) == 1.41924 and step(0.518149, 20) > 0)
    ising = 1.41262528            # 3D Ising Delta_epsilon, bootstrap (cited input, not replayed)
    T.add('SR-GAP', '6.6e-3 above Ising', f'{sr - ising:.3e}', 'note: D(20) at x = 0.518149 minus 1.41262528, to 2 significant digits',
          fmt_sig(sr - ising, 2) == 6.6e-3)
    from bp_x07 import bp
    b = bp(0.7)
    T.add('BP-0.7', '1.47214(3)', f"{b['median']:.7f} +- {b['half_spread']:.1e} (n={b['n']})",
          r'\HTnpDthreeBPerr: Borel-Pade median at x=0.7 = 1.4721437 to 1e-7; half-spread to 1 significant digit = 3e-5; 29 approximants',
          abs(b['median'] - 1.4721437) < 1e-7 and fmt_sig(b['half_spread'], 1) == 3e-5 and b['n'] == 29)
    dev = b['median'] - D[0.7, 20]
    away = D[0.7, 16] > D[0.7, 18] > D[0.7, 20] and b['median'] > D[0.7, 16]
    T.add('BP-DEV', '2.2e-4 below, moves away', f'{dev:.3e}',
          r'\HTnpDthreeBPdev: BP(0.7) - D(0.7, 20) to 2 significant digits; D(16) > D(18) > D(20) below BP',
          fmt_sig(dev, 2) == 2.2e-4 and away)
    # C4 ratio: C4 of the consistent window at L = 20 (HT_Pert record) over C4(3) = 1.228063545 (closed form, GFF)
    C4_3 = 1.228063545; C4_L20_cited = 0.7400078407092003721
    src = Path(a.pert_summary) if a.pert_summary else None
    if src and src.exists():
        row = [l for l in src.read_text().splitlines() if l.startswith('| 20 | consistent')]
        c4 = float(row[0].split('|')[5]); pct = 100 * c4 / C4_3
        T.add('C4-RATIO', '60%', f'{pct:.2f} % (C4(20) = {c4:.7f})', r'\HTnpDthreeCfourRatio: C4^cons(L=20)/C4(3), rounded to integer percent',
              round(pct) == 60, f'read from {src.name}')
    else:
        T.add('C4-RATIO', '60%', f'({100 * C4_L20_cited / C4_3:.2f} % with the cited C4(20) = {C4_L20_cited:.7f})',
              r'\HTnpDthreeCfourRatio: C4^cons(L=20)/C4(3), rounded to integer percent', 'SKIP',
              f'HT_Pert record not found at {a.pert_summary}; replayed in HT_Pert (lri_ht3d_pert)')
    # SO(3) projector at N = 18, 20: blocks, gesvd fallbacks of the 0.2.1rc1 repair, J+ residual (from the records)
    proj = {}
    for L in (18, 20):
        st = {(r['scalar_projector_checks']['svd_statistics']['blocks'], len(r['scalar_projector_checks']['svd_statistics']['fallback_blocks']))
              for (x, LL), (_, r) in rec.items() if LL == L}
        jp = max(r['scalar_projector_checks']['Jplus_residual'] for (x, LL), (_, r) in rec.items() if LL == L)
        proj[L] = (st, jp)
    T.add('PROJECTOR', 'N=18: 8 of 17335 blocks; N=20: 62 of 40033; residual < 1e-14',
          '; '.join(f'N={L}: {sorted(s)} J+ res {j:.1e}' for L, (s, j) in proj.items()),
          'note: J=0 projector species blocks and gesdd->gesvd fallbacks, identical at every Ds; max |J+ Q| < 1e-14',
          proj[18][0] == {(17335, 8)} and proj[20][0] == {(40033, 62)} and max(j for _, j in proj.values()) < 1e-14)
    # costs quoted in the HT note (from the records themselves)
    l18 = [rec[x, 18][1] for x in X_GRID]
    t18 = [r['elapsed_total_seconds'] / 60 for r in l18]; m18 = [r['peak_rss_kib'] / 2**20 for r in l18]
    T.add('COST-L18', '34-74 min, 38.5 GiB', f'{min(t18):.0f}-{max(t18):.0f} min, {min(m18):.1f}-{max(m18):.1f} GiB',
          'note: N=18 wall time and peak RSS per point (16 cores, J=1 diagnostics), from the records',
          (round(min(t18)), round(max(t18))) == (34, 74) and round(max(m18), 1) == 38.5)
    l20 = [rec[x, 20][1] for x in X_GRID if x != 0.6]
    tmin = min(r['elapsed_total_seconds'] for r in l20) / 60; tmax = max(r['elapsed_total_seconds'] for r in l20) / 60
    mmin = min(r['peak_rss_kib'] for r in l20) / 2**20; mmax = max(r['peak_rss_kib'] for r in l20) / 2**20
    r06 = rec[0.6, 20][1]
    T.add('COST-L20', '27-104 min, 84-87 GiB; x=0.6: 239 min, 328 GiB',
          f'{tmin:.0f}-{tmax:.0f} min, {mmin:.0f}-{mmax:.0f} GiB; x=0.6: {r06["elapsed_total_seconds"] / 60:.0f} min, {r06["peak_rss_kib"] / 2**20:.0f} GiB',
          'note: L20 wall time and peak RSS per point from the records (scalar only; x=0.6 with J=1 diagnostics)',
          (round(tmin), round(tmax), round(mmin), round(mmax)) == (27, 104, 84, 87)
          and (round(r06['elapsed_total_seconds'] / 60), round(r06['peak_rss_kib'] / 2**20)) == (239, 328))

    T.bp = b

def finish(T, out):
    txt = T.text(); print(txt)
    (out / 'replay_table.txt').write_text(txt)
    (out / 'replay.json').write_text(json.dumps({'rows': T.rows, 'bp_0.7': getattr(T, 'bp', None)}, indent=1))
    fails = [r for r in T.rows if r['status'] == 'FAIL']
    print(f"{len(T.rows) - len(fails)}/{len(T.rows)} not failed; outputs in {out}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
