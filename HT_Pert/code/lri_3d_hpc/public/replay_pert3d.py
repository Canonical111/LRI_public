#!/usr/bin/env python3
"""Replay of every d = 3 number of this package quoted in the HT_Pert note (Supplemental Material) or in earlier paper drafts.

Reads the shipped production records of the Expanse campaign pert3d (HT_Pert/data/HT_3d/pert3d), checks their
integrity and the hash chain code -> store -> gate -> solve -> result, rebuilds the C_n(L) table of
HT_Pert/results/HT_3d/SUMMARY.md, and recomputes each quoted number. Prints a PASS/FAIL table, writes it to --out,
and exits 1 on any FAIL. Nothing is re-solved: `make -f public.mk test` reruns the package's own checks and
public/REPRODUCE.md describes a production rerun.

Run from code/lri_3d_hpc:  python3 -B public/replay_pert3d.py   (make -f public.mk replay)
Needs Python >= 3.9 only (standard library; decimal arithmetic on the records' 20-digit strings).

Check ids are the names used in results_map.md and in the note's reproduction table.
"""
import argparse, hashlib, io, json, sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                     # code/lri_3d_hpc
CUTOFFS = (16, 18, 20)
SCHEMES = ('raw', 'consistent')
# The eight files whose sha256 every result and gate record carries (request.source_sha256).
SOURCES = ['ht3d_coefficients.py', 'mpi_backend.py', 'native_backend.py', 'native_kernels.cpp',
           'optimized_solver.py', 'taylor_pipeline.py', 'taylor_vertices.py', 'vertex_store.py']
# Continuum values C_n(3), Table 1 (tab:pt) of the paper (GFF/note/README.md "Current numerical entries"; C2..C5 exact,
# C6..C8 the estimators with their reported allowances).
CONT = {2: ('0.18122178540555422213', '0'),          # (2 + 4 log 2 - pi)/9
        3: ('-0.353581520433', '0'),
        4: ('1.22806354532762307997', '0'),
        5: ('-5.8503514207513272292', '0'),
        6: ('33.57542664131543', '0.0005'),
        7: ('-220.35448047392794', '0.13'),
        8: ('1602.6052229663408', '3.9')}
# Quoted in earlier paper drafts (\HTpRatio<n>Three; defined, unprinted, in the final numbers.tex): C_n(20)/C_n, consistent, 3 decimals.
RATIOS = {2: '0.995', 3: '0.933', 4: '0.603', 5: '0.577', 6: '0.507', 7: '0.414', 8: '0.378'}


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Table:
    def __init__(self):
        self.rows = []

    def add(self, cid, quoted, value, rule, ok, note=''):
        self.rows.append({'id': cid, 'quoted': quoted, 'replayed': value, 'rule': rule,
                          'status': ok if isinstance(ok, str) else ('PASS' if ok else 'FAIL'), 'note': note})

    def text(self):
        head = ('id', 'quoted', 'replayed', 'status')
        w = [max(len(str(r[k])) for r in self.rows + [dict(zip(head, head))]) for k in head]
        out = io.StringIO()
        out.write('  '.join(h.ljust(n) for h, n in zip(head, w)) + '  rule\n')
        for r in self.rows:
            out.write('  '.join(str(r[k]).ljust(n) for k, n in zip(head, w)) + '  ' + r['rule']
                      + (f'  [{r["note"]}]' if r['note'] else '') + '\n')
        return out.getvalue()


def load(p):
    return json.loads(Path(p).read_text())


def scaled_diff(a, b):
    """The package's validate_coefficients (code/ht3d_coefficients.py) in exact decimal arithmetic on the stored
    strings: max over C, r, g, energies_by_seed, vacuum_energies_by_subcutoff of |a - b| / max(1, |b|).
    a and b are 'result' dicts; the key sets of the two dict series must agree."""
    worst = Decimal(0)
    for field in ('C', 'r', 'g', 'energies_by_seed', 'vacuum_energies_by_subcutoff'):
        x, y = a[field], b[field]
        if isinstance(x, dict):
            if set(x) != set(y):
                raise ValueError('series keys differ: ' + field)
            pairs = [(x[k], y[k]) for k in x]
        else:
            pairs = [(x, y)]
        for u, v in pairs:
            if len(u) != len(v):
                raise ValueError('series lengths differ: ' + field)
            for s1, s2 in zip(u, v):
                d1, d2 = Decimal(s1), Decimal(s2)
                worst = max(worst, abs(d1 - d2) / max(Decimal(1), abs(d2)))
    return worst


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', default=str(PKG / '../../data/HT_3d/pert3d'))
    ap.add_argument('--manifest', default=str(PKG / '../../data/HT_3d/MANIFEST.sha256'))
    ap.add_argument('--summary', default=str(PKG / '../../results/HT_3d/SUMMARY.md'))
    ap.add_argument('--out', default=str(PKG / '.work/replay'))
    a = ap.parse_args()
    data, out = Path(a.data), Path(a.out)
    T = Table()

    # REC-MANIFEST: every shipped record against HT_Pert/data/HT_3d/MANIFEST.sha256 (sha256sum format). Records listed
    # in HT_Pert/data/HT_3d/SCRUBBED.txt (if present: placeholders replaced cluster paths before publication, AGENTS.md
    # rule 7) count as scrubbed; any other difference fails. The hash-bound records (results, gates, crosscheck) are
    # never scrubbed: REC-SRC, REC-CHAIN, CROSSCHECK-L16 and GATE-L14 check their contents and bindings.
    mdir = Path(a.manifest).parent
    scrubbed = set()
    if (mdir / 'SCRUBBED.txt').exists():
        scrubbed = {l.strip() for l in (mdir / 'SCRUBBED.txt').read_text().splitlines() if l.strip() and not l.startswith('#')}
    entries = {}
    for line in Path(a.manifest).read_text().splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            entries[name.lstrip('*')] = digest
    bad = sorted(n for n, h in entries.items() if (mdir / n).exists() and sha256_file(mdir / n) != h and n not in scrubbed)
    missing = sorted(n for n in entries if not (mdir / n).exists())
    shipped = {str(p.relative_to(mdir)) for p in data.rglob('*') if p.is_file()}
    unlisted = sorted(shipped - set(entries))
    stale = sorted(scrubbed - set(entries))
    bound = [n for n in scrubbed if n.split('/')[1:2] and n.split('/')[1] in ('results', 'gates', 'crosscheck')]
    nscr = sum(1 for n in scrubbed if n in entries and (mdir / n).exists() and sha256_file(mdir / n) != entries[n])
    T.add('REC-MANIFEST', 'records as produced', f'{len(entries)} files, {len(bad)} differ, {nscr} scrubbed, '
          f'{len(missing)} missing, {len(unlisted)} unlisted',
          'sha256 of every shipped record equals MANIFEST.sha256 (files in SCRUBBED.txt excepted, never a result, gate '
          'or crosscheck record); nothing extra', not (bad or missing or unlisted or stale or bound),
          '; '.join((bad + missing + unlisted + stale + bound)[:3]))

    # Results of the three stores (each store's own cutoff), the gates and the cross-store solves
    res = {(L, s): load(data / f'results/L{L}/c{L}_{s}.json') for L in CUTOFFS for s in SCHEMES}
    gates = {(L, s): load(data / f'gates/L{L}/{s}_c14.json') for L in CUTOFFS for s in SCHEMES}
    camp = load(data / 'campaign.json')

    # REC-SRC: the shipped code is the code that produced every result and gate
    have = {f: sha256_file(PKG / 'code' / f) for f in SOURCES}
    srcs = [r['request']['source_sha256'] for r in list(res.values()) + list(gates.values())]
    src_ok = all(s == have for s in srcs)
    T.add('REC-SRC', 'code at 7c8a67e', f'{len(srcs)} records, {"all" if src_ok else "NOT all"} match code/',
          'request.source_sha256 of every result and gate record equals sha256 of the 8 shipped code files', src_ok)

    # REC-CHAIN: store manifest hash verify -> gate -> solve -> result, release fingerprint, completeness
    chain = []
    for L in CUTOFFS:
        verify = load(data / f'records/L{L}/verify/store.json')
        h = verify['store_manifest_sha256']
        for s in SCHEMES:
            r, g = res[L, s], gates[L, s]
            solve = [load(p) for p in (data / f'records/L{L}/solve').glob(f'c{L}_{s}.*.json')]
            gate = [load(p) for p in (data / f'records/L{L}/gate').glob(f'c14_{s}.*.json')]
            ok = (verify['passed'] and r['complete'] and g['complete']
                  and r['request']['store_manifest_sha256'] == h == g['request']['store_manifest_sha256']
                  and len(solve) == 1 and len(gate) == 1 and solve[0]['rc'] == 0 and gate[0]['rc'] == 0
                  and solve[0]['store_manifest_sha256'] == h == gate[0]['store_manifest_sha256']
                  and solve[0]['release'] == gate[0]['release'] == camp['release']['fingerprint']
                  and r['request']['cutoff'] == L and g['request']['cutoff'] == 14
                  and r['request']['order'] == g['request']['order'] == camp['order'] == 8
                  and r['request']['scheme'] == g['request']['scheme'] == s)
            chain.append(ok)
    T.add('REC-CHAIN', 'verify -> gate -> solve', f'{sum(chain)}/{len(chain)} store/scheme chains intact',
          'store manifest sha256 equal in verify, gate and solve records and in the result and gate requests; '
          'release fingerprint of the campaign; cutoff, order 8, scheme', all(chain))

    # CUTOFFS (\HTpThreeLmax and the list L = 16, 18, 20 of the HT_Pert note)
    T.add('CUTOFFS', 'L = 16, 18, 20 (\\HTpThreeLmax = 20)', ', '.join(str(L) for L in sorted({k[0] for k in res})),
          'cutoffs of the shipped results', sorted({k[0] for k in res}) == [16, 18, 20])

    # RESIDUAL: x87 recursion/tuning residual gate of every result
    rmax = max(Decimal(r['execution']['residual_gate']['value']) for r in res.values())
    T.add('RESIDUAL', '<= 1e-16', f'{rmax:.2e}', 'max residual_gate.value over the 6 results; limit 1e-16',
          rmax <= Decimal('1e-16') and all(r['execution']['residual_gate']['limit'] == '1e-16' for r in res.values()))

    # TABLE: SUMMARY.md rows rebuilt from the records (C2..C8 strings exactly as stored)
    summary = Path(a.summary).read_text().splitlines() if Path(a.summary).exists() else []
    rows = ['| %d | %s | ' % (L, s) + ' | '.join(res[L, s]['result']['C'][2:]) + ' |' for L in CUTOFFS for s in SCHEMES]
    missing_rows = [r for r in rows if r not in summary]
    T.add('TABLE', 'SUMMARY.md, 6 rows', f'{len(rows) - len(missing_rows)}/{len(rows)} rows identical',
          'C2..C8 of every (L, scheme) record, as stored, equal the rows of results/HT_3d/SUMMARY.md', not missing_rows)

    # RATIO-n: C_n(20)/C_n, consistent scheme (earlier paper drafts; \HTpRatio<n>Three)
    lines = ['n,C_n(20)_consistent,C_n(3),allowance,ratio,ratio_low,ratio_high,quoted']
    for n, q in RATIOS.items():
        c20 = Decimal(res[20, 'consistent']['result']['C'][n])
        c, u = (Decimal(x) for x in CONT[n])
        ratio = c20 / c
        lo, hi = sorted((c20 / (c - u), c20 / (c + u))) if u else (ratio, ratio)
        rounded = f'{ratio:.3f}'
        lines.append(f'{n},{c20},{c},{u},{ratio:.6f},{lo:.6f},{hi:.6f},{q}')
        band = f' (allowance gives {lo:.4f}..{hi:.4f})' if u else ''
        T.add(f'RATIO-{n}', q, f'{ratio:.5f}{band}',
              f'C{n}(20) consistent / C{n}(3), rounded to 3 decimals (central value of C{n}(3))', rounded == q)

    # C4-RATIO: the 60.26 % that HT/code/lri_3d_window_hpc reads from SUMMARY.md (\HTnpDthreeCfourRatio = 60 %)
    pct = 100 * Decimal(res[20, 'consistent']['result']['C'][4]) / Decimal(CONT[4][0])
    T.add('C4-RATIO', '60.26 % (HT: 60 %)', f'{pct:.2f} %', 'C4(20) consistent / C4(3) in percent, 2 decimals',
          f'{pct:.2f}' == '60.26')

    # GATE-L14: cutoff-14 solve on every production store against the original code's reference results
    # (\HTpThreeGateL, \HTpThreeGate "about 1e-14"). reference_sha256 binds the shipped
    # results/reference_coefficients_L14.json; the scaled error is recomputed here from the gate record and that file.
    ref_path = PKG / 'results/reference_coefficients_L14.json'
    ref_sha, ref = sha256_file(ref_path), load(ref_path)['results']
    errs, agree = {}, True
    for (L, s), g in gates.items():
        row = [r for r in ref if r['cutoff'] == 14 and r['scheme'] == s and r['order'] == 8]
        mine = scaled_diff(g['result'], row[0]) if len(row) == 1 else Decimal('Infinity')
        stored = Decimal(g['execution']['validation']['max_scaled_error'])
        agree &= abs(mine - stored) <= Decimal('1e-17')   # long double vs decimal rounding of the stored strings
        errs[L, s] = mine
    gmax = max(errs.values())
    gate_ok = (agree and all(g['execution']['validation']['reference_sha256'] == ref_sha for g in gates.values())
               and all(Decimal(g['execution']['validation']['tolerance']) == Decimal('5e-13') for g in gates.values())
               and all(e <= Decimal('5e-13') for e in errs.values()))
    T.add('GATE-L14', 'L = 14, about 1e-14', f'max {gmax:.2e} over 6 gates (raw {max(v for k, v in errs.items() if k[1] == "raw"):.1e})',
          'each store solved at L = 14 vs results/reference_coefficients_L14.json (bound by reference_sha256): scaled error '
          'recomputed here, equal to the stored one within 1e-17, <= 5e-13 (tolerance); the max rounds to 1e-14',
          gate_ok and f'{gmax:.0e}' == '1e-14')

    # CROSSCHECK: recurrence strategy against stationary at L = 16 (comparison records bound to both files)
    cc_ok, cc = [], []
    for s in SCHEMES:
        cmp_ = load(data / f'crosscheck/L16/c16_{s}.compare.json')
        same = (cmp_['passed'] and Decimal(cmp_['max_scaled_difference']) <= Decimal(cmp_['limit']) == Decimal('1e-15')
                and cmp_['other_sha256'] == sha256_file(data / f'results/L16/c16_{s}.json')
                and cmp_['result_sha256'] == sha256_file(data / f'crosscheck/L16/c16_{s}.json'))
        mine = scaled_diff(load(data / f'crosscheck/L16/c16_{s}.json')['result'], res[16, s]['result'])
        cc_ok.append(same and mine <= Decimal('1e-15'))
        cc.append(f'{s} {Decimal(cmp_["max_scaled_difference"]):.1e}')
    T.add('CROSSCHECK-L16', '<= 1e-15', ', '.join(cc), 'recurrence vs stationary at L = 16: comparison records pass, '
          'are bound to both files by sha256, and the scaled difference recomputed here is <= 1e-15', all(cc_ok))

    # CROSS-STORE: the L20 store re-solved at L = 16, 18 against the L16 and L18 stores (SUMMARY.md: ~1e-14)
    xs = []
    for L in (16, 18):
        for s in SCHEMES:
            xs.append(scaled_diff(load(data / f'results/L20/c{L}_{s}.json')['result'], res[L, s]['result']))
    T.add('CROSS-STORE', '~1e-14 (SUMMARY.md)', f'max {max(xs):.1e}', 'every series at L = 16, 18 from the L20 store vs the '
          'L16, L18 stores: scaled difference <= 5e-13 (the gate tolerance); SUMMARY.md quotes ~1e-14', max(xs) <= Decimal('5e-13'))

    out.mkdir(parents=True, exist_ok=True)
    (out / 'ratios_L20.csv').write_text('\n'.join(lines) + '\n')
    text = T.text()
    (out / 'replay.txt').write_text(text)
    print(text, end='')
    fails = [r['id'] for r in T.rows if r['status'] == 'FAIL']
    print(f'\n{len(T.rows) - len(fails)}/{len(T.rows)} not failed' + (f'; FAIL: {" ".join(fails)}' if fails else '')
          + f'  (table and ratios in {out})')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
